// The Battman Help card (www/battman-guide.js and the guide it loads) in a real browser, against a stand-in
// Home Assistant: the guide's own pages (read from custom_components/battman/guide/ through the same files the
// API serves), Battman's entity map and a few states. Prints one JSON line of what it saw.
//
// node guide_check.mjs <custom_components/battman> <out dir>
import http from "http";
import fs from "fs";
import path from "path";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const ROOT = process.argv[2];
const OUT = process.argv[3];
const WWW = path.join(ROOT, "www");
const GUIDE = JSON.parse(process.env.GUIDE_JSON);     // {index, pages: {id: markdown}} from the Python side

const PAGE = `<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{margin:0;font-family:sans-serif;--primary-text-color:#111;--secondary-text-color:#555;--card-background-color:#fff;
--divider-color:#ddd;--primary-color:#03a9f4;--secondary-background-color:#f3f3f3}</style></head><body>
<div id="host"></div>
<script>
window.__loaded = [];
const states = {
  "input_boolean.battman_enable": {state: "on", attributes: {}},
  "input_select.battman_mode": {state: "Self Consume", attributes: {}},
  "input_boolean.battman_no_export": {state: "off", attributes: {}},
  "sensor.battman_run": {state: "False", attributes: {lastRunAt: new Date(Date.now() - 180000).toISOString()}},
};
const guide = ${JSON.stringify(GUIDE)};
window.hass = {
  states,
  callApi: async (method, p) => {
    if (p === "battman/entities") return {version: "test", entities: {enable: "input_boolean.battman_enable",
      mode: "input_select.battman_mode", run: "sensor.battman_run", no_export: "input_boolean.battman_no_export"}};
    if (p === "battman/guide") return {version: "9.9.9", ...guide.index};
    const m = /^battman\\/guide\\/page\\/(.+)$/.exec(p);
    if (m && guide.pages[m[1]] != null) return {id: m[1], markdown: guide.pages[m[1]]};
    const e = new Error("404"); e.body = {message: "no page"}; throw e;
  },
  connection: {sendMessagePromise: async (msg) => ({issues: [
    {domain: "battman", issue_id: "packages_not_loaded", ignored: false},
    {domain: "battman", issue_id: "opennem_missing", ignored: true},
    {domain: "other", issue_id: "x", ignored: false}]})},
};
</script>
<script type="module">
import "/files/battman-guide.js";
window.__stubLoaded = performance.getEntriesByType("resource").map((r) => r.name);
window.addCard = () => { const c = document.createElement("battman-guide"); c.setConfig({type: "custom:battman-guide"});
  c.hass = window.hass; document.getElementById("host").appendChild(c); return true; };
window.__ready = true;
</script></body></html>`;

const server = http.createServer((req, res) => {
  const u = new URL(req.url, "http://x");
  if (u.pathname.startsWith("/files/")) {
    const f = path.join(WWW, u.pathname.slice(7));
    if (!f.startsWith(WWW) || !fs.existsSync(f)) { res.writeHead(404); return res.end(); }
    res.writeHead(200, {"Content-Type": f.endsWith(".js") ? "text/javascript" : "application/octet-stream"});
    return res.end(fs.readFileSync(f));
  }
  if (u.pathname.startsWith("/dash/help")) { res.writeHead(200, {"Content-Type": "text/html"}); return res.end(PAGE); }
  res.writeHead(404); res.end();
});

