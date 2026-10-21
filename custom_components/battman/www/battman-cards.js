// Battman cards: custom:battman-<id>.
//
// Each Battman card is a plain YAML file (custom_components/battman/cards/<id>.yaml,
// or your own copy in config/battman/cards/<id>.yaml). This file only fetches that
// YAML from Battman (with the entity map filled in) and draws it with HA's own card
// code, so it looks and behaves exactly like the YAML pasted onto a view. It adds no
// box of its own (display: contents). Nothing to edit here: change the card's YAML.
//
// Problems are shown on the card, never hidden: unknown card, bad YAML, a missing map
// entry, a card type that isn't installed (e.g. button-card), or a theme that isn't there.
//
// theme: (optional) draw the card in a theme's colours wherever it's placed.
//   theme: battman        the Battman dashboard's theme (follows it when you change it)
//   theme: Battman Nord   that theme
//   (no theme)            the view's theme, as any card
// In HA's card picker (Add card) a card with no theme: is drawn in PREVIEW_THEME, so the previews are
// in colour; once placed it has no theme: and takes its view's theme, as any card.

const PARAMS = new URL(import.meta.url).searchParams;
const START_IDS = (PARAMS.get("cards") || "").split(",").filter(Boolean);
const DOCS = "https://github.com/AJErazzor/battman/blob/main/docs/cards.md";
const PREVIEW_THEME = "Battman Coffee";   // the card picker's previews (a theme Battman ships)
const THEME_SENSOR = "sensor.battman_theme_mode_colours";   // its `theme` attribute: the Battman dashboard's theme

// Register a custom element so HA finds it. HA's frontend may swap window.customElements for
// its own registry (a compatibility layer) while it starts; anything registered just before the
// swap is lost to HA. So register now, and again in HA's registry if the swap comes after us.
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
    // HA's registry was already in place when we registered (it leaves this marker): nothing to wait for
    if (window.CustomElementRegistryPolyfill) return;
    if (Date.now() - t0 < 30000) setTimeout(watch, 20);
  })();
}


// The theme to use for `theme:` in a card's config. { name } or { problem }.
function themeFor(hass, wanted) {
  let name = wanted;
  if (String(wanted).toLowerCase() === "battman") {
    const st = hass.states[THEME_SENSOR];
    if (!st) return { problem: `theme: battman needs ${THEME_SENSOR}, which doesn't exist (is Battman set up?).` };
    name = st.attributes.theme;
    if (!name) return { problem: `theme: battman: ${st.attributes.problem || "the Battman dashboard has no theme picked"}.` };
  }
  const theme = hass.themes && hass.themes.themes && hass.themes.themes[name];
  if (!theme) return { problem: `Theme “${name}” isn't installed in Home Assistant.` };
  return { name, theme };
}

// True inside HA's card picker (Add card), looking up through the page's shadow roots.
function inCardPicker(el) {
  for (let n = el; n; n = n.parentNode || n.host) if (n.tagName === "HUI-CARD-PICKER") return true;
  return false;
}

