#!/usr/bin/env node
/**
 * Seed a rich Excalidraw board on a live deploy, then capture 2× screenshots
 * for the install-modal demo video.
 *
 * Usage:
 *   node seed-excalidraw-and-capture.mjs --url https://….stackblaze.app
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const OUT = path.resolve(__dirname, '../services/excalidraw')

function parseArgs(argv) {
  const args = { headless: true }
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i]
    if (a === '--url') args.url = argv[++i]
    else if (a === '--headed') args.headless = false
    else if (a === '--out') args.out = argv[++i]
  }
  return args
}

function id(prefix, n) {
  return `${prefix}${n}`
}

function base(partial) {
  return {
    version: 1,
    versionNonce: Math.floor(Math.random() * 1e9),
    isDeleted: false,
    fillStyle: 'solid',
    strokeWidth: 2,
    strokeStyle: 'solid',
    roughness: 1,
    opacity: 100,
    angle: 0,
    groupIds: [],
    frameId: null,
    roundness: { type: 3 },
    boundElements: null,
    updated: Date.now(),
    link: null,
    locked: false,
    seed: Math.floor(Math.random() * 1e9),
    ...partial,
  }
}

function rect(n, x, y, w, h, bg, stroke = '#1e1e1e') {
  return base({
    id: id('r', n),
    type: 'rectangle',
    x,
    y,
    width: w,
    height: h,
    backgroundColor: bg,
    strokeColor: stroke,
  })
}

function text(n, x, y, str, opts = {}) {
  const fontSize = opts.fontSize || 28
  const width = opts.width || Math.max(120, str.length * fontSize * 0.55)
  const height = opts.height || fontSize * 1.4
  return base({
    id: id('t', n),
    type: 'text',
    x,
    y,
    width,
    height,
    text: str,
    originalText: str,
    fontSize,
    fontFamily: 5,
    textAlign: opts.align || 'center',
    verticalAlign: 'middle',
    containerId: null,
    lineHeight: 1.25,
    autoResize: true,
    backgroundColor: 'transparent',
    strokeColor: opts.stroke || '#1e1e1e',
    rough: 0,
    roughness: 0,
  })
}

function arrow(n, x, y, points, opts = {}) {
  const xs = points.map((p) => p[0])
  const ys = points.map((p) => p[1])
  return base({
    id: id('a', n),
    type: 'arrow',
    x,
    y,
    width: Math.max(...xs) - Math.min(...xs) || 1,
    height: Math.max(...ys) - Math.min(...ys) || 1,
    points,
    startArrowhead: opts.start || null,
    endArrowhead: opts.end || 'arrow',
    backgroundColor: 'transparent',
    strokeColor: opts.stroke || '#1e1e1e',
    roundness: { type: 2 },
  })
}

function ellipse(n, x, y, w, h, bg) {
  return base({
    id: id('e', n),
    type: 'ellipse',
    x,
    y,
    width: w,
    height: h,
    backgroundColor: bg,
    strokeColor: '#1e1e1e',
  })
}

function freedraw(n, x, y, points) {
  return base({
    id: id('f', n),
    type: 'freedraw',
    x,
    y,
    width: 40,
    height: 40,
    points,
    pressures: [],
    simulatePressure: true,
    backgroundColor: 'transparent',
    strokeColor: '#e03131',
    strokeWidth: 1,
  })
}

/** Product planning whiteboard — architecture + sticky notes. */
function buildScene() {
  const elements = [
    text(1, 420, 40, 'Stackblaze — Sprint board', { fontSize: 48, width: 620, align: 'left' }),
    text(2, 420, 100, 'Self-hosted whiteboard for product & eng', {
      fontSize: 22,
      width: 520,
      align: 'left',
      stroke: '#868e96',
    }),

    // Sticky notes
    rect(1, 80, 180, 220, 160, '#ffec99'),
    text(3, 100, 210, 'Ideas', { fontSize: 24, width: 180 }),
    text(4, 100, 250, '• Dark mode\n• Live collab\n• Export PNG', {
      fontSize: 18,
      width: 180,
      align: 'left',
      height: 80,
    }),

    rect(2, 80, 380, 220, 160, '#b2f2bb'),
    text(5, 100, 410, 'Done', { fontSize: 24, width: 180 }),
    text(6, 100, 450, '• Auth SSO\n• CDN edge\n• Autosave', {
      fontSize: 18,
      width: 180,
      align: 'left',
      height: 80,
    }),

    rect(3, 80, 580, 220, 160, '#ffc9c9'),
    text(7, 100, 610, 'Blocked', { fontSize: 24, width: 180 }),
    text(8, 100, 650, '• GPU quota\n• Design QA', {
      fontSize: 18,
      width: 180,
      align: 'left',
      height: 70,
    }),

    // Architecture boxes
    rect(4, 420, 200, 240, 110, '#a5d8ff'),
    text(9, 450, 235, 'Dashboard', { fontSize: 28, width: 180 }),
    text(10, 450, 275, 'Vue · Vite', { fontSize: 18, width: 180, stroke: '#495057' }),

    rect(5, 760, 200, 240, 110, '#d0bfff'),
    text(11, 790, 235, 'API', { fontSize: 28, width: 180 }),
    text(12, 790, 275, 'NestJS · K8s', { fontSize: 18, width: 180, stroke: '#495057' }),

    rect(6, 1100, 200, 240, 110, '#96f2d7'),
    text(13, 1130, 235, 'Cluster', { fontSize: 28, width: 180 }),
    text(14, 1130, 275, 'ingress · pods', { fontSize: 18, width: 180, stroke: '#495057' }),

    rect(7, 590, 420, 280, 120, '#ffd8a8'),
    text(15, 630, 455, 'Excalidraw', { fontSize: 30, width: 200 }),
    text(16, 620, 500, 'on Stackblaze', { fontSize: 20, width: 220, stroke: '#495057' }),

    arrow(1, 660, 255, [
      [0, 0],
      [100, 0],
    ]),
    arrow(2, 1000, 255, [
      [0, 0],
      [100, 0],
    ]),
    arrow(3, 880, 310, [
      [0, 0],
      [-40, 110],
    ]),

    ellipse(1, 1280, 420, 180, 180, '#ffc9c9'),
    text(17, 1310, 485, 'Users', { fontSize: 28, width: 120 }),

    arrow(4, 870, 480, [
      [0, 0],
      [400, 20],
    ]),

    // Hand-drawn check
    freedraw(1, 1320, 560, [
      [0, 12],
      [8, 22],
      [28, 0],
    ]),

    text(18, 420, 620, 'End-to-end encrypted · Works offline · MIT', {
      fontSize: 20,
      width: 560,
      align: 'left',
      stroke: '#868e96',
    }),
  ]

  return elements
}

