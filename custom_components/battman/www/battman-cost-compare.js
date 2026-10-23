// Battman Cost compare: custom:battman-cost-compare. This bill cycle against the last one, as the
// running net cost ($) day by day from the bill day, with how far ahead or behind you are today.
// From the cost totals' long-term statistics (battman-cost-data.js). Refreshes every minute.

import { BattmanCardBase, battmanDefine, battmanMap, battmanPicker, cssVar, loadChartJs, missingEntities, missingThemeVars } from "./battman-card-base.js";
import { costData, midnight, money } from "./battman-cost-data.js";

const NEEDS = ["buy_total", "sell_total", "network_fee_total", "parameters"];
const THEME_VARS = ["--battman-green", "--battman-amber", "--battman-red"];

class BattmanCostCompareCard extends BattmanCardBase {
  static cardName = "Battman Cost compare";
  static preview = "cost-compare.webp";
  static gridOptions = { columns: "full", rows: 8 };
  static css = `
    :host { display: block; height: 100%; }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    ha-card { height: 100%; min-height: 300px; display: flex; flex-direction: column; overflow: hidden;
      background: var(--card-background-color); border: 1px solid var(--divider-color); border-radius: 12px;
      color: var(--primary-text-color); box-shadow: none; font-size: 16px; line-height: normal;
      font-family: var(--primary-font-family, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif); }
    .head { display: flex; flex-wrap: wrap; gap: 4px 16px; align-items: baseline; justify-content: space-between;
      padding: 12px 16px; border-bottom: 1px solid var(--divider-color); }
    .title { font-size: 13px; font-weight: 700; letter-spacing: 0.09em; text-transform: uppercase; }
    .delta { font-size: 13px; font-weight: 700; font-variant-numeric: tabular-nums; }
    .sub { flex-basis: 100%; font-size: 11px; color: var(--secondary-text-color); }
    .chartWrap { flex: 1; position: relative; padding: 10px 10px 6px; min-height: 0; }
    .msg { padding: 24px; text-align: center; color: var(--secondary-text-color); font-size: 14px; }
  `;
  static html = `
    <ha-card>
      <div class="head">
        <span class="title">This vs Last Cycle · cumulative $</span>
        <span class="delta" id="delta"></span>
        <span class="sub" id="sub"></span>
      </div>
      <div class="chartWrap"><canvas id="c"></canvas><div class="msg" id="msg" style="display:none"></div></div>
    </ha-card>`;

