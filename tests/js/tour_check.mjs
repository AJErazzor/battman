// "Show me" (www/battman-tour.js) in a real browser, on a stand-in dashboard view. The stand-in card has a mode button
// (whose label is inside a span: the ring must take the whole button), a button that opens a modal "Turn Curtail?"
// popup (a native <dialog>, like Battman's), and a folded section holding a setting. The walkthrough:
//   1. the whole card (until next)        2. Curtail (until popup: pressing it opens the popup)
//   3. Turn on, inside the popup (until closed)    4. the folded setting (Show me asks to open the section first, until press)
// The check also clicks off (pauses), resumes, goes Back, and presses Escape. Desktop and phone. Prints one JSON line.
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
.pad{height:240px}</style></head><body><div class="pad"></div><battman-fakecard></battman-fakecard><div class="pad"></div><div class="pad"></div>
<script>
customElements.define("battman-fakecard", class extends HTMLElement {
  connectedCallback() {
    const r = this.attachShadow({ mode: "open" });
    r.innerHTML = '<style>:host{display:block;margin:0 auto;width:320px;padding:12px;border:1px solid #888;--battman-sky:#123456}'
      + 'button{margin:4px;padding:10px 16px;border-radius:8px}.sec.folded .body{display:none}.head{cursor:pointer;padding:6px;border:1px solid #ccc}</style>'
      + '<button id="mode"><span>Self Consume</span></button><button id="c"><span>Curtail</span></button>'
      + '<div class="sec folded"><div class="head" id="head">Billing</div><div class="body"><button id="fee">Daily network charge</button></div></div>';
    window.__clicks = [];
    r.getElementById("c").addEventListener("click", () => {
      window.__clicks.push("curtail");
      const d = document.createElement("dialog");
      d.innerHTML = '<h3>Turn Curtail?</h3><p>This will stop any exports.</p><button id="cancel">Cancel</button><button id="on">Turn on</button>';
      document.body.appendChild(d);
      d.showModal();
      d.querySelector("#on").addEventListener("click", () => { window.__clicks.push("on"); d.close(); d.remove(); });
      d.querySelector("#cancel").addEventListener("click", () => { d.close(); d.remove(); });
    });
    r.getElementById("head").addEventListener("click", () => r.querySelector(".sec").classList.remove("folded"));
    r.getElementById("fee").addEventListener("click", () => window.__clicks.push("fee"));
  }
});
</script>
<script type="module">
import { startTour, stopTour } from "/files/battman-tour.js";
window.__tour = { startTour, stopTour };
window.__steps = [
  { view: "power", card: "battman-fakecard", target: "", until: "next", say: "The mode card", body: "Open the Power view." },
  { view: "power", card: "battman-fakecard", target: "Curtail", until: "popup", say: "Tap Curtail", body: "On the card, tap Curtail." },
  { view: "power", popup: "Turn Curtail?", target: "Turn on", until: "closed", say: "Press Turn on", body: "It asks Turn Curtail?. Press Turn on." },
  { view: "power", card: "battman-fakecard", target: "Daily network charge", until: "press", say: "Tap the charge", body: "In Billing, tap Daily network charge." },
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
try {
  for (const [name, viewport] of [["desktop", { width: 1200, height: 800 }], ["phone", { width: 390, height: 760 }]]) {
    const ctx = await browser.newContext({ viewport, reducedMotion: "reduce" });
    const page = await ctx.newPage();
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("console", (m) => { if (m.type() === "error" && !/^Failed to load resource/.test(m.text())) errors.push(m.text()); });
    await page.goto(`${base}/dash/power`);
    await page.waitForFunction(() => window.__ready);
    const o = { vw: viewport.width };
    const T = "document.getElementById('battman-tour')";
    // what the walkthrough shows now: its words, where its ring is, where the stage lives
    const look = () => page.evaluate(`(() => { const t = ${T}; if (!t) return null; const r = t.shadowRoot; const q = (s) => r.querySelector(s);
      const box = (e) => { const b = e.getBoundingClientRect(); return [Math.round(b.left), Math.round(b.top), Math.round(b.right), Math.round(b.bottom)]; };
      return { meta: q('.meta').textContent, say: q('.say').textContent, ring: q('.ring').hidden ? null : box(q('.ring')), beckon: q('.ring').classList.contains('beckon'),
        words: box(q('.words')), inDialog: !!t.closest('dialog'), paused: !q('.pill').hidden, next: !!q('button[data-act=next]'),
        frost: getComputedStyle(q('.frost')).backdropFilter || getComputedStyle(q('.frost')).webkitBackdropFilter }; })()`);
    const el = (sel) => page.evaluate((s) => { const r = document.querySelector("battman-fakecard").shadowRoot; const e = r.querySelector(s) || document.querySelector(s); const b = e.getBoundingClientRect(); return [Math.round(b.left), Math.round(b.top), Math.round(b.right), Math.round(b.bottom)]; }, sel);
    const centre = (b) => [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2];
    const settle = (ms = 700) => page.waitForTimeout(ms);
    await page.evaluate(() => window.__tour.startTour({ title: "Stop exporting", steps: window.__steps }));
    await settle();
    o.card = await page.evaluate(() => { const b = document.querySelector("battman-fakecard").getBoundingClientRect(); return [Math.round(b.left), Math.round(b.top), Math.round(b.right), Math.round(b.bottom)]; });
    o.s1 = await look();
    await page.evaluate(`${T}.shadowRoot.querySelector('button[data-act=next]').click()`);
    await settle();
    o.curtail = await el("#c");
    o.s2 = await look();
    // a click off the ringed control pauses; Back to the walkthrough resumes on the same step
    await page.mouse.click(5, viewport.height - 5);
    await settle(300);
    o.paused = (await look()).paused;
    await page.evaluate(`${T}.shadowRoot.querySelector('button[data-act=resume]').click()`);
    await settle();
    o.resumed = await look();
    // the person presses Curtail: the popup opens and the walkthrough follows into it
    await page.mouse.click(...centre(o.curtail));
    await settle(900);
    o.on = await el("dialog #on");
    o.s3 = await look();
    await page.mouse.click(...centre(o.on));
    await settle(900);
    // step 4: the setting is in a folded section: open it first
    o.head = await el("#head");
    o.s4fold = await look();
    await page.mouse.click(...centre(o.head));
    await settle(900);
    o.fee = await el("#fee");
    o.s4 = await look();
    // Back goes to the step before
    await page.evaluate(`${T}.shadowRoot.querySelector('button[data-act=back]').click()`);
    await settle(1800);
    o.back = await look();     // step 3's popup isn't open, so it goes back to step 2, which opens it
    await page.keyboard.press("Escape");
    o.afterEsc = await page.evaluate(`!!${T}`);
    o.clicks = await page.evaluate(() => window.__clicks);
    out[name] = o;
    await ctx.close();
  }
} finally {
  await browser.close();
  server.close();
}
out.errors = errors;
console.log(JSON.stringify(out));
