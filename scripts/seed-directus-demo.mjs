#!/usr/bin/env node
// Seed a Directus deploy with a small, invented magazine ("Trailhead Journal")
// for screenshots and the website demo: authors, categories and posts with
// generated cover images, a tabular preset, and public read access so the
// generated REST API (/items/posts) answers without a token.
//
// Usage (from scripts/):
//   DIRECTUS_URL=https://… DIRECTUS_EMAIL=admin@example.com DIRECTUS_PASSWORD=… node seed-directus-demo.mjs
//
// Idempotent enough for re-runs on a fresh deploy: existing collections are
// dropped and recreated.
import { chromium } from 'playwright'

const base = process.env.DIRECTUS_URL?.replace(/\/$/, '')
const email = process.env.DIRECTUS_EMAIL
const password = process.env.DIRECTUS_PASSWORD
if (!base || !email || !password) {
  console.error('DIRECTUS_URL, DIRECTUS_EMAIL and DIRECTUS_PASSWORD are required')
  process.exit(2)
}

let token
async function api(path, { method = 'GET', body, raw } = {}) {
  const headers = { authorization: `Bearer ${token}` }
  if (body && !(body instanceof FormData)) headers['content-type'] = 'application/json'
  const r = await fetch(base + path, { method, headers, body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined })
  const text = await r.text()
  if (!r.ok && !raw) throw new Error(`${method} ${path} -> ${r.status} ${text.slice(0, 300)}`)
  return text ? JSON.parse(text) : null
}

const login = await fetch(base + '/auth/login', {
  method: 'POST',
  headers: { 'content-type': 'application/json' },
  body: JSON.stringify({ email, password }),
})
if (!login.ok) throw new Error(`login failed: ${login.status}`)
token = (await login.json()).data.access_token

// Admin profile: a real-looking name, theme follows the browser
const me = (await api('/users/me')).data
await api(`/users/${me.id}`, { method: 'PATCH', body: { first_name: 'Alex', last_name: 'Morgan', appearance: null } })
await api('/settings', { method: 'PATCH', body: { project_name: 'Trailhead Journal', project_color: '#6644FF' } })

for (const c of ['posts', 'authors', 'categories', 'articles']) await api(`/collections/${c}`, { method: 'DELETE', raw: true })

const pk = { field: 'id', type: 'integer', meta: { hidden: true, readonly: true, interface: 'input' }, schema: { is_primary_key: true, has_auto_increment: true } }

await api('/collections', {
  method: 'POST',
  body: {
    collection: 'categories',
    meta: { icon: 'label', display_template: '{{name}}', sort: 3 },
    schema: {},
    fields: [
      pk,
      { field: 'name', type: 'string', meta: { interface: 'input', required: true, width: 'half' }, schema: {} },
      { field: 'color', type: 'string', meta: { interface: 'select-color', width: 'half', display: 'color' }, schema: {} },
    ],
  },
})
await api('/collections', {
  method: 'POST',
  body: {
    collection: 'authors',
    meta: { icon: 'person', display_template: '{{name}}', sort: 2 },
    schema: {},
    fields: [
      pk,
      { field: 'name', type: 'string', meta: { interface: 'input', required: true, width: 'half' }, schema: {} },
      { field: 'role', type: 'string', meta: { interface: 'input', width: 'half' }, schema: {} },
      { field: 'bio', type: 'text', meta: { interface: 'input-multiline' }, schema: {} },
    ],
  },
})
await api('/collections', {
  method: 'POST',
  body: {
    collection: 'posts',
    meta: { icon: 'article', display_template: '{{title}}', note: 'Stories published on the website', sort: 1, archive_field: 'status', archive_value: 'archived', unarchive_value: 'draft' },
    schema: {},
    fields: [
      pk,
      {
        field: 'status', type: 'string',
        meta: {
          interface: 'select-dropdown', width: 'half', display: 'labels',
          options: { choices: [{ text: 'Published', value: 'published' }, { text: 'Draft', value: 'draft' }, { text: 'Archived', value: 'archived' }] },
          display_options: { showAsDot: true, choices: [{ value: 'published', foreground: '#FFFFFF', background: '#2ECDA7' }, { value: 'draft', foreground: '#18222F', background: '#D3DAE4' }, { value: 'archived', foreground: '#FFFFFF', background: '#A2B5CD' }] },
        },
        schema: { default_value: 'draft' },
      },
      { field: 'published_on', type: 'date', meta: { interface: 'datetime', width: 'half', display: 'datetime', display_options: { format: 'short' } }, schema: {} },
      { field: 'title', type: 'string', meta: { interface: 'input', required: true }, schema: {} },
      { field: 'slug', type: 'string', meta: { interface: 'input', width: 'half', options: { slug: true, font: 'monospace' } }, schema: { is_unique: true } },
      { field: 'reading_time', type: 'integer', meta: { interface: 'input', width: 'half', note: 'Minutes' }, schema: {} },
      { field: 'summary', type: 'text', meta: { interface: 'input-multiline' }, schema: {} },
      { field: 'body', type: 'text', meta: { interface: 'input-rich-text-html' }, schema: {} },
    ],
  },
})
const m2o = (field, related, template, extra = {}) => [
  api('/fields/posts', { method: 'POST', body: { field, type: 'integer', meta: { interface: 'select-dropdown-m2o', special: ['m2o'], width: 'half', display: 'related-values', display_options: { template }, options: { template }, ...extra }, schema: {} } }),
]
await Promise.all(m2o('author', 'authors', '{{name}}'))
await api('/relations', { method: 'POST', body: { collection: 'posts', field: 'author', related_collection: 'authors', schema: { on_delete: 'SET NULL' } } })
await Promise.all(m2o('category', 'categories', '{{name}}'))
await api('/relations', { method: 'POST', body: { collection: 'posts', field: 'category', related_collection: 'categories', schema: { on_delete: 'SET NULL' } } })
await api('/fields/posts', { method: 'POST', body: { field: 'cover', type: 'uuid', meta: { interface: 'file-image', special: ['file'], display: 'image', display_options: { circle: false } }, schema: {} } })
await api('/relations', { method: 'POST', body: { collection: 'posts', field: 'cover', related_collection: 'directus_files', schema: { on_delete: 'SET NULL' } } })
await api('/fields/authors', { method: 'POST', body: { field: 'avatar', type: 'uuid', meta: { interface: 'file-image', special: ['file'], display: 'image', display_options: { circle: true }, width: 'half' }, schema: {} } })
await api('/relations', { method: 'POST', body: { collection: 'authors', field: 'avatar', related_collection: 'directus_files', schema: { on_delete: 'SET NULL' } } })

