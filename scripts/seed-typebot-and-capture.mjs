#!/usr/bin/env node
/**
 * Seed a Typebot deploy with upstream's own starter bots (packages/templates at the pinned tag),
 * answer two of them on the viewer like visitors, then capture 2x screenshots in light and dark.
 *
 *   TYPEBOT_URL=https://<builder> TYPEBOT_VIEWER_URL=https://<viewer> \
 *   TYPEBOT_TOKEN_FILE=<file with an API token> TYPEBOT_SESSION_FILE=<file with {name,value,domain}> \
 *   node seed-typebot-and-capture.mjs --out <dir> [--seed] [--capture]
 *
 * Typebot signs in by emailed code only, so the browser gets a session cookie from a file
 * (never printed). The API token is created in Settings > API tokens (or by the QA helper).
 */
import fs from 'node:fs'
import { chromium } from 'playwright'

const TAG = 'v3.19.1'
const STARTERS = ['lead-gen', 'nps', 'quiz', 'customer-support', 'product-recommendation']
const RUN = { 'lead-gen': 4, nps: 5 } // visitor sessions per published bot
const B = process.env.TYPEBOT_URL.replace(/\/$/, '')
const V = process.env.TYPEBOT_VIEWER_URL.replace(/\/$/, '')
const TOKEN = fs.readFileSync(process.env.TYPEBOT_TOKEN_FILE, 'utf8').trim()
const SESSION = JSON.parse(fs.readFileSync(process.env.TYPEBOT_SESSION_FILE, 'utf8'))
const args = process.argv.slice(2)
const OUT = args[args.indexOf('--out') + 1]
const H = { Authorization: `Bearer ${TOKEN}`, 'Content-Type': 'application/json' }

async function api(method, path, body, base = B, headers = H) {
  const r = await fetch(base + path, { method, headers, body: body ? JSON.stringify(body) : undefined })
  const t = await r.text()
  if (!r.ok) throw new Error(`${method} ${path} ${r.status} ${t.slice(0, 300)}`)
  return t ? JSON.parse(t) : {}
}

// Fictional visitors (no real people).
const VISITORS = [
  { name: 'Ava Lindqvist', email: 'ava@example.com', company: 'Northwind Studio', text: 'We need a quote form for our new site.' },
  { name: 'Mateo Ruiz', email: 'mateo@example.org', company: 'Bluefin Labs', text: 'Looking for onboarding help.' },
  { name: 'Priya Nair', email: 'priya@example.net', company: 'Cedar & Co', text: 'Can we embed this on Webflow?' },
  { name: 'Jonas Weber', email: 'jonas@example.com', company: 'Orbit Bikes', text: 'Pricing for a team of 12?' },
  { name: 'Lea Moreau', email: 'lea@example.org', company: 'Atelier Lune', text: 'Great experience so far.' },
]

function answer(input, v, i) {
  const t = input?.type || ''
  if (t.includes('choice')) {
    const items = input.items || []
    const it = items[(i + 1) % Math.max(items.length, 1)] || items[0]
    return { type: 'text', text: it?.content ?? 'Yes' }
  }
  if (t.includes('email')) return { type: 'text', text: v.email }
  if (t.includes('rating')) return { type: 'text', text: String([9, 10, 8, 7, 10][i % 5]) }
  if (t.includes('number')) return { type: 'text', text: String(3 + i) }
  if (t.includes('phone')) return { type: 'text', text: '+15555550' + (100 + i) }
  if (t.includes('url')) return { type: 'text', text: 'https://example.com' }
  if (t.includes('date')) return { type: 'text', text: '2026-12-0' + (1 + (i % 9)) }
  const ph = JSON.stringify(input?.options || '').toLowerCase()
  if (ph.includes('name')) return { type: 'text', text: v.name.split(' ')[0] }
  if (ph.includes('company')) return { type: 'text', text: v.company }
  return { type: 'text', text: v.text }
}

