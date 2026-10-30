// Battman Mode history strip: custom:battman-mode-history-strip. The battery mode over the last 15
// minutes to 24 hours as one coloured strip, for when you want the Log page's mode timeline on its own.
// Pills pick the range (kept per device); tap or drag along the strip for the mode at that point (a red
// line marks it) with when it started and how long it ran. Always ends at now; redraws when the mode
// changes and once a minute. The mode entity comes from Battman's entity map, the colours from
// BattmanLib.modeHues (the same colours as the Log, the Battery mode buttons and the Live Activity).

import { BattmanCardBase, battmanDefine, battmanMap, battmanPicker, cssVar, esc, inCardPicker } from "./battman-card-base.js";
import { DEFAULT_RANGE_MIN, RANGES_MIN, blockAt, durationText, modeBlocks, rangeLabel, tickTimes } from "./battman-mode-history-data.js";

const SAVE_KEY = "battman.modeHistoryStrip";

class BattmanModeHistoryStripCard extends BattmanCardBase {
  static cardName = "Battman Mode history strip";
  static gridOptions = { columns: "full", rows: "auto" };
  static css = `
    :host { display: block; }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    button { font-family: inherit; }
    ha-card { overflow: hidden; background: var(--card-background-color); border: 1px solid var(--divider-color);
      border-radius: 12px; color: var(--primary-text-color); box-shadow: none; font-size: 16px; line-height: normal;
      font-family: var(--primary-font-family, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif); }
    .head { display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; justify-content: space-between;
      padding: 10px 16px; border-bottom: 1px solid var(--divider-color); }
    .title { font-size: 13px; font-weight: 700; letter-spacing: 0.09em; text-transform: uppercase; }
    .pills { display: flex; flex-wrap: wrap; gap: 6px; }
    .pill { padding: 5px 10px; border: 1px solid var(--divider-color); border-radius: 999px; background: transparent;
      color: var(--secondary-text-color); font: inherit; font-size: 12px; font-weight: 600; line-height: 1; cursor: pointer;
      -webkit-tap-highlight-color: transparent; transition: background .12s ease, border-color .12s ease, color .12s ease; }
    .pill:hover { color: var(--primary-text-color); }
    .pill.active { background: var(--primary-color); border-color: var(--primary-color); color: #fff; }
    .body { padding: 14px 16px 12px; }
    .bar { position: relative; display: flex; height: 30px; border: 1px solid var(--divider-color); border-radius: 6px;
      overflow: hidden; background: var(--secondary-background-color, transparent); touch-action: pan-y; cursor: crosshair; }
    .seg { height: 100%; }
    .mark { position: absolute; top: -1px; bottom: -1px; width: 2px; margin-left: -1px; background: #ff3b30;
      box-shadow: 0 0 0 1px rgba(255,255,255,.55); opacity: 0; pointer-events: none; }
    .ticks { position: relative; height: 14px; margin-top: 5px; font-size: 10px; color: var(--secondary-text-color);
      font-variant-numeric: tabular-nums; }
    .ticks span { position: absolute; transform: translateX(-50%); white-space: nowrap; }
    .read { margin-top: 8px; min-height: 20px; font-size: 13px; display: flex; flex-wrap: wrap; align-items: center; gap: 4px 8px; }
    .read .dot { width: 10px; height: 10px; border-radius: 2px; flex: none; }
    .read b { font-weight: 700; }
    .read .hint, .read .sub { color: var(--secondary-text-color); }
    .legend { display: flex; flex-wrap: wrap; gap: 5px 12px; margin-top: 8px; font-size: 11px; color: var(--secondary-text-color); }
    .legend .li { display: flex; align-items: center; gap: 5px; }
    .legend .dot { width: 10px; height: 10px; border-radius: 2px; flex: none; }
    .msg { padding: 22px 16px; text-align: center; color: var(--secondary-text-color); font-size: 14px; }
  `;
  static html = `<ha-card><div class="head"><span class="title" id="t">Mode history</span><div class="pills" id="p"></div></div><div class="body" id="b"><div class="msg">Loading…</div></div></ha-card>`;

