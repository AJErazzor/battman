// Real-browser check of battman-pie-card's `style: bar` (run by tests/test_pie_card.py): the same
// slices as the doughnut laid along one stacked bar, the % inside blocks that are big enough, every
// block named in the legend, the pie left alone by default.
// usage: NODE_PATH=<node_modules with playwright> CHROME=<chromium> node pie_bar_check.js <www dir>
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
const http = require("http");
(async () => {
  const www = process.argv[2];
  const page = `<!doctype html><html><head><style>
ha-card{display:block}#wrap{width:420px}</style></head><body><div id="wrap"></div>
<script type="module">
await import("/battman-pie-card.js");
const S = (v, u = "MW") => ({ state: String(v), attributes: { unit_of_measurement: u } });
window.states = { "sensor.w": S(812.4), "sensor.sr": S(1120.7), "sensor.su": S(301.25), "sensor.b": S(41.9),
  "sensor.g1": S(55), "sensor.g2": S(12.5) };
window.CFG = { type: "custom:battman-pie-card", display_unit: "MW", decimals: 1, min_pct_label: 4, sort: "max", hide_legend_value: true,
  entities: [{ name: "Wind", color: "#a6e3a1", entity: "sensor.w" }, { name: "Solar (S)", color: "#f9a066", entity: "sensor.sr" },
    { name: "Solar (L)", color: "#fab387", entity: "sensor.su" }, { name: "Battery", color: "#cba6f7", entity: "sensor.b" },
    { name: "Gas", color: "#89b4fa", entities: ["sensor.g1", "sensor.g2"] }] };
window.mk = (extra) => { const el = document.createElement("battman-pie-card"); el.setConfig({ ...CFG, ...extra });
  document.getElementById("wrap").appendChild(el); el.hass = { states, themes: {} }; return el; };
window.ready = true;
</script></body></html>`;
  const server = http.createServer((req, res) => {
    const u = req.url.split("?")[0];
    if (u === "/index.html") { res.setHeader("content-type", "text/html"); return res.end(page); }
    const f = path.join(www, u);
    if (!fs.existsSync(f)) { res.statusCode = 404; return res.end(); }
    res.setHeader("content-type", "text/javascript");
    res.end(fs.readFileSync(f));
  }).listen(0);
  const browser = await chromium.launch({ executablePath: process.env.CHROME });
  const p = await browser.newPage({ viewport: { width: 460, height: 420 } });
  const errors = [];
  p.on("pageerror", (e) => errors.push(e.message));
  await p.goto(`http://127.0.0.1:${server.address().port}/index.html`);
  await p.waitForFunction(() => window.ready);
  const out = {};
  const info = (id) => p.evaluate((id) => {
    const r = window[id].shadowRoot;
    return {
      segs: [...r.querySelectorAll(".seg")].map((s) => ({ left: s.style.left, width: parseFloat(s.style.width), color: s.style.background,
        label: s.firstElementChild.textContent, shown: s.firstElementChild.style.visibility !== "hidden" })),
      total: (r.querySelector(".total") || {}).textContent || null,
      legend: [...r.querySelectorAll(".legend .row .name")].map((n) => n.textContent),
      arcs: r.querySelectorAll("circle.arc").length,
      isBar: r.querySelector("ha-card").classList.contains("bar"),
    };
  }, id);
  await p.evaluate(() => { window.bar = mk({ style: "bar" }); window.pie = mk({}); window.bad = mk({ style: "sideways" }); });
  await p.waitForTimeout(1200);
  out.bar = await info("bar");
  out.pie = await info("pie");
  out.bad = await info("bad");
  // the legend names every block, even with min_pct_legend unset and min_pct_label 4
  // a hovered block dims the others
  await p.evaluate(() => window.bar.shadowRoot.querySelector(".seg").dispatchEvent(new MouseEvent("mouseenter")));
  out.hover = await p.evaluate(() => [...window.bar.shadowRoot.querySelectorAll(".seg")].map((s) => s.className));
  // a missing sensor drops a block, and the others re-fill the bar
  await p.evaluate(() => { window.bar.shadowRoot.querySelector(".seg").dispatchEvent(new MouseEvent("mouseleave"));
    window.bar.hass = { states: { ...states, "sensor.w": { state: "unknown", attributes: {} } }, themes: {} }; });
  await p.waitForTimeout(1200);
  out.noWind = await info("bar");
  out.errors = errors;
  console.log(JSON.stringify(out));
  await browser.close();
  server.close();
})();