async function dismissWelcome(page) {
  // Click canvas to dismiss welcome overlay / start drawing hint
  await page.keyboard.press('Escape').catch(() => {})
  await page.mouse.click(900, 500)
  await page.waitForTimeout(400)
  // Prefer closing any "Excalidraw+" / signup panels via Escape
  await page.keyboard.press('Escape').catch(() => {})
}

async function injectScene(page, elements) {
  await page.evaluate((els) => {
    localStorage.setItem('excalidraw', JSON.stringify(els))
    const stateRaw = localStorage.getItem('excalidraw-state')
    let state = {}
    try {
      state = stateRaw ? JSON.parse(stateRaw) : {}
    } catch {
      state = {}
    }
    state.showWelcomeScreen = false
    state.theme = 'light'
    state.zoom = { value: 0.85 }
    state.scrollX = -40
    state.scrollY = -20
    localStorage.setItem('excalidraw-state', JSON.stringify(state))
    localStorage.setItem('excalidraw-theme', 'light')
  }, elements)
}

async function capture(page, outDir, name) {
  const file = path.join(outDir, `screenshot-${name}.png`)
  await page.screenshot({ path: file, type: 'png' })
  const st = fs.statSync(file)
  console.log(`  wrote ${file} (${Math.round(st.size / 1024)} KB)`)
  return file
}

