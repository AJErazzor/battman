// Battman Solar card: custom:battman-solar-card.
// Two inverters (Symo = third party, Sig = Sigenergy) with live power, today's energy and Solcast's
// forecast. view: now | forecast | toggle (pills) | both (two tables stacked).
// Rows whose power sensor doesn't exist are not drawn, so a one-inverter install just works.
// Solcast: sensor attributes estimate / estimate10, or estimate_<site> / estimate10_<site> per inverter.

import { BattmanCardBase, battmanDefine, battmanPicker, esc, inCardPicker } from "./battman-card-base.js";

const SAVE_KEY = "battman.solarCard";
const VIEWS = ["now", "forecast", "toggle", "both"];

const DEFAULTS = {
  view: "toggle", default_view: "now", forecast_basis: "p10", title: "Solar",
  show_total: true, show_10: true, show_progress: true, sparkline: "total",
  forecast_remaining: "sensor.solcast_pv_forecast_forecast_remaining_today",
  forecast_today: "sensor.solcast_pv_forecast_forecast_today",
  forecast_tomorrow: "sensor.solcast_pv_forecast_forecast_tomorrow",
  no_export_entity: "input_boolean.solarsystemcontrolnoexport",
  soft_limit_entity: "",
  symo: { show: true, label: "Symo", power: "sensor.sigen_plant_third_party_pv_power",
    today: "sensor.sigen_plant_daily_third_party_inverter_energy", site: "", color: "--battman-orange" },
  sig: { show: true, label: "Sig", power: "sensor.sigen_inverter_pv_power",
    today: "sensor.sigen_inverter_daily_pv_energy", site: "", color: "--battman-yellow" },
};
const FALLBACK = { "--battman-orange": "#f97316", "--battman-yellow": "#eab308", "--battman-green": "#22c55e",
  "--battman-red": "#ef4444" };

const CONFIG_KEYS = ["type", "grid_options", "view_layout", "visibility", ...Object.keys(DEFAULTS)];

class BattmanSolarCard extends BattmanCardBase {
  static cardName = "Battman Solar card";
  static gridOptions = { columns: "full", rows: "auto" };

  static getStubConfig() { return { view: "toggle" }; }

  // HA's Add card list: a small drawing of the card (no picture file to ship)
  _build() {
    if (!this._hass || !this.isConnected || this._built) return;
    if (!inCardPicker(this)) return super._build();
    this._built = true;
    const row = (n, c, w, v) => `<div style="padding:6px 0"><div style="display:flex;align-items:baseline;gap:8px"><span style="width:9px;height:9px;border-radius:50%;background:${c}"></span><b style="flex:1;font-size:13px">${n}</b><b style="font-size:16px">${v}<small style="font-size:10px;opacity:.6"> kW</small></b></div><div style="height:7px;border-radius:4px;background:var(--divider-color);margin:6px 0 2px"><div style="height:100%;width:${w}%;border-radius:4px;background:${c}"></div></div></div>`;
    this.shadowRoot.innerHTML = `<ha-card style="overflow:hidden;padding:0 14px 10px;font-family:var(--primary-font-family,sans-serif)">`
      + `<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid var(--divider-color)"><b style="font-size:12px;letter-spacing:.09em">SOLAR</b>`
      + `<span style="font-size:11px;color:var(--secondary-text-color)">10% &nbsp; Now &nbsp; Forecast</span></div>`
      + row("Symo", "#f97316", 62, "3.1") + row("Sig", "#eab308", 78, "4.6") + `</ha-card>`;
  }

