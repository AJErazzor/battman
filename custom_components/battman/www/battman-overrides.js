// Battman Overrides: custom:battman-overrides. The override dock: a strip (the overrides set, No reset, the armed
// scene, Plughole, the Net Target readout) and a row for each override that is set or pinned, then the override timer.
//
//   type: custom:battman-overrides
//
//   Strip   tap: the control centre (Net Target, the five overrides, Scenes, Save current / Manage)   hold: help
//   Row     tap: quick edit (SOC, price, No reset, timer, presets, cost / cheapest-price calculators, save, clear)
//           double-tap: clear   hold: help
//   Timer   toggle, countdown, H / M unit with - and +, tap: the timer sheet, hold: the timer's more-info
//
// Settings change by firing Battman's parameters update event (SetAttribute) and starting or cancelling the override
// timer. Popups are Battman's own <dialog> (BattmanLib.modal). Entities: Battman's entity map for its own sensors,
// Sigen and Amber named directly. Anything missing is said on the card, never made up.

import { AMBER as AMBER_ENT, BattmanCardBase, SIGEN, battmanDefine, battmanMap, battmanPicker, esc, inCardPicker } from "./battman-card-base.js";
import { OVERRIDES, colours, isFalse, isOn, isTrue, money, num, pad2, rowHtml, stripHtml } from "./battman-overrides-core.js";

// Battman's own names are replaced by the entity map's when the card starts (run); the rest are named directly.
const E = {
  params: "sensor.battman_parameters",
  soc: SIGEN.battery_soc,
  capacity: SIGEN.rated_energy_capacity,
  sellTotal: "sensor.battman_sell_total",
  buyTotal: "sensor.battman_buy_total",
  timer: "timer.battman_override_timer",
  scene: "script.battman_apply_scene",
  forecast: AMBER_ENT.buy_forecast,
  chargeKw: "sensor.sigen_plant_available_max_active_power",
};
const EVENT = "battman_parameters_update";
const PRICE_FIELD = "advanced_price_predicted", ROUND_STEP = 1, SAFETY_MIN = 30, SAFETY_IVL = 2;

// ── popups (Battman's own <dialog>) ──────────────────────────────────────────────────────────
const lib = () => window.BattmanLib;
const hassNow = () => document.querySelector("home-assistant").hass;
const fireParams = (d) => hassNow().connection.sendMessage({ type: "fire_event", event_type: EVENT, event_data: { action: "SetAttribute", ...d } });
const closeDialog = (dlg) => { try { dlg.close(); } catch (e) { /* already closed */ } };

const FL = "font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;display:block;margin-bottom:5px";
const CHL = "font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:var(--battman-text-dim);margin-bottom:6px";
const CHS = "height:26px;display:inline-flex;align-items:center;gap:5px;padding:0 9px;border-radius:5px;background:var(--battman-surface-card);cursor:pointer;margin:0 5px 5px 0";
const NUM = "width:100%;box-sizing:border-box;height:37px;background:var(--battman-surface-card);border-radius:6px;color:var(--battman-text-bright);font-weight:800;text-align:center;padding:0 4px;font-family:var(--battman-font)";
const BTN = "flex:1;text-align:center;padding:8px 4px;border-radius:6px;font-size:11px;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;cursor:pointer";

const plugStyle = "display:flex;align-items:center;gap:10px;padding:9px 10px;border-radius:8px;cursor:pointer;margin-bottom:10px;box-sizing:border-box;background:transparent;border:1px solid var(--battman-border-neutral)";
const plugInner = (on) => `<div style="flex:1;min-width:0"><div style="font-size:12px;font-weight:900;letter-spacing:0.08em;text-transform:uppercase;color:${on ? "var(--battman-red)" : "var(--battman-text-bright)"}">Plughole</div><div style="font-size:10.5px;font-weight:600;line-height:1.35;color:var(--battman-text-muted)">Drain instead of House Party</div></div><div style="width:44px;height:26px;border-radius:13px;flex:none;position:relative;background:${on ? "var(--battman-red)" : "var(--battman-border-neutral)"}"><div style="position:absolute;top:3px;left:${on ? 21 : 3}px;width:20px;height:20px;border-radius:50%;background:#fff"></div></div>`;

// Cost preview and cheapest-price calculator (Buy Anytime): shared by the row popup and the control centre.
const stateNum = (H, id) => { const x = H.states[id]; return x ? parseFloat(x.state) : NaN; };
function costPreview(H, el, tgt, price, K) {
  if (!el) return;
  const cap = stateNum(H, E.capacity), cur = stateNum(H, E.soc);
  if (isNaN(cap) || isNaN(cur)) { el.innerHTML = "—"; return; }
  const gap = tgt - cur;
  if (tgt <= 0) { el.innerHTML = "set a target SOC to preview cost"; return; }
  if (gap <= 0.5) { el.innerHTML = "target already met at " + cur.toFixed(0) + "%"; return; }
  const kwh = gap * (cap / 100);
  el.innerHTML = price > 0
    ? `<b style="color:${K.c}">$${(kwh * price / 100).toFixed(2)}</b> to reach ${tgt.toFixed(0)}% <span style="color:var(--battman-text-muted)">(${kwh.toFixed(1)} kWh)</span>`
    : `${cur.toFixed(0)}% → ${tgt.toFixed(0)}% <span style="color:var(--battman-text-muted)">(${kwh.toFixed(1)} kWh, no price set)</span>`;
}
// Works out the price threshold that fills the target (or covers the safety window) by the deadline, writes it into the
// price box (setPrice) and says what it found in ex. dlSec = seconds until the deadline (0 = none).
function cheapestPrice(H, ex, tgt, dlSec, K, setPrice, afterFill) {
  const L = lib();
  const red = (t) => `<span style="color:var(--battman-darkred)">${t}</span>`, amb = (t) => `<span style="color:var(--battman-amber)">${t}</span>`;
  try {
    const fa = (H.states[E.forecast] || {}).attributes || {};
    const fc = fa.forecasts || fa.Forecasts || [];
    if (!fc.length) { ex.innerHTML = red("No forecast on " + E.forecast); return; }
    const ckw = stateNum(H, E.chargeKw), cap = stateNum(H, E.capacity), cur = stateNum(H, E.soc);
    if (isNaN(ckw) || isNaN(cap) || isNaN(cur)) { ex.innerHTML = red("Missing sensor (charge/capacity/SOC)"); return; }
    const dlMs = dlSec > 0 ? Date.now() + dlSec * 1000 : 0;
    const dlTxt = dlMs ? " by " + L.clk(new Date(dlMs)) : "";
    const r = tgt > 0
      ? L.cheapestFill({ forecasts: fc, price_field: PRICE_FIELD, charge_kw: ckw, capacity_kwh: cap, cur_soc: cur, target_soc: tgt,
        round_step_cents: ROUND_STEP, deadline_ms: dlMs || undefined })
      : { ok: false, reason: "target_met" };
    if (!r.ok && r.reason === "target_met") {
      const sn = L.cheapestSustained({ forecasts: fc, price_field: PRICE_FIELD, min_minutes: SAFETY_MIN, min_intervals: SAFETY_IVL,
        round_step_cents: ROUND_STEP, deadline_ms: dlMs || undefined });
      if (!sn.ok) { ex.innerHTML = sn.reason === "no_window" ? amb("No forecast intervals before" + dlTxt) : red("No usable forecast"); return; }
      setPrice(sn.threshold_cents.toFixed(1));
      let msg = (tgt > 0 ? "No fill needed at " + cur.toFixed(0) + "% — " : "")
        + `armed <b style="color:${K.c}">${sn.threshold_cents.toFixed(1)}¢</b>` + (dlTxt ? `<span style="color:var(--battman-amber);font-weight:800">${dlTxt}</span>` : "")
        + " — " + L.hm(sn.hours_at_or_under * 3600) + " at/under";
      if (!sn.enough) msg += " " + amb("(only " + Math.round(sn.minutes_at_or_under) + " min available)");
      ex.innerHTML = msg;
      return;
    }
    if (!r.ok) { ex.innerHTML = r.reason === "no_window" ? amb("No forecast intervals before" + dlTxt) : red("No usable forecast"); return; }
    setPrice(r.threshold_cents.toFixed(1));
    let msg = `Buy under <b style="color:${K.c}">${r.threshold_cents.toFixed(1)}¢</b>` + (dlTxt ? `<span style="color:var(--battman-amber);font-weight:800">${dlTxt}</span>` : "")
      + ` — ~${r.kwh_filled.toFixed(1)} kWh, ` + L.hm(r.hours_at_or_under * 3600) + " at/under";
    if (!r.fully_reachable) msg += " " + amb("(only reaches ~" + Math.min(100, cur + r.kwh_filled / r.kwh_per_pct).toFixed(0) + "%)");
    ex.innerHTML = msg;
    if (afterFill) afterFill();
  } catch (ce) { ex.innerHTML = red("Calc error: " + (ce && ce.message ? ce.message : ce)); }
}

