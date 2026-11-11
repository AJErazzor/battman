// "?" help on the Power, Curvy, Pricy, Finances, Log and Theme views. (The Settings card has its own, in battman-settings.js.)
//
// Cards, or parts of a card, register here while they're on a page: helpRegister("power.house", () => element).
// The id is a summary block's id; its first part names the guide page (PAGES). While anything is registered, and
// Settings -> Dashboard options -> Show help is on, a floating Help button sits at the top right of the page.
// Pressing it loads the panel (battman-help-panel.js) and the guide pages it needs, once each, and puts a "?" on
// the top right of every registered part whose summary exists. The tags and the panel live in one layer on the
// page, not inside the cards, because many cards are drawn by other cards that can't hold them. The layer follows
// each part's position, and takes the theme variables from the cards, so it looks like the view.

const PAGES = { power: "intermediate/power", curvy: "intermediate/curvy", pricy: "intermediate/pricy", finances: "intermediate/finances", log: "intermediate/log", theme: "intermediate/theme" };
const pageOf = (id) => PAGES[String(id).split(".")[0]];
// the parts that have help: a summary block on their page (tests/test_guide.py keeps this in step with the pages).
// Anything else that registers (a Battman card on another view) is ignored, so no Help button shows there.
const SECTIONS = {
  power: ["house", "batterymode", "state", "profitloss", "overrides", "amber5minpricegrid", "limits", "amber24hourforecasttable",
    "gauges", "nemmix"],
  curvy: ["edit", "options", "readouts", "chart", "hours", "buttons", "editing"],
  pricy: ["edit", "options", "readouts", "chart", "preferred", "second", "buttons", "editing"],
  // a part of a busy card is <card>.<part>, and gets a small "?"
  finances: ["costchart", "costchart.ranges", "costchart.totals", "costchart.chart", "costcompare", "billing", "billing.buttons",
    "solar", "solar.financials", "solar.roi"],
  log: ["controls", "log", "mode", "price", "power", "grid", "soc", "solar"],
  theme: ["themes", "palette", "surfaces", "harmonic", "font", "fx", "preview", "yaml"],
};
const HAS_HELP = new Set(Object.entries(SECTIONS).flatMap(([page, ids]) => ids.map((i) => `${page}.${i}`)));
const PARAMETERS = "sensor.battman_parameters";
// the theme variables the button, the tags and the panel use (copied from a card, which is inside the view's theme)
const VARS = ["--battman-sky", "--battman-sky-soft-bg", "--battman-text-bright", "--battman-text-muted", "--battman-border-neutral",
  "--battman-surface-popup", "--battman-surface-card", "--battman-amber", "--primary-text-color", "--primary-color", "--divider-color",
  "--card-background-color", "--primary-font-family"];

const cards = new Map();       // registration token -> {id, measure}
let layer = null;              // {host, root}
let help = null;               // {mod, summaries} once the panel has loaded; summaries grow as pages load
const pagesLoaded = new Set();
let loading = null;
let on = false;
let timer = 0;
let frame = 0;

const hassNow = () => { const h = document.querySelector("home-assistant"); return h && h.hass; };
const shown = () => {
  const st = hassNow() && hassNow().states[PARAMETERS];
  return !(st && st.attributes && st.attributes.showHelp === false);     // on until it's turned off, and while it can't be read
};
const headerHeight = () => parseInt(getComputedStyle(document.documentElement).getPropertyValue("--header-height"), 10) || 56;

const CSS = `
:host { all: initial; }
.helpbtn { position: fixed; right: 16px; z-index: 6; display: inline-flex; align-items: center; gap: 6px; font: 14px/1 var(--primary-font-family, sans-serif);
  padding: 6px 12px; min-height: 34px; border-radius: 8px; cursor: pointer; color: var(--battman-text-bright, var(--primary-text-color));
  border: 1px solid var(--battman-border-neutral, var(--divider-color)); background: var(--battman-surface-popup, var(--card-background-color));
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.35); }
.helpbtn[hidden] { display: none; }
.helpbtn .qtag { display: inline-flex; align-items: center; justify-content: center; width: 20px; height: 17px; border-radius: 5px;
  border: 1px solid currentColor; font-weight: 800; font-size: 11px; line-height: 1; }
.helpbtn[aria-pressed="true"] { background: var(--battman-sky, var(--primary-color)); color: var(--card-background-color);
  border-color: var(--battman-sky, var(--primary-color)); }
.helpbtn:focus-visible { outline: 2px solid var(--battman-sky, var(--primary-color)); outline-offset: 2px; }
.msg { position: fixed; right: 16px; z-index: 6; font: 12px/1.3 var(--primary-font-family, sans-serif); color: var(--battman-text-muted, var(--secondary-text-color)); }
.msg.bad { color: var(--error-color, #db4437); }
.bh-tag { position: fixed; z-index: 5; }
`;

