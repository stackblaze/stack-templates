#!/usr/bin/env node
// Seed an Instatic deploy with a small invented coffee-roaster site, for
// screenshots and the website demo. Everything is fictional; the images are
// abstract illustrations rendered here (no people, no real brands).
//
// usage: INSTATIC_URL=https://… INSTATIC_EMAIL=… INSTATIC_PASSWORD=… \
//        node seed-instatic-demo.mjs
//
// 1. renders 4 illustrations and uploads them to the Media library (API),
// 2. creates and publishes 3 blog posts with featured images (API),
// 3. imports the home page through the editor's own Import HTML dialog
//    (Playwright), so the page tree is built by Instatic itself,
// 4. publishes the site (API, after step-up).
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const { chromium } = require('playwright')

const base = (process.env.INSTATIC_URL ?? '').replace(/\/$/, '')
const email = process.env.INSTATIC_EMAIL
const password = process.env.INSTATIC_PASSWORD
if (!base || !email || !password) {
  console.error('set INSTATIC_URL, INSTATIC_EMAIL and INSTATIC_PASSWORD')
  process.exit(2)
}

let cookie = ''
async function api(path, opts = {}) {
  const headers = { origin: base, ...(cookie ? { cookie } : {}), ...(opts.headers ?? {}) }
  if (typeof opts.body === 'string') headers['content-type'] = 'application/json'
  const res = await fetch(base + path, { ...opts, headers })
  for (const c of res.headers.getSetCookie?.() ?? []) if (c.startsWith('instatic_admin_session=')) cookie = c.split(';')[0]
  const text = await res.text()
  let json = null
  try { json = JSON.parse(text) } catch {}
  if (res.status >= 400) throw new Error(`${opts.method ?? 'GET'} ${path} -> ${res.status} ${text.slice(0, 200)}`)
  return json
}

// ---------------------------------------------------------------- images
const ART = {
  'hero-roastery': `
    <div style="position:absolute;inset:0;background:linear-gradient(135deg,#f3e3cf 0%,#e7c9a6 45%,#b9805a 100%)"></div>
    <div style="position:absolute;left:8%;bottom:-18%;width:62%;height:78%;border-radius:50%;background:#7a4a2e;opacity:.9"></div>
    <div style="position:absolute;left:22%;bottom:12%;width:34%;height:44%;border-radius:0 0 46% 46%;background:#fbf6ef"></div>
    <div style="position:absolute;left:52%;bottom:26%;width:10%;height:18%;border:22px solid #fbf6ef;border-left:none;border-radius:0 60% 60% 0"></div>
    <div style="position:absolute;left:23%;bottom:51%;width:32%;height:6%;border-radius:50%;background:#5a3420"></div>
    <div style="position:absolute;left:30%;top:6%;width:3%;height:26%;border-radius:40px;background:#fbf6ef;opacity:.55;transform:rotate(8deg)"></div>
    <div style="position:absolute;left:38%;top:2%;width:3%;height:30%;border-radius:40px;background:#fbf6ef;opacity:.45;transform:rotate(-6deg)"></div>
    <div style="position:absolute;right:7%;top:12%;width:22%;height:34%;border-radius:50%;background:#f7d9a8;opacity:.8"></div>`,
  'beans-origin': `
    <div style="position:absolute;inset:0;background:#2f4a3a"></div>
    ${Array.from({ length: 34 }, (_, i) => {
      const x = (i * 137) % 100, y = (i * 61) % 100, r = (i * 47) % 180
      return `<div style="position:absolute;left:${x}%;top:${y}%;width:9%;height:13%;border-radius:50%;background:${i % 3 ? '#8a5634' : '#a86b3f'};transform:rotate(${r}deg)"><div style="position:absolute;left:47%;top:10%;width:6%;height:80%;border-radius:50%;background:#4e2c18"></div></div>`
    }).join('')}`,
  'pour-over': `
    <div style="position:absolute;inset:0;background:linear-gradient(180deg,#e9eef2,#cfd9e0)"></div>
    <div style="position:absolute;left:34%;top:14%;width:32%;height:0;border-left:13vw solid transparent;border-right:13vw solid transparent;border-top:30vh solid #f6f1ea"></div>
    <div style="position:absolute;left:36%;top:52%;width:28%;height:34%;border-radius:12% 12% 40% 40%;background:rgba(255,255,255,.65);border:6px solid #9fb2bf"></div>
    <div style="position:absolute;left:37.5%;top:66%;width:25%;height:18%;border-radius:0 0 40% 40%;background:#6b3f24"></div>
    <div style="position:absolute;left:49%;top:44%;width:2%;height:12%;border-radius:20px;background:#6b3f24"></div>
    <div style="position:absolute;left:12%;bottom:8%;width:76%;height:3%;border-radius:20px;background:#9fb2bf"></div>`,
  'shop-front': `
    <div style="position:absolute;inset:0;background:#f4efe6"></div>
    <div style="position:absolute;left:14%;top:22%;width:72%;height:70%;background:#c4643b"></div>
    <div style="position:absolute;left:10%;top:14%;width:80%;height:12%;background:#2f4a3a"></div>
    ${[0, 1, 2, 3, 4, 5, 6, 7].map((i) => `<div style="position:absolute;left:${10 + i * 10}%;top:26%;width:10%;height:8%;background:${i % 2 ? '#f4efe6' : '#2f4a3a'};border-radius:0 0 50% 50%"></div>`).join('')}
    <div style="position:absolute;left:22%;top:44%;width:30%;height:34%;background:#fbe9c9;border:10px solid #7a3b20"></div>
    <div style="position:absolute;left:60%;top:44%;width:16%;height:48%;background:#7a3b20"></div>
    <div style="position:absolute;left:72%;top:66%;width:2%;height:4%;border-radius:50%;background:#f4c76a"></div>`,
}

