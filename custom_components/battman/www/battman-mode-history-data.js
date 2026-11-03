// Battman mode history strip: the figures, kept apart from the card so they can be tested on their own.
// Used by battman-mode-history-strip.js.

// The pills: minutes back from now.
export const RANGES_MIN = [15, 30, 60, 120, 240, 480, 720, 1440];
export const DEFAULT_RANGE_MIN = 240;

export const rangeLabel = (min) => (min < 60 ? `${min}m` : `${min / 60}h`);

// The mode blocks that fall in [t0, t1] from the mode entity's history (HA's history/period rows).
// Each block: { mode, start, end } clipped to the window, and { from, to } its real extent (the first
// block really began before the window; the last is still running, so its `to` is null).
// States that aren't a mode name (unknown, unavailable) are left out, so they show as a gap.
export function modeBlocks(rows, t0, t1) {
  const pts = (rows || [])
    .map((r) => ({ t: Date.parse(r.last_changed || r.last_updated), m: r.state }))
    .filter((p) => Number.isFinite(p.t))
    .sort((a, b) => a.t - b.t);
  const out = [];
  for (let i = 0; i < pts.length; i++) {
    const from = pts[i].t, to = i + 1 < pts.length ? pts[i + 1].t : null;
    const start = Math.max(t0, from), end = Math.min(t1, to === null ? t1 : to);
    if (end <= start) continue;
    if (!pts[i].m || pts[i].m === "unknown" || pts[i].m === "unavailable") continue;
    out.push({ mode: pts[i].m, start, end, from, to });
  }
  return out;
}

// The block under time t, or null.
export function blockAt(blocks, t) {
  return blocks.find((b) => t >= b.start && t < b.end) || (blocks.length && t >= blocks[blocks.length - 1].end ? blocks[blocks.length - 1] : null);
}

// Where the time labels go along the strip: whole steps of the clock, as fractions of the window.
export function tickTimes(t0, t1, offsetMs) {
  const span = t1 - t0;
  const steps = [5, 10, 15, 30, 60, 120, 180, 240, 360].map((m) => m * 60000);
  const step = steps.find((s) => span / s <= 6) || steps[steps.length - 1];
  const out = [];
  for (let t = Math.ceil((t0 + offsetMs) / step) * step - offsetMs; t <= t1; t += step) out.push(t);
  return out;
}

// ---- the engine log's figures at a point in time (the Log page and the strip show the same ones) ----
// A log line is "<YYYY-MM-DD HH:MM:SS>|<message>". The 5-minute price sensors aren't kept in the
// recorder, so buy / sell price and SOC come from the engine log: the line nearest to t, either side.
// stampMs turns the line's time text into ms (default: the browser's own time zone).
export function nearestLogLine(lines, t, stampMs = Date.parse) {
  let best = null, bestDiff = Infinity;
  for (const l of lines || []) {
    const p = l.indexOf("|");
    if (p < 0) continue;
    const tt = stampMs(l.slice(0, p));
    if (!Number.isFinite(tt)) continue;
    const diff = Math.abs(tt - t);
    if (diff < bestDiff) { bestDiff = diff; best = { line: l, at: tt }; }
  }
  return best;
}

// { at, soc, buy, sell } at t: at = the nearest line's time, the figures null where the line has none.
// Buy / sell are $/kWh as the engine logs them ("Current:").
export function logValuesAt(lines, t, stampMs = Date.parse) {
  const n = nearestLogLine(lines, t, stampMs);
  if (!n) return { at: null, soc: null, buy: null, sell: null };
  const pick = (re) => { const m = n.line.match(re); return m ? parseFloat(m[1]) : null; };
  return {
    at: n.at,
    soc: pick(/Battery:\s*(-?[\d.]+)%/),
    buy: pick(/Buy:\s*\$[^()]*\(Current:\s*\$(-?[\d.]+)\)/),
    sell: pick(/Sell:\s*\$[^()]*\(Current:\s*\$(-?[\d.]+)\)/),
  };
}

export const centsText = (v) => (v === null || v === undefined ? "—" : (v * 100).toFixed(1) + "c");
export const percentText = (v) => (v === null || v === undefined ? "—" : v.toFixed(1) + "%");

// How long a mode block runs, as the Log page says it: "12 min", "30 min+" (it began before the window),
// "5 min so far" (still running; `now` is the window's end).
export function modeLengthText(from, to, now, windowStart) {
  if (to === null || to === undefined) return Math.max(0, Math.round((now - from) / 60000)) + " min so far";
  return Math.max(1, Math.round((to - from) / 60000)) + " min" + (from <= windowStart ? "+" : "");
}
