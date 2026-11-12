// Battman's "Show me": walks through a "How do I…?" task on the person's own dashboard.
//
// startTour({title, steps}); each step is {view, card, popup, target, until, say, body} (battman-guide-howto.js reads
// them from the page's guide:show markers; the format is in the guide's CLAUDE.md row and tests/test_guide.py).
//
// How it looks: the page is frosted (blurred and tinted in the theme's colours), most strongly behind the step's words and
// fading out from them (on a phone, one even layer). Clear of the frost are a rounded "lens" around the whole control to
// press (padded 8px, its corners one step rounder than the control's) and the card it's on, or as much of the card as
// leaves room for the words beside it, so you see what the control changes. A thin ring in the theme's accent sits on the
// lens; it glows once when it lands and, while the control is the thing to press, breathes outwards. The words sit beside
// the clear part (level with the control's top, or flush with its left above or below it; on a phone, docked at the top
// or bottom, away from it). Everything glides from stop to stop; with reduced motion it jumps.
//
// How it behaves: it never presses anything. A step ends when the real thing happens: the person presses the ringed
// control, a popup opens or closes, or a Home Assistant entity reaches a state. It follows the person into Battman's
// popups (a modal <dialog> makes the rest of the page inert, so the walkthrough moves inside the open one). If a step's
// popup isn't open, it goes back to the step that opens it. A target in a folded section gets a step to open the section
// first. A click anywhere else pauses it ("Back to the walkthrough" / "Stop"); Escape or Stop ends it. When the last step
// happens it stays, says "That's it." and waits for Done (a click elsewhere ends it too).

import { findText, headerBottom } from "./battman-help-layer.js";

const VARS = ["--battman-sky", "--battman-text-bright", "--battman-text-muted", "--battman-border-neutral", "--battman-surface-popup",
  "--battman-surface-card", "--battman-blue", "--battman-blue-soft-bg", "--battman-blue-border-strong", "--primary-text-color",
  "--secondary-text-color", "--primary-color", "--divider-color", "--card-background-color", "--primary-font-family"];
const PAD = 8;
const PRESSABLE = "button, a[href], [role=button], [role=switch], [role=checkbox], [role=tab], select, input, textarea, label, summary, ha-switch, ha-select, ha-checkbox";

const CSS = `
:host { all: initial; }
.layer, .tint { position: fixed; inset: 0; z-index: 2147483000; pointer-events: none; }
.ring { position: fixed; z-index: 2147483001; box-sizing: border-box; pointer-events: none; border: 1.5px solid var(--battman-sky, var(--primary-color, #4af)); }
.ring.glow { animation: bt-glow .9s cubic-bezier(.2,.8,.2,1) both; }
.ring.beckon::after { content: ""; position: absolute; inset: -1.5px; border-radius: inherit; animation: bt-beckon 1.8s cubic-bezier(.2,.8,.2,1) infinite; }
@keyframes bt-glow { 0% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--battman-sky, #4af) 60%, transparent); } 100% { box-shadow: 0 0 0 7px transparent; } }
@keyframes bt-beckon { 0% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--battman-sky, #4af) 45%, transparent); } 70%, 100% { box-shadow: 0 0 0 9px transparent; } }
.words { position: fixed; z-index: 2147483002; box-sizing: border-box; width: min(340px, calc(100vw - 32px)); color: var(--battman-text-bright, var(--primary-text-color, #eee));
  font: 14px/1.45 var(--primary-font-family, system-ui, sans-serif); text-shadow: 0 1px 2px color-mix(in srgb, var(--battman-surface-card, #000) 70%, transparent);
  opacity: 0; transform: translateY(6px); transition: opacity .25s, transform .25s; }
.words.in { opacity: 1; transform: none; }
.meta { font-size: 12px; color: var(--battman-text-muted, var(--secondary-text-color, #aaa)); letter-spacing: .02em; }
.say { font-weight: 700; font-size: 18px; line-height: 1.3; margin: 4px 0 4px; }
.body { margin: 0 0 12px; }
.note { margin: 0 0 12px; font-size: 13px; color: var(--battman-text-muted, var(--secondary-text-color, #aaa)); }
.nav { display: flex; align-items: center; gap: 8px; }
.nav .sp { flex: 1; }
button { font: inherit; font-size: 14px; padding: 6px 14px; border-radius: 8px; cursor: pointer; min-height: 34px; text-shadow: none;
  border: 1px solid var(--battman-border-neutral, var(--divider-color, #555)); color: inherit;
  background: color-mix(in srgb, var(--battman-surface-popup, var(--card-background-color, #222)) 85%, transparent); }
button[disabled] { opacity: .45; cursor: default; }
button.fwd { background: var(--battman-blue-soft-bg, rgba(127,127,127,.15)); color: var(--battman-blue, var(--primary-color)); border-color: var(--battman-blue-border-strong, var(--battman-blue, var(--primary-color))); font-weight: 600; }
button:focus:not(:focus-visible) { outline: none; }
button:focus-visible { outline: 2px solid var(--battman-sky, var(--primary-color)); outline-offset: 2px; }
.pill { position: fixed; z-index: 2147483002; left: 50%; bottom: 16px; transform: translateX(-50%); display: flex; gap: 8px; align-items: center;
  padding: 8px 10px 8px 16px; border-radius: 12px; font: 14px var(--primary-font-family, system-ui, sans-serif);
  background: var(--battman-surface-popup, var(--card-background-color, #222)); color: var(--battman-text-bright, var(--primary-text-color, #eee));
  border: 1px solid var(--battman-border-neutral, var(--divider-color, #555)); box-shadow: 0 6px 20px rgba(0,0,0,.35); }
[hidden] { display: none !important; }
@media (prefers-reduced-motion: reduce) { .words { transition: none; } .ring.glow, .ring.beckon::after { animation: none; } }
`;

