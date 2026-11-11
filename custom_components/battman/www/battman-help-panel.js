// Battman's "?" help on a card: the side panel (a bottom sheet on a phone) that a card's "?" tags open.
//
// A card loads this only when you first turn its help on. The words come from the built-in guide
// (custom_components/battman/guide/): a tag names a summary block on a guide page
// (<!-- guide:summary id="settings.buy" -->), and the panel shows that summary, the headings under it as
// chips (each opens its own part of the page here), the whole section on Expand, and a link that opens the
// Help view at that section. So there's one copy of the words: the guide's.

import { esc, renderPage, sectionOf, slugify, summaries } from "./battman-guide-md.js";

export { slugify };

const loaded = new Map();     // guide page id -> Promise<{text, summaries}>

// a guide page's summaries, read once per page load
export function loadPage(hass, page) {
  if (!loaded.has(page)) {
    loaded.set(page, hass.callApi("GET", `battman/guide/page/${page}`).then((r) => ({ text: r.markdown, summaries: summaries(r.markdown) })));
    loaded.get(page).catch(() => loaded.delete(page));
  }
  return loaded.get(page);
}

// the Help view on the dashboard this card is on (/<dashboard>/help)
export function helpView() {
  const dash = window.location.pathname.split("/")[1] || "battman";
  return `/${dash}/help`;
}

// a "?" tag; small for a sub-group
export function tagHtml(id, label, small) {
  return `<button type="button" class="bh-tag${small ? " small" : ""}" data-help="${esc(id)}" aria-label="Help: ${esc(label)}" title="Help: ${esc(label)}">?</button>`;
}

export const TAG_CSS = `
.bh-tag { display: none; flex: none; align-items: center; justify-content: center; width: 28px; height: 24px; padding: 0;
  border-radius: 6px; border: 1px solid var(--battman-sky, var(--primary-color)); color: var(--battman-sky, var(--primary-color));
  background: var(--battman-sky-soft-bg, rgba(127, 127, 127, 0.12)); font: 800 13px/1 var(--primary-font-family, sans-serif); cursor: pointer; }
.bh-tag.small { width: 24px; height: 20px; border-radius: 5px; font-size: 11px; }
/* open: the same outline, tinted deeper (never a solid fill) */
.bh-tag[aria-expanded="true"] { background: color-mix(in srgb, var(--battman-sky, var(--primary-color)) 26%, transparent); color: var(--battman-sky, var(--primary-color)); border-color: var(--battman-sky, var(--primary-color)); box-shadow: 0 0 0 2px color-mix(in srgb, var(--battman-sky, var(--primary-color)) 26%, transparent); }
.bh-tag:focus:not(:focus-visible) { outline: none; }
.helpmode .bh-tag { display: inline-flex; }
.bh-tag:focus-visible { outline: 2px solid var(--battman-sky, var(--primary-color)); outline-offset: 2px; }
`;