async function main() {
  const args = parseArgs(process.argv)
  if (!args.url) {
    console.error('Usage: node seed-excalidraw-and-capture.mjs --url <https://…>')
    process.exit(1)
  }
  const baseUrl = args.url.replace(/\/$/, '')
  const outDir = args.out || OUT
  fs.mkdirSync(outDir, { recursive: true })

  const elements = buildScene()
  console.log(`Seeding ${elements.length} elements → ${baseUrl}`)

  const browser = await chromium.launch({ headless: args.headless })
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 2,
    locale: 'en-US',
    colorScheme: 'light',
    ignoreHTTPSErrors: true,
  })
  const page = await context.newPage()
  page.setDefaultTimeout(60000)

  // Prime storage before first paint of app chrome
  await page.goto(baseUrl, { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(1500)
  await injectScene(page, elements)
  await page.reload({ waitUntil: 'networkidle' })
  await page.waitForTimeout(2500)
  await dismissWelcome(page)
  await page.waitForTimeout(800)

  // Shot 1 — full board
  await capture(page, outDir, 'board')

  // Shot 2 — zoom into architecture
  await page.evaluate(() => {
    const stateRaw = localStorage.getItem('excalidraw-state')
    const state = stateRaw ? JSON.parse(stateRaw) : {}
    state.zoom = { value: 1.25 }
    state.scrollX = -380
    state.scrollY = -120
    localStorage.setItem('excalidraw-state', JSON.stringify(state))
  })
  await page.reload({ waitUntil: 'networkidle' })
  await page.waitForTimeout(2000)
  await dismissWelcome(page)
  await capture(page, outDir, 'architecture')

  // Shot 3 — sticky notes / planning (left column @ x≈80)
  await page.evaluate(() => {
    const stateRaw = localStorage.getItem('excalidraw-state')
    const state = stateRaw ? JSON.parse(stateRaw) : {}
    state.zoom = { value: 1.45 }
    // Positive scrollX moves view left toward stickies
    state.scrollX = 200
    state.scrollY = -160
    localStorage.setItem('excalidraw-state', JSON.stringify(state))
  })
  await page.reload({ waitUntil: 'networkidle' })
  await page.waitForTimeout(2000)
  await dismissWelcome(page)
  await capture(page, outDir, 'stickies')

  // Shot 4 — dark theme
  await page.evaluate((els) => {
    localStorage.setItem('excalidraw', JSON.stringify(els))
    const stateRaw = localStorage.getItem('excalidraw-state')
    const state = stateRaw ? JSON.parse(stateRaw) : {}
    state.showWelcomeScreen = false
    state.theme = 'dark'
    state.zoom = { value: 0.9 }
    state.scrollX = -40
    state.scrollY = -20
    localStorage.setItem('excalidraw-state', JSON.stringify(state))
    localStorage.setItem('excalidraw-theme', 'dark')
  }, elements)
  await page.reload({ waitUntil: 'networkidle' })
  await page.waitForTimeout(2500)
  await dismissWelcome(page)
  await capture(page, outDir, 'dark')

  // Shot 5 — library / tools (open help briefly then board overview)
  await page.evaluate((els) => {
    localStorage.setItem('excalidraw', JSON.stringify(els))
    const stateRaw = localStorage.getItem('excalidraw-state')
    const state = stateRaw ? JSON.parse(stateRaw) : {}
    state.showWelcomeScreen = false
    state.theme = 'light'
    state.zoom = { value: 0.75 }
    state.scrollX = -20
    state.scrollY = 0
    localStorage.setItem('excalidraw-state', JSON.stringify(state))
    localStorage.setItem('excalidraw-theme', 'light')
  }, elements)
  await page.reload({ waitUntil: 'networkidle' })
  await page.waitForTimeout(2000)
  await dismissWelcome(page)
  // Select rectangle tool for toolbar highlight
  await page.keyboard.press('2').catch(() => {})
  await page.waitForTimeout(400)
  await capture(page, outDir, 'tools')

  // dashboard.png = hero for catalog
  fs.copyFileSync(path.join(outDir, 'screenshot-board.png'), path.join(outDir, 'dashboard.png'))
  console.log('  wrote dashboard.png (from board)')

  await browser.close()
  console.log('Done')
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
