// Capture Plane screenshots (1920x1080 @2x) in Plane's own light and dark theme.
// usage: node capture-plane.mjs <vars.json> <base url> <outdir> [light|dark ...]
// Run scripts/seed-plane-demo.py first. Signs in through Plane's API (no password typed on screen); never prints secrets.
import { chromium } from 'playwright'
import fs from 'node:fs'

const [varsPath, base, out, ...themes] = process.argv.slice(2)
const v = Object.fromEntries(JSON.parse(fs.readFileSync(varsPath, 'utf8')).vars.map((x) => [x.name, x.value]))
fs.mkdirSync(out, { recursive: true })

const b = await chromium.launch()
for (const theme of themes.length ? themes : ['light', 'dark']) {
  const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2, colorScheme: theme })
  const r = ctx.request
  await r.get(`${base}/auth/get-csrf-token/`)
  const csrf = (await ctx.cookies()).find((c) => c.name === 'csrftoken')?.value
  const H = { 'X-CSRFToken': csrf, Referer: base + '/', Origin: base }
  await r.post(`${base}/auth/sign-in/`, { form: { csrfmiddlewaretoken: csrf, email: v.ADMIN_EMAIL, password: v.ADMIN_PASSWORD }, headers: H, maxRedirects: 0 })
  const api = async (m, p, data) => { const res = await r.fetch(base + p, { method: m, data, headers: H }); if (!res.ok()) throw new Error(`${m} ${p} ${res.status()}`); return res.status() === 204 ? null : res.json() }
  await api('PATCH', '/api/users/me/profile/', { theme: { theme } })
  const projects = await api('GET', '/api/workspaces/plane/projects/')
  const web = (Array.isArray(projects) ? projects : projects.results).find((p) => p.identifier === 'WEB')
  const P = `/api/workspaces/plane/projects/${web.id}`
  const cycles = await api('GET', `${P}/cycles/`)
  const sprint = cycles.find((c) => c.name === 'Sprint 14')
  const setLayout = (layout, extra = {}) => api('PATCH', `${P}/user-properties/`, { display_filters: { layout, group_by: 'state', order_by: 'sort_order', ...extra } })
  const page = await ctx.newPage()
  const shot = async (name, path, ready, before) => {
    if (before) await before()
    await page.goto(base + path, { waitUntil: 'domcontentloaded' })
    try { await page.locator(ready).first().waitFor({ timeout: 30000 }) } catch { console.log('NOT READY', name); await page.screenshot({ path: `${out}/fail-${name}-${theme}.png` }); return }
    await page.waitForLoadState('networkidle', { timeout: 20000 }).catch(() => {})
    await page.waitForTimeout(2500)
    await page.mouse.move(1910, 1070)
    await page.screenshot({ path: `${out}/${name}${theme === 'dark' ? '-dark' : ''}.png` })
    console.log('shot', name, theme)
  }
  const only = (process.env.ONLY || '').split(',').filter(Boolean)
  const shot0 = shot
  const shotF = (n, ...a) => (only.length && !only.includes(n) ? null : shot0(n, ...a))
  await shotF('board', `/plane/projects/${web.id}/issues/`, 'text=Migrate blog posts', () => setLayout('kanban'))
  await shotF('cycle', `/plane/projects/${web.id}/cycles/${sprint.id}/`, 'text=Accessibility pass on forms', () => setLayout('list'))
  await shotF('cycles', `/plane/projects/${web.id}/cycles/`, 'text=Sprint 14')
  await shotF('item', `/plane/browse/WEB-4/`, 'text=Migrate blog posts to the new CMS')
  await shotF('modules', `/plane/projects/${web.id}/modules/`, 'text=Content migration')
  const pages = await api('GET', `${P}/pages/`)
  const plan = pages.find((x) => x.name === 'Launch plan')
  await shotF('page', `/plane/projects/${web.id}/pages/${plan.id}/`, 'text=Relaunch the marketing site')
  await shotF('home', `/plane/`, 'text=Website Relaunch')
  await setLayout('kanban')
  await ctx.close()
}
await b.close()
