// Battman Amber forecast chart: custom:battman-amber-forecast-chart. Amber's buy and sell price
// forecasts for the next 4, 8, 12 or 24 hours: the price, Amber Advanced's prediction and its low /
// high band, for each side, in c/kWh, each line solid in its own theme colour. Until the first
// forecast, the Price lines show Amber's current prices. Tap a name under the chart to hide or show that line; the range
// and the hidden lines are kept per device. From Amber's two forecast sensors (amber2mqtt), named
// directly (AMBER in battman-card-base.js); the figures are worked out in battman-amber-forecast-data.js.

import { AMBER, BattmanCardBase, battmanDefine, battmanPicker, cssVar, loadChartJs, missingEntities, missingThemeVars } from "./battman-card-base.js";
import { RANGES_H, SERIES, covering, forecastSeries } from "./battman-amber-forecast-data.js";

const NEED_ENTITIES = ["buy_forecast", "feed_in_forecast", "buy_price", "feed_in_price"];
// each line's theme colour: Buy in the warm colours, Sell in the cool ones
const LINE_COLOR = {
  buy: "--battman-amber", buy_predicted: "--battman-orange", buy_low: "--battman-yellow", buy_high: "--battman-red",
  sell: "--battman-green", sell_predicted: "--battman-teal", sell_low: "--battman-sky", sell_high: "--battman-blue",
};
const THEME_VARS = Object.values(LINE_COLOR);
const SAVE_KEY = "battman.amberForecastChart";
const DEFAULT_RANGE_H = 8;
const TICK_H = { 4: 0.5, 8: 1, 12: 2, 24: 3 };   // hours between time labels, per range

// every line solid; Price a little heavier, Low / High a little lighter
const WIDTH = { per_kwh: 2.5, predicted: 2, low: 1.5, high: 1.5 };
const kindOf = (sd) => sd.id.endsWith("_predicted") ? "predicted" : sd.id.endsWith("_low") ? "low" : sd.id.endsWith("_high") ? "high" : "per_kwh";

class BattmanAmberForecastChartCard extends BattmanCardBase {
  static cardName = "Battman Amber forecast chart";
  static preview = "amber-forecast-chart.webp";
  static gridOptions = { columns: "full", rows: 8 };
  static css = `
    :host { display: block; height: 100%; }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    button { font-family: inherit; }
    ha-card { height: 100%; min-height: 320px; display: flex; flex-direction: column; overflow: hidden;
      background: var(--card-background-color); border: 1px solid var(--divider-color); border-radius: 12px;
      color: var(--primary-text-color); box-shadow: none; font-size: 16px; line-height: normal;
      font-family: var(--primary-font-family, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif); }
    .head { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; justify-content: space-between;
      padding: 10px 16px; border-bottom: 1px solid var(--divider-color); }
    .title { font-size: 13px; font-weight: 700; letter-spacing: 0.09em; text-transform: uppercase; }
    .pills { display: flex; flex-wrap: wrap; gap: 6px; }
    .pill { padding: 5px 12px; border: 1px solid var(--divider-color); border-radius: 999px; background: transparent;
      color: var(--secondary-text-color); font: inherit; font-size: 12px; font-weight: 600; line-height: 1; cursor: pointer;
      -webkit-tap-highlight-color: transparent; transition: background .12s ease, border-color .12s ease, color .12s ease; }
    .pill:hover { color: var(--primary-text-color); }
    .pill.active { background: var(--primary-color); border-color: var(--primary-color); color: #fff; }
    .chartWrap { flex: 1; position: relative; padding: 10px 10px 6px; min-height: 0; }
    .msg { padding: 24px; text-align: center; color: var(--secondary-text-color); font-size: 14px; }
  `;
  static html = `
    <ha-card>
      <div class="head">
        <span class="title" id="titleEl">Amber Price Forecast</span>
        <div class="pills" id="pills"></div>
      </div>
      <div class="chartWrap"><canvas id="c"></canvas><div class="msg" id="msg" style="display:none"></div></div>
    </ha-card>`;

