// Battman House: custom:battman-house. The house picture with live numbers on it: prices, solar,
// home, grid, battery, PV strings, temperature and up to three of your own devices, with flow
// lines that move when power flows. Battman's copy of the Smiggles house card, drawn by itself
// (no button-card, mushroom or card-mod needed).
//
// Every item has its own settings, all optional (the defaults are Battman's entity map, or the
// Smiggles entities where the map has no entry):
//
//   type: custom:battman-house
//   buy:     { show: true, entity: sensor.amber_5min_current_general_price }
//   pc1:     { show: true, label: Malachy PC, entity: sensor.malachys_pc_power, suffix: W }
//   house:   { show: true, image: /battmanfiles/images/house.webp }
//   ...
//
// An item whose entity doesn't exist isn't drawn (nothing to show); a picture that doesn't load
// isn't drawn either. The card's editor lists every item. The pictures are Battman's
// (www/images/house*.webp); point house / battery_unit / gateway at your own to change them.
// ---------------------------------------------------------------------------------------------

const HOUSE_MAP_URL = "battman/entities";

// Register a custom element so HA finds it (as in battman-cards.js: HA may swap its element
// registry while it starts, so register again in the new one if that happens after us).
function battmanDefine(tag, cls) {
  const reg = window.customElements;
  if (!reg.get(tag)) reg.define(tag, cls);
  const t0 = Date.now();
  (function watch() {
    const now = window.customElements;
    if (now !== reg) {
      if (!now.get(tag)) {
        try { now.define(tag, cls); } catch (e) { console.error(`Battman: couldn't register ${tag}: ${e.message}`); }
      }
      return;
    }
    if (window.CustomElementRegistryPolyfill) return;
    if (Date.now() - t0 < 30000) setTimeout(watch, 20);
  })();
}

