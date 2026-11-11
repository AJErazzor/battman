// Battman's "Show me": walks through a "How do I…?" task on the person's own dashboard.
//
// startTour({title, steps}) where each step is {view, card, text, say, body} (battman-guide-howto.js reads them from
// the page). For each step it goes to the view on this dashboard, finds the card (the custom element named `card`)
// and, with `text`, the element inside it that shows that text, then dims the page around the card, rings the
// target and shows a bubble: "Step n of m", the step's title and words, Back and Next. Nothing blocks the page: the
// person can press the real control while the bubble points at it. Escape, Done, or leaving the dashboard ends it.
// It lives on document.body, so it keeps going while Home Assistant switches views.

import { findText } from "./battman-help-layer.js";

const VARS = ["--battman-sky", "--battman-text-bright", "--battman-text-muted", "--battman-border-neutral", "--battman-surface-popup",
  "--primary-text-color", "--secondary-text-color", "--primary-color", "--divider-color", "--card-background-color", "--primary-font-family"];

const CSS = `
:host { all: initial; }
.hole { position: fixed; z-index: 8; border-radius: 12px; pointer-events: none; box-shadow: 0 0 0 200vmax rgba(5, 5, 12, 0.62);
  outline: 2px solid color-mix(in srgb, var(--battman-sky, var(--primary-color)) 45%, transparent); outline-offset: 0; transition: all .2s; }
.hole.none { left: 50%; top: 50%; width: 0; height: 0; outline: 0; }
.ring { position: fixed; z-index: 9; box-sizing: border-box; border-radius: 10px; pointer-events: none; border: 3px solid var(--battman-sky, var(--primary-color));
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--battman-sky, var(--primary-color)) 30%, transparent); transition: all .2s; }
.ring[hidden] { display: none; }
.bubble { position: fixed; z-index: 10; box-sizing: border-box; width: min(360px, calc(100vw - 24px)); padding: 14px 16px 12px; border-radius: 14px;
  background: var(--battman-surface-popup, var(--card-background-color, #1e1e2e)); color: var(--battman-text-bright, var(--primary-text-color, #eee));
  border: 2px solid var(--battman-sky, var(--primary-color)); box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45);
  font: 14px/1.45 var(--primary-font-family, system-ui, sans-serif); }
.bubble:focus { outline: none; }
.meta { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--battman-text-muted, var(--secondary-text-color, #aaa)); }
.dots { margin-left: auto; display: flex; gap: 5px; }
.dots i { width: 6px; height: 6px; border-radius: 50%; background: var(--battman-border-neutral, var(--divider-color, #555)); }
.dots i.on { background: var(--battman-sky, var(--primary-color)); }
.say { font-weight: 700; font-size: 16px; margin: 6px 0 4px; }
.body { margin: 0 0 12px; }
.miss { margin: 0 0 12px; color: var(--battman-text-muted, var(--secondary-text-color, #aaa)); font-size: 13px; }
.acts { display: flex; align-items: center; gap: 10px; }
.acts .sp { flex: 1; font-size: 12px; color: var(--battman-text-muted, var(--secondary-text-color, #aaa)); }
button { font: inherit; font-size: 14px; padding: 6px 14px; border-radius: 8px; cursor: pointer; min-height: 34px;
  border: 1px solid var(--battman-border-neutral, var(--divider-color, #555)); background: transparent; color: inherit; }
button.next { background: var(--battman-sky, var(--primary-color)); border-color: var(--battman-sky, var(--primary-color));
  color: var(--card-background-color, #111); font-weight: 700; }
button:focus-visible { outline: 2px solid var(--battman-sky, var(--primary-color)); outline-offset: 2px; }
.pointer { position: absolute; width: 14px; height: 14px; background: inherit; border: inherit; transform: rotate(45deg); }
`;

let tour = null;    // the one running: {host, root, steps, i, title, dash, target, card, frame, expected}

const deepFind = (root, test) => {
  for (const el of root.querySelectorAll("*")) {
    if (test(el)) return el;
    if (el.shadowRoot) { const f = deepFind(el.shadowRoot, test); if (f) return f; }
  }
  return null;
};
// the card's own box: a card drawn by another card (display: contents) has none, so take the one inside
const boxOf = (el) => (el && getComputedStyle(el).display === "contents" && el.firstElementChild ? el.firstElementChild : el);
const visible = (el) => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };

function navigate(path) {
  if (window.location.pathname === path) return;
  window.history.pushState(null, "", path);
  window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
}

export function startTour({ title, steps }) {
  stopTour();
  if (!steps || !steps.length) return;
  const dash = window.location.pathname.split("/")[1] || "battman";
  const host = document.createElement("div");
  host.id = "battman-tour";
  const root = host.attachShadow({ mode: "open" });
  root.innerHTML = `<style>${CSS}</style><div class="hole none"></div><div class="ring" hidden></div>`
    + `<div class="bubble" role="dialog" aria-live="polite" tabindex="-1"></div>`;
  document.body.appendChild(host);
  tour = { host, root, steps, i: 0, title, dash, target: null, card: null, frame: 0, expected: "" };
  root.addEventListener("click", onClick);
  document.addEventListener("keydown", onKey, true);
  window.addEventListener("location-changed", onLocation);
  go(0);
}