let tour = null;

// ── finding things, through shadow roots ─────────────────────────────────────────────────────────
function deepAll(root, test, out = []) {
  for (const el of root.querySelectorAll("*")) {
    if (test(el)) out.push(el);
    if (el.shadowRoot) deepAll(el.shadowRoot, test, out);
  }
  return out;
}
const up = (el) => el.parentElement || (el.getRootNode && el.getRootNode().host) || null;
const within = (el, scope) => { for (let n = el; n; n = up(n)) if (n === scope) return true; return false; };
const boxOf = (el) => (el && getComputedStyle(el).display === "contents" && el.firstElementChild ? el.firstElementChild : el);
const rectOf = (el) => el.getBoundingClientRect();
const shown = (el) => { const r = rectOf(el); return r.width > 0 && r.height > 0; };
// the open modal popups (Battman's, Home Assistant's), last opened last: these sit in the browser's top layer
const openPopups = () => deepAll(document, (el) => el.localName === "dialog" && el.open && el.matches(":modal"));
// every open popup, also a card's own window (Curvy's Manage Presets is a .modal inside the card), not the walkthrough's
const anyPopups = () => deepAll(document, (el) => !(tour && within(el, tour.host)) && ((el.localName === "dialog" && el.open)
  || (el.matches(".modal, [role=dialog], [aria-modal=true]") && el.localName !== "dialog" && shown(el))));
function popupWith(text) {
  if (text === "*") return anyPopups().pop() || null;       // whichever popup is open (the one the step before opened)
  const want = String(text || "").toLowerCase();
  // its words, not its <style>: a Battman popup carries its CSS inside it
  const words = (d) => [...d.querySelectorAll("*")].filter((e) => e.localName !== "style").map((e) => e.childNodes.length ? [...e.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent).join(" ") : "").join(" ").toLowerCase();
  return anyPopups().reverse().find((d) => words(d).includes(want)) || null;
}
// the element showing exactly this text, inside scope (through shadow roots), preferring one that's on screen:
// the same label can be in several panels of a popup, and only the open panel's is visible
function findShown(scope, text) {
  // an icon-only button: target="icon:mdi:information-outline"
  if (/^icon:/.test(text)) {
    const icon = text.slice(5);
    const hits = deepAll(scope.shadowRoot || scope, (el) => (el.getAttribute && el.getAttribute("icon") === icon) || el.icon === icon);
    if (scope.shadowRoot) hits.push(...deepAll(scope, (el) => (el.getAttribute && el.getAttribute("icon") === icon) || el.icon === icon));
    return hits.find(shown) || hits[0] || null;
  }
  // a control with no text of its own (the Theme view's theme picker): target="id:themeSel"
  if (/^id:/.test(text)) {
    const id = text.slice(3);
    const hits = deepAll(scope.shadowRoot || scope, (el) => el.id === id);
    return hits.find(shown) || hits[0] || null;
  }
  const want = String(text).trim().toLowerCase();
  const hits = deepAll(scope.shadowRoot || scope, (el) => el.textContent.trim().toLowerCase() === want
    && ![...el.children].some((c) => c.textContent.trim().toLowerCase() === want));
  if (scope.shadowRoot) hits.push(...deepAll(scope, (el) => el.textContent.trim().toLowerCase() === want
    && ![...el.children].some((c) => c.textContent.trim().toLowerCase() === want)));
  if (!hits.length) {
    // a label broken over two lines ("SELL<br>OVERRIDE" on an Overrides row): read the line break as a space
    const spaced = (n) => [...n.childNodes].map((c) => (c.nodeType === 3 ? c.textContent : c.localName === "br" ? " " : c.nodeType === 1 ? spaced(c) : "")).join("");
    const norm = (n) => spaced(n).replace(/\s+/g, " ").trim().toLowerCase();
    const want2 = want.replace(/\s+/g, " ");
    const test = (el) => el.querySelector && el.querySelector("br") && norm(el) === want2 && ![...el.children].some((c) => norm(c) === want2);
    hits.push(...deepAll(scope.shadowRoot || scope, test));
  }
  return hits.find((h) => shown(h) && onTop(h)) || hits.find(shown) || hits[0] || findText(scope, text);
}
// is el what's actually on screen at its middle (not under another panel, not clipped away)?
function onTop(el) {
  const r = rectOf(el), x = r.left + r.width / 2, y = r.top + r.height / 2;
  if (x < 0 || y < 0 || x > window.innerWidth || y > window.innerHeight) return false;
  let n = document.elementFromPoint(x, y);
  for (let k = 0; n && n.shadowRoot && k < 30; k++) { const m = n.shadowRoot.elementFromPoint(x, y); if (!m || m === n) break; n = m; }
  return !!n && (n === el || within(n, el) || within(el, n) && n.textContent.trim() === el.textContent.trim());
}

