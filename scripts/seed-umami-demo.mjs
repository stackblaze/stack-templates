#!/usr/bin/env node
// Live demo traffic for an Umami deploy: real browsers load a test site that
// embeds the deploy's own tracker (script.js), click around and fire custom
// events, so pageviews, visitors and the Realtime view fill through the real
// collection path (/api/send), not through the database.
//
// History first (optional, recommended for screenshots): upstream's own sample
// data generator at the pinned tag (scripts/seed-data.ts, "Demo Blog" and
// "Demo SaaS", 30 days), run against the deploy's database through a
// `kubectl port-forward` of the CNPG `-rw` service:
//   git clone --depth 1 --branch v3.5.0 https://github.com/umami-software/umami
//   (copy scripts/seed*, prisma/schema.prisma, prisma.config.ts into an empty dir;
//    npm i prisma@7.10.0 @prisma/client@7.10.0 @prisma/adapter-pg@7.10.0 tsx dotenv uuid;
//    npx prisma generate; DATABASE_URL=... npx tsx scripts/seed-data.ts --days 30)
//
// Usage (from scripts/, Playwright installed):
//   UMAMI_URL=https://umami-xxxx... UMAMI_PASSWORD=<ADMIN_PASSWORD> \
//   VISITORS=30 node seed-umami-demo.mjs
// The test site is served by Playwright itself (page.route) at SITE_HOST, so
// nothing is deployed; the tracker reports that hostname.
import { chromium } from 'playwright';

const URL_ = (process.env.UMAMI_URL || '').replace(/\/$/, '');
const PASSWORD = process.env.UMAMI_PASSWORD;
const SITE_NAME = process.env.SITE_NAME || 'Demo SaaS';
const SITE_HOST = process.env.SITE_HOST || 'app.example.com';
const VISITORS = Number(process.env.VISITORS || 30);
const PARALLEL = Number(process.env.PARALLEL || 5);
if (!URL_ || !PASSWORD) {
  console.error('Set UMAMI_URL and UMAMI_PASSWORD');
  process.exit(1);
}

async function api(token, method, path, body) {
  const r = await fetch(`${URL_}${path}`, {
    method,
    headers: { 'content-type': 'application/json', ...(token && { authorization: `Bearer ${token}` }) },
    body: body && JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${method} ${path} ${r.status}`);
  return r.json();
}

const { token } = await api(null, 'POST', '/api/auth/login', { username: 'admin', password: PASSWORD });
const list = await api(token, 'GET', '/api/websites?pageSize=100');
let site = (list.data || list).find(w => w.name === SITE_NAME);
if (!site) site = await api(token, 'POST', '/api/websites', { name: SITE_NAME, domain: SITE_HOST });
console.log(`website ${site.name} (${site.domain})`);

const PAGES = {
  '/': 'Ship faster with fewer meetings',
  '/features': 'Features',
  '/pricing': 'Pricing',
  '/docs': 'Documentation',
  '/docs/getting-started': 'Getting started',
  '/blog/release-notes': 'Release notes',
  '/signup': 'Create your account',
};
const html = path => `<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>${PAGES[path] || 'Page'} | Demo SaaS</title>
<script defer src="${URL_}/script.js" data-website-id="${site.id}"></script>
<style>body{font:16px system-ui;margin:0}nav{display:flex;gap:16px;padding:16px;background:#111;color:#fff}
nav a{color:#fff}main{padding:40px}button{font-size:18px;padding:12px 20px}</style></head><body>
<nav>${Object.keys(PAGES).map(p => `<a href="${p}">${PAGES[p]}</a>`).join('')}</nav>
<main><h1>${PAGES[path] || 'Page'}</h1>
<button data-umami-event="cta_click" data-umami-event-page="${path}">Start free trial</button>
${path === '/signup' ? '<button id="su" data-umami-event="signup_completed">Sign up</button>' : ''}
</main></body></html>`;

const DEVICES = [
  { ua: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36', vp: [1920, 1080] },
  { ua: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15', vp: [1512, 982] },
  { ua: 'Mozilla/5.0 (X11; Linux x86_64; rv:144.0) Gecko/20100101 Firefox/144.0', vp: [1366, 768] },
  { ua: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0', vp: [1536, 864] },
  { ua: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1', vp: [390, 844], mobile: true },
  { ua: 'Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Mobile Safari/537.36', vp: [412, 915], mobile: true },
  { ua: 'Mozilla/5.0 (iPad; CPU OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1', vp: [820, 1180], mobile: true },
];
const LOCALES = ['en-US', 'en-US', 'en-GB', 'de-DE', 'fr-FR', 'es-ES', 'pt-BR', 'ja-JP'];
const REFERRERS = ['https://www.google.com/', 'https://www.google.com/', 'https://duckduckgo.com/', 'https://github.com/',
  'https://news.ycombinator.com/', 'https://www.reddit.com/', '', ''];
const ENTRY = ['/', '/', '/', '/pricing', '/features', '/docs/getting-started', '/blog/release-notes',
  '/?utm_source=newsletter&utm_medium=email&utm_campaign=november'];
const pick = a => a[Math.floor(Math.random() * a.length)];
const sleep = ms => new Promise(r => setTimeout(r, ms));

const browser = await chromium.launch();
let done = 0;
async function visitor(i) {
  const d = pick(DEVICES);
  const ctx = await browser.newContext({ userAgent: d.ua, viewport: { width: d.vp[0], height: d.vp[1] },
    isMobile: !!d.mobile, hasTouch: !!d.mobile, locale: pick(LOCALES) });
  await ctx.route(`https://${SITE_HOST}/**`, route => {
    const p = new URL(route.request().url()).pathname;
    route.fulfill({ status: 200, contentType: 'text/html', body: html(p) });
  });
  const page = await ctx.newPage();
  const sent = [];
  page.on('response', r => { if (r.url().startsWith(`${URL_}/api/send`)) sent.push(r.status()); });
  try {
    await page.goto(`https://${SITE_HOST}${pick(ENTRY)}`, { referer: pick(REFERRERS) || undefined });
    await sleep(1500 + Math.random() * 3000);
    const hops = Math.floor(Math.random() * 4);
    for (let h = 0; h < hops; h++) {
      const target = pick(Object.keys(PAGES));
      await page.click(`nav a[href="${target}"]`);
      await page.waitForLoadState('load');
      await sleep(1500 + Math.random() * 4000);
      if (Math.random() < 0.3) { await page.click('button[data-umami-event="cta_click"]'); await sleep(800); }
    }
    if (Math.random() < 0.25) {
      await page.click('nav a[href="/signup"]');
      await page.waitForLoadState('load');
      await sleep(1200);
      await page.click('#su');
      await sleep(1000);
    }
  } finally {
    await sleep(800);
    await ctx.close();
    done++;
    console.log(`visitor ${i + 1}/${VISITORS}: ${sent.length} hits (${[...new Set(sent)].join(',') || 'none'})`);
  }
}

let next = 0;
await Promise.all(Array.from({ length: PARALLEL }, async () => {
  while (next < VISITORS) {
    const i = next++;
    await visitor(i).catch(e => console.log(`visitor ${i + 1} error: ${e.message}`));
    await sleep(Math.random() * 4000);
  }
}));
await browser.close();
console.log(`done: ${done} visitors`);