// A theme's variables as CSS custom properties (its dark / light mode part on top, like HA does).
function themeVars(hass, theme) {
  const out = {};
  for (const [k, v] of Object.entries(theme)) if (k !== "modes" && typeof v !== "object") out[`--${k}`] = String(v);
  const mode = theme.modes && theme.modes[hass.themes.darkMode ? "dark" : "light"];
  if (mode) for (const [k, v] of Object.entries(mode)) if (typeof v !== "object") out[`--${k}`] = String(v);
  return out;
}

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

  // Added from the card picker: no theme: (the card takes its view's theme), and the card file's
  // grid_options (e.g. columns: full), because HA only reads grid_options on the card as placed.
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
    // a preview in HA's card picker: draw it in PREVIEW_THEME (unless it names a theme)
    this._inPicker = inCardPicker(this);
    if (!this._themeName() && this._themeKeys && this._themeKeys.length) {
      for (const k of this._themeKeys) this.style.removeProperty(k);
      this._themeKeys = [];
      this._themeObj = null;
    }
    if (this._hass) this.hass = this._hass;
  }

  // The theme to draw in: the card's theme:, or PREVIEW_THEME in the card picker, or none (the view's).
  _themeName() {
    return (this._config && this._config.theme) || (this._inPicker ? PREVIEW_THEME : null);
  }

  setConfig(config) {
    this._config = config;
    this._inner = null;
    this._state = "new";
    this._themeObj = null;
    if (!this._themeName()) {
      for (const k of this._themeKeys || []) this.style.removeProperty(k);
      this._themeKeys = [];
    }
    if (this._hass) this.hass = this._hass;
  }

  set hass(hass) {
    this._hass = hass;
    if (this._themeName()) {
      const ok = this._applyTheme();
      if (!ok) return;
      if (this._state === "theme") { this._state = "new"; }   // the theme's back: draw the card
    }
    if (this._inner) this._inner.hass = hass;
    else if (this._state === "new" && this._config) this._build();
  }

  // Put the chosen theme's variables on this element (the card inherits them). False if it can't.
  _applyTheme() {
    const t = themeFor(this._hass, this._themeName());
    if (t.problem) {
      if (this._state !== "theme" || this._themeProblem !== t.problem) {
        this._themeProblem = t.problem;
        this._problem(t.problem);
        this._state = "theme";
      }
      return false;
    }
    if (this._themeObj === t.theme && this._themeDark === this._hass.themes.darkMode) return true;
    const vars = themeVars(this._hass, t.theme);
    for (const k of this._themeKeys || []) if (!(k in vars)) this.style.removeProperty(k);
    for (const [k, v] of Object.entries(vars)) this.style.setProperty(k, v);
    this._themeKeys = Object.keys(vars);
    this._themeObj = t.theme;
    this._themeDark = this._hass.themes.darkMode;
    this._themeProblem = null;
    return true;
  }

  // HA tells a card which kind of view it's in ("grid" = sections view, "panel" = panel view).
  // Pass it on to the card inside: e.g. an iframe card ignores its aspect_ratio and fills
  // the space in those views, so it resizes with the card.
  set layout(value) {
    this._layout = value;
    if (this._inner) this._inner.layout = value;
  }
  get layout() {
    return this._layout;
  }
  set isPanel(value) {
    this._isPanel = value;
    if (this._inner) this._inner.isPanel = value;
  }
  get isPanel() {
    return this._isPanel;
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
    if (this._layout !== undefined) el.layout = this._layout;
    if (this._isPanel !== undefined) el.isPanel = this._isPanel;
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
battmanDefine("battman-card-editor", BattmanCardEditor);

window.customCards = window.customCards || [];
const pickerEntries = new Map();
const cardClasses = new Map();   // tag -> class, made once (registered again if HA swaps its registry)

function defineCard(id, name, description) {
  const tag = `battman-${id}`;
  if (!cardClasses.has(tag)) {
    const cls = class extends BattmanCard {
      static cardId = id;
    };
    cardClasses.set(tag, cls);
    battmanDefine(tag, cls);
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

// ---------------------------------------------------------------------------------------------
// Battman Image: custom:battman-image. Shows one image from Battman's images (www/images/)
// or yours (config/battman/images/), with options for how it fills the card when resized.
//
//   type: custom:battman-image
//   image: battman-main.webp      required: a name from the list (the editor's dropdown)
//   fit: contain                  contain | cover | stretch | actual | shrink
//   position: center              center | top | bottom | left | right | top-left | top-right | bottom-left | bottom-right
//   height: auto                  auto (the image's own shape) | fill (the space the card is given) | a number (px)
//   background: card              card | none | colour  (colour uses background_color)
//   background_color: '#1e1e2e'   any CSS colour, or a theme colour like var(--battman-blue)
//   frame: true                   the card's border and shadow
//   padding: 0                    px
//   radius: 0                     px, the image's corners
//   flip: false                   mirror left to right
//   alt: Battman                  text for screen readers (default: the image name)
//   theme: battman                as other Battman cards
//   dark:   { ...any of image, fit, position, background, background_color, frame, padding, radius, flip, alt }
//   narrow: { ...the same }       narrow wins over dark when both apply
//
// Narrow = a screen under 768 px wide: the same line as HA's "Mobile" visibility condition.
// Problems (no such image, a setting HA doesn't know) show on the card, never a blank space.
// ---------------------------------------------------------------------------------------------

const IMG_FITS = { contain: "contain", cover: "cover", stretch: "fill", actual: "none", shrink: "scale-down" };
const IMG_POSITIONS = {
  center: "center", top: "center top", bottom: "center bottom", left: "left center", right: "right center",
  "top-left": "left top", "top-right": "right top", "bottom-left": "left bottom", "bottom-right": "right bottom",
};
const IMG_BACKGROUNDS = ["card", "none", "colour"];
const IMG_OVERRIDE_KEYS = ["image", "fit", "position", "background", "background_color", "frame", "padding", "radius", "flip", "alt"];
const IMG_KEYS = ["type", "height", "theme", "dark", "narrow", "grid_options", "view_layout", "visibility", ...IMG_OVERRIDE_KEYS];
const IMG_DEFAULTS = { fit: "contain", position: "center", height: "auto", background: "card", frame: true, padding: 0, radius: 0, flip: false };
const NARROW_QUERY = "(max-width: 767px)";
const IMG_FOLDER = "config/battman/images/";

// The image list, once per page load (the editor fetches it fresh, so new files show there).
let imageList = null;
function fetchImages(hass, fresh) {
  if (fresh || !imageList) {
    imageList = hass.callApi("GET", "battman/images");
    imageList.catch(() => { imageList = null; });
  }
  return imageList;
}

// Check a config (or a dark/narrow part of one). Returns a problem message, or "".
function imageConfigProblem(c, where) {
  const at = where ? ` (in ${where})` : "";
  const allowed = where ? IMG_OVERRIDE_KEYS : IMG_KEYS;
  const unknown = Object.keys(c).filter((k) => !allowed.includes(k));
  if (unknown.length) return `Unknown setting${unknown.length > 1 ? "s" : ""}${at}: ${unknown.join(", ")}.`;
  if ("image" in c && (typeof c.image !== "string" || !c.image)) return `image${at} must be an image name.`;
  if ("fit" in c && !(c.fit in IMG_FITS)) return `fit${at} is “${c.fit}”: use ${Object.keys(IMG_FITS).join(", ")}.`;
  if ("position" in c && !(c.position in IMG_POSITIONS)) return `position${at} is “${c.position}”: use ${Object.keys(IMG_POSITIONS).join(", ")}.`;
  if ("background" in c && !IMG_BACKGROUNDS.includes(c.background)) return `background${at} is “${c.background}”: use card, none or colour.`;
  for (const k of ["padding", "radius"]) {
    if (k in c && !(typeof c[k] === "number" && c[k] >= 0 && c[k] <= 200)) return `${k}${at} must be a number from 0 to 200 (px).`;
  }
  for (const k of ["frame", "flip"]) if (k in c && typeof c[k] !== "boolean") return `${k}${at} must be true or false.`;
  if ("height" in c && !(c.height === "auto" || c.height === "fill" || (typeof c.height === "number" && c.height >= 20 && c.height <= 2000))) {
    return `height is “${c.height}”: use auto, fill, or a number of px (20 to 2000).`;
  }
  for (const part of ["dark", "narrow"]) {
    if (part in c) {
      if (!c[part] || typeof c[part] !== "object" || Array.isArray(c[part])) return `${part} must be a set of settings.`;
      const p = imageConfigProblem(c[part], part);
      if (p) return p;
    }
  }
  return "";
}

class BattmanImageCard extends HTMLElement {
  static getStubConfig() {
    return { image: "battman-main.webp" };
  }

  static getConfigElement() {
    return document.createElement("battman-image-editor");
  }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._mq = window.matchMedia(NARROW_QUERY);
    this._onMq = () => this._update();
  }

  connectedCallback() {
    this._mq.addEventListener("change", this._onMq);
    this._update();
  }

  disconnectedCallback() {
    this._mq.removeEventListener("change", this._onMq);
    if (this._ro) { this._ro.disconnect(); this._ro = null; }
  }

  setConfig(config) {
    const problem = imageConfigProblem(config);
    if (problem) throw new Error(`Battman Image: ${problem}`);
    if (!config.image) throw new Error("Battman Image: pick an image (image:).");
    this._config = config;
    this._drawnKey = null;
    if (!config.theme) {
      for (const k of this._themeKeys || []) this.style.removeProperty(k);
      this._themeKeys = [];
      this._themeObj = null;
    }
    this._update();
  }

  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  // The settings in force now: the card's, then dark (in dark mode), then narrow (on a narrow screen).
  _effective() {
    const c = this._config;
    const out = { ...IMG_DEFAULTS, ...c };
    delete out.dark; delete out.narrow;
    if (c.dark && this._hass && this._hass.themes && this._hass.themes.darkMode) Object.assign(out, c.dark);
    if (c.narrow && this._mq.matches) Object.assign(out, c.narrow);
    return out;
  }

  _update() {
    if (!this._config || !this._hass || !this.isConnected) return;
    if (this._config.theme) {
      const t = themeFor(this._hass, this._themeName());
      if (t.problem) return this._problem(t.problem, "theme:" + t.problem);
      if (this._themeObj !== t.theme || this._themeDark !== this._hass.themes.darkMode) {
        const vars = themeVars(this._hass, t.theme);
        for (const k of this._themeKeys || []) if (!(k in vars)) this.style.removeProperty(k);
        for (const [k, v] of Object.entries(vars)) this.style.setProperty(k, v);
        this._themeKeys = Object.keys(vars);
        this._themeObj = t.theme;
        this._themeDark = this._hass.themes.darkMode;
      }
    }
    const eff = this._effective();
    const key = JSON.stringify(eff);
    if (key === this._drawnKey) return;
    this._drawnKey = key;
    const hass = this._hass;
    fetchImages(hass).then(
      (res) => {
        if (this._drawnKey !== key) return;              // settings changed while the list loaded
        const hit = (res.images || []).find((i) => i.name === eff.image);
        if (!hit) {
          return this._problem(`There's no image called “${eff.image}” (Battman's images, or yours in ${res.folder ? "config/" + res.folder + "/" : IMG_FOLDER}).`, key);
        }
        this._draw(eff, hit);
      },
      (e) => this._problem(`Couldn't list Battman's images: ${errText(e)}`, key)
    );
  }

  _draw(eff, hit) {
    const fill = eff.height === "fill";
    const fixed = typeof eff.height === "number";
    const fit = IMG_FITS[eff.fit];
    const pos = IMG_POSITIONS[eff.position];
    const natural = !fill && !fixed && (eff.fit === "actual" || eff.fit === "shrink");
    const justify = eff.position.includes("left") ? "flex-start" : eff.position.includes("right") ? "flex-end" : "center";
    const bg = eff.background === "none" ? "transparent"
      : eff.background === "colour" ? (eff.background_color || "") : "";
    if (eff.background === "colour" && !eff.background_color) {
      return this._problem("background: colour needs background_color (a CSS colour or theme colour).", this._drawnKey);
    }
    const imgCss = [
      "display:block",
      `object-fit:${fit}`,
      `object-position:${pos}`,
      `border-radius:${eff.radius}px`,
      eff.flip ? "transform:scaleX(-1)" : "",
      natural ? `max-width:${eff.fit === "shrink" ? "100%" : "none"};width:auto;height:auto`
        // fill / fixed: the image sits inside the box (so it never makes the box taller)
        : fill || fixed ? `position:absolute;top:${eff.padding}px;left:${eff.padding}px;width:calc(100% - ${2 * eff.padding}px);height:calc(100% - ${2 * eff.padding}px)`
        : "width:100%;height:auto",
    ].filter(Boolean).join(";");
    const boxCss = [
      "box-sizing:border-box",
      `padding:${eff.padding}px`,
      fill ? "height:100%;position:relative" : fixed ? `height:${eff.height}px;position:relative` : "",
      natural ? `display:flex;justify-content:${justify};overflow:hidden` : "",
    ].filter(Boolean).join(";");
    const cardCss = [
      "overflow:hidden",
      fill ? "height:100%" : "",
      eff.frame ? "" : "border:none;box-shadow:none",
      bg ? `background:${bg}` : "",
    ].filter(Boolean).join(";");
    this.style.display = "block";
    this.style.height = fill ? "100%" : "";
    this.shadowRoot.innerHTML = `<style>:host{display:block}</style>
      <ha-card style="${cardCss}"><div class="box" style="${boxCss}"><img style="${imgCss}"></div></ha-card>`;
    const img = this.shadowRoot.querySelector("img");
    img.alt = eff.alt || eff.image.replace(/\.[a-z]+$/i, "");
    const key = this._drawnKey;
    img.addEventListener("error", () => {
      if (this._drawnKey === key) this._problem(`Couldn't load the image “${eff.image}” (${hit.source}).`, key);
    });
    img.src = hit.url;
    if (this._ro) { this._ro.disconnect(); this._ro = null; }
    if (fill) {
      // fill takes the height the card is given: a sections view gives one, other views don't
      const box = this.shadowRoot.querySelector(".box");
      this._ro = new ResizeObserver(() => {
        if (this._drawnKey === key && box.isConnected && box.clientHeight < 2 && this.clientWidth > 0) {
          this._problem("height: fill needs a sections view (it takes the height you give the card there). Use auto or a number of px here.", key);
        }
      });
      this._ro.observe(box);
    }
  }

  _problem(message, key) {
    if (this._ro) { this._ro.disconnect(); this._ro = null; }
    this._drawnKey = key;
    this.style.height = "";
    this.shadowRoot.innerHTML = `<ha-card><div style="padding:12px 16px;font-size:13px;line-height:1.4;color:var(--error-color,#db4437)"><b>Battman card problem</b><br><span></span></div></ha-card>`;
    this.shadowRoot.querySelector("span").textContent = message;
  }

  getCardSize() {
    const h = this._config && this._config.height;
    return typeof h === "number" ? Math.max(1, Math.ceil(h / 50)) : 3;
  }

  getGridOptions() {
    const h = this._config && this._config.height;
    return h === "fill" ? { columns: 12, rows: 4, min_rows: 1, min_columns: 2 } : { columns: 12, rows: "auto", min_columns: 2 };
  }
}
battmanDefine("battman-image", BattmanImageCard);

// The editor: HA's own form, with the image list as a dropdown and a preview of the chosen image.
const IMG_LABELS = {
  image: "Image", fit: "Fit", position: "Position", height_mode: "Height", height_px: "Height (px)",
  background: "Background", background_color: "Colour (e.g. #1e1e2e or var(--battman-blue))", frame: "Card border and shadow",
  padding: "Padding (px)", radius: "Image corner rounding (px)", flip: "Mirror left to right", alt: "Description (for screen readers)",
  theme: "Theme (battman, a theme name, or empty)", dark: "In dark mode", narrow: "On narrow screens (under 768 px, e.g. phones)",
};
const opt = (pairs) => pairs.map(([value, label]) => ({ value, label }));
const FIT_OPTS = opt([["contain", "Contain (whole image)"], ["cover", "Cover (fill, crop edges)"],
  ["stretch", "Stretch (fill, reshape)"], ["actual", "Actual size"], ["shrink", "Shrink only (if too big)"]]);
const POS_OPTS = opt([["center", "Centre"], ["top", "Top"], ["bottom", "Bottom"], ["left", "Left"], ["right", "Right"],
  ["top-left", "Top left"], ["top-right", "Top right"], ["bottom-left", "Bottom left"], ["bottom-right", "Bottom right"]]);
const BG_OPTS = opt([["card", "Card background"], ["none", "None (transparent)"], ["colour", "Colour"]]);
const ONOFF_OPTS = opt([["on", "On"], ["off", "Off"]]);

function imageSchema(imageOpts, data) {
  const sel = (options, required = true) => ({ select: { mode: "dropdown", options } });
  const part = (name) => ({
    type: "expandable", name, title: IMG_LABELS[name], schema: [
      { name: "image", selector: sel(imageOpts) },
      { type: "grid", name: "", flatten: true, schema: [
        { name: "fit", selector: sel(FIT_OPTS) }, { name: "position", selector: sel(POS_OPTS) }] },
      { type: "grid", name: "", flatten: true, schema: [
        { name: "background", selector: sel(BG_OPTS) }, { name: "background_color", selector: { text: {} } }] },
      { type: "grid", name: "", flatten: true, schema: [
        { name: "frame", selector: sel(ONOFF_OPTS) }, { name: "flip", selector: sel(ONOFF_OPTS) }] },
      { type: "grid", name: "", flatten: true, schema: [
        { name: "padding", selector: { number: { min: 0, max: 200, mode: "box", unit_of_measurement: "px" } } },
        { name: "radius", selector: { number: { min: 0, max: 200, mode: "box", unit_of_measurement: "px" } } }] },
      { name: "alt", selector: { text: {} } },
    ],
  });
  return [
    { name: "image", required: true, selector: sel(imageOpts) },
    { type: "grid", name: "", flatten: true, schema: [
      { name: "fit", required: true, selector: sel(FIT_OPTS) }, { name: "position", required: true, selector: sel(POS_OPTS) }] },
    { type: "grid", name: "", flatten: true, schema: [
      { name: "height_mode", required: true, selector: sel(opt([["auto", "Auto (image's shape)"],
        ["fill", "Fill (sections view)"], ["fixed", "Fixed (px)"]])) },
      ...(data.height_mode === "fixed" ? [{ name: "height_px", required: true, selector: { number: { min: 20, max: 2000, mode: "box", unit_of_measurement: "px" } } }] : [])] },
    { type: "grid", name: "", flatten: true, schema: [
      { name: "background", required: true, selector: sel(BG_OPTS) },
      ...(data.background === "colour" ? [{ name: "background_color", required: true, selector: { text: {} } }] : [])] },
    { type: "grid", name: "", flatten: true, schema: [
      { name: "padding", required: true, selector: { number: { min: 0, max: 200, mode: "box", unit_of_measurement: "px" } } },
      { name: "radius", required: true, selector: { number: { min: 0, max: 200, mode: "box", unit_of_measurement: "px" } } }] },
    { type: "grid", name: "", flatten: true, schema: [
      { name: "frame", selector: { boolean: {} } }, { name: "flip", selector: { boolean: {} } }] },
    { name: "alt", selector: { text: {} } },
    { name: "theme", selector: { text: {} } },
    part("narrow"),
    part("dark"),
  ];
}

// card config -> form data, and back. In dark / narrow every field can be left empty (= as above).
function toFormPart(p) {
  const out = { ...(p || {}) };
  for (const k of ["frame", "flip"]) if (k in out) out[k] = out[k] ? "on" : "off";
  return out;
}
function fromFormPart(p) {
  const out = {};
  for (const [k, v] of Object.entries(p || {})) {
    if (v === undefined || v === null || v === "") continue;
    out[k] = k === "frame" || k === "flip" ? v === "on" : v;
  }
  return out;
}
function toForm(config) {
  const c = { ...IMG_DEFAULTS, ...config };
  const data = { ...c, height_mode: typeof c.height === "number" ? "fixed" : c.height, height_px: typeof c.height === "number" ? c.height : undefined };
  delete data.height;
  data.narrow = toFormPart(c.narrow);
  data.dark = toFormPart(c.dark);
  return data;
}
function fromForm(data, previous) {
  const out = { type: "custom:battman-image" };
  // keep the placed card's own layout keys (size, visibility) untouched
  for (const k of ["grid_options", "view_layout", "visibility"]) if (previous && k in previous) out[k] = previous[k];
  for (const k of ["image", "fit", "position", "background", "background_color", "frame", "padding", "radius", "flip", "alt", "theme"]) {
    const v = data[k];
    if (v === undefined || v === null || v === "") continue;
    if (k in IMG_DEFAULTS && IMG_DEFAULTS[k] === v) continue;       // leave defaults out of the YAML
    out[k] = v;
  }
  if (data.height_mode === "fixed") out.height = data.height_px || 200;
  else if (data.height_mode && data.height_mode !== "auto") out.height = data.height_mode;
  for (const part of ["narrow", "dark"]) {
    const p = fromFormPart(data[part]);
    if (Object.keys(p).length) out[part] = p;
  }
  return out;
}

class BattmanImageEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._render();
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) {
      fetchImages(hass, true).then(
        (res) => { this._images = res.images || []; this._folder = res.folder; this._render(); },
        (e) => { this._listProblem = `Couldn't list Battman's images: ${errText(e)}`; this._render(); }
      );
    }
    if (this._form) this._form.hass = hass;
  }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._root) {
      this.innerHTML = `<div class="msg" style="color:var(--error-color,#db4437);margin-bottom:8px"></div>
        <div class="preview" style="margin-bottom:12px;text-align:center"></div><div class="form"></div>
        <p style="color:var(--secondary-text-color);font-size:13px;margin:12px 0 0">Your own images go in
        <code>${IMG_FOLDER}</code> (png, jpg, webp or gif). Battman never touches that folder. Reopen this editor to see new ones.
        <a href="${DOCS}#battman-image" target="_blank" rel="noreferrer">How it works</a></p>`;
      this._root = true;
    }
    const msg = this.querySelector(".msg");
    msg.textContent = this._listProblem || "";
    if (!this._images) return;
    const opts = this._images.map((i) => ({ value: i.name, label: i.source === "battman" ? i.name : `${i.name} (${i.source})` }));
    if (this._config.image && !this._images.some((i) => i.name === this._config.image)) {
      opts.unshift({ value: this._config.image, label: `${this._config.image} (not found)` });
      msg.textContent = `There's no image called “${this._config.image}”. Pick another.`;
    }
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (s) => IMG_LABELS[s.name] || s.name;
      this._form.addEventListener("value-changed", (ev) => {
        ev.stopPropagation();
        const config = fromForm(ev.detail.value, this._config);
        this._config = config;
        this._form.data = toForm(config);
        this._form.schema = imageSchema(this._opts, this._form.data);
        this._preview();
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config }, bubbles: true, composed: true }));
      });
      this.querySelector(".form").append(this._form);
    }
    this._form.hass = this._hass;
    this._opts = opts;
    this._form.data = toForm(this._config);
    this._form.schema = imageSchema(opts, this._form.data);
    this._preview();
  }

  _preview() {
    const box = this.querySelector(".preview");
    const hit = this._images && this._images.find((i) => i.name === this._config.image);
    if (!hit) { box.replaceChildren(); return; }
    let img = box.querySelector("img");
    if (!img) {
      img = document.createElement("img");
      img.style.cssText = "max-width:100%;max-height:120px;border-radius:6px";
      box.append(img);
    }
    if (img.getAttribute("src") !== hit.url) img.src = hit.url;
    img.alt = hit.name;
  }
}
battmanDefine("battman-image-editor", BattmanImageEditor);

if (!window.customCards.some((c) => c.type === "battman-image")) {
  window.customCards.push({
    type: "battman-image", name: "Battman Image", preview: true, documentationURL: `${DOCS}#battman-image`,
    description: "Any of Battman's images (or yours), with fit, position and size options.",
  });
}
