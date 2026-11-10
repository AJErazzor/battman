// Battman Help card (custom:battman-guide): Battman's built-in guide, on the Help view of the Battman dashboard.
//
// This file is all that loads on every Home Assistant page: a small card that, the first time it's shown,
// loads the guide itself (battman-guide-view.js, its Markdown pages and the Markdown reader). Pages that
// don't show the guide never load any of it.

import { battmanDefine, inCardPicker, problemHtml } from "./battman-card-base.js";

const GUIDE_ON_GITHUB = "https://github.com/AJErazzor/battman/blob/main/custom_components/battman/guide/README.md";

class BattmanGuideCard extends HTMLElement {
  static getStubConfig() {
    return {};
  }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    const extra = Object.keys(config || {}).filter((k) => !["type", "grid_options", "view_layout", "visibility"].includes(k));
    if (extra.length) throw new Error(`Battman Help has no options (found: ${extra.join(", ")}).`);
    this._config = config;
  }

  set hass(hass) {
    this._hass = hass;
    if (this._view) this._view.hassChanged(hass);
    else this._start();
  }

  get hass() {
    return this._hass;
  }

  connectedCallback() {
    if (this._view) this._view.resume();
    else this._start();
  }

  disconnectedCallback() {
    if (this._view) this._view.pause();
  }

  // the first time it's on the page with hass: load the guide
  _start() {
    if (this._loading || !this._hass || !this.isConnected) return;
    this._loading = true;
    if (inCardPicker(this)) {
      this.shadowRoot.innerHTML = `<ha-card style="padding:16px 18px"><div style="font-weight:600;margin-bottom:6px">Battman help</div>`
        + `<div style="color:var(--secondary-text-color);font-size:14px;line-height:1.4">Battman's built-in guide. `
        + `Best on its own panel view: the Help view.</div></ha-card>`;
      return;
    }
    this.shadowRoot.innerHTML = `<ha-card style="padding:16px 18px;color:var(--secondary-text-color)">Loading Battman's guide…</ha-card>`;
    import("./battman-guide-view.js")
      .then((m) => { this._view = m.mount(this); })
      .catch((e) => {
        this.shadowRoot.innerHTML = `<ha-card>${problemHtml("Battman help problem",
          `The guide didn't load (${(e && e.message) || e}). Refresh the page; if it stays, restart Home Assistant.`)}</ha-card>`;
      });
  }

  getCardSize() {
    return 12;
  }

  getGridOptions() {
    return { columns: "full", rows: "auto" };
  }
}

battmanDefine("battman-guide", BattmanGuideCard);

window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "battman-guide")) {
  window.customCards.push({
    type: "battman-guide",
    name: "Battman Help",
    description: "Battman's built-in guide: how Battman works and what to do about its Repairs. Best on a panel view of its own.",
    preview: false,
    documentationURL: GUIDE_ON_GITHUB,
  });
}
