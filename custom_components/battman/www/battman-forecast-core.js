// Battman forecast core: turning the forecast's slots (what script.battman_engine_forecast returns) into the rows
// shown. One copy, used by the "Next hours" forecast (battman-forecast-view.js) and by the Log card's Forecast /
// Both views (battman-log.js), so both group and word it exactly the same. Pure functions: no page access.

// ---- turning the forecast's slots into the rows shown (no page access in this block) ----
const c1 = x => (x * 100);
const d1 = x => { const r = Math.round(c1(x) * 10) / 10; return Number.isInteger(r) ? String(r) : r.toFixed(1); };
const hhmm = iso => String(iso).slice(11, 16);
const money = x => (x < 0 ? '−$' : '+$') + Math.abs(x).toFixed(2);
const sum = (a, f) => a.reduce((t, x) => t + f(x), 0);

function addMinutes(iso, mins) {
  // 'YYYY-MM-DDTHH:MM:SS+10:30' + minutes, as HH:MM (same offset, so only the clock part moves)
  const h = +iso.slice(11, 13), m = +iso.slice(14, 16);
  const t = (h * 60 + m + Math.round(mins)) % 1440;
  return String(Math.floor(t / 60)).padStart(2, '0') + ':' + String(t % 60).padStart(2, '0');
}

function kind(s) {
  // what the slot is, in the words the card uses
  const m = s.mode;
  if (m === 'Charge Solar Off') return 'hooover';
  if (m === 'Float Solar Off') return 'party';
  if (m === 'Charge') return 'buy';
  if (m === 'Discharge') return 'sell';
  if (m === 'Drain') return 'drain';
  if (m === 'Float') return 'float';
  return 'idle';
}

// v1's two "what would make Battman act" keys for a quiet slot:
//   bpk: the buy line (in whole cents), or 'P' when it is below the line but it is peak (no buying 5-9pm); null when the battery is not below the line
//   spk: the sell line (whole cents) when the battery is above the sell line, null otherwise
function bpk(s) {
  if (kind(s) !== 'idle' || !(s.soc_start < s.buy_below)) return null;
  return s.buy_reason === 'No Buy in Peak Tariff' ? 'P' : Math.round(c1(s.buy_line));
}
function spk(s) {
  return kind(s) === 'idle' && s.sell_price_known && s.soc_start > s.sell_above + 1 ? Math.round(c1(s.sell_line)) : null;
}
// two keys are "the same" when both are absent, both present and equal, or both numbers within 2c (v1's rule)
const near = (x, y) => (x === null) === (y === null) && (x === null || x === y || (typeof x === 'number' && typeof y === 'number' && Math.abs(x - y) < 2));
// the sell / buy "kind of reason" (v1 only split where this changed)
const sellCat = s => /^Solar/.test(s.sell_reason) ? 'solar' : (/Drain/.test(s.sell_reason) ? 'drain' : 'sell');
const buyCat = s => s.buy_reason === 'Anytime' ? 'anytime' : 'buy';

function group(slots) {
  // MASTERS: runs of the same kind of slot
  const S = slots.map((s, i) => Object.assign({}, s, { _end: i + 1 < slots.length ? hhmm(slots[i + 1].start) : addMinutes(s.start, s.minutes) }));
  const out = [];
  S.forEach(s => {
    const k = kind(s), last = out[out.length - 1];
    if (last && last.kind === k) last.slots.push(s); else out.push({ kind: k, slots: [s] });
  });
  out.forEach(m => { m.start = m.slots[0].live ? 'Now' : hhmm(m.slots[0].start); m.end = m.slots[m.slots.length - 1]._end; });
  return out;
}

