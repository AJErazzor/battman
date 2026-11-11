// Battman's built-in guide, drawn inside the Battman Help card (battman-guide.js loads this the first
// time the card is shown).
//
// The guide's pages are Markdown files in custom_components/battman/guide/, listed in its index.yaml;
// Battman serves them at /api/battman/guide. A page is chosen by the view's address:
//   <the Help view>?page=<track>/<page>#<section>     (no page= is the guide's home page)
// so a link from anywhere in Home Assistant can open a page at a section, and Back works.
//
// What's live: the status line at the top (Active, the battery mode, the last engine run, Curtail and
// Battman's open Repairs, read from your Home Assistant; nothing is made up: a value Battman hasn't got
// is shown as "—" or "not found"), and the list of open Repairs where a page asks for it
// (<!-- guide:repairs -->).

import { battmanMap, esc, problemHtml } from "./battman-card-base.js";
import { pageHref, renderPage } from "./battman-guide-md.js";

const NEEDS = ["enable", "mode", "run", "no_export"];

const CSS = `
:host { display: block; container-type: inline-size; }
ha-card { overflow: hidden; color: var(--g-text); background: var(--g-card);
  --g-text: var(--battman-text-bright, var(--primary-text-color));
  --g-muted: var(--battman-text-muted, var(--secondary-text-color));
  --g-card: var(--battman-surface-card, var(--ha-card-background, var(--card-background-color)));
  --g-raised: var(--battman-surface-popup, var(--secondary-background-color));
  --g-border: var(--battman-border-neutral, var(--divider-color));
  --g-link: var(--battman-sky, var(--primary-color));
  --g-accent: var(--battman-blue, var(--primary-color));
  font-family: var(--primary-font-family, sans-serif); }
.top { display: flex; align-items: center; gap: 12px; padding: 14px 20px 10px; border-bottom: 1px solid var(--g-border); }
.top .name { font-size: 18px; font-weight: 700; margin: 0; }
.top .ver { font-size: 12px; color: var(--g-muted); }
.top .spacer { flex: 1; }
button.toc-btn { display: none; }
button { font: inherit; }
.status { display: flex; flex-wrap: wrap; gap: 6px 18px; padding: 10px 20px; font-size: 13px; color: var(--g-muted);
  background: var(--g-raised); border-bottom: 1px solid var(--g-border); }
.status b { color: var(--g-text); font-weight: 600; }
.status .bad b { color: var(--battman-red, var(--error-color)); }
.status a { color: var(--g-link); }
.body { display: grid; grid-template-columns: 250px minmax(0, 1fr); }
nav.toc { padding: 16px 12px 24px 20px; border-right: 1px solid var(--g-border); font-size: 14px; }
nav.toc h2 { font-size: 11px; letter-spacing: .06em; text-transform: uppercase; color: var(--g-muted); margin: 16px 0 6px; font-weight: 600; }
nav.toc h2:first-child { margin-top: 0; }
nav.toc ul { list-style: none; margin: 0; padding: 0; }
nav.toc a { display: block; padding: 5px 8px; border-radius: 6px; color: var(--g-text); text-decoration: none; line-height: 1.3; }
nav.toc a:hover { background: var(--g-raised); }
nav.toc a[aria-current="page"] { background: var(--battman-blue-soft-bg, var(--g-raised)); color: var(--g-accent); font-weight: 600; }
main { padding: 8px 28px 40px; min-width: 0; outline: none; }
article { max-width: 820px; line-height: 1.6; font-size: 15px; }
article h1 { font-size: 26px; line-height: 1.25; margin: 18px 0 12px; }
article h2 { font-size: 20px; margin: 30px 0 8px; padding-top: 6px; border-top: 1px solid var(--g-border); }
article h3 { font-size: 16px; margin: 22px 0 6px; }
article h1, article h2, article h3, article .anchor { scroll-margin-top: 72px; }
.hlink { margin-left: 8px; border: 0; background: none; color: var(--g-muted); cursor: pointer; font-size: .85em;
  opacity: 0; padding: 0 4px; border-radius: 4px; }
h2:hover .hlink, h3:hover .hlink, h4:hover .hlink, .hlink:focus-visible { opacity: 1; }
article a { color: var(--g-link); }
article code { font-family: var(--code-font-family, monospace); font-size: .9em; background: var(--g-raised);
  padding: 1px 5px; border-radius: 4px; }
article .code { position: relative; margin: 12px 0; }
article pre { background: var(--g-raised); border: 1px solid var(--g-border); border-radius: 8px; padding: 12px 14px;
  overflow-x: auto; margin: 0; }
article pre code { background: none; padding: 0; font-size: 13px; line-height: 1.5; }
.copy { position: absolute; top: 6px; right: 6px; font-size: 12px; padding: 3px 9px; border-radius: 6px; cursor: pointer;
  border: 1px solid var(--g-border); background: var(--g-card); color: var(--g-text); }
.gimg { display: block; max-width: 100%; height: auto; margin: 12px 0; border-radius: 10px; border: 1px solid var(--g-border); }
.table { overflow-x: auto; margin: 12px 0; }
article table { border-collapse: collapse; font-size: 14px; min-width: 100%; }
article th, article td { border: 1px solid var(--g-border); padding: 6px 10px; text-align: left; vertical-align: top; }
article th { background: var(--g-raised); }
article details { border: 1px solid var(--g-border); border-radius: 8px; padding: 8px 14px; margin: 12px 0; }
article summary { cursor: pointer; font-weight: 600; }
article kbd { border: 1px solid var(--g-border); border-bottom-width: 2px; border-radius: 4px; padding: 0 5px; font-size: .9em; }
.callout { border-left: 4px solid var(--c); background: var(--cbg); border-radius: 6px; padding: 8px 14px; margin: 14px 0; }
.callout > p:last-child { margin-bottom: 4px; }
.callout-title { font-weight: 700; color: var(--c); margin: 2px 0 4px; }
.callout.note { --c: var(--battman-blue, #2f81f7); --cbg: var(--battman-blue-soft-bg, rgba(47,129,247,.1)); }
.callout.tip { --c: var(--battman-green, #2da44e); --cbg: var(--battman-green-soft-bg, rgba(45,164,78,.1)); }
.callout.important { --c: var(--battman-purple, #8250df); --cbg: var(--battman-purple-soft-bg, rgba(130,80,223,.1)); }
.callout.warning { --c: var(--battman-amber, #bf8700); --cbg: var(--battman-amber-soft-bg, rgba(191,135,0,.12)); }
.callout.caution { --c: var(--battman-red, #cf222e); --cbg: var(--battman-red-soft-bg, rgba(207,34,46,.1)); }
.repairs { border: 1px solid var(--g-border); border-radius: 8px; padding: 10px 14px; margin: 12px 0; background: var(--g-raised); }
.repairs ul { margin: 6px 0 0; padding-left: 20px; }
.muted { color: var(--g-muted); }
.deadlink { text-decoration: underline dotted; }
.problem { padding: 16px 0; }
@container (max-width: 760px) {
  .body { grid-template-columns: minmax(0, 1fr); }
  nav.toc { display: none; border-right: 0; border-bottom: 1px solid var(--g-border); padding: 12px 16px; }
  .open nav.toc { display: block; }
  button.toc-btn { display: inline-block; border: 1px solid var(--g-border); background: var(--g-card); color: var(--g-text);
    border-radius: 6px; padding: 5px 10px; cursor: pointer; font-size: 13px; }
  .top, .status { padding-left: 16px; padding-right: 16px; }
  main { padding: 4px 16px 32px; }
  article h1 { font-size: 22px; }
  .hlink { opacity: 1; }
}
@media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto !important; } }
`;

