// Real-browser check of <battman-forecast-view> and the dialog that shows it (run by tests/test_log_forecast.py).
// usage: NODE_PATH=<node_modules with playwright> CHROME=<chromium> node forecast_view_check.js <www dir>
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
const http = require("http");
(async () => {
  const www = process.argv[2];
  const server = http.createServer((req, res) => {
    const name = req.url.split("?")[0];
    const f = name === "/index.html" ? null : path.join(www, name);
    if (name === "/index.html") {
      res.setHeader("content-type", "text/html");
      return res.end(`<!doctype html><html><body><home-assistant></home-assistant>
<script type="module" src="battman-forecast-view.js"></script><script src="battman-lib.js"></script></body></html>`);
    }
    if (!fs.existsSync(f) || !fs.statSync(f).isFile()) { res.statusCode = 404; return res.end(); }
    res.setHeader("content-type", f.endsWith(".js") ? "text/javascript" : "text/html");
    res.end(fs.readFileSync(f));
  }).listen(0);
  const port = server.address().port;
  const browser = await chromium.launch({ executablePath: process.env.CHROME });
  const page = await browser.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(`http://127.0.0.1:${port}/index.html`);
  await page.waitForFunction(() => customElements.get("battman-forecast-view") && window.BattmanLib && window.BattmanLib.showPopup);
  const out = await page.evaluate(async () => {
    const wait = (f, ms = 4000) => new Promise((ok, no) => { const t0 = Date.now(); (function p() { try { if (f()) return ok(true); } catch (e) {} if (Date.now() - t0 > ms) return no(new Error("timeout waiting")); setTimeout(p, 50); })(); });
    const slot = (start, mode, o = {}) => Object.assign({ start, minutes: 30, mode, live: false, soc_start: 50, soc_end: 50, buy_price: 0.2, sell_price: 0.1,
      buy_line: 0.1, sell_line: 0.3, buy_below: 20, sell_above: 90, sell_price_known: true, buy_reason: "", sell_reason: "", money: 0, battery_kwh: 0,
      export_kwh: 0, import_kwh: 0, load_kw: 1, pv_kw: 0 }, o);
    const forecast = { generated: "2026-11-07T10:00:00+10:30", assumptions: ["a test forecast"], failed_slots: 0, total: { money: 1, soc_end: 70 },
      slots: [slot("2026-11-07T10:00:00+10:30", "Self Consume", { live: true }), slot("2026-11-07T10:30:00+10:30", "Self Consume"),
        slot("2026-11-07T11:00:00+10:30", "Discharge", { soc_start: 80, soc_end: 70, sell_price: 0.5, export_kwh: 2, battery_kwh: -3, money: 1, sell_reason: "Sell Above" })] };
    let calls = 0;
    const ha = document.querySelector("home-assistant");
    ha.hass = {
      config: { time_zone: "Australia/Adelaide" },
      states: { "sensor.sigen_plant_battery_state_of_charge": { state: "50", attributes: {} }, "sensor.battman_load_30m_avg": { state: "1.2", attributes: {} },
        "sensor.battman_parameters": { state: "x", attributes: {} }, "sensor.battman_run": { state: "x", attributes: {} } },
      callWS: async (m) => {
        if (m.type === "call_service") { calls++; return { response: forecast }; }
        return {};
      },
    };
    const r = {};
    const REMINDERS = ["What are you prepared to lose today? Set a limit.", "Imagine what you could be buying instead.", "You win some, you lose more.",
      "What are you really gambling with?", "Chances are you’re about to lose.", "Think. Is this a bet you really want to place?", "What’s gambling really costing you?"];
    // 1. the element on its own
    const el = document.createElement("battman-forecast-view");
    document.body.append(el);
    const sr = el.shadowRoot;
    await wait(() => sr.querySelectorAll(".row").length > 0);
    r.rows = sr.querySelectorAll(".row").length;
    r.title = sr.getElementById("title").textContent;
    r.total = sr.querySelector(".total").textContent.replace(/\s+/g, " ");
    r.reminderOk = REMINDERS.includes(sr.getElementById("gamble").textContent);
    r.sellRow = [...sr.querySelectorAll(".row")].some((x) => /Sell 2\.0 kWh/.test(x.textContent));
    r.callsBefore = calls;
    sr.querySelector('button[data-k="soc"][data-d="5"]').click();          // a what-if change
    await wait(() => calls >= 2 && sr.querySelector(".wrap").classList.contains("wi"), 5000);
    r.whatIf = sr.querySelector(".wrap").classList.contains("wi");
    r.callsAfter = calls;
    el.remove();
    // 2. in Battman's dialog
    window.BattmanLib.showPopup({ kind: "forecast" }, document.body);
    const dlg = document.querySelector("dialog.bm");
    r.dialogOpen = !!(dlg && dlg.open);
    const view = dlg && dlg.querySelector("battman-forecast-view");
    r.viewInDialog = !!view;
    await wait(() => view && view.shadowRoot.querySelectorAll(".row").length > 0);
    r.dialogRows = view.shadowRoot.querySelectorAll(".row").length;
    r.hasClose = !!dlg.querySelector("button.x");
    dlg.querySelector("button.x").click();
    await wait(() => !document.querySelector("dialog.bm"));
    r.closed = true;
    return r;
  });
  console.log(JSON.stringify({ ...out, errors }));
  await browser.close();
  server.close();
})().catch((e) => { console.error(e); process.exit(1); });