const PANEL_CSS = `
.bh-panel { position: fixed; top: var(--header-height, 56px); right: 0; bottom: 0; width: min(400px, 100vw); z-index: 7; box-sizing: border-box;
  display: flex; flex-direction: column; gap: 12px; padding: 16px 20px 20px; overflow-y: auto;
  background: var(--battman-surface-popup, var(--card-background-color)); color: var(--battman-text-bright, var(--primary-text-color));
  border-left: 1px solid var(--battman-border-neutral, var(--divider-color)); box-shadow: -8px 0 24px rgba(0, 0, 0, 0.25);
  font: 14px/1.55 var(--primary-font-family, sans-serif); }
@media (max-width: 700px) {
  .bh-panel { top: auto; left: 0; width: auto; max-height: 75vh; border-left: 0; border-top: 1px solid var(--battman-border-neutral, var(--divider-color));
    border-radius: 16px 16px 0 0; box-shadow: 0 -8px 24px rgba(0, 0, 0, 0.3); padding-bottom: calc(20px + env(safe-area-inset-bottom, 0px)); }
}
.bh-head { display: flex; align-items: center; gap: 8px; }
.bh-crumb { font-size: 11px; letter-spacing: .06em; text-transform: uppercase; color: var(--battman-text-muted, var(--secondary-text-color)); }
.bh-sp { flex: 1; }
.bh-btn { font: inherit; font-size: 12px; padding: 5px 10px; border-radius: 6px; cursor: pointer; min-height: 30px;
  border: 1px solid var(--battman-border-neutral, var(--divider-color)); background: transparent; color: inherit; }
.bh-x { font: inherit; font-size: 18px; width: 32px; height: 32px; border-radius: 8px; cursor: pointer;
  border: 1px solid var(--battman-border-neutral, var(--divider-color)); background: transparent; color: inherit; }
.bh-panel h2 { margin: 0; font-size: 20px; line-height: 1.25; }
.bh-body p { margin: 0 0 10px; }
.bh-body h3, .bh-body h4 { font-size: 15px; margin: 14px 0 4px; }
.bh-body .hlink { display: none; }
.bh-body a { color: var(--battman-sky, var(--primary-color)); }
.bh-body code { font-size: .9em; background: rgba(127, 127, 127, 0.15); padding: 1px 4px; border-radius: 4px; }
.bh-body .callout { border-left: 3px solid var(--battman-amber, #bf8700); padding: 4px 10px; margin: 10px 0; background: rgba(127, 127, 127, 0.08); border-radius: 4px; }
.bh-body .callout.note, .bh-body .callout.tip { border-left-color: var(--battman-sky, var(--primary-color)); }
.bh-body .callout-title { font-weight: 700; margin: 2px 0; }
.bh-body .table { overflow-x: auto; }
.bh-body .gimg { display: block; width: 100%; max-width: 320px; height: auto; margin: 8px 0 12px; border-radius: 8px; border: 1px solid var(--battman-border-neutral, var(--divider-color)); }
.bh-body .gimg.wide { max-width: 100%; }
.bh-body table { border-collapse: collapse; font-size: 13px; }
.bh-body th, .bh-body td { border: 1px solid var(--battman-border-neutral, var(--divider-color)); padding: 4px 8px; text-align: left; }
.bh-body .code { position: relative; }
.bh-body .copy { display: none; }
.bh-body pre { overflow-x: auto; background: rgba(127, 127, 127, 0.12); padding: 8px 10px; border-radius: 6px; }
.bh-lbl { font-size: 11px; letter-spacing: .06em; text-transform: uppercase; color: var(--battman-text-muted, var(--secondary-text-color)); }
.bh-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.bh-chip { font: inherit; font-size: 13px; padding: 6px 12px; border-radius: 16px; cursor: pointer; min-height: 32px; text-align: left;
  border: 0; background: var(--battman-surface-card, rgba(127, 127, 127, 0.15)); color: inherit; }
.bh-all { display: flex; align-items: center; justify-content: center; min-height: 44px; border-radius: 10px; margin-top: 4px;
  border: 1px solid var(--battman-border-neutral, var(--divider-color)); background: transparent; color: inherit; font-weight: 600; text-decoration: none; }
.bh-all:hover { background: rgba(127, 127, 127, 0.12); }
.bh-all:focus-visible { outline: 2px solid var(--battman-sky, var(--primary-color)); outline-offset: 2px; }
`;

// Open (or move) the panel in a card's shadow root for a summary id. from = the tag pressed.
export async function openPanel(root, hass, { page, id, from }) {
  if (!root.querySelector("style[data-bh]")) {
    const st = document.createElement("style");
    st.dataset.bh = "1";
    st.textContent = PANEL_CSS;
    root.appendChild(st);
  }
  const data = await loadPage(hass, page);
  const s = data.summaries[id];
  if (!s) return;
  root.querySelectorAll('.bh-tag[aria-expanded="true"]').forEach((t) => t.setAttribute("aria-expanded", "false"));
  if (from) from.setAttribute("aria-expanded", "true");
  let panel = root.querySelector(".bh-panel");
  if (!panel) {
    panel = document.createElement("aside");
    panel.className = "bh-panel";
    panel.setAttribute("role", "dialog");
    panel.tabIndex = -1;
    root.appendChild(panel);
    panel.addEventListener("click", (e) => onPanelClick(root, panel, e));
  }
  panel._state = { page, id, data, from, view: "summary", child: null };
  draw(panel);
  panel.focus({ preventScroll: true });
}

