// Battman Overrides, the part the Overrides card and the Theme studio share: the five overrides (one list),
// and the OVERRIDES strip and the override rows drawn from them. Pure functions of the settings (the parameters
// sensor's attributes) and the states, so the same code draws the card and the studio's preview.
//
//   stripHtml(attrs, states, E)       the 52px strip: No reset chip, armed scene, Plughole, Net Target readout
//   rowHtml(override, attrs, states, E)   one 60px row (SOC, price, cost, preset name, lock)
//   E = the entity names: { soc, capacity, sellTotal, buyTotal }

import { esc } from "./battman-card-base.js";

// One entry per override. Colours come from the hue name: --battman-<hue>, -border, -wash, -border-soft, -soft-bg.
export const OVERRIDES = [
  { id: "sell", name: "Sell Override", helpSoc: "Fixed battery level to sell down to, overriding the normal time-based curve. Setting 100% means no selling at all.", helpPrice: "Minimum sell price — energy only sold if price is above this value.", label: "SELL<br>OVERRIDE", hue: "green", soc: "sellOverrideSOC", price: "sellOverridePrice",
    reset: "sellOverrideAllowReset", pin: "sellOverridePinned", dir: "down", money: "EARN", specialAt: 100, specialDesc: "NO SELLING" },
  { id: "sellsolar", name: "Sell Solar", helpSoc: "Battery level threshold for solar selling, overriding the normal time-based curve.", helpPrice: "Minimum sell price — solar only sold if price is above this value.", label: "SELL<br>SOLAR", hue: "orange", soc: "sellSolarSOC", price: "sellSolarPrice",
    reset: "sellSolarAllowReset", pin: "sellSolarPinned", dir: "down", money: "EARN", specialAt: 0, specialDesc: "" },
  { id: "buy", name: "Buy Override", helpSoc: "Fixed battery level to buy up to, overriding the normal time-based curve.", helpPrice: "Maximum buy price — energy only bought if price is below this value.", label: "BUY<br>OVERRIDE", hue: "yellow", soc: "buyOverrideSOC", price: "buyOverridePrice",
    reset: "buyOverrideAllowReset", pin: "buyOverridePinned", dir: "up", money: "COST", specialAt: 0, specialDesc: "", allowNegative: true },
  { id: "any", name: "Buy Anytime", helpSoc: "Target battery level to charge up to at any time, ignoring the time-based curve.", helpPrice: "Maximum buy price — energy only bought if price is below this value.", label: "BUY<br>ANYTIME", hue: "purple", soc: "buyAnytimeSOC", price: "buyAnytimePrice",
    reset: "buyAnytimeAllowReset", pin: "buyAnytimePinned", dir: "up", money: "COST", specialAt: 0, specialDesc: "" },
  { id: "drain", name: "Drain Battery", helpSoc: "Fixed battery level to drain down to — the house runs off the battery with solar off until this level, then the override clears.", helpPrice: "Only drain while price is below this value (kept for consistency; drain is a manual mode).", label: "DRAIN<br>BATTERY", hue: "red", soc: "drainBatterySOC", price: "drainBatteryPrice",
    reset: "drainBatteryAllowReset", pin: "drainBatteryPinned", dir: "down", money: "COST", specialAt: 100, specialDesc: "NO DRAINING" },
];
export const colours = (o) => {
  const v = `var(--battman-${o.hue}`;
  return { c: `${v})`, dim: `${v}-border)`, wash: `${v}-wash)`, washBorder: `${v}-border-soft)`, bg: `${v}-soft-bg)` };
};

export const num = (v) => parseFloat(v) || 0;
export const isTrue = (v) => v === true || v === "true";
export const isFalse = (v) => v === false || v === "false";
export const pad2 = (n) => ("0" + n).slice(-2);
export const money = (v) => {
  if (isNaN(v)) return "—";
  const n = Math.abs(v) < 0.005 ? 0 : v;
  return (n < 0 ? "−" : "") + "$" + Math.abs(n).toFixed(2);
};
export const isOn = (o, a) => {
  const soc = num(a[o.soc]), price = num(a[o.price]);
  return soc > 0 || price > 0 || (!!o.allowNegative && price < 0);
};

