import { chromium } from 'playwright';
const cards = [
  ['autumn', 'Autumn Blend', 'Maple, toasted pecan, dark cocoa', '#7c2d12', '#ea580c'],
  ['latte', 'Oat Latte Week', 'Every oat latte $1 off, Mon to Fri', '#3f2a1d', '#a16207'],
  ['roast', 'Roasting Day', 'Ethiopia Guji, light roast, fresh Thursday', '#14532d', '#65a30d'],
  ['brew', 'Pour-over 101', 'Free class, Saturday 10 am', '#1e3a8a', '#0ea5e9'],
  ['beans', 'New Single Origin', 'Colombia Huila: red apple, caramel', '#581c87', '#db2777'],
];
const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1200, height: 800 } });
for (const [k, t, s, c1, c2] of cards) {
  await p.setContent(`<html><body style="margin:0"><div style="width:1200px;height:800px;background:linear-gradient(135deg,${c1},${c2});display:flex;flex-direction:column;justify-content:center;padding:0 110px;box-sizing:border-box;font-family:Georgia,serif;color:#fff">
  <div style="font:600 28px system-ui;letter-spacing:6px;opacity:.85">NORTHWIND COFFEE</div>
  <div style="font-size:120px;line-height:1.05;margin:28px 0 24px">${t}</div>
  <div style="font:400 40px system-ui;opacity:.92">${s}</div>
  <div style="position:absolute;right:110px;bottom:90px;width:150px;height:150px;border-radius:50%;border:10px solid rgba(255,255,255,.35)"></div></div></body></html>`);
  await p.screenshot({ path: `seedimg/${k}.png` });
}
await b.close();
