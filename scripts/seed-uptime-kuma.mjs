// Seed demo monitors and a public status page on an Uptime Kuma deploy (idempotent by name).
// UPTIME_KUMA_URL=https://... UPTIME_KUMA_ADMIN_PASSWORD=... node scripts/seed-uptime-kuma.mjs
// Needs socket.io-client (npm i socket.io-client@4) in scripts/.
import { io } from 'socket.io-client'

const base = process.env.UPTIME_KUMA_URL
const url = base.replace(/\/+$/, '')

const v = { ADMIN_USERNAME: process.env.UPTIME_KUMA_ADMIN_USERNAME || 'admin', ADMIN_PASSWORD: process.env.UPTIME_KUMA_ADMIN_PASSWORD }
const s = io(url, { transports: ['websocket'] })
await new Promise((r) => s.once('connect', r))
const call = (ev, ...a) => new Promise((done, fail) => s.timeout(30000).emit(ev, ...a, (e, r) => (e ? fail(new Error(ev)) : done(r))))
let monitorList = {}
s.on('monitorList', (l) => { monitorList = l })
s.on('updateMonitorIntoList', (l) => { monitorList = { ...monitorList, ...l } })
await new Promise((r) => setTimeout(r, 1500))
const login = await call('login', { username: v.ADMIN_USERNAME, password: v.ADMIN_PASSWORD, token: '' })
if (!login.ok) throw new Error('login failed')
await new Promise((r) => setTimeout(r, 2500))

const common = {
  method: 'GET', interval: 30, retryInterval: 30, resendInterval: 0, maxretries: 1, timeout: 24,
  accepted_statuscodes: ['200-299'], notificationIDList: {}, maxredirects: 10, ignoreTls: false, upsideDown: false,
  expiryNotification: false, active: true, conditions: [], kafkaProducerBrokers: [], kafkaProducerSaslOptions: { mechanism: 'None' }, rabbitmqNodes: [],
}
const MONITORS = [
  { group: 'Websites', type: 'http', name: 'StackBlaze website', url: 'https://www.stackblaze.com' },
  { group: 'Websites', type: 'http', name: 'Example.com', url: 'https://example.com' },
  { group: 'Websites', type: 'keyword', name: 'Wikipedia (keyword)', url: 'https://www.wikipedia.org', keyword: 'Wikipedia' },
  { group: 'Infrastructure', type: 'http', name: 'GitHub API', url: 'https://api.github.com/zen' },
  { group: 'Infrastructure', type: 'dns', name: 'Cloudflare DNS', hostname: 'example.com', dns_resolve_server: '1.1.1.1', port: 53, dns_resolve_type: 'A' },
  { group: 'Infrastructure', type: 'port', name: 'Cloudflare HTTPS port', hostname: '1.1.1.1', port: 443 },
]
const byName = () => Object.fromEntries(Object.values(monitorList).map((m) => [m.name, m]))
const ids = {}
for (const m of MONITORS) {
  const { group, ...mon } = m
  const have = byName()[m.name]
  if (have) { ids[m.name] = have.id; console.log('have', m.name); continue }
  const r = await call('add', { ...common, ...mon })
  console.log('add', m.name, r.ok ? 'ok' : r.msg)
  if (r.ok) ids[m.name] = r.monitorID
}

const slug = 'status'
const sp = await call('getStatusPage', slug)
if (!sp.ok) console.log('addStatusPage', (await call('addStatusPage', 'Service Status', slug)).msg)
const groups = ['Websites', 'Infrastructure'].map((g, i) => ({
  name: g, weight: i + 1,
  monitorList: MONITORS.filter((m) => m.group === g && ids[m.name]).map((m) => ({ id: ids[m.name] })),
}))
const saved = await call('saveStatusPage', slug, {
  slug, title: 'Service Status', description: 'Live status of our websites and infrastructure.', theme: 'auto', published: true,
  showTags: false, domainNameList: [], customCSS: '', footerText: '', showPoweredBy: true, googleAnalyticsId: '',
  autoRefreshInterval: 300, showCertificateExpiry: false, rssTitle: '', analyticsType: null, analyticsId: null, analyticsScriptUrl: null,
}, '/icon.svg', groups)
console.log('status page', saved.ok ? 'saved' : saved.msg)
s.close()
process.exit(0)