// the whole control around a piece of text: the nearest thing that can be pressed, inside scope
function controlAround(el, scope) {
  const pointer = (n) => n && n.nodeType === 1 && n !== scope && within(n, scope) && getComputedStyle(n).cursor === "pointer";
  for (let n = el; n && n !== scope; n = up(n)) {
    if (n.nodeType !== 1) continue;
    // a field's label beside its box (not around it): the whole field, label and box
    if (n.localName === "label" && !n.querySelector(FIELD)) { const f = fieldAround(n, scope); if (f) return f; }
    if (n.matches(PRESSABLE) || n.hasAttribute("data-a")) return n;
    // the hand cursor is inherited, so a label inside a button has it too: take the outermost element that has it,
    // which is the one that sets it (the whole button, the whole row)
    if (pointer(n) && shown(n)) {
      let top = n;
      for (let m = up(n); pointer(m); m = up(m)) if (shown(m)) top = m;
      return top;
    }
  }
  // a setting's name (Settings' rows: the name, then its box): the whole row, name and box
  return fieldAround(el, scope) || el;
}
// the nearest box (up to three levels up, no taller than a row) that holds a field: a label and its box, a setting's row
const FIELD = "input:not([type=hidden]), select, textarea";
function fieldAround(el, scope) {
  let n = up(el);
  for (let k = 0; n && n !== scope && k < 3; k++, n = up(n)) {
    if (n.nodeType !== 1) continue;
    if (rectOf(n).height > 140) return null;          // a whole block, not one field's row
    if ([...n.querySelectorAll(FIELD)].some(shown)) return n;
  }
  return null;
}
// a folded box around el (Settings sections, Log's sections, <details>): [the box, its header to press]
function foldAround(el, scope) {
  for (let n = up(el); n && n !== scope; n = up(n)) {
    if (n.nodeType !== 1) continue;
    if (n.localName === "details" && !n.open) return [n, n.querySelector("summary") || n];
    if (n.classList && (n.classList.contains("folded") || n.classList.contains("collapsed")))
      return [n, n.querySelector(".head, .hd, .title, header, summary, [data-fold]") || n.firstElementChild || n];
  }
  return null;
}

// ── running ─────────────────────────────────────────────────────────────────────────────────────
function navigate(path) {
  if (window.location.pathname === path) return;
  window.history.pushState(null, "", path);
  window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
}
const hass = () => { const h = document.querySelector("home-assistant"); return h && h.hass; };

