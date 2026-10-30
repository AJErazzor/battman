// Battman mode history strip: the figures, kept apart from the card so they can be tested on their own.
// Used by battman-mode-history-strip.js.

// The pills: minutes back from now.
export const RANGES_MIN = [15, 30, 60, 120, 240, 480, 720, 1440];
export const DEFAULT_RANGE_MIN = 240;

export const rangeLabel = (min) => (min < 60 ? `${min}m` : `${min / 60}h`);

// Hours / minutes: "45s", "12m", "1h 05m".
export function durationText(ms) {
  const s = Math.max(0, Math.round(ms / 1000));
  if (s < 60) return `${s}s`;
  const m = Math.round(s / 60);
  if (m < 60) return `${m}m`;
  return `${Math.floor(m / 60)}h ${String(m % 60).padStart(2, "0")}m`;
}

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