await new Promise((r) => server.listen(0, "127.0.0.1", r));
const base = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch({ executablePath: process.env.CHROME });
const out = {};
const errors = [];
try {
  const ctx = await browser.newContext({ viewport: { width: 1200, height: 900 } });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => { if (m.type() === "error" && !/^Failed to load resource/.test(m.text())) errors.push(m.text()); });
  page.on("response", (r) => { if (r.status() >= 400 && !r.url().endsWith("/favicon.ico")) errors.push(`${r.status()} ${r.url()}`); });
  const inCard = (fn, arg) => page.evaluate(([f, a]) => {
    const r = document.querySelector("battman-guide").shadowRoot;
    return new Function("r", "a", f)(r, a);
  }, [fn, arg]);
  const waitH1 = (text) => page.waitForFunction((t) => {
    const c = document.querySelector("battman-guide");
    const h = c && c.shadowRoot && c.shadowRoot.querySelector("article h1");
    return h && h.textContent.includes(t);
  }, text, { timeout: 10000 });

  await page.goto(`${base}/dash/help`);
  await page.waitForFunction(() => window.__ready);
  // the stub alone: nothing of the guide itself loads on a page without the card
  const names = (await page.evaluate(() => window.__stubLoaded)).map((n) => n.replace(/^.*\/files\//, ""));
  out.before = names.filter((n) => /guide|marked/.test(n));
  await page.evaluate(() => window.addCard());
  await waitH1("Battman help");
  out.after = (await page.evaluate(() => performance.getEntriesByType("resource").map((r) => r.name)))
    .map((n) => n.replace(/^.*\/files\//, "")).filter((n) => /guide|marked/.test(n));
  out.home = await inCard(`return {h1: r.querySelector("article h1").textContent,
    toc: [...r.querySelectorAll("nav.toc a")].map((a) => a.textContent),
    current: r.querySelector('nav.toc a[aria-current="page"]').textContent,
    status: r.querySelector(".status").textContent.replace(/\\s+/g, " ").trim(),
    scripts: r.querySelectorAll("script").length}`);
  await page.waitForFunction(() => /1 open/.test(document.querySelector("battman-guide").shadowRoot.querySelector(".status").textContent));
  out.status = await inCard(`return r.querySelector(".status").textContent.replace(/\\s+/g, " ").trim()`);

  // a link to another page: the address changes, the page shows
  await inCard(`r.querySelector('article a[data-page="start/device-page"]').click()`);
  await waitH1("The Battman device page");
  out.device = { url: await page.evaluate(() => location.pathname + location.search + location.hash),
    h1: await inCard(`return r.querySelector("article h1").textContent`) };
  // Back
  await page.goBack();
  await waitH1("Battman help");
  out.back = await page.evaluate(() => location.pathname + location.search);

  // straight to a section, as a link from elsewhere in HA does
  await page.evaluate(() => { history.pushState(null, "", "/dash/help?page=help/repairs#packages-not-loaded");
    window.dispatchEvent(new CustomEvent("location-changed")); });
  await waitH1("Battman's Repairs");
  await page.waitForTimeout(300);
  out.repairs = await inCard(`const t = r.getElementById("packages-not-loaded");
    return {anchor: !!t, top: Math.round(t.getBoundingClientRect().top),
      open: [...r.querySelectorAll(".directive.repairs li")].map((li) => li.textContent),
      openLink: (r.querySelector(".directive.repairs li a") || {}).getAttribute && r.querySelector(".directive.repairs li a").getAttribute("href"),
      callouts: r.querySelectorAll(".callout").length, codeCopy: r.querySelectorAll("button[data-copy-code]").length}`);
  await page.screenshot({ path: path.join(OUT, "guide-wide.png") });

  // a page that isn't in the guide
  await page.evaluate(() => { history.pushState(null, "", "/dash/help?page=nope/nothing"); window.dispatchEvent(new CustomEvent("location-changed")); });
  await waitH1("Page not found");
  out.missing = await inCard(`return r.querySelector("article").textContent.includes("nope/nothing")`);

  // phone width: the contents fold behind a button
  await page.setViewportSize({ width: 390, height: 800 });
  await page.evaluate(() => { history.pushState(null, "", "/dash/help"); window.dispatchEvent(new CustomEvent("location-changed")); });
  await waitH1("Battman help");
  out.phone = await inCard(`const n = r.querySelector("nav.toc"); const b = r.querySelector("button.toc-btn");
    const before = getComputedStyle(n).display; b.click(); const after = getComputedStyle(n).display;
    return {before, after, expanded: b.getAttribute("aria-expanded"), btn: getComputedStyle(b).display,
      overflow: document.documentElement.scrollWidth > window.innerWidth}`);
  await page.screenshot({ path: path.join(OUT, "guide-phone.png") });
} finally {
  out.errors = errors;
  console.log(JSON.stringify(out));
  await browser.close();
  server.close();
}
