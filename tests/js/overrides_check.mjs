// Runs the Overrides card (battman-overrides.js) on a stand-in page with frozen sample states, and writes JSON to the file
// named by its first argument:
//   { snapshots: { "row:<scenario>:<id>" | "strip:<scenario>": html }, results: [{ n, ok, got, exp }] }
// The Python test (tests/test_overrides_card.py) compares the snapshots with what the old card produced and fails on
// any result that isn't ok. Time is frozen (13:30 on 4 Mar 2026, Adelaide) so the output repeats.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const WWW = path.join(HERE, "../../custom_components/battman/www");
const FIX = JSON.parse(fs.readFileSync(path.join(HERE, "../fixtures/overrides_states.json"), "utf8"));
const SC = JSON.parse(fs.readFileSync(path.join(HERE, "../fixtures/overrides_scenarios.json"), "utf8"));

const NOW = Date.parse("2026-03-04T04:00:00Z");
const RealDate = Date;
let skew = 0;   // the frozen clock only moves when a test lets it (gestures need time to pass)
globalThis.Date = class extends RealDate { constructor(...a) { if (a.length === 0) super(NOW + skew); else super(...a); } static now() { return NOW + skew; } };

// the page stand-in
globalThis.window = globalThis;
globalThis.HTMLElement = class { attachShadow() { return {}; } };
globalThis.customElements = { get: () => undefined, define() {} };
const store = {};
globalThis.localStorage = { getItem: (k) => store[k] ?? null, setItem: (k, v) => { store[k] = String(v); } };
globalThis.CustomEvent = class { constructor(n, o) { this.n = n; this.d = o; } };
const cur = { hass: null };
globalThis.document = { querySelector: (q) => (q === "home-assistant" ? { hass: cur.hass } : null), createElement: () => ({}),
  head: { appendChild() {} }, addEventListener() {} };
(0, eval)(fs.readFileSync(path.join(WWW, "battman-lib.js"), "utf8"));
const L = window.BattmanLib;
const C = await import(pathToFileURL(path.join(WWW, "battman-overrides.js")).href);
const CORE = await import(pathToFileURL(path.join(WWW, "battman-overrides-core.js")).href);

// ---- helpers ----
const results = [];
const T = (n, got, exp) => results.push({ n, ok: JSON.stringify(got) === JSON.stringify(exp), got, exp });
const PE = "sensor.battman_parameters", TM = "timer.battman_override_timer";
const MET = new RealDate(NOW - 3600e3).toISOString() + "|5";
const clone = (o) => JSON.parse(JSON.stringify(o));
function world(attrs = {}, extra = {}) {
  const st = clone(FIX);
  Object.assign(st[PE].attributes, clone(attrs));
  for (const k of Object.keys(st[PE].attributes)) if (st[PE].attributes[k] === "__MET__") st[PE].attributes[k] = MET;
  // a forecast: 5-minute intervals from now, cheap in the middle
  st["sensor.amber_billing_interval_forecasts_general_price"] = { state: "x", attributes: { forecasts: Array.from({ length: 96 }, (_, i) => ({
    start_time: new RealDate(NOW + (i + 1) * 300e3).toISOString(), duration: 5, advanced_price_predicted: 0.1 + 0.15 * Math.abs(Math.sin(i / 12)) }) ) } };
  Object.assign(st, clone(extra));
  const sent = [], calls = [];
  const hass = { states: st, connection: { sendMessage: (m) => sent.push(m) }, callService: (d, s, x) => calls.push([d, s, x]),
    callApi: async () => ({ entities: { parameters: PE, override_timer: TM, sell_total: "sensor.battman_sell_total", buy_total: "sensor.battman_buy_total", apply_scene_script: "script.battman_apply_scene" } }) };
  cur.hass = hass;
  return { st, hass, sent, calls, ev: () => sent.map((m) => m.event_data) };
}
const E = { params: PE, soc: "sensor.sigen_plant_battery_state_of_charge", capacity: "sensor.sigen_plant_rated_energy_capacity",
  sellTotal: "sensor.battman_sell_total", buyTotal: "sensor.battman_buy_total" };

