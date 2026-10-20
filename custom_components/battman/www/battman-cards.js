// Battman cards: custom:battman-<id>.
//
// Each Battman card is a plain YAML file (custom_components/battman/cards/<id>.yaml,
// or your own copy in config/battman/cards/<id>.yaml). This file only fetches that
// YAML from Battman (with the entity map filled in) and draws it with HA's own card
// code, so it looks and behaves exactly like the YAML pasted onto a view. It adds no
// box of its own (display: contents). Nothing to edit here: change the card's YAML.
//
// Problems are shown on the card, never hidden: unknown card, bad YAML, a missing map
// entry, or a card type that isn't installed (e.g. button-card).

const PARAMS = new URL(import.meta.url).searchParams;
const START_IDS = (PARAMS.get("cards") || "").split(",").filter(Boolean);
const DOCS = "https://github.com/AJErazzor/battman/blob/main/docs/cards.md";

// One fetch per card per page load (refresh the page to pick up an edited card file).
const loaded = new Map();
function fetchCard(hass, id, fresh) {
  if (fresh || !loaded.has(id)) {
    const p = hass.callApi("GET", `battman/cards/${encodeURIComponent(id)}`);
    p.catch(() => loaded.delete(id));
    loaded.set(id, p);
  }
  return loaded.get(id);
}
function errText(e) {
  return (e && e.body && e.body.message) || (e && e.message) || String(e);
}

class BattmanCard extends HTMLElement {
  static cardId = "";

  // Added from the card picker: bring the card file's grid_options (e.g. columns: full),
  // because HA only reads grid_options on the card as placed.
  static async getStubConfig(hass) {
    try {
      const data = await fetchCard(hass, this.cardId);
      return data.grid_options ? { grid_options: data.grid_options } : {};
    } catch (e) {
      return {};
    }
  }

  static getConfigElement() {
    const ed = document.createElement("battman-card-editor");
    ed.cardId = this.cardId;
    return ed;
  }

  connectedCallback() {
    this.style.display = "contents";
  }

  setConfig(config) {
    this._config = config;
    this._inner = null;
    this._state = "new";
    if (this._hass) this._build();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._inner) this._inner.hass = hass;
    else if (this._state === "new" && this._config) this._build();
  }

  getCardSize() {
    return this._inner && this._inner.getCardSize ? this._inner.getCardSize() : 1;
  }

  getGridOptions() {
    if (this._gridOptions) return this._gridOptions;     // the card file's own grid_options
    return this._inner && this._inner.getGridOptions ? this._inner.getGridOptions() : undefined;
  }

  async _build() {
    this._state = "building";
    const id = this.constructor.cardId;
    let data;
    try {
      data = await fetchCard(this._hass, id);
    } catch (e) {
      return this._problem(`Couldn't load the Battman card “${id}”: ${errText(e)}`);
    }
    if (data.missing_map.length) {
      return this._problem(`Battman entity map has no entry for: ${data.missing_map.join(", ")} (card “${data.name}”).`);
    }
    const missing = [];
    for (const tag of data.needs) {
      if (customElements.get(tag)) continue;
      const ok = await Promise.race([
        customElements.whenDefined(tag).then(() => true),
        new Promise((r) => setTimeout(() => r(false), 5000)),
      ]);
      if (!ok) missing.push(tag);
    }
    if (missing.length) {
      return this._problem(`Card “${data.name}” needs ${missing.join(", ")}, which isn't installed (HACS → Frontend).`);
    }
    let el;
    try {
      const helpers = await window.loadCardHelpers();
      el = helpers.createCardElement(data.config);
    } catch (e) {
      return this._problem(`Card “${data.name}” couldn't be drawn: ${errText(e)}`);
    }
    this._gridOptions = data.grid_options || null;
    el.hass = this._hass;
    this.replaceChildren(el);
    this._inner = el;
    this._state = "ready";
    // the inner card may size itself differently from our placeholder: let HA re-measure
    this.dispatchEvent(new Event("card-visibility-changed", { bubbles: true, composed: true }));
  }

  _problem(message) {
    this._state = "failed";
    this._inner = null;
    const card = document.createElement("ha-card");
    const box = document.createElement("div");
    box.style.cssText = "padding:12px 16px;font-size:13px;line-height:1.4;color:var(--error-color,#db4437)";
    const title = document.createElement("b");
    title.textContent = "Battman card problem";
    box.append(title, document.createElement("br"), message);
    card.append(box);
    this.replaceChildren(card);
  }
}

class BattmanCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (this._drawn || !this._hass) return;
    this._drawn = true;
    const id = this.cardId;
    this.innerHTML = `
      <div style="padding:8px 0;line-height:1.5">
        <p style="margin:0 0 8px">This is the Battman card <b>${id}</b>. It's drawn from Battman's
        <code>cards/${id}.yaml</code> and updates with Battman releases. There's nothing to set here.</p>
        <p style="margin:0 0 12px;color:var(--secondary-text-color)">To change how it looks everywhere,
        edit the card file (see <a href="${DOCS}" target="_blank" rel="noreferrer">Battman cards</a>).
        To make just this copy your own, convert it: you get the full card YAML with your entities
        filled in, and this copy stops updating with Battman.</p>
        <button class="convert" style="font:inherit;padding:6px 14px;border-radius:6px;cursor:pointer;border:1px solid var(--primary-color);background:transparent;color:var(--primary-color)">Convert to plain YAML</button>
        <div class="msg" style="margin-top:8px;color:var(--error-color,#db4437)"></div>
      </div>`;
    this.querySelector(".convert").addEventListener("click", () => this._convert());
  }

  async _convert() {
    const msg = this.querySelector(".msg");
    msg.textContent = "";
    if (!confirm("Convert this copy to plain YAML? It will stop updating with Battman.")) return;
    let data;
    try {
      data = await fetchCard(this._hass, this.cardId, true);
    } catch (e) {
      msg.textContent = `Couldn't load the card: ${errText(e)}`;
      return;
    }
    if (data.missing_map.length) {
      msg.textContent = `Battman entity map has no entry for: ${data.missing_map.join(", ")}.`;
      return;
    }
    this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: data.config }, bubbles: true, composed: true }));
  }
}
if (!customElements.get("battman-card-editor")) customElements.define("battman-card-editor", BattmanCardEditor);

window.customCards = window.customCards || [];
const pickerEntries = new Map();

function defineCard(id, name, description) {
  const tag = `battman-${id}`;
  if (!customElements.get(tag)) {
    customElements.define(tag, class extends BattmanCard {
      static cardId = id;
    });
  }
  let entry = pickerEntries.get(id);
  if (!entry) {
    entry = { type: tag, preview: true, documentationURL: DOCS };
    pickerEntries.set(id, entry);
    window.customCards.push(entry);
  }
  entry.name = `Battman ${name}`;
  entry.description = description || "A Battman card. Updates with Battman releases.";
}

// Cards known when HA started: defined straight away so dashboards can draw them.
for (const id of START_IDS) defineCard(id, id.replace(/[-_]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()), "");

// Then names and descriptions for the card picker (and any card file added since start).
(function names(tries) {
  const ha = document.querySelector("home-assistant");
  const hass = ha && ha.hass;
  if (!hass) {
    if (tries < 120) setTimeout(() => names(tries + 1), 500);
    return;
  }
  hass.callApi("GET", "battman/cards").then(
    (res) => (res.cards || []).forEach((c) => defineCard(c.id, c.name, c.description)),
    (e) => console.error("Battman: couldn't list cards:", errText(e))
  );
})(0);