  // HA's Add card list: a small drawing of the card (no picture file to ship)
  _build() {
    if (!this._hass || !this.isConnected || this._built) return;
    if (!inCardPicker(this)) return super._build();
    this._built = true;
    const seg = (w, c) => `<div style="width:${w}%;background:${c}"></div>`;
    this.shadowRoot.innerHTML = `<ha-card style="overflow:hidden;padding:0 14px 12px;font-family:var(--primary-font-family,sans-serif)">`
      + `<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0"><b style="font-size:12px;letter-spacing:.09em">MODE HISTORY</b>`
      + `<span style="font-size:11px;color:var(--secondary-text-color)">1h &nbsp; 4h &nbsp; 12h</span></div>`
      + `<div style="display:flex;height:28px;border-radius:6px;overflow:hidden">${seg(26, "#3b82f6")}${seg(14, "#22c55e")}${seg(30, "#eab308")}${seg(10, "#ef4444")}${seg(20, "#3b82f6")}</div></ha-card>`;
  }

  run(root) {
    const card = this;
    const $ = (id) => root.getElementById(id);
    let rangeMin = DEFAULT_RANGE_MIN, modeId = null, FATAL = null, rows = null, fetchedAt = 0, busy = false, timer = null;
    let blocks = [], win = { t0: 0, t1: 0 }, modeColor = {}, fmtHM = null, fmtDay = null, seq = 0;

    try { const s = JSON.parse(localStorage.getItem(SAVE_KEY)); if (s && RANGES_MIN.includes(s.range)) rangeMin = s.range; } catch (e) {}
    const save = () => { try { localStorage.setItem(SAVE_KEY, JSON.stringify({ range: rangeMin })); } catch (e) {} };

    // ---- start-up checks: the entity map, Battman's mode colours, the clock ----
    async function init() {
      const L = window.BattmanLib;
      if (!L || !L.modeHues) return (FATAL = "Battman's card library (battman-lib.js) isn't loaded on this HA page, so the mode colours aren't known. Refresh the page.");
      try { modeId = (await battmanMap(card.hass, ["mode"])).mode; } catch (e) { return (FATAL = e.message); }
      if (!card.hass.states[modeId]) return (FATAL = "Entity not found: mode → " + modeId);
      const tz = card.hass.config && card.hass.config.time_zone;
      if (!tz) return (FATAL = "Home Assistant has no time zone set (Settings → System → General).");
      fmtHM = new Intl.DateTimeFormat([], { timeZone: tz, hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
      fmtDay = new Intl.DateTimeFormat([], { timeZone: tz, weekday: "short" });
      return colours();
    }
    function colours() {
      const L = window.BattmanLib, hex = {};
      try {
        for (const hue of L.PALETTE) hex[hue] = L.cssHex(cssVar(card, "--battman-" + hue));
        const hues = L.modeHues(hex);
        modeColor = {};
        for (const m of L.MODES) modeColor[m] = hex[hues[m]];
        return (FATAL = null);
      } catch (e) { return (FATAL = "Battman mode colours: " + e.message + " (this view needs a Battman theme)."); }
    }
    const tzOffset = (ms) => {
      const p = {};
      new Intl.DateTimeFormat("en-US", { timeZone: card.hass.config.time_zone, hourCycle: "h23", year: "numeric", month: "2-digit", day: "2-digit",
        hour: "2-digit", minute: "2-digit", second: "2-digit" }).formatToParts(ms).forEach((x) => { p[x.type] = x.value; });
      return Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour, +p.minute, +p.second) - Math.floor(ms / 1000) * 1000;
    };
    const clock = (ms) => fmtHM.format(ms);
    const clockDay = (ms) => (Date.now() - ms > 20 * 3600000 ? fmtDay.format(ms) + " " : "") + clock(ms);

    function pills() {
      $("p").innerHTML = RANGES_MIN.map((m) => `<button class="pill${m === rangeMin ? " active" : ""}" data-m="${m}">${rangeLabel(m)}</button>`).join("");
    }

    // ---- history: the mode entity from (now - range) to now ----
    async function load() {
      if (FATAL || busy) return;
      busy = true;
      const my = ++seq, t1 = Date.now(), t0 = t1 - rangeMin * 60000;
      try {
        const r = await card.hass.callApi("GET", `history/period/${new Date(t0).toISOString()}?filter_entity_id=${modeId}&end_time=${new Date(t1).toISOString()}&minimal_response&no_attributes`);
        if (my === seq) { rows = (r && r[0]) || []; fetchedAt = Date.now(); win = { t0, t1 }; }
      } catch (e) { if (my === seq) rows = null; }
      busy = false;
      if (my !== seq) return load();   // the range changed while this was loading
      draw();
    }

    function draw() {
      if (FATAL) { $("b").innerHTML = `<div class="msg">${esc(FATAL)}</div>`; return; }
      $("t").textContent = `Mode history · last ${rangeLabel(rangeMin)}`;
      if (rows === null) { $("b").innerHTML = `<div class="msg">History unavailable</div>`; return; }
      const { t0, t1 } = win, span = Math.max(1, t1 - t0);
      blocks = modeBlocks(rows, t0, t1);
      if (!blocks.length) { $("b").innerHTML = `<div class="msg">No mode history in this window</div>`; return; }
      const seen = [];
      const bar = blocks.map((b) => {
        if (!seen.includes(b.mode)) seen.push(b.mode);
        return `<div class="seg" style="width:${(((b.end - b.start) / span) * 100).toFixed(3)}%;background:${modeColor[b.mode] || "var(--primary-color)"}" title="${esc(b.mode)}"></div>`;
      }).join("");
      const ticks = tickTimes(t0, t1, tzOffset(t1)).map((t) => `<span style="left:${(((t - t0) / span) * 100).toFixed(2)}%">${clock(t)}</span>`).join("");
      const legend = seen.map((m) => `<span class="li"><span class="dot" style="background:${modeColor[m] || "var(--primary-color)"}"></span>${esc(m)}</span>`).join("");
      $("b").innerHTML = `<div class="bar" id="bar">${bar}<div class="mark" id="mark"></div></div><div class="ticks">${ticks}</div>`
        + `<div class="read" id="read"><span class="hint">Tap the strip for the mode at a point</span></div><div class="legend">${legend}</div>`;
    }

    // ---- tap / drag: the mode at that point, a red line on the strip ----
    function scrub(e) {
      const bar = $("bar"); if (!bar || !blocks.length) return;
      const r = bar.getBoundingClientRect();
      const f = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width));
      const t = win.t0 + f * (win.t1 - win.t0), b = blockAt(blocks, t);
      const mark = $("mark"); mark.style.left = (f * 100).toFixed(2) + "%"; mark.style.opacity = "1";
      if (!b) return;
      const running = b.to === null;
      const len = (running ? Date.now() : b.to) - b.from;
      $("read").innerHTML = `<span class="dot" style="background:${modeColor[b.mode] || "var(--primary-color)"}"></span><b>${esc(b.mode)}</b>`
        + `<span class="sub">from ${clockDay(b.from)}${running ? "" : " to " + clock(b.to)} · ${durationText(len)}${running ? " so far" : ""}</span>`;
    }
    let dragging = false;
    root.addEventListener("pointerdown", (e) => { if (e.target.closest && e.target.closest("#bar")) { dragging = true; scrub(e); } });
    root.addEventListener("pointermove", (e) => { if (dragging) scrub(e); });
    root.addEventListener("pointerup", () => { dragging = false; });
    root.addEventListener("pointercancel", () => { dragging = false; });
    root.addEventListener("click", (e) => {
      const p = e.target.closest && e.target.closest(".pill");
      if (!p) return;
      rangeMin = Number(p.dataset.m); save(); pills(); seq++; load();
    });

    const start = async () => { pills(); await init(); if (FATAL) draw(); else load(); timer = setInterval(() => { if (!FATAL) load(); }, 60000); };
    start();
    return {
      pause: () => { clearInterval(timer); timer = null; },
      resume: () => { if (!timer) { timer = setInterval(() => { if (!FATAL) load(); }, 60000); if (!FATAL && Date.now() - fetchedAt > 30000) load(); } },
      hassChanged: (old) => { if (!FATAL && modeId && old && old.states[modeId] !== card.hass.states[modeId]) load(); },
      themeChanged: () => { if (!FATAL || modeId !== null) { colours(); if (!FATAL && rows) draw(); } },
    };
  }
}
battmanDefine("battman-mode-history-strip", BattmanModeHistoryStripCard);
battmanPicker("battman-mode-history-strip", "Battman Mode history strip",
  "The battery mode over the last 15 minutes to 24 hours as one coloured strip; tap it for the mode at a point.",
  "battman-mode-history-strip");
