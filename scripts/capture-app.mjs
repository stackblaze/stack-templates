#!/usr/bin/env node
/**
 * Capture high-DPI PNG screenshots from a deployed app URL.
 *
 * Usage:
 *   npm run capture -- --slug attendize --url https://my-app.stackblaze.app
 *   npm run capture -- --slug metabase --url https://... --apply
 *   npm run capture -- --slug n8n --url https://... --spec ./capture-specs/n8n.json
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
} from './capture-lib.mjs';

function parseArgs(argv) {
  const args = { apply: false, headless: true };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--apply') args.apply = true;
    else if (a === '--headed') args.headless = false;
    else if (a === '--slug') args.slug = argv[++i];
    else if (a === '--url') args.url = argv[++i];
    else if (a === '--spec') args.specPath = argv[++i];
    else if (a === '--out') args.outDir = argv[++i];
    else if (a === '--help' || a === '-h') args.help = true;
  }
  return args;
}

function usage() {
  console.log(`Usage:
  node capture-app.mjs --slug <name> --url <https://...> [--apply] [--headed]
  node capture-app.mjs --slug <name> --url <https://...> --spec capture-specs/foo.json

Defaults: 1920×1080 viewport @ 2× DPR → ~3840×2160 PNG (sharp for 1080p video).
Writes to services/<slug>/screenshot-*.png`);
}

async function main() {
  const args = parseArgs(process.argv);
  if (args.help || !args.slug || !args.url) {
    usage();
    process.exit(args.help ? 0 : 1);
  }

  const { spec } = args.specPath
    ? { spec: JSON.parse(fs.readFileSync(args.specPath, 'utf8')) }
    : loadCaptureSpec(args.slug);

  const baseUrl = resolveBaseUrl(spec, args.url);
  const outDir = args.outDir || path.join(SERVICES, args.slug);
  fs.mkdirSync(outDir, { recursive: true });

  const viewport = spec.viewport || DEFAULT_VIEWPORT;
  const dpr = spec.deviceScaleFactor ?? DEFAULT_DPR;

  console.log(`Capturing ${args.slug}`);
  console.log(`  URL: ${baseUrl}`);
  console.log(`  Viewport: ${viewport.width}×${viewport.height} @ ${dpr}× DPR`);
  console.log(`  Out: ${outDir}`);

  const browser = await chromium.launch({ headless: args.headless });
  const context = await browser.newContext({
    viewport,
    deviceScaleFactor: dpr,
    locale: spec.locale || 'en-US',
    colorScheme: spec.colorScheme || 'light',
    ignoreHTTPSErrors: true,
  });
  const page = await context.newPage();
  page.setDefaultTimeout(spec.defaultTimeoutMs || 60000);

  try {
    await runLogin(page, spec.login, baseUrl, context);
    const shots = await capturePages(page, spec, baseUrl, outDir, args.slug);

    if (args.apply) {
      const filenames = shots.map((s) => s.filename);
      const { urls, yamlPatched, indexPatched } = applyCatalogScreenshots(args.slug, filenames);
      console.log(`  Catalog: index=${indexPatched}, yaml=${yamlPatched}`);
      console.log(`  URLs: ${urls.join(', ')}`);
    }

    console.log(`Done — ${shots.length} screenshot(s)`);
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err.message || err);
  process.exit(1);
});
