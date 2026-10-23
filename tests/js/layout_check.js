// Real-browser check that the Battman card wrapper passes HA's view layout ("grid" / "panel")
// to the card inside it, before and after the inner card is built (run by tests/test_card_wrapper.py).
// usage: NODE_PATH=<node_modules with playwright> CHROME=<chromium> node layout_check.js <battman-cards.js> <scratch dir>
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
(async () => {
  const dir = process.argv[3];
  fs.writeFileSync(path.join(dir, "battman-cards.js"), fs.readFileSync(process.argv[2], "utf8"));
  fs.writeFileSync(path.join(dir, "index.html"), `<!doctype html><html><body>
<script>
window.loadCardHelpers = async () => ({ createCardElement: (cfg) => { const d = document.createElement("div"); d.className = "inner"; return d; } });
</script>
<script type="module" src="battman-cards.js?cards=limits"></script></body></html>`);
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
  await page.waitForFunction(() => customElements.get("battman-limits"));
  const out = await page.evaluate(async () => {
    const card = { config: { type: "vertical-stack", cards: [] }, missing_map: [], needs: [], name: "Limits",
                   grid_options: { columns: "full", rows: 12, min_rows: 6 } };
    const hass = { states: {}, themes: { darkMode: true, themes: {} }, callApi: async () => card };
    const wait = () => new Promise((r) => setTimeout(r, 200));
    const r = {};
    // HA sets layout before hass (the card isn't built yet): the inner card gets it when built
    const a = document.createElement("battman-limits");
    document.body.append(a);
    a.setConfig({ type: "custom:battman-limits" });
    a.layout = "grid";
    a.hass = hass;
    await wait();
    r.early = a.querySelector(".inner").layout;
    // HA changes it after the card is built (e.g. the view type changed): passed straight on
    a.layout = "panel";
    a.isPanel = true;
    r.later = [a.querySelector(".inner").layout, a.querySelector(".inner").isPanel];
    r.grid = a.getGridOptions();
    // no layout from HA (masonry view): the inner card gets none
    const b = document.createElement("battman-limits");
    document.body.append(b);
    b.setConfig({ type: "custom:battman-limits" });
    b.hass = hass;
    await wait();
    r.none = b.querySelector(".inner").layout === undefined;
    // in HA's card picker (added the way HA adds it): the card itself is drawn
    if (!customElements.get("hui-card-picker")) customElements.define("hui-card-picker", class extends HTMLElement {});
    const picker = document.createElement("hui-card-picker");
    picker.attachShadow({ mode: "open" });
    document.body.append(picker);
    const pv = document.createElement("battman-limits");
    pv.setConfig({ type: "custom:battman-limits" });
    pv.hass = hass;
    picker.shadowRoot.append(pv);
    await wait();
    r.picker = { img: !!pv.querySelector("img"), inner: !!pv.querySelector(".inner") };
    return r;
  });
  console.log(JSON.stringify(out));
  await browser.close();
  server.close();
})().catch((e) => { console.error(e); process.exit(1); });
