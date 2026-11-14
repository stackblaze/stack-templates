#!/usr/bin/env node
// Seeds a realistic board on a live Excalidraw deploy and captures the catalog
// stills in light and dark at 2x: the board, a live collaboration room with a
// second person (a second browser through the instance's own relay), and the
// export dialog. Drawing data stays in the throwaway browsers.
//
//   node seed-excalidraw-and-capture.mjs <app url> <outdir>
//
// The diagram comes from the app's own "Mermaid to Excalidraw" converter (it
// runs in the browser; no AI service).
import { chromium } from 'playwright';
import fs from 'node:fs';

const MERMAID = `flowchart LR
  C([Customer]) --> W[Web shop]
  W --> A[Checkout API]
  A --> D[(Orders DB)]
  A --> P[Payment provider]
  A --> Q[[Job queue]]
  Q --> E[Email receipts]
  Q --> S[Stock sync]
  style C fill:#ffec99,stroke:#f08c00
  style W fill:#a5d8ff,stroke:#1971c2
  style A fill:#d0bfff,stroke:#6741d9
  style D fill:#b2f2bb,stroke:#2f9e44
  style P fill:#ffc9c9,stroke:#e03131
  style Q fill:#ffd8a8,stroke:#e8590c
  style E fill:#e9ecef,stroke:#495057
  style S fill:#e9ecef,stroke:#495057`;

async function seedDiagram(p, text = MERMAID) {
  await p.locator('[title="More tools"], [aria-label="More tools"]').first().click();
  await p.getByRole('menuitem', { name: /Mermaid to Excalidraw/ }).click().catch(async () => {
    await p.locator('.dropdown-menu-item', { hasText: 'Mermaid to Excalidraw' }).click();
  });
  const ta = p.locator('.ttd-dialog .cm-content, .ttd-dialog textarea').first();
  await ta.waitFor();
  await ta.fill(text);
  await p.waitForTimeout(1500);
  await p.getByRole('button', { name: /^Insert/ }).click();
  await p.waitForSelector('.ttd-dialog', { state: 'detached' });
  await p.keyboard.press('Escape');
  await p.mouse.click(30, 600); // empty canvas: focus, deselect
  await p.keyboard.press('Shift+1'); // zoom to fit
  await p.waitForTimeout(500);
}

async function setTheme(p, theme) {
  const dark = await p.evaluate(() => document.querySelector('.excalidraw')?.classList.contains('theme--dark'));
  if ((theme === 'dark') !== dark) await p.keyboard.press('Alt+Shift+D');
  await p.waitForTimeout(400);
}

const [url, out] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const b = await chromium.launch();
const ctxFor = async (theme, name) => {
  const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2, colorScheme: theme });
  await ctx.addInitScript(([t, n]) => {
    localStorage.setItem('excalidraw-theme', t);
    localStorage.setItem('excalidraw-collab', JSON.stringify({ username: n }));
  }, [theme, name]);
  return ctx;
};
async function addNotes(p) {
  // a title and a hand-drawn ring, with the app's own tools
  await p.keyboard.press('t'); await p.mouse.click(420, 330);
  await p.keyboard.type('Checkout flow: Black Friday plan', { delay: 5 });
  await p.keyboard.press('Escape');
  await p.keyboard.press('o'); await p.mouse.move(1050, 500); await p.mouse.down();
  await p.mouse.move(1290, 605, { steps: 6 }); await p.mouse.up(); await p.keyboard.press('Escape');
  await p.keyboard.press('t'); await p.mouse.click(1300, 470);
  await p.keyboard.type('retry on 5xx?', { delay: 5 });
  await p.keyboard.press('Escape'); await p.keyboard.press('Escape');
  await p.mouse.click(30, 900);
}
for (const theme of ['light', 'dark']) {
  const sfx = theme === 'dark' ? '-dark' : '';
  const A = await (await ctxFor(theme, 'Alex')).newPage();
  await A.goto(url); await A.waitForSelector('.excalidraw'); await A.waitForTimeout(1500);
  await seedDiagram(A); await addNotes(A); await A.waitForTimeout(600);
  await A.screenshot({ path: `${out}/board${sfx}.png` });

  // export dialog
  await A.keyboard.press('Control+Shift+E'); await A.waitForSelector('.ImageExportModal');
  await A.waitForTimeout(1200);
  await A.screenshot({ path: `${out}/export${sfx}.png` });
  await A.keyboard.press('Escape'); await A.waitForTimeout(300);

  // live collaboration: start a room, a second person joins and points
  await A.getByRole('button', { name: /^Share$/ }).click();
  await A.getByRole('button', { name: /Start session/i }).click();
  await A.waitForFunction(() => location.hash.startsWith('#room='));
  await A.waitForTimeout(500);
  await A.mouse.click(150, 500); // backdrop closes the dialog
  await A.waitForSelector('.Modal', { state: 'detached' }); await A.waitForTimeout(300);
  const B = await (await ctxFor(theme, 'Maya')).newPage();
  await B.goto(A.url()); await B.waitForSelector('.excalidraw'); await B.waitForTimeout(3000);
  // Maya adds a sticky-style note and leaves her pointer on it
  await B.keyboard.press('r'); await B.mouse.move(1300, 760); await B.mouse.down(); await B.mouse.move(1560, 840, { steps: 5 }); await B.mouse.up();
  await B.keyboard.press('Enter'); await B.keyboard.type('Add a stock alert', { delay: 5 }); await B.keyboard.press('Escape');
  await B.keyboard.press('Escape'); await B.mouse.click(30, 950);
  await B.mouse.move(1480, 870, { steps: 8 });
  await A.waitForTimeout(1500);
  await A.screenshot({ path: `${out}/collab${sfx}.png` });
  await B.context().close(); await A.context().close();
}
await b.close();
