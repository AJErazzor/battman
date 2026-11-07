// Real-browser check of the one Battman script (www/battman.js): it starts the others, each in its own import, so a
// script that fails to load is reported and the rest carry on. (run by tests/test_element_registry.py)
// usage: NODE_PATH=<node_modules with playwright> CHROME=<chromium> node loader_check.js <www dir (a copy)>
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
const http = require("http");
(async () => {
  const www = process.argv[2];
  const server = http.createServer((req, res) => {
    const name = req.url.split("?")[0];
    if (name === "/index.html") {
      res.setHeader("content-type", "text/html");
      return res.end(`<!doctype html><html><body><home-assistant></home-assistant><script type="module" src="battman.js?cards=state"></script></body></html>`);
    }
    const f = path.join(www, name);
    if (!fs.existsSync(f) || !fs.statSync(f).isFile()) { res.statusCode = 404; return res.end(); }
    res.setHeader("content-type", f.endsWith(".js") ? "text/javascript" : "text/html");
    res.end(fs.readFileSync(f));
  }).listen(0);
  const browser = await chromium.launch({ executablePath: process.env.CHROME });
  const page = await browser.newPage();
  const errors = [];
  page.on("console", (m) => { if (m.type() === "error" && m.text().startsWith("Battman:")) errors.push(m.text()); });   // (not the favicon 404)
  await page.goto(`http://127.0.0.1:${server.address().port}/index.html`);
  const tags = ["battman-countdown", "battman-house", "battman-log", "battman-settings", "battman-curvy", "battman-pricy", "battman-forecast-view", "battman-pie-card", "battman-state", "battman-overrides"];
  await page.waitForTimeout(2500);
  const out = await page.evaluate((tags) => ({
    defined: tags.filter((t) => customElements.get(t)),
    lib: !!(window.BattmanLib && window.BattmanLib.modal),
    enginelog: !!window.battmanEngineLog,
  }), tags);
  console.log(JSON.stringify({ ...out, errors }));
  await browser.close();
  server.close();
})().catch((e) => { console.error(e); process.exit(1); });