// The Net Target state: today's net (sell total - buy total - daily network charge), the target set
// (sell or buy), what is left to reach it, and a "met" time that stays until midnight.
export function netState(a, states, E) {
  const day = (id) => {
    const s = states[id];
    return s && s.attributes ? parseFloat(s.attributes.day) : NaN;   // a missing total is unknown, not $0
  };
  const net = day(E.sellTotal) - day(E.buyTotal) - num(a.dailyNetworkCharge);
  const ts = num(a.netTargetSellPrice), tb = num(a.netTargetBuyPrice);
  const met = (v) => {
    if (!v || typeof v !== "string" || v.indexOf("|") < 0) return null;
    const p = v.split("|"), t = new Date(p[0].trim().replace(/\.\d+/, ""));
    if (isNaN(t.getTime())) return null;
    const n = new Date();
    if (t.getFullYear() !== n.getFullYear() || t.getMonth() !== n.getMonth() || t.getDate() !== n.getDate()) return null;
    return { t, v: parseFloat(p[1]) || 0 };
  };
  const mode = ts !== 0 ? "sell" : (tb !== 0 ? "buy" : "");
  const target = mode === "sell" ? ts : tb;
  const sm = met(a.netTargetSellMet), bm = met(a.netTargetBuyMet);
  let metK = "";
  if (!mode) {
    if (sm && (!bm || sm.t >= bm.t)) metK = "sell";
    else if (bm) metK = "buy";
  }
  let rem = mode === "sell" ? target - net : (mode === "buy" ? net - target : 0);
  if (rem < 0) rem = 0;
  return { net, mode, target, be: mode !== "" && Math.abs(target) < 0.005, rem, met: metK,
    metAt: metK === "sell" ? sm.t : (metK === "buy" ? bm.t : null), active: mode !== "" || metK !== "" };
}

const LOCK = "M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z";
export const lockSvg = (px, block) => `<svg viewBox="0 0 24 24" style="width:${px}px;height:${px}px;fill:var(--battman-amber);flex:none${block ? ";display:block" : ""}"><path d="${LOCK}"/></svg>`;