export function closePanel(root) {
  const panel = root.querySelector(".bh-panel");
  const from = panel && panel._state && panel._state.from;
  if (panel) panel.remove();
  root.querySelectorAll('.bh-tag[aria-expanded="true"]').forEach((t) => t.setAttribute("aria-expanded", "false"));
  if (from && from.isConnected) from.focus({ preventScroll: true });
}

function draw(panel) {
  const { page, id, data, view, child } = panel._state;
  const s = data.summaries[id];
  const lines = data.text.split("\n");
  const head = child || s.head;
  let body;
  if (child) body = renderPage(sectionOf(lines, child), page).html;
  else if (view === "all") body = renderPage(s.section, page).html;
  else body = renderPage(s.markdown, page).html;
  const chips = child ? [] : s.children;
  panel.setAttribute("aria-label", `Help: ${head.title}`);
  panel.innerHTML = `
    <div class="bh-head">
      ${child ? `<button type="button" class="bh-btn" data-bh-back>← ${esc(s.head.title)}</button>` : `<span class="bh-crumb">Help</span>`}
      <span class="bh-sp"></span>
      ${child ? "" : `<button type="button" class="bh-btn" data-bh-expand aria-expanded="${view === "all"}">${view === "all" ? "Less" : "Expand"}</button>`}
      <button type="button" class="bh-x" data-bh-close aria-label="Close help">×</button>
    </div>
    <h2>${esc(head.title)}</h2>
    <div class="bh-body">${body}</div>
    ${chips.length && view !== "all" ? `<div class="bh-lbl">In this section</div><div class="bh-chips">${chips.map((c, i) =>
      `<button type="button" class="bh-chip" data-bh-child="${i}">${esc(c.title)}</button>`).join("")}</div>` : ""}
    <a class="bh-all" href="${esc(`${helpView()}?page=${page}#${head.anchor}`)}" data-bh-go="${esc(head.anchor)}">Browse all help</a>`;
}

// draw again, then put focus back where it makes sense (the pressed control is gone), else on the panel
function redraw(panel, focus) {
  draw(panel);
  panel.scrollTop = 0;
  (panel.querySelector(focus) || panel).focus({ preventScroll: true });
}

// A card redrew its tags: the tag for the open panel is a new element, so mark it and return focus to it later.
export function retag(root, tag) {
  const panel = root.querySelector(".bh-panel");
  if (!panel || !panel._state || panel._state.id !== tag.dataset.help) return;
  tag.setAttribute("aria-expanded", "true");
  panel._state.from = tag;
}

function go(root, url) {
  closePanel(root);
  // going to the Help view: remember where from, so the Help view can offer the way back
  if (url.startsWith(helpView())) {
    try { sessionStorage.setItem("battman.helpFrom", JSON.stringify({ path: window.location.pathname + window.location.search, at: Date.now() })); } catch (e) { /* no storage */ }
  }
  window.history.pushState(null, "", url);
  window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
}

function onPanelClick(root, panel, e) {
  const t = e.target.closest("button, a");
  if (!t) return;
  const st = panel._state;
  if (t.dataset.bhClose !== undefined) return closePanel(root);
  if (t.dataset.bhExpand !== undefined) { st.view = st.view === "all" ? "summary" : "all"; return redraw(panel, "[data-bh-expand]"); }
  if (t.dataset.bhBack !== undefined) {
    const i = st.data.summaries[st.id].children.indexOf(st.child);
    st.child = null;
    return redraw(panel, `[data-bh-child="${i}"]`);
  }
  if (t.dataset.bhChild !== undefined) { st.child = st.data.summaries[st.id].children[Number(t.dataset.bhChild)]; return redraw(panel, "[data-bh-back]"); }
  if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  if (t.dataset.bhGo !== undefined) { e.preventDefault(); return go(root, t.getAttribute("href")); }
  if (t.dataset.page !== undefined) {           // a link in the guide's text: open that page in the Help view
    e.preventDefault();
    const p = t.dataset.page;
    return go(root, `${helpView()}${p === "home" ? "" : `?page=${p}`}${t.dataset.anchor ? `#${t.dataset.anchor}` : ""}`);
  }
  if (t.dataset.ha) { e.preventDefault(); return go(root, t.dataset.ha); }
}