export function startTour({ title, steps }) {
  stopTour();
  if (!steps || !steps.length) return;
  const host = document.createElement("div");
  host.id = "battman-tour";
  const root = host.attachShadow({ mode: "open" });
  root.innerHTML = `<style>${CSS}</style><div class="stage">`
    + `<div class="layer"></div><div class="layer"></div><div class="layer"></div><div class="layer"></div><div class="tint"></div>`
    + `<div class="ring" hidden></div><div class="words" role="dialog" aria-live="polite" tabindex="-1"></div></div>`
    + `<div class="pill" hidden><span>Walkthrough paused</span><button data-act="resume" class="fwd">Back to the walkthrough</button><button data-act="stop">Stop</button></div>`;
  document.body.appendChild(host);
  tour = { host, root, title, steps, i: -1, dash: window.location.pathname.split("/")[1] || "battman", paused: false, frame: 0, poll: 0,
    step: null, lens: null, scope: null, card: null, popupsAtStart: 0, popupSince: 0, landed: false, last: null, extra: null };
  root.addEventListener("click", onOwnClick);
  document.addEventListener("click", onPageClick, true);
  document.addEventListener("keydown", onKey, true);
  window.addEventListener("location-changed", onLocation);
  go(0);
  tour.poll = setInterval(tick, 200);
  tour.frame = requestAnimationFrame(place);
}

export function stopTour() {
  if (!tour) return;
  clearInterval(tour.poll);
  cancelAnimationFrame(tour.frame);
  document.removeEventListener("click", onPageClick, true);
  document.removeEventListener("keydown", onKey, true);
  window.removeEventListener("location-changed", onLocation);
  if (tour.lensEl && tour.onPress) tour.lensEl.removeEventListener("click", tour.onPress, true);
  tour.host.remove();
  tour = null;
}

function go(i, dir = 1) {
  const t = tour;
  // a step whose outcome is already true ("skipif": Curtail is already on) is passed over
  while (i >= 0 && i < t.steps.length && t.steps[i].skipif && stateIs(t.steps[i].skipif)) i += dir;
  if (i >= t.steps.length) return stopTour();
  if (i < 0) i = 0;
  t.i = Math.max(0, i);
  t.step = t.steps[t.i];
  t.cameBy = t.ended || "";        // how the step before ended ("popup", "press", "state:…"; "" after Back or Next)
  t.ended = "";
  t.extra = null;
  t.landed = false;
  t.lensEl = null;
  t.pressed = false;
  t.finished = false;
  t.popupsAtStart = anyPopups().length;
  t.counted = false;
  t.popupSince = 0;
  if (!t.step.popup) navigate(`/${t.dash}/${t.step.view}`);
  draw("finding");
}

// the step happened: on to the next, or, on the last step, stay on it to show it's done (the person presses Done)
function next() {
  const t = tour;
  if (t.i < t.steps.length - 1) return go(t.i + 1);
  t.finished = true;
  t.root.querySelector(".ring").classList.remove("beckon");
  draw("done");
}

// what the current step points at now: {lens, scope, card} or null
function locate(s) {
  let scope = null, card = null;
  if (s.popup) {
    scope = popupWith(s.popup);
  } else {
    if (window.location.pathname !== `/${tour.dash}/${s.view}`) return null;
    const cs = deepAll(document, (el) => el.localName === s.card);
    const c = cs.find(shown) || cs[0];
    card = c && boxOf(c);
    scope = card;
  }
  if (!scope) return null;
  let lens = scope;
  if (s.target) {
    const txt = findShown(scope, s.target);
    if (!txt) return { scope, card, lens: null };
    lens = controlAround(txt, scope);
  }
  return { scope, card: card || scope, lens };
}

// has the step happened? until may list alternatives ("popup|state:input_select.battman_mode=Sell"); returns which, or ""
function done(s, at) {
  for (const u of String(s.until || "press").split("|")) if (doneOne(s, at, u)) return u;
  return "";
}
function stateIs(cond) {
  const m = /^state:([^=]+)=(.*)$/.exec(String(cond || ""));
  const h = hass();
  return !!(m && h && h.states[m[1]] && same(h.states[m[1]].state, m[2]));
}
const same = (a, b) => String(a) === String(b) || (a !== "" && b !== "" && isFinite(a) && isFinite(b) && Number(a) === Number(b));
function doneOne(s, at, u) {
  if (u === "popup") return anyPopups().length > tour.popupsAtStart;
  if (u === "closed") return !!tour.landed && !popupWith(s.popup);
  if (u.startsWith("state:")) {
    const [e, v] = u.slice(6).split("=");
    const h = hass();
    return !!(h && h.states[e] && same(h.states[e].state, v));
  }
  // the section the target heads (or sits in) is open: nothing folded around it
  if (u === "open") return !!(at && at.lens && shown(at.lens) && !foldAround(at.lens, at.scope));
  return false;    // press: the click handler; next: the button
}