async function seed() {
  const { workspaces } = await api('GET', '/api/v1/workspaces')
  const ws = workspaces[0].id
  const { typebots: existing = [] } = await api('GET', `/api/v1/typebots?workspaceId=${ws}`)
  const ids = {}
  for (const slug of STARTERS) {
    const src = await (await fetch(`https://raw.githubusercontent.com/baptisteArno/typebot.io/${TAG}/packages/templates/src/typebots/${slug}.json`)).json()
    const name = src.name
    const have = existing.find((t) => t.name === name)
    if (have) { ids[slug] = have.id; continue }
    const typebot = { ...src }
    for (const k of ['id', 'workspaceId', 'createdAt', 'updatedAt']) delete typebot[k]
    for (const k of ['folderId', 'customDomain', 'whatsAppCredentialsId', 'resultsTablePreferences']) typebot[k] = null
    // starters embed GIFs of real people (film stills): leave image bubbles out of the demo data
    typebot.groups = typebot.groups.map((g) => ({ ...g, blocks: g.blocks.filter((b) => b.type !== 'image') }))
    typebot.publicId = `${slug}-${Math.random().toString(36).slice(2, 8)}`
    const r = await api('POST', '/api/v1/typebots/import', { workspaceId: ws, typebot })
    ids[slug] = r.typebot.id
    console.log('imported', slug)
  }
  for (const [slug, n] of Object.entries(RUN)) {
    const { typebot } = await api('GET', `/api/v1/typebots/${ids[slug]}`)
    if (!typebot.publicId) await api('PATCH', `/api/v1/typebots/${ids[slug]}`, { typebot: { publicId: `${slug}-${Math.random().toString(36).slice(2, 8)}` } })
    await api('POST', `/api/v1/typebots/${ids[slug]}/publish`, {})
    const pub = (await api('GET', `/api/v1/typebots/${ids[slug]}`)).typebot.publicId
    for (let i = 0; i < n; i++) {
      const v = VISITORS[i % VISITORS.length]
      let r = await api('POST', `/api/v1/typebots/${pub}/startChat`, {}, V, { 'Content-Type': 'application/json' })
      const sid = r.sessionId
      for (let step = 0; step < 14 && r.input; step++) {
        r = await api('POST', `/api/v1/sessions/${sid}/continueChat`, { message: answer(r.input, v, i) }, V, { 'Content-Type': 'application/json' })
      }
    }
    console.log('answered', slug, n)
  }
  fs.writeFileSync(`${OUT}/ids.json`, JSON.stringify(ids))
  return ids
}

async function capture(ids) {
  const host = new URL(B).host
  for (const theme of ['light', 'dark']) {
    // Typebot's own appearance setting (user preference), not inverted colours.
    await api('PATCH', '/api/v1/users/me', { updates: { preferredAppAppearance: theme } }).catch((e) => console.log('appearance:', e.message))
    const b = await chromium.launch()
    const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2, colorScheme: theme })
    await ctx.addCookies([{ name: SESSION.name, value: SESSION.value, domain: host, path: '/', secure: true, httpOnly: true, sameSite: 'Lax' }])
    const p = await ctx.newPage()
    const sfx = theme === 'dark' ? '-dark' : ''
    const shot = async (name, path, wait) => {
      await p.goto(B + path, { waitUntil: 'domcontentloaded', timeout: 90000 })
      if (wait) await p.locator(wait).first().waitFor({ timeout: 60000 })
      await p.waitForTimeout(2500)
      await p.screenshot({ path: `${OUT}/${name}${sfx}.png` })
      console.log('shot', name + sfx)
    }
    await shot('typebots', '/typebots', 'text=Lead Generation')
    await shot('editor', `/typebots/${ids['lead-gen']}/edit`, 'text=Welcome')
    await shot('results', `/typebots/${ids.nps}/results`, 'table')
    await b.close()
  }
}

fs.mkdirSync(OUT, { recursive: true })
let ids = fs.existsSync(`${OUT}/ids.json`) ? JSON.parse(fs.readFileSync(`${OUT}/ids.json`)) : null
if (args.includes('--seed') || !ids) ids = await seed()
if (args.includes('--capture')) await capture(ids)