function split(m) {
  // PARTS: v1's splitting of a master
  const parts = [];
  m.slots.forEach(s => {
    const p = parts[parts.length - 1];
    let same = false;
    if (p) {
      const f = p.slots[0];
      if (m.kind === 'idle') same = near(spk(s), p.spk) && near(bpk(s), p.bpk);
      else if (m.kind === 'buy' || m.kind === 'hooover') same = (s.buy_price < 0) === (f.buy_price < 0) && buyCat(s) === buyCat(f);
      else if (m.kind === 'sell' || m.kind === 'drain') same = sellCat(s) === sellCat(f);
      else same = true;
      // whatever the mode: a price move of 2c or more starts a new part (sell kinds follow the sell price, the rest the buy price)
      if (same && m.kind !== 'idle') {
        const px = x => c1(m.kind === 'sell' || m.kind === 'drain' ? x.sell_price : x.buy_price);
        if (Number.isFinite(px(s)) && Number.isFinite(px(f)) && Math.abs(px(s) - px(f)) >= 2) same = false;
      }
    }
    if (same) p.slots.push(s); else parts.push({ kind: m.kind, slots: [s], spk: spk(s), bpk: bpk(s) });
  });
  parts.forEach(p => { p.start = p.slots[0].live ? 'Now' : hhmm(p.slots[0].start); p.end = p.slots[p.slots.length - 1]._end; });
  return parts;
}

const rng = (vals) => { const lo = Math.min(...vals), hi = Math.max(...vals); return d1(lo) === d1(hi) ? d1(lo) : d1(lo) + '–' + d1(hi); };
const tag = (a, ruled, over) => a.some(s => s[ruled]) ? ' (' + (ruled === 'buy_ruled' ? 'buy' : 'sell') + ' rule)' : (a.some(s => s[over]) ? ' (override)' : '');

// "House 1.2 kW · solar 3.4 kW" for the slots of a row (a range when they differ)
function loadLine(a) {
  const range = v => { const lo = Math.min(...v), hi = Math.max(...v); return lo.toFixed(1) === hi.toFixed(1) ? lo.toFixed(1) : lo.toFixed(1) + '–' + hi.toFixed(1); };
  const L = a.map(s => s.load_kw).filter(Number.isFinite), P = a.map(s => s.pv_kw).filter(Number.isFinite);
  if (!L.length) return '';
  const kwh = f => { const v = sum(a, s => (Number.isFinite(s[f]) ? s[f] : 0) * s.minutes / 60); return v >= 10 ? v.toFixed(0) : v.toFixed(1); };
  const off = a.every(s => s.solar_off);   // the mode has the solar switched off: the figure is what is available, not what is used
  return `House ${range(L)} kW (${kwh('load_kw')} kWh)` + (P.length && Math.max(...P) > 0.05
    ? (off ? ` · solar switched off, ${range(P)} kW (${kwh('pv_kw')} kWh) available` : ` · solar ${range(P)} kW (${kwh('pv_kw')} kWh)`) : '');
}
// the orange line for solar that is sent to the grid (or held back because the price is negative)
function exportHint(a) {
  const kwh = sum(a, s => s.export_kwh);
  if (kwh >= 0.05) return ['var(--battman-orange)', `Exporting excess solar, ${kwh.toFixed(1)} kWh at ${d1(sum(a, s => s.export_kwh * s.sell_price) / kwh)}c`];
  if (a.some(s => s.curtail && s.pv_kw > 0.05)) return ['var(--battman-orange)', 'Solar curtailed: the export price is negative'];
  return null;
}