// every 200ms: is the step done, has its popup gone, is its target folded away, where should the stage live
function tick() {
  const t = tour;
  if (!t) return;
  const s = t.step;
  const at = locate(s);
  const why = t.landed && done(s, at);
  if (t.finished) {                // the last step is done: it stays to say so, in the popup still open or the page
    const top = openPopups().pop() || document.body;
    if (t.host.parentNode !== top) top.appendChild(t.host);
    // what it pointed at has gone (the popup closed): the card the popup came from, where the outcome shows
    if (!(t.lensEl && t.lensEl.isConnected && shown(t.lensEl)) && t.homeCard && t.homeCard.isConnected) { t.lensEl = t.homeCard; t.chain = [t.homeCard]; }
    return;
  }
  if (why) { t.ended = why; return next(); }
  // its popup isn't open: if the step before ended without opening one (the question only comes sometimes), this
  // step is skipped; otherwise the person closed it, so back to the step that opens it
  if (s.popup && !(at && at.scope)) {
    if (!t.popupSince) t.popupSince = Date.now();
    if (Date.now() - t.popupSince > 1200) {
      if (t.cameBy && t.cameBy !== "popup" && t.cameBy !== "next") return go(t.i + 1);
      for (let k = t.i - 1; k >= 0; k--) if (String(t.steps[k].until || "").split("|").includes("popup")) return go(k, -1);
    }
  } else t.popupSince = 0;
  // the stage lives in the open popup, or the page can't be pressed through to it
  const top = openPopups().pop() || document.body;
  if (t.host.parentNode !== top) top.appendChild(t.host);
  t.host.dataset.at = (!at ? "no-scope" : !at.lens ? "no-target" : shown(at.lens) ? "shown" : "hidden") + ` ${t.i} ${anyPopups().length}/${t.popupsAtStart}`;   // what it sees (for checks)
  if (!at || !at.lens) { if (t.landed || !t.extra) draw("finding"); return; }
  if (!s.popup && at.card) t.homeCard = at.card;     // the card on the page the walkthrough is working with
  // folded away: a step of its own, to open it first
  if (!shown(at.lens)) {
    const f = foldAround(at.lens, at.scope);
    if (f && (!t.extra || t.extra.box !== f[0])) {
      t.extra = { box: f[0], head: controlAround(f[1], at.scope) };
      land(t.extra.head, at.card, true);
      draw("fold");
    }
    return;
  }
  if (t.extra) t.extra = null;
  if (t.lensEl !== at.lens) {
    land(at.lens, at.card, false);
    draw("found");
  } else if (!inView(at.lens) && Date.now() - (t.scrolled || 0) > 1500) {
    // still off screen (a scroll was cut short as the card redrew): bring it in again
    t.scrolled = Date.now();
    at.lens.scrollIntoView({ block: s.popup ? "nearest" : "center" });
  }
}
const inView = (el) => { const r = rectOf(el); return r.bottom > 0 && r.top < window.innerHeight && r.right > 0 && r.left < window.innerWidth; };

