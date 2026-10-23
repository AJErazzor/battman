// Real-browser check of the curve editors' button wiring (battman-curve-editor.js wireHandlers):
// data-on-click / -input / -change / -mouseenter / -mouseleave inside a shadow root call the named
// handler with its arguments ('text', numbers, this, this.value, event). Run by tests/test_v0220.py.
// usage: NODE_PATH=<node_modules with playwright> CHROME=<chromium> node curve_handlers_check.js <www dir>
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
const http = require("http");
(async () => {
  const www = process.argv[2];
  const page = `<!doctype html><html><body><div id="host"></div>
<script type="module">
import { wireHandlers } from "/battmanfiles/battman-curve-editor.js";
const root = document.getElementById("host").attachShadow({ mode: "open" });
root.innerHTML = \`<button id="b" data-on-click="pick('jan', 3, this)">b</button>
  <input id="i" data-on-input="typed(7, this.value)">
  <input id="c" type="checkbox" data-on-change="changed(event)">
  <div id="h" data-on-mouseenter="enter(5)" data-on-mouseleave="leave()" style="width:100px;height:100px"><span>in</span></div>\`;
window.calls = [];
wireHandlers(root, {
  pick: (a, n, el) => calls.push(["pick", a, n, el.id]),
  typed: (n, v) => calls.push(["typed", n, v]),
  changed: (ev) => calls.push(["changed", ev.target.id]),
  enter: (h) => calls.push(["enter", h]),
  leave: () => calls.push(["leave"]),
});
window.root = root;
</script></body></html>`;
  const server = http.createServer((req, res) => {
    const u = req.url.split("?")[0];
    if (u === "/index.html") { res.setHeader("content-type", "text/html"); return res.end(page); }
    const f = path.join(www, u.replace(/^\/battmanfiles\//, ""));
    if (!fs.existsSync(f)) { res.statusCode = 404; return res.end(); }
    res.setHeader("content-type", "text/javascript");
    res.end(fs.readFileSync(f));
  }).listen(0);
  const browser = await chromium.launch({ executablePath: process.env.CHROME });
  const p = await browser.newPage();
  const errors = []; p.on("pageerror", (e) => errors.push(e.message));
  await p.goto(`http://127.0.0.1:${server.address().port}/index.html`);
  await p.waitForFunction(() => window.root);
  await p.locator("#b").click();
  await p.locator("#i").fill("42");
  await p.locator("#c").check();
  const h = await p.locator("#h").boundingBox();
  await p.mouse.move(h.x - 20, h.y - 20);
  await p.mouse.move(h.x + 10, h.y + 10);         // enter
  await p.mouse.move(h.x + 50, h.y + 50);         // move inside (onto its child): no second enter
  await p.locator("#h span").hover();
  await p.mouse.move(h.x + 300, h.y + 300);       // leave
  const calls = await p.evaluate(() => window.calls);
  console.log(JSON.stringify({ calls, errors }));
  await browser.close();
  server.close();
})().catch((e) => { console.error(e); process.exit(1); });
