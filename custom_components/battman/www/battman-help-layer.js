// "?" help on the Power view's cards. (The Settings card has its own, in battman-settings.js.)
//
// Cards register themselves here while they're on a page: helpRegister(host, "house"). While at least one is,
// and Settings -> Dashboard options -> Show help is on, a floating Help button sits at the top right of the page.
// Pressing it loads the panel (battman-help-panel.js) and the guide's Power page once, and puts a "?" on the
// top right of every card that page has a summary block for ("power.<card>"). The tags and the panel live in one
// layer on the page, not inside the cards, because many cards are drawn by other cards that can't hold them. The
// layer follows each card's position, and takes the theme variables from the cards, so it looks like the view.

const PAGE = "intermediate/power";
const PARAMETERS = "sensor.battman_parameters";
// the theme variables the button, the tags and the panel use (copied from a card, which is inside the view's theme)
const VARS = ["--battman-sky", "--battman-sky-soft-bg", "--battman-text-bright", "--battman-text-muted", "--battman-border-neutral",
  "--battman-surface-popup", "--battman-surface-card", "--battman-amber", "--primary-text-color", "--primary-color", "--divider-color",
  "--card-background-color", "--primary-font-family"];

const cards = new Map();       // registration token -> {id, measure}
let layer = null;              // {host, root}
let help = null;               // {mod, summaries} once loaded
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
    if (t && help) help.mod.openPanel(root, hassNow(), { page: PAGE, id: t.dataset.help, from: t });
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
    if (!el || !el.isConnected) continue;
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
  for (const [token, { id, measure }] of cards) {
    const sid = "power." + id;
    if (!help.summaries[sid]) continue;
    let tag = layer.root.querySelector(`.bh-tag[data-token="${token.n}"]`);
    if (!tag) {
      layer.frame.insertAdjacentHTML("beforeend", help.mod.tagHtml(sid, id));
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
      tag.style.left = r.right - 8 - tag.offsetWidth + "px";
    }
  }
  layer.root.querySelectorAll(".bh-tag").forEach((t) => { if (!seen.has(t)) t.remove(); });
  frame = requestAnimationFrame(place);
}

async function setHelp(want) {
  ensureLayer();
  if (want && !help) {
    if (loading) return loading;
    tell("Loading help…");
    loading = (async () => {
      const mod = await import("./battman-help-panel.js");
      const page = await mod.loadPage(hassNow(), PAGE);
      const st = document.createElement("style");
      st.textContent = mod.TAG_CSS;
      layer.root.appendChild(st);
      help = { mod, summaries: page.summaries };
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

// A card calls this when it's added to the page and calls the function it returns when it's taken off.
// measure() gives the element whose box the "?" sits on (a card drawn by another card has none of its own).
export function helpRegister(id, measure) {
  const token = { n: String(Math.random()).slice(2) };
  cards.set(token, { id, measure });
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