async function renderArt(browser) {
  const out = {}
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } })
  for (const [name, html] of Object.entries(ART)) {
    await page.setContent(`<html><body style="margin:0"><div style="position:relative;width:1600px;height:1000px;overflow:hidden">${html}</div></body></html>`)
    out[name] = await page.screenshot({ type: 'png' })
  }
  await page.close()
  return out
}

// ---------------------------------------------------------------- content
const POSTS = [
  {
    title: 'Meet our new Huila single origin',
    slug: 'huila-single-origin',
    image: 'beans-origin',
    body: `This month's single origin comes from a cooperative of small farms in Huila. We roast it light to keep the red apple and panela notes.\n\n## Brewing it\n\n- 18 g coffee, 300 g water at 94 °C\n- Bloom for 40 seconds, then pour in three stages\n- Aim for a total time around 3:15\n\nBags are on the shelf at the roastery from Friday.`,
  },
  {
    title: 'A slower pour over, step by step',
    slug: 'slower-pour-over',
    image: 'pour-over',
    body: `Pour over rewards patience. Rinse the filter, warm the carafe, and grind a little coarser than you think.\n\n1. Bloom with twice the coffee's weight in water.\n2. Pour in slow circles, keeping the bed flat.\n3. Swirl once at the end and let it drain.\n\nIf it tastes sour, grind finer. If it tastes bitter, go coarser.`,
  },
  {
    title: 'Weekend hours and the new tasting bar',
    slug: 'weekend-hours',
    image: 'shop-front',
    body: `We are opening the tasting bar on Saturdays from 9 to 2. Drop in for a free flight of three coffees and a chat about what you like.\n\nWeekday hours stay the same: 7 to 4, Monday to Friday.`,
  },
]

function homeHtml(img) {
  return `<style>
.el-page{font-family:Inter,system-ui,sans-serif;color:#2b211b;background:#fbf7f1}
.el-nav{display:flex;align-items:center;justify-content:space-between;padding:22px 56px;border-bottom:1px solid #eadfd2}
.el-logo{font-weight:800;font-size:22px;letter-spacing:-0.02em;color:#2b211b}
.el-links{display:flex;gap:28px;font-size:15px;color:#6b5a4c}
.el-hero{display:grid;grid-template-columns:1.1fr 1fr;gap:56px;align-items:center;padding:72px 56px}
.el-kicker{font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:#b0623a;font-weight:700}
.el-title{font-size:60px;line-height:1.02;letter-spacing:-0.03em;margin:14px 0 18px;color:#2b211b}
.el-lead{font-size:19px;line-height:1.6;color:#6b5a4c;max-width:520px}
.el-cta{display:inline-block;margin-top:28px;padding:14px 26px;border-radius:999px;background:#2f4a3a;color:#fbf7f1;font-weight:600;text-decoration:none}
.el-hero-img{width:100%;border-radius:28px;aspect-ratio:8/5;object-fit:cover}
.el-cards{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;padding:8px 56px 72px}
.el-card{background:#fff;border:1px solid #eadfd2;border-radius:22px;padding:28px}
.el-card h3{font-size:20px;margin:0 0 8px;color:#2b211b}
.el-card p{font-size:15px;line-height:1.6;color:#6b5a4c;margin:0}
.el-band{display:grid;grid-template-columns:1fr 1fr;gap:48px;align-items:center;padding:64px 56px;background:#2f4a3a;color:#f4efe6}
.el-band h2{font-size:40px;letter-spacing:-0.02em;margin:0 0 14px;color:#f4efe6}
.el-band p{font-size:17px;line-height:1.6;color:#d6dfd8}
.el-band img{width:100%;border-radius:22px}
.el-foot{padding:32px 56px;font-size:14px;color:#8a7a6c}
</style>
<div class="el-page">
  <nav class="el-nav"><span class="el-logo">Ember Row Coffee</span><div class="el-links"><a href="#beans">Beans</a><a href="#visit">Visit</a></div></nav>
  <section class="el-hero">
    <div>
      <p class="el-kicker">Small batch roastery</p>
      <h1 class="el-title">Coffee roasted on Tuesday, in your cup by Friday.</h1>
      <p class="el-lead">We roast in small batches, ship within three days and write down everything we learn along the way.</p>
      <a class="el-cta" href="#beans">See this week's beans</a>
    </div>
    <img class="el-hero-img" src="${img['hero-roastery']}" alt="Illustration of a coffee cup in warm light">
  </section>
  <section class="el-cards" id="beans">
    <div class="el-card"><h3>Single origins</h3><p>Rotating lots from small farms, roasted light to show where they come from.</p></div>
    <div class="el-card"><h3>House espresso</h3><p>A chocolatey blend that works in a machine at home or a moka pot.</p></div>
    <div class="el-card"><h3>Brew classes</h3><p>Pour over and espresso basics on Saturday mornings at the tasting bar.</p></div>
  </section>
  <section class="el-band" id="visit">
    <div><h2>Visit the roastery</h2><p>Open 7 to 4 on weekdays, with a tasting bar on Saturdays from 9 to 2. Bring your own cup and the first refill is on us.</p></div>
    <img src="${img['shop-front']}" alt="Illustration of the roastery shop front">
  </section>
  <footer class="el-foot">Ember Row Coffee, 12 Ember Row. Built with Instatic.</footer>
</div>`
}

