// Real-browser check of the Battman card wrapper's `theme:` option (run by tests/test_v0171.py).
// usage: NODE_PATH=<node_modules with playwright> CHROME=<chromium> node theme_check.js <battman-cards.js> <scratch dir>
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
(async () => {
  const src = fs.readFileSync(process.argv[2], "utf8");
  const dir = process.argv[3];
  fs.writeFileSync(path.join(dir, "battman-cards.js"), src);
  fs.writeFileSync(path.join(dir, "index.html"), `<!doctype html><html><body>
<script>
window.loadCardHelpers = async () => ({ createCardElement: (cfg) => { const d = document.createElement("div"); d.className = "inner"; d.textContent = cfg.type; return d; } });
</script>
<script type="module" src="battman-cards.js?cards=state"></script></body></html>`);
  const http = require("http");
  const server = http.createServer((req, res) => {
    const f = path.join(dir, req.url.split("?")[0]);
    if (!fs.existsSync(f)) { res.statusCode = 404; return res.end(); }
    res.setHeader("content-type", f.endsWith(".js") ? "text/javascript" : "text/html");
    res.end(fs.readFileSync(f));
  }).listen(0);
  const port = server.address().port;
  const browser = await chromium.launch({ executablePath: process.env.CHROME });
  const page = await browser.newPage();
  await page.goto(`http://127.0.0.1:${port}/index.html`);
  await page.waitForFunction(() => customElements.get("battman-state"));
  const out = await page.evaluate(async () => {
    const card = { config: { type: "custom:fake" }, missing_map: [], needs: [], name: "State", grid_options: { columns: "full" } };
    const themes = { darkMode: true, themes: {
      "Battman Coffee": { "battman-green": "#123456", "primary-text-color": "#eeeeee", modes: { dark: { "battman-red": "#ff0000" }, light: { "battman-red": "#00ff00" } } },
      "Battman Nord": { "battman-green": "#abcdef" } } };
    const mk = (themeName, problem) => ({
      states: { "sensor.battman_theme_mode_colours": { state: "x", attributes: themeName ? { theme: themeName } : { problem } } },
      themes, callApi: async () => card,
    });
    const r = {};
    const Cls = customElements.get("battman-state");
    r.stub = await Cls.getStubConfig(mk("Battman Coffee"));
    const el = document.createElement("battman-state");
    document.body.append(el);
    el.setConfig({ type: "custom:battman-state", theme: "battman" });
    el.hass = mk("Battman Coffee");
    await new Promise((res) => setTimeout(res, 200));
    const inner = () => el.querySelector(".inner");
    const v = (n) => inner() && getComputedStyle(inner()).getPropertyValue(n).trim();
    r.coffee = { green: v("--battman-green"), red: v("--battman-red"), text: v("--primary-text-color") };
    el.hass = mk("Battman Nord");                       // dashboard theme changed
    r.nord = { green: v("--battman-green"), red: v("--battman-red") };
    el.hass = mk("Battman Gone");                        // not installed
    r.gone = el.textContent;
    el.hass = mk(null, "No dashboard theme picked");
    r.unpicked = el.textContent;
    el.hass = mk("Battman Coffee");                      // back
    await new Promise((res) => setTimeout(res, 200));
    r.back = v("--battman-green");
    const named = document.createElement("battman-state");
    document.body.append(named);
    named.setConfig({ type: "custom:battman-state", theme: "Battman Nord" });
    named.hass = mk("Battman Coffee");
    await new Promise((res) => setTimeout(res, 200));
    r.named = getComputedStyle(named.querySelector(".inner")).getPropertyValue("--battman-green").trim();
    const plain = document.createElement("battman-state");
    document.body.append(plain);
    plain.setConfig({ type: "custom:battman-state" });
    plain.hass = mk("Battman Coffee");
    await new Promise((res) => setTimeout(res, 200));
    r.plain = getComputedStyle(plain.querySelector(".inner")).getPropertyValue("--battman-green").trim();
    return r;
  });
  console.log(JSON.stringify(out));
  await browser.close();
  server.close();
})().catch((e) => { console.error(e); process.exit(1); });
