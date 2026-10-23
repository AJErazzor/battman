// Battman curve editors: what the Curvy (SOC curves) and Pricy (price curves) cards share.
//
// - wireHandlers(root, handlers): the cards' buttons and inputs say what they do in a data-on-*
//   attribute, e.g. data-on-click="switchPeriod('jan')", which calls handlers.switchPeriod('jan').
// - savedIn / NOT_SAVED: a save only says "Saved" once the curves sensor really has it.
// - debugBox, presetMenus, pressFeedback, showNote: the debug box, the Save / Load Preset menus,
//   the press look and phone haptic on buttons, and the amber notes at the top.

// What an argument in a data-on-* attribute means: 'text', a number, this (the element),
// this.value (its value) or event (the event).
function arg(a, el, ev) {
  if (a === "this") return el;
  if (a === "this.value") return el.value;
  if (a === "event") return ev;
  if (/^'.*'$/.test(a)) return a.slice(1, -1);
  const n = Number(a);
  if (a === "" || !isFinite(n)) throw new Error(`Battman: can't read the argument ${a}`);
  return n;
}

export function wireHandlers(root, handlers) {
  function call(el, attr, ev) {
    const text = el.getAttribute(attr).trim();
    const m = /^(\w+)\((.*)\)$/.exec(text);
    if (!m || !handlers[m[1]]) { console.error(`Battman: nothing handles ${attr}="${text}"`); return; }
    const args = m[2].trim() ? m[2].split(",").map((a) => arg(a.trim(), el, ev)) : [];
    Promise.resolve(handlers[m[1]](...args)).catch((e) => console.error(`Battman: ${m[1]}:`, e));
  }
  for (const type of ["click", "change", "input"]) {
    const attr = `data-on-${type}`;
    root.addEventListener(type, (ev) => {
      const el = ev.target.closest && ev.target.closest(`[${attr}]`);
      if (el) call(el, attr, ev);
    });
  }
  // mouseenter / mouseleave don't bubble: found from mouseover / mouseout instead
  for (const [type, attr] of [["mouseover", "data-on-mouseenter"], ["mouseout", "data-on-mouseleave"]]) {
    root.addEventListener(type, (ev) => {
      const el = ev.target.closest && ev.target.closest(`[${attr}]`);
      if (el && !(ev.relatedTarget && el.contains(ev.relatedTarget))) call(el, attr, ev);
    });
  }
}

export const hourLabel = (h) => (h === 0 ? "12am" : h < 12 ? `${h}am` : h === 12 ? "12pm" : `${h - 12}pm`);

// Battman's curves sensors ignore changes while Battman isn't in charge of the battery.
export const NOT_SAVED = "Not saved: Battman didn't take it (it ignores changes while it isn't in charge of the battery)";
function sameData(a, b) {
  if (typeof a === "number" || typeof b === "number") return Math.abs(Number(a) - Number(b)) < 1e-6;
  if (Array.isArray(a)) return Array.isArray(b) && a.length === b.length && a.every((x, i) => sameData(x, b[i]));
  if (a && typeof a === "object") return !!b && typeof b === "object" && Object.keys(a).every((k) => sameData(a[k], b[k]));
  return a === b;
}
// true once the entity's attribute holds `want` (within ms), false if it never does
export async function savedIn(getHass, entityId, attr, want, ms = 5000) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    const h = getHass(), s = h && h.states[entityId];
    if (s && sameData(want, s.attributes[attr])) return true;
    await new Promise((r) => setTimeout(r, 250));
  }
  return false;
}

// The Show Debug box: #show-debug, #debug-box, #debug-content.
export function debugBox($) {
  let shown = false;
  return {
    toggle() {
      shown = $("show-debug").checked;
      $("debug-box").style.display = shown && $("debug-content").innerHTML.trim() ? "block" : "none";
    },
    log(message) {
      const box = $("debug-box");
      if (shown) box.style.display = "block";
      const clean = String(message).replace(/[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{2B00}-\u{2BFF}\u{FE0F}]/gu, "").replace(/^\s+/, "");
      $("debug-content").innerHTML += `[${new Date().toLocaleTimeString()}] ${clean}<br>`;
      box.scrollTop = box.scrollHeight;
    },
    clear() { $("debug-content").innerHTML = ""; },
  };
}

// The Save Preset / Load Preset menus (#save-preset-menu, #load-preset-menu): one open at a time,
// closed by a tap anywhere outside them.
export function presetMenus($) {
  return function toggle(type) {
    const me = $(type === "save" ? "save-preset-menu" : "load-preset-menu");
    $(type === "save" ? "load-preset-menu" : "save-preset-menu").classList.remove("show");
    me.classList.toggle("show");
    if (!me.classList.contains("show")) return;
    setTimeout(() => {
      document.addEventListener("click", function close(e) {
        if (e.composedPath().some((n) => n.classList && n.classList.contains("preset-menu"))) return;
        me.classList.remove("show");
        document.removeEventListener("click", close);
      });
    }, 0);
  };
}

// Press look on .btn / .mode-btn (reliable on iOS where :active often won't fire), and HA's
// haptic event, which the Companion app turns into a vibration.
export function pressFeedback(root) {
  const clear = () => root.querySelectorAll(".btn.pressed, .mode-btn.pressed").forEach((el) => el.classList.remove("pressed"));
  root.addEventListener("pointerdown", (e) => {
    const b = e.target.closest && e.target.closest(".btn, .mode-btn");
    if (!b || b.disabled) return;
    b.classList.add("pressed");
    window.dispatchEvent(new CustomEvent("haptic", { detail: "selection" }));
  }, true);
  for (const ev of ["pointerup", "pointercancel", "pointerleave", "dragend"]) root.addEventListener(ev, clear, true);
}

// An amber note at the top of the editor (something it can work without is missing).
export function showNote(container, msg) {
  const n = document.createElement("div");
  n.style.cssText = "margin:0 0 10px;padding:6px 10px;border-radius:6px;font-size:12px;color:var(--battman-amber);background:var(--battman-amber-soft-bg);border:1px solid var(--battman-amber-border-strong)";
  n.textContent = msg;
  container.insertBefore(n, container.firstChild);
}