function editHtml(o, P, UL) {
  const K = colours(o), L = lib();
  const lka = L.lockSvg("var(--battman-amber)", 13);
  let chips = "";
  (P.overridePresets || []).forEach((p, pi) => {
    const v = p.values || {};
    if (Object.keys(v).length !== 1 || !v[o.id]) return;
    const cv = [];
    if ((+v[o.id].soc || 0) > 0) cv.push((+v[o.id].soc).toFixed(0) + "%");
    if ((+v[o.id].price || 0) > 0) cv.push((+v[o.id].price).toFixed(1) + "¢");
    chips += `<div data-preset="${pi}" style="${CHS};border:1px solid ${K.dim}"><span style="font-size:11px;font-weight:800;color:${K.c}">${esc(p.name)}</span>`
      + `<span style="font-size:10px;font-weight:700;color:var(--battman-text-dim)">${cv.join("·")}</span>${v[o.id].allowReset === false ? lka : ""}${L.presetLabel(p)}</div>`;
  });
  const dchips = [["15m", 0.25], ["30m", 0.5], ["1h", 1], ["2h", 2]].map((e) =>
    `<span data-dur="${e[1]}" style="${CHS};border:1px solid var(--battman-blue-border);font-size:11px;font-weight:800;color:var(--battman-blue)">${e[0]}</span>`).join("");
  const uchips = UL.map((e, i) =>
    `<span data-ul="${i}" style="${CHS};border:1px solid var(--battman-border-neutral-soft);font-size:11px;font-weight:800;color:var(--battman-text-muted)">${esc(e[0])}</span>`).join("");
  const input = (id, label, color, attrs, border, fz) =>
    `<div style="flex:1"><span style="${FL};color:${color}">${label}</span><input id="${id}" type="number" ${attrs} style="${NUM};border:1px solid ${border};font-size:${fz}px"></div>`;
  return `<div style="background:var(--battman-surface-popup);padding:12px;border-radius:10px;font-family:var(--battman-font)">`
    + `<div style="font-size:14px;font-weight:800;letter-spacing:0.04em;text-transform:uppercase;color:${K.c};display:flex;align-items:center;min-height:44px;box-sizing:border-box;padding:0 60px 9px 0;margin-bottom:9px;border-bottom:1px solid ${K.dim}">${o.name}</div>`
    + `<div id="body">`
    + (chips ? `<div style="margin-bottom:10px">${chips}</div>` : "")
    + `<div style="display:flex;gap:8px;margin-bottom:10px">`
    + input("s", "SOC %", K.c, 'min="0" max="100" step="1" placeholder="off"', K.dim, 18)
    + input("p", "PRICE ¢", K.c, 'min="0" max="200" step="0.01" placeholder="off"', K.dim, 18)
    + `<div style="flex:0.95"><span style="${FL};color:var(--battman-amber)">No Reset</span><div id="r" data-on="0" style="height:37px;box-sizing:border-box;display:flex;align-items:center;justify-content:center;gap:5px;border-radius:6px;cursor:pointer;background:transparent;border:1px solid var(--battman-border-neutral)"><span style="font-size:11px;font-weight:800;color:var(--battman-text-muted)">OFF</span></div></div>`
    + `</div>`
    + (o.id === "drain" ? `<div id="ph" data-on="0" style="${plugStyle}">${plugInner(false)}</div>` : "")
    + (o.id === "any" ? `<div id="costpv" style="font-size:12px;font-weight:600;line-height:1.5;text-align:center;color:var(--battman-text-dim);min-height:16px;margin-bottom:10px">set a target SOC to preview cost</div>` : "")
    + `<div style="border-top:1px solid var(--battman-border-neutral-soft);padding-top:10px;margin-bottom:10px">`
    + `<div style="${CHL}">Start for</div><div style="margin-bottom:9px">${dchips}</div>`
    + `<div style="${CHL}">Run until</div><div style="margin-bottom:10px">${uchips}</div>`
    + `<div style="display:flex;gap:8px;align-items:flex-end">`
    + input("t", "Timer h", "var(--battman-blue)", 'min="0" max="48" step="0.25" placeholder="—"', "var(--battman-blue-border)", 16)
    + `<div style="color:var(--battman-text-dim);font-size:10px;font-weight:700;padding-bottom:11px">or</div>`
    + `<div style="flex:1"><span style="${FL};color:var(--battman-blue)">Until</span><input id="u" type="time" style="${NUM};border:1px solid var(--battman-blue-border);font-size:16px;color-scheme:dark"></div>`
    + `</div><div id="pv" style="font-size:11px;font-weight:700;color:var(--battman-text-dim);text-align:center;min-height:15px;margin-top:7px"></div></div>`
    + (o.id === "any"
      ? `<div id="calc" style="width:100%;box-sizing:border-box;height:40px;border-radius:7px;cursor:pointer;background:var(--battman-purple-soft-bg);border:1px solid ${K.dim};color:${K.c};font-size:12px;font-weight:800;letter-spacing:0.06em;text-transform:uppercase;display:flex;align-items:center;justify-content:center;gap:8px;margin-bottom:8px"><svg viewBox="0 0 24 24" style="width:15px;height:15px;fill:${K.c}"><path d="M13 2 3 14h7l-1 8 10-12h-7z"/></svg>Calculate cheapest price</div>`
        + `<div id="cx" style="font-size:11px;font-weight:600;line-height:1.5;color:var(--battman-text-dim);text-align:center;min-height:15px;margin-bottom:10px"></div>`
      : "")
    + `<div id="sv" style="text-align:center;min-height:0;margin-bottom:2px"></div>`
    + `<div style="display:flex;gap:6px">`
    + `<div id="clear" style="${BTN};background:transparent;color:var(--battman-text-muted);border:1px solid var(--battman-border-neutral)">Clear</div>`
    + `<div id="saveopen" style="${BTN};background:transparent;color:var(--battman-green);border:1px solid var(--battman-green-border-light)">Save</div>`
    + `<div id="set" style="${BTN};background:${K.wash};color:${K.c};border:1px solid ${K.dim}">Set</div>`
    + `</div></div>`
    + `<div id="save" style="display:none"><div style="font-size:12px;font-weight:800;letter-spacing:0.1em;text-transform:uppercase;color:var(--battman-text-bright);margin-bottom:10px">Save preset</div>`
    + `<div style="margin-bottom:10px"><span style="${FL};color:var(--battman-text-muted)">Name</span><input id="nm" type="text" placeholder="e.g. Cheapest fill" style="width:100%;box-sizing:border-box;background:var(--battman-surface-card);border:1px solid var(--battman-border-neutral);border-radius:7px;color:var(--battman-text-bright);font-size:15px;font-weight:700;padding:10px 12px"></div>`
    + `<div style="font-size:10px;color:var(--battman-text-dim);font-weight:700;margin-bottom:12px;text-align:center">Saves SOC, price, lock and timer for ${o.name}</div>`
    + `<div style="display:flex;gap:8px"><div id="savecancel" style="flex:1;text-align:center;padding:11px;border-radius:7px;font-size:11px;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;color:var(--battman-text-muted);border:1px solid var(--battman-border-neutral);cursor:pointer">Cancel</div>`
    + `<div id="saveok" style="flex:1.4;text-align:center;padding:11px;border-radius:7px;font-size:11px;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;color:var(--battman-green);background:var(--battman-green-soft-bg);border:1px solid var(--battman-green-border-strong);cursor:pointer">Save preset</div></div></div>`
    + `</div>`;
}

// The quick-edit popup for one override.
function openEdit(o, anchor) {
  const L = lib();
  if (!L || !L.modal) return;
  const H = hassNow();
  const P = (H.states[E.params] || {}).attributes || {};
  const UL = L.runUntilList(H);
  const K = colours(o);
  const dlg = L.modal(anchor, { width: "min(94vw,340px)", close: true, html: editHtml(o, P, UL) });
  if (!dlg) return;
  const Q = (id) => dlg.querySelector("#" + id);
  let untilSec = 0;
  const pv = () => { Q("pv").innerHTML = L.preview(Q("t").value, Q("u").value, "no timer — stays until cleared"); };
  const secs = () => (untilSec > 0 ? untilSec : L.timerSec(Q("t"), Q("u")));
  const send = (d) => { fireParams(d); closeDialog(dlg); };
  const startTimer = (sec) => { if (sec > 0) H.callService("timer", "start", { entity_id: E.timer, duration: Math.round(sec) }); };

  // no-reset toggle
  const lockToggle = () => {
    const el = Q("r"), on = el.getAttribute("data-on") !== "1";
    el.setAttribute("data-on", on ? "1" : "0");
    el.style.background = on ? "var(--battman-amber-soft-bg)" : "transparent";
    el.style.borderColor = on ? "var(--battman-amber-border)" : "var(--battman-border-neutral)";
    el.innerHTML = on ? L.lockSvg("var(--battman-amber)", 15) + `<span style="font-size:11px;font-weight:800;color:var(--battman-amber)">ON</span>`
      : `<span style="font-size:11px;font-weight:800;color:var(--battman-text-muted)">OFF</span>`;
  };
  Q("r").addEventListener("click", lockToggle);
  const ph = Q("ph");
  const plugToggle = () => {
    const on = ph.getAttribute("data-on") !== "1";
    ph.setAttribute("data-on", on ? "1" : "0");
    ph.setAttribute("style", plugStyle);
    ph.innerHTML = plugInner(on);
  };
  if (ph) ph.addEventListener("click", plugToggle);

  // timer: hours OR an "until" time: filling one clears the other
  Q("t").addEventListener("input", () => { untilSec = 0; if (Q("t").value) Q("u").value = ""; pv(); });
  Q("u").addEventListener("input", () => { untilSec = 0; if (Q("u").value) Q("t").value = ""; pv(); });
  dlg.querySelectorAll("[data-dur]").forEach((el) => el.addEventListener("click", () => {
    untilSec = 0; Q("u").value = ""; Q("t").value = el.dataset.dur; pv();
  }));
  dlg.querySelectorAll("[data-ul]").forEach((el) => el.addEventListener("click", () => {
    const e = UL[+el.dataset.ul];
    untilSec = e[1]; Q("t").value = ""; Q("u").value = e[2]; pv();
  }));

  // presets: apply one for this override (values, lock, and its timer)
  dlg.querySelectorAll("[data-preset]").forEach((el) => el.addEventListener("click", () => {
    const pr = (P.overridePresets || [])[+el.dataset.preset];
    if (!pr) return;
    const v = pr.values || {};
    startTimer(L.presetSec(pr));
    send({ [o.soc]: (v[o.id] && parseFloat(v[o.id].soc)) || 0, [o.price]: (v[o.id] && parseFloat(v[o.id].price)) || 0,
      [o.reset]: !(v[o.id] && v[o.id].allowReset === false) });
  }));

  // cost preview and cheapest price (Buy Anytime)
  const costPv = () => costPreview(H, Q("costpv"), parseFloat(Q("s").value) || 0, parseFloat(Q("p").value) || 0, K);
  Q("s").addEventListener("input", costPv);
  Q("p").addEventListener("input", costPv);
  if (Q("calc")) Q("calc").addEventListener("click", () =>
    cheapestPrice(H, Q("cx"), parseFloat(Q("s").value) || 0, secs(), K, (v) => { Q("p").value = v; }, costPv));

  // Set / Clear
  Q("set").addEventListener("click", () => {
    const d = { [o.soc]: parseFloat(Q("s").value) || 0, [o.price]: parseFloat(Q("p").value) || 0 };
    startTimer(secs());
    d[o.reset] = Q("r").getAttribute("data-on") !== "1";
    if (ph) d.drainBatteryPlughole = ph.getAttribute("data-on") === "1";
    send(d);
  });
  Q("clear").addEventListener("click", () => {
    const d = { [o.soc]: 0, [o.price]: 0, [o.reset]: true };
    if (o.id === "drain") d.drainBatteryPlughole = false;
    send(d);
  });

  // Save as a preset (this override's SOC, price, lock and timer)
  Q("saveopen").addEventListener("click", () => {
    const sv = parseFloat(Q("s").value) || 0, pr = parseFloat(Q("p").value) || 0;
    if (sv <= 0 && pr <= 0) { Q("sv").innerHTML = `<span style="color:var(--battman-amber);font-size:11px">Set a value first</span>`; return; }
    Q("body").style.display = "none"; Q("save").style.display = "block"; Q("nm").focus();
  });
  Q("savecancel").addEventListener("click", () => { Q("save").style.display = "none"; Q("body").style.display = "block"; });
  Q("saveok").addEventListener("click", () => {
    const nm = Q("nm").value.trim();
    if (!nm) { Q("nm").style.borderColor = "var(--battman-darkred)"; Q("nm").focus(); return; }
    const th = parseFloat(Q("t").value) || 0, ta = Q("u").value;
    const np = { name: nm, timer: (!ta && th > 0) ? Math.round(th * 3600) : 0,
      values: { [o.id]: { soc: parseFloat(Q("s").value) || 0, price: parseFloat(Q("p").value) || 0, allowReset: Q("r").getAttribute("data-on") !== "1" } } };
    if (ta) np.timer_at = ta;
    send({ overridePresets: (P.overridePresets || []).concat([np]) });
  });

  // start values
  Q("s").value = parseFloat(P[o.soc]) || "";
  Q("p").value = parseFloat(P[o.price]) || "";
  const tm = H.states[E.timer] || {};
  if (tm.state === "active" && tm.attributes && tm.attributes.finishes_at) Q("u").value = L.clk(new Date(tm.attributes.finishes_at));
  pv(); costPv();
  if (isFalse(P[o.reset])) lockToggle();
  if (ph && isTrue(P.drainBatteryPlughole)) plugToggle();
}