// Field order in the item form
const order = ['id', 'status', 'published_on', 'title', 'slug', 'reading_time', 'cover', 'author', 'category', 'summary', 'body']
for (const [i, f] of order.entries()) await api(`/fields/posts/${f}`, { method: 'PATCH', body: { meta: { sort: i + 1 } } })

// Generated images (rendered locally; no stock photos)
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1600, height: 900 } })
async function render(html, w, h) {
  await page.setViewportSize({ width: w, height: h })
  await page.setContent(`<html><body style="margin:0">${html}</body></html>`)
  return page.screenshot({ type: 'jpeg', quality: 88 })
}
function landscape([sky1, sky2, m1, m2, m3], sun) {
  return `<div style="position:relative;width:1600px;height:900px;overflow:hidden;background:linear-gradient(180deg,${sky1},${sky2})">
    <div style="position:absolute;left:${sun[0]}px;top:${sun[1]}px;width:220px;height:220px;border-radius:50%;background:radial-gradient(circle,#fff8e1,rgba(255,240,200,0.0) 70%)"></div>
    <svg width="1600" height="900" style="position:absolute;inset:0" viewBox="0 0 1600 900" preserveAspectRatio="none">
      <path d="M0 560 L220 380 L380 500 L620 300 L860 520 L1060 360 L1300 540 L1600 400 L1600 900 L0 900Z" fill="${m1}"/>
      <path d="M0 660 L260 520 L520 640 L760 500 L1020 660 L1260 540 L1600 650 L1600 900 L0 900Z" fill="${m2}"/>
      <path d="M0 780 L300 700 L620 780 L940 720 L1240 790 L1600 730 L1600 900 L0 900Z" fill="${m3}"/>
    </svg></div>`
}
async function upload(buf, name, title, folder) {
  const fd = new FormData()
  if (folder) fd.append('folder', folder)
  fd.append('title', title)
  fd.append('file', new Blob([buf], { type: 'image/jpeg' }), name)
  return (await api('/files', { method: 'POST', body: fd })).data.id
}
const old = (await api('/files?limit=-1&fields=id')).data.map((f) => f.id)
if (old.length) await api('/files', { method: 'DELETE', body: old })
await api('/folders?limit=-1').then(async (r) => { if (r.data.length) await api('/folders', { method: 'DELETE', body: r.data.map((f) => f.id) }) })
const covers = (await api('/folders', { method: 'POST', body: { name: 'Covers' } })).data.id
const people = (await api('/folders', { method: 'POST', body: { name: 'Authors' } })).data.id

const palettes = [
  [['#ffd6a5', '#fdf1e1', '#7d8fb3', '#4f6191', '#2c3a63'], [1080, 140]],
  [['#a8d8ea', '#e8f6fb', '#6fa57b', '#3f7a56', '#24503a'], [260, 120]],
  [['#ffb4a2', '#ffe5d9', '#b5838d', '#6d6875', '#3d3a4b'], [700, 200]],
  [['#cde7ff', '#f4faff', '#9bb7d4', '#5e81ac', '#334c6e'], [1200, 90]],
  [['#fbe7c6', '#fffaf0', '#c0a080', '#8a6a4f', '#4e3b2c'], [400, 160]],
  [['#d4c1ec', '#f5effc', '#8e7dbe', '#5d4e8c', '#352c57'], [980, 180]],
  [['#b8f2e6', '#effcf9', '#5e9c8f', '#3b6e64', '#22433d'], [180, 200]],
  [['#ffd3b6', '#fff4ec', '#e09f7d', '#a8604a', '#5c3427'], [820, 110]],
]

