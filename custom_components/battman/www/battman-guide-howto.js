// Battman's guide: the "How do I…?" page (guide/howto/tasks.md) in the Help view.
//
// The page is plain Markdown that GitHub shows as headings and numbered steps. Two hidden markers make it
// interactive here:
//   <!-- guide:task where="Power · Battery mode" uses="power-batterymode.png power-limits.png" -->
//     straight under a task's ### heading: the task becomes a card that opens and closes, with the pictures
//     of the cards it uses, Show me and Open <view> buttons.
//   <!-- guide:show view="power" card="battman-batterymode" target="Curtail" until="popup" say="Tap Curtail" -->
//     inside a numbered step: a stop on the Show me walkthrough (battman-tour.js), which goes to that view, finds
//     the card or the open popup (popup="<text it shows>") and the control showing `target`, rings it with the
//     step's own words, and moves on when `until` happens (press, popup, closed, state:<entity>=<state>, open, next).
// A <!-- guide:howto --> marker near the top is where the filter box and the topic chips go; the topics are
// the page's ## headings.

import { esc } from "./battman-guide-md.js";

export const HOWTO_CSS = `
.howto-find { display: flex; align-items: center; gap: 10px; background: var(--g-card); border: 1px solid var(--g-border);
  border-radius: 12px; padding: 4px 6px 4px 14px; margin: 14px 0 10px; }
.howto-find input { flex: 1; min-width: 0; border: 0; background: transparent; color: var(--g-text); font: inherit; font-size: 15px; padding: 8px 0; outline: none; }
.howto-find .k { font-size: 12px; color: var(--g-muted); border: 1px solid var(--g-border); border-radius: 5px; padding: 1px 6px; margin-right: 6px; }
.howto-chips { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 6px; }
.howto-chips button { font: inherit; font-size: 13px; padding: 6px 13px; border-radius: 16px; cursor: pointer; min-height: 32px;
  background: var(--g-card); color: var(--g-text); border: 1px solid var(--g-border); }
.howto-chips button[aria-pressed="true"] { background: color-mix(in srgb, var(--battman-sky, var(--primary-color)) 26%, transparent); color: var(--battman-sky, var(--primary-color)); border-color: var(--battman-sky, var(--primary-color)); font-weight: 600; }
article h2.howto-group { font-size: 12px; letter-spacing: .07em; text-transform: uppercase; color: var(--g-muted); border: 0; margin: 22px 0 6px; padding: 0; }
article h2.howto-group .hlink { display: none; }
.howto-none { color: var(--g-muted); padding: 10px 2px; }
.task { background: var(--g-card); border: 1px solid var(--g-border); border-radius: 12px; margin: 8px 0; }
.task[hidden] { display: none; }
.task > .task-q { display: flex; align-items: center; gap: 12px; width: 100%; padding: 12px 14px; border: 0; background: transparent; color: var(--g-text);
  font: inherit; font-weight: 600; text-align: left; cursor: pointer; border-radius: 12px; }
.task > .task-q:focus-visible { outline: 2px solid var(--battman-sky, var(--primary-color)); outline-offset: -2px; }
.task-t { flex: 1; min-width: 0; }
.task-where { font-weight: 400; font-size: 12px; color: var(--g-muted); white-space: nowrap; }
.task-chev { color: var(--g-muted); font-size: 12px; transition: transform .15s; }
.task.open .task-chev { transform: rotate(90deg); }
.task-b { display: none; padding: 0 18px 16px 18px; }
.task.open .task-b { display: block; }
.task-uses { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; font-size: 13px; color: var(--g-muted); margin: 0 0 10px; }
.task-uses img { height: 48px; width: auto; border-radius: 6px; border: 1px solid var(--g-border); }
.task-b ol { list-style: none; padding: 0; margin: 0 0 6px; counter-reset: st; }
.task-b ol > li { counter-increment: st; position: relative; padding: 0 0 12px 38px; margin: 0; }
.task-b ol > li::before { content: counter(st); position: absolute; left: 0; top: 0; width: 26px; height: 26px; border-radius: 50%;
  background: var(--g-raised); color: var(--battman-sky, var(--primary-color)); font-weight: 700; font-size: 13px; display: grid; place-items: center; }
.task-b ol > li:not(:last-child)::after { content: ""; position: absolute; left: 12px; top: 30px; bottom: 2px; width: 2px; background: var(--g-raised); }
.task-acts { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-top: 12px; }
.task-acts button { font: inherit; font-size: 14px; font-weight: 600; padding: 8px 16px; border-radius: 9px; cursor: pointer; min-height: 38px;
  border: 1px solid var(--g-border); background: transparent; color: var(--g-text); }
.task-acts button.showme { background: color-mix(in srgb, var(--battman-sky, var(--primary-color)) 8%, transparent); color: var(--battman-sky, var(--primary-color)); border-color: color-mix(in srgb, var(--battman-sky, var(--primary-color)) 55%, transparent); }
@media (max-width: 600px) { .task-b { padding-left: 16px; } .task-where { display: none; } }
`;