// The items, in the editor's order. ent: { field: default } where a default "map:x" is entry x of
// Battman's entity map. need: the fields that must exist for the item to be drawn.
// at: [top %, left %, width %] on the card (the Smiggles card's places).
const HOUSE_ITEMS = [
  { key: "house", title: "House picture", image: "/battmanfiles/images/house.webp", at: [1.1, 0, 100] },
  { key: "battery_unit", title: "Battery picture", image: "/battmanfiles/images/house-battery.webp", at: [1.1, -3.8, 100] },
  { key: "gateway", title: "Gateway picture", image: "/battmanfiles/images/house-gateway.webp", at: [-2.4, 2, 97.7] },
  { key: "temperature", title: "Outside temperature", ent: { entity: "weather.athelstone" }, need: ["entity"], at: [0, 2.5, 25.3] },
  { key: "pv2", title: "PV string (top)", label: "PV2 East", ent: { entity: "sensor.sigen_inverter_pv2_power" }, need: ["entity"], at: [9.0, 2.5, 25.3] },
  { key: "pv1", title: "PV string (middle)", label: "PV1 North", ent: { entity: "sensor.sigen_inverter_pv1_power" }, need: ["entity"], at: [16.8, 2.5, 25.3] },
  { key: "pv3", title: "PV string (bottom)", label: "PV3 West", ent: { entity: "sensor.sigen_inverter_pv3_power" }, need: ["entity"], at: [24.6, 2.5, 25.3] },
  { key: "solar", title: "Solar power", label: "SOLAR", ent: { entity: "map:pv_power" }, need: ["entity"], at: [5.6, 44.3, 25.3] },
  { key: "solar_today", title: "Solar today", ent: { entity: "sensor.sigen_plant_daily_pv_energy" }, need: ["entity"], at: [14.3, 44.3, 35.4] },
  { key: "countdown", title: "Price countdown", label: "LEFT", at: [3, 60, 20] },
  { key: "sell", title: "Sell price (feed-in)", label: "FIT", ent: { entity: "map:feed_in_price" }, need: ["entity"], at: [0, 74, 25] },
  { key: "buy", title: "Buy price", label: "BUY", ent: { entity: "map:buy_price" }, need: ["entity"], at: [7.8, 74, 25] },
  { key: "home", title: "Home power", label: "HOME", ent: { entity: "map:home_power" }, need: ["entity"], at: [32.2, 80.5, 19] },
  { key: "home_today", title: "Home today", ent: { entity: "sensor.sigen_plant_daily_load_consumption" }, need: ["entity"], at: [40.7, 80.5, 19] },
  { key: "pc1", title: "Device 1", label: "Malachy PC", suffix: "W", ent: { entity: "sensor.malachys_pc_power" }, need: ["entity"], at: [60, 2.5, 25.3] },
  { key: "pc2", title: "Device 2", label: "Noah PC", suffix: "W", ent: { entity: "sensor.noahspc_power" }, need: ["entity"], at: [67.8, 2.5, 25.3] },
  { key: "pc3", title: "Device 3", label: "Hamish PC", suffix: "W", ent: { entity: "sensor.hamish_pc_power" }, need: ["entity"], at: [75.6, 2.5, 25.3] },
  { key: "battery_temp", title: "Battery temperature", ent: { entity: "sensor.sigen_inverter_battery_maximum_temperature" }, need: ["entity"], at: [58.9, 27.6, 25.3] },
  { key: "battery", title: "Battery charge", label: "SOC", ent: { entity: "map:battery_soc", capacity: "map:rated_energy_capacity" }, need: ["entity"], at: [75.6, 32, 46] },
  { key: "battery_flow", title: "Battery charging / discharging", ent: { entity: "map:battery_power", soc: "map:battery_soc", capacity: "map:rated_energy_capacity" }, need: ["entity"], at: [83.3, 32, 46] },
  { key: "grid", title: "Grid power", label: "GRID", ent: { import: "map:grid_import_power", export: "map:grid_export_power" }, need: ["import", "export"], at: [75.6, 79.8, 19.5] },
  { key: "grid_flow", title: "Grid import / export today", ent: { import: "map:grid_import_power", export: "map:grid_export_power", import_today: "map:grid_import_today", export_today: "map:grid_export_today" }, need: ["import", "export"], at: [83.3, 79.8, 19.5] },
  { key: "lines", title: "Flow lines", ent: { solar: "map:pv_power", home: "map:home_power", battery: "map:battery_power", import: "map:grid_import_power", export: "map:grid_export_power" } },
];
const HOUSE_BY_KEY = Object.fromEntries(HOUSE_ITEMS.map((i) => [i.key, i]));
const HOUSE_ENT_LABELS = {
  entity: "Entity", capacity: "Battery capacity (kWh)", soc: "Battery charge (%)", import: "Grid import power",
  export: "Grid export power", import_today: "Grid import today", export_today: "Grid export today",
  solar: "Solar power", home: "Home power", battery: "Battery power",
};
const HOUSE_TOP_KEYS = ["type", "theme", "grid_options", "view_layout", "visibility", ...HOUSE_ITEMS.map((i) => i.key)];

// The static lines, and the moving ones: [top %, left %, width %, angle].
const HOUSE_STATIC = [
  { at: [35.6, 78.7], w: "1px", h: "17.8%", muted: true },
  { at: [8.9, 45.6], w: "1px", h: "14%", muted: true },
  { at: [66.7, 33], w: "2px", h: "26.7%", muted: true },
  { at: [73.3, 78], w: "2px", h: "20.3%", muted: false },
];
const HOUSE_FLOWS = {
  pv_sig_01: [22.2, 34.2, 30.9, 90],
  pv_sig_02: [22.4, 33.9, 11.9, 0],
  gw_home: [61.6, 58.2, 22.8, -25],
  sig_gw: [55.6, 39.2, 20.3, 20],
  gw_grid_01: [61.6, 58.2, 6.3, 90],
  gw_grid_02: [67.1, 58, 21, 20],
};

// Battman's entity map, once per page load.
let houseMap = null;
function houseFetchMap(hass) {
  if (!houseMap) {
    houseMap = hass.callApi("GET", HOUSE_MAP_URL).then((r) => r.entities || {});
    houseMap.catch(() => { houseMap = null; });
  }
  return houseMap;
}

