// "Show me" (www/battman-tour.js) in a real browser: a stand-in dashboard view with one card that shows three
// buttons. The check runs a three-step walkthrough on it (the whole card, then the Curtail button, then Sell),
// presses the real button under the tour, goes Back, Next to Done, and Escape, on a desktop and on a phone.
// Prints one JSON line of what it saw.
//
// node tour_check.mjs <custom_components/battman>
import http from "http";
import fs from "fs";
import path from "path";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const WWW = path.join(process.argv[2], "www");

const HTML = `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{margin:0;font-family:sans-serif;--primary-color:#03a9f4;--card-background-color:#fff;--primary-text-color:#111}
.pad{height:300px}</style></head><body><div class="pad"></div><battman-fakecard></battman-fakecard><div class="pad"></div>
<script>
customElements.define("battman-fakecard", class extends HTMLElement {
  connectedCallback() {
    const r = this.attachShadow({ mode: "open" });
    r.innerHTML = '<style>:host{display:block;margin:0 auto;width:320px;padding:12px;border:1px solid #888;--battman-sky:#123456}'
      + 'button{margin:4px;padding:8px 12px}</style><button>Active</button><button id="c"><span>Curtail</span></button><button>Sell</button>';
    window.__pressed = 0;
    r.getElementById("c").addEventListener("click", () => window.__pressed++);
  }
});
</script>
<script type="module">
import { startTour, stopTour } from "/files/battman-tour.js";
window.__tour = { startTour, stopTour };
window.__steps = [
  { view: "power", card: "battman-fakecard", text: "", say: "The mode card", body: "Open the Power view." },
  { view: "power", card: "battman-fakecard", text: "Curtail", say: "Tap Curtail", body: "On the card, tap Curtail." },
  { view: "power", card: "battman-fakecard", text: "Sell", say: "Then Sell", body: "Tap Sell." },
];
window.__ready = true;
</script></body></html>`;

const server = http.createServer((req, res) => {
  const u = new URL(req.url, "http://x");
  if (u.pathname.startsWith("/files/")) {
    const f = path.join(WWW, u.pathname.slice(7));
    if (!f.startsWith(WWW) || !fs.existsSync(f)) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { "Content-Type": "text/javascript" });
    return res.end(fs.readFileSync(f));
  }
  if (u.pathname === "/dash/power") { res.writeHead(200, { "Content-Type": "text/html" }); return res.end(HTML); }
  res.writeHead(404); res.end();
});

await new Promise((r) => server.listen(0, "127.0.0.1", r));
const base = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch({ executablePath: process.env.CHROME });
const out = {};
const errors = [];
const R = (b) => [Math.round(b.left), Math.round(b.top), Math.round(b.right), Math.round(b.bottom)];
try {
  for (const [name, viewport] of [["desktop", { width: 1200, height: 800 }], ["phone", { width: 390, height: 760 }]]) {
    const ctx = await browser.newContext({ viewport });
    const page = await ctx.newPage();
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("console", (m) => { if (m.type() === "error" && !/^Failed to load resource/.test(m.text())) errors.push(m.text()); });
    await page.goto(`${base}/dash/power`);
    await page.waitForFunction(() => window.__ready);
    const o = { vw: viewport.width };
    const T = "document.getElementById('battman-tour')";
    const step = () => page.evaluate(`(() => { const t = ${T}; if (!t) return null; const r = t.shadowRoot;
      const q = (s) => r.querySelector(s); const box = (e) => { const b = e.getBoundingClientRect(); return b; };
      const hole = box(q('.hole')), ring = q('.ring'), bub = box(q('.bubble'));
      return { meta: q('.meta span').textContent, say: q('.say').textContent, body: q('.body').textContent,
        hole: [Math.round(hole.left + 6), Math.round(hole.top + 6), Math.round(hole.right - 6), Math.round(hole.bottom - 6)],
        ring: !ring.hidden, ringBox: ring.hidden ? null : (() => { const b = box(ring); return [Math.round(b.left + 6), Math.round(b.top + 6), Math.round(b.right - 6), Math.round(b.bottom - 6)]; })(),
        ringTop: Math.round(box(ring).top), ringBottom: Math.round(box(ring).bottom),
        bubbleTop: Math.round(bub.top), bubbleBottom: Math.round(bub.bottom), bubbleLeft: Math.round(bub.left), bubbleRight: Math.round(bub.right),
        next: q('button[data-act=next]').textContent }; })()`);
    const settle = () => page.waitForTimeout(900);
    await page.evaluate(() => window.__tour.startTour({ title: "Stop exporting", steps: window.__steps }));
    await settle();
    o.card = await page.evaluate((r) => { const e = document.querySelector("battman-fakecard").getBoundingClientRect(); return [Math.round(e.left), Math.round(e.top), Math.round(e.right), Math.round(e.bottom)]; });
    o.step1 = await step();
    await page.evaluate(`${T}.shadowRoot.querySelector('button[data-act=next]').click()`);
    await settle();
    o.button = await page.evaluate(() => { const e = document.querySelector("battman-fakecard").shadowRoot.querySelector("#c span").getBoundingClientRect(); return [Math.round(e.left), Math.round(e.top), Math.round(e.right), Math.round(e.bottom)]; });
    o.step2 = await step();
    const b = o.button;
    await page.mouse.click((b[0] + b[2]) / 2, (b[1] + b[3]) / 2);
    o.pressed = await page.evaluate(() => window.__pressed);
    await page.evaluate(`${T}.shadowRoot.querySelector('button[data-act=back]').click()`);
    await settle();
    o.back = (await step()).say;
    await page.evaluate(`${T}.shadowRoot.querySelector('button[data-act=next]').click()`); await settle();
    await page.evaluate(`${T}.shadowRoot.querySelector('button[data-act=next]').click()`); await settle();
    o.step3 = await step();
    await page.keyboard.press("Escape");
    o.afterEsc = await page.evaluate(`!!${T}`);
    await page.evaluate(() => window.__tour.startTour({ title: "Again", steps: window.__steps.slice(2) }));
    await settle();
    await page.evaluate(`${T}.shadowRoot.querySelector('button[data-act=next]').click()`);
    o.afterDone = await page.evaluate(`!!${T}`);
    out[name] = o;
    await ctx.close();
  }
} finally {
  await browser.close();
  server.close();
}
out.errors = errors;
console.log(JSON.stringify(out));