// ---------------------------------------------------------------- run
const browser = await chromium.launch()
try {
  await api('/admin/api/cms/login', { method: 'POST', body: JSON.stringify({ email, password }) })

  // 1. media
  const art = await renderArt(browser)
  const media = {}
  const existing = (await api('/admin/api/cms/media')).assets ?? []
  for (const [name, bytes] of Object.entries(art)) {
    const found = existing.find((a) => a.filename?.endsWith(`${name}.png`) && !a.deletedAt)
    if (found) { media[name] = found; continue }
    const fd = new FormData()
    fd.append('file', new Blob([bytes], { type: 'image/png' }), `${name}.png`)
    const up = await api('/admin/api/cms/media', { method: 'POST', body: fd })
    media[name] = up.asset ?? up
    console.log('uploaded', name)
  }
  const img = Object.fromEntries(Object.entries(media).map(([k, v]) => [k, v.publicPath]))

  // 2. posts
  const rows = (await api('/admin/api/cms/data/tables/posts/rows')).rows ?? []
  for (const p of POSTS) {
    if (rows.some((r) => r.slug === p.slug)) continue
    const created = await api('/admin/api/cms/data/tables/posts/rows', {
      method: 'POST',
      body: JSON.stringify({ cells: { title: p.title, slug: p.slug, body: p.body, featuredMedia: media[p.image].id } }),
    })
    const id = created.row?.id ?? created.id
    await api(`/admin/api/cms/data/rows/${id}/publish`, { method: 'POST', body: '{}' })
    console.log('post', p.slug)
  }

  // 3. home page through the editor's Import HTML dialog
  const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, permissions: ['clipboard-read', 'clipboard-write'] })
  const [name, value] = cookie.split('=')
  await ctx.addCookies([{ name, value, url: base }])
  const page = await ctx.newPage()
  await page.goto(base + '/admin/site', { waitUntil: 'domcontentloaded' })
  await page.getByRole('button', { name: 'Publish site' }).waitFor({ timeout: 60000 })
  await page.waitForTimeout(3000)
  const layers = await page.locator('[role=treeitem], [data-node-id]').count()
  if (layers > 3) {
    console.log('home page already has content, skipping import')
  } else {
    await page.keyboard.press('Control+k')
    await page.waitForTimeout(500)
    await page.keyboard.type('Import HTML')
    await page.waitForTimeout(500)
    await page.keyboard.press('Enter')
    const editor = page.locator('.cm-content').last()
    await editor.waitFor({ timeout: 15000 })
    await page.evaluate((t) => navigator.clipboard.writeText(t), homeHtml(img))
    await editor.click()
    await page.keyboard.press('Control+v')
    await page.waitForTimeout(1500)
    await page.getByRole('button', { name: 'Insert', exact: true }).click()
    await page.waitForTimeout(2500)
    // autosave: wait until the draft is synced
    await page.getByText('Draft synced').waitFor({ timeout: 30000 }).catch(() => {})
    await page.waitForTimeout(2000)
    console.log('home page imported')
  }
  await ctx.close()

  // 4. publish
  await api('/admin/api/cms/auth/step-up', { method: 'POST', body: JSON.stringify({ password }) })
  await api('/admin/api/cms/publish', { method: 'POST', body: '{}' })
  console.log('published', JSON.stringify(await api('/admin/api/cms/publish/status')))
} finally {
  await browser.close()
}
