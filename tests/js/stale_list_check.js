// Real-browser check: a page that still has an older list of card files naming cards that are real
// cards now (open since before the update) gets each from its own script (battman-log.js and so
// on), not a card-file card of that name (run by tests/test_v0200.py).
// usage: NODE_PATH=<node_modules with playwright> CHROME=<chromium> node stale_list_check.js <www dir>
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
const http = require("http");
(async () => {
  const www = process.argv[2];
  const page = `<!doctype html><html><body>
<script>window.loadCardHelpers = async () => ({ createCardElement: () => document.createElement("div") });</script>
<script type="module" src="/battmanfiles/battman-cards.js?v=0.19.1&cards=state,log,limits,cost-compare,cost-chart,settings,theme-studio,curvy,pricy"></script>
</body></html>`;
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
  await p.goto(`http://127.0.0.1:${server.address().port}/index.html`);
  const REAL = ["log", "cost-compare", "cost-chart", "settings", "theme-studio", "curvy", "pricy"];
  await p.waitForFunction((real) => customElements.get("battman-state") && real.every((c) => customElements.get("battman-" + c)),
                          REAL, { timeout: 10000 });
  const out = await p.evaluate((real) => ({
    real: Object.fromEntries(real.map((c) => [c, Object.getPrototypeOf(customElements.get("battman-" + c)).name])),
    log: customElements.get("battman-log").name,
    state: Object.getPrototypeOf(customElements.get("battman-state")).name,
    logPicker: window.customCards.filter((c) => c.type === "battman-log").length,
  }), REAL);
  console.log(JSON.stringify(out));
  await browser.close(); server.close();
})();