// ---- 1. what the rows and the strip draw, for the scenarios the old card was recorded on ----
const rowNorm = (h) => h.replace(/^<div[^>]*>/, "").replace(/\s+/g, " ");
const stripNormNew = (h) => h.replace(/^<div[^>]*><div[^>]*>/, "").replace(/<\/div><\/div>$/, "").replace(/ class="[^"]*"/g, "");
const snapshots = {};
for (const sc of SC.rows) {
  const w = world(sc.attrs, sc.soc ? { "sensor.sigen_plant_battery_state_of_charge": { state: sc.soc, attributes: {} } } : {});
  for (const o of CORE.OVERRIDES) snapshots[`row:${sc.name}:${o.id}`] = rowNorm(CORE.rowHtml(o, w.st[PE].attributes, w.st, E));
}
for (const sc of SC.strips) {
  const w = world(sc.attrs);
  snapshots[`strip:${sc.name}`] = stripNormNew(CORE.stripHtml(w.st[PE].attributes, w.st, E));
}

// ---- fake dialogs ----
// a dialog whose content is looked up by id in the markup it was given (and re-given by render())
function fakeDlg(html) {
  const els = {};
  const dlg = { ls: {}, closed: 0, html, cc: null,
    close() { this.closed++; },
    addEventListener(e, f) { (this.ls[e] = this.ls[e] || []).push(f); } };
  const mk = (id) => els[id] || (els[id] = { id, value: "", textContent: "", innerHTML: "", style: {}, attrs: {}, dataset: {}, ls: {},
    set outerHTML(h) { if (dlg.cc) dlg.cc.innerHTML += h; },
    getAttribute(k) { return this.attrs[k] ?? null; }, setAttribute(k, v) { this.attrs[k] = v; }, focus() {},
    addEventListener(e, f) { this.ls[e] = f; }, click() { this.ls.click && this.ls.click(); } });
  const present = (id) => dlg.html.includes(`id="${id}"`) || (dlg.cc && dlg.cc.innerHTML.includes(`id="${id}"`)) || /^b\d+$/.test(id) || id === "cc";
  dlg.cc = mk("cc"); dlg.cc.innerHTML = "";
  dlg.querySelector = (sel) => { const id = sel.slice(1); return present(id) ? mk(id) : null; };
  dlg.querySelectorAll = (sel) => {
    const k = (sel.match(/data-([a-z]+)/) || [])[1];
    if (k) return [...dlg.html.matchAll(new RegExp(`data-${k}="([^"]*)"`, "g"))].map((m) => { const e = mk(k + m[1]); e.dataset = { [k]: m[1] }; return e; });
    const cls = sel.slice(1);
    return [...dlg.html.matchAll(new RegExp(`class="${cls}[^"]*"([^>]*)>`, "g"))].map((m) => { const e = mk(cls + m.index); for (const a of m[1].matchAll(/data-([a-z]+)="([^"]*)"/g)) e.dataset[a[1]] = a[2]; return e; });
  };
  return dlg;
}
let lastDlg = null; const opened = [];
L.modal = (a, o) => { opened.push(o.html); return (lastDlg = fakeDlg(o.html)); };
const click = (d, dataset) => d.ls.click.forEach((f) => f({ target: { closest: () => ({ dataset }) } }));
const elClick = (d, el) => d.ls.click.forEach((f) => f({ target: { closest: () => el } }));
const toggleEl = (a, on = "0") => ({ dataset: { a }, attrs: { "data-on": on }, style: {}, innerHTML: "", getAttribute(k) { return this.attrs[k]; }, setAttribute(k, v) { this.attrs[k] = v; } });
const O = (id) => CORE.OVERRIDES.find((o) => o.id === id);

// ---- 2. the quick-edit popup (tap a row) ----
{
  let w = world(); C.openEdit(O("sell"), {}); let d = lastDlg;
  d.querySelector("#s").value = "40"; d.querySelector("#p").value = "12"; d.querySelector("#set").click();
  T("popup: Set sell 40/12", w.ev(), [{ action: "SetAttribute", sellOverrideSOC: 40, sellOverridePrice: 12, sellOverrideAllowReset: true }]);
  T("popup: Set sends no timer and closes", [w.calls, d.closed], [[], 1]);
  w = world(); C.openEdit(O("buy"), {}); d = lastDlg; d.querySelector("#s").value = "80"; d.querySelector("#t").value = "1"; d.querySelector("#t").ls.input(); d.querySelector("#set").click();
  T("popup: 1 h timer", w.calls, [["timer", "start", { entity_id: TM, duration: 3600 }]]);
  w = world(); C.openEdit(O("sellsolar"), {}); d = lastDlg; d.querySelector("#s").value = "30";
  d.querySelectorAll("[data-dur]").find((c) => c.dataset.dur === "0.5").click();
  T("popup: 30 m chip fills Timer h", d.querySelector("#t").value, "0.5");
  d.querySelector("#set").click(); T("popup: 30 m chip timer", w.calls[0][2].duration, 1800);
  w = world(); C.openEdit(O("sell"), {}); d = lastDlg; d.querySelector("#s").value = "50"; d.querySelector("#r").click(); d.querySelector("#set").click();
  T("popup: No Reset on -> allowReset false", w.ev()[0].sellOverrideAllowReset, false);
  w = world(); C.openEdit(O("drain"), {}); d = lastDlg; d.querySelector("#clear").click();
  T("popup: clear drain also clears Plughole", w.ev(), [{ action: "SetAttribute", drainBatterySOC: 0, drainBatteryPrice: 0, drainBatteryAllowReset: true, drainBatteryPlughole: false }]);
  w = world(); C.openEdit(O("drain"), {}); d = lastDlg; d.querySelector("#s").value = "20"; d.querySelector("#ph").click(); d.querySelector("#set").click();
  T("popup: Plughole on", w.ev()[0].drainBatteryPlughole, true);
  w = world(); C.openEdit(O("buy"), {}); d = lastDlg; d.querySelector("#saveopen").click();
  T("popup: save refused with nothing set", d.querySelector("#sv").innerHTML.includes("Set a value first"), true);
  d.querySelector("#s").value = "70"; d.querySelector("#p").value = "9"; d.querySelector("#r").click(); d.querySelector("#t").value = "2"; d.querySelector("#t").ls.input();
  d.querySelector("#saveopen").click(); d.querySelector("#nm").value = "Night top-up"; d.querySelector("#saveok").click();
  T("popup: preset saved", w.ev()[0].overridePresets.slice(-1)[0], { name: "Night top-up", timer: 7200, values: { buy: { soc: 70, price: 9, allowReset: false } } });
  w = world({ overridePresets: [{ name: "P1", timer: 3600, values: { buy: { soc: 65, price: 7, allowReset: false } } }] });
  C.openEdit(O("buy"), {}); d = lastDlg; d.querySelectorAll("[data-preset]")[0].click();
  T("popup: preset applied", [w.ev(), w.calls.length], [[{ action: "SetAttribute", buyOverrideSOC: 65, buyOverridePrice: 7, buyOverrideAllowReset: false }], 1]);
  w = world(); C.openEdit(O("any"), {}); d = lastDlg; d.querySelector("#s").value = "90"; d.querySelector("#p").value = "12"; d.querySelector("#s").ls.input();
  T("popup: Buy Anytime cost preview", /to reach 90%/.test(d.querySelector("#costpv").innerHTML), true);
  d.querySelector("#calc").click();
  T("popup: cheapest price found, no error", [/Calc error|No forecast|Missing sensor/.test(d.querySelector("#cx").innerHTML), /Buy under/.test(d.querySelector("#cx").innerHTML)], [false, true]);
  w = world({ sellOverrideSOC: 33, sellOverrideAllowReset: false }); C.openEdit(O("sell"), {}); d = lastDlg;
  T("popup: starts from the current settings", [d.querySelector("#s").value, d.querySelector("#r").attrs["data-on"]], [33, "1"]);
  w = world({}, { [TM]: { state: "active", attributes: { finishes_at: new RealDate(NOW + 1800e3).toISOString() } } }); C.openEdit(O("sell"), {}); d = lastDlg;
  T("popup: a running timer fills Until", /^\d\d:\d\d$/.test(d.querySelector("#u").value), true);
  w = world(); C.openHelp(O("sell"), {}); T("help: names the override and its rules", [lastDlg.html.includes("Sell Override"), /no selling/i.test(lastDlg.html), lastDlg.html.includes("Spike Rules")], [true, true, true]);
  w = world(); C.clearOverride(O("sellsolar"));
  T("double-tap clear", w.ev(), [{ action: "SetAttribute", sellSolarSOC: 0, sellSolarPrice: 0, sellSolarAllowReset: true }]);
  w = world(); C.openDockHelp({}); T("dock help", [lastDlg.html.includes("Override Dock"), lastDlg.html.includes("Net target")], [true, true]);
}

// ---- 3. the timer bar and sheet ----
{
  const idle = { state: "idle", attributes: {} }, act = { state: "active", attributes: { finishes_at: new RealDate(NOW + 5400e3).toISOString() } };
  const S = (t, a = {}) => world(a, { [TM]: t }).st;
  T("timer bar hidden: idle, nothing set", C.timerShown(S(idle)[PE].attributes, S(idle)), false);
  T("timer bar shown: always-show setting", C.timerShown({ alwaysShowOverrideTimer: "show" }, S(idle)), true);
  T("timer bar hidden: running but nothing set or pinned", C.timerShown(S(act)[PE].attributes, S(act)), false);
  T("timer bar shown: running + a row set", C.timerShown({ sellOverrideSOC: 40 }, S(act)), true);
  T("timer bar shown: running + pinned", C.timerShown({ buyAnytimePinned: "show" }, S(act)), true);
  T("timer bar hidden: idle + a row set", C.timerShown({ sellOverrideSOC: 40 }, S(idle)), false);
  T("timer bar: idle says OFF / tap to set", [C.timerHtml(S(idle), "h").includes(">OFF<"), C.timerHtml(S(idle), "h").includes("tap to set")], [true, true]);
  T("timer bar: running shows 1:30:00 and the end time", [/id="tcd"[^>]*>1:30:00</.test(C.timerHtml(S(act), "h")), C.timerHtml(S(act), "h").includes("until ")], [true, true]);
  T("timer bar: minus dimmed when idle", C.timerHtml(S(idle), "h").includes("opacity:0.35"), true);
  T("countdown format", [C.countdown(5), C.countdown(65), C.countdown(3725)], ["5", "1:05", "1:02:05"]);
  T("unit highlight H / M", [/data-u="h"[^>]*background:var\(--battman-blue-wash\)/.test(C.timerHtml(S(idle), "h")), /data-u="m"[^>]*background:var\(--battman-blue-wash\)/.test(C.timerHtml(S(idle), "m"))], [true, true]);
  let w = world({}, { [TM]: idle }); C.openTimerSheet({}); let d = lastDlg;
  T("sheet (idle): Start for", d.html.includes("Timer is off") && d.html.includes("Start for"), true);
  d.querySelectorAll(".sh-x").find((e) => e.dataset.s === "1800").click();
  T("sheet: start 30 m", [w.calls, d.closed], [[["timer", "start", { entity_id: TM, duration: 1800 }]], 1]);
  w = world({}, { [TM]: idle }); C.openTimerSheet({}); d = lastDlg; d.querySelector("#sh-d").value = "1.5"; d.querySelector("#sh-d").ls.input(); d.querySelector("#sh-ok").click();
  T("sheet: 1.5 h", w.calls[0][2].duration, 5400);
  w = world({}, { [TM]: idle }); C.openTimerSheet({}); d = lastDlg; d.querySelector("#sh-u").value = "23:59"; d.querySelector("#sh-u").ls.input();
  T("sheet: Until clears Duration", d.querySelector("#sh-d").value, ""); d.querySelector("#sh-ok").click();
  T("sheet: Until starts a timer", w.calls[0][2].duration > 0, true);
  w = world({}, { [TM]: act }); C.openTimerSheet({}); d = lastDlg;
  T("sheet (running): Extend + Cancel", [d.html.includes("Extend"), !!d.querySelector("#sh-cx")], [true, true]);
  d.querySelectorAll(".sh-x").find((e) => e.dataset.s === "900").click();
  T("sheet: extend adds to what is left", w.calls[0][2].duration, 5400 + 900);
  w = world({}, { [TM]: act }); C.openTimerSheet({}); d = lastDlg; d.querySelector("#sh-cx").click();
  T("sheet: cancel", w.calls, [["timer", "cancel", { entity_id: TM }]]);
}

// ---- 4. the control centre ----
{
  const presets = [
    { name: "Sell hi", timer: 3600, values: { sell: { soc: 20, price: 30, allowReset: false } } },
    { name: "Eve dump", timer: 0, values: { sell: { soc: 30, price: 25, allowReset: true }, buy: { soc: 0, price: 5, allowReset: true }, net: { side: "sell", price: 1.5 } } },
    { name: "Net 2", timer: 0, values: { net: { side: "sell", price: 2 } } }];
  const open = (attrs = {}, extra = {}) => { const w = world({ overridePresets: clone(presets), ...attrs }, extra); C.openControl({}); return { w, d: lastDlg }; };
  const html = (d) => d.cc.innerHTML;
  let { w, d } = open();
  T("cc: sections", ["Net Target", "Sell Override", "Sell Solar", "Buy Override", "Buy Anytime", "Drain Battery", "Scenes", "Save current", "Manage"].every((t) => html(d).includes(t)), true);
  T("cc: a single-override preset is a chip, a multi one is a scene", [html(d).includes("Eve dump"), (html(d).match(/data-a="apply"/g) || []).length], [true, 2]);
  T("cc: the net chip for the sell side", html(d).includes("Net 2"), true);
  d.querySelector("#s0").value = "40"; d.querySelector("#p0").value = "12"; click(d, { a: "set", i: "0" });
  T("cc: Set sell", [w.ev(), d.closed], [[{ action: "SetAttribute", sellOverrideSOC: 40, sellOverridePrice: 12, sellOverrideAllowReset: true }], 1]);
  ({ w, d } = open(), 0); click(d, { a: "dur", i: "0", h: "0.5" }); d.querySelector("#s0").value = "10"; click(d, { a: "set", i: "0" });
  T("cc: duration chip then Set starts a 30 m timer", w.calls, [["timer", "start", { entity_id: TM, duration: 1800 }]]);
  ({ w, d } = open()); d.ls.input.forEach((f) => f({ target: { dataset: { in: "tdur", i: "1" }, value: "2" } })); d.querySelector("#s1").value = "5"; click(d, { a: "set", i: "1" });
  T("cc: typed hours drive the timer", w.calls[0][2].duration, 7200);
  ({ w, d } = open()); click(d, { a: "clear", i: "4" });
  T("cc: clear drain", w.ev(), [{ action: "SetAttribute", drainBatterySOC: 0, drainBatteryPrice: 0, drainBatteryAllowReset: true, drainBatteryPlughole: false }]);
  ({ w, d } = open()); click(d, { a: "pin", i: "2" }); click(d, { a: "pin", i: "2" });
  T("cc: pin then unpin", w.ev(), [{ action: "SetAttribute", buyOverridePinned: "show" }, { action: "SetAttribute", buyOverridePinned: "hide" }]);
  ({ w, d } = open()); click(d, { a: "apply", pi: "0" });
  T("cc: apply a chip", [w.ev(), w.calls], [[{ action: "SetAttribute", sellOverrideSOC: 20, sellOverridePrice: 30, sellOverrideAllowReset: false }], [["timer", "start", { entity_id: TM, duration: 3600 }]]]);
  ({ w, d } = open()); click(d, { a: "apply", pi: "1" });
  T("cc: apply a scene runs the scene script", w.calls, [["script", "battman_apply_scene", { name: "Eve dump" }]]);
  ({ w, d } = open()); click(d, { a: "arm", pi: "1" }); click(d, { a: "arm", pi: "1" });
  T("cc: arm then disarm a scene", w.ev(), [{ action: "SetAttribute", armedScene: "Eve dump" }, { action: "SetAttribute", armedScene: "" }]);
  ({ w, d } = open()); click(d, { a: "mgmt" }); click(d, { a: "apply", pi: "0" });
  T("cc: nothing applies in Manage mode", [w.ev().length, d.closed], [0, 0]);
  click(d, { a: "del", pi: "0" });
  T("cc: delete a preset", w.ev()[0].overridePresets.map((p) => p.name), ["Eve dump", "Net 2"]);
  ({ w, d } = open({ armedScene: "Eve dump" })); click(d, { a: "mgmt" }); click(d, { a: "del", pi: "1" });
  T("cc: deleting the armed scene disarms it", [w.ev()[0].armedScene, w.ev()[0].overridePresets.map((p) => p.name)], ["", ["Sell hi", "Net 2"]]);
  // Net Target
  ({ w, d } = open()); click(d, { a: "nttoggle" });
  const down = (dir) => { d.ls.pointerdown.forEach((f) => f({ target: { closest: () => ({ dataset: { d: String(dir) } }) }, preventDefault() {} })); d.ls.pointerup.forEach((f) => f()); };
  down(1); down(1); down(1);
  T("cc: 3 taps of + = $0.15", d.querySelector("#ntv").innerHTML, "$0.15");
  T("cc: readout says it is already reached", d.querySelector("#ntr").innerHTML.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim(), "Net today $7.30 Already reached · will mark met");
  down(-1); down(-1); down(-1); down(-1);
  T("cc: below zero", d.querySelector("#ntv").innerHTML, "\u2212$0.05");
  click(d, { a: "ntside", k: "1" }); click(d, { a: "ntset" });
  T("cc: net Set on the buy side", w.ev(), [{ action: "SetAttribute", netTargetSellPrice: 0, netTargetBuyPrice: -0.05 }]);
  ({ w, d } = open()); click(d, { a: "ntbe" });
  T("cc: net break even", w.ev(), [{ action: "SetAttribute", netTargetSellPrice: 0.001, netTargetBuyPrice: 0 }]);
  ({ w, d } = open()); click(d, { a: "ntapply", pi: "2" });
  T("cc: a net chip", w.ev(), [{ action: "SetAttribute", netTargetSellPrice: 2, netTargetBuyPrice: 0 }]);
  ({ w, d } = open()); click(d, { a: "ntclear" });
  T("cc: net clear", w.ev(), [{ action: "SetAttribute", netTargetSellPrice: 0, netTargetBuyPrice: 0 }]);
  ({ w, d } = open()); click(d, { a: "nttoggle" }); down(1); down(1); click(d, { a: "ntsave" }); d.querySelector("#ntnm").value = "Two tens"; click(d, { a: "ntsaveok" });
  T("cc: save a net preset", w.ev()[0].overridePresets.slice(-1)[0], { name: "Two tens", timer: 0, values: { net: { side: "sell", price: 0.1 } } });
  ({ w, d } = open({}, { "sensor.battman_sell_total": { state: "x", attributes: {} } })); click(d, { a: "ntbe" });
  T("cc: no target without the totals", w.ev(), []);
  ({ w, d } = open({ netTargetSellPrice: 3 })); T("cc: opens on an existing target", d.querySelector("#ntv").innerHTML, "$3.00");
  // Save current
  ({ w, d } = open({ sellOverrideSOC: 50, sellOverridePrice: 20, buyAnytimeSOC: 80, buyAnytimeAllowReset: false })); click(d, { a: "saveopen" });
  T("cc: the overlay lists what will be saved", ["Will save", "Sell Override", "Buy Anytime", "2 overrides \u2192 saves as a Scene"].every((t) => html(d).includes(t)), true);
  d.querySelector("#nm").value = "Mix"; d.querySelector("#snt").value = "1.5"; click(d, { a: "saveok" });
  const np = w.ev()[0].overridePresets.slice(-1)[0];
  T("cc: saves a scene with its timer (the old card dropped it)", [np.name, np.timer, Object.keys(np.values), np.values.any.allowReset], ["Mix", 5400, ["sell", "any"], false]);
  ({ w, d } = open({ sellOverrideSOC: 50 })); click(d, { a: "saveopen" }); click(d, { a: "saveok" });
  T("cc: a name is required", w.ev(), []);
  ({ w, d } = open()); click(d, { a: "saveopen" }); T("cc: nothing active to save", html(d).includes("Nothing active to save"), true);
  ({ w, d } = open()); click(d, { a: "toggle", i: "3" }); d.querySelector("#s3").value = "90"; click(d, { a: "calc", i: "3" });
  T("cc: Buy Anytime calculator", /Buy under/.test(d.querySelector("#cx-any").innerHTML), true);
  const rEl = toggleEl("rt"); elClick(d, rEl); T("cc: No Reset toggle", [rEl.attrs["data-on"], rEl.innerHTML.includes("ON")], ["1", true]);
  const pEl = toggleEl("pht"); elClick(d, pEl); T("cc: Plughole toggle", pEl.attrs["data-on"], "1");
}

// ---- 5. the card itself: starting, redrawing, the strip / row / timer gestures ----
{
  const sets = {}, els = {};
  const mkEl = (id) => ({ id, ls: {}, addEventListener(e, f) { (this.ls[e] = this.ls[e] || []).push(f); }, dispatchEvent() {}, querySelectorAll: () => [],
    set innerHTML(v) { this._h = v; sets[id] = (sets[id] || 0) + 1; }, get innerHTML() { return this._h || ""; } });
  const root = { getElementById: (id) => (els[id] = els[id] || mkEl(id)) };
  const w = world({ buyAnytimePinned: "show" }, { [TM]: { state: "idle", attributes: {} } });
  const card = new C.BattmanOverrides(); card.hass = w.hass;
  card.problem = (m) => T("card: no problem at start", m, "");
  const run = card.run(root);
  await new Promise((r) => setTimeout(r, 20));           // the entity map answers
  const fire = (el, ev, sel, data = {}) => (els[el].ls[ev] || []).forEach((f) => f({ target: { closest: (s) => (s === sel ? { dataset: data } : null) } }));
  const wait = (ms) => new Promise((r) => setTimeout(() => { skew += ms; r(); }, ms));
  T("card: strip and the pinned row are drawn", [els.strip.innerHTML.includes("OVERRIDES"), els.rows.innerHTML.includes('data-id="any"')], [true, true]);
  const before = sets.strip; run.hassChanged(); run.hassChanged();
  T("card: no redraw while its states are the same objects", sets.strip, before);
  const keep = w.st[PE];
  w.st[PE] = { ...keep, attributes: { ...keep.attributes, buyAnytimePinned: "hide" } }; run.hassChanged();
  T("card: redraws when the settings change (row unpinned)", [sets.strip > before, els.rows.innerHTML.includes('data-id="any"')], [true, false]);
  w.st[PE] = { ...keep, attributes: { ...keep.attributes, buyAnytimePinned: "show" } }; run.hassChanged();
  opened.length = 0; fire("strip", "pointerdown", ".strip"); fire("strip", "pointerup", ".strip");
  T("card: strip tap opens the control centre", [opened.length, opened[0].includes('id="cc"')], [1, true]);
  opened.length = 0; fire("strip", "pointerdown", ".strip"); await wait(650); fire("strip", "pointerup", ".strip");
  T("card: strip hold opens only the dock help", [opened.length, opened[0].includes("Override Dock")], [1, true]);
  const rowFire = (ev) => (els.rows.ls[ev] || []).forEach((f) => f({ target: { closest: (s) => (s === ".row" ? { dataset: { id: "any" } } : null) } }));
  opened.length = 0; rowFire("pointerdown"); rowFire("pointerup"); await wait(450);
  T("card: row tap opens the quick edit", [opened.length, opened[0].includes("Buy Anytime")], [1, true]);
  w.sent.length = 0; opened.length = 0; rowFire("pointerdown"); rowFire("pointerup"); await wait(120); rowFire("pointerdown"); rowFire("pointerup"); await wait(450);
  T("card: row double-tap clears and opens nothing", [opened.length, w.ev()], [0, [{ action: "SetAttribute", buyAnytimeSOC: 0, buyAnytimePrice: 0, buyAnytimeAllowReset: true }]]);
  opened.length = 0; rowFire("pointerdown"); await wait(650); rowFire("pointerup");
  T("card: row hold opens the help", [opened.length, opened[0].includes("Spike Rules")], [1, true]);
  w.st[TM] = { state: "active", attributes: { finishes_at: new RealDate(Date.now() + 600e3).toISOString() } }; run.hassChanged();
  T("card: the timer bar appears while running with a row pinned", els.timer.innerHTML.includes("tplus"), true);
  opened.length = 0; (els.timer.ls.pointerup || []).forEach((f) => f({ target: { closest: (s) => (s === ".tmid" ? { dataset: {} } : null) } }));
  T("card: tapping the timer opens the sheet", [opened.length, opened[0].includes("Extend")], [1, true]);
  // + / - in hours and minutes, and the unit set behind its back
  const tfire = (sel, data = {}) => (els.timer.ls.pointerup || []).forEach((f) => f({ target: { closest: (s) => (s === sel ? { dataset: data } : null) } }));
  store.battman_timer_unit = "h"; w.calls.length = 0; tfire(".tplus");
  T("card: + in hour mode adds 3600 s", w.calls[0][2].duration, 600 + 3600);
  tfire(".tu", { u: "m" }); T("card: M stores the unit and redraws", store.battman_timer_unit, "m");
  w.calls.length = 0; tfire(".tplus"); T("card: + in minute mode adds 60 s", w.calls[0][2].duration, 600 + 60);
  w.calls.length = 0; tfire(".tminus"); T("card: - in minute mode takes 1 minute off", w.calls[0][2], { entity_id: TM, duration: "-00:01:00" });
  store.battman_timer_unit = "h"; w.calls.length = 0; tfire(".tplus");
  T("card: the unit is read each press (another card may have changed it)", w.calls[0][2].duration, 600 + 3600);
  w.calls.length = 0; tfire(".tpill"); T("card: the toggle cancels a running timer", w.calls[0].slice(0, 2), ["timer", "cancel"]);
  run.pause && run.pause();
}

// ---- 6. the shared pieces ----
T("core: five overrides, in the dock's order", CORE.OVERRIDES.map((o) => o.id), ["sell", "sellsolar", "buy", "any", "drain"]);
T("core: only Buy takes a negative price", CORE.OVERRIDES.filter((o) => o.allowNegative).map((o) => o.id), ["buy"]);

// to a file (argv[2]): a large write to a pipe can be cut off by process.exit
fs.writeFileSync(process.argv[2], JSON.stringify({ snapshots, results }));
process.exit(0);