  static getConfigForm() {
    const ent = (name, label, domain) => ({ name, label, selector: { entity: domain ? { domain } : {} } });
    const inv = (name, label) => ({ name, type: "expandable", title: label, schema: [
      { name: "show", label: "Show", selector: { boolean: {} } },
      { name: "label", label: "Name", selector: { text: {} } },
      ent("power", "Power sensor (live)", "sensor"),
      ent("today", "Energy today sensor", "sensor"),
      { name: "site", label: "Solcast site id (blank = whole forecast)", selector: { text: {} } },
    ] });
    return { schema: [
      { name: "view", label: "Layout", selector: { select: { mode: "dropdown", options: [
        { value: "toggle", label: "One card, Now / Forecast pills" }, { value: "both", label: "Both tables, stacked" },
        { value: "now", label: "Now only" }, { value: "forecast", label: "Forecast only" }] } } },
      { name: "default_view", label: "Pill selected first (toggle)", selector: { select: { mode: "dropdown", options: [
        { value: "now", label: "Now" }, { value: "forecast", label: "Forecast" }] } } },
      { name: "forecast_basis", label: "Forecast figures shown big (pill changes it)", selector: { select: { mode: "dropdown", options: [
        { value: "p10", label: "10% pessimistic (estimate small)" }, { value: "est", label: "Estimate (10% small)" }] } } },
      { name: "title", label: "Title", selector: { text: {} } },
      { name: "", type: "grid", schema: [
        { name: "show_total", label: "Total row", selector: { boolean: {} } },
        { name: "show_10", label: "10% (pessimistic) figures", selector: { boolean: {} } },
        { name: "show_progress", label: "Progress bars", selector: { boolean: {} } } ] },
      { name: "sparkline", label: "Today's power sparkline (actual vs forecast)", selector: { select: { mode: "dropdown", options: [
        { value: "total", label: "Total only" }, { value: "rows", label: "Per inverter only" },
        { value: "both", label: "Total and per inverter" }, { value: "off", label: "Off" }] } } },
      inv("symo", "Inverter 1 (third party)"), inv("sig", "Inverter 2 (Sigenergy)"),
      { name: "", type: "expandable", title: "Solcast and status", schema: [
        ent("forecast_remaining", "Forecast remaining today", "sensor"), ent("forecast_today", "Forecast today", "sensor"),
        ent("forecast_tomorrow", "Forecast tomorrow", "sensor"),
        ent("no_export_entity", "No-export toggle (orange pill)"), ent("soft_limit_entity", "Soft-limit toggle (red pill)")] },
    ] };
  }

  setConfig(config) {
    const extra = Object.keys(config || {}).filter((k) => !CONFIG_KEYS.includes(k));
    if (extra.length) throw new Error(`${this.constructor.cardName} has no options (found: ${extra.join(", ")}).`);
    const c = { ...DEFAULTS, ...config, symo: { ...DEFAULTS.symo, ...(config.symo || {}) },
      sig: { ...DEFAULTS.sig, ...(config.sig || {}) } };
    if (!["total", "rows", "both", "off"].includes(c.sparkline)) throw new Error("sparkline must be one of: total, rows, both, off");
    if (!VIEWS.includes(c.view)) throw new Error(`view must be one of: ${VIEWS.join(", ")}`);
    this._config = c;
  }