function land(el, card, folding) {
  const t = tour;
  if (t.lensEl && t.onPress) { t.lensEl.removeEventListener("click", t.onPress, true); t.lensEl.removeEventListener("pointerup", t.onPress, true); }
  t.lensEl = el;
  t.chain = chainOf(el, card);
  t.host.dataset.lens = (el.textContent || el.localName).replace(/\s+/g, " ").trim().slice(0, 40);   // what it rings (for checks)
  t.card = card;
  t.landed = true;
  // count the popups open when the step first lands on its own view (not where the walkthrough started), so "popup"
  // means a new one
  if (!folding && !t.counted) { t.popupsAtStart = anyPopups().length; t.counted = true; }
  copyTheme(card || el);
  const u = String(t.step.until || "press");
  const step = t.step;
  t.onPress = folding ? null : () => {
    if (tour && tour.step === step && !tour.pressed && u.split("|").includes("press")) {
      tour.pressed = true;
      setTimeout(() => { if (tour && tour.step === step) { tour.ended = "press"; next(); } }, 150);
    }
  };
  if (t.onPress) { el.addEventListener("click", t.onPress, true); el.addEventListener("pointerup", t.onPress, true); }
  t.scrolled = Date.now();
  if (!folding) el.scrollIntoView({ block: t.step.popup ? "nearest" : "center", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  const ring = t.root.querySelector(".ring");
  ring.hidden = false;
  ring.classList.remove("glow");
  void ring.offsetWidth;
  ring.classList.add("glow");
  ring.classList.toggle("beckon", folding || /press|popup|closed|state:/.test(u));
}

// the boxes from the control up to its card (or popup), smallest first: the walkthrough clears the biggest that leaves
// room for the words beside it, so the whole card shows while the ring stays on the control
function chainOf(el, card) {
  const out = [];
  for (let n = el; n; n = up(n)) {
    if (n.nodeType === 1 && getComputedStyle(n).display !== "contents") out.push(n);
    if (n === card) break;
  }
  return out;
}

function copyTheme(el) {
  const cs = getComputedStyle(el);
  for (const v of VARS) { const val = cs.getPropertyValue(v); if (val) tour.host.style.setProperty(v, val); }
}

const esc = (v) => String(v == null ? "" : v).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

function draw(state) {
  const t = tour;
  const s = t.step, n = t.steps.length, last = t.i === n - 1;
  const w = t.root.querySelector(".words");
  const say = state === "fold" ? `Open ${t.extra && t.extra.head ? t.extra.head.textContent.replace(/\s+/g, " ").trim().split(" ").slice(0, 4).join(" ") : "this section"}` : s.say;
  const body = state === "fold" ? "It's folded. Tap its heading to open it." : s.body;
  const fwd = (String(s.until || "").split("|").includes("next") || state === "done") && state !== "fold";
  const key = `${t.i}|${state}`;
  if (t.last === key) return;
  t.last = key;
  w.classList.remove("in");
  w.innerHTML = `<div class="meta">Step ${t.i + 1} of ${n} · ${esc(t.title)}</div><div class="say">${esc(say)}</div><p class="body">${esc(body)}</p>`
    + (state === "finding" ? `<p class="note">Finding it… If it doesn't show, it may not be on this screen.</p>` : "")
    + (state === "done" ? `<p class="note done">That's it.</p>` : "")
    + `<div class="nav"><button data-act="back" ${t.i ? "" : "disabled"}>Back</button><span class="sp"></span>`
    + (last && fwd ? "" : `<button data-act="stop">Stop</button>`) + (fwd ? `<button data-act="next" class="fwd">${last ? "Done" : "Next"}</button>` : "") + `</div>`;
  if (state === "finding") {
    t.root.querySelector(".ring").hidden = true;
    t.lensEl = null;
    t.chain = [];
  }
  setTimeout(() => { if (tour === t) w.classList.add("in"); }, state === "finding" ? 0 : 320);
}

// every frame: the frost, the ring on the control, the words beside the clear part. The frost is several blur layers and
// a tint, each fading out from the words (on a phone, one even layer); the control and its card (or the part of it that
// leaves room for the words) are clear holes in all of them. Everything glides to where it's going; reduced motion jumps.
const BLURS = [2, 5, 10, 16], REACH = [640, 420, 260, 120], PHONE_BLUR = 8, PHONE_TINT = 55;
const tintOf = (p) => `color-mix(in srgb, var(--battman-surface-card, var(--card-background-color, #111)) ${p}%, transparent)`;
const r1 = (v) => Math.round(v * 10) / 10;
function roundRect({ x, y, w, h, r }) {
  const k = Math.max(0, Math.min(r, w / 2, h / 2));
  return `M${r1(x + k)} ${r1(y)}H${r1(x + w - k)}A${r1(k)} ${r1(k)} 0 0 1 ${r1(x + w)} ${r1(y + k)}V${r1(y + h - k)}`
    + `A${r1(k)} ${r1(k)} 0 0 1 ${r1(x + w - k)} ${r1(y + h)}H${r1(x + k)}A${r1(k)} ${r1(k)} 0 0 1 ${r1(x)} ${r1(y + h - k)}`
    + `V${r1(y + k)}A${r1(k)} ${r1(k)} 0 0 1 ${r1(x + k)} ${r1(y)}Z`;
}
const inside = (a, b) => a.x >= b.x - 1 && a.y >= b.y - 1 && a.x + a.w <= b.x + b.w + 1 && a.y + a.h <= b.y + b.h + 1;

// where the words go outside box B (level with the control's top, or flush with its left); null if they don't fit
function wordsBeside(B, L, ww, wh, vw, vh, phone, topMin) {
  const gap = 20;
  if (phone) {
    const x = (vw - ww) / 2, top = { x, y: topMin }, bottom = { x, y: vh - wh - 16 };
    const fitsTop = B.y >= topMin + wh + gap, fitsBottom = B.y + B.h <= vh - wh - 16 - gap;
    const pref = L.y + L.h / 2 > vh / 2 ? [fitsTop && top, fitsBottom && bottom] : [fitsBottom && bottom, fitsTop && top];
    return pref.find(Boolean) || null;
  }
  const clampY = (y) => Math.min(Math.max(topMin, y), vh - wh - 16), clampX = (x) => Math.min(Math.max(16, x), vw - ww - 16);
  if (vw - (B.x + B.w) - gap >= ww + 16) return { x: B.x + B.w + gap, y: clampY(L.y) };
  if (B.x - gap >= ww + 16) return { x: B.x - gap - ww, y: clampY(L.y) };
  if (vh - (B.y + B.h) - gap >= wh + 16) return { x: clampX(L.x), y: B.y + B.h + gap };
  if (B.y - gap - wh >= topMin) return { x: clampX(L.x), y: B.y - gap - wh };
  return null;
}

function place() {
  const t = tour;
  if (!t) return;
  t.frame = requestAnimationFrame(place);
  const R = t.root;
  const stage = R.querySelector(".stage"), w = R.querySelector(".words");
  stage.hidden = t.paused;
  R.querySelector(".pill").hidden = !t.paused;
  if (t.paused) return;
  const vw = window.innerWidth, vh = window.innerHeight, phone = vw < 600, topMin = Math.max(12, headerBottom() + 12);
  const ww = w.offsetWidth, wh = w.offsetHeight;
  // where everything is going: the lens round the control, the clear part around it, the words
  let L = null, C = null, at = null;
  if (t.lensEl && t.lensEl.isConnected && shown(t.lensEl)) {
    const r = rectOf(t.lensEl);
    const radius = parseFloat(getComputedStyle(t.lensEl).borderTopLeftRadius) || 8;
    L = { x: r.left - PAD, y: r.top - PAD, w: r.width + PAD * 2, h: r.height + PAD * 2, r: radius + 4 };
    const x2 = Math.min(vw - 2, L.x + L.w);       // keep the ring on screen: a control at the edge gets its padding inside
    L.x = Math.max(2, L.x);
    L.w = Math.max(0, x2 - L.x);
    // the biggest box from the card down that, cut to the screen, still leaves room for the words outside it
    const screen = { x: 0, y: topMin - 12, w: vw, h: vh - topMin + 12 };
    for (const el of (t.chain || []).slice().reverse()) {
      if (!el.isConnected || !shown(el)) continue;
      const b = rectOf(el);
      const x = Math.max(screen.x, b.left), y = Math.max(screen.y, b.top);
      const box = { x, y, w: Math.min(screen.x + screen.w, b.right) - x, h: Math.min(screen.y + screen.h, b.bottom) - y,
        r: parseFloat(getComputedStyle(el).borderTopLeftRadius) || 12 };
      if (box.w <= 0 || box.h <= 0 || inside(box, L) || !inside(L, { ...box, x: box.x - PAD, y: box.y - PAD, w: box.w + 2 * PAD, h: box.h + 2 * PAD })) continue;
      const spot = wordsBeside(box, L, ww, wh, vw, vh, phone, topMin);
      if (spot) { C = box; at = spot; break; }
    }
    if (!at) at = wordsBeside(L, L, ww, wh, vw, vh, phone, topMin);
  }
  if (!at) at = { x: (vw - ww) / 2, y: L ? (L.y + L.h / 2 > vh / 2 ? topMin : vh - wh - 16) : (vh - wh) / 2 };
  const F = { x: at.x + ww / 2, y: at.y + wh / 2, r: Math.max(ww, wh) / 2 + 16 };
  // glide: a step of the way there, by the time since the last frame (it settles in about half a second, however
  // slowly the frames come)
  const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const now = performance.now(), k = 1 - Math.exp(-Math.min(200, now - (t.at || now)) / 110);
  t.at = now;
  let moving = false;
  const step = (a, b) => (!a || !b || still ? b : Object.fromEntries(Object.keys(b).map((key) => {
    if (Math.abs(b[key] - a[key]) < 0.5) return [key, b[key]];
    moving = true;
    return [key, a[key] + (b[key] - a[key]) * k];
  })));
  const cur = t.cur || (t.cur = {});
  cur.L = L ? step(cur.L, L) : null;
  cur.C = C ? step(cur.C || cur.L, C) : null;
  cur.F = step(cur.F, F);
  if (t.host.dataset.still !== String(!moving)) t.host.dataset.still = String(!moving);   // (for checks: it has arrived)
  // the frost: holes for the lens and the clear part (one hole when one holds the other)
  // (overlapping holes become one: evenodd would fill the overlap back in)
  const holes = [];
  const apart = (a, b) => a.x + a.w <= b.x || b.x + b.w <= a.x || a.y + a.h <= b.y || b.y + b.h <= a.y;
  if (cur.C && cur.L && !apart(cur.L, cur.C)) {
    const x = Math.min(cur.L.x, cur.C.x), y = Math.min(cur.L.y, cur.C.y);
    holes.push({ x, y, w: Math.max(cur.L.x + cur.L.w, cur.C.x + cur.C.w) - x, h: Math.max(cur.L.y + cur.L.h, cur.C.y + cur.C.h) - y, r: cur.C.r });
  } else for (const b of [cur.L, cur.C]) if (b && b.w > 0 && b.h > 0) holes.push(b);
  const clip = holes.length ? `path(evenodd, "M0 0H${vw}V${vh}H0Z ${holes.map(roundRect).join(" ")}")` : "none";
  const fade = (reach) => `radial-gradient(circle at ${r1(cur.F.x)}px ${r1(cur.F.y)}px, #000 0, #000 ${r1(cur.F.r)}px, transparent ${r1(cur.F.r + reach)}px)`;
  // (a style is written only when it changes: repainting the blur every frame would keep the page busy)
  const put = (el, prop, v) => { const k = `_${prop}`; if (el[k] !== v) { el[k] = v; el.style.setProperty(prop, v); } };
  R.querySelectorAll(".layer").forEach((el, i) => {
    const on = !phone || i === 0;
    if (el.hidden === on) el.hidden = !on;
    if (!on) return;
    const blur = `blur(${phone ? PHONE_BLUR : BLURS[i]}px)`;
    const mask = phone ? "none" : fade(REACH[i]);
    put(el, "backdrop-filter", blur);
    put(el, "-webkit-backdrop-filter", blur);
    put(el, "mask-image", mask);
    put(el, "-webkit-mask-image", mask);
    put(el, "clip-path", clip);
  });
  const tint = R.querySelector(".tint");
  put(tint, "clip-path", clip);
  const { x: fx, y: fy, r: fr } = cur.F;
  put(tint, "background", phone ? tintOf(PHONE_TINT)
    : `radial-gradient(circle at ${r1(fx)}px ${r1(fy)}px, ${tintOf(66)} 0, ${tintOf(52)} ${r1(fr)}px, ${tintOf(18)} ${r1(fr + 220)}px, ${tintOf(0)} ${r1(fr + 460)}px)`);
  // the ring on the control
  const ring = R.querySelector(".ring");
  const Lr = cur.L || { x: vw / 2, y: vh / 2, w: 0, h: 0, r: 0 };
  put(ring, "left", `${Lr.x}px`); put(ring, "top", `${Lr.y}px`); put(ring, "width", `${Math.max(0, Lr.w)}px`);
  put(ring, "height", `${Math.max(0, Lr.h)}px`); put(ring, "border-radius", `${Lr.r}px`);
  put(w, "left", `${at.x}px`); put(w, "top", `${at.y}px`);
}

// ── the person ──────────────────────────────────────────────────────────────────────────────────
function onOwnClick(e) {
  const b = e.target.closest && e.target.closest("button");
  if (!b || !tour) return;
  e.stopPropagation();
  const a = b.dataset.act;
  if (a === "next") { tour.ended = "next"; go(tour.i + 1); }
  else if (a === "back") { tour.ended = ""; go(tour.i - 1, -1); }
  else if (a === "stop") stopTour();
  else if (a === "resume") { tour.paused = false; tour.last = null; draw(tour.lensEl ? "found" : "finding"); }
}

// a click on the page: on the ringed control (or inside the step's popup) carries on; anywhere else pauses
function onPageClick(e) {
  const t = tour;
  // only the person's own clicks: a card's code clicking something itself (the haptic switch) isn't clicking off
  if (!t || t.paused || !e.isTrusted) return;
  const path = e.composedPath ? e.composedPath() : [];
  if (path.includes(t.host)) return;
  if (t.finished) return stopTour();     // done: a click anywhere else just ends it
  if (t.lensEl && path.includes(t.lensEl)) return;
  const s = t.step;
  if (s.popup && path.some((n) => n.localName === "dialog" && n.open)) return;
  if (t.extra && t.lensEl && path.includes(t.lensEl)) return;
  t.paused = true;
}

function onKey(e) {
  if (!tour || e.key !== "Escape") return;
  if (!openPopups().length) e.stopPropagation();
  stopTour();
}

function onLocation() {
  if (!tour) return;
  if (!window.location.pathname.startsWith(`/${tour.dash}/`)) stopTour();
}