// One item's defaults, with map entries filled in.
function houseDefaults(item, map) {
  const out = { show: true };
  if (item.image) out.image = item.image;
  if (item.label !== undefined) out.label = item.label;
  if (item.suffix !== undefined) out.suffix = item.suffix;
  for (const [f, d] of Object.entries(item.ent || {})) out[f] = d.startsWith("map:") ? (map[d.slice(4)] || "") : d;
  return out;
}

function houseConfigProblem(c) {
  const unknown = Object.keys(c).filter((k) => !HOUSE_TOP_KEYS.includes(k));
  if (unknown.length) return `Unknown setting${unknown.length > 1 ? "s" : ""}: ${unknown.join(", ")}.`;
  for (const item of HOUSE_ITEMS) {
    const v = c[item.key];
    if (v === undefined) continue;
    if (!v || typeof v !== "object" || Array.isArray(v)) return `${item.key} must be a set of settings (show, entity, ...).`;
    const allowed = Object.keys(houseDefaults(item, {}));
    const bad = Object.keys(v).filter((k) => !allowed.includes(k));
    if (bad.length) return `${item.key}: unknown setting${bad.length > 1 ? "s" : ""} ${bad.join(", ")} (use ${allowed.join(", ")}).`;
    if ("show" in v && typeof v.show !== "boolean") return `${item.key}: show must be true or false.`;
    for (const [k, x] of Object.entries(v)) if (k !== "show" && typeof x !== "string") return `${item.key}: ${k} must be text.`;
  }
  return "";
}

// A state as a number, or null when it isn't one (unknown, unavailable, missing).
function houseNum(hass, id) {
  const st = id && hass.states[id];
  if (!st) return null;
  const n = parseFloat(st.state);
  return Number.isFinite(n) ? n : null;
}
// Like Jinja's round(): no trailing zeros forced.
const houseRound = (n, d) => String(Number(n.toFixed(d)));

const HOUSE_CSS = `
  :host { display: block; }
  ha-card { position: relative; border: none; aspect-ratio: 395 / 450; container-type: inline-size; overflow: hidden; }
  .it { position: absolute; box-sizing: border-box; padding: 12px; font-weight: bold; letter-spacing: -0.1px;
        font-family: var(--battman-font, var(--primary-font-family, sans-serif)); line-height: 1.3; cursor: pointer; }
  .it.noclick { cursor: default; }
  .p { font-size: clamp(13px, 4.1cqw, 17px); white-space: nowrap; overflow: visible; }
  .s { font-size: clamp(11px, 3.6cqw, 15px); white-space: nowrap; }
  .small { font-size: clamp(10px, 3.1cqw, 13px); white-space: pre; }
  .blend { color: #fff; mix-blend-mode: difference; }
  .muted { color: var(--battman-text-muted, var(--secondary-text-color)); }
  .blue { color: var(--battman-blue, var(--primary-color)); }
  .right { text-align: right; }
  img.pic { position: absolute; display: block; height: auto; pointer-events: none; }
  .bar { position: absolute; }
  .ln { position: absolute; height: 2px; background: #fff; opacity: .6; overflow: hidden; transform-origin: left center; pointer-events: none; }
  .ln::before { content: ""; position: absolute; top: 0; width: 60%; height: 2px; border-radius: 1px; opacity: 0;
                background: linear-gradient(to right, rgba(0,123,255,0) 0%, rgba(0,123,255,.4) 40%, rgba(0,123,255,1) 100%); }
  .ln.fwd::before { opacity: 1; animation: house-fwd 2s ease-in-out infinite var(--delay, 0s); }
  .ln.rev::before { opacity: 1; transform: scaleX(-1); animation: house-rev 2s ease-in-out infinite var(--delay, 0s); }
  @keyframes house-fwd { 0% { left: -50%; } 100% { left: 100%; } }
  @keyframes house-rev { 0% { left: 100%; } 100% { left: -50%; } }
`;