export function stopTour() {
  if (!tour) return;
  cancelAnimationFrame(tour.frame);
  document.removeEventListener("keydown", onKey, true);
  window.removeEventListener("location-changed", onLocation);
  tour.host.remove();
  tour = null;
}

function onClick(e) {
  const b = e.target.closest && e.target.closest("button");
  if (!b || !tour) return;
  if (b.dataset.act === "next") (tour.i < tour.steps.length - 1 ? go(tour.i + 1) : stopTour());
  else if (b.dataset.act === "back") go(Math.max(0, tour.i - 1));
  else if (b.dataset.act === "stop") stopTour();
}

function onKey(e) {
  if (!tour) return;
  if (e.key === "Escape") { e.stopPropagation(); stopTour(); }
}

// leaving the dashboard, or going to a view the walkthrough didn't ask for, ends it
function onLocation() {
  if (!tour) return;
  const p = window.location.pathname;
  if (p !== tour.expected && !p.startsWith(`/${tour.dash}/`)) stopTour();
}

async function go(i) {
  const t = tour;
  t.i = i;
  const s = t.steps[i];
  t.expected = `/${t.dash}/${s.view}`;
  t.target = t.card = null;
  draw(s, "finding");
  navigate(t.expected);
  // wait for the view to draw the card (and the text in it)
  const until = Date.now() + 12000;
  while (tour === t && t.i === i && Date.now() < until) {
    const card = deepFind(document, (el) => el.localName === s.card);
    const box = card && boxOf(card);
    const target = box && (s.text ? findText(box, s.text) : box);
    if (box && target && visible(box) && visible(target)) {
      t.card = box;
      t.target = target;
      copyTheme(box);
      target.scrollIntoView({ block: "center", behavior: "smooth" });
      draw(s, "found");
      cancelAnimationFrame(t.frame);
      t.frame = requestAnimationFrame(place);
      return;
    }
    await new Promise((r) => setTimeout(r, 200));
  }
  if (tour === t && t.i === i) draw(s, "missing");
}

function copyTheme(el) {
  const cs = getComputedStyle(el);
  for (const v of VARS) { const val = cs.getPropertyValue(v); if (val) tour.host.style.setProperty(v, val); }
}

function draw(s, state) {
  const { root, steps, i, title } = tour;
  const b = root.querySelector(".bubble");
  const last = i === steps.length - 1;
  b.setAttribute("aria-label", `Step ${i + 1} of ${steps.length}: ${s.say || title}`);
  b.innerHTML = `<div class="meta"><span>Step ${i + 1} of ${steps.length} · ${esc(title)}</span>`
    + `<span class="dots">${steps.map((_, k) => `<i class="${k === i ? "on" : ""}"></i>`).join("")}</span></div>`
    + `<div class="say">${esc(s.say || "")}</div><p class="body">${esc(s.body)}</p>`
    + (state === "missing" ? `<p class="miss">This isn't on the screen. It may be in a folded section, or the card may not be on this view. Open it, or press Next.</p>` : "")
    + (state === "finding" ? `<p class="miss">Finding it…</p>` : "")
    + `<div class="acts"><button data-act="back" ${i ? "" : "disabled"}>Back</button><span class="sp">Esc to stop</span>`
    + `<button class="next" data-act="next">${last ? "Done" : "Next"}</button></div>`;
  if (state !== "found") {
    root.querySelector(".hole").className = state === "missing" ? "hole none" : "hole none";
    root.querySelector(".ring").hidden = true;
    Object.assign(b.style, { left: "50%", top: "50%", transform: "translate(-50%, -50%)" });
  }
  b.focus({ preventScroll: true });
}

// keep the hole, the ring and the bubble on the target while the page scrolls or redraws
function place() {
  const t = tour;
  if (!t || !t.target) return;
  const { root, card, target } = t;
  if (!card.isConnected || !target.isConnected) { go(t.i); return; }
  const c = card.getBoundingClientRect(), r = target.getBoundingClientRect();
  const hole = root.querySelector(".hole"), ring = root.querySelector(".ring"), b = root.querySelector(".bubble");
  hole.className = "hole";
  Object.assign(hole.style, { left: `${c.left - 6}px`, top: `${c.top - 6}px`, width: `${c.width + 12}px`, height: `${c.height + 12}px` });
  ring.hidden = target === card;
  if (!ring.hidden) Object.assign(ring.style, { left: `${r.left - 6}px`, top: `${r.top - 6}px`, width: `${r.width + 12}px`, height: `${r.height + 12}px` });
  // the bubble: under the target if it fits, else above it, else at the bottom of the screen
  const bw = b.offsetWidth, bh = b.offsetHeight, vw = window.innerWidth, vh = window.innerHeight, gap = 16;
  let top = r.bottom + gap;
  if (top + bh > vh - 8) top = r.top - gap - bh;
  if (top < 64) top = Math.max(64, vh - bh - 12);
  const left = Math.min(Math.max(12, r.left + r.width / 2 - bw / 2), vw - bw - 12);
  Object.assign(b.style, { left: `${left}px`, top: `${top}px`, transform: "none" });
  t.frame = requestAnimationFrame(place);
}

const esc = (v) => String(v == null ? "" : v).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
