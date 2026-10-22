// Real-browser check: Battman's scripts register their elements again when HA's frontend swaps
// window.customElements for its own registry after they've run (run by tests/test_v0184.py).
// usage: NODE_PATH=<node_modules with playwright> CHROME=<chromium> node registry_check.js <www dir> <scratch dir>
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
(async () => {
  const [www, dir] = process.argv.slice(2);
  for (const f of ["battman-cards.js", "battman-countdown.js"]) fs.copyFileSync(path.join(www, f), path.join(dir, f));
  fs.writeFileSync(path.join(dir, "index.html"), `<!doctype html><html><body>
<script>window.loadCardHelpers = async () => ({ createCardElement: () => document.createElement("div") });</script>
<script type="module" src="battman-countdown.js"></script>
<script type="module" src="battman-cards.js?cards=state,limits"></script>
</body></html>`);
  const http = require("http");
  const server = http.createServer((req, res) => {
    const f = path.join(dir, req.url.split("?")[0]);
    if (!fs.existsSync(f)) { res.statusCode = 404; return res.end(); }
    res.setHeader("content-type", f.endsWith(".js") ? "text/javascript" : "text/html");
    res.end(fs.readFileSync(f));
  }).listen(0);
  const browser = await chromium.launch({ executablePath: process.env.CHROME });
  const page = await browser.newPage();
  await page.goto(`http://127.0.0.1:${server.address().port}/index.html`);
  await page.waitForFunction(() => customElements.get("battman-image") && customElements.get("battman-countdown"));
  const tags = ["battman-countdown", "battman-card-editor", "battman-state", "battman-limits", "battman-image", "battman-image-editor"];
  const out = await page.evaluate(async (tags) => {
    // what HA's frontend does: a new registry in window.customElements, and its marker
    const defs = new Map();
    const swapped = { get: (t) => defs.get(t), define: (t, c) => { if (defs.has(t)) throw new Error("already defined"); defs.set(t, c); },
      whenDefined: async () => {} };
    Object.defineProperty(window, "customElements", { value: swapped, configurable: true, writable: true });
    window.CustomElementRegistryPolyfill = {};
    await new Promise((r) => setTimeout(r, 300));
    return { missing: tags.filter((t) => !defs.get(t)), sameClass: defs.get("battman-image") && defs.get("battman-image").name };
  }, tags);
  console.log(JSON.stringify(out));
  await browser.close();
  server.close();
})().catch((e) => { console.error(e); process.exit(1); });
