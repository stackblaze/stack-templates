// Seed a Stirling PDF deploy with three demo documents and capture the catalog stills (light and dark).
//   STIRLING_PDF_URL=https://<app> STIRLING_PDF_PASSWORD=<SECURITY_INITIALLOGIN_PASSWORD> \
//     node seed-stirling-pdf-and-capture.mjs <outdir>
// The documents (a fictional design studio's report, invoice and agreement) are rendered to PDF by the
// app's own HTML to PDF tool (seed-stirling-pdf/*.html, inline styles: the app's HTML sanitizer drops
// <style>). Stills: the three files in the workbench, Merge result in the viewer, the merged PDF with a
// CONFIDENTIAL text watermark (zoomed in). Dark comes from the app's own preference (stirlingpdf_preferences.theme).
// capture-lib has no file-upload step, hence this script (like seed-excalidraw-and-capture.mjs).
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { chromium } from 'playwright'

const URL_ = (process.env.STIRLING_PDF_URL || '').replace(/\/$/, '')
const PW = process.env.STIRLING_PDF_PASSWORD
const out = process.argv[2] || '.'
if (!URL_ || !PW) throw new Error('set STIRLING_PDF_URL and STIRLING_PDF_PASSWORD')
const SRC = new URL('./seed-stirling-pdf/', import.meta.url).pathname
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'stirling-seed-'))

const login = await (await fetch(URL_ + '/api/v1/auth/login', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ username: 'admin', password: PW }) })).json()
const H = { authorization: 'Bearer ' + (login?.session?.access_token || login.access_token) }
const DOCS = { 'q3-report': 'Q3 Report 2026', invoice: 'Invoice INV-2041', agreement: 'Design Services Agreement' }
for (const [f, n] of Object.entries(DOCS)) {
  const fd = new FormData()
  fd.append('fileInput', new Blob([fs.readFileSync(SRC + f + '.html')], { type: 'text/html' }), f + '.html')
  const r = await fetch(URL_ + '/api/v1/convert/html/pdf', { method: 'POST', headers: H, body: fd })
  if (r.status !== 200) throw new Error(`html->pdf ${f}: ${r.status}`)
  fs.writeFileSync(`${tmp}/${n}.pdf`, Buffer.from(await r.arrayBuffer()))
}

const b = await chromium.launch()
for (const theme of ['light', 'dark']) {
  const sfx = theme === 'dark' ? '-dark' : ''
  const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2, colorScheme: theme })
  await ctx.addInitScript((t) => { try { localStorage.setItem('stirlingpdf_preferences', JSON.stringify({ ...JSON.parse(localStorage.getItem('stirlingpdf_preferences') || '{}'), theme: t })) } catch {} }, theme)
  const p = await ctx.newPage()
  await p.goto(URL_ + '/login', { waitUntil: 'networkidle' })
  await p.fill('#email', 'admin'); await p.fill('#password', PW)
  await p.click('button:has-text("Login")'); await p.waitForURL(/editor/); await p.waitForTimeout(1500)
  await p.locator('input[type=file]').first().setInputFiles(Object.values(DOCS).map((n) => `${tmp}/${n}.pdf`))
  await p.getByText('Design Services Agreement.pdf').last().waitFor({ timeout: 30000 }); await p.waitForTimeout(4000)
  await p.mouse.move(1000, 900)
  await p.screenshot({ path: `${out}/files${sfx}.png` })
  await p.getByText('Merge', { exact: true }).first().click(); await p.waitForTimeout(1200)
  await p.getByRole('button', { name: /Merge \(3 files\)/ }).click()
  await p.getByRole('button', { name: 'Undo' }).waitFor({ timeout: 60000 }); await p.waitForTimeout(2500)
  await p.mouse.move(1000, 1000)
  await p.screenshot({ path: `${out}/merge${sfx}.png` })
  await p.getByRole('button', { name: 'Back to all tools' }).click(); await p.waitForTimeout(1000)
  await p.getByText('Add Watermark', { exact: true }).first().click(); await p.mouse.move(1000, 600); await p.waitForTimeout(1200)
  await p.locator('label').filter({ hasText: /^Text$/ }).first().click(); await p.waitForTimeout(600)
  await p.getByPlaceholder('Enter watermark text').fill('CONFIDENTIAL')
  await p.getByRole('button', { name: /^Add Watermark/ }).click()
  await p.getByText('Review', { exact: true }).waitFor({ timeout: 60000 }); await p.waitForTimeout(2000)
  for (let i = 0; i < 3; i++) { await p.getByRole('button', { name: 'Zoom In' }).click(); await p.waitForTimeout(400) }
  await p.waitForTimeout(2000)
  await p.mouse.move(1000, 1000)
  await p.screenshot({ path: `${out}/watermark${sfx}.png` })
  await ctx.close()
}
await b.close()
fs.rmSync(tmp, { recursive: true, force: true })
console.log('stills in', out)