  run(root) {
    const card = this;
    const $ = (id) => root.getElementById(id);
    let Chart = null, chart = null, chartProblem = "", FATAL = null, started = false, timer = null;
    let COL = {}, rangeH = DEFAULT_RANGE_H, hidden = new Set(), lastSeries = null;

    // ---- kept per device: the range and the hidden lines ----
    function load() {
      try {
        const s = JSON.parse(localStorage.getItem(SAVE_KEY));
        if (s && RANGES_H.includes(s.range)) rangeH = s.range;
        if (s && Array.isArray(s.hidden)) hidden = new Set(s.hidden.filter((id) => SERIES.some((sd) => sd.id === id)));
      } catch (e) { /* nothing kept yet, or storage blocked: defaults */ }
    }
    function save() {
      try { localStorage.setItem(SAVE_KEY, JSON.stringify({ range: rangeH, hidden: [...hidden] })); } catch (e) {}
    }

    // ---- colours: one theme colour per line (LINE_COLOR) ----
    function readColors() {
      const c = (v) => cssVar(card, v);
      COL = { grid: c("--divider-color"), muted: c("--secondary-text-color"), text: c("--primary-text-color") };
      for (const id in LINE_COLOR) COL[id] = c(LINE_COLOR[id]);
      const ff = c("--primary-font-family"); if (ff && Chart) Chart.defaults.font.family = ff;
    }

    // ---- times, in HA's time zone (the same clock as Battman's Amber price grid and table) ----
    let fmtHM = null, fmtDay = null, fmtDayHM = null;
    function makeFormats(tz) {
      fmtHM = new Intl.DateTimeFormat([], { timeZone: tz, hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
      fmtDay = new Intl.DateTimeFormat([], { timeZone: tz, weekday: "short" });
      fmtDayHM = new Intl.DateTimeFormat([], { timeZone: tz, weekday: "short", hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
    }
    // HA's time zone's offset from UTC at ms (so the time labels land on its whole hours)
    function tzOffsetMs(ms) {
      const p = {};
      new Intl.DateTimeFormat("en-US", { timeZone: card.hass.config.time_zone, hourCycle: "h23", year: "numeric", month: "2-digit",
        day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" }).formatToParts(ms).forEach((x) => { p[x.type] = x.value; });
      return Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour, +p.minute, +p.second) - Math.floor(ms / 1000) * 1000;
    }
    const tickLabel = (ms) => { const hm = fmtHM.format(ms); return hm === "00:00" ? fmtDay.format(ms) : hm; };
    const cents = (v) => (Math.round(v * 100) / 100).toFixed(2) + "c";

    // ---- range pills ----
    function buildPills() {
      $("pills").innerHTML = RANGES_H.map((h) => `<button class="pill" data-h="${h}">${h}h</button>`).join("");
      root.querySelectorAll(".pill").forEach((b) => { b.onclick = () => { rangeH = Number(b.dataset.h); save(); syncPills(); render(); }; });
      syncPills();
    }
    function syncPills() {
      root.querySelectorAll(".pill").forEach((b) => b.classList.toggle("active", Number(b.dataset.h) === rangeH));
      $("titleEl").textContent = `Amber Price Forecast · next ${rangeH} hours`;
    }

    function showMsg(m) { const e = $("msg"); e.style.display = ""; e.textContent = m; $("c").style.display = "none"; if (chart) { chart.destroy(); chart = null; } }
    function hideMsg() { $("msg").style.display = "none"; $("c").style.display = ""; }

    function check() {
      FATAL = missingThemeVars(card, THEME_VARS) || missingEntities(card.hass, AMBER, NEED_ENTITIES);
      if (!FATAL && !(card.hass.config && card.hass.config.time_zone)) FATAL = "Home Assistant has no time zone set (Settings → System → General).";
      return FATAL;
    }

    function datasets(S) {
      return SERIES.map((sd) => {
        const color = COL[sd.id];
        return {
          label: sd.label, sid: sd.id, hidden: hidden.has(sd.id),
          data: S.times.map((t, i) => ({ x: t, y: S.data[sd.id][i] })),
          borderColor: color, backgroundColor: color, borderWidth: WIDTH[kindOf(sd)],
          pointRadius: 0, pointHoverRadius: 3, stepped: "after", spanGaps: false,
        };
      });
    }

    // the interval the tooltip is in: "Tue 14:30 – 15:00"
    function tooltipTitle(items) {
      if (!items.length || !lastSeries) return "";
      const t = items[0].parsed.x;
      const iv = covering(lastSeries.buyIv, t, false) || covering(lastSeries.sellIv, t, false);
      if (iv) return fmtDayHM.format(iv.s) + " – " + fmtHM.format(iv.e);
      const first = Math.min(...[lastSeries.buyIv, lastSeries.sellIv].filter((x) => x.length).map((x) => x[0].s));
      return t < first ? "Now – " + fmtHM.format(first) + " (current price)" : fmtDayHM.format(t);
    }

    function render() {
      if (check()) return showMsg(FATAL);
      if (!Chart) return showMsg("Chart library unavailable: " + chartProblem);
      readColors();
      makeFormats(card.hass.config.time_zone);
      const buyF = card.hass.states[AMBER.buy_forecast].attributes.Forecasts;
      const sellF = card.hass.states[AMBER.feed_in_forecast].attributes.Forecasts;
      if (!Array.isArray(buyF) || !buyF.length || !Array.isArray(sellF) || !sellF.length) {
        return showMsg("No Amber forecasts yet (Forecasts is empty on " + AMBER.buy_forecast + " or " + AMBER.feed_in_forecast + ").");
      }
      const now = Date.now(), end = now + rangeH * 3600000;
      const cur = (k) => card.hass.states[AMBER[k]].state;
      const S = forecastSeries(buyF, sellF, now, end, { buy: cur("buy_price"), sell: cur("feed_in_price") });
      lastSeries = S;
      hideMsg();
      const stepMs = TICK_H[rangeH] * 3600000;
      const cfg = {
        type: "line",
        data: { datasets: datasets(S) },
        options: {
          responsive: true, maintainAspectRatio: false, animation: false, parsing: false, normalized: true,
          layout: { padding: { top: 4, bottom: 0 } },
          interaction: { mode: "index", intersect: false },
          plugins: {
            legend: {
              display: true, position: "bottom",
              labels: { color: COL.muted, boxWidth: 18, boxHeight: 2, padding: 9 },
              // tap a name: hide / show that line, and keep it that way on this device
              onClick: (e, item, legend) => {
                const ds = legend.chart.data.datasets[item.datasetIndex];
                if (hidden.has(ds.sid)) hidden.delete(ds.sid); else hidden.add(ds.sid);
                ds.hidden = hidden.has(ds.sid);
                save();
                legend.chart.update("none");
              },
            },
            tooltip: {
              mode: "index", intersect: false,
              filter: (it) => it.parsed.y !== null && it.parsed.y !== undefined,
              callbacks: {
                title: tooltipTitle,
                label: (c) => " " + c.dataset.label + ": " + cents(c.parsed.y),
              },
            },
          },
          scales: {
            x: {
              type: "linear", min: now, max: end,
              afterBuildTicks: (axis) => {
                // on whole hours / half hours of HA's clock (Adelaide is +10:30), not at "now"
                const off = tzOffsetMs(now);
                const first = Math.ceil((now + off) / stepMs) * stepMs - off;
                const ticks = [];
                for (let t = first; t <= end; t += stepMs) ticks.push({ value: t });
                axis.ticks = ticks;
              },
              ticks: { color: COL.muted, maxRotation: 0, autoSkip: true, callback: (v) => tickLabel(v) },
              grid: { display: false },
            },
            y: {
              title: { display: true, text: "c/kWh", color: COL.muted },
              ticks: { color: COL.muted, callback: (v) => v + "c" },
              grid: { color: (ctx) => ctx.tick && ctx.tick.value === 0 ? COL.muted : COL.grid },
            },
          },
        },
      };
      if (chart) chart.destroy();
      chart = new Chart($("c").getContext("2d"), cfg);
    }

    (async function start() {
      try { Chart = await loadChartJs(); } catch (e) { chartProblem = e.message; }
      load();
      buildPills();
      started = true;
      render();
      if (card.isConnected) resume();
    })();

    // "now" moves: redrawn every minute, and when either forecast sensor changes
    function resume() { if (started && !timer) timer = setInterval(render, 60000); }
    function pause() { clearInterval(timer); timer = null; }
    let lastRetry = 0;
    function hassChanged(old) {
      if (!started) return;
      const changed = NEED_ENTITIES.some((k) => !old || old.states[AMBER[k]] !== card.hass.states[AMBER[k]]);
      if (changed) return render();
      // showing a problem: look again, no more than every 2 s
      if (FATAL && Date.now() - lastRetry > 2000) { lastRetry = Date.now(); render(); }
    }
    return { resume, pause, hassChanged, themeChanged: () => { if (started) render(); } };
  }
}
battmanDefine("battman-amber-forecast-chart", BattmanAmberForecastChartCard);
battmanPicker("battman-amber-forecast-chart", "Battman Amber forecast chart",
  "Amber's buy and sell price forecasts (price, predicted, low and high) for the next 4 to 24 hours; tap a name to hide a line.",
  "battman-amber-forecast-chart");
