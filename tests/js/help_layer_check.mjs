// The Power view's "?" help (www/battman-help-layer.js) in a real browser, against a stand-in Home Assistant that
// serves the guide's own pages. Three stand-in cards register with the layer (two have a summary on the Power
// page, one doesn't); the check presses the Help button, a "?" tag, Escape, and changes Show help and the theme.
// Prints one JSON line of what it saw.
//
// node help_layer_check.mjs <custom_components/battman>
import http from "http";
import fs from "fs";
import path from "path";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const WWW = path.join(process.argv[2], "www");
const GUIDE = JSON.parse(process.env.GUIDE_JSON);          // {pages: {id: markdown}}
const CARDS = JSON.parse(process.env.HELP_CARDS);          // [card id with a summary, another, ...]

const HTML = `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{margin:0;font-family:sans-serif;--primary-text-color:#111;--card-background-color:#fff;--divider-color:#ddd;--primary-color:#03a9f4;--header-height:56px}
.card{position:absolute;left:20px;width:300px;height:200px;border:1px solid #888;background:#eee;--battman-sky:#123456}
#a{top:100px}#b{top:340px;left:340px}#c{top:600px}#tall{top:900px;height:1400px;left:340px}</style></head><body>
<div class="card" id="a"></div><div class="card" id="b"></div><div class="card" id="c"></div><div class="card" id="tall"></div>
<script>
const pages = ${JSON.stringify(GUIDE.pages)};
window.__calls = [];
const el = document.createElement("home-assistant");
el.hass = { states: { "sensor.battman_parameters": { attributes: { showHelp: true } } },
  callApi: async (method, p) => { window.__calls.push(p); const m = /^battman\\/guide\\/page\\/(.+)$/.exec(p);
    if (m && pages[m[1]] != null) return { id: m[1], markdown: pages[m[1]] }; throw new Error("404"); } };
document.body.appendChild(el);
</script>
<script type="module">
import { helpRegister } from "/files/battman-help-layer.js";
window.__reg = helpRegister;
window.__off = {};
const byId = (i) => document.getElementById(i);
window.__off.a = helpRegister(${JSON.stringify(CARDS[0])}, () => byId("a"));
window.__off.b = helpRegister(${JSON.stringify(CARDS[1])}, () => byId("b"));
window.__off.c = helpRegister("no-such-card", () => byId("c"));
window.__off.tall = helpRegister(${JSON.stringify(CARDS[0])}, () => byId("tall"));
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
  for (const [name, viewport] of [["desktop", { width: 1200, height: 900 }], ["phone", { width: 390, height: 800 }]]) {
    const ctx = await browser.newContext({ viewport });
    const page = await ctx.newPage();
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("console", (m) => { if (m.type() === "error" && !/^Failed to load resource/.test(m.text())) errors.push(m.text()); });
    page.on("response", (r) => { if (r.status() >= 400 && !r.url().endsWith("/favicon.ico")) errors.push(`${r.status()} ${r.url()}`); });
    await page.goto(`${base}/dash/power`);
    await page.waitForFunction(() => window.__ready);
    const q = (fn, arg) => page.evaluate(([f, a]) => new Function("root", "a", f)(document.getElementById("battman-help-layer").shadowRoot, a), [fn, arg]);
    const r = {};
    r.button = await q(`const b = root.querySelector(".helpbtn"); const r = b.getBoundingClientRect();
      return {hidden: b.hidden, pressed: b.getAttribute("aria-pressed"), right: Math.round(innerWidth - r.right), top: Math.round(r.top), theme: getComputedStyle(root.host).getPropertyValue("--battman-sky").trim()};`);
    r.tagsBefore = await q(`return root.querySelectorAll(".bh-tag").length;`);
    const tagInfo = () => q(`return [...root.querySelectorAll(".bh-tag")].map((t) => { const r = t.getBoundingClientRect();
      return {id: t.dataset.help, right: Math.round(r.right), top: Math.round(r.top), vis: t.style.visibility, display: getComputedStyle(t).display}; });`);
    await q(`root.querySelector(".helpbtn").click();`);
    await page.waitForFunction(() => document.getElementById("battman-help-layer").shadowRoot.querySelectorAll(".bh-tag").length > 0);
    await page.waitForTimeout(150);
    r.pressed = await q(`return root.querySelector(".helpbtn").getAttribute("aria-pressed");`);
    r.tags = await tagInfo();
    r.cardBoxes = await page.evaluate(() => ["a", "b", "c", "tall"].map((i) => { const r = document.getElementById(i).getBoundingClientRect(); return {i, right: Math.round(r.right), top: Math.round(r.top)}; }));
    // a card that fills the screen: the tag stays in view under the header
    await page.evaluate(() => window.scrollTo(0, 1200));
    await page.waitForTimeout(150);
    r.scrolled = await tagInfo();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(150);
    // press a tag: the panel opens, in the layer
    await q(`root.querySelector('.bh-tag[data-token]').click();`);
    await page.waitForFunction(() => document.getElementById("battman-help-layer").shadowRoot.querySelector(".bh-panel"));
    r.panel = await q(`const p = root.querySelector(".bh-panel"); const b = p.getBoundingClientRect();
      return {title: p.querySelector("h2").textContent, left: Math.round(b.left), top: Math.round(b.top), width: Math.round(b.width), pressed: [...root.querySelectorAll('.bh-tag[aria-expanded="true"]')].length,
        allBg: getComputedStyle(p.querySelector(".bh-all")).backgroundColor, allBorder: getComputedStyle(p.querySelector(".bh-all")).borderTopWidth, tagBorder: getComputedStyle(root.querySelector(".bh-tag")).borderTopColor};`);
    r.fetches = await page.evaluate(() => window.__calls.length);
    await page.keyboard.press("Escape");
    r.afterEsc1 = await q(`return {panel: !!root.querySelector(".bh-panel"), pressed: root.querySelector(".helpbtn").getAttribute("aria-pressed")};`);
    await page.keyboard.press("Escape");
    r.afterEsc2 = await q(`return {tags: root.querySelectorAll(".bh-tag").length, pressed: root.querySelector(".helpbtn").getAttribute("aria-pressed")};`);
    // Show help off: the button goes, and help mode with it
    await q(`root.querySelector(".helpbtn").click();`);
    await page.waitForFunction(() => document.getElementById("battman-help-layer").shadowRoot.querySelectorAll(".bh-tag").length > 0);
    await page.evaluate(() => { document.querySelector("home-assistant").hass.states["sensor.battman_parameters"].attributes.showHelp = false; });
    await page.waitForTimeout(1300);
    r.showHelpOff = await q(`return {hidden: root.querySelector(".helpbtn").hidden, tags: root.querySelectorAll(".bh-tag").length, pressed: root.querySelector(".helpbtn").getAttribute("aria-pressed")};`);
    await page.evaluate(() => { document.querySelector("home-assistant").hass.states["sensor.battman_parameters"].attributes.showHelp = true; });
    await page.waitForTimeout(1300);
    r.showHelpOn = await q(`return root.querySelector(".helpbtn").hidden;`);
    // the theme follows the card
    await page.evaluate(() => { document.getElementById("a").style.setProperty("--battman-sky", "#abcdef"); });
    await page.waitForTimeout(1300);
    r.theme = await q(`return getComputedStyle(root.host).getPropertyValue("--battman-sky").trim();`);
    // every card taken off: no button, no tags
    await q(`root.querySelector(".helpbtn").click();`);
    await page.waitForTimeout(200);
    await page.evaluate(() => { for (const k of Object.keys(window.__off)) window.__off[k](); });
    await page.waitForTimeout(200);
    r.gone = await q(`return {hidden: root.querySelector(".helpbtn").hidden, tags: root.querySelectorAll(".bh-tag").length, panel: !!root.querySelector(".bh-panel")};`);
    out[name] = r;
    await ctx.close();
  }
} finally {
  await browser.close();
  server.close();
}
out.errors = errors;
console.log(JSON.stringify(out));