// ── the 52px OVERRIDES strip ─────────────────────────────────────────────────────────────────
export function stripHtml(a, states, E) {
  const NS = netState(a, states, E);
  let anyOn = false, noSell = false, warn = false, warnDots = "";
  OVERRIDES.forEach((o) => {
    const soc = num(a[o.soc]);
    const on = isOn(o, a);
    if (on) anyOn = true;
    if (o.specialAt > 0 && soc === o.specialAt) noSell = true;
    if (on && isFalse(a[o.reset])) {
      warn = true;
      const c = colours(o).c;
      warnDots += `<div style="width:7px;height:7px;border-radius:50%;background:${c};box-shadow:0 0 6px ${c}"></div>`;
    }
  });
  const label = noSell ? "OVERRIDES · NO SELL" : "OVERRIDES";
  const lcolor = noSell ? "var(--battman-green)" : (anyOn ? "var(--battman-text-bright)" : "var(--battman-text-muted)");

  const lockChip = (warn && !NS.active)
    ? `<div style="display:flex;align-items:center;gap:7px;flex:none">${lockSvg(13)}`
      + `<span style="font-size:10px;font-weight:800;letter-spacing:0.1em;text-transform:uppercase;color:var(--battman-amber);white-space:nowrap">No reset</span>`
      + `<div style="display:flex;gap:5px;align-items:center">${warnDots}</div></div>`
    : "";

  const armName = String(a.armedScene || "").trim();
  const armChip = armName
    ? `<div title="Runs at 00:01" style="display:flex;align-items:center;gap:5px;height:24px;padding:0 8px;border-radius:12px;flex:0 1 auto;min-width:0;background:var(--battman-blue-soft-bg);border:1px solid var(--battman-blue-border-strong)">`
      + `<svg viewBox="0 0 24 24" class="moon" style="width:12px;height:12px;fill:var(--battman-blue);flex:none"><path d="M12.3 2a9.9 9.9 0 0 0 0 20 10 10 0 0 0 8.7-5.1A8 8 0 0 1 12.3 2z"/></svg>`
      + `<span style="font-size:10px;font-weight:800;letter-spacing:0.06em;text-transform:uppercase;color:var(--battman-blue);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0">${esc(armName)}</span>`
      + `<span style="font-size:10px;font-weight:800;color:var(--battman-blue);flex:none">00:01</span></div>`
    : "";

  const plugOn = isTrue(a.drainBatteryPlughole) && (num(a.drainBatterySOC) > 0 || num(a.drainBatteryPrice) > 0);
  const plugChip = plugOn
    ? `<div style="display:flex;align-items:center;gap:4px;height:24px;padding:0 8px;border-radius:12px;flex:none;background:var(--battman-red-soft-bg);border:1px solid var(--battman-red)">`
      + `<span style="font-size:10px;font-weight:800;letter-spacing:0.06em;text-transform:uppercase;color:var(--battman-red);white-space:nowrap">Plughole</span></div>`
    : "";

  let netRight = "";
  if (NS.active) {
    const TC = "var(--battman-teal)";
    const t1 = `font-size:12px;font-weight:800;letter-spacing:0.04em;color:${TC};white-space:nowrap`;
    const t2 = `font-size:12px;font-weight:700;opacity:0.9;color:${TC};white-space:nowrap`;
    const big = (lbl, v) =>
      `<div style="display:flex;flex-direction:column;align-items:flex-end;flex:none">`
      + `<span style="font-size:8px;font-weight:800;letter-spacing:0.1em;color:${TC};opacity:0.6;white-space:nowrap">${lbl}</span>`
      + `<span style="font-size:22px;font-weight:900;color:${TC};line-height:1;white-space:nowrap">${v}</span></div>`;
    const word = NS.mode === "sell" ? " to make" : " to spend";
    if (NS.mode && NS.be) {
      netRight = `<div style="text-align:right;line-height:1.25;flex:none"><div style="${t1}">BREAK EVEN</div><div style="${t2}">${money(NS.rem)}${word}</div></div>`;
    } else if (NS.mode) {
      netRight = `<div style="display:flex;align-items:center;gap:12px;flex:none"><span style="${t2}">${money(NS.rem)}${word}</span>${big(NS.mode === "sell" ? "SELL TARGET" : "BUY BUDGET", money(NS.target))}</div>`;
    } else {
      const at = NS.metAt ? " " + pad2(NS.metAt.getHours()) + ":" + pad2(NS.metAt.getMinutes()) : "";
      netRight = `<div style="display:flex;align-items:center;gap:12px;flex:none"><span style="${t1}">${NS.met === "sell" ? "TARGET MET" : "BUDGET REACHED"}${at}</span>${big("NET TODAY", money(NS.net))}</div>`;
    }
  }

  const bg = NS.met
    ? "linear-gradient(var(--battman-teal-soft-bg),var(--battman-teal-soft-bg)),var(--battman-surface-card)"
    : "var(--battman-surface-card)";
  let border;
  if (NS.active) border = "1px solid var(--battman-teal-border)";
  else if (OVERRIDES.some((o) => (num(a[o.soc]) > 0 || num(a[o.price]) > 0) && isFalse(a[o.reset]))) border = "1px solid var(--battman-amber-border-soft)";
  else border = armName ? "1px solid var(--battman-blue-border)" : "1px solid var(--battman-border-neutral-soft)";

  return `<div class="strip" style="background:${bg};border:${border}">`
    + `<div class="strip-in"><div style="display:flex;align-items:center;gap:10px;min-width:0">`
    + `<div style="font-size:11px;font-weight:800;letter-spacing:0.14em;color:${lcolor};white-space:nowrap;flex:none">${label}</div>${armChip}${plugChip}</div>`
    + `${lockChip}${netRight}</div></div>`;
}