function describe(p) {
  // the words for a part or a whole master: { head, sub, hints:[[colour, text]], money, colour, ... }
  const a = p.slots, f = a[0], l = a[a.length - 1];
  const money$ = sum(a, x => x.money), batt = sum(a, x => x.battery_kwh);
  const avgBuy = sum(a, x => x.buy_price) / a.length, avgSell = sum(a, x => x.sell_price) / a.length;
  const soc = `battery ${Math.round(f.soc_start)}% → ${Math.round(l.soc_end)}%`;
  const kwhSold = sum(a, x => x.export_kwh).toFixed(1), kwhBought = sum(a, x => x.import_kwh).toFixed(1);
  const houseKwh = sum(a, x => (x.load_kw || 0) * x.minutes / 60);
  const kwh = Math.abs(batt).toFixed(1);   // the whole battery change (the house included): used for Drain only
  // a quiet row's colour (as the Chill card): orange when the grid is used, green when solar fills the battery, blue otherwise
  const holdCol = money$ < -0.005 ? 'var(--battman-orange)' : (l.soc_end > f.soc_start + 0.05 ? 'var(--battman-green)' : 'var(--battman-blue)');
  const o = { money: money$, color: holdCol, bg: '', chip: '', hints: [], act: p.kind !== 'idle', fx: p.kind === 'hooover' ? 'hooover' : (p.kind === 'party' ? 'houseparty' : '') };
  switch (p.kind) {
    case 'sell':
      Object.assign(o, { color: 'var(--battman-green)', head: `Sell ${kwhSold} kWh, ${soc}`,
        sub: /^Spike/.test(f.sell_reason) ? `Price spike: Amber pays ${d1(avgSell)}c (${f.sell_reason}).`
          : `Amber pays ${d1(avgSell)}c. BATTMAN sells at ${d1(f.sell_line)}c or more (${f.sell_reason}).` }); break;
    case 'buy':
      Object.assign(o, { color: 'var(--battman-yellow)', head: `Buy ${kwhBought} kWh, ${soc}`,
        sub: `${avgBuy < 0 ? 'Amber pays you ' + d1(-avgBuy) + 'c' : 'Amber charges ' + d1(avgBuy) + 'c'}. BATTMAN buys at ${d1(f.buy_line)}c or less (${f.buy_reason}).` }); break;
    case 'hooover':
      Object.assign(o, { color: 'var(--battman-purple)', chip: 'Hoooover', head: `Buy ${kwhBought} kWh, ${soc}`,
        sub: `Amber pays you ${d1(-avgBuy)}c to use power: charging to 100%, ignoring the curve.` }); break;
    case 'party':
      Object.assign(o, { color: 'var(--battman-purple)', chip: 'House Party', head: `Run the house off the grid, battery holds at ${Math.round(l.soc_end)}%`,
        sub: `Amber pays you ${d1(-avgBuy)}c to use power: holding the battery, no grid charge.` }); break;
    case 'drain':
      Object.assign(o, { color: 'var(--battman-red)', head: `Drain ${kwh} kWh, ${soc}`,
        sub: `Grid price is under the drain price (${f.sell_reason}); this moves charge, not dollars.` }); break;
    case 'float':
      Object.assign(o, { color: 'var(--battman-green)', head: `Hold the battery at ${Math.round(l.soc_end)}%`,
        sub: `Solar goes to the house and grid (${f.sell_reason}).` }); break;
    default: {
      o.head = `Do nothing, ${soc}`;
      // the Chill card's words for a quiet stretch
      o.sub = money$ < -0.005 ? 'Battery runs low, house uses the grid.' : (l.soc_end > f.soc_start ? 'Solar fills the battery.' : 'House runs off the battery.');
    }
  }
  if (p.kind === 'idle') {
    // v1's two hints under a quiet row
    if (p.bpk === 'P') o.hints.push(['var(--battman-yellow)', 'Below the buy line, but no buying in peak (5–9pm)']);
    else if (p.bpk !== null && p.bpk !== undefined) o.hints.push(['var(--battman-yellow)', `Buys if Amber charges ${d1(Math.max(...a.map(s => s.buy_line)))}c or less${tag(a, 'buy_ruled', 'buy_override')}`]);
    const sp = a.filter(s => spk(s) !== null);
    if (sp.length) o.hints.push(['var(--battman-orange)', `Sells if Amber pays ${d1(Math.min(...sp.map(s => s.sell_line)))}c or more${tag(sp, 'sell_ruled', 'sell_override')}`]);
  }
  o.load = loadLine(a);
  if (p.kind === 'sell' && houseKwh >= 0.05) o.load += ` · battery covers ${houseKwh.toFixed(1)} kWh of the house`;
  if (p.kind === 'idle' || p.kind === 'float') { const ex = exportHint(a); if (ex) o.hints.push(ex); }
  return o;
}

function summaryHints(parts) {
  // the master's one-line summary: the range of each hint across its parts
  const hints = [];
  const buys = parts.filter(p => p.bpk !== null && p.bpk !== 'P').map(p => Math.max(...p.slots.map(s => s.buy_line)));
  const sells = parts.filter(p => p.spk !== null).map(p => Math.min(...p.slots.filter(s => spk(s) !== null).map(s => s.sell_line)));
  if (parts.some(p => p.bpk === 'P')) hints.push(['var(--battman-yellow)', 'No buying in peak (5–9pm)']);
  if (buys.length) hints.push(['var(--battman-yellow)', `Buys if Amber charges ${rng(buys)}c or less`]);
  if (sells.length) hints.push(['var(--battman-orange)', `Sells if Amber pays ${rng(sells)}c or more`]);
  return hints;
}

export { group, split, describe, summaryHints, exportHint, money, hhmm, sum };