class BattmanHouseCard extends HTMLElement {
  static getStubConfig() {
    return {};
  }

  static getConfigElement() {
    return document.createElement("battman-house-editor");
  }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    const problem = houseConfigProblem(config);
    if (problem) throw new Error(`Battman House: ${problem}`);
    this._config = config;
    this._built = false;
    this._draw();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._map && !this._mapProblem) {
      houseFetchMap(hass).then(
        (m) => { this._map = m; this._draw(); },
        (e) => { this._mapProblem = (e && e.body && e.body.message) || (e && e.message) || String(e); this._draw(); }
      );
    }
    this._draw();
  }

  // Each item's settings in force: its defaults, then the card's.
  _settings() {
    const out = {};
    for (const item of HOUSE_ITEMS) out[item.key] = { ...houseDefaults(item, this._map), ...(this._config[item.key] || {}) };
    return out;
  }

  _draw() {
    if (!this._config || !this._hass) return;
    if (this._mapProblem) {
      this.shadowRoot.innerHTML = `<ha-card><div style="padding:12px 16px;font-size:13px;color:var(--error-color,#db4437)"><b>Battman card problem</b><br><span></span></div></ha-card>`;
      this.shadowRoot.querySelector("span").textContent = `Couldn't load Battman's entity map: ${this._mapProblem}`;
      return;
    }
    if (!this._map) return;
    if (!this._built) this._build();
    this._update();
  }

  // The parts that don't change with states: pictures, lines, the boxes the numbers go in.
  _build() {
    const s = (this._s = this._settings());
    const pos = (a) => `top:${a[0]}%;left:${a[1]}%;width:${a[2]}%`;
    let html = `<style>${HOUSE_CSS}</style><ha-card>`;
    for (const k of ["house", "battery_unit", "gateway"]) {
      if (s[k].show && s[k].image) html += `<img class="pic" data-k="${k}" alt="" style="${pos(HOUSE_BY_KEY[k].at)}">`;
    }
    if (s.lines.show) {
      for (const b of HOUSE_STATIC) {
        html += `<div class="bar" style="top:${b.at[0]}%;left:${b.at[1]}%;width:${b.w};height:${b.h};background:${b.muted ? "var(--battman-text-muted, var(--secondary-text-color))" : "rgba(255,255,255,0.35)"}"></div>`;
      }
      for (const [k, f] of Object.entries(HOUSE_FLOWS)) {
        html += `<div class="ln" data-flow="${k}" style="top:${f[0]}%;left:${f[1]}%;width:${f[2]}%;transform:rotate(${f[3]}deg)"></div>`;
      }
    }
    for (const item of HOUSE_ITEMS) {
      if (item.image || item.key === "lines") continue;
      const right = item.key === "buy" || item.key === "sell" || item.key === "countdown";
      html += `<div class="it${right ? " right" : ""}" data-item="${item.key}" style="${pos(item.at)};display:none"></div>`;
    }
    html += `</ha-card>`;
    this.shadowRoot.innerHTML = html;
    for (const img of this.shadowRoot.querySelectorAll("img.pic")) {
      img.addEventListener("error", () => { img.style.display = "none"; });   // no picture there: draw nothing
      img.src = s[img.dataset.k].image;
    }
    for (const el of this.shadowRoot.querySelectorAll(".it")) el.addEventListener("click", () => this._tap(el.dataset.item));
    this._els = Object.fromEntries([...this.shadowRoot.querySelectorAll(".it")].map((e) => [e.dataset.item, e]));
    this._flows = Object.fromEntries([...this.shadowRoot.querySelectorAll(".ln")].map((e) => [e.dataset.flow, e]));
    this._last = {};
    this._built = true;
  }

  _tap(key) {
    if (key === "grid") {
      history.pushState(null, "", "/energy");
      window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
      return;
    }
    const st = this._s[key];
    const id = st && (st.entity || st.import);
    if (!id || key === "grid_flow") return;
    this.dispatchEvent(new CustomEvent("hass-more-info", { detail: { entityId: id }, bubbles: true, composed: true }));
  }

  _update() {
    const hass = this._hass;
    const s = this._s;
    const has = (id) => !!(id && hass.states[id]);
    const num = (id) => houseNum(hass, id);
    for (const item of HOUSE_ITEMS) {
      const el = this._els[item.key];
      if (!el) continue;
      const st = s[item.key];
      const shown = st.show && (item.need || []).every((f) => has(st[f]));
      const html = shown ? this._html(item.key, st, num, has) : null;
      if (html === null) {
        el.style.display = "none";
        this._last[item.key] = null;
        continue;
      }
      el.style.display = "";
      if (this._last[item.key] !== html) { el.innerHTML = html; this._last[item.key] = html; }
      el.classList.toggle("noclick", item.key === "grid_flow" || item.key === "countdown");
    }
    if (s.lines.show) this._lines(s.lines, num);
  }

  // One item's contents (HTML), or null for nothing to show.
  _html(key, st, num, has) {
    const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
    // a value with its text under it; pc / sc: their classes, colour: the value's theme colour
    const two = (p, sec, pc = "blend", sc = "muted", colour = "") =>
      `<div class="p ${pc}"${colour ? ` style="color:var(--battman-${colour})"` : ""}>${p}</div>${sec ? `<div class="s ${sc}">${esc(sec)}</div>` : ""}`;
    const v = num(st.entity);
    const dash = "-";
    switch (key) {
      case "buy": {
        const c = v === null ? "muted" : v < 0 ? "purple" : v <= 0.08 ? "green" : v <= 0.25 ? "yellow" : "darkred";
        return two(v === null ? dash : `${houseRound(v * 100, 1)}c`, st.label, "", "muted", c);
      }
      case "sell": {
        const c = v === null ? "muted" : v < 0 ? "darkred" : v < 0.05 ? "orange" : v < 0.15 ? "yellow" : v < 0.25 ? "green" : "purple";
        return two(v === null ? dash : `${houseRound(v * 100, 1)}c`, st.label, "", "muted", c);
      }
      case "countdown":
        return `<div style="display:flex;align-items:baseline;justify-content:flex-end;gap:4px;line-height:1">
          <span class="s muted" style="text-transform:uppercase">${esc(st.label)}</span>
          <span class="p" style="color:var(--battman-text-bright,var(--primary-text-color));text-shadow:0 1px 2px rgba(0,0,0,.6)"><battman-countdown></battman-countdown></span></div>`;
      case "solar":
        return two(`${v !== null && v > 0 ? houseRound(v, 2) : 0} kW`, st.label, "blend", "blend");
      case "home":
        return two(`${v === null ? dash : houseRound(v, 1)} kW`, st.label, "blend", "blend");
      case "solar_today":
      case "home_today":
        return `<div class="small blend">Today:\n${v === null ? dash : houseRound(v, 2)} kWh</div>`;
      case "temperature": {
        const e = this._hass.states[st.entity];
        const t = st.entity.startsWith("weather.") ? e.attributes.temperature : e.state;
        const n = parseFloat(t);
        const unit = st.entity.startsWith("weather.") ? (e.attributes.temperature_unit || "°C") : (e.attributes.unit_of_measurement || "");
        return two(Number.isFinite(n) ? `${t}${unit}` : "unavailable", "");
      }
      case "pv1":
      case "pv2":
      case "pv3": {
        if (v === null) return two(dash, st.label, "blend", "blue");
        // the plant's solar power, split by each string's share (as Smiggles did)
        const plant = num(this._s.solar.entity) || 0;
        const tot = ["pv1", "pv2", "pv3"].reduce((a, k) => a + (num(this._s[k].entity) || 0), 0);
        return two(`${houseRound(tot > 0 ? (plant * v) / tot : 0, 2)} kW`, st.label, "blend", "blue");
      }
      case "pc1":
      case "pc2":
      case "pc3":
        return two(v === null ? dash : `${houseRound(v, 3)}${st.suffix ? " " + esc(st.suffix) : ""}`, st.label, "blend", "blue");
      case "battery_temp":
        return `<div class="s" style="color:var(--battman-green);transform:rotate(22deg);transform-origin:left center;white-space:nowrap">${v === null ? dash : houseRound(v, 1) + " °C"}</div>`;
      case "battery": {
        if (v === null) return two(dash, st.label, "blend", "blend");
        const cap = num(st.capacity);
        return two(`${houseRound(v, 1)}%${cap !== null ? ` | ${houseRound((v * cap) / 100, 2)} kWh` : ""}`, st.label, "blend", "blend");
      }
      case "battery_flow": {
        if (v === null) return null;
        const soc = num(st.soc);
        const cap = num(st.capacity);
        const p = Number(v.toFixed(1));
        const rate = cap ? ` | ${houseRound((Math.abs(p) / cap) * 100, 1)}%/h` : "";
        const top = p > 0 ? `Chg ${houseRound(p, 1)} kW${rate}` : p < 0 ? `Dischg ${houseRound(Math.abs(p), 1)} kW${rate}` : "Floating";
        const colour = v > 0.1 ? "green" : v < -0.1 ? "darkred" : "yellow";
        let lines = "";
        if (soc !== null && cap) {
          const hm = (h) => `${Math.floor(h)}h ${Math.round((h % 1) * 60)}m`;
          const t = v > 0 ? `${hm((cap - (soc / 100) * cap) / v)} to full` : v < 0 ? `${hm(((soc / 100) * cap) / Math.abs(v))} to empty` : "—";
          lines = `${t}\n${soc >= 100 ? "Full" : `${houseRound(((100 - soc) / 100) * cap, 1)} kWh to full`}`;
        }
        return `<div class="p" style="font-size:clamp(11px,3.3cqw,14px);color:var(--battman-${colour});overflow:hidden;text-overflow:ellipsis">${top}</div>`
          + (lines ? `<div class="small muted">${lines}</div>` : "");
      }
      case "grid": {
        const imp = num(st.import) || 0;
        const exp = num(st.export) || 0;
        const t = imp > 0 ? houseRound(imp, 2) : exp > 0 ? houseRound(-exp, 2) : "0";
        return two(`${t} kW`, st.label, "blend", "blend");
      }
      case "grid_flow": {
        const imp = num(st.import) || 0;
        const exp = num(st.export) || 0;
        const word = imp > 0 ? "Import" : exp > 0 ? "Export" : "";
        const colour = imp > 0 ? "var(--battman-darkred)" : exp > 0 ? "var(--battman-green)" : "var(--battman-text-muted)";
        const todayId = imp > 0 ? st.import_today : exp > 0 ? st.export_today : "";
        const today = todayId && has(todayId) ? num(todayId) : null;
        const sec = word ? (today !== null ? `Today:\n${houseRound(today, 2)} kWh` : "") : "—";
        return `<div class="p" style="font-size:clamp(12px,3.8cqw,16px);color:${colour}">${word || " "}</div>`
          + (sec ? `<div class="small muted">${sec}</div>` : "");
      }
    }
    return null;
  }

  // The moving lines: which way power flows now (each line only when its entities exist).
  _lines(st, num) {
    const pv = num(st.solar);
    const home = num(st.home);
    const batt = num(st.battery);
    const imp = num(st.import);
    const exp = num(st.export);
    const set = (k, dir, delay) => {
      const el = this._flows[k];
      if (!el) return;
      const cls = `ln${dir ? " " + dir : ""}`;
      if (el.className !== cls) el.className = cls;
      el.style.setProperty("--delay", delay || "0s");
    };
    const solarOn = pv !== null && pv > 0;
    set("pv_sig_01", solarOn ? "fwd" : "", "1.6s");
    set("pv_sig_02", solarOn ? "rev" : "", "0s");
    set("gw_home", home !== null && home > 0 ? "fwd" : "", "2.6s");
    const fwd = (batt !== null && batt < 0) || solarOn;
    const flow = (batt !== null && batt !== 0) || (pv !== null && pv !== 0);
    set("sig_gw", flow ? (fwd ? "fwd" : "rev") : "", fwd ? "1.3s" : "0s");
    const gridDir = exp !== null && exp > 0 ? "fwd" : imp !== null && imp > 0 ? "rev" : "";
    set("gw_grid_01", gridDir, gridDir === "rev" ? "1.3s" : "0s");
    set("gw_grid_02", gridDir, gridDir === "fwd" ? "1.3s" : "0s");
  }

  getCardSize() {
    return 9;
  }

  getGridOptions() {
    return { columns: 12, rows: "auto", min_columns: 6 };
  }
}
battmanDefine("battman-house", BattmanHouseCard);