// ── one 60px override row ────────────────────────────────────────────────────────────────────
export function rowHtml(o, a, states, E) {
  const K = colours(o);
  const soc = num(a[o.soc]), price = num(a[o.price]);
  const on = isOn(o, a);
  const bg = on ? K.bg : `linear-gradient(${K.wash},${K.wash}), var(--battman-surface-card)`;
  const border = on ? K.dim : K.washBorder;
  const cur = parseFloat(states[E.soc] && states[E.soc].state);   // NaN when unavailable: shown as —, never 0%
  const isSpecial = o.specialAt > 0 && soc === o.specialAt;
  const locked = isFalse(a[o.reset]);
  const plug = o.id === "drain" && on && isTrue(a.drainBatteryPlughole);

  // the name of a saved preset that is exactly this row's value (and nothing else)
  let pname = "";
  for (const p of a.overridePresets || []) {
    const v = p.values || {};
    if (Object.keys(v).length === 1 && v[o.id] && num(v[o.id].soc) === soc && num(v[o.id].price) === price
      && ((v[o.id].allowReset === false) === locked)) { pname = p.name; break; }
  }

  const rem = o.dir === "up" ? soc - cur : cur - soc;
  const cap = states[E.capacity];
  const kwh = Math.abs(rem) * ((cap ? parseFloat(cap.state) : NaN) / 100);
  const live = on && soc > 0 && !isSpecial && rem > 0.5;
  const cost = (live && price > 0) ? kwh * price / 100 : 0;

  // the cost column steps down (or moves inline) as the preset name and SOC / PRICE take more width
  const nameW = (on && pname) ? pname.length * 7.5 : 0;
  let costFz = 24, costMw = 52, costInline = false;
  if (cost > 0) {
    if (nameW > 116) costInline = true;
    else if (nameW > 96) { costFz = 18; costMw = 44; }
    else if (nameW > 72) { costFz = 20; costMw = 48; }
  }
  if (cost > 0 && costFz === 24) {
    const wide = (soc >= 100 ? 1 : 0) + (price >= 10 ? 1 : 0);
    if (wide >= 2) { costFz = 18; costMw = 44; }
    else if (wide >= 1) { costFz = 20; costMw = 48; }
  }

  let l1 = "", l2 = "", l3 = "";
  const P = pname.toUpperCase();
  if (isSpecial) {
    if (pname && on) { l1 = `<span>${esc(P)}</span>`; l2 = `<span>${o.specialDesc}</span>`; }
    else l1 = `<span>${o.specialDesc}</span>`;
  } else if (pname && on) l1 = `<span>${esc(P)}</span>`;
  else if (!on) l1 = "<span>TAP TO SET</span>";
  if (plug) l1 = "<span>PLUGHOLE</span>";   // Plughole wins the label slot on the Drain row

  if (on && soc > 0 && !isSpecial) {
    if (live) {
      l2 = cur.toFixed(0) + "% → " + soc.toFixed(0) + "%";
      l3 = (isNaN(kwh) ? "—" : kwh.toFixed(1)) + " kWh";
    } else if (isNaN(cur)) {   // SOC unavailable: neither "target met" nor a made-up gap
      l2 = "—% → " + soc.toFixed(0) + "%";
      l3 = "— kWh";
    } else l2 = "target met";
  }
  if (costInline && l3) l3 += ` <span style="font-weight:800;opacity:1;letter-spacing:0.04em">· $${cost.toFixed(2)}</span>`;

  const vOp = on ? "1" : "0.5", tOp = on ? "1" : "0.75", nOp = on ? "1" : "0.55";
  const fmt = (v, u, d) => (v > 0 ? v.toFixed(d) + u : "—");
  const vcol = (label, val, mw, fz, op, pr = 8) =>
    `<div style="display:flex;flex-direction:column;min-width:${mw}px;flex:none;padding-right:${pr}px">`
    + `<span style="font-size:8px;font-weight:700;letter-spacing:0.1em;opacity:0.55;margin-bottom:3px">${label}</span>`
    + `<span style="height:23px;display:flex;align-items:center;${val === "—" ? "justify-content:center;" : ""}font-size:${fz}px;font-weight:900;line-height:1;white-space:nowrap;opacity:${op}">${val}</span></div>`;

  const moneyCol = (cost > 0 && !costInline) ? vcol(o.money, "$" + cost.toFixed(2), costMw, costFz, "1", 0) : "";
  const labelCol = `<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;width:64px;flex:none">`
    + (locked ? `<div style="line-height:0;margin-bottom:3px">${lockSvg(16, true)}</div>` : "")
    + `<div style="font-size:11px;font-weight:800;letter-spacing:0.06em;text-transform:uppercase;line-height:1.15;text-align:center;opacity:${tOp}">${o.label}</div></div>`;
  const priceTxt = (o.allowNegative && price < 0) ? price.toFixed(1) + "¢" : fmt(price, "¢", 1);

  return `<div class="row" data-id="${o.id}" style="background:${bg};border:${plug ? "1.5px solid " + K.c : "1px solid " + border};color:${K.c}">`
    + `<div style="display:flex;align-items:center;gap:8px;padding:0 12px 0 10px;height:100%">`
    + labelCol + vcol("SOC", fmt(soc, "%", 0), 50, 24, vOp) + vcol("PRICE", priceTxt, 54, 24, vOp) + moneyCol
    + `<div style="margin-left:auto;flex:0 1 auto;text-align:right;line-height:1.25;white-space:nowrap;min-width:0">`
    + (l1 ? `<div style="font-size:12px;font-weight:800;letter-spacing:0.04em;display:flex;align-items:center;gap:4px;justify-content:flex-end;opacity:${nOp}">${l1}</div>` : "")
    + (l2 ? `<div style="font-size:12px;font-weight:700;opacity:0.9">${l2}</div>` : "")
    + (l3 ? `<div style="font-size:12px;font-weight:700;opacity:0.9">${l3}</div>` : "")
    + `</div></div></div>`;
}