// Hold: what this override's values mean.
function openHelp(o, anchor) {
  const L = lib();
  if (!L || !L.modal) return;
  const K = colours(o);
  const line = (t, size = 11) => `<div style="margin-bottom:4px;color:var(--battman-text-muted);font-size:${size}px">${t}</div>`;
  const hr = `<div style="border-top:1px solid var(--battman-border-neutral-soft);margin:8px 0"></div>`;
  const b = (t) => `<span style="color:var(--battman-text-bright);font-weight:600">${t}</span>`;
  L.modal(anchor, { width: "min(94vw,360px)", close: true, html:
    `<div style="background:var(--battman-surface-popup);padding:14px 16px;border-radius:8px;font-family:var(--battman-font)">`
    + `<div style="font-size:9px;font-weight:700;color:${K.c};text-transform:uppercase;letter-spacing:0.14em;display:flex;align-items:center;min-height:44px;box-sizing:border-box;padding:0 60px 6px 0;margin-bottom:10px;border-bottom:1px solid ${K.dim}">${o.name}</div>`
    + `<div style="margin-bottom:10px"><div style="margin-bottom:5px"><span style="color:${K.c};font-weight:700;font-size:12px">SOC</span><span style="color:var(--battman-text-muted);font-size:11px"> — ${o.helpSoc}</span></div>`
    + `<div><span style="color:${K.c};font-weight:700;font-size:12px">Price</span><span style="color:var(--battman-text-muted);font-size:11px"> — ${o.helpPrice}</span></div></div>`
    + hr + line("If only SOC is set, the curve price thresholds still apply.") + line("If only Price is set, the SOC curve thresholds still apply.")
    + line("If both are set, both conditions must be met — curves are ignored.")
    + (o.specialAt > 0 ? line(`Setting SOC to ${o.specialAt}% means: ${o.specialDesc.toLowerCase()}.`) : "")
    + line("Once the SOC target is reached, as long as the override timer is not running, both values turn off automatically.")
    + hr + line(`${b("Timer:")} give it a duration in hours OR an exact finish time — whichever you fill, the other clears.`, 10)
    + line(`${b("Tap:")} edit values or apply a preset. ${b("Double-tap:")} clear.`, 10)
    + `<div style="margin-top:10px;padding:6px 8px;background:${K.wash};border-left:2px solid ${K.c};border-radius:3px;font-size:10px;color:${K.c};font-weight:700;letter-spacing:0.02em">⚡ Spike Rules will always override everything</div></div>` });
}

// Double-tap clears an override (SOC and price off, reset allowed again), with no dialog.
const clearOverride = (o) => fireParams({ [o.soc]: 0, [o.price]: 0, [o.reset]: true });

// ── the override timer bar ───────────────────────────────────────────────────────────────────
const timerOf = (st) => st[E.timer] || { state: "idle", attributes: {} };
const remSec = (t) => {
  if (t.state !== "active" || !t.attributes || !t.attributes.finishes_at) return null;
  const ms = new Date(t.attributes.finishes_at) - new Date();
  return ms > 0 ? Math.round(ms / 1000) : 0;
};
// like HA's own timer countdown: h:mm:ss, m:ss under an hour, s under a minute
const countdown = (s) => (s >= 3600 ? Math.floor(s / 3600) + ":" + pad2(Math.floor((s % 3600) / 60)) + ":" + pad2(s % 60)
  : (s >= 60 ? Math.floor(s / 60) + ":" + pad2(s % 60) : String(s)));