const categories = (await api('/items/categories', { method: 'POST', body: [
  { name: 'Trails', color: '#2ECDA7' }, { name: 'Gear', color: '#6644FF' }, { name: 'Guides', color: '#FFA439' }, { name: 'Field notes', color: '#3399FF' },
] })).data
const authorsSeed = [
  { name: 'Maya Okafor', role: 'Editor in chief', bio: 'Maps every trail twice before writing about it.', color: '#6644FF' },
  { name: 'Jonas Lindqvist', role: 'Gear editor', bio: 'Tests packs, stoves and boots until something breaks.', color: '#2ECDA7' },
  { name: 'Priya Raman', role: 'Staff writer', bio: 'Long walks, short sentences.', color: '#FFA439' },
]
const authors = []
for (const a of authorsSeed) {
  const initials = a.name.split(' ').map((s) => s[0]).join('')
  const img = await render(`<div style="width:400px;height:400px;display:flex;align-items:center;justify-content:center;background:${a.color};color:#fff;font:600 160px system-ui,sans-serif">${initials}</div>`, 400, 400)
  const avatar = await upload(img, `${initials.toLowerCase()}.jpg`, a.name, people)
  authors.push((await api('/items/authors', { method: 'POST', body: { name: a.name, role: a.role, bio: a.bio, avatar } })).data)
}

const posts = [
  ['Ridge walks for a long weekend', 'Trails', 0, 'published', 'Three days, two huts and one very windy saddle: a loop that rewards an early start.', 7],
  ['How we test hiking boots', 'Gear', 1, 'published', 'Two hundred kilometres, four surfaces and a bucket of cold water per pair.', 5],
  ['Packing list for shoulder season', 'Guides', 2, 'published', 'Layers that work from frost at dawn to sun at noon, without the extra weight.', 6],
  ['Notes from the lake district', 'Field notes', 0, 'published', 'Low cloud, high water and the best breakfast on the whole route.', 4],
  ['A beginner’s guide to map and compass', 'Guides', 2, 'published', 'Five skills that still matter when the phone battery does not.', 9],
  ['Lightweight stoves, compared', 'Gear', 1, 'draft', 'Boil times, fuel use and how each one behaves in a crosswind.', 8],
  ['Waterfall trails after the rain', 'Trails', 0, 'draft', 'Where to go when the forecast finally clears, and what to skip.', 5],
  ['Winter camping without the misery', 'Guides', 2, 'draft', 'Sleep warm, wake dry: the habits that make the difference.', 10],
]
const day = (n) => new Date(Date.UTC(2026, 9, 2 + n * 4)).toISOString().slice(0, 10)
for (const [i, [title, cat, ai, status, summary, mins]] of posts.entries()) {
  const img = await render(landscape(...palettes[i]), 1600, 900)
  const slug = title.toLowerCase().replace(/[’']/g, '').replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '')
  const cover = await upload(img, `${slug}.jpg`, title, covers)
  await api('/items/posts', {
    method: 'POST',
    body: {
      title, slug, status, summary, reading_time: mins, cover,
      published_on: status === 'published' ? day(i) : null,
      author: authors[ai].id,
      category: categories.find((c) => c.name === cat).id,
      body: `<p>${summary}</p><h2>Before you go</h2><p>Check the forecast the night before and again at the trailhead. Leave your route with someone at home.</p><ul><li>Water: two litres, plus a filter</li><li>Layers for wind and rain</li><li>Map, compass and a charged phone</li></ul><p>We will keep this page updated as conditions change.</p>`,
    },
  })
}
await browser.close()

// Posts list: a tabular preset with the useful columns
const presets = (await api('/presets?filter[collection][_eq]=posts&filter[user][_null]=true')).data
if (presets.length) await api('/presets', { method: 'DELETE', body: presets.map((p) => p.id) })
await api('/presets', {
  method: 'POST',
  body: {
    collection: 'posts', layout: 'tabular',
    layout_query: { tabular: { fields: ['cover', 'title', 'status', 'author', 'category', 'published_on'], sort: ['-published_on'] } },
    layout_options: { tabular: { widths: { cover: 90, title: 360, status: 140, author: 190, category: 150, published_on: 160 }, spacing: 'comfortable' } },
  },
})

// Public read on the content collections (a headless site reads these).
// Row filters (e.g. status = published) are a licensed feature
// (custom_permission_rules_enabled is false on the Core tier), so the site
// filters by status in its query instead.
const policies = (await api('/access?filter[role][_null]=true&filter[user][_null]=true&fields=policy')).data
const publicPolicy = policies[0]?.policy
if (publicPolicy) {
  for (const collection of ['posts', 'authors', 'categories', 'directus_files']) {
    await api('/permissions', { method: 'POST', raw: true, body: { policy: publicPolicy, collection, action: 'read', fields: ['*'], permissions: {} } })
  }
}

const check = await fetch(`${base}/items/posts?fields=title,author.name&filter[status][_eq]=published`)
console.log(`public /items/posts -> ${check.status}, ${(await check.json()).data?.length} published posts`)
console.log('seeded: 4 categories, 3 authors, 8 posts, 11 files')