  run(root) {
    const card = this;
    const $ = (id) => root.getElementById(id);
    const col = (v) => cssVar(card, v);
    let M = null, data = null, Chart = null, chart = null, timer = null, FATAL = null, started = false;

    function showMsg(m) { const e = $("msg"); e.style.display = ""; e.textContent = m; $("c").style.display = "none"; }
    function hideMsg() { $("msg").style.display = "none"; $("c").style.display = ""; }
    const fmtD = (d) => d.toLocaleDateString([], { day: "2-digit", month: "short" });

    // cumulative net ($) per day-of-cycle over [start..end]
    function cumulative(maps, start, end) {
      const out = []; let run = 0;
      const d = new Date(start);
      while (d <= end) {
        const v = data.day(maps, d);
        run += v.sell - v.buy - v.fee;
        out.push(Number(run.toFixed(2)));
        d.setDate(d.getDate() + 1);
      }
      return out;
    }

    // faint vertical marker at today's day-of-cycle, so the same point on last cycle is obvious
    const markerPlugin = (idx) => ({
      id: "todayMark",
      afterDatasetsDraw(c) {
        if (idx < 0) return;
        const x = c.scales.x.getPixelForValue(idx);
        const ctx = c.ctx; ctx.save();
        ctx.strokeStyle = col("--secondary-text-color"); ctx.globalAlpha = 0.5; ctx.setLineDash([4, 4]); ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(x, c.chartArea.top); ctx.lineTo(x, c.chartArea.bottom); ctx.stroke();
        ctx.restore();
      },
    });

    async function render() {
      FATAL = missingThemeVars(card, THEME_VARS) || missingEntities(card.hass, M, NEEDS);
      if (FATAL) return showMsg(FATAL);
      if (!Chart) return showMsg("Chart library unavailable: " + chartProblem);
      const today = midnight(new Date());
      const thisStart = data.cycleStart(today, 0), lastStart = data.cycleStart(today, 1);
      const lastEnd = new Date(thisStart); lastEnd.setDate(lastEnd.getDate() - 1);
      const maps = await data.days(lastStart, today);
      if (!maps) return showMsg("History unavailable");
      hideMsg();
      const thisCum = cumulative(maps, thisStart, today), lastCum = cumulative(maps, lastStart, lastEnd);
      const C = { accent: col("--primary-color"), amber: col("--battman-amber"), green: col("--battman-green"),
                  red: col("--battman-red"), grid: col("--divider-color"), muted: col("--secondary-text-color"), text: col("--primary-text-color") };
      const ff = col("--primary-font-family"); if (ff) Chart.defaults.font.family = ff;

      const n = Math.max(thisCum.length, lastCum.length);
      const labels = Array.from({ length: n }, (_, i) => i + 1);
      const pad = (arr) => arr.concat(Array.from({ length: n - arr.length }, () => null));

      // ahead/behind at the same day-of-cycle
      const idx = thisCum.length - 1;
      const dEl = $("delta");
      if (idx >= 0 && idx < lastCum.length) {
        const diff = thisCum[idx] - lastCum[idx];
        dEl.textContent = (diff >= 0 ? "▲ ahead " : "▼ behind ") + money(Math.abs(diff)) + " vs last cycle";
        dEl.style.color = diff >= 0 ? C.green : C.red;
      } else if (idx >= 0) {
        dEl.textContent = money(thisCum[idx]) + " so far";
        dEl.style.color = C.text;
      } else { dEl.textContent = ""; }
      $("sub").textContent = "Day 1 = the " + data.billDay() + "th · This: " + fmtD(thisStart) + "→" + fmtD(today)
        + " · Last: " + fmtD(lastStart) + "→" + fmtD(lastEnd);

      const cfg = {
        type: "line",
        data: { labels, datasets: [
          { label: "Last cycle", data: pad(lastCum), borderColor: C.amber, backgroundColor: C.amber,
            borderWidth: 2, borderDash: [5, 4], pointRadius: 0, tension: 0.15, spanGaps: false },
          { label: "This cycle", data: pad(thisCum), borderColor: C.accent, backgroundColor: C.accent,
            borderWidth: 2.5, pointRadius: 0, tension: 0.15, spanGaps: false },
        ] },
        options: {
          responsive: true, maintainAspectRatio: false, animation: false,
          layout: { padding: { top: 8, bottom: 4 } },
          interaction: { mode: "index", intersect: false },
          plugins: {
            legend: { display: true, position: "bottom", labels: { color: C.muted, boxWidth: 18, boxHeight: 2, usePointStyle: false } },
            tooltip: {
              mode: "index", intersect: false,
              callbacks: {
                title: (items) => "Day " + (items.length ? items[0].label : ""),
                label: (c) => c.raw == null ? null : " " + c.dataset.label + ": " + money(c.raw),
                footer: (items) => {
                  const m = {}; items.forEach((i) => { if (i.raw != null) m[i.dataset.label] = Number(i.raw); });
                  if ("This cycle" in m && "Last cycle" in m) {
                    const diff = m["This cycle"] - m["Last cycle"];
                    return (diff >= 0 ? "Ahead " : "Behind ") + money(Math.abs(diff));
                  }
                  return "";
                },
              },
            },
          },
          scales: {
            x: { title: { display: true, text: "Day of cycle", color: C.muted }, ticks: { color: C.muted, maxRotation: 0, autoSkip: true }, grid: { display: false } },
            y: { ticks: { color: C.muted, callback: (v) => money(v) }, grid: { color: C.grid } },
          },
        },
        plugins: [markerPlugin(idx)],
      };
      if (chart) chart.destroy();
      chart = new Chart($("c").getContext("2d"), cfg);
    }

    let chartProblem = "";
    (async function start() {
      try { M = await battmanMap(card.hass, NEEDS); } catch (e) { return card.problem(e.message); }
      try { Chart = await loadChartJs(); } catch (e) { chartProblem = e.message; }
      data = costData(() => card.hass, { buy: M.buy_total, sell: M.sell_total, fee: M.network_fee_total, param: M.parameters });
      started = true;
      render();
      if (card.isConnected) resume();
    })();

    function resume() { if (started && !timer) timer = setInterval(render, 60000); }
    function pause() { clearInterval(timer); timer = null; }
    return { resume, pause, themeChanged: () => { if (started) render(); } };
  }
}
battmanDefine("battman-cost-compare", BattmanCostCompareCard);
battmanPicker("battman-cost-compare", "Battman Cost compare",
  "This bill cycle against the last: the running net cost day by day, and how far ahead or behind you are.", "battman-cost-compare");
