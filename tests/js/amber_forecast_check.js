// Real-browser check of the Amber forecast chart card (run by tests/test_v0270.py): it draws from
// the two Amber forecast sensors, the range pills and legend taps are kept per device, the tooltip
// names the interval, and a missing sensor or empty forecast is said on the card.
// usage: NODE_PATH=<node_modules with playwright> CHROME=<chromium> node amber_forecast_check.js <www dir>
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
const http = require("http");
(async () => {
  const www = process.argv[2];
  const page = `<!doctype html><html><head><style>
:root{--battman-amber:#fab387;--battman-green:#a6e3a1;--battman-orange:#f9a066;--battman-yellow:#f9e2af;
--battman-red:#f38ba8;--battman-teal:#94e2d5;--battman-sky:#89dceb;--battman-blue:#89b4fa;--divider-color:#333;--secondary-text-color:#aaa;
--primary-text-color:#eee;--card-background-color:#1e1e2e;--primary-color:#a6e3a1}
#wrap{width:800px;height:340px}</style></head><body><div id="wrap"></div>
<script type="module">
const base = Math.floor(Date.now() / 1800000) * 1800000;   // on a half hour
const f = (i, raw, dur) => ({ start_time: new Date(base + i * 1800000).toISOString(), duration: dur || 30,
  per_kwh: raw, advanced_price_low: raw - 0.02, advanced_price_predicted: raw + 0.01, advanced_price_high: raw + 0.03 });
window.mk = (buy, sell, tz) => ({ config: { time_zone: tz === undefined ? "Australia/Adelaide" : tz }, themes: {}, states: Object.assign({},
  buy === null ? {} : { "sensor.amber_billing_interval_forecasts_general_price": { attributes: { Forecasts: buy } } },
  sell === null ? {} : { "sensor.amber_billing_interval_forecasts_feed_in_price": { attributes: { Forecasts: sell } } },
  { "sensor.amber_5min_current_general_price": { state: "0.31", attributes: {} },
    "sensor.amber_5min_current_feed_in_price": { state: "0.12", attributes: {} } }) });
// Amber's own shape: the interval under way isn't in the forecasts, and each starts a second past the boundary
const g = (i, raw) => ({ start_time: new Date(base + i * 1800000 + 1000).toISOString(), end_time: new Date(base + (i + 1) * 1800000).toISOString(),
  per_kwh: raw, advanced_price_low: raw - 0.02, advanced_price_predicted: raw + 0.01, advanced_price_high: raw + 0.03 });
window.BUY2 = Array.from({ length: 60 }, (_, i) => g(i + 1, 0.25 + (i % 2) * 0.1));
window.SELL2 = Array.from({ length: 60 }, (_, i) => g(i + 1, -0.10));
window.BUY = Array.from({ length: 60 }, (_, i) => f(i, 0.25));
window.SELL = Array.from({ length: 60 }, (_, i) => f(i, -0.10));
await import("/battmanfiles/battman-amber-forecast-chart.js");
const el = document.createElement("battman-amber-forecast-chart");
el.setConfig({ type: "custom:battman-amber-forecast-chart" });
document.getElementById("wrap").appendChild(el);
el.hass = mk(BUY, SELL);
window.el = el;
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
  const p = await browser.newPage({ viewport: { width: 800, height: 340 } });
  const errors = [];
  p.on("pageerror", (e) => errors.push(e.message));
  const url = `http://127.0.0.1:${server.address().port}/index.html`;
  await p.goto(url);
  await p.waitForFunction(() => window.el && window.Chart && window.Chart.getChart(window.el.shadowRoot.getElementById("c")), null, { timeout: 10000 });
  const out = {};
  const chartInfo = () => p.evaluate(() => {
    const r = el.shadowRoot, c = Chart.getChart(r.getElementById("c"));
    return { title: r.getElementById("titleEl").textContent, active: [...r.querySelectorAll(".pill.active")].map((b) => b.textContent),
      labels: c ? c.data.datasets.map((d) => d.label) : [], hidden: c ? c.data.datasets.filter((d, i) => !c.isDatasetVisible(i)).map((d) => d.label) : [],
      firstBuy: c ? c.data.datasets[0].data[0].y : null, firstSell: c ? c.data.datasets[4].data[0].y : null,
      sellLow: c ? c.data.datasets[6].data[0].y : null, sellHigh: c ? c.data.datasets[7].data[0].y : null,
      saved: JSON.parse(localStorage.getItem("battman.amberForecastChart")),
      msg: r.getElementById("msg").style.display === "none" ? "" : r.getElementById("msg").textContent };
  });
  out.first = await chartInfo();
  // tap "Buy Low" in the legend
  await p.evaluate(() => {
    const c = Chart.getChart(el.shadowRoot.getElementById("c"));
    const i = c.legend.legendItems.findIndex((it) => it.text === "Buy Low");
    const box = c.legend.legendHitBoxes[i];
    c.options.plugins.legend.onClick(null, c.legend.legendItems[i], c.legend);
    return box;
  });
  // and the 24h pill
  await p.evaluate(() => [...el.shadowRoot.querySelectorAll(".pill")].find((b) => b.textContent === "24h").click());
  out.afterTaps = await chartInfo();
  // tooltip over the middle of the chart: the interval's times
  const canvasBox = await p.evaluate(() => { const b = el.shadowRoot.getElementById("c").getBoundingClientRect(); return { x: b.x, y: b.y, w: b.width, h: b.height }; });
  await p.mouse.move(canvasBox.x + canvasBox.w * 0.3, canvasBox.y + canvasBox.h * 0.4);
  out.tooltip = await p.evaluate(() => {
    const t = Chart.getChart(el.shadowRoot.getElementById("c")).tooltip;
    return { title: t.title, lines: t.body.map((b) => b.lines.join(" ")) };
  });
  // a new page on this device: the range and hidden line come back
  await p.reload();
  await p.waitForFunction(() => window.el && window.Chart && window.Chart.getChart(window.el.shadowRoot.getElementById("c")), null, { timeout: 10000 });
  out.reloaded = await chartInfo();
  // problems are said, not papered over
  await p.evaluate(() => { el.hass = mk(BUY, null); });
  await p.waitForTimeout(100);
  out.missing = (await chartInfo()).msg;
  await p.evaluate(() => { el.hass = mk([], SELL); });
  await p.waitForTimeout(100);
  out.empty = (await chartInfo()).msg;
  await p.evaluate(() => { el.hass = mk(BUY, SELL, ""); });
  await p.waitForTimeout(100);
  out.noTz = (await chartInfo()).msg;
  await p.evaluate(() => { el.hass = mk(BUY, SELL); });
  await p.waitForTimeout(100);
  out.back = (await chartInfo()).msg;
  // Amber's own shape: current price until the first forecast, then no gaps; every line solid, its own colour
  await p.evaluate(() => { el.hass = mk(BUY2, SELL2); });
  await p.waitForTimeout(100);
  out.amberShape = await p.evaluate(() => {
    const c = Chart.getChart(el.shadowRoot.getElementById("c"));
    const ds = c.data.datasets;
    const firstFc = Date.parse(BUY2[0].start_time) - 1000;
    const gaps = (d) => d.data.filter((pt) => pt.x >= firstFc && pt.y === null).length;
    return { firstBuy: ds[0].data[0].y, firstSell: ds[4].data[0].y, firstPredicted: ds[1].data[0].y,
      gaps: ds.map(gaps), dashed: ds.filter((d) => d.borderDash && d.borderDash.length).length,
      colours: new Set(ds.map((d) => d.borderColor)).size };
  });
  out.picker = await p.evaluate(() => window.customCards.filter((c) => c.type === "battman-amber-forecast-chart").map((c) => ({ name: c.name, preview: c.preview })));
  out.errors = errors;
  console.log(JSON.stringify(out));
  await browser.close(); server.close();
})();
