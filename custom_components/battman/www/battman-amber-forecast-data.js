// Battman Amber forecast chart's figures (battman-amber-forecast-chart.js), kept apart from the card so
// they can be checked without a browser.
//
// Amber's two forecast sensors (amber2mqtt) carry a Forecasts list: one entry per billing interval
// with start_time, end_time (or duration, minutes), per_kwh ($/kWh) and Amber Advanced's
// low / predicted / high, nested (advanced_price.low) or flat (advanced_price_low).
//
// Feed-in prices are negative when you're paid, so Sell is shown negated (positive = earning), as the
// engine does. Negating swaps the band's ends: Sell High is the raw low, Sell Low the raw high, so
// High is always the upper line. Prices are shown in c/kWh. A missing figure is a gap, never 0.

export const SERIES = [
  { id: "buy", label: "Buy Price", side: "buy", field: "per_kwh" },
  { id: "buy_predicted", label: "Buy Predicted", side: "buy", field: "predicted" },
  { id: "buy_low", label: "Buy Low", side: "buy", field: "low" },
  { id: "buy_high", label: "Buy High", side: "buy", field: "high" },
  { id: "sell", label: "Sell Price", side: "sell", field: "per_kwh" },
  { id: "sell_predicted", label: "Sell Predicted", side: "sell", field: "predicted" },
  { id: "sell_low", label: "Sell Low", side: "sell", field: "high" },     // negated: raw high is the lower line
  { id: "sell_high", label: "Sell High", side: "sell", field: "low" },
];

// hours ahead: 15m, 30m, 1h, 2h, 4h, 8h, 12h, 24h
export const RANGES_H = [0.25, 0.5, 1, 2, 4, 8, 12, 24];
const STEP_MS = 5 * 60 * 1000;   // the chart has a point at least every 5 minutes, so the tooltip is always inside the right interval

function num(x) {
  if (x === null || x === undefined || x === "") return null;
  const n = Number(x);
  return isFinite(n) ? n : null;
}

// One forecast entry's figure ($/kWh as Amber gives it), or null.
export function amberValue(f, field) {
  if (!f) return null;
  if (field === "per_kwh") return num(f.per_kwh);
  const ap = f.advanced_price;
  if (ap && typeof ap === "object" && ap[field] !== undefined && ap[field] !== null) return num(ap[field]);
  return num(f["advanced_price_" + field]);
}

// Amber's intervals start a second past the boundary (17:30:01 to 18:00:00): on the whole minute, so
// one interval ends where the next starts and the line has no gap between them.
const toMinute = (ms) => isNaN(ms) ? ms : Math.floor(ms / 60000) * 60000;

// Forecasts list -> [{ s, e, f }] (ms), in time order. An entry with no usable start is skipped; one with
// no end_time or duration ends where the next one starts (the last such entry is dropped).
export function intervals(forecasts) {
  const list = (Array.isArray(forecasts) ? forecasts : [])
    .map((f) => ({ f, s: toMinute(Date.parse(f && f.start_time)) }))
    .filter((x) => !isNaN(x.s))
    .sort((a, b) => a.s - b.s);
  const out = [];
  list.forEach((x, i) => {
    let e = toMinute(Date.parse(x.f.end_time));
    if (isNaN(e) && num(x.f.duration) !== null) e = x.s + num(x.f.duration) * 60000;
    if (isNaN(e) && list[i + 1]) e = list[i + 1].s;
    if (!isNaN(e) && e > x.s) out.push({ s: x.s, e, f: x.f });
  });
  return out;
}

// The interval covering t (start <= t < end); for the line's last point, the one ending at t.
export function covering(iv, t, last) {
  for (const x of iv) if (x.s <= t && t < x.e) return x;
  if (last) for (const x of iv) if (x.s < t && t <= x.e) return x;
  return null;
}

// The chart's points over [fromMs, toMs]: every interval edge plus a 5-minute grid, and each series'
// value (c/kWh) at each, as the interval covering it says. -> { times, data: { id: [..] }, buyIv, sellIv }
// current: { buy, sell } ($/kWh, Sell already positive = earning, as Amber's current-price sensors give
// them): the Price lines from now until each side's first forecast (the interval under way isn't in
// the forecasts). Predicted / Low / High have nothing there.
export function forecastSeries(buyForecasts, sellForecasts, fromMs, toMs, current) {
  const buyIv = intervals(buyForecasts), sellIv = intervals(sellForecasts);
  const set = new Set([fromMs, toMs]);
  for (let t = Math.ceil(fromMs / STEP_MS) * STEP_MS; t < toMs; t += STEP_MS) set.add(t);
  for (const x of buyIv.concat(sellIv)) {
    if (x.s > fromMs && x.s < toMs) set.add(x.s);
    if (x.e > fromMs && x.e < toMs) set.add(x.e);
  }
  const times = [...set].sort((a, b) => a - b);
  // the line runs only as far as there are forecasts
  const lastEnd = Math.max(0, ...buyIv.concat(sellIv).map((x) => x.e));
  const data = {};
  for (const sd of SERIES) {
    const iv = sd.side === "buy" ? buyIv : sellIv;
    const firstStart = iv.length ? iv[0].s : Infinity;
    const now = current && sd.field === "per_kwh" ? num(current[sd.side]) : null;
    data[sd.id] = times.map((t, i) => {
      if (t < firstStart) return now === null ? null : Math.round(now * 100 * 10000) / 10000;
      if (t > lastEnd) return null;
      const x = covering(iv, t, i === times.length - 1 || t === lastEnd);
      const v = x ? amberValue(x.f, sd.field) : null;
      if (v === null) return null;
      return Math.round((sd.side === "sell" ? -v : v) * 100 * 10000) / 10000;
    });
  }
  return { times, data, buyIv, sellIv };
}
