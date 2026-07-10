import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const ROOT = path.resolve(__dirname, '..');
export const SERVICES = path.join(ROOT, 'services');
export const INDEX = path.join(ROOT, 'index.json');
export const SPECS_DIR = path.join(__dirname, 'capture-specs');
export const SCREENSHOT_ANNOTATION = 'kubero.dev/template.screenshots';

export const DEFAULT_VIEWPORT = { width: 1920, height: 1080 };
export const DEFAULT_DPR = 2;

export function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

export function writeJson(filePath, data) {
  fs.writeFileSync(filePath, `${JSON.stringify(data, null, 2)}\n`, 'utf8');
}

export function loadCaptureSpec(slug) {
  const custom = path.join(SPECS_DIR, `${slug}.json`);
  const fallback = path.join(SPECS_DIR, '_default.json');
  const file = fs.existsSync(custom) ? custom : fallback;
  if (!fs.existsSync(file)) {
    throw new Error(`No capture spec for ${slug} and missing ${fallback}`);
  }
  const spec = readJson(file);
  return { spec, file };
}

export function resolveBaseUrl(spec, cliUrl) {
  const raw = cliUrl || spec.baseUrl;
  if (!raw) throw new Error('baseUrl required (CLI --url or spec.baseUrl)');
  return raw.replace(/\/$/, '');
}

export function screenshotUrlsForSlug(slug, filenames) {
  const base =
    'https://raw.githubusercontent.com/stackblaze/stack-templates/main/services';
  return filenames.map((f) => `${base}/${slug}/${f}`);
}

export function patchYamlScreenshots(yamlPath, urls) {
  if (!fs.existsSync(yamlPath)) return false;
  let text = fs.readFileSync(yamlPath, 'utf8');
  const payload = JSON.stringify(urls);
  const pat = new RegExp(`(    ${SCREENSHOT_ANNOTATION.replace(/\./g, '\\.')}: ).*`);
  let newText;
  if (pat.test(text)) {
    newText = text.replace(pat, `$1'${payload}'`);
  } else {
    const insertPat = /(    kubero\.dev\/template\.icon: .*\n)/;
    if (!insertPat.test(text)) return false;
    newText = text.replace(
      insertPat,
      `$1    ${SCREENSHOT_ANNOTATION}: '${payload}'\n`,
    );
  }
  if (newText !== text) {
    fs.writeFileSync(yamlPath, newText, 'utf8');
    return true;
  }
  return false;
}

export function patchIndexScreenshots(indexData, slug, urls) {
  for (const svc of indexData.services || []) {
    if (svc.name === slug || svc.dirname === slug) {
      svc.screenshots = urls;
      return true;
    }
  }
  return false;
}

export function applyCatalogScreenshots(slug, filenames) {
  const urls = screenshotUrlsForSlug(slug, filenames);
  const indexData = readJson(INDEX);
  let yamlPatched = 0;
  const svcDir = path.join(SERVICES, slug);
  for (const fname of ['app.yaml', 'app.ha.yaml']) {
    if (patchYamlScreenshots(path.join(svcDir, fname), urls)) yamlPatched += 1;
  }
  const indexPatched = patchIndexScreenshots(indexData, slug, urls);
  if (indexPatched) writeJson(INDEX, indexData);
  return { urls, yamlPatched, indexPatched };
}

export async function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

export async function runLogin(page, login, baseUrl) {
  if (!login) return;
  const loginUrl = login.url || `${baseUrl}${login.path || '/login'}`;
  await page.goto(loginUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });
  for (const step of login.steps || []) {
    if (step.sleep) await sleep(step.sleep);
    if (step.waitForSelector) {
      await page.waitForSelector(step.waitForSelector, { timeout: step.timeout || 30000 });
    }
    if (step.fill) {
      for (const [selector, value] of Object.entries(step.fill)) {
        await page.locator(selector).first().fill(String(value));
      }
    }
    if (step.click) {
      await page.locator(step.click).first().click();
    }
    if (step.press) {
      await page.locator(step.press.selector).first().press(step.press.key);
    }
    if (step.waitForURL) {
      await page.waitForURL(step.waitForURL, { timeout: step.timeout || 30000 });
    }
    if (step.waitForNavigation) {
      await page.waitForLoadState('networkidle', { timeout: step.timeout || 45000 }).catch(() => {});
    }
  }
  if (login.waitAfterMs) await sleep(login.waitAfterMs);
}

export async function capturePages(page, spec, baseUrl, outDir, slug) {
  const pages = spec.pages?.length ? spec.pages : [{ name: 'home', path: '/', waitMs: 3000 }];
  const results = [];

  for (const p of pages) {
    const target = p.url || `${baseUrl}${p.path || '/'}`;
    const filename = p.filename || `screenshot-${p.name}.png`;
    const outPath = path.join(outDir, filename);

    await page.goto(target, { waitUntil: 'domcontentloaded', timeout: 60000 });
    if (p.waitFor) {
      await page.waitForSelector(p.waitFor, { timeout: p.waitForTimeout || 30000 }).catch(() => {});
    }
    if (p.waitMs) await sleep(p.waitMs);
    else if (!p.waitFor) await sleep(spec.waitAfterNavigationMs ?? 2500);

    await page.screenshot({
      path: outPath,
      type: 'png',
      fullPage: Boolean(p.fullPage),
      animations: 'disabled',
    });

    const stat = fs.statSync(outPath);
    results.push({ name: p.name, filename, path: outPath, bytes: stat.size, url: target });
    console.log(`  ✓ ${slug}/${filename} (${(stat.size / 1024).toFixed(0)} KB)`);
  }
  return results;
}

export async function fetchQaUrls(apiBase, token) {
  const res = await fetch(`${apiBase.replace(/\/$/, '')}/api/platform/template-validation/status`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`QA status HTTP ${res.status}: ${await res.text()}`);
  const map = await res.json();
  const entries = [];
  for (const [name, row] of Object.entries(map)) {
    if (row?.status === 'pass' && row?.url) entries.push({ slug: name, url: row.url });
  }
  entries.sort((a, b) => a.slug.localeCompare(b.slug));
  return entries;
}
