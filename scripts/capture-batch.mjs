#!/usr/bin/env node
/**
 * Batch-capture screenshots for many deployed templates.
 *
 * Sources (pick one):
 *   --qa              Fetch live URLs from Platform template-validation status (pass only)
 *   --manifest FILE   JSON { "slug": "https://...", ... } or [{ slug, url }]
 *   --slugs a,b,c     With --url-template "https://{slug}.qa.stackblaze.app"
 *
 * Usage:
 *   export STACKBLAZE_TOKEN=...
 *   npm run capture:batch -- --qa --limit 10
 *   npm run capture:batch -- --manifest urls.json --apply
 *   npm run capture:batch -- --slugs metabase,n8n --url-template 'https://{slug}-qa.stackblaze.app'
 */

import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';
import {
  SERVICES,
  DEFAULT_VIEWPORT,
  DEFAULT_DPR,
  loadCaptureSpec,
  resolveBaseUrl,
  runLogin,
  capturePages,
  applyCatalogScreenshots,
  fetchQaUrls,
  readJson,
  writeJson,
} from './capture-lib.mjs';

const REPORT = path.join(path.dirname(new URL(import.meta.url).pathname), 'capture-report.json');

function parseArgs(argv) {
  const args = {
    apply: false,
    headless: true,
    qa: false,
    api: process.env.STACKBLAZE_API || 'https://api.stackblaze.cloud',
    token: process.env.STACKBLAZE_TOKEN || '',
    limit: 0,
    concurrency: 1,
    skip: [],
  };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--apply') args.apply = true;
    else if (a === '--headed') args.headless = false;
    else if (a === '--qa') args.qa = true;
    else if (a === '--manifest') args.manifest = argv[++i];
    else if (a === '--slugs') args.slugs = argv[++i].split(',').map((s) => s.trim()).filter(Boolean);
    else if (a === '--url-template') args.urlTemplate = argv[++i];
    else if (a === '--api') args.api = argv[++i];
    else if (a === '--token') args.token = argv[++i];
    else if (a === '--limit') args.limit = Number(argv[++i]);
    else if (a === '--concurrency') args.concurrency = Math.max(1, Number(argv[++i]));
    else if (a === '--skip') args.skip = argv[++i].split(',').map((s) => s.trim()).filter(Boolean);
    else if (a === '--help' || a === '-h') args.help = true;
  }
  return args;
}

function usage() {
  console.log(`Batch screenshot capture for Stackblaze templates.

  npm run capture:batch -- --qa [--limit N] [--apply]
  npm run capture:batch -- --manifest deploy-urls.json [--apply]
  npm run capture:batch -- --slugs foo,bar --url-template 'https://{slug}.example.app'

Env: STACKBLAZE_TOKEN (required for --qa), STACKBLAZE_API`);
}

async function loadTargets(args) {
  if (args.qa) {
    if (!args.token) throw new Error('STACKBLAZE_TOKEN required for --qa');
    let entries = await fetchQaUrls(args.api, args.token);
    if (args.skip.length) {
      const skip = new Set(args.skip);
      entries = entries.filter((e) => !skip.has(e.slug));
    }
    if (args.limit > 0) entries = entries.slice(0, args.limit);
    return entries;
  }

  if (args.manifest) {
    const raw = readJson(path.resolve(args.manifest));
    if (Array.isArray(raw)) return raw.map((r) => ({ slug: r.slug, url: r.url }));
    return Object.entries(raw).map(([slug, url]) => ({ slug, url }));
  }

  if (args.slugs?.length && args.urlTemplate) {
    return args.slugs.map((slug) => ({
      slug,
      url: args.urlTemplate.replaceAll('{slug}', slug),
    }));
  }

  throw new Error('Provide --qa, --manifest, or --slugs + --url-template');
}

async function captureOne(browser, slug, url, apply) {
  const { spec } = loadCaptureSpec(slug);
  const baseUrl = resolveBaseUrl(spec, url);
  const outDir = path.join(SERVICES, slug);
  fs.mkdirSync(outDir, { recursive: true });

  const context = await browser.newContext({
    viewport: spec.viewport || DEFAULT_VIEWPORT,
    deviceScaleFactor: spec.deviceScaleFactor ?? DEFAULT_DPR,
    locale: spec.locale || 'en-US',
    colorScheme: spec.colorScheme || 'light',
    ignoreHTTPSErrors: true,
  });
  const page = await context.newPage();
  page.setDefaultTimeout(spec.defaultTimeoutMs || 60000);

  try {
    await runLogin(page, spec.login, baseUrl);
    const shots = await capturePages(page, spec, baseUrl, outDir, slug);
    let catalog = null;
    if (apply) {
      catalog = applyCatalogScreenshots(
        slug,
        shots.map((s) => s.filename),
      );
    }
    return { slug, ok: true, shots, catalog };
  } catch (err) {
    return { slug, ok: false, error: err.message || String(err) };
  } finally {
    await context.close();
  }
}

async function runPool(browser, targets, concurrency, apply) {
  const results = [];
  let index = 0;

  async function worker() {
    while (index < targets.length) {
      const i = index++;
      const { slug, url } = targets[i];
      console.log(`\n[${i + 1}/${targets.length}] ${slug}`);
      const result = await captureOne(browser, slug, url, apply);
      results.push(result);
      if (!result.ok) console.error(`  ✗ ${result.error}`);
    }
  }

  await Promise.all(Array.from({ length: concurrency }, () => worker()));
  return results;
}

async function main() {
  const args = parseArgs(process.argv);
  if (args.help) {
    usage();
    process.exit(0);
  }

  const targets = await loadTargets(args);
  if (!targets.length) {
    console.log('No targets to capture.');
    process.exit(0);
  }

  console.log(`Batch capture: ${targets.length} app(s), concurrency=${args.concurrency}`);

  const browser = await chromium.launch({ headless: args.headless });
  try {
    const results = await runPool(browser, targets, args.concurrency, args.apply);
    const ok = results.filter((r) => r.ok);
    const fail = results.filter((r) => !r.ok);

    const report = {
      at: new Date().toISOString(),
      total: results.length,
      ok: ok.length,
      failed: fail.length,
      results,
    };
    writeJson(REPORT, report);

    console.log('\n---');
    console.log(`OK: ${ok.length}  Failed: ${fail.length}`);
    console.log(`Report: ${REPORT}`);
    if (fail.length) process.exit(1);
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err.message || err);
  process.exit(1);
});
