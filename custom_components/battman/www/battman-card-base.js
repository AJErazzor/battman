// Battman card base: what every Battman card that draws itself shares (the Log, Cost compare,
// Cost chart, Settings and Theme studio cards import it).
//
// - battmanDefine(tag, cls): register a card with HA (and again if HA swaps its registry).
// - BattmanCardBase: the card element. HA hands it hass; the first time, it draws the card's
//   page into its shadow root and starts it (run(card, root)); after that it passes on changes.
//   In HA's card picker it shows the card's preview picture instead.
// - battmanMap(hass, needs): Battman's entity map, checked for the names a card needs.
// - missingEntities / missingThemeVars: the start-up checks. Problems are shown on the card
//   (problemHtml), never papered over.
// - loadChartJs(): Chart.js (shipped in vendor/), loaded once per HA page.
// - cssVar(el, name): a theme colour as the card sees it.

export const FILES = "/battmanfiles";
const DOCS = "https://github.com/AJErazzor/battman/blob/main/docs/cards.md";

// Register a custom element so HA finds it. HA's frontend may swap window.customElements for its
// own registry (a compatibility layer) while it starts; anything registered just before the swap
// is lost to HA. So register now, and again in HA's registry if the swap comes after us.
export function battmanDefine(tag, cls) {
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

// The card in HA's Add card list.
export function battmanPicker(type, name, description, anchor) {
  window.customCards = window.customCards || [];
  if (window.customCards.some((c) => c.type === type)) return;
  window.customCards.push({ type, name, description, preview: true, documentationURL: `${DOCS}#${anchor}` });
}

// Chart.js, loaded once per HA page the first time a card needs it.
let chartLoad = null;
export function loadChartJs() {
  if (window.Chart) return Promise.resolve(window.Chart);
  if (!chartLoad) {
    chartLoad = new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = `${FILES}/vendor/chart.umd.min.js`;
      s.onload = () => (window.Chart ? resolve(window.Chart) : reject(new Error("Chart.js loaded but didn't start")));
      s.onerror = () => { chartLoad = null; reject(new Error(`couldn't load ${s.src}`)); };
      document.head.appendChild(s);
    });
  }
  return chartLoad;
}

// Battman's entity map (Battman name -> entity in this HA), checked for the names a card needs.
// Throws an Error saying what's wrong.
export async function battmanMap(hass, needs) {
  let r;
  try { r = await hass.callApi("GET", "battman/entities"); }
  catch (e) {
    throw new Error("Battman entity map unavailable (" + ((e && e.status_code) || (e && e.message) || e)
      + "). Is the Battman integration installed and set up?");
  }
  const m = (r && r.entities) || {};
  const noEntry = needs.filter((k) => !m[k]);
  if (noEntry.length) throw new Error("Battman entity map has no entry for: " + noEntry.join(", "));
  return m;
}

// "Battman entity map: entity not found: …", or null when every named entity exists.
export function missingEntities(hass, map, keys) {
  const bad = keys.filter((k) => !hass.states[map[k]]).map((k) => k + " → " + map[k]);
  return bad.length ? "Battman entity map: entity not found: " + bad.join(", ") : null;
}

// A theme colour as the card sees it (CSS variables reach it from its view's theme).
export function cssVar(el, name) {
  return getComputedStyle(el).getPropertyValue(name).trim();
}

// "Theme colour … not found — this view needs a Battman theme.", or null when all are there.
export function missingThemeVars(el, vars) {
  const missing = vars.filter((v) => !cssVar(el, v));
  if (!missing.length) return null;
  const shown = missing.slice(0, 4).join(", ") + (missing.length > 4 ? " (+" + (missing.length - 4) + " more)" : "");
  return "Theme colour " + shown + " not found — this view needs a Battman theme.";
}

export const esc = (v) => String(v == null ? "" : v).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

// The box a card shows instead of itself when it can't run.
export function problemHtml(title, msg) {
  return `<div style="padding:16px 18px;font-family:var(--primary-font-family,sans-serif)">`
    + `<div style="font-weight:700;color:var(--error-color,#db4437);margin-bottom:6px">${esc(title)}</div>`
    + `<div style="color:var(--primary-text-color);font-size:14px;line-height:1.4">${esc(msg)}</div></div>`;
}

// True inside HA's card picker (Add card), looking up through the page's shadow roots.
export function inCardPicker(el) {
  for (let n = el; n; n = n.parentNode || n.host) if (n.tagName === "HUI-CARD-PICKER") return true;
  return false;
}

// A Battman card that draws itself. A card sets:
//   static css / static html   its page (styles and markup, into the shadow root)
//   static preview             its picture for HA's card picker (www/previews/)
//   static gridOptions         its size in a sections view
//   run(root)                  starts it once the page is drawn; returns any of
//                              { resume, pause, themeChanged, hassChanged }
export class BattmanCardBase extends HTMLElement {
  static getStubConfig() {
    return {};
  }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    const extra = Object.keys(config || {}).filter((k) => !["type", "grid_options", "view_layout", "visibility"].includes(k));
    if (extra.length) throw new Error(`${this.constructor.cardName} has no options (found: ${extra.join(", ")}).`);
    this._config = config;
  }

  set hass(hass) {
    const old = this._hass;
    this._hass = hass;
    if (!this._built) return this._build();
    if (!this._run) return;
    if (old.themes !== hass.themes && this._run.themeChanged) this._run.themeChanged();
    if (this._run.hassChanged) this._run.hassChanged(old);
  }

  get hass() {
    return this._hass;
  }

  // drawn once it has hass and is on the page (its theme colours only reach it there)
  _build() {
    if (!this._hass || !this.isConnected || this._built) return;
    this._built = true;
    const C = this.constructor;
    if (inCardPicker(this)) {
      this.shadowRoot.innerHTML = `<ha-card style="overflow:hidden"><img src="${FILES}/previews/${C.preview}" alt="${esc(C.cardName)}" style="display:block;width:100%;height:auto"></ha-card>`;
      return;
    }
    this.shadowRoot.innerHTML = `<style>${C.css}</style>${C.html}`;
    this._run = this.run(this.shadowRoot) || {};
  }

  // the card's page couldn't start: say why, in place of the page
  problem(msg) {
    const host = this.shadowRoot.querySelector("ha-card") || this.shadowRoot;
    host.innerHTML = problemHtml(`${this.constructor.cardName} problem`, msg);
  }

  connectedCallback() {
    if (!this._built) return this._build();
    if (this._run && this._run.resume) this._run.resume();
  }

  disconnectedCallback() {
    if (this._run && this._run.pause) this._run.pause();
  }

  getCardSize() {
    return 8;
  }

  getGridOptions() {
    return this.constructor.gridOptions || { columns: "full", rows: "auto" };
  }
}