function ensureLayer() {
  if (layer) return layer;
  const host = document.createElement("div");
  host.id = "battman-help-layer";
  const root = host.attachShadow({ mode: "open" });
  root.innerHTML = `<style>${CSS}</style><div class="frame">
    <button type="button" class="helpbtn" aria-pressed="false" hidden><span class="qtag" aria-hidden="true">?</span>Help</button>
    <span class="msg" role="status"></span></div>`;
  document.body.appendChild(host);
  root.querySelector(".helpbtn").addEventListener("click", () => setHelp(!on));
  root.addEventListener("click", (e) => {
    const t = e.target.closest && e.target.closest(".bh-tag");
    if (t && help) help.mod.openPanel(root, hassNow(), { page: pageOf(t.dataset.help), id: t.dataset.help, from: t });
  });
  layer = { host, root, frame: root.querySelector(".frame"), btn: root.querySelector(".helpbtn"), msg: root.querySelector(".msg") };
  return layer;
}

function tell(text, bad) {
  if (!layer) return;
  layer.msg.textContent = text;
  layer.msg.className = "msg" + (bad ? " bad" : "");
}

// copy the view's theme onto the layer, from the first card that's on the page
function copyTheme() {
  for (const { measure } of cards.values()) {
    const el = measure();
    if (!(el instanceof Element) || !el.isConnected) continue;
    const cs = getComputedStyle(el);
    for (const v of VARS) {
      const val = cs.getPropertyValue(v);
      if (val) layer.host.style.setProperty(v, val);
    }
    return;
  }
}

function syncButton() {
  if (!cards.size) return;
  ensureLayer();
  copyTheme();
  const top = headerHeight() + 12;
  layer.btn.style.top = top + "px";
  layer.msg.style.top = top + 8 + "px";
  layer.msg.style.right = layer.btn.hidden ? "16px" : layer.btn.offsetWidth + 28 + "px";
  const ok = shown();
  layer.btn.hidden = !ok;
  if (!ok && on) setHelp(false);
}

// one "?" per registered card that has a summary, kept at the card's top right
function place() {
  frame = 0;
  if (!on || !layer) return;
  const top = headerHeight() + 4;
  const seen = new Set();
  for (const [token, { id, measure, inset }] of cards) {
    const sid = id;
    if (!help.summaries[sid]) continue;
    let tag = layer.root.querySelector(`.bh-tag[data-token="${token.n}"]`);
    if (!tag) {
      layer.frame.insertAdjacentHTML("beforeend", help.mod.tagHtml(sid, sid.split(".").slice(1).join(" "), sid.split(".").length > 2));
      tag = layer.frame.lastElementChild;
      tag.dataset.token = token.n;
      help.mod.retag(layer.root, tag);       // a panel that's open for this card keeps its tag
    }
    seen.add(tag);
    const el = measure();
    const r = el && el.isConnected ? el.getBoundingClientRect() : null;
    const visible = r && r.width > 0 && r.height > 0 && r.bottom > top + 34 && r.top < window.innerHeight;
    tag.style.visibility = visible ? "" : "hidden";
    if (visible) {
      tag.style.top = Math.max(r.top + 8, top) + "px";       // stays in view while the card's top scrolls under the header
      tag.style.left = r.right - inset - tag.offsetWidth + "px";
    }
  }
  layer.root.querySelectorAll(".bh-tag").forEach((t) => { if (!seen.has(t)) t.remove(); });
  frame = requestAnimationFrame(place);
}

async function setHelp(want) {
  ensureLayer();
  const need = [...new Set([...cards.values()].map((c) => pageOf(c.id)).filter(Boolean))].filter((p) => !pagesLoaded.has(p));
  if (want && (!help || need.length)) {
    if (loading) return loading;
    tell("Loading help…");
    loading = (async () => {
      if (!help) {
        const mod = await import("./battman-help-panel.js");
        const st = document.createElement("style");
        st.textContent = mod.TAG_CSS;
        layer.root.appendChild(st);
        help = { mod, summaries: {} };
      }
      for (const page of need) {
        Object.assign(help.summaries, (await help.mod.loadPage(hassNow(), page)).summaries);
        pagesLoaded.add(page);
      }
    })();
    try {
      await loading;
      tell("");
    } catch (e) {
      tell("Help didn't load: " + ((e && e.body && e.body.message) || (e && e.message) || String(e)), true);
      return;
    } finally {
      loading = null;
    }
  }
  on = want;
  layer.frame.classList.toggle("helpmode", on);
  layer.btn.setAttribute("aria-pressed", String(on));
  if (!on) {
    if (help) help.mod.closePanel(layer.root);
    layer.root.querySelectorAll(".bh-tag").forEach((t) => t.remove());
    if (frame) cancelAnimationFrame(frame);
    frame = 0;
  } else if (!frame) {
    frame = requestAnimationFrame(place);
  }
}