const HTML = `
<ha-card>
  <div class="frame">
    <div class="top">
      <button class="toc-btn" type="button" aria-expanded="false" aria-controls="toc">Contents</button>
      <p class="name">Battman help</p><span class="ver"></span><span class="spacer"></span>
    </div>
    <div class="status" role="status" aria-label="Battman now"></div>
    <div class="body">
      <nav class="toc" id="toc" aria-label="Guide contents"></nav>
      <main tabindex="-1"><article></article></main>
    </div>
  </div>
</ha-card>`;

// "3 min ago" from an ISO time, or null
function ago(iso) {
  const t = Date.parse(iso);
  if (!Number.isFinite(t)) return null;
  const s = Math.max(0, Math.round((Date.now() - t) / 1000));
  if (s < 90) return "just now";
  if (s < 5400) return `${Math.round(s / 60)} min ago`;
  if (s < 172800) return `${Math.round(s / 3600)} h ago`;
  return `${Math.round(s / 86400)} days ago`;
}

export function mount(card) {
  const root = card.shadowRoot;
  root.innerHTML = `<style>${CSS}</style>${HTML}`;
  const $ = (s) => root.querySelector(s);
  const frame = $(".frame");
  const article = $("article");
  const main = $("main");
  const toc = $("nav.toc");
  const status = $(".status");
  const viewPath = window.location.pathname;   // the Help view this card is on
  let hass = card.hass;
  let index = null;
  let map = null;
  let shown = null;          // the page id on screen
  let repairs;               // Battman's open Repairs: undefined until first read, null when they couldn't be read
  let paused = false;
  let moved = false;         // false until the first page is shown (don't take the focus on load)
  let timer = null;
  const pages = new Map();   // page id -> Markdown (read once per page load)

  const toast = (message) => card.dispatchEvent(new CustomEvent("hass-notification", { detail: { message }, bubbles: true, composed: true }));

  async function copy(text, done) {
    try {
      await navigator.clipboard.writeText(text);
    } catch (e) {
      const ta = document.createElement("textarea");
      ta.value = text;
      root.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
    }
    toast(done);
  }

  // where we are: {page, anchor} from the address
  function here() {
    const page = new URLSearchParams(window.location.search).get("page") || "home";
    let anchor = window.location.hash.slice(1);
    try { anchor = decodeURIComponent(anchor); } catch (e) { /* not encoded: use it as it is */ }
    return { page, anchor };
  }

  // the address of a page on this view, keeping anything else in the address (?kiosk, ?edit=1 …)
  function urlFor(page, anchor) {
    const q = new URLSearchParams(window.location.search);
    if (page === "home") q.delete("page");
    else q.set("page", page);
    const search = q.toString().replace(/%2F/g, "/");
    return viewPath + (search ? `?${search}` : "") + (anchor ? `#${anchor}` : "");
  }

  // open a page: a new entry in the browser's history (Back returns), then location-changed draws it
  function go(page, anchor) {
    window.history.pushState(null, "", urlFor(page, anchor));
    window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
  }

  function scrollTo(anchor) {
    const target = anchor && root.getElementById(anchor);
    if (target) {
      target.scrollIntoView({ block: "start" });
    } else {
      card.scrollIntoView({ block: "start" });
    }
  }

  function drawToc() {
    if (!index) return;
    const link = (p) => `<li><a href="${esc(pageHref(p.id, ""))}" data-page="${esc(p.id)}" data-anchor=""`
      + `${p.id === shown ? ' aria-current="page"' : ""}>${esc(p.title)}</a></li>`;
    toc.innerHTML = `<ul>${link(index.home)}</ul>`
      + index.tracks.map((t) => `<h2>${esc(t.title)}</h2><ul>${t.pages.map(link).join("")}</ul>`).join("");
  }

  function allPages() {
    return index ? [index.home, ...index.tracks.flatMap((t) => t.pages)] : [];
  }

  async function show() {
    if (window.location.pathname !== viewPath || !index) return;
    const { page, anchor } = here();
    if (page === shown) return scrollTo(anchor);
    const known = allPages().find((p) => p.id === page);
    if (!known) {
      shown = page;
      article.innerHTML = `<h1>Page not found</h1><p>The guide has no page called <code>${esc(page)}</code>. `
        + `It may have been renamed. <a href="?" data-page="home" data-anchor="">Go to the guide's home page</a>.</p>`;
      drawToc();
      return;
    }
    let md = pages.get(page);
    if (md == null) {
      try {
        md = (await hass.callApi("GET", `battman/guide/page/${page}`)).markdown;
        pages.set(page, md);
      } catch (e) {
        article.innerHTML = `<div class="problem">${problemHtml("Battman help problem",
          `Couldn't read the page ${page} (${(e && (e.body && e.body.message)) || (e && e.message) || e}).`)}</div>`;
        return;
      }
      if (here().page !== page) return;     // moved on while it loaded
    }
    const out = renderPage(md, page);
    shown = page;
    article.innerHTML = out.html;
    fillDirectives();
    drawToc();
    frame.classList.remove("open");
    $(".toc-btn").setAttribute("aria-expanded", "false");
    if (anchor) scrollTo(anchor);
    else if (moved) {
      scrollTo("");
      main.focus({ preventScroll: true });
    }
    moved = true;
  }

  // ── live parts ────────────────────────────────────────────────────────────────────────────
  function drawStatus() {
    if (!hass) return;
    const st = (key) => (map && hass.states[map[key]]) || null;
    const item = (label, value, bad) => `<span${bad ? ' class="bad"' : ""}>${esc(label)}: <b>${value}</b></span>`;
    if (!map) {
      status.innerHTML = `<span>Battman's entities aren't available: ${esc(mapProblem || "loading…")}</span>`;
      return;
    }
    const enable = st("enable");
    const mode = st("mode");
    const run = st("run");
    const noExport = st("no_export");
    const parts = [];
    parts.push(item("Active", enable ? (enable.state === "on" ? "On" : enable.state === "off" ? "Off" : esc(enable.state)) : "not found",
      !enable || enable.state !== "on"));
    parts.push(item("Mode", mode ? esc(mode.state) : "not found", !mode));
    const last = run && ago(run.attributes.lastRunAt);
    parts.push(item("Last engine run", last ? esc(last) : "—", !last));
    parts.push(item("Curtail", noExport ? (noExport.state === "on" ? "On (exports stopped)" : noExport.state === "off" ? "Off" : esc(noExport.state)) : "not found", !noExport));
    if (repairs) {
      const n = repairs.length;
      parts.push(`<span${n ? ' class="bad"' : ""}>Repairs: <b>${n ? `${n} open` : "none"}</b>`
        + `${n ? ` · <a href="?page=help/repairs" data-page="help/repairs" data-anchor="">what they mean</a>` : ""}</span>`);
    } else {
      parts.push(item("Repairs", "—", false));
    }
    status.innerHTML = parts.join("");
  }

  function fillDirectives() {
    for (const el of article.querySelectorAll(".directive")) {
      const name = el.dataset.directive;
      if (name === "repairs") {
        el.className = "directive repairs";
        if (repairs === undefined) {
          el.innerHTML = `<span class="muted">Checking Battman's open Repairs…</span>`;
        } else if (!repairs) {
          el.innerHTML = `<span class="muted">Your open Battman Repairs couldn't be read here. See Settings → Repairs.</span>`;
        } else if (!repairs.length) {
          el.innerHTML = `<b>Right now:</b> Battman has no open Repairs.`;
        } else {
          el.innerHTML = `<b>Right now, Battman has ${repairs.length === 1 ? "this Repair" : "these Repairs"} open:</b><ul>`
            + repairs.map((r) => {
              const id = r.issue_id.replace(/_/g, "-");
              const known = root.getElementById(id);
              // the heading straight after the section's anchor (<a id> may sit in a paragraph of its own)
              const h = known && [...article.querySelectorAll("h1, h2, h3, h4")]
                .find((x) => known.compareDocumentPosition(x) & Node.DOCUMENT_POSITION_FOLLOWING);
              const title = h
                ? [...h.childNodes].filter((n) => n.nodeName !== "BUTTON").map((n) => n.textContent).join("")
                : r.issue_id;
              return `<li>${known ? `<a href="?page=help/repairs#${esc(id)}" data-page="help/repairs" data-anchor="${esc(id)}">${esc(title)}</a>` : esc(title)}</li>`;
            }).join("") + "</ul>";
        }
      }
    }
  }

  let mapProblem = null;
  async function loadRepairs() {
    try {
      const r = await hass.connection.sendMessagePromise({ type: "repairs/list_issues" });
      repairs = (r.issues || []).filter((i) => i.domain === "battman" && !i.ignored);
    } catch (e) {
      repairs = null;
    }
    drawStatus();
    if (shown) fillDirectives();
  }

  // ── events ────────────────────────────────────────────────────────────────────────────────
  root.addEventListener("click", (ev) => {
    const a = ev.target.closest("a, button");
    if (!a || ev.defaultPrevented || ev.button !== 0 || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
    if (a.matches("button.toc-btn")) {
      const open = frame.classList.toggle("open");
      a.setAttribute("aria-expanded", String(open));
      return;
    }
    if (a.matches("button[data-copy]")) {
      const id = a.dataset.copy;
      copy(window.location.origin + urlFor(shown, id), "Link to this section copied");
      return;
    }
    if (a.matches("button[data-copy-code]")) {
      copy(a.parentElement.querySelector("code").textContent, "Copied");
      return;
    }
    if (a.dataset.page !== undefined) {
      ev.preventDefault();
      const page = a.dataset.page;
      const anchor = a.dataset.anchor || "";
      if (page === shown) {
        window.history.pushState(null, "", anchor ? `#${anchor}` : window.location.pathname + window.location.search);
        scrollTo(anchor);
      } else {
        go(page, anchor);
      }
      return;
    }
    if (a.dataset.ha) {
      ev.preventDefault();
      window.history.pushState(null, "", a.dataset.ha);
      window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
    }
  });

  // listening only while the card is on the page: a card that's been removed holds on to nothing
  const onLocation = () => show();
  function listen(on) {
    const f = on ? "addEventListener" : "removeEventListener";
    window[f]("location-changed", onLocation);
    window[f]("popstate", onLocation);
    clearInterval(timer);
    timer = on ? setInterval(loadRepairs, 30000) : null;
  }

  async function start() {
    try {
      index = await hass.callApi("GET", "battman/guide");
      $(".ver").textContent = index.version ? `v${index.version}` : "";
    } catch (e) {
      article.innerHTML = `<div class="problem">${problemHtml("Battman help problem",
        `Couldn't read the guide's contents (${(e && e.message) || e}). Is the Battman integration set up?`)}</div>`;
      return;
    }
    try {
      map = await battmanMap(hass, NEEDS);
    } catch (e) {
      mapProblem = e.message;
    }
    drawStatus();
    drawToc();
    loadRepairs();
    await show();
  }
  listen(true);
  start();

  // the status line follows hass, redrawn at most every 2 seconds (and always with the latest)
  let redraw = null;
  return {
    hassChanged(h) {
      hass = h;
      if (!paused && !redraw) redraw = setTimeout(() => { redraw = null; drawStatus(); }, 2000);
    },
    pause() {
      paused = true;
      listen(false);
    },
    resume() {
      paused = false;
      listen(true);
      drawStatus();
      loadRepairs();
      show();
    },
  };
}
