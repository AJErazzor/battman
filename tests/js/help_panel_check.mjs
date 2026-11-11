// Battman's "?" help panel (www/battman-help-panel.js) in a real browser, against a stand-in Home Assistant that
// serves the guide's own pages. A card's shadow root holds two "?" tags; the check presses them and the panel's
// buttons, on a desktop and on a phone, and prints one JSON line of what it saw.
//
// node help_panel_check.mjs <custom_components/battman>
import http from "http";
import fs from "fs";
import path from "path";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const WWW = path.join(process.argv[2], "www");
const GUIDE = JSON.parse(fs.readFileSync(process.env.GUIDE_FILE, "utf8"));          // {pages: {id: markdown}}
const PAGE_ID = process.env.HELP_PAGE;                       // the guide page the tags point at
const IDS = JSON.parse(process.env.HELP_IDS);                // [section summary id, sub-group summary id]

const HTML = `<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{margin:0;font-family:sans-serif;--primary-text-color:#111;--card-background-color:#fff;--divider-color:#ddd;--primary-color:#03a9f4}</style>
</head><body><div id="host"></div>
<script>
const pages = ${JSON.stringify(GUIDE.pages)};
window.__calls = [];
window.hass = { callApi: async (method, p) => {
  window.__calls.push(p);
  const m = /^battman\\/guide\\/page\\/(.+)$/.exec(p);
  if (m && pages[m[1]] != null) return {id: m[1], markdown: pages[m[1]]};
  throw new Error("404");
} };
window.__nav = [];
window.addEventListener("location-changed", () => window.__nav.push(location.pathname + location.search + location.hash));
</script>
<script type="module">
import * as help from "/files/battman-help-panel.js";
const host = document.getElementById("host");
const root = host.attachShadow({mode: "open"});
root.innerHTML = '<style>' + help.TAG_CSS + '</style><div class="wrap">' + help.tagHtml(${JSON.stringify(IDS[0])}, "Section")
  + help.tagHtml(${JSON.stringify(IDS[1])}, "Group", true) + '</div>';
root.addEventListener("click", (e) => { const t = e.target.closest("[data-help]"); if (t) help.openPanel(root, window.hass, {page: ${JSON.stringify(PAGE_ID)}, id: t.dataset.help, from: t}); });
root.addEventListener("keydown", (e) => { if (e.key === "Escape") help.closePanel(root); });
window.__help = help;
window.__ready = true;
</script></body></html>`;

const server = http.createServer((req, res) => {
  const u = new URL(req.url, "http://x");
  if (u.pathname.startsWith("/files/")) {
    const f = path.join(WWW, u.pathname.slice(7));
    if (!f.startsWith(WWW) || !fs.existsSync(f)) { res.writeHead(404); return res.end(); }
    res.writeHead(200, {"Content-Type": "text/javascript"});
    return res.end(fs.readFileSync(f));
  }
  if (u.pathname.startsWith("/dash/settings")) { res.writeHead(200, {"Content-Type": "text/html"}); return res.end(HTML); }
  res.writeHead(404); res.end();
});

await new Promise((r) => server.listen(0, "127.0.0.1", r));
const base = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch({ executablePath: process.env.CHROME });
const out = {};
const errors = [];
try {
  for (const [name, viewport] of [["desktop", {width: 1200, height: 900}], ["phone", {width: 390, height: 800}]]) {
    const ctx = await browser.newContext({ viewport });
    const page = await ctx.newPage();
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("console", (m) => { if (m.type() === "error" && !/^Failed to load resource/.test(m.text())) errors.push(m.text()); });
    page.on("response", (r) => { if (r.status() >= 400 && !r.url().endsWith("/favicon.ico")) errors.push(`${r.status()} ${r.url()}`); });
    await page.goto(`${base}/dash/settings`);
    await page.waitForFunction(() => window.__ready);
    const r = {};
    const q = (fn, arg) => page.evaluate(([f, a]) => new Function("root", "a", f)(document.getElementById("host").shadowRoot, a), [fn, arg]);
    const panel = () => q(`const p = root.querySelector(".bh-panel"); if (!p) return null; const b = p.getBoundingClientRect();
      return {title: p.querySelector("h2").textContent, label: p.getAttribute("aria-label"), body: p.querySelector(".bh-body").textContent.trim(),
        chips: [...p.querySelectorAll(".bh-chip")].map((c) => c.textContent), expand: (p.querySelector("[data-bh-expand]") || {}).textContent || null,
        back: (p.querySelector("[data-bh-back]") || {}).textContent || null, href: p.querySelector(".bh-all").getAttribute("href"),
        left: Math.round(b.left), top: Math.round(b.top), width: Math.round(b.width), bottom: Math.round(b.bottom),
        focused: root.activeElement === p, focus: root.activeElement === p ? "panel" : (root.activeElement ? root.activeElement.textContent : null), pressed: [...root.querySelectorAll('.bh-tag[aria-expanded="true"]')].map((t) => t.dataset.help)};`);
    r.hidden = await q(`return [...root.querySelectorAll(".bh-tag")].map((t) => getComputedStyle(t).display);`);
    await q(`root.querySelector(".wrap").classList.add("helpmode");`);
    r.shown = await q(`return [...root.querySelectorAll(".bh-tag")].map((t) => getComputedStyle(t).display + " " + getComputedStyle(t).borderRadius);`);
    await page.locator("#host .bh-tag").first().click();
    await page.waitForFunction(() => document.getElementById("host").shadowRoot.querySelector(".bh-panel"));
    r.summary = await panel();
    if (r.summary.chips.length) {
      await page.locator("#host .bh-chip").first().click();
      r.child = await panel();
      await page.locator("#host [data-bh-back]").click();
      const back = await panel();
      r.backTo = back.title;
      r.backFocus = back.focus;
    }
    await page.locator("#host [data-bh-expand]").click();
    r.expanded = await panel();
    await page.locator("#host [data-bh-expand]").click();
    r.less = await panel();
    await page.keyboard.press("Escape");                       // focus stayed in the panel, so Esc still closes it
    r.escAfterButtons = await q(`return !!root.querySelector(".bh-panel")`);
    await page.locator("#host .bh-tag.small").click();
    await page.waitForFunction((t) => document.getElementById("host").shadowRoot.querySelector(".bh-panel h2").textContent !== t, r.summary.title);
    r.group = await panel();
    await page.keyboard.press("Escape");
    r.closed = await q(`return {panel: !!root.querySelector(".bh-panel"), focus: (root.activeElement || {}).dataset ? root.activeElement.dataset.help : null,
      pressed: root.querySelectorAll('.bh-tag[aria-expanded="true"]').length};`);
    await page.locator("#host .bh-tag").first().click();
    await page.waitForFunction(() => document.getElementById("host").shadowRoot.querySelector(".bh-panel"));
    await page.locator("#host .bh-all").click();
    r.browse = await page.evaluate(() => ({nav: window.__nav, at: location.pathname + location.search + location.hash,
      from: JSON.parse(sessionStorage.getItem('battman.helpFrom') || 'null'),
      panel: !!document.getElementById("host").shadowRoot.querySelector(".bh-panel")}));
    r.fetches = await page.evaluate(() => window.__calls.length);
    r.overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
    if (name === "phone") await page.screenshot({ path: path.join(process.env.OUT_DIR || ".", "help_panel_phone.png") });
    out[name] = r;
    await ctx.close();
  }
} catch (e) {
  errors.push(String(e && e.stack || e));
} finally {
  await browser.close();
  server.close();
}
out.errors = errors;
process.stdout.write(JSON.stringify(out) + "\n");