function onKey(e) {
  if (e.key !== "Escape" || !on || !layer) return;
  if (layer.root.querySelector(".bh-panel")) help.mod.closePanel(layer.root);
  else setHelp(false);
}

// A card calls this when it's added to the page (once for each part with help) and calls the function it returns
// when it's taken off. id is the summary's id ("power.house", "curvy.chart"); measure() gives the element whose box
// the "?" sits on (a card drawn by another card has no box of its own, so it names the one inside it). inset: how far
// in from the box's right edge the "?" sits (more where the part has its own control in that corner).
export function helpRegister(id, measure, { inset = 8 } = {}) {
  if (!HAS_HELP.has(id)) return () => {};
  const token = { n: String(Math.random()).slice(2) };
  cards.set(token, { id, measure, inset });
  if (cards.size === 1) {
    document.addEventListener("keydown", onKey);
    timer = setInterval(syncButton, 1000);
  }
  syncButton();
  return () => {
    cards.delete(token);
    if (cards.size) return;
    clearInterval(timer);
    document.removeEventListener("keydown", onKey);
    if (on) setHelp(false);
    if (layer) layer.btn.hidden = true;
  };
}

// ── Battman's YAML cards (drawn by the wrapper in battman-cards.js, mostly through button-card) ──

// a YAML card's id in the help, where it isn't the card's own id without hyphens
const YAML_IDS = { "solar-system": "solar" };

// The parts of a YAML card that have their own "?": found by the text they show, inside the cards that draw them.
// [part, first text, last text]: the "?" sits on the box from the first to the last.
const YAML_PARTS = {
  billing: [["buttons", "Bank New Income", "Correct Totals"]],
  solar: [["financials", "Financials"], ["roi", "ROI Timeline"]],
};

// the element under root (through shadow roots) that shows exactly this text
function findText(root, text) {
  const want = text.toLowerCase();
  const walk = (node) => {
    for (const el of node.children || []) {
      if (el.textContent.trim().toLowerCase() === want && ![...el.children].some((c) => c.textContent.trim().toLowerCase() === want)) return el;
      if (el.shadowRoot) { const f = walk(el.shadowRoot); if (f) return f; }
      const f = walk(el);
      if (f) return f;
    }
    return null;
  };
  if (root.shadowRoot) { const f = walk(root.shadowRoot); if (f) return f; }
  return walk(root);
}

// the box from one found element to another, as the layer measures it
function spanOf(a, b) {
  return {
    get isConnected() { return a.isConnected && b.isConnected; },
    getBoundingClientRect() {
      const r = a.getBoundingClientRect(), s = b.getBoundingClientRect();
      return { top: Math.min(r.top, s.top), left: Math.min(r.left, s.left), right: Math.max(r.right, s.right), bottom: Math.max(r.bottom, s.bottom),
        width: Math.max(r.right, s.right) - Math.min(r.left, s.left), height: Math.max(r.bottom, s.bottom) - Math.min(r.top, s.top) };
    },
  };
}

// The wrapper calls this for every YAML card: the card's own "?" (on whichever view's page has it) and its parts'.
// inner() gives the card that draws it. Returns the function that takes them all off.
export function helpRegisterCard(cardId, inner) {
  const key = YAML_IDS[cardId] || String(cardId).replace(/-/g, "");
  const page = Object.keys(SECTIONS).find((p) => HAS_HELP.has(`${p}.${key}`));
  if (!page) return () => {};
  const offs = [helpRegister(`${page}.${key}`, inner)];
  for (const [part, first, last] of YAML_PARTS[key] || []) {
    let found = null;
    offs.push(helpRegister(`${page}.${key}.${part}`, () => {
      if (found && found.isConnected) return found;
      const el = inner();
      const a = el && findText(el, first), b = last ? el && findText(el, last) : a;
      found = a && b ? (a === b ? a : spanOf(a, b)) : null;
      return found;
    }));
  }
  return () => offs.forEach((off) => off());
}
