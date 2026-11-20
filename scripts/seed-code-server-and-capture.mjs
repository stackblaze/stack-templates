// seed-code-server-and-capture.mjs <url> <outdir> <light|dark> <probe|test|capture>
// Password from $CODE_SERVER_PASSWORD, or from the PASSWORD entry of a `stackblaze variables list --reveal -o json` file in $CS_VARS. Never printed.
// Seed first: see seed-code-server/seed.sh (run as uid 1000 in the pod) and copy seed-code-server/settings.json to ~/.local/share/code-server/User/.
import { chromium } from 'playwright';
const [url, out, theme = 'dark', mode = 'probe'] = process.argv.slice(2);
import { readFileSync } from 'node:fs';
const pw = process.env.CODE_SERVER_PASSWORD || JSON.parse(readFileSync(process.env.CS_VARS || 'vars.json', 'utf8')).vars.find((v) => v.name === 'PASSWORD')?.value;
if (!pw) throw new Error('CS_PASSWORD unset');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2, colorScheme: theme });
const page = await ctx.newPage();
const errors = [];
page.on('pageerror', (e) => errors.push(String(e)));
const shot = async (name) => { await page.screenshot({ path: `${out}/${name}${theme === 'dark' ? '-dark' : ''}.png` }); console.log('shot', name); };
await page.goto(url + '/login');
await page.waitForSelector('input[type=password]', { timeout: 60000 });
await page.fill('input[type=password]', pw);
await page.press('input[type=password]', 'Enter');
await page.waitForSelector('.monaco-workbench', { timeout: 90000 });
await sleep(4000);
const trust = page.getByRole('button', { name: /Yes, I trust/ });
if (await trust.isVisible().catch(() => false)) { await trust.click(); await sleep(1500); }
const kb = page.keyboard;
async function quickOpen(name) {
  await kb.press('Control+P'); await sleep(800);
  await kb.type(name, { delay: 30 }); await sleep(1200);
  await kb.press('Enter'); await sleep(1500);
}
async function terminal(cmd, wait = 2500) {
  await page.locator('.xterm-helper-textarea').last().focus();
  await kb.type(cmd, { delay: 15 }); await kb.press('Enter'); await sleep(wait);
}
if (mode === 'probe') { await shot('probe-0'); }
async function cmd(name, wait = 1200) {
  await kb.press('F1'); await sleep(700); await kb.type(name, { delay: 20 }); await sleep(900); await kb.press('Enter'); await sleep(wait);
}
if (mode === 'capture') {
  await cmd('Terminal: Kill All Terminals');
  await cmd('View: Close All Editors');
  await cmd('Notifications: Clear All Notifications');
  await kb.press('Control+Shift+E'); await sleep(800);
  await quickOpen('server.js');
  await kb.press('Control+G'); await sleep(400); await kb.type('9'); await kb.press('Enter'); await sleep(400); await kb.press('End');
  await kb.press('Control+Backquote'); await sleep(3500);
  await terminal('clear; cd ~/project/todo-api && npm test', 7000);
  await cmd('Notifications: Clear All Notifications', 600);
  await shot('editor');
  await terminal('clear; PORT=3000 npm start & sleep 2; curl -s localhost:3000/todos | grep title', 5000);
  await shot('run');
  await cmd('Notifications: Clear All Notifications', 600);
  await kb.press('Control+Shift+G'); await sleep(1500);
  await page.locator('.scm-view .monaco-list-row', { hasText: 'server.js' }).first().click(); await sleep(3000);
  await shot('source-control');
  await terminal('kill %1', 800);
}
if (mode === 'test') {
  // 1. open a file and edit it
  await quickOpen('server.js');
  if (mode === 'test') {
    await kb.press('Control+G'); await sleep(500); await kb.type('8'); await kb.press('Enter'); await sleep(400);
    await kb.press('End'); await kb.press('Enter');
    await kb.type('{ id: 4, title: "Deploy on StackBlaze", done: false },', { delay: 10 });
    await kb.press('Control+S'); await sleep(1500);
  }
  // 2. integrated terminal
  await kb.press('Control+Backquote'); await sleep(3000);
  await terminal('clear; cd ~/project/todo-api && npm test 2>&1 | tail -n 9', 6000);
  if (mode === 'test') {
    await terminal('(PORT=3000 npm start > /tmp/todo-api.log 2>&1 &) ; sleep 2; curl -s localhost:3000/todos | tee /tmp/todos.json', 5000);
  }
  await shot('editor-terminal');
}
console.log('pageerrors', errors.length, errors.slice(0, 3).join(' | ').slice(0, 400));
await browser.close();
