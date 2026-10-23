// Battman Cost chart: custom:battman-cost-chart. Each day's cost (fee + buy) and sell as stacked
// bars with the day's net above, for 5 to 30 days or a bill cycle (or dates you pick), with
// today's sell and buy, this and last bill, and lifetime figures on top. From the cost totals'
// long-term statistics (battman-cost-data.js). The range you pick is kept per device.

import { BattmanCardBase, battmanDefine, battmanMap, battmanPicker, cssVar, loadChartJs, missingEntities, missingThemeVars } from "./battman-card-base.js";
import { costData, fromDateStr, midnight, money, num, toDateStr } from "./battman-cost-data.js";

const NEEDS = ["buy_total", "sell_total", "network_fee_total", "parameters", "grid_export_today", "grid_import_today"];
const THEME_VARS = ["--battman-green", "--battman-amber", "--battman-red"];
const DAY_PILLS = [5, 10, 14, 20, 30];
const RANGE_KEY = "battman.costRange";

// contrast: dark or light label text for a bar colour
function parseColor(s) {
  if (!s) return null; s = String(s).trim();
  if (s[0] === "#") { let h = s.slice(1); if (h.length === 3) h = h.split("").map((x) => x + x).join(""); if (h.length >= 6) return { r: parseInt(h.slice(0, 2), 16), g: parseInt(h.slice(2, 4), 16), b: parseInt(h.slice(4, 6), 16) }; }
  const m = s.match(/rgba?\(([^)]+)\)/); if (m) { const p = m[1].split(",").map(Number); return { r: p[0], g: p[1], b: p[2] }; }
  return null;
}
function roundRectPath(ctx, x, y, w, h, r) {
  if (ctx.roundRect) { ctx.beginPath(); ctx.roundRect(x, y, w, h, r); return; }
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

class BattmanCostChartCard extends BattmanCardBase {
  static cardName = "Battman Cost chart";
  static preview = "cost-chart.webp";
  static gridOptions = { columns: "full", rows: 9 };
  static css = `
    :host { display: block; height: 100%; }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    input, button { font-family: inherit; }
    ha-card { height: 100%; min-height: 340px; display: flex; flex-direction: column; overflow: hidden; container-type: inline-size;
      background: var(--card-background-color); border: 1px solid var(--divider-color); border-radius: 12px;
      color: var(--primary-text-color); box-shadow: none; font-size: 16px; line-height: normal;
      font-family: var(--primary-font-family, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif); }
    .title { padding: 12px 16px; font-size: 13px; font-weight: 700; letter-spacing: 0.09em; text-transform: uppercase;
      border-bottom: 1px solid var(--divider-color); }
    .stats { display: flex; flex-wrap: wrap; gap: 10px 18px; justify-content: space-between; align-items: center;
      padding: 12px 22px; border-bottom: 1px solid var(--divider-color); }
    .stat { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
    .stat .k { font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--secondary-text-color); }
    .stat .v { font-size: 21px; font-weight: 700; font-variant-numeric: tabular-nums; white-space: nowrap; }
    .statbreak { display: none; }
    @container (max-width: 640px) { .statbreak { display: block; flex-basis: 100%; height: 0; } }
    .chartWrap { flex: 1; position: relative; padding: 10px 10px 6px; min-height: 0; }
    .msg { padding: 24px; text-align: center; color: var(--secondary-text-color); font-size: 14px; }
    .controls { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; justify-content: space-between;
      padding: 10px 16px; border-bottom: 1px solid var(--divider-color); }
    .pills { display: flex; flex-wrap: wrap; gap: 6px; }
    .pill { padding: 5px 12px; border: 1px solid var(--divider-color); border-radius: 999px; background: transparent;
      color: var(--secondary-text-color); font: inherit; font-size: 12px; font-weight: 600; line-height: 1; cursor: pointer;
      -webkit-tap-highlight-color: transparent; transition: background .12s ease, border-color .12s ease, color .12s ease; }
    .pill:hover { color: var(--primary-text-color); }
    .pill.active { background: var(--primary-color); border-color: var(--primary-color); color: #fff; }
    .dates { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
    .dates label { display: flex; align-items: center; gap: 5px; font-size: 12px; color: var(--secondary-text-color); }
    .dates input[type="date"] { background: var(--primary-background-color); color: var(--primary-text-color);
      border: 1px solid var(--divider-color); border-radius: 8px; padding: 5px 8px; font: inherit; font-size: 12px; color-scheme: dark; }
  `;
  static html = `
    <ha-card>
      <div class="title" id="titleEl">Last 10 Days Activity</div>
      <div class="controls">
        <div class="pills" id="pills"></div>
        <div class="dates">
          <label>From <input type="date" id="fromDt"></label>
          <label>To <input type="date" id="toDt"></label>
        </div>
      </div>
      <div class="stats" id="stats"></div>
      <div class="chartWrap"><canvas id="c"></canvas><div class="msg" id="msg" style="display:none"></div></div>
    </ha-card>`;

  run(root) {
    const card = this;
    const $ = (id) => root.getElementById(id);
    let M = null, data = null, Chart = null, chart = null, chartProblem = "", FATAL = null, started = false;
    let curStart = null, curEnd = null, curKey = null;   // first / last day shown; active pill ('days:N' | 'cycle:0' | 'cycle:1' | 'custom')
    let COL = {};
    const timers = [];

    function readColors() {
      const c = (v) => cssVar(card, v);
      COL = { green: c("--battman-green"), amber: c("--battman-amber"), red: c("--battman-red"),
              grid: c("--divider-color"), muted: c("--secondary-text-color"), text: c("--primary-text-color") };
      const ff = c("--primary-font-family"); if (ff && Chart) Chart.defaults.font.family = ff;
    }
    const barColor = (v) => v < 0 ? COL.red : (v < 2 ? COL.amber : COL.green);
    function labelColor(bg) {
      const c = parseColor(bg); if (!c) return COL.text;
      const L = 0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b;   // 0..255
      return L > 140 ? "#141414" : "#f5f5f5";
    }

    // ---- header stats ----
    function renderStats() {
      const S = (id) => card.hass.states[id];
      const sell = S(M.sell_total), buy = S(M.buy_total), P = S(M.parameters), feeS = S(M.network_fee_total);
      if (!sell || !buy || !P) return;
      const expKwh = num(S(M.grid_export_today) && S(M.grid_export_today).state);
      const impKwh = num(S(M.grid_import_today) && S(M.grid_import_today).state);
      const sellDay = num(sell.attributes.day), buyDay = num(buy.attributes.day);
      const sellAvg = expKwh > 0 ? sellDay / expKwh : 0, buyAvg = impKwh > 0 ? buyDay / impKwh : 0;
      const thisBill = num(sell.attributes.bill) - num(buy.attributes.bill) - num(feeS && feeS.attributes.bill);
      const lastBill = num(sell.attributes.bill_last) - num(buy.attributes.bill_last) - num(feeS && feeS.attributes.bill_last);
      const withAmber = num(P.attributes.energyIncome) + num(sell.state) - num(buy.state) - num(feeS && feeS.state);
      const sgn = (v) => v >= 0 ? COL.green : COL.red;
      const items = [
        { k: "Today Sell", v: `${expKwh.toFixed(2)} kWh @ $${sellAvg.toFixed(2)}`, c: COL.green },
        { k: "Today Buy", v: `${impKwh.toFixed(2)} kWh @ $${buyAvg.toFixed(2)}`, c: COL.amber },
        { brk: true },
        { k: "This Bill", v: money(thisBill), c: sgn(thisBill) },
        { k: "Last Bill", v: money(lastBill), c: sgn(lastBill) },
        { k: "Lifetime", v: money(withAmber), c: sgn(withAmber) },
      ];
      const html = items.map((it) => it.brk ? '<div class="statbreak"></div>'
        : `<div class="stat"><span class="k">${it.k}</span><span class="v" style="color:${it.c}">${it.v}</span></div>`).join("");
      if ($("stats").innerHTML !== html) $("stats").innerHTML = html;
    }

    // ---- range: pills (N days ending today), a bill cycle, or From / To ----
    function saveRange(v) { try { localStorage.setItem(RANGE_KEY, JSON.stringify(v)); } catch (e) {} }
    function loadRange() {
      try {
        // one-time move of the range saved by the old Smiggles page
        const old = localStorage.getItem("costRange");
        if (old !== null) { if (localStorage.getItem(RANGE_KEY) === null) localStorage.setItem(RANGE_KEY, old); localStorage.removeItem("costRange"); }
        return JSON.parse(localStorage.getItem(RANGE_KEY));
      } catch (e) { return null; }
    }
    function daysRange(n) {
      const end = midnight(new Date());
      const start = new Date(end); start.setDate(start.getDate() - (n - 1));
      return { start, end, key: "days:" + n };
    }
    function cycleRange(back) {
      const today = midnight(new Date());
      const start = data.cycleStart(today, back);
      let end;
      if (back === 0) end = today;
      else { end = data.cycleStart(today, 0); end.setDate(end.getDate() - 1); }   // day before the current cycle
      return { start, end, key: "cycle:" + back };
    }
    function applyRange(start, end, key) { curStart = start; curEnd = end; curKey = key; syncControls(); }
    function setDaysMode(n) { const r = daysRange(n); applyRange(r.start, r.end, r.key); saveRange({ mode: "days", n }); render(); }
    function setCycleMode(back) { const r = cycleRange(back); applyRange(r.start, r.end, r.key); saveRange({ mode: "cycle", back }); render(); }
    function setCustomRange(from, to) {
      let s = midnight(from), e = midnight(to);
      if (e < s) { const t = s; s = e; e = t; }
      applyRange(s, e, "custom");
      saveRange({ mode: "custom", from: toDateStr(s), to: toDateStr(e) });
      render();
    }
    const PILLS = [
      ...DAY_PILLS.map((n) => ({ key: "days:" + n, label: n + "d", fn: () => setDaysMode(n) })),
      { key: "cycle:0", label: "This cycle", fn: () => setCycleMode(0) },
      { key: "cycle:1", label: "Last cycle", fn: () => setCycleMode(1) },
    ];
    function syncControls() {
      root.querySelectorAll(".pill").forEach((b) => b.classList.toggle("active", b.dataset.key === curKey));
      const from = $("fromDt"), to = $("toDt"), today = toDateStr(midnight(new Date()));
      from.max = today; to.max = today;
      from.value = toDateStr(curStart); to.value = toDateStr(curEnd);
      const t = $("titleEl");
      if (curKey === "cycle:0") t.textContent = "This Bill Cycle";
      else if (curKey === "cycle:1") t.textContent = "Last Bill Cycle";
      else if (curKey && curKey.indexOf("days:") === 0) t.textContent = "Last " + curKey.slice(5) + " Days Activity";
      else { const f = (d) => d.toLocaleDateString([], { day: "2-digit", month: "short" }); t.textContent = f(curStart) + " – " + f(curEnd); }
    }
    function buildControls() {
      $("pills").innerHTML = PILLS.map((p) => '<button class="pill" data-key="' + p.key + '">' + p.label + "</button>").join("");
      root.querySelectorAll(".pill").forEach((b) => { const p = PILLS.find((x) => x.key === b.dataset.key); if (p) b.onclick = p.fn; });
      const onDate = () => { const f = $("fromDt").value, tv = $("toDt").value; if (f && tv) setCustomRange(fromDateStr(f), fromDateStr(tv)); };
      $("fromDt").addEventListener("change", onDate);
      $("toDt").addEventListener("change", onDate);
    }
    function initRange() {
      const saved = loadRange();
      if (saved && saved.mode === "custom" && saved.from && saved.to) {
        let s = midnight(fromDateStr(saved.from)), e = midnight(fromDateStr(saved.to));
        if (e < s) { const t = s; s = e; e = t; }
        applyRange(s, e, "custom"); return;
      }
      if (saved && saved.mode === "cycle" && (saved.back === 0 || saved.back === 1)) { const r = cycleRange(saved.back); applyRange(r.start, r.end, r.key); return; }
      // a phone-sized card starts on 5 days, a wider one on 10
      const narrow = card.getBoundingClientRect().width <= 640;
      const n = (saved && saved.mode === "days" && DAY_PILLS.includes(saved.n)) ? saved.n : (narrow ? 5 : 10);
      const r = daysRange(n); applyRange(r.start, r.end, r.key);
    }

    // the day's net above each stack
    const totalsPlugin = {
      id: "stackTotals",
      afterDatasetsDraw(c) {
        const { ctx, scales: { y } } = c;
        const meta = c.getDatasetMeta(0);
        if (!meta || !meta.data) return;
        const n = c.data.labels.length;
        const avail = n > 0 ? c.chartArea.width / n : 0;   // horizontal space per bar
        ctx.save();
        ctx.textAlign = "center"; ctx.textBaseline = "middle";
        for (let i = 0; i < n; i++) {
          const el = meta.data[i]; if (!el) continue;
          let total = 0, pos = 0;
          c.data.datasets.forEach((ds) => { const v = Number(ds.data[i]) || 0; total += v; if (v > 0) pos += v; });
          const fs = Math.max(11, Math.min(22, Math.round((el.width || 0) * 0.22)));
          ctx.font = "800 " + fs + 'px "Segoe UI", Roboto, sans-serif';
          const txt = money(total);
          const boxH = fs + 6;
          const cx = el.x, cy = y.getPixelForValue(pos) - (boxH / 2) - 4;
          const boxW = ctx.measureText(txt).width + 12, bg = total >= 0 ? COL.green : COL.red;
          if (boxW > avail - 2) continue;   // would overlap the next bar's badge: hidden (the tooltip has it)
          roundRectPath(ctx, cx - boxW / 2, cy - boxH / 2, boxW, boxH, 4);
          ctx.fillStyle = bg; ctx.fill();
          ctx.fillStyle = labelColor(bg);
          ctx.fillText(txt, cx, cy);
        }
        ctx.restore();
      },
    };
    // each segment's $ inside it, only when it fits
    const segLabelsPlugin = {
      id: "segLabels",
      afterDatasetsDraw(c) {
        const ctx = c.ctx;
        ctx.save();
        ctx.textAlign = "center"; ctx.textBaseline = "middle";
        [0, 1].forEach((di) => {                     // dataset 0 = Cost (fee + buy), 1 = Sell
          const meta = c.getDatasetMeta(di); if (!meta || meta.hidden || !meta.data) return;
          const ds = c.data.datasets[di];
          meta.data.forEach((el, i) => {
            if (!el) return;
            const v = Number(ds.data[i]);
            if (!isFinite(v) || Math.abs(v) < 0.005) return;
            const w = el.width || 0;
            const base = (el.base != null) ? el.base : el.y;
            const h = Math.abs(base - el.y);
            const fs = Math.max(10, Math.min(18, Math.round(w * 0.20)));
            ctx.font = "700 " + fs + 'px "Segoe UI", Roboto, sans-serif';
            const txt = money(v);
            const tw = ctx.measureText(txt).width;
            if (h < fs + 2 || w < tw + 4) return;   // doesn't fit: skipped (the tooltip has it)
            const cx = el.x, cy = (el.y + base) / 2;
            const bw = tw + 8, bh = fs + 4;
            roundRectPath(ctx, cx - bw / 2, cy - bh / 2, bw, bh, 3);
            ctx.fillStyle = "rgba(20,20,20,0.55)"; ctx.fill();
            ctx.fillStyle = "#f5f5f5"; ctx.fillText(txt, cx, cy);
          });
        });
        ctx.restore();
      },
    };

    function showMsg(m) { const e = $("msg"); e.style.display = ""; e.textContent = m; $("c").style.display = "none"; }
    function hideMsg() { $("msg").style.display = "none"; $("c").style.display = ""; }

    function check() {
      FATAL = missingThemeVars(card, THEME_VARS) || missingEntities(card.hass, M, NEEDS);
      return FATAL;
    }

    async function render() {
      if (check()) return showMsg(FATAL);
      if (!Chart) return showMsg("Chart library unavailable: " + chartProblem);
      readColors();
      const maps = await data.days(curStart, curEnd);
      if (!maps) return showMsg("History unavailable");
      hideMsg();
      const days = [], buy = [], sell = [], fee = [];
      for (const d = new Date(curStart); d <= curEnd; d.setDate(d.getDate() + 1)) {
        const v = data.day(maps, d);
        days.push(new Date(d)); buy.push(v.buy); sell.push(v.sell); fee.push(v.fee);
      }
      const labels = days.map((d) => d.toLocaleDateString([], { day: "2-digit", month: "short" }));
      // Fee + Buy are one "Cost" segment; the tooltip still breaks them out
      const costArr = days.map((_, i) => -((fee[i] || 0) + (buy[i] || 0)));
      const mk = (label, arr) => ({ label, data: arr, stack: "day", backgroundColor: (ctx) => barColor(ctx.raw), borderWidth: 0,
                                     borderRadius: 3, maxBarThickness: 80 });
      const cfg = {
        type: "bar",
        data: { labels, datasets: [mk("Cost", costArr), mk("Sell", sell.slice())] },
        options: {
          responsive: true, maintainAspectRatio: false, animation: false,
          layout: { padding: { top: 36, bottom: 20 } },
          interaction: { mode: "index", intersect: false },
          plugins: {
            legend: { display: false },
            tooltip: {
              mode: "index", intersect: false, displayColors: false,
              filter: (it) => Math.abs(Number(it.raw)) >= 0.005,
              callbacks: {
                // Cost is one bar, broken back out here into Fee / Buy / Sell
                label: (c) => {
                  if (c.dataset.label !== "Cost") return null;
                  const i = c.dataIndex;
                  return [" Fee: " + money(-(fee[i] || 0)), " Buy: " + money(-(buy[i] || 0)), " Sell: " + money(sell[i] || 0)];
                },
                footer: (items) => {
                  const i = items.length ? items[0].dataIndex : 0;
                  return "Net: " + money((sell[i] || 0) - (buy[i] || 0) - (fee[i] || 0));
                },
              },
            },
          },
          scales: {
            x: { stacked: true, ticks: { color: COL.muted }, grid: { display: false } },
            y: { stacked: true, ticks: { color: COL.muted, callback: (v) => money(v) }, grid: { color: COL.grid } },
          },
        },
        plugins: [totalsPlugin, segLabelsPlugin],
      };
      if (chart) chart.destroy();
      chart = new Chart($("c").getContext("2d"), cfg);
    }

    (async function start() {
      try { M = await battmanMap(card.hass, NEEDS); } catch (e) { return card.problem(e.message); }
      try { Chart = await loadChartJs(); } catch (e) { chartProblem = e.message; }
      data = costData(() => card.hass, { buy: M.buy_total, sell: M.sell_total, fee: M.network_fee_total, param: M.parameters });
      readColors();
      buildControls();
      initRange();
      if (!check()) renderStats();
      started = true;
      render();
      if (card.isConnected) resume();
    })();

    function resume() {
      if (!started || timers.length) return;
      timers.push(setInterval(render, 60000));
    }
    function pause() { timers.splice(0).forEach(clearInterval); }
    // HA hands the card every state change; the figures on top need no more than every 2 s
    let lastCheck = 0;
    function hassChanged() {
      if (!started || Date.now() - lastCheck < 2000) return;
      lastCheck = Date.now();
      const was = FATAL;
      if (check()) return showMsg(FATAL);
      renderStats();
      if (was) render();
    }
    return { resume, pause, hassChanged, themeChanged: () => { if (started) { readColors(); renderStats(); render(); } } };
  }
}
battmanDefine("battman-cost-chart", BattmanCostChartCard);
battmanPicker("battman-cost-chart", "Battman Cost chart",
  "Daily buy, sell and net cost, with today's figures and this / last bill.", "battman-cost-chart");