const VIEW_NAMES = { power: "Power", curvy: "Curvy", pricy: "Pricy", finances: "Finances", settings: "Settings", log: "Log", theme: "Theme" };
const imgUrl = (name) => new URL(`./guide-images/${name}`, import.meta.url).href;
const argsOf = (el) => { try { return JSON.parse(el.dataset.args || "{}"); } catch (e) { return {}; } };
const plainText = (el) => {
  const c = el.cloneNode(true);
  c.querySelectorAll(".directive, .hlink, img").forEach((x) => x.remove());
  return c.textContent.replace(/\s+/g, " ").trim();
};

// The steps of one task for Show me: one for each guide:show marker, with its step's own words.
export function stepsOf(body) {
  return [...body.querySelectorAll('.directive[data-directive="show"]')].map((d) => {
    const a = argsOf(d), li = d.closest("li");
    return { view: a.view || "", card: a.card || "", popup: a.popup || "", target: a.target || "", until: a.until || "", skipif: a.skipif || "",
      say: a.say || "", body: li ? plainText(li) : "" };
  }).filter((s) => s.view && (s.card || s.popup));
}

// Turn the rendered page into task cards with a filter. go(view) opens a dashboard view; showMe(tour) starts a walkthrough.
export function decorateHowto(root, article, { go, showMe, openAnchor }) {
  if (!root.querySelector("style[data-howto]")) {
    const st = document.createElement("style");
    st.dataset.howto = "1";
    st.textContent = HOWTO_CSS;
    root.appendChild(st);
  }
  const tasks = [];
  for (const marker of [...article.querySelectorAll('.directive[data-directive="task"]')]) {
    const h = marker.previousElementSibling;
    if (!h || h.tagName !== "H3") continue;
    const a = argsOf(marker);
    // the task's anchor sits in a paragraph of its own just before the heading
    const anchorP = h.previousElementSibling && h.previousElementSibling.querySelector(":scope > .anchor:only-child") ? h.previousElementSibling : null;
    const id = anchorP ? anchorP.firstElementChild.id : h.id;
    const group = (() => { let p = h.previousElementSibling; while (p && p.tagName !== "H2") p = p.previousElementSibling; return p; })();
    const sec = document.createElement("section");
    sec.className = "task";
    sec.id = id;
    sec.dataset.group = group ? group.id : "";
    const title = [...h.childNodes].filter((n) => !(n.nodeType === 1 && n.matches(".hlink"))).map((n) => n.textContent).join("").trim();
    sec.innerHTML = `<button class="task-q" type="button" aria-expanded="false">`
      + `<span class="task-t">${esc(title)}</span><span class="task-where">${esc(a.where || "")}</span><span class="task-chev" aria-hidden="true">▶</span></button>`
      + `<div class="task-b"></div>`;
    const body = sec.querySelector(".task-b");
    const uses = String(a.uses || "").split(/\s+/).filter((n) => /^[a-z0-9][a-z0-9-]*\.(png|webp|jpg|svg)$/.test(n));
    if (uses.length) body.innerHTML = `<div class="task-uses">You'll use ${uses.map((n) => `<img src="${esc(imgUrl(n))}" alt="" loading="lazy">`).join("")}</div>`;
    // everything up to the next task (its anchor paragraph or heading) or the next topic
    let n = marker.nextElementSibling;
    while (n && !(n.tagName === "H2" || n.tagName === "H3" || (n.tagName === "P" && n.querySelector(":scope > .anchor:only-child")
      && n.nextElementSibling && n.nextElementSibling.tagName === "H3"))) {
      const next = n.nextElementSibling;
      body.appendChild(n);
      n = next;
    }
    const steps = stepsOf(body);
    const acts = document.createElement("div");
    acts.className = "task-acts";
    if (steps.length) acts.innerHTML = `<button class="showme" type="button">Show me</button>`
      + `<button class="openview" type="button">Open ${esc(VIEW_NAMES[steps[0].view] || steps[0].view)}</button>`;
    body.appendChild(acts);
    h.replaceWith(sec);
    marker.remove();
    if (anchorP) anchorP.remove();
    sec.querySelector(".task-q").addEventListener("click", () => setOpen(sec, !sec.classList.contains("open")));
    const sm = acts.querySelector(".showme"), ov = acts.querySelector(".openview");
    if (sm) sm.addEventListener("click", () => showMe({ title, steps }));
    if (ov) ov.addEventListener("click", () => go(steps[0].view));
    tasks.push({ sec, text: (title + " " + body.textContent).toLowerCase() });
  }
  const groups = [...article.querySelectorAll("h2")].filter((g) => tasks.some((t) => t.sec.dataset.group === g.id));
  groups.forEach((g) => g.classList.add("howto-group"));

  // the filter box and the topic chips, where the page's guide:howto marker is (or after the intro)
  const at = article.querySelector('.directive[data-directive="howto"]');
  const find = document.createElement("div");
  find.innerHTML = `<label class="howto-find"><input type="search" placeholder="Type what you want to do, e.g. &quot;stop exporting&quot;"`
    + ` aria-label="Find a task"><span class="k" aria-hidden="true">/</span></label>`
    + `<div class="howto-chips" role="group" aria-label="Topics"><button type="button" data-topic="" aria-pressed="true">All</button>`
    + groups.map((g) => `<button type="button" data-topic="${esc(g.id)}" aria-pressed="false">${esc(g.textContent.replace(/#$/, "").trim())}</button>`).join("")
    + `</div><p class="howto-none" hidden>No task matches. Try other words, or browse the pages in the contents.</p>`;
  if (at) at.replaceWith(...find.childNodes);
  else if (groups[0]) groups[0].before(...find.childNodes);
  const input = article.querySelector(".howto-find input");
  let topic = "";
  function filter() {
    const words = (input ? input.value : "").toLowerCase().split(/\s+/).filter(Boolean);
    let shown = 0;
    for (const t of tasks) {
      const ok = (!topic || t.sec.dataset.group === topic) && words.every((w) => t.text.includes(w));
      t.sec.hidden = !ok;
      if (ok) shown++;
    }
    groups.forEach((g) => { g.hidden = !tasks.some((t) => t.sec.dataset.group === g.id && !t.sec.hidden); });
    const none = article.querySelector(".howto-none");
    if (none) none.hidden = shown > 0;
    // one match: open it
    if (words.length && shown === 1) setOpen(tasks.find((t) => !t.sec.hidden).sec, true);
  }
  if (input) input.addEventListener("input", filter);
  article.querySelectorAll(".howto-chips button").forEach((b) => b.addEventListener("click", () => {
    topic = b.dataset.topic;
    article.querySelectorAll(".howto-chips button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    filter();
  }));
  // "/" jumps to the filter box
  root.addEventListener("keydown", (e) => {
    if (e.key === "/" && input && root.activeElement !== input && !(e.target && /input|textarea/i.test(e.target.tagName))) {
      e.preventDefault();
      input.focus();
    }
  });
  if (openAnchor) {
    const t = tasks.find((x) => x.sec.id === openAnchor);
    if (t) setOpen(t.sec, true);
  }
  return tasks.length;
}

function setOpen(sec, open) {
  sec.classList.toggle("open", open);
  sec.querySelector(".task-q").setAttribute("aria-expanded", String(open));
}