const getUnit = () => { try { return localStorage.getItem("battman_timer_unit") === "m" ? "m" : "h"; } catch (e) { return "h"; } };
const setUnitStore = (u) => { try { localStorage.setItem("battman_timer_unit", u); } catch (e) { /* private mode */ } };
const timerShown = (a, st) => {
  const on = timerOf(st).state === "active";
  const anyOn = OVERRIDES.some((o) => isOn(o, a)), anyPin = OVERRIDES.some((o) => a[o.pin] === "show");
  return a.alwaysShowOverrideTimer === "show" || (on && (anyOn || anyPin));
};
function timerHtml(st, unit) {
  const t = timerOf(st), on = t.state === "active", rem = remSec(t);
  const bg = on ? "var(--battman-blue-wash)" : "var(--battman-border-neutral)";
  const bd = on ? "var(--battman-blue-border-strong)" : "var(--battman-border-neutral)";
  const pill = `<div class="tpill bmb2" style="width:46px;height:27px;border-radius:999px;position:relative;cursor:pointer;background:${bg};border:1px solid ${bd}">`
    + `<div style="position:absolute;top:2px;left:${on ? "19px" : "2px"};width:21px;height:21px;border-radius:50%;background:${on ? "var(--battman-blue)" : "var(--battman-text-muted)"};transition:all .2s"></div></div>`;
  let mid;
  if (on && rem !== null) {
    const until = new Date(t.attributes.finishes_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    mid = `<div id="tcd" style="color:var(--battman-blue);font-size:22px;font-weight:800;font-variant-numeric:tabular-nums;letter-spacing:0.01em">${countdown(rem)}</div>`
      + `<div style="color:var(--battman-blue);font-size:13px;font-weight:700;margin-top:4px">until ${until}</div>`;
  } else {
    mid = `<div style="color:var(--battman-text-dim);font-size:15px;font-weight:800;letter-spacing:0.08em">OFF</div>`
      + `<div style="color:var(--battman-text-dim);font-size:12px;font-weight:700;border-bottom:1px dashed var(--battman-border-neutral-soft);margin-top:2px">tap to set</div>`;
  }
  const uBtn = (u, extra) => `<div class="tu tu-${u} bmb2" data-u="${u}" style="flex:1;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:800;cursor:pointer;${extra}background:${unit === u ? "var(--battman-blue-wash)" : "var(--battman-surface-card)"};color:${unit === u ? "var(--battman-blue)" : "var(--battman-text-muted)"}">${u.toUpperCase()}</div>`;
  const sq = "width:44px;height:44px;box-sizing:border-box;display:flex;align-items:center;justify-content:center;border-radius:7px;cursor:pointer;background:var(--battman-surface-card);font-size:24px;font-weight:800;";
  const ctl = `<div style="display:flex;align-items:center;gap:10px">`
    + `<div style="display:flex;flex-direction:column;width:30px;height:44px;border-radius:6px;overflow:hidden;border:1px solid var(--battman-border-neutral)">${uBtn("h", "")}${uBtn("m", "border-top:1px solid var(--battman-border-neutral);")}</div>`
    + `<div class="tminus bmb2" style="${sq}border:1px solid var(--battman-darkred-border);color:var(--battman-darkred);opacity:${on ? "1" : "0.35"}">−</div>`
    + `<div class="tplus bmb2" style="${sq}border:1px solid var(--battman-green-border);color:var(--battman-green)">+</div></div>`;
  return `<div class="tbar" style="border:${on ? "1px solid var(--battman-blue-border-light)" : "1px solid var(--battman-border-neutral-soft)"}">`
    + `<div style="display:flex;align-items:center">${pill}</div>`
    + `<div class="tmid" style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;cursor:pointer">${mid}</div>`
    + `<div style="display:flex;align-items:center">${ctl}</div></div>`;
}

// The timer sheet: start / extend / run until / set until / duration / cancel.
function openTimerSheet(anchor) {
  const L = lib();
  if (!L || !L.modal) return;
  const H = hassNow();
  const C = "var(--battman-blue)";
  const t0 = timerOf(H.states), live = t0.state === "active";
  const CH = "height:30px;display:inline-flex;align-items:center;padding:0 11px;border-radius:6px;background:var(--battman-surface-card);cursor:pointer;font-size:12px;font-weight:800;margin:0 5px 5px 0";
  const LB = "font-size:9px;font-weight:800;letter-spacing:0.12em;text-transform:uppercase;color:var(--battman-text-dim);margin-bottom:6px";
  const IN = "width:100%;box-sizing:border-box;height:36px;background:var(--battman-surface-card);border:1px solid var(--battman-blue-border);border-radius:6px;color:var(--battman-text-bright);font-size:16px;font-weight:800;text-align:center;padding:0 4px;font-family:var(--battman-font);color-scheme:dark";
  const head = live
    ? `<div style="display:flex;align-items:baseline;gap:8px;margin-bottom:13px;padding-right:60px"><span id="sh-cd" style="font-size:26px;font-weight:800;color:${C};font-variant-numeric:tabular-nums"></span><span id="sh-un" style="font-size:12px;font-weight:700;color:${C}"></span></div>`
    : `<div style="font-size:13px;font-weight:800;color:var(--battman-text-dim);margin-bottom:13px;padding-right:60px">Timer is off</div>`;
  const ext = [["+15m", 900], ["+30m", 1800], ["+1h", 3600], ["+2h", 7200]].map((e) =>
    `<span class="sh-x bmb2" data-s="${e[1]}" style="${CH};border:1px solid var(--battman-blue-border);color:${C}">${live ? e[0] : e[0].replace("+", "")}</span>`).join("");
  const run = L.runUntilList(H).map((r) =>
    `<span class="sh-r bmb2" data-at="${esc(r[2])}" data-s="${r[1]}" style="${CH};border:1px solid var(--battman-border-neutral-soft);color:var(--battman-text-muted)">${esc(r[0])}</span>`).join("");
  const html = `<div style="background:var(--battman-surface-popup);padding:14px;border-radius:12px;font-family:var(--battman-font)">` + head
    + `<div style="${LB}">${live ? "Extend" : "Start for"}</div><div style="margin-bottom:12px">${ext}</div>`
    + `<div style="${LB}">Run until</div><div style="margin-bottom:11px">${run}</div>`
    + `<div style="display:flex;gap:8px;align-items:flex-end;margin-bottom:8px">`
    + `<div style="flex:1"><div style="${LB};color:${C}">Set until</div><input id="sh-u" type="time" style="${IN}"></div>`
    + `<div style="color:var(--battman-text-dim);font-size:10px;font-weight:700;padding-bottom:11px">or</div>`
    + `<div style="flex:1"><div style="${LB};color:${C}">Duration h</div><input id="sh-d" type="number" min="0" max="48" step="0.25" placeholder="—" style="${IN}"></div></div>`
    + `<div id="sh-pv" style="font-size:11px;font-weight:700;color:var(--battman-text-dim);text-align:center;min-height:16px;margin-bottom:12px"></div>`
    + `<div style="display:flex;gap:6px">`
    + (live ? `<div id="sh-cx" class="bmb2" style="flex:1;text-align:center;padding:9px 4px;border-radius:6px;font-size:10px;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;cursor:pointer;background:transparent;color:var(--battman-darkred);border:1px solid var(--battman-darkred-border-light)">Cancel timer</div>` : "")
    + `<div id="sh-ok" class="bmb2" style="flex:1;text-align:center;padding:9px 4px;border-radius:6px;font-size:10px;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;cursor:pointer;background:var(--battman-blue-soft-bg);color:${C};border:1px solid var(--battman-blue-border)">Set</div></div></div>`;
  let tick = null;
  const dlg = L.modal(anchor, { width: "min(94vw,340px)", close: true, html, onClose: () => clearInterval(tick),
    css: ".bmb2{transition:filter .1s,transform .1s}.bmb2:active{transform:scale(0.94);filter:brightness(1.6)}" });
  if (!dlg) return;
  const Q = (id) => dlg.querySelector(id);
  const done = () => closeDialog(dlg);
  const start = (sec) => { if (!(sec > 0)) return; H.callService("timer", "start", { entity_id: E.timer, duration: Math.round(sec) }); done(); };
  const add = (sec) => { H.callService("timer", "start", { entity_id: E.timer, duration: Math.round((remSec(timerOf(H.states)) || 0) + sec) }); done(); };
  const preview = () => { Q("#sh-pv").innerHTML = L.preview(Q("#sh-d").value, Q("#sh-u").value, "pick a duration or an exact finish time"); };
  dlg.querySelectorAll(".sh-x").forEach((el) => el.addEventListener("click", () => { const sec = parseFloat(el.dataset.s); if (live) add(sec); else start(sec); }));
  dlg.querySelectorAll(".sh-r").forEach((el) => el.addEventListener("click", () => { const at = el.dataset.at; start(at ? L.nextAt(at).sec : parseFloat(el.dataset.s)); }));
  Q("#sh-u").addEventListener("input", () => { if (Q("#sh-u").value) Q("#sh-d").value = ""; preview(); });
  Q("#sh-d").addEventListener("input", () => { if (Q("#sh-d").value) Q("#sh-u").value = ""; preview(); });
  Q("#sh-ok").addEventListener("click", () => start(L.timerSec(Q("#sh-d"), Q("#sh-u"))));
  if (Q("#sh-cx")) Q("#sh-cx").addEventListener("click", () => { H.callService("timer", "cancel", { entity_id: E.timer }); done(); });
  const show = () => {
    const cd = Q("#sh-cd"); if (!cd) return;
    const t = timerOf(hassNow().states), r = remSec(t);
    if (r === null) { cd.textContent = "OFF"; return; }
    cd.textContent = Math.floor(r / 3600) + ":" + pad2(Math.floor((r % 3600) / 60)) + ":" + pad2(r % 60);
    Q("#sh-un").textContent = "until " + L.clk(new Date(t.attributes.finishes_at));
  };
  preview(); show();
  tick = setInterval(show, 1000);
}

// ── the control centre (tap the OVERRIDES strip) ─────────────────────────────────────────────
// Net Target, then the five overrides as panels (one open at a time), the Scenes strip, Save current / Manage.
// Everything inside is plain markup with data-a="action" attributes and ONE click handler on the dialog.
const AMBER = "var(--battman-amber)";
const PIN_PATH = "M16,12V4H17V2H7V4H8V12L6,14V16H11.2V22H12.8V16H18V14L16,12Z";
const MOON_PATH = "M12.3 2a9.9 9.9 0 0 0 0 20 10 10 0 0 0 8.7-5.1A8 8 0 0 1 12.3 2z";
const pairs = (v) => {
  const a = [];
  if ((+v.soc || 0) > 0) a.push((+v.soc).toFixed(0) + "%");
  if ((+v.price || 0) > 0) a.push((+v.price).toFixed(1) + "¢");
  return a;
};
const ntIsBE = (v) => v !== 0 && Math.abs(v) < 0.005;
const ntFmt = (v) => (v === 0 ? "off" : (ntIsBE(v) ? "Break even" : money(v)));
const NT = { c: "var(--battman-teal)", d: "var(--battman-teal-border)", w: "var(--battman-teal-wash)", s: "var(--battman-teal-soft-bg)" };
const NT_BAD = "Buy / sell totals unavailable, so no target can be set";
const CC_LBL = "font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;display:block;margin-bottom:5px";
const CC_CHS = "height:26px;display:inline-flex;align-items:center;padding:0 9px;border-radius:5px;background:var(--battman-surface-card);cursor:pointer;margin:0 5px 5px 0;font-size:11px;font-weight:800";
const CC_TIN = "width:100%;box-sizing:border-box;height:37px;background:var(--battman-surface-card);border:1px solid var(--battman-blue-border);border-radius:6px;color:var(--battman-text-bright);font-size:16px;font-weight:800;text-align:center;padding:0 4px;font-family:var(--battman-font);color-scheme:dark";
const CC_TLB = "font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:var(--battman-blue);display:block;margin-bottom:5px";
const CHEV = `<svg viewBox="0 0 24 24" style="width:15px;height:15px;fill:var(--battman-border-neutral);flex:none"><path d="M7.41 8.59 12 13.17l4.59-4.58L18 10l-6 6-6-6z"/></svg>`;
const rBox = (lk) => (lk ? lib().lockSvg(AMBER, 15) + `<span style="font-size:11px;font-weight:800;color:${AMBER}">ON</span>` : `<span style="font-size:11px;font-weight:800;color:var(--battman-text-muted)">OFF</span>`);

function openControl(anchor) {
  const L = lib();
  if (!L || !L.modal) return;
  const H = hassNow();
  const P = { ...((H.states[E.params] || {}).attributes || {}) };   // a snapshot at open; our own changes are merged in
  let presets = (P.overridePresets || []).slice();
  const UL = L.runUntilList(H);
  const pins = OVERRIDES.filter((o) => P[o.pin] === "show").map((o) => o.id);
  let MG = false, SV = false, SVALS = null, OPEN = -1, TDUR = "", TUNT = "", ARM = String(P.armedScene || "");
  let DRAFT = null;   // what was typed in a panel when its Save was pressed: { i, s, p, locked }
  let NTSIDE = "sell", NTV = 0, NTSV = false, ntHold = null, ntN = 0;
  const tm0 = H.states[E.timer] || {};
  if (tm0.state === "active" && tm0.attributes && tm0.attributes.finishes_at) TUNT = L.clk(new Date(tm0.attributes.finishes_at));
  {
    const s = num(P.netTargetSellPrice), b = num(P.netTargetBuyPrice);
    if (b !== 0 && s === 0) { NTSIDE = "buy"; NTV = b; } else NTV = s;
    if (s !== 0 || b !== 0) OPEN = 99;
  }
  const val = (k) => num(P[k]);
  const lockedNow = (o) => isFalse(P[o.reset]);
  const fire = (d) => { fireParams(d); Object.assign(P, d); };
  const startTimer = (sec) => { if (sec > 0) hassNow().callService("timer", "start", { entity_id: E.timer, duration: Math.round(sec) }); };
  const timerSecShared = () => { const d = parseFloat(TDUR) || 0; if (d > 0) return d * 3600; if (TUNT) return L.nextAt(TUNT).sec; return 0; };
  const ntNet = () => {
    const st = hassNow().states;
    const day = (id) => { const x = st[id]; return x && x.attributes ? parseFloat(x.attributes.day) : NaN; };
    return day(E.sellTotal) - day(E.buyTotal) - num(P.dailyNetworkCharge);
  };

  // ---- markup ----
  const delX = (pi) => (MG ? `<span data-a="del" data-pi="${pi}" style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;margin-left:2px;color:var(--battman-darkred);font-size:16px;font-weight:800;cursor:pointer;flex:none">×</span>` : "");
  const chipsFor = (o) => {
    const K = colours(o);
    let out = "";
    presets.forEach((p, pi) => {
      const v = p.values || {};
      if (Object.keys(v).length !== 1 || !v[o.id]) return;
      const lk = v[o.id].allowReset === false ? L.lockSvg(AMBER, 13) : "";
      out += `<div data-a="apply" data-pi="${pi}" style="height:26px;display:inline-flex;align-items:center;gap:5px;padding:0 9px;border-radius:5px;background:var(--battman-surface-card);border:1px solid ${K.dim};cursor:pointer;margin:0 5px 5px 0">`
        + `<span style="font-size:11px;font-weight:800;color:${K.c}">${esc(p.name)}</span>`
        + `<span style="font-size:10px;font-weight:700;color:var(--battman-text-dim)">${pairs(v[o.id]).join("·")}</span>${lk}${L.presetLabel(p)}${delX(pi)}</div>`;
    });
    return out;
  };
  const timerBlock = (i, mt) =>
    `<div style="border-top:1px solid var(--battman-border-neutral-soft);padding-top:10px;margin:${mt} 0 10px">`
    + `<div style="${CHL}">Start for</div><div style="margin-bottom:9px">`
    + [["15m", 0.25], ["30m", 0.5], ["1h", 1], ["2h", 2]].map((e) => `<span data-a="dur" data-i="${i}" data-h="${e[1]}" style="${CC_CHS};border:1px solid var(--battman-blue-border);color:var(--battman-blue)">${e[0]}</span>`).join("")
    + `</div><div style="${CHL}">Run until</div><div style="margin-bottom:10px">`
    + UL.map((e, n) => `<span data-a="ul" data-i="${i}" data-n="${n}" style="${CC_CHS};border:1px solid var(--battman-border-neutral-soft);color:var(--battman-text-muted)">${esc(e[0])}</span>`).join("")
    + `</div><div style="display:flex;gap:8px;align-items:flex-end"><div style="flex:1"><span style="${CC_TLB}">Timer h</span><input id="t${i}" data-in="tdur" data-i="${i}" type="number" min="0" max="48" step="0.25" placeholder="—" style="${CC_TIN}"></div>`
    + `<div style="color:var(--battman-text-dim);font-size:10px;font-weight:700;padding-bottom:11px">or</div>`
    + `<div style="flex:1"><span style="${CC_TLB}">Until</span><input id="u${i}" data-in="tunt" data-i="${i}" type="time" style="${CC_TIN}"></div></div>`
    + `<div id="pv${i}" style="font-size:11px;font-weight:700;color:var(--battman-text-dim);text-align:center;min-height:15px;margin-top:7px"></div></div>`;

  const panel = (o, i) => {
    const K = colours(o);
    const soc = val(o.soc), price = val(o.price), on = isOn(o, P);
    const parts = [];
    if (soc > 0) parts.push(soc.toFixed(0) + "%");
    if (price > 0 || (o.allowNegative && price < 0)) parts.push(price.toFixed(1) + "¢");
    const pon = pins.indexOf(o.id) >= 0, chips = chipsFor(o), lk0 = lockedNow(o);
    const ph0 = o.id === "drain" && isTrue(P.drainBatteryPlughole);
    const plugRow = o.id !== "drain" ? "" : `<div id="ph${i}" data-a="pht" data-on="${ph0 ? 1 : 0}" style="${plugStyle}">${plugInner(ph0)}</div>`;
    const noReset = `<div style="flex:0.95"><span style="${CC_LBL};color:${AMBER}">No Reset</span>`
      + `<div id="r${i}" data-a="rt" data-on="${lk0 ? 1 : 0}" style="height:37px;box-sizing:border-box;display:flex;align-items:center;justify-content:center;gap:5px;border-radius:6px;cursor:pointer;background:${lk0 ? "var(--battman-amber-wash)" : "transparent"};border:1px solid ${lk0 ? "var(--battman-amber-border)" : "var(--battman-border-neutral)"}">${rBox(lk0)}</div></div>`;
    const head = `<div data-a="toggle" data-i="${i}" style="display:flex;align-items:center;gap:9px;padding:11px 10px 11px 12px;cursor:pointer">`
      + `<div style="width:7px;height:7px;border-radius:50%;background:${on ? K.c : "var(--battman-border-neutral)"};box-shadow:${on ? "0 0 5px " + K.c : "none"};flex:none"></div>`
      + `<div style="font-size:14px;font-weight:800;letter-spacing:0.04em;text-transform:uppercase;color:${on ? K.c : "var(--battman-text-muted)"};flex:1">${o.name}</div>`
      + `<div style="font-size:13px;font-weight:800;color:${on ? K.c : "var(--battman-text-dim)"}">${parts.join(" · ") || "off"}</div>${lk0 ? L.lockSvg(AMBER, 16) : ""}`
      + `<div data-a="pin" data-i="${i}" style="width:24px;height:24px;display:flex;align-items:center;justify-content:center;border-radius:5px;flex:none;cursor:pointer;background:${pon ? "var(--battman-blue-wash)" : "transparent"}">`
      + `<svg viewBox="0 0 24 24" style="width:14px;height:14px;fill:${pon ? "var(--battman-blue)" : "var(--battman-text-dim)"};transform:rotate(${pon ? 0 : 35}deg)"><path d="${PIN_PATH}"/></svg></div>${CHEV}</div>`;
    const numBox = (id, label, max, step) =>
      `<div style="flex:1"><span style="${CC_LBL};color:${K.c}">${label}</span><input id="${id}${i}" data-in="cost" data-i="${i}" type="number" min="0" max="${max}" step="${step}" placeholder="off" style="width:100%;box-sizing:border-box;height:37px;background:var(--battman-surface-card);border:1px solid ${K.dim};border-radius:6px;color:var(--battman-text-bright);font-size:18px;font-weight:800;text-align:center;padding:0 4px"></div>`;
    const calcBlock = o.id === "any"
      ? `<div data-a="calc" data-i="${i}" style="width:100%;box-sizing:border-box;height:40px;border-radius:7px;cursor:pointer;background:var(--battman-purple-soft-bg);border:1px solid ${K.dim};color:${K.c};font-size:12px;font-weight:800;letter-spacing:0.06em;text-transform:uppercase;display:flex;align-items:center;justify-content:center;gap:8px;margin-bottom:8px"><svg viewBox="0 0 24 24" style="width:15px;height:15px;fill:${K.c}"><path d="M13 2 3 14h7l-1 8 10-12h-7z"/></svg>Calculate cheapest price</div>`
        + `<div id="cx-any" style="font-size:11px;font-weight:600;line-height:1.5;color:var(--battman-text-dim);text-align:center;min-height:15px;margin-bottom:10px"></div>` : "";
    const costBlock = o.id === "any" ? `<div id="costpv-any" style="font-size:12px;font-weight:600;line-height:1.5;text-align:center;color:var(--battman-text-dim);min-height:16px;margin-bottom:10px">set a target SOC to preview cost</div>` : "";
    const body = `<div id="b${i}" style="max-height:0;overflow:hidden;transition:max-height .25s ease"><div style="padding:2px 12px 12px">`
      + (chips ? `<div style="margin-bottom:10px">${chips}</div>` : "")
      + `<div style="display:flex;gap:8px;margin-bottom:10px">${numBox("s", "SOC %", 100, 1)}${numBox("p", "PRICE ¢", 200, 0.01)}${noReset}</div>`
      + plugRow + costBlock + timerBlock(i, "0") + calcBlock
      + `<div id="svm${i}" style="text-align:center;min-height:0;margin-bottom:2px"></div>`
      + `<div style="display:flex;gap:6px"><div data-a="clear" data-i="${i}" style="${BTN};background:transparent;color:var(--battman-text-muted);border:1px solid var(--battman-border-neutral)">Clear</div>`
      + `<div data-a="panelsave" data-i="${i}" style="${BTN};background:transparent;color:var(--battman-green);border:1px solid var(--battman-green-border-light)">Save</div>`
      + `<div data-a="set" data-i="${i}" style="${BTN};background:${K.wash};color:${K.c};border:1px solid ${K.dim}">Set</div></div></div></div>`;
    return `<div style="border:1px solid ${on ? K.dim : "var(--battman-border-neutral-soft)"};border-radius:8px;margin-bottom:6px;background:var(--battman-surface-card);overflow:hidden">${head}${body}</div>`;
  };

  const ntReadout = () => {
    const net = ntNet();
    if (isNaN(net)) return `<span>Net today —</span><span style="color:var(--battman-darkred)">${NT_BAD}</span>`;
    let r;
    if (NTV === 0) r = `<span style="color:var(--battman-text-dim)">off — step or pick a chip</span>`;
    else {
      const rem = NTSIDE === "sell" ? NTV - net : net - NTV;
      r = rem > 0.004 ? money(rem) + (NTSIDE === "sell" ? " to make" : " to spend") : `<span style="color:var(--battman-amber)">Already reached · will mark met</span>`;
    }
    return `<span>Net today ${money(net)}</span><span style="opacity:.85">${r}</span>`;
  };
  const ntPanel = () => {
    const s = val("netTargetSellPrice"), b = val("netTargetBuyPrice"), on = s !== 0 || b !== 0;
    const cur = s !== 0 ? "Sell " + ntFmt(s) : (b !== 0 ? "Buy " + ntFmt(b) : "off");
    const SQ = "width:44px;height:44px;flex:none;border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:24px;font-weight:700;cursor:pointer;background:var(--battman-surface-card);touch-action:none;user-select:none;-webkit-user-select:none;-webkit-touch-callout:none";
    const head = `<div data-a="nttoggle" style="display:flex;align-items:center;gap:9px;padding:11px 10px 11px 12px;cursor:pointer"><div style="width:7px;height:7px;border-radius:50%;background:${on ? NT.c : "var(--battman-border-neutral)"};box-shadow:${on ? "0 0 5px " + NT.c : "none"};flex:none"></div>`
      + `<div style="font-size:14px;font-weight:800;letter-spacing:0.04em;text-transform:uppercase;color:${on ? NT.c : "var(--battman-text-muted)"};flex:1">Net Target</div>`
      + `<div style="font-size:13px;font-weight:800;color:${on ? NT.c : "var(--battman-text-dim)"}">${cur}</div>${CHEV}</div>`;
    let seg = `<div style="display:flex;border:1px solid var(--battman-border-neutral);border-radius:6px;overflow:hidden;margin-bottom:10px">`;
    ["Sell", "Buy"].forEach((x, k) => {
      const a = (k === 1) === (NTSIDE === "buy");
      seg += `<div data-a="ntside" data-k="${k}" style="flex:1;height:32px;display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:11px;font-weight:800;letter-spacing:0.12em;text-transform:uppercase;${k === 1 ? "border-left:1px solid var(--battman-border-neutral);" : ""}background:${a ? NT.s : "transparent"};color:${a ? NT.c : "var(--battman-text-dim)"}">${x}</div>`;
    });
    seg += "</div>";
    const NCH = `height:26px;display:inline-flex;align-items:center;gap:5px;padding:0 9px;border-radius:5px;background:var(--battman-surface-card);border:1px solid ${NT.d};cursor:pointer;margin:0 5px 5px 0`;
    let chips = `<div data-a="ntbe" style="${NCH}"><span style="font-size:11px;font-weight:800;color:${NT.c}">Break even</span></div>`;
    presets.forEach((p, pi) => {
      const v = p.values || {};
      if (Object.keys(v).length !== 1 || !v.net) return;
      if ((v.net.side === "buy" ? "buy" : "sell") !== NTSIDE) return;
      chips += `<div data-a="ntapply" data-pi="${pi}" style="${NCH}"><span style="font-size:11px;font-weight:800;color:${NT.c}">${esc(p.name)}</span><span style="font-size:10px;font-weight:700;color:var(--battman-text-muted)">${ntFmt(parseFloat(v.net.price) || 0)}</span>${L.presetLabel(p)}${delX(pi)}</div>`;
    });
    const step = `<span style="${CC_LBL};color:${NT.c}">${NTSIDE === "sell" ? "Sell target $" : "Buy budget $"}</span><div style="display:flex;gap:8px;align-items:center">`
      + `<div data-a="ntdown" data-d="-1" oncontextmenu="return false" style="${SQ};border:1px solid var(--battman-darkred-border);color:var(--battman-darkred)">−</div>`
      + `<div id="ntv" style="flex:1;height:44px;box-sizing:border-box;display:flex;align-items:center;justify-content:center;border-radius:6px;background:var(--battman-surface-card);border:1px solid ${NT.d};font-size:20px;font-weight:800"></div>`
      + `<div data-a="ntdown" data-d="1" oncontextmenu="return false" style="${SQ};border:1px solid var(--battman-green-border);color:var(--battman-green)">+</div></div>`
      + `<div id="ntr" style="display:flex;justify-content:space-between;gap:8px;margin-top:8px;font-size:12px;font-weight:700;color:${NT.c}"></div>`
      + `<div style="font-size:10px;color:var(--battman-text-dim);margin-top:4px">5¢ per tap · hold to speed up · Set clears the ${NTSIDE === "sell" ? "buy" : "sell"} side</div>`;
    const sv = NTSV ? `<div style="display:flex;gap:6px;margin-bottom:10px"><input id="ntnm" type="text" maxlength="16" placeholder="Preset name" style="flex:1;min-width:0;box-sizing:border-box;height:34px;background:var(--battman-surface-card);border:1px solid ${NT.d};border-radius:6px;color:var(--battman-text-bright);font-size:14px;font-weight:700;padding:0 10px"><div data-a="ntsaveok" style="${BTN};flex:none;padding:8px 14px;background:${NT.w};color:${NT.c};border:1px solid ${NT.d}">Save</div></div>` : "";
    const btns = `<div style="display:flex;gap:6px"><div data-a="ntclear" style="${BTN};background:transparent;color:var(--battman-text-muted);border:1px solid var(--battman-border-neutral)">Clear</div>`
      + `<div data-a="ntsave" style="${BTN};background:transparent;color:${NT.c};border:1px solid ${NT.d}">${NTSV ? "Cancel" : "Save"}</div>`
      + `<div data-a="ntset" style="${BTN};background:${NT.w};color:${NT.c};border:1px solid ${NT.d}">Set</div></div>`;
    const body = `<div id="b99" style="max-height:0;overflow:hidden;transition:max-height .25s ease"><div style="padding:2px 12px 12px">${seg}<div style="margin-bottom:6px">${chips}</div>${step}${timerBlock(99, "12px")}${sv}${btns}</div></div>`;
    return `<div id="nt" style="border:1px solid ${on ? NT.d : "var(--battman-border-neutral-soft)"};border-radius:8px;margin-bottom:6px;background:var(--battman-surface-card);overflow:hidden">${head}${body}</div>`;
  };

  const moonBtn = (pi, on) => `<span data-a="arm" data-pi="${pi}" title="Run at 00:01" style="display:inline-flex;align-items:center;gap:3px;height:24px;padding:0 6px;margin-left:2px;border-radius:5px;cursor:pointer;flex:none;border:1px solid ${on ? "var(--battman-blue-border-strong)" : "var(--battman-border-neutral)"};background:${on ? "var(--battman-blue-soft-bg)" : "transparent"}"><svg viewBox="0 0 24 24" style="width:13px;height:13px;fill:${on ? "var(--battman-blue)" : "var(--battman-text-dim)"}"><path d="${MOON_PATH}"/></svg>${on ? `<span style="font-size:10px;font-weight:800;color:var(--battman-blue)">00:01</span>` : ""}</span>`;
  const scenesStrip = () => {
    let out = "";
    presets.forEach((p, pi) => {
      const v = p.values || {};
      if (Object.keys(v).length < 2) return;
      const arm = ARM === p.name, canArm = !!v.net && !MG;
      let dots = "";
      Object.keys(v).forEach((id) => {
        const o = OVERRIDES.find((x) => x.id === id);
        const col = o ? colours(o).c : (id === "net" ? "var(--battman-teal)" : "var(--battman-text-muted)");
        const lk = v[id] && v[id].allowReset === false ? L.lockSvg(col, 12) : "";
        dots += `<span style="display:inline-flex;align-items:center;margin-right:3px"><i style="width:5px;height:5px;border-radius:50%;display:inline-block;background:${col}"></i>${lk}</span>`;
      });
      out += `<div data-a="apply" data-pi="${pi}" style="flex:0 1 auto;max-width:100%;box-sizing:border-box;height:34px;display:flex;align-items:center;gap:6px;padding:0 11px;border-radius:6px;background:${arm ? "var(--battman-blue-wash)" : "var(--battman-surface-card)"};border:1px solid ${arm ? "var(--battman-blue-border-strong)" : "var(--battman-border-neutral-soft)"};cursor:pointer">`
        + `<span style="display:inline-flex">${dots}</span><span style="font-size:11px;font-weight:800;color:${arm ? "var(--battman-text-bright)" : "var(--battman-text-muted)"};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0">${esc(p.name)}</span>${L.presetLabel(p)}${canArm ? moonBtn(pi, arm) : ""}${delX(pi)}</div>`;
    });
    return out;
  };
  const overlay = () => {
    const keys = SVALS ? Object.keys(SVALS) : [];
    let box;
    if (!keys.length) {
      box = `<div style="font-size:12px;color:var(--battman-text-bright);line-height:1.5;text-align:center;margin-bottom:14px">Nothing active to save.<br><span style="color:var(--battman-text-muted);font-size:11px">Set an override first, then save.</span></div>`
        + `<div data-a="savecancel" style="text-align:center;padding:11px;border-radius:7px;font-size:11px;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;color:var(--battman-text-muted);border:1px solid var(--battman-border-neutral);cursor:pointer">Close</div>`;
    } else {
      let rows = "";
      keys.forEach((id) => {
        let o = OVERRIDES.find((x) => x.id === id);
        const cv = id === "net" ? [(SVALS.net.side === "buy" ? "Buy " : "Sell ") + ntFmt(parseFloat(SVALS.net.price) || 0)] : pairs(SVALS[id]);
        const nm = o ? o.name : (id === "net" ? "Net Target" : id);
        const col = o ? colours(o).c : (id === "net" ? "var(--battman-teal)" : "var(--battman-text-muted)");
        const nr = SVALS[id] && SVALS[id].allowReset === false ? L.lockSvg(AMBER, 13) + `<span style="font-size:10px;color:${AMBER};font-weight:700">no reset</span>` : "";
        rows += `<div style="display:flex;align-items:center;gap:8px;padding:3px 0"><div style="width:6px;height:6px;border-radius:50%;background:${col};flex:none"></div>`
          + `<div style="font-size:12px;font-weight:700;color:var(--battman-text-bright);flex:1">${nm}</div>`
          + `<div style="font-size:12px;font-weight:800;color:${col};display:flex;align-items:center;gap:5px">${cv.join(" · ")}${nr}</div></div>`;
      });
      const kind = keys.length > 1 ? keys.length + " overrides → saves as a Scene" : "1 override → saves as a chip";
      const tin = "width:100%;box-sizing:border-box;height:40px;background:var(--battman-surface-card);border:1px solid var(--battman-blue-border);border-radius:7px;color:var(--battman-text-bright);font-size:15px;font-weight:700;text-align:center;padding:0 6px";
      box = `<div style="font-size:10px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:var(--battman-text-dim);margin-bottom:6px">Will save</div>`
        + `<div style="background:var(--battman-surface-card);border:1px solid var(--battman-border-neutral-soft);border-radius:8px;padding:9px 12px;margin-bottom:12px">${rows}</div>`
        + `<div style="margin-bottom:10px"><span style="${CC_LBL};color:var(--battman-text-muted)">Name</span><input id="nm" type="text" placeholder="e.g. Evening dump" style="width:100%;box-sizing:border-box;background:var(--battman-surface-card);border:1px solid var(--battman-border-neutral);border-radius:7px;color:var(--battman-text-bright);font-size:15px;font-weight:700;padding:10px 12px"></div>`
        + `<div style="display:flex;gap:8px;align-items:flex-end;margin-bottom:8px"><div style="flex:1"><span style="${CC_TLB}">Timer h</span><input id="snt" data-in="nin0" type="number" min="0" max="48" step="0.25" placeholder="—" style="${tin}"></div>`
        + `<div style="color:var(--battman-text-dim);font-size:10px;font-weight:700;padding-bottom:13px">or</div>`
        + `<div style="flex:1"><span style="${CC_TLB}">Until</span><input id="snu" data-in="nin1" type="time" style="${tin};font-family:var(--battman-font);color-scheme:dark"></div></div>`
        + `<div style="font-size:10px;color:var(--battman-text-dim);font-weight:700;margin-bottom:10px;text-align:center">Until is re-evaluated each time the preset is applied</div>`
        + `<div style="font-size:11px;color:var(--battman-purple);font-weight:700;margin-bottom:12px">${kind}</div>`
        + `<div style="display:flex;gap:8px"><div data-a="savecancel" style="flex:1;text-align:center;padding:11px;border-radius:7px;font-size:11px;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;color:var(--battman-text-muted);border:1px solid var(--battman-border-neutral);cursor:pointer">Cancel</div>`
        + `<div data-a="saveok" style="flex:1.4;text-align:center;padding:11px;border-radius:7px;font-size:11px;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;color:var(--battman-green);background:var(--battman-green-soft-bg);border:1px solid var(--battman-green-border-strong);cursor:pointer">Save preset</div></div>`;
    }
    return `<div style="position:absolute;inset:0;background:rgba(6,10,18,0.94);border-radius:12px;display:flex;flex-direction:column;justify-content:flex-start;padding:16px;overflow:auto"><div style="font-size:12px;font-weight:800;letter-spacing:0.12em;text-transform:uppercase;color:var(--battman-text-bright);margin-bottom:12px">Save preset</div>${box}</div>`;
  };

  // ---- the dialog ----
  const dlg = L.modal(anchor, { width: "min(94vw,360px)", close: true,
    html: `<div id="cc" style="background:var(--battman-surface-popup);padding:12px;border-radius:12px;font-family:var(--battman-font)"></div>` });
  if (!dlg) return;
  const q = (sel) => dlg.querySelector(sel);
  const closeIt = () => closeDialog(dlg);
  const pv = (i) => { const p = q("#pv" + i); if (p) p.innerHTML = L.preview(TDUR, TUNT, "no timer — stays until cleared"); };
  const ntShow = () => {
    const e = q("#ntv");
    if (e) { e.innerHTML = ntFmt(NTV); e.style.color = NTV === 0 ? "var(--battman-text-dim)" : "var(--battman-text-bright)"; }
    const r = q("#ntr"); if (r) r.innerHTML = ntReadout();
  };
  const expand = (b) => { if (b) b.style.maxHeight = (b.scrollHeight + 4) + "px"; };
  const collapseAll = () => { ["b99", ...OVERRIDES.map((o, i) => "b" + i)].forEach((id) => { const b = q("#" + id); if (b) b.style.maxHeight = "0px"; }); };
  const fillPanel = (i) => {
    const o = OVERRIDES[i];
    q("#s" + i).value = val(o.soc) || "";
    q("#p" + i).value = val(o.price) || "";
    q("#t" + i).value = TDUR; q("#u" + i).value = TUNT;
    if (DRAFT && DRAFT.i === i) {
      q("#s" + i).value = DRAFT.s; q("#p" + i).value = DRAFT.p;
      const r = q("#r" + i);
      if (r && (r.getAttribute("data-on") === "1") !== DRAFT.locked) lockToggle(r);
    }
    pv(i);
    if (o.id === "any") costPreview(H, q("#costpv-any"), parseFloat(q("#s" + i).value) || 0, parseFloat(q("#p" + i).value) || 0, colours(o));
  };
  const fillNet = () => { const t = q("#t99"), u = q("#u99"); if (t) t.value = TDUR; if (u) u.value = TUNT; pv(99); ntShow(); };
  const render = () => {
    const html = `<div style="position:relative"><div style="font-size:11px;font-weight:800;letter-spacing:0.16em;text-transform:uppercase;color:var(--battman-text-muted);display:flex;align-items:center;min-height:44px;box-sizing:border-box;padding:0 60px 9px 0;margin-bottom:9px;border-bottom:1px solid var(--battman-border-neutral-soft)">Overrides</div>`
      + ntPanel() + OVERRIDES.map(panel).join("")
      + (scenesStrip() ? `<div style="font-size:10px;font-weight:800;letter-spacing:0.16em;text-transform:uppercase;color:var(--battman-text-dim);margin:12px 2px 6px">Scenes</div><div style="display:flex;flex-wrap:wrap;gap:6px;padding-bottom:2px">${scenesStrip()}</div>` : "")
      + `<div style="display:flex;align-items:center;justify-content:space-between;margin-top:14px;padding-top:11px;border-top:1px solid var(--battman-border-neutral-soft)">`
      + `<div data-a="saveopen" style="display:inline-flex;align-items:center;gap:5px;height:30px;padding:0 11px;border-radius:6px;cursor:pointer;border:1px solid var(--battman-green-border-light)"><span style="font-size:11px;font-weight:800;letter-spacing:0.06em;text-transform:uppercase;color:var(--battman-green)">＋ Save current</span></div>`
      + `<div data-a="mgmt" style="display:inline-flex;align-items:center;gap:5px;height:30px;padding:0 11px;border-radius:6px;cursor:pointer;border:1px solid ${MG ? "var(--battman-blue-border-strong)" : "var(--battman-border-neutral)"};background:${MG ? "var(--battman-blue-wash)" : "transparent"}"><span style="font-size:11px;font-weight:800;letter-spacing:0.06em;text-transform:uppercase;color:${MG ? "var(--battman-blue)" : "var(--battman-text-muted)"}">${MG ? "Done" : "Manage"}</span></div></div>`
      + `<div style="font-size:11px;color:var(--battman-text-dim);line-height:1.5;margin-top:10px;text-align:center">${MG ? "× deletes a preset · ＋ Save current adds one" : "Chips apply instantly · Scenes replace all overrides + net target · moon runs a scene at 00:01 · pin keeps a row visible"}</div>`
      + (SV ? overlay() : "") + `</div>`;
    q("#cc").innerHTML = html;
    if (SV) { const sc = dlg.querySelector(".bm-scroll"); if (sc) sc.scrollTop = 0; }
    OVERRIDES.forEach((o, i) => fillPanel(i));
    if (!SV) {
      if (OPEN === 99) { fillNet(); expand(q("#b99")); }
      else if (OPEN >= 0) expand(q("#b" + OPEN));
    }
  };
  const ntRedraw = () => { const w = q("#nt"); if (!w) return; w.outerHTML = ntPanel(); if (OPEN === 99) { fillNet(); expand(q("#b99")); } };
  const ntBlocked = () => {
    if (!isNaN(ntNet())) return false;
    const r = q("#ntr"); if (r) r.innerHTML = `<span style="color:var(--battman-darkred)">${NT_BAD}</span>`;
    return true;
  };
  const ntFireV = (side, v) => fire({ netTargetSellPrice: side === "sell" ? v : 0, netTargetBuyPrice: side === "buy" ? v : 0 });
  const ntStep = (k) => {
    const v = ntIsBE(NTV) ? 0 : NTV;
    NTV = Math.round((Math.round(v * 20) / 20 + k * 0.05) * 100) / 100;
    if (Math.abs(NTV) < 0.001) NTV = 0;
    if (NTV > 999) NTV = 999;
    if (NTV < -999) NTV = -999;
    ntShow();
  };
  const ntUp = () => { if (ntHold) { clearTimeout(ntHold); ntHold = null; } };
  const ntDown = (d) => {
    ntUp(); ntN = 0; ntStep(d);
    ntHold = setTimeout(function rep() { ntN++; ntStep(d * (ntN > 30 ? 20 : (ntN > 12 ? 4 : 1))); ntHold = setTimeout(rep, ntN > 12 ? 70 : 120); }, 420);
  };
  const lockToggle = (el) => {
    const on = el.getAttribute("data-on") !== "1";
    el.setAttribute("data-on", on ? "1" : "0");
    el.style.background = on ? "var(--battman-amber-soft-bg)" : "transparent";
    el.style.borderColor = on ? "var(--battman-amber-border)" : "var(--battman-border-neutral)";
    el.innerHTML = rBox(on);
  };

  const ACT = {
    toggle(t) {
      const i = +t.dataset.i, b = q("#b" + i);
      if (!b) return;
      const open = b.style.maxHeight && b.style.maxHeight !== "0px";
      collapseAll();
      if (!open) { OPEN = i; fillPanel(i); expand(b); } else OPEN = -1;
    },
    nttoggle() {
      const b = q("#b99");
      if (!b) return;
      const open = b.style.maxHeight && b.style.maxHeight !== "0px";
      collapseAll();
      if (open) OPEN = -1; else { OPEN = 99; fillNet(); expand(b); }
    },
    pin(t) {
      const o = OVERRIDES[+t.dataset.i], on = pins.indexOf(o.id) >= 0;
      if (on) pins.splice(pins.indexOf(o.id), 1); else pins.push(o.id);
      fire({ [o.pin]: on ? "hide" : "show" });
      render();
    },
    rt(t) { lockToggle(t); },
    pht(t) {
      const on = t.getAttribute("data-on") !== "1";
      t.setAttribute("data-on", on ? "1" : "0");
      t.setAttribute("style", plugStyle);
      t.innerHTML = plugInner(on);
    },
    dur(t) {
      const i = +t.dataset.i;
      TDUR = String(t.dataset.h); TUNT = "";
      const d = q("#t" + i), u = q("#u" + i);
      if (u) u.value = ""; if (d) d.value = TDUR;
      pv(i);
    },
    ul(t) {
      const i = +t.dataset.i;
      TUNT = UL[+t.dataset.n][2]; TDUR = "";
      const d = q("#t" + i), u = q("#u" + i);
      if (d) d.value = ""; if (u) u.value = TUNT;
      pv(i);
    },
    calc(t) {
      const i = +t.dataset.i, o = OVERRIDES[i];
      cheapestPrice(hassNow(), q("#cx-any"), parseFloat(q("#s" + i).value) || 0, timerSecShared(), colours(o), (v) => { q("#p" + i).value = v; },
        () => costPreview(H, q("#costpv-any"), parseFloat(q("#s" + i).value) || 0, parseFloat(q("#p" + i).value) || 0, colours(o)));
    },
    set(t) {
      const i = +t.dataset.i, o = OVERRIDES[i];
      const d = { [o.soc]: parseFloat(q("#s" + i).value) || 0, [o.price]: parseFloat(q("#p" + i).value) || 0 };
      startTimer(timerSecShared());
      const r = q("#r" + i); if (r) d[o.reset] = r.getAttribute("data-on") !== "1";
      const ph = q("#ph" + i); if (ph) d.drainBatteryPlughole = ph.getAttribute("data-on") === "1";
      fire(d); closeIt();
    },
    clear(t) {
      const o = OVERRIDES[+t.dataset.i];
      const d = { [o.soc]: 0, [o.price]: 0, [o.reset]: true };
      if (o.id === "drain") d.drainBatteryPlughole = false;
      fire(d); closeIt();
    },
    apply(t) {
      if (MG) return;
      const p = presets[+t.dataset.pi], v = p.values || {};
      if (Object.keys(v).length > 1) { hassNow().callService("script", E.scene.split(".")[1], { name: p.name }); closeIt(); return; }
      const d = {};
      OVERRIDES.forEach((o) => {
        if (v[o.id]) { d[o.soc] = parseFloat(v[o.id].soc) || 0; d[o.price] = parseFloat(v[o.id].price) || 0; d[o.reset] = v[o.id].allowReset !== false; }
      });
      fire(d); startTimer(L.presetSec(p)); closeIt();
    },
    del(t) {
      const pi = +t.dataset.pi, dn = presets[pi] && presets[pi].name;
      presets.splice(pi, 1);
      const d0 = { overridePresets: presets };
      if (dn && dn === ARM) { ARM = ""; d0.armedScene = ""; }
      fire(d0); render();
    },
    arm(t) {
      const nm = presets[+t.dataset.pi].name;
      ARM = ARM === nm ? "" : nm;
      fire({ armedScene: ARM }); render();
    },
    mgmt() { MG = !MG; if (!MG) { SV = false; SVALS = null; } render(); },
    // Save in a panel: the values typed there (not applied) become a preset chip for that override
    panelsave(t) {
      const i = +t.dataset.i, o = OVERRIDES[i];
      const sv = parseFloat(q("#s" + i).value) || 0, pr = parseFloat(q("#p" + i).value) || 0;
      const r = q("#r" + i), locked = !!r && r.getAttribute("data-on") === "1";
      if (sv <= 0 && pr <= 0 && !(o.allowNegative && pr < 0)) {
        const m = q("#svm" + i);
        if (m) m.innerHTML = `<span style="color:var(--battman-amber);font-size:11px">Set a value first</span>`;
        return;
      }
      DRAFT = { i, s: q("#s" + i).value, p: q("#p" + i).value, locked };
      SVALS = { [o.id]: { soc: sv, price: pr, allowReset: !locked } };
      SV = true; render();
      const nt = q("#snt"), nu = q("#snu");                            // the timer typed in the panel comes along
      if (nt) nt.value = TDUR;
      if (nu) nu.value = TUNT;
      const ni = q("#nm"); if (ni) ni.focus();
    },
    saveopen() {
      const vals = {};
      OVERRIDES.forEach((o) => {
        const s = val(o.soc), pr = val(o.price);
        if (s > 0 || pr > 0 || (o.allowNegative && pr < 0)) vals[o.id] = { soc: s, price: pr, allowReset: !lockedNow(o) };
      });
      const ns = val("netTargetSellPrice"), nb = val("netTargetBuyPrice");
      if (ns !== 0) vals.net = { side: "sell", price: ns }; else if (nb !== 0) vals.net = { side: "buy", price: nb };
      SVALS = vals; SV = true; render();
      const ni = q("#nm"); if (ni) ni.focus();
    },
    savecancel() { SV = false; SVALS = null; render(); },
    saveok() {
      const ni = q("#nm"), nm = ni ? ni.value.trim() : "";
      if (!nm) { if (ni) { ni.style.borderColor = "var(--battman-darkred)"; ni.focus(); } return; }
      const ti = q("#snt"), ui = q("#snu");
      const th = ti ? (parseFloat(ti.value) || 0) : 0, ta = ui ? ui.value : "";
      const np = { name: nm, timer: (!ta && th > 0) ? Math.round(th * 3600) : 0, values: SVALS };
      if (ta) np.timer_at = ta;
      presets = presets.concat([np]);
      fire({ overridePresets: presets }); SV = false; SVALS = null; DRAFT = null; render();
    },
    ntside(t) { const s = +t.dataset.k === 1 ? "buy" : "sell"; if (s === NTSIDE) return; NTSIDE = s; ntRedraw(); },
    ntbe() { if (MG || ntBlocked()) return; ntFireV(NTSIDE, NTSIDE === "sell" ? 0.001 : -0.001); closeIt(); },
    ntapply(t) {
      if (MG || ntBlocked()) return;
      const p = presets[+t.dataset.pi];
      if (!p || !p.values || !p.values.net) return;
      const n = p.values.net;
      ntFireV(n.side === "buy" ? "buy" : "sell", parseFloat(n.price) || 0);
      startTimer(L.presetSec(p)); closeIt();
    },
    ntset() { if (NTV !== 0 && ntBlocked()) return; ntFireV(NTSIDE, NTV); startTimer(timerSecShared()); closeIt(); },
    ntclear() { fire({ netTargetSellPrice: 0, netTargetBuyPrice: 0 }); closeIt(); },
    ntsave() { NTSV = !NTSV; ntRedraw(); const n = q("#ntnm"); if (n) n.focus(); },
    ntsaveok() {
      const n = q("#ntnm"), nm = n ? n.value.trim() : "";
      if (!nm || NTV === 0) { if (n) { n.style.borderColor = "var(--battman-darkred)"; n.focus(); } return; }
      const ta = TUNT, th = parseFloat(TDUR) || 0;
      const np = { name: nm, timer: (!ta && th > 0) ? Math.round(th * 3600) : 0, values: { net: { side: NTSIDE, price: NTV } } };
      if (ta) np.timer_at = ta;
      presets = presets.concat([np]);
      fire({ overridePresets: presets }); NTSV = false; ntRedraw();
    },
  };
  dlg.addEventListener("click", (e) => {
    const t = e.target.closest ? e.target.closest("[data-a]") : null;
    if (t && ACT[t.dataset.a]) ACT[t.dataset.a](t);
  });
  dlg.addEventListener("input", (e) => {
    const t = e.target, k = t.dataset && t.dataset.in;
    if (!k) return;
    const i = +t.dataset.i;
    if (k === "tdur") { TDUR = t.value; if (t.value) { TUNT = ""; q("#u" + i).value = ""; } pv(i); }
    else if (k === "tunt") { TUNT = t.value; if (t.value) { TDUR = ""; q("#t" + i).value = ""; } pv(i); }
    else if (k === "cost") {
      if (OVERRIDES[i].id === "any") costPreview(H, q("#costpv-any"), parseFloat(q("#s" + i).value) || 0, parseFloat(q("#p" + i).value) || 0, colours(OVERRIDES[i]));
    } else if (k === "nin0") { if (t.value) q("#snu").value = ""; }
    else if (k === "nin1") { if (t.value) q("#snt").value = ""; }
  });
  // hold the net target's - / + to repeat, faster the longer it's held
  dlg.addEventListener("pointerdown", (e) => {
    const t = e.target.closest ? e.target.closest('[data-a="ntdown"]') : null;
    if (!t) return;
    e.preventDefault();
    ntDown(+t.dataset.d);
  });
  ["pointerup", "pointerleave", "pointercancel"].forEach((ev) => dlg.addEventListener(ev, ntUp, true));
  dlg.addEventListener("close", ntUp);
  render();
}

// Hold the strip: how the dock works.
function openDockHelp(anchor) {
  const L = lib();
  if (!L || !L.modal) return;
  const m = (t, size = 10) => `<div style="margin-bottom:4px;color:var(--battman-text-muted);font-size:${size}px">${t}</div>`;
  const k = (t, col = "var(--battman-text-bright)") => `<span style="color:${col};font-weight:600">${t}</span>`;
  L.modal(anchor, { width: "min(94vw,360px)", close: true, html:
    `<div style="background:var(--battman-surface-popup);padding:14px 16px;border-radius:8px;font-family:var(--battman-font)">`
    + `<div style="font-size:9px;font-weight:700;color:var(--battman-text-muted);text-transform:uppercase;letter-spacing:0.14em;display:flex;align-items:center;min-height:44px;box-sizing:border-box;padding:0 60px 6px 0;margin-bottom:10px;border-bottom:1px solid var(--battman-border-neutral-soft)">Override Dock</div>`
    + m("Rows appear below the dock when an override is active or pinned. The override timer follows the same rule.", 11)
    + `<div style="border-top:1px solid var(--battman-border-neutral-soft);margin:8px 0"></div>`
    + m(`${k("Dock tap:")} control centre — presets, values, pins and the override timer.`)
    + m(`${k("Row tap:")} quick-edit. ${k("Double-tap:")} clear. ${k("Hold:")} help.`)
    + m(`${k("No reset:", "var(--battman-amber)")} shown on the right of the dock, with a dot per locked override, and the dock border turns amber. A locked override will NOT clear itself when its target is met.`)
    + m(`${k("Net target:", "var(--battman-teal)")} a daily net goal (sell) or budget (buy), set in the control centre. When net today passes it the watchdog clears that side and the dock shows TARGET MET or BUDGET REACHED until the timer ends, a new target is set, or midnight. The No Reset chip hides while a target is shown; padlocks on rows still apply.`)
    + m(`${k("Override timer:")} when running it shows as its own row. Tap the clock — there or in the control centre — for the timer sheet: extend chips, run-until chips, or an exact finish time. Pin it to keep it visible while it is off.`)
    + m(`${k("Presets:")} a preset saved with an Until time re-resolves that time every time it is applied.`)
    + m(`${k("Preset names:")} up to ~9 characters keep the row as-is. Longer names shrink the cost value in steps, then move it beside the kWh figure.`)
    + `<div style="margin-top:10px;padding:6px 8px;background:var(--battman-yellow-soft-bg);border-left:2px solid var(--battman-yellow);border-radius:3px;font-size:10px;color:var(--battman-yellow);font-weight:700;letter-spacing:0.02em">⚡ Spike Rules will always override everything</div></div>` });
}

const TAP_GAP = 300, HOLD_MS = 500;

const CSS = `
  :host { display: block; }
  .stack { display: flex; flex-direction: column; gap: 2px; font-family: var(--primary-font-family, sans-serif); }
  .strip { height: 52px; box-sizing: border-box; border-radius: 8px; overflow: hidden; cursor: pointer; }
  .strip-in { height: 100%; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 0 14px; }
  .row { position: relative; height: 60px; box-sizing: border-box; border-radius: 8px; overflow: hidden; cursor: pointer; }
  .strip, .row { transition: filter .1s, transform .1s; }
  .strip:active, .row:active { transform: scale(0.96); filter: brightness(1.5); }
  .moon { animation: pulse 1.6s ease-in-out infinite; }
  @keyframes pulse { 50% { opacity: .3; } }
  @media (prefers-reduced-motion: reduce) { .moon { animation: none; } }
  .gone { display: none; }
  .tbar { height: 60px; box-sizing: border-box; background: var(--battman-surface-card); border-radius: 8px; padding: 0 14px; overflow: hidden;
    display: grid; grid-template-columns: 46px 1fr auto; column-gap: 10px; align-items: center; }
  .bmb2 { transition: filter .1s, transform .1s; }
  .bmb2:active { transform: scale(0.94); filter: brightness(1.6); }
`;

class BattmanOverrides extends BattmanCardBase {
  static cardName = "Battman Overrides";
  static css = CSS;
  static html = `<div class="stack"><div id="strip"></div><div id="rows" class="stack"></div><div id="timer"></div></div>`;

  // HA's Add card list: the card itself, drawn from sample settings (no picture file to ship)
  _build() {
    if (!this._hass || !this.isConnected || this._built) return;
    if (!inCardPicker(this)) return super._build();
    this._built = true;
    const a = { sellOverrideSOC: 20, sellOverridePrice: 30, buyAnytimeSOC: 80, buyAnytimePrice: 9, netTargetSellPrice: 5 };
    this.shadowRoot.innerHTML = `<style>${CSS}</style><div class="stack">${stripHtml(a, {}, E)}`
      + `${rowHtml(OVERRIDES[0], a, {}, E)}${rowHtml(OVERRIDES[3], a, {}, E)}</div>`;
  }

  // The entities Battman's map names (the parameters sensor, the override timer, the totals, the scene script, Sigen's available power), then the card starts.
  run(root) {
    let inner = null;
    battmanMap(this.hass, ["parameters", "override_timer", "sell_total", "buy_total", "apply_scene_script", "sigen_available_max_active_power"])
      .then((m) => {
        Object.assign(E, { params: m.parameters, timer: m.override_timer, sellTotal: m.sell_total, buyTotal: m.buy_total, scene: m.apply_scene_script,
          chargeKw: m.sigen_available_max_active_power });
        inner = this.start(root);
      })
      .catch((e) => this.problem(e.message));
    return {
      hassChanged: (old) => inner && inner.hassChanged(old),
      themeChanged: () => inner && inner.themeChanged(),
      pause: () => inner && inner.pause(),
      resume: () => inner && inner.resume(),
    };
  }

  start(root) {
    let last = "", lastRefs = null;
    const invalidate = () => { last = ""; lastRefs = null; };
    const draw = () => {
      const hass = this.hass;
      const st = hass.states;
      const p = st[E.params];
      // HA hands over a new hass on every state change anywhere: skip at once unless one of OUR states is a new object
      const refs = [p, st[E.soc], st[E.capacity], st[E.sellTotal], st[E.buyTotal], st[E.timer]];
      if (lastRefs && refs.every((r, i) => r === lastRefs[i])) return;
      lastRefs = refs;
      if (!p) { root.getElementById("strip").innerHTML = `<div style="padding:12px;color:var(--error-color)">${E.params} not found</div>`; return; }
      const a = p.attributes;
      // redraw only when something this card shows has changed
      const key = JSON.stringify([a, (st[E.soc] || {}).state, (st[E.capacity] || {}).state,
        (st[E.sellTotal] || {}).attributes, (st[E.buyTotal] || {}).attributes, timerOf(st).state, timerOf(st).attributes.finishes_at, getUnit()]);
      if (key === last) return;
      last = key;
      root.getElementById("strip").innerHTML = stripHtml(a, st, E);
      root.getElementById("rows").innerHTML = OVERRIDES
        .filter((o) => isOn(o, a) || a[o.pin] === "show")
        .map((o) => rowHtml(o, a, st, E)).join("");
      root.getElementById("timer").innerHTML = timerShown(a, st) ? timerHtml(st, getUnit()) : "";
    };
    draw();
    // Gestures on the rows (pointer events: iPhone doesn't always turn a tap in a card into a click).
    // hold = help, double-tap = clear, single tap (after the gap, so a double-tap doesn't also open the popup) = edit.
    const rowsEl = root.getElementById("rows");
    let holdT = null, held = false, tapT = null, lastTap = { id: "", t: 0 };
    const find = (e) => { const r = e.target.closest ? e.target.closest(".row") : null; return r ? { r, o: OVERRIDES.find((x) => x.id === r.dataset.id) } : null; };
    rowsEl.addEventListener("pointerdown", (e) => {
      const f = find(e); if (!f) return;
      held = false; clearTimeout(holdT);
      holdT = setTimeout(() => { held = true; openHelp(f.o, f.r); }, HOLD_MS);
    });
    ["pointercancel", "pointerleave"].forEach((ev) => rowsEl.addEventListener(ev, () => clearTimeout(holdT)));
    rowsEl.addEventListener("pointerup", (e) => {
      clearTimeout(holdT);
      const f = find(e); if (!f || held) return;
      const now = Date.now();
      if (lastTap.id === f.o.id && now - lastTap.t < TAP_GAP) { clearTimeout(tapT); lastTap = { id: "", t: 0 }; clearOverride(f.o); return; }
      lastTap = { id: f.o.id, t: now };
      clearTimeout(tapT);
      tapT = setTimeout(() => openEdit(f.o, f.r), TAP_GAP);
    });
    // The strip: tap = control centre, hold = how the dock works.
    const stripEl = root.getElementById("strip");
    let sHold = null, sHeld = false;
    const onStrip = (e) => (e.target.closest ? e.target.closest(".strip") : null);
    stripEl.addEventListener("pointerdown", (e) => {
      const el = onStrip(e); if (!el) return;
      sHeld = false; clearTimeout(sHold);
      sHold = setTimeout(() => { sHeld = true; openDockHelp(el); }, HOLD_MS);
    });
    ["pointercancel", "pointerleave"].forEach((ev) => stripEl.addEventListener(ev, () => clearTimeout(sHold)));
    stripEl.addEventListener("pointerup", (e) => {
      clearTimeout(sHold);
      const el = onStrip(e);
      if (el && !sHeld) openControl(el);
    });
    // The timer bar: toggle, H/M unit, - / +, tap the middle for the sheet, hold it for more-info.
    const timerEl = root.getElementById("timer");
    let tHold = null, tHeld = false;
    const svc = (d, sv, data) => hassNow().callService(d, sv, data);
    timerEl.addEventListener("pointerdown", (e) => {
      if (!(e.target.closest && e.target.closest(".tmid"))) return;
      tHeld = false; clearTimeout(tHold);
      tHold = setTimeout(() => { tHeld = true; timerEl.dispatchEvent(new CustomEvent("hass-more-info", { detail: { entityId: E.timer }, bubbles: true, composed: true })); }, HOLD_MS);
    });
    ["pointercancel", "pointerleave"].forEach((ev) => timerEl.addEventListener(ev, () => clearTimeout(tHold)));
    timerEl.addEventListener("pointerup", (e) => {
      clearTimeout(tHold);
      const c = (sel) => e.target.closest && e.target.closest(sel);
      const t = timerOf(hassNow().states);
      if (c(".tpill")) svc("timer", t.state === "active" ? "cancel" : "start", { entity_id: E.timer });
      else if (c(".tu")) { setUnitStore(c(".tu").dataset.u); invalidate(); draw(); }
      else if (c(".tminus")) { if (t.state === "active") svc("timer", "change", { entity_id: E.timer, duration: getUnit() === "m" ? "-00:01:00" : "-01:00:00" }); }
      else if (c(".tplus")) svc("timer", "start", { entity_id: E.timer, duration: (remSec(t) || 0) + (getUnit() === "m" ? 60 : 3600) });
      else if (c(".tmid") && !tHeld) openTimerSheet(c(".tmid"));
    });
    // the countdown ticks every second (the card only redraws when something changes)
    let ticker = setInterval(() => {
      const cd = root.getElementById("tcd");
      if (!cd) return;
      const r = remSec(timerOf(hassNow().states));
      if (r !== null) cd.textContent = countdown(r);
    }, 1000);
    return { hassChanged: draw, themeChanged: () => { invalidate(); draw(); },
      pause: () => { clearInterval(ticker); ticker = null; },
      resume: () => { if (!ticker) ticker = setInterval(() => { const cd = root.getElementById("tcd"); if (!cd) return; const r = remSec(timerOf(hassNow().states)); if (r !== null) cd.textContent = countdown(r); }, 1000); invalidate(); draw(); } };
  }
}

// for the tests (tests/js/overrides_check.mjs)
export { BattmanOverrides, clearOverride, countdown, openControl, openDockHelp, openEdit, openHelp, openTimerSheet, remSec, timerHtml, timerShown };

battmanDefine("battman-overrides", BattmanOverrides);
battmanPicker("battman-overrides", "Battman Overrides",
  "The override dock: Sell, Sell Solar, Buy, Buy Anytime and Drain overrides, the control centre (presets, scenes, Net Target) and the override timer.",
  "battman-overrides");