// The editor: one fold-out per item (show, entity, and label / suffix / picture where it has them).
class BattmanHouseEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._map) houseFetchMap(hass).then((m) => { this._map = m; this._render(); }, () => {});
    if (this._form) this._form.hass = hass;
  }

  _schema() {
    return HOUSE_ITEMS.map((item) => {
      const fields = [{ name: "show", selector: { boolean: {} } }];
      if (item.image) fields.push({ name: "image", selector: { text: {} } });
      if (item.label !== undefined) fields.push({ name: "label", selector: { text: {} } });
      for (const f of Object.keys(item.ent || {})) {
        fields.push({ name: f, selector: f === "entity" && item.key === "temperature" ? { entity: { domain: ["weather", "sensor"] } } : { entity: {} } });
      }
      if (item.suffix !== undefined) fields.push({ name: "suffix", selector: { text: {} } });
      return { type: "expandable", name: item.key, title: item.title, schema: fields };
    });
  }

  _render() {
    if (!this._hass || !this._config || !this._map) return;
    if (!this._form) {
      this.innerHTML = `<p style="color:var(--secondary-text-color);font-size:13px;margin:0 0 12px">Each item can be
        turned off, or pointed at your own entity. An item whose entity doesn't exist isn't shown.</p><div class="form"></div>`;
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (sch) => ({ show: "Show", image: "Picture (e.g. /local/house.png)", label: "Text", suffix: "After the value (e.g. W)" }[sch.name] || HOUSE_ENT_LABELS[sch.name] || sch.name);
      this._form.addEventListener("value-changed", (ev) => {
        ev.stopPropagation();
        const config = this._fromForm(ev.detail.value);
        this._config = config;
        this._form.data = this._toForm(config);
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config }, bubbles: true, composed: true }));
      });
      this.querySelector(".form").append(this._form);
      this._form.schema = this._schema();
    }
    this._form.hass = this._hass;
    this._form.data = this._toForm(this._config);
  }

  _toForm(config) {
    const data = {};
    for (const item of HOUSE_ITEMS) data[item.key] = { ...houseDefaults(item, this._map), ...(config[item.key] || {}) };
    return data;
  }

  // Only what differs from the defaults goes in the YAML (so map changes still follow through).
  _fromForm(data) {
    const out = {};
    for (const [k, v] of Object.entries(this._config)) if (!HOUSE_BY_KEY[k]) out[k] = v;
    out.type = "custom:battman-house";
    for (const item of HOUSE_ITEMS) {
      const d = houseDefaults(item, this._map);
      const diff = {};
      for (const [k, v] of Object.entries(data[item.key] || {})) {
        const val = v === undefined || v === null ? (k === "show" ? false : "") : v;
        if (val !== d[k]) diff[k] = val;
      }
      if (Object.keys(diff).length) out[item.key] = diff;
    }
    return out;
  }
}
battmanDefine("battman-house-editor", BattmanHouseEditor);

window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "battman-house")) {
  window.customCards.push({
    type: "battman-house", name: "Battman House", preview: true,
    documentationURL: "https://github.com/AJErazzor/battman/blob/main/docs/cards.md#battman-house",
    description: "The house picture with live prices, solar, home, grid and battery, and flow lines. Every item can be turned off or pointed at your own entity.",
  });
}