  static css = `
    :host { display: block; }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    button { font-family: inherit; }
    ha-card { overflow: hidden; background: var(--card-background-color); border: 1px solid var(--divider-color);
      border-radius: 12px; color: var(--primary-text-color); box-shadow: none; font-size: 16px; line-height: normal;
      font-family: var(--primary-font-family, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif); }
    .head { display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; justify-content: space-between;
      padding: 10px 16px; border-bottom: 1px solid var(--divider-color); }
    .title { font-size: 13px; font-weight: 700; letter-spacing: 0.09em; text-transform: uppercase; }
    .right { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
    .pills { display: flex; gap: 6px; }
    .pill { padding: 5px 12px; border: 1px solid var(--divider-color); border-radius: 999px; background: transparent;
      color: var(--secondary-text-color); font: inherit; font-size: 12px; font-weight: 600; line-height: 1; cursor: pointer;
      -webkit-tap-highlight-color: transparent; transition: background .12s ease, border-color .12s ease, color .12s ease; }
    .pill:hover { color: var(--primary-text-color); }
    .pill.active { background: var(--primary-color); border-color: var(--primary-color); color: #fff; }
    .flag { padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: 700; letter-spacing: 0.04em;
      text-transform: uppercase; border: 1px solid currentColor; line-height: 1; }
    .body { padding: 6px 16px 14px; }
    .sec + .sec { border-top: 1px solid var(--divider-color); margin-top: 6px; }
    .sub { font-size: 11px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
      color: var(--secondary-text-color); padding: 10px 0 2px; }
    .hero { display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap; padding: 10px 0 4px; }
    .hero .big { font-size: 34px; font-weight: 700; line-height: 1; }
    .hero .big small { font-size: 15px; font-weight: 600; color: var(--secondary-text-color); margin-left: 3px; }
    .hero .side { font-size: 13px; color: var(--secondary-text-color); }
    .hero .side b { color: var(--primary-text-color); font-weight: 700; }
    .row { padding: 9px 0; cursor: pointer; -webkit-tap-highlight-color: transparent; }
    .row + .row { border-top: 1px solid var(--divider-color); }
    .row.total { cursor: default; }
    .line { display: flex; align-items: baseline; gap: 10px; }
    .dot { width: 9px; height: 9px; border-radius: 50%; flex: none; align-self: center; }
    .name { font-weight: 700; font-size: 14px; flex: 1; min-width: 0; }
    .num { font-size: 17px; font-weight: 700; font-variant-numeric: tabular-nums; }
    .num small { font-size: 11px; font-weight: 600; color: var(--secondary-text-color); margin-left: 2px; }
    .num.dim { color: var(--secondary-text-color); font-weight: 600; }
    .spark { display: block; width: 100%; height: 30px; margin-top: 6px; }
    .spark.big { height: 44px; margin-top: 2px; }
    .bar { height: 7px; border-radius: 4px; background: var(--divider-color); margin: 7px 0 4px; position: relative; overflow: hidden; }
    .bar i { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 4px; }
    .bar i.lo { opacity: .45; }
    .foot { display: flex; justify-content: space-between; gap: 10px; font-size: 12px; color: var(--secondary-text-color);
      font-variant-numeric: tabular-nums; }
    .foot b { color: var(--primary-text-color); font-weight: 600; }
    .fc { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    .fc .colh { font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
      color: var(--secondary-text-color); padding-top: 4px; }
    .fc .cell .v { font-size: 15px; font-weight: 700; font-variant-numeric: tabular-nums; }
    .fc .cell .v small { font-size: 11px; font-weight: 600; color: var(--secondary-text-color); margin-left: 2px; }
    .fc .cell .p { font-size: 11px; color: var(--secondary-text-color); font-variant-numeric: tabular-nums; }
    .msg { padding: 22px 16px; text-align: center; color: var(--secondary-text-color); font-size: 14px; }
  `;
  static html = `<ha-card><div class="head"><span class="title" id="t"></span><div class="right" id="r"></div></div><div class="body" id="b"></div></ha-card>`;

