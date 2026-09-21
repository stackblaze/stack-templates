#!/usr/bin/env node
/** Record a ~12s walkthrough MP4 from a live listmonk URL (after admin exists). */
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const base = process.argv[2]?.replace(/\/+$/, '');
const outFile = process.argv[3] || path.join('..', 'services', 'listmonk', 'demo.mp4');
if (!base) {
  console.error('Usage: node record-listmonk-demo.mjs <https://host:9000> [out.mp4]');
  process.exit(1);
}

const scenes = [
  { path: '/admin', dwell: 2800 },
  { path: '/admin/lists', dwell: 2800 },
  { path: '/admin/subscribers', dwell: 2800 },
  { path: '/admin/campaigns', dwell: 2800 },
  { path: '/archive', dwell: 2200 },
];

const tmpDir = fs.mkdtempSync(path.join(fs.realpathSync('/tmp'), 'listmonk-demo-'));
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1920, height: 1080 },
  recordVideo: { dir: tmpDir, size: { width: 1920, height: 1080 } },
  ignoreHTTPSErrors: true,
});
const page = await context.newPage();

async function loginIfNeeded() {
  await page.goto(`${base}/admin`, { waitUntil: 'domcontentloaded', timeout: 120_000 });
  if (await page.locator('#email').isVisible({ timeout: 8_000 }).catch(() => false)) {
    await page.locator('#email').fill('newsletter@stackblaze.local');
    await page.locator('#username').fill('admin');
    await page.locator('#password').fill('Changeme1!');
    await page.locator('#password2').fill('Changeme1!');
    await page.locator('section.login form.form button[type="submit"]').click();
    await page.waitForTimeout(3500);
  } else if (await page.locator('#username').isVisible({ timeout: 3_000 }).catch(() => false)) {
    await page.goto(`${base}/admin/login`, { waitUntil: 'domcontentloaded' });
    await page.locator('#username').fill('admin');
    await page.locator('#password').fill('Changeme1!');
    await page.locator('form[action="/admin/login"] button[type="submit"]').click();
    await page.waitForTimeout(2500);
  }
}

await loginIfNeeded();
for (const scene of scenes) {
  await page.goto(`${base}${scene.path}`, { waitUntil: 'domcontentloaded', timeout: 60_000 });
  await page.waitForTimeout(scene.dwell);
}

const video = page.video();
await context.close();
await browser.close();
if (!video) throw new Error('Playwright did not produce a video');
const webm = await video.path();
fs.mkdirSync(path.dirname(path.resolve(outFile)), { recursive: true });
fs.copyFileSync(webm, outFile.replace(/\.mp4$/, '.webm'));
console.log(`Wrote ${outFile.replace(/\.mp4$/, '.webm')} (transcode to mp4 with ffmpeg if needed)`);