  run(root) {
    const card = this;
    const $ = (id) => root.getElementById(id);
    let tab = null, basis = null;
    let hist = {}, histAt = 0, histBusy = false, histTimer = null;

    const loadTab = () => { try { const s = localStorage.getItem(SAVE_KEY + "." + (card._config.title || "")); if (s === "now" || s === "forecast") return s; } catch (e) {} return null; };
    const saveTab = () => { try { localStorage.setItem(SAVE_KEY + "." + (card._config.title || ""), tab); } catch (e) {} };
    const loadBasis = () => { try { const s = localStorage.getItem(SAVE_KEY + ".basis." + (card._config.title || "")); if (s === "est" || s === "p10") return s; } catch (e) {} return null; };
    const saveBasis = () => { try { localStorage.setItem(SAVE_KEY + ".basis." + (card._config.title || ""), basis); } catch (e) {} };

    const colour = (v) => getComputedStyle(card).getPropertyValue(v).trim() || FALLBACK[v] || "var(--primary-color)";
    const st = (id) => (id ? card.hass.states[id] : undefined);
    const num = (id) => { const s = st(id); const v = s ? parseFloat(s.state) : NaN; return Number.isFinite(v) ? v : null; };
    // power in kW / energy in kWh whatever unit the sensor reports
    const kw = (id) => { const v = num(id); if (v == null) return null; const u = (st(id).attributes.unit_of_measurement || "").trim(); return u === "W" ? v / 1000 : u === "MW" ? v * 1000 : v; };
    const kwh = (id) => { const v = num(id); if (v == null) return null; const u = (st(id).attributes.unit_of_measurement || "").trim(); return u === "Wh" ? v / 1000 : u === "MWh" ? v * 1000 : v; };
    const attr = (id, a) => { const s = st(id); const v = s ? parseFloat(s.attributes[a]) : NaN; return Number.isFinite(v) ? v : null; };
    const f1 = (v) => (v == null ? "–" : (Math.round(v * 10) / 10).toFixed(1));
    const on = (id) => { const s = st(id); return !!s && s.state === "on"; };

    // forecast figure: one site's attribute, or the whole-forecast attribute when no site is named
    const fc = (entity, base, site) => attr(entity, site ? `${base}_${site}` : base);

    function rowsOf(c) {
      const out = [];
      for (const k of ["symo", "sig"]) {
        const r = c[k];
        if (r.show === false || !st(r.power)) continue;
        out.push({ ...r, key: k, col: colour(r.color) });
      }
      // a row with no site id can only show the whole forecast, which is right for a single inverter
      out.forEach((r) => { r.hasFc = out.length === 1 || !!r.site; });
      return out;
    }

    // ---- today's power, from midnight: one series per inverter (kW), 5-minute steps ----
    const DAY0 = () => { const d = new Date(); d.setHours(0, 0, 0, 0); return d.getTime(); };
    async function loadHist() {
      const c = card._config; if (c.sparkline === "off" || histBusy || !card.hass) return;
      const ids = rowsOf(c).map((r) => r.power); if (!ids.length) return;
      histBusy = true;
      try {
        const start = new Date(DAY0()).toISOString();
        const r = await card.hass.callApi("GET", `history/period/${start}?filter_entity_id=${ids.join(",")}&minimal_response&no_attributes`);
        const out = {};
        r.forEach((arr) => {
          if (!arr.length) return;
          const id = arr[0].entity_id;
          out[id] = arr.map((x) => [Date.parse(x.last_changed || x.last_updated), parseFloat(x.state)]).filter((x) => Number.isFinite(x[1]));
        });
        hist = out; histAt = Date.now();
      } catch (e) { hist = {}; histAt = Date.now(); }
      histBusy = false;
      render();
    }
    // power sensors report W or kW; use the unit the sensor reports now
    const scaleOf = (id) => ((st(id) && st(id).attributes.unit_of_measurement) || "").trim() === "W" ? 0.001 : 1;
    // 5-minute step series from midnight to now (null before the first reading)
    function series(id) {
      const pts = hist[id]; if (!pts || !pts.length) return null;
      const t0 = DAY0(), n = Math.floor((Date.now() - t0) / 300000) + 1, k = scaleOf(id), out = new Array(n).fill(null);
      let j = 0, last = null;
      for (let i = 0; i < n; i++) {
        const t = t0 + i * 300000;
        while (j < pts.length && pts[j][0] <= t) { last = pts[j][1]; j++; }
        out[i] = last == null ? null : last * k;
      }
      return out;
    }
    // Solcast's half-hour curve for today (kW), as 5-minute steps midnight to midnight; the basis picks
    // 10% or the estimate. A site's curve is the whole curve scaled by that site's share of the day.
    function fcCurve(c, site) {
      const s0 = st(c.forecast_today), d = s0 && s0.attributes.detailedForecast;
      if (!Array.isArray(d) || !d.length) return null;
      const key = basis === "p10" ? "pv_estimate10" : "pv_estimate", ak = basis === "p10" ? "estimate10" : "estimate";
      let k = 1;
      if (site) { const a = attr(c.forecast_today, `${ak}_${site}`), b = attr(c.forecast_today, ak); k = a != null && b ? a / b : 0; }
      const t0 = DAY0(), pts = d.map((x) => [Date.parse(x.period_start), Number(x[key])]).filter((x) => Number.isFinite(x[0]) && Number.isFinite(x[1]));
      const out = []; let j = 0, last = 0;
      for (let i = 0; i < 288; i++) {
        const t = t0 + i * 300000;
        while (j < pts.length && pts[j][0] <= t) { last = pts[j][1]; j++; }
        out.push(last * k);
      }
      return out;
    }
    function sparkSvg(vals, col, cls, fvals) {
      if (!vals || vals.length < 2) return "";
      const W = 288, H = cls === "big" ? 44 : 30, N = 288;   // x spans the whole day, midnight to midnight
      const max = Math.max(0.1, ...vals.map((v) => v || 0), ...(fvals || []));
      const fline = fvals ? "M" + fvals.map((v, i) => ((i / (N - 1)) * W).toFixed(1) + " " + (H - 2 - (v / max) * (H - 5)).toFixed(1)).join("L") : "";
      const pts = vals.map((v, i) => [(i / (N - 1)) * W, H - 2 - ((v || 0) / max) * (H - 5)]);
      const line = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join("");
      const area = line + `L${pts[pts.length - 1][0].toFixed(1)} ${H}L0 ${H}Z`;
      const nowX = pts[pts.length - 1][0].toFixed(1);
      return `<svg class="spark ${cls || ""}" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none"><path d="${area}" fill="${col}" opacity=".18"/>`
        + (fline ? `<path d="${fline}" fill="none" stroke="${col}" stroke-width="1.3" stroke-dasharray="4 3" opacity=".75" vector-effect="non-scaling-stroke"/>` : "")
        + `<path d="${line}" fill="none" stroke="${col}" stroke-width="1.6" vector-effect="non-scaling-stroke"/>`
        + `<line x1="${nowX}" x2="${nowX}" y1="0" y2="${H}" stroke="var(--secondary-text-color)" stroke-width="1" stroke-dasharray="2 3" opacity=".6" vector-effect="non-scaling-stroke"/></svg>`;
    }

    function flags(c) {
      const f = [];
      if (c.no_export_entity && on(c.no_export_entity)) f.push(`<span class="flag" style="color:${colour("--battman-orange")}">No export</span>`);
      if (c.soft_limit_entity && on(c.soft_limit_entity)) f.push(`<span class="flag" style="color:${colour("--battman-red")}">Soft limit</span>`);
      return f.join("");
    }

    // ---------------- Now ----------------
    function nowHtml(c, rows, withSub) {
      if (!rows.length) return `<div class="msg">No inverter sensors found. Check the power sensors in the card options.</div>`;
      const tot = { p: 0, g: 0, left: 0, lo: 0, any: false };
      const other = basis === "p10" ? "est" : "10%";
      const rowHtml = rows.map((r) => {
        const p = kw(r.power), g = kwh(r.today);
        const est = r.hasFc ? fc(c.forecast_remaining, "estimate", r.site) : null;
        const p10 = r.hasFc ? fc(c.forecast_remaining, "estimate10", r.site) : null;
        const left = basis === "p10" && p10 != null ? p10 : est;
        const lo = basis === "p10" ? est : p10;
        tot.p += p || 0; tot.g += g || 0;
        const pct = left != null && g != null && g + left > 0 ? Math.min(100, (g / (g + left)) * 100) : null;
        return `<div class="row" data-e="${esc(r.power)}">
          <div class="line"><span class="dot" style="background:${r.col}"></span><span class="name">${esc(r.label)}</span>
            <span class="num">${f1(p)}<small>kW</small></span></div>
          ${c.sparkline === "rows" || c.sparkline === "both" ? sparkSvg(series(r.power), r.col, "", r.hasFc ? fcCurve(c, rows.length === 1 ? "" : r.site) : null) : ""}
          ${c.show_progress && pct != null ? `<div class="bar"><i style="width:${pct}%;background:${r.col}"></i></div>` : `<div style="height:6px"></div>`}
          <div class="foot"><span>Today <b>${f1(g)} kWh</b></span>
            <span>${left != null ? `To go <b>${f1(left)}</b>${c.show_10 && lo != null ? ` · ${other} ${f1(lo)}` : ""} kWh` : ""}</span></div></div>`;
      }).join("");
      const tEst = fc(c.forecast_remaining, "estimate"), tP10 = fc(c.forecast_remaining, "estimate10");
      const left = basis === "p10" && tP10 != null ? tP10 : tEst, lo = basis === "p10" ? tEst : tP10;
      const sers = rows.map((r) => series(r.power)).filter(Boolean);
      const sum = sers.length ? sers[0].map((_, i) => sers.reduce((a, x) => a + (x[i] || 0), 0)) : null;
      const heroSpark = c.sparkline === "total" || c.sparkline === "both" ? sparkSvg(sum, colour("--battman-green"), "big", fcCurve(c, "")) : "";
      const hero = `<div class="hero"><div class="big">${f1(tot.p)}<small>kW</small></div>
        <div class="side">Today <b>${f1(tot.g)} kWh</b>${left != null ? ` · to go <b>${f1(left)}</b>${c.show_10 && lo != null ? ` (${other} ${f1(lo)})` : ""} kWh` : ""}</div></div>${heroSpark}`;
      const totalRow = c.show_total && rows.length > 1 ? `<div class="row total"><div class="line"><span class="dot" style="background:${colour("--battman-green")}"></span>
          <span class="name">Total</span><span class="num">${f1(tot.p)}<small>kW</small></span></div>
          ${c.show_progress && left != null && tot.g + left > 0 ? `<div class="bar"><i style="width:${Math.min(100, tot.g / (tot.g + left) * 100)}%;background:${colour("--battman-green")}"></i></div>` : `<div style="height:6px"></div>`}
          <div class="foot"><span>Today <b>${f1(tot.g)} kWh</b></span><span>${left != null ? `To go <b>${f1(left)}</b>${c.show_10 && lo != null ? ` · ${other} ${f1(lo)}` : ""} kWh` : ""}</span></div></div>` : "";
      return (withSub ? `<div class="sub">Now</div>` : "") + hero + rowHtml + totalRow;
    }

    // ---------------- Forecast ----------------
    function fcHtml(c, rows, withSub) {
      if (!rows.length) return `<div class="msg">No inverter sensors found. Check the power sensors in the card options.</div>`;
      const days = [["Today", c.forecast_today], ["Tomorrow", c.forecast_tomorrow]];
      const lines = rows.map((r) => ({ label: r.label, col: r.col, site: r.site, hasFc: r.hasFc, tot: false }));
      if (c.show_total && rows.length > 1) lines.push({ label: "Total", col: colour("--battman-green"), site: "", hasFc: true, tot: true });
      const vals = lines.map((l) => days.map(([, e]) => ({ hi: l.hasFc ? fc(e, "estimate", l.site) : null, lo: l.hasFc ? fc(e, "estimate10", l.site) : null })));
      const max = Math.max(1, ...vals.flat().map((v) => v.hi || 0));
      const p10 = basis === "p10";
      const body = lines.map((l, i) => `<div class="row total"><div class="line"><span class="dot" style="background:${l.col}"></span><span class="name">${esc(l.label)}</span></div>
        <div class="fc">${days.map(([d], j) => { const v = vals[i][j];
          return `<div class="cell"><div class="colh">${d}</div><div class="v">${f1(p10 && v.lo != null ? v.lo : v.hi)}<small>kWh</small></div>
            <div class="bar"><i style="width:${v.hi != null ? (v.hi / max) * 100 : 0}%;background:${l.col};${p10 ? "opacity:.35" : ""}"></i>${c.show_10 && v.lo != null ? `<i class="lo" style="width:${(v.lo / max) * 100}%;${p10 ? `background:${l.col};opacity:1` : "background:#000;opacity:.28"}"></i>` : ""}</div>
            ${c.show_10 ? `<div class="p">${p10 ? "est" : "10%"} ${f1(p10 ? v.hi : v.lo)} kWh</div>` : ""}</div>`; }).join("")}</div></div>`).join("");
      return (withSub ? `<div class="sub">Forecast</div>` : "") + body;
    }

    function render() {
      const c = card._config; if (!c || !card.hass) return;
      const rows = rowsOf(c);
      if (!tab) tab = loadTab() || c.default_view || "now";
      if (!basis) basis = loadBasis() || c.forecast_basis || "est";
      let body = "";
      if (c.view === "now") body = nowHtml(c, rows, false);
      else if (c.view === "forecast") body = fcHtml(c, rows, false);
      else if (c.view === "both") body = `<div class="sec">${nowHtml(c, rows, true)}</div><div class="sec">${fcHtml(c, rows, true)}</div>`;
      else body = tab === "forecast" ? fcHtml(c, rows, false) : nowHtml(c, rows, false);
      $("t").textContent = c.title || "";
      $("r").innerHTML = flags(c)
        + (c.show_10 ? `<div class="pills"><button class="pill${basis === "est" ? " active" : ""}" data-b="${basis === "est" ? "p10" : "est"}" title="Tap to switch the main forecast figures between 10% and the estimate">${basis === "est" ? "Est" : "10%"}</button></div>` : "")
        + (c.view === "toggle"
        ? `<div class="pills"><button class="pill${tab === "now" ? " active" : ""}" data-t="now">Now</button><button class="pill${tab === "forecast" ? " active" : ""}" data-t="forecast">Forecast</button></div>` : "");
      $("b").innerHTML = body;
    }

    root.addEventListener("click", (e) => {
      const p = e.target.closest && e.target.closest(".pill");
      if (p && p.dataset.b) { basis = p.dataset.b; saveBasis(); render(); return; }
      if (p) { tab = p.dataset.t; saveTab(); render(); return; }
      const r = e.target.closest && e.target.closest(".row[data-e]");
      if (r) card.dispatchEvent(new CustomEvent("hass-more-info", { detail: { entityId: r.dataset.e }, bubbles: true, composed: true }));
    });

    const watched = () => { const c = card._config; return [c.symo.power, c.symo.today, c.sig.power, c.sig.today, c.forecast_remaining,
      c.forecast_today, c.forecast_tomorrow, c.no_export_entity, c.soft_limit_entity].filter(Boolean); };
    render();
    loadHist();
    return {
      hassChanged: (old) => { if (Date.now() - histAt > 300000) loadHist(); if (!old || watched().some((id) => old.states[id] !== card.hass.states[id])) render(); },
      themeChanged: render,
    };
  }
}
battmanDefine("battman-solar-card", BattmanSolarCard);
battmanPicker("battman-solar-card", "Battman Solar card",
  "Live power, today's generation and Solcast forecast for one or two inverters, as pills, stacked tables, or either alone.",
  "battman-solar-card");
