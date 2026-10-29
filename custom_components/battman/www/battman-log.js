// Battman Log: custom:battman-log. The engine log (each run's decisions) with the mode timeline and
// price, power, grid, battery and solar charts over the same window. A real card (it used to be the
// Log page, /battmanfiles/log.html, in a frame): HA hands it its connection and theme directly.
//
//   type: custom:battman-log
//
// Same as the Log page it replaces: the Filter Log controls (quick ranges, ‹ › pager, From / To),
// the Log (collapsed to start; mode and Changes Only filters), the Mode timeline (tap a point to
// see it and to limit the log to that 5-minute block; drag to scrub) and the chart panels, which
// you drag into your own order by their grip (kept per device).
//
// Live: when the engine logs a run, the log reloads; on a quick range (4h, 1h, ...) the window moves
// on to now, keeping your filters. The charts also refresh every minute.
//
// Entities come from Battman's entity map, colours from the Battman theme, the mode colours from
// BattmanLib.modeHues (battman-lib.js). Anything missing is shown on the card, never made up.
// The charts use Chart.js, shipped with Battman (/battmanfiles/vendor/).
// ---------------------------------------------------------------------------------------------

import { AMBER, BATTMAN_SENSORS, BattmanCardBase, FILES, SIGEN, battmanDefine, battmanMap, battmanPicker, cssVar, loadChartJs, missingEntities, missingThemeVars } from "./battman-card-base.js";

const LOG_EVENT = "battman_engine_log";

const LOG_CSS = `
  :host {
    display: block;
    --ha-bg:     var(--battman-surface-popup);
    --ha-card:   var(--battman-surface-card);
    --ha-text:   var(--primary-text-color);
    --ha-muted:  var(--secondary-text-color);
    --ha-border: var(--divider-color);
    --ha-accent: var(--primary-color);
    --chip:      var(--battman-blue);
    --chip-brd:  var(--battman-blue-border);
    --chip-bg:   var(--battman-surface-card);
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }
  ha-card { overflow: hidden; container-type: inline-size; }
  input, textarea, select, button { font-family: inherit; }
  .page {
    background: var(--ha-bg);
    color: var(--ha-text);
    font-family: var(--primary-font-family, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif);
    font-size: 15px;
    line-height: 1.5;
    padding: 20px;
  }
  .wrap { max-width: 1400px; margin: 0 auto; display: flex; flex-direction: column; gap: 14px; }

  .hdr h1 { font-size: 20px; font-weight: 700; letter-spacing: -0.3px; display: flex; align-items: center; gap: 10px; margin: 0; }
  .hdr .who { height: 56px; width: auto; flex: none; }
  .hdr .word { height: 30px; width: auto; max-width: 100%; min-width: 0; flex: 0 1 auto; }
  @container (max-width: 600px) { .hdr h1 { font-size: 18px; } }

  .card {
    background: var(--ha-card);
    border: 1px solid var(--ha-border);
    border-radius: 12px;
    padding: 14px 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.18);
  }
  .card > .title {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--ha-muted);
    margin-bottom: 12px;
  }

  /* --- quick-range chips (styled after the Power override panel) --- */
  .chips { display: flex; flex-wrap: wrap; }
  .chip {
    height: 30px;
    display: inline-flex;
    align-items: center;
    padding: 0 12px;
    border-radius: 6px;
    background: var(--chip-bg);
    border: 1px solid var(--battman-border-neutral);
    color: var(--chip);
    cursor: pointer;
    font-size: 12px;
    font-weight: 800;
    margin: 0 6px 6px 0;
    transition: background .12s ease, border-color .12s ease, transform .1s ease;
    user-select: none;
  }
  .chip:active { transform: scale(0.94); }
  /* selected = ghost wash + colour border (not a flat full fill) */
  .chip.active { background: color-mix(in srgb, var(--chip) 18%, transparent); border-color: var(--chip); color: var(--chip); }
  .pager { display: flex; align-items: center; gap: 12px; margin: 8px 0 2px; }
  .chip.pgr { min-width: 40px; justify-content: center; font-size: 18px; font-weight: 800; padding: 0 10px; }
  .chip.disabled { opacity: 0.35; pointer-events: none; }
  .pgrspan { font-size: 12px; color: var(--ha-muted); font-variant-numeric: tabular-nums; }
  .live { font-size: 12px; color: var(--ha-muted); margin-top: 6px; }

  /* --- always-visible range editor (From/To value + Set button) --- */
  .rangeEditor {
    margin-top: 12px;
    padding: 12px;
    border: 1px solid var(--ha-border);
    border-radius: 10px;
    background: var(--ha-bg);
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .editWrap { position: relative; display: inline-flex; }
  .overlayPicker {
    position: absolute; inset: 0; width: 100%; height: 100%;
    margin: 0; padding: 0; border: 0; opacity: 0; cursor: pointer; color-scheme: dark;
  }
  .crow { display: flex; align-items: center; gap: 10px; }
  .crow .clabel { font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--ha-muted); width: 42px; }
  .crow .cval { flex: 1; font-size: 14px; font-variant-numeric: tabular-nums; }
  /* ghost-wash buttons, matching the Curvy action buttons */
  button.btn {
    --c: var(--battman-blue);
    --c-fill: var(--battman-blue-soft-bg);
    background: var(--c-fill);
    color: var(--c);
    border: 1px solid var(--battman-border-neutral);
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    font-family: inherit;
    transition: background 0.12s ease, border-color 0.12s ease, transform 0.08s ease;
  }
  button.btn.small { padding: 6px 12px; font-size: 12px; }
  @media (hover: hover) { button.btn:hover { border-color: var(--c); } }
  button.btn:active { background: color-mix(in srgb, var(--c) 32%, transparent); border-color: var(--c); transform: scale(0.96); }
  .hiddenPicker { position: absolute; width: 1px; height: 1px; opacity: 0; pointer-events: none; left: -9999px; }

  /* --- filters --- */
  .filters { display: flex; flex-wrap: wrap; gap: 6px 16px; align-items: center; }
  .filters label {
    color: var(--ha-text); font-size: 13px; cursor: pointer;
    display: flex; align-items: center; gap: 5px; user-select: none;
  }
  .filters label.heading { color: var(--ha-muted); font-size: 12px; cursor: default; margin-right: 2px; }
  .filters input[type="checkbox"] { accent-color: var(--mode-accent, var(--ha-accent)); width: 15px; height: 15px; cursor: pointer; }
  .divider { width: 1px; height: 20px; background: var(--ha-border); margin: 0 4px; }

  /* --- log --- */
  .logHead { display: flex; align-items: center; justify-content: space-between; cursor: pointer; user-select: none; margin-bottom: 0; }
  .logHead .chev { transition: transform .15s ease; color: var(--ha-muted); font-size: 22px; line-height: 1; }
  .logBody { margin-top: 12px; }
  #logCard.collapsed .logBody { display: none; }
  #logCard.collapsed .chev { transform: rotate(-90deg); }
  #log { display: flex; flex-direction: column; gap: 8px; }
  .entry { background: var(--ha-bg); border-radius: 8px; padding: 10px 14px; border-left: 3px solid var(--ha-accent); }
  .empty { color: var(--ha-muted); text-align: center; padding: 40px 20px; font-size: 16px; }
  .count { color: var(--ha-muted); font-size: 13px; text-align: right; padding-bottom: 6px; border-bottom: 1px solid var(--ha-border); margin-bottom: 4px; }

  /* --- history --- */
  .chartWrap { position: relative; height: 170px; touch-action: pan-y; }
  .chart-empty { color: var(--ha-muted); text-align: center; padding: 24px; font-size: 14px; }
  /* mode state-timeline strip */
  .mbar { display: flex; height: 26px; border: 1px solid var(--ha-border); border-radius: 6px; overflow: hidden; background: var(--ha-bg); touch-action: none; position: relative; }
  .mseg { height: 100%; }
  /* tap/scrub marker — a red line showing the selected point on the timeline */
  .mmark { position: absolute; top: -1px; bottom: -1px; width: 2px; margin-left: -1px; background: #ff3b30;
           box-shadow: 0 0 0 1px rgba(255,255,255,0.55); opacity: 0; pointer-events: none; transition: opacity .1s ease; }
  .mreadout { margin-top: 8px; min-height: 18px; font-size: 12px; color: var(--ha-text); display: flex; flex-wrap: wrap; align-items: center; gap: 6px 8px; }
  .mreadout b { color: var(--ha-text); font-weight: 700; }
  .mreadout .dot { width: 10px; height: 10px; border-radius: 2px; flex: none; }
  .mreadout .hint { color: var(--ha-muted); }
  .mreadout .ro-dur { color: var(--ha-text); font-weight: 700; font-variant-numeric: tabular-nums; }
  .mreadout .ro-extra { color: var(--ha-muted); font-variant-numeric: tabular-nums; }
  .mticks { position: relative; height: 13px; margin-top: 4px; font-size: 10px; color: var(--ha-muted); font-variant-numeric: tabular-nums; }
  .mticks span { position: absolute; transform: translateX(-50%); white-space: nowrap; }
  .mlegend { display: flex; flex-wrap: wrap; gap: 5px 12px; margin-top: 8px; font-size: 11px; color: var(--ha-muted); }
  .mlegend .li { display: flex; align-items: center; gap: 5px; }
  .mlegend .dot { width: 10px; height: 10px; border-radius: 2px; flex: none; }

  /* --- drag-to-reorder blocks --- */
  .reorder { display: flex; flex-direction: column; gap: 14px; position: relative; }
  /* synced scrubber guide — a thin 1px line inside each chart's plot area only */
  .cline { position: absolute; width: 1px; margin-left: -0.5px; background: #ff3b30;
    box-shadow: 0 0 0 0.5px rgba(0,0,0,0.25); opacity: 0; pointer-events: none;
    z-index: 3; transition: opacity .1s ease; }
  .cardHead { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  .logLeft { display: flex; align-items: center; gap: 8px; }
  /* the usual six-dot grip, drawn in CSS (2 cols x 3 rows) — no image asset */
  .grip {
    width: 12px; height: 18px; flex: none; align-self: center;
    color: var(--ha-muted); opacity: 0.7; cursor: grab; touch-action: none;
    background-image: radial-gradient(circle at center, currentColor 1.3px, transparent 1.7px);
    background-size: 6px 6px; background-position: 0 0; background-repeat: repeat;
  }
  .grip:hover { opacity: 1; }
  .grip:active { cursor: grabbing; }
  .reCard.dragging { box-shadow: 0 10px 30px rgba(0,0,0,0.45); opacity: 0.97; }
  .re-placeholder { border: 2px dashed var(--ha-border); border-radius: 12px;
    background: color-mix(in srgb, var(--ha-accent) 7%, transparent); }

`;

const LOG_HTML = `<ha-card><div class="page">
<label class="hiddenPicker" aria-hidden="true"><input type="checkbox" switch id="hapticSwitch"></label>
<div class="wrap">

  <div class="hdr"><h1><img class="who" src="${FILES}/images/battman-toilet-mirror.webp" alt="Battman"><img class="word" src="${FILES}/images/logs-line.webp" alt="Logs"></h1></div>

  <!-- Reorderable stack: Filter Log + Log + Mode + chart panels (drag the grip; order saved per-device) -->
  <div class="reorder" id="reorder">

    <!-- Filter Log controls -->
    <div class="card reCard" id="controlsCard" data-block="controls">
      <div class="title cardHead"><span>Filter Log</span><span class="grip" data-grip></span></div>
      <div class="chips" id="rangeChips"></div>
      <div class="pager">
        <button class="chip pgr" id="pagePrev" aria-label="Previous window">‹</button>
        <span class="pgrspan" id="pgrSpan"></span>
        <button class="chip pgr" id="pageNext" aria-label="Next window">›</button>
      </div>
      <div class="rangeEditor">
        <div class="crow">
          <span class="clabel">From</span>
          <span class="cval" id="fromLabel">—</span>
          <span class="editWrap"><button class="btn small">Set</button><input type="datetime-local" id="fromDt" step="300" class="overlayPicker"></span>
        </div>
        <div class="crow">
          <span class="clabel">To</span>
          <span class="cval" id="toLabel">—</span>
          <span class="editWrap"><button class="btn small">Set</button><input type="datetime-local" id="toDt" step="300" class="overlayPicker"></span>
        </div>
      </div>
      <div class="live" id="liveNote" hidden></div>
    </div>

    <!-- Log -->
    <div class="card reCard collapsed" id="logCard" data-block="log">
      <div class="title logHead" id="logToggle">
        <span class="logLeft"><span class="chev">▾</span><span>Log</span></span>
        <span class="grip" data-grip></span>
      </div>
      <div class="logBody" id="logBody">
        <div class="filters" id="filters"></div>
        <div id="log"><div class="empty">Loading&hellip;</div></div>
      </div>
    </div>

    <!-- Mode -->
    <div class="card reCard" id="modeCard" data-block="mode">
      <div class="title cardHead"><span>Mode</span><span class="grip" data-grip></span></div>
      <div id="modeStrip"><div class="chart-empty">Loading&hellip;</div></div>
    </div>

    <!-- chart panel cards are added here -->
  </div>

</div>
</div></ha-card>`;

// The Log itself: everything the card draws and does, on its shadow root. Returns
// { resume, pause, themeChanged } for the card to call.
function battmanLogRun(card, root) {
  const $ = (id) => root.getElementById(id);
  const haObj = () => card.hass;

  // ------------------------------------------------------------------ state
  let last = '';
  let allLines = [];
  let changesOnly = false;

  const HISTORY_HOURS = 5;
  // Entity IDs: Battman's engine entities from Battman's entity map (GET /api/battman/entities),
  // Sigen's, Amber's and Battman's own sensors by name (SIGEN, AMBER, BATTMAN_SENSORS). Panels are built once the map has loaded.
  const NEEDS = ['mode'];
  // must exist in HA (pv_string is a pattern, third_party_pv is optional hardware)
  const NEED_ENTITIES = NEEDS.concat(['buy_price', 'feed_in_price', 'load_30m_avg', 'pv_power', 'home_power', 'battery_power', 'grid_import_power', 'grid_export_power', 'battery_soc']);
  let M = {};                 // the entity map plus SIGEN, AMBER and BATTMAN_SENSORS
  let MODE_ENTITY = null;
  const GRID_ID = '__battman_grid';   // the grid panel's series, worked out in gridSeries()
  let PANELS = [];
  let HISTORY_ENTITIES = [];

  function buildPanels() {
    MODE_ENTITY = M.mode;
    // Line-chart panels (price, power, grid, SOC, solar). Each panel becomes its own
    // synced chart; Buy+Sell share one (same units). unit '' = read the sensor's own unit.
    PANELS = [
      { id: 'price', title: 'Price (c/kWh)', unit: 'c', series: [
          { id: M.buy_price,     label: 'Buy',  token: '--battman-red',   mul: 100 },
          { id: M.feed_in_price, label: 'Sell', token: '--battman-green', mul: 100 },
        ] },
      { id: 'power', title: 'Power (kW)', unit: 'kW', series: [
          { id: M.pv_power,      label: 'Solar',   token: '--battman-amber' },
          { id: M.home_power,    label: 'Home',    token: '--battman-blue' },
          { id: M.battery_power, label: 'Battery', token: '--battman-purple' },
          { id: M.load_30m_avg,  label: 'Load',    token: '--battman-red' },
        ] },
      // grid: worked out from the Sigen import / export history (+ import, - export), so the
      // graph has full history (Battman's grid power sensor only has history from v0.17.0)
      { id: 'grid', title: 'Grid (kW)', unit: 'kW', series: [ { id: GRID_ID, label: 'Grid', token: '--battman-teal' } ] },
      { id: 'soc', title: 'Battery SOC (%)', unit: '%', series: [ { id: M.battery_soc, label: 'SOC', token: '--battman-green' } ] },
    ];

    // Solar per-string panel: however many strings (Sigen's pv_string pattern, {n} = 1..12)
    // are PRESENT and AVAILABLE, plus the plant total and an optional third-party feed.
    const h = haObj();
    const palette = ['--battman-blue', '--battman-green', '--battman-purple', '--battman-teal',
                     '--battman-red', '--battman-yellow', '--battman-orange'];
    const avail = id => { const st = h && h.states && h.states[id]; return !!(st && st.state !== 'unavailable' && st.state !== 'unknown'); };
    // a custom friendly name (e.g. "North Solar") when the entity's been renamed; the generic
    // label if it's still the default "…PVn Power" name
    const nameFor = (id, generic) => {
      const st = h && h.states && h.states[id];
      const fn = ((st && st.attributes && st.attributes.friendly_name) || '').replace(/\s*power$/i, '').trim();
      return (fn && !/pv\s*\d+\b/i.test(fn)) ? fn : generic;
    };
    const series = [{ id: M.pv_power, label: 'Total', token: '--battman-amber' }];
    let ci = 0;
    for (let n = 1; n <= 12; n++) {
      const id = M.pv_string.replace('{n}', n);
      if (avail(id)) { series.push({ id: id, label: nameFor(id, 'String ' + n), token: palette[ci % palette.length] }); ci++; }
    }
    if (avail(M.third_party_pv)) {
      series.push({ id: M.third_party_pv, label: nameFor(M.third_party_pv, '3rd Party'), token: palette[ci % palette.length] }); ci++;
    }
    PANELS.push({ id: 'solar', title: 'Solar per String (kW)', unit: 'kW', series: series }); // at the bottom
    HISTORY_ENTITIES = [MODE_ENTITY].concat(PANELS.reduce((acc, pn) => acc.concat(pn.series.map(x => x.id)), []))
      .filter(id => id !== GRID_ID).concat([M.grid_import_power, M.grid_export_power]);
  }

  const modes = ['Self Consume', 'Charge', 'Charge Solar Off', 'Float', 'Float Solar Off', 'Discharge', 'Solar Soak', 'Drain'];
  let activeModes = new Set(modes);
  let periodFilter = null;     // { start, end, mode } — limit the log to a tapped mode period

  // Mode colours: Battman's one list (window.BattmanLib.modeHues in battman-lib.js, loaded on
  // every HA page), so the timeline matches the Power view's Battery mode buttons and the Live
  // Activity: the five everyday modes are the buttons' colours, the three party modes the
  // theme's furthest-apart other colours. Checked at start (no fallback colours).
  let modeColor = {};
  let accentHex = '';
  // every Battman theme colour the card uses; all must come from the view's theme
  const THEME_VARS = ['--battman-blue', '--battman-green', '--battman-red', '--battman-orange',
    '--battman-purple', '--battman-amber', '--battman-teal', '--battman-yellow', '--battman-darkpurple',
    '--battman-pink', '--battman-sky', '--battman-text-muted',
    '--battman-blue-border', '--battman-blue-soft-bg', '--battman-surface-card', '--battman-surface-popup',
    '--battman-border-neutral', '--battman-darkred', '--battman-text-dim'];
  let FATAL = null;   // set when the card can't run; shown instead of everything else

  function pad(n) { return n.toString().padStart(2, '0'); }
  function fmtDt(d) {
    return d.getFullYear() + '-' + pad(d.getMonth()+1) + '-' + pad(d.getDate()) + ' ' +
           pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
  }
  function toInputVal(d) {
    // Round to nearest 5 min (matches picker step="300") and drop seconds.
    const r = new Date(d.getTime());
    r.setSeconds(0, 0);
    r.setMinutes(Math.round(r.getMinutes() / 5) * 5);
    return r.getFullYear() + '-' + pad(r.getMonth()+1) + '-' + pad(r.getDate()) + 'T' +
           pad(r.getHours()) + ':' + pad(r.getMinutes());
  }
  function hhmm(d) { return pad(d.getHours()) + ':' + pad(d.getMinutes()); }

  // ----------------------------------------------------------------- theme
  const gc = (name) => cssVar(card, name);
  function syncColors() {
    if (window.Chart) { const ff = gc('--primary-font-family'); if (ff) window.Chart.defaults.font.family = ff; }
    accentHex = gc('--ha-accent');
    const L = window.BattmanLib, hex = {};
    for (const hue of L.PALETTE) hex[hue] = L.cssHex(gc('--battman-' + hue));
    const hues = L.modeHues(hex);      // throws if the theme lacks a palette colour (checked at start)
    modeColor = {};
    for (const mode of modes) modeColor[mode] = hex[hues[mode]];
  }

  // --------------------------------------------------------------- filters

  const filtersEl = $('filters');
  const modesHeading = document.createElement('label');
  modesHeading.className = 'heading';
  modesHeading.textContent = 'Modes:';
  filtersEl.appendChild(modesHeading);

  const modeCheckboxes = {};
  modes.forEach(mode => {
    const lbl = document.createElement('label');
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.checked = true;
    cb.onchange = () => {
      if (cb.checked) activeModes.add(mode); else activeModes.delete(mode);
      renderLog();
    };
    modeCheckboxes[mode] = cb;
    lbl.appendChild(cb);
    lbl.appendChild(document.createTextNode(mode));
    filtersEl.appendChild(lbl);
  });

  function applyModeColors() {
    for (const [mode, cb] of Object.entries(modeCheckboxes)) {
      if (modeColor[mode]) cb.style.setProperty('--mode-accent', modeColor[mode]);
    }
  }

  const dv = document.createElement('div');
  dv.className = 'divider';
  filtersEl.appendChild(dv);

  const changesLbl = document.createElement('label');
  const changesCb = document.createElement('input');
  changesCb.type = 'checkbox';
  changesCb.checked = false;
  changesCb.onchange = () => { changesOnly = changesCb.checked; renderLog(); };
  changesLbl.appendChild(changesCb);
  changesLbl.appendChild(document.createTextNode('Changes Only'));
  filtersEl.appendChild(changesLbl);

  // ---------------------------------------------------------- log parsing
  function escapeHtml(t) { return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
  // strip a trailing "(...)" variant so e.g. "Charge (Anytime)" matches the "Charge" checkbox
  function baseMode(m) { return m.replace(/\s*\([^)]*\)\s*$/, '').trim(); }
  // each log line is "time|message"; Battman's renderer reads both its own and Smiggles' format
  const EL = window.battmanEngineLog;
  const parsed = new Map();
  function parseLine(line) {
    let p = parsed.get(line);
    if (!p) {
      const f = EL.fromFileLine(line);
      p = { stamp: f.stamp, message: f.message, log: EL.parse(f.message) };
      parsed.set(line, p);
      if (parsed.size > 6000) parsed.clear();
    }
    return p;
  }
  function getMode(line) { return baseMode(parseLine(line).log.to); }
  function isChange(line) {
    const l = parseLine(line).log;
    const from = baseMode(l.from), to = baseMode(l.to);
    return from !== '' && to !== '' && from !== to;
  }
  // an entry looks exactly like the Engine log popup (same renderer), with its mode's colour on the left
  function format(line) {
    if (line.indexOf('|') < 0) return '';
    const p = parseLine(line);
    const mode = getMode(line);
    const border = modeColor[mode] ? ' style="border-left-color:' + modeColor[mode] + '"' : '';
    return '<div class="entry"' + border + '>' + EL.render(p.message, { title: 'Engine run', timePrefix: '' }) + '</div>';
  }

  function renderLog() {
    if (FATAL) return;
    const el = $('log');
    if (allLines.length === 0) {
      el.innerHTML = '<div class="empty">Pick a range above to load the log</div>';
      return;
    }
    const filtered = allLines.filter(line => {
      if (line.indexOf('(Est)') >= 0) return false;   // drop the preliminary estimate line (one entry per 5-min)
      const mode = getMode(line);
      if (!activeModes.has(mode)) return false;
      if (changesOnly && !isChange(line)) return false;
      if (periodFilter) {
        const p = line.indexOf('|');
        const tt = p > 0 ? Date.parse(line.slice(0, p)) : NaN;
        if (!isNaN(tt) && (tt < periodFilter.start || tt >= periodFilter.end)) return false;
      }
      return true;
    });
    if (filtered.length === 0) {
      el.innerHTML = '<div class="empty">No entries match filters' + (periodFilter ? ' (block ' + escapeHtml(periodFilter.label || '') + ')' : '') + '</div>';
      return;
    }
    const periodNote = periodFilter ? ' · block ' + escapeHtml(periodFilter.label || '') + ' (' + escapeHtml(periodFilter.mode) + ')' : '';
    const countHtml = '<div class="count">' + filtered.length + ' of ' + allLines.length + ' entries' + periodNote + '</div>';
    el.innerHTML = countHtml + filtered.slice().reverse().map(format).join('');
  }

  // collapse / expand the log to reach the charts quickly
  $('logToggle').onclick = () => { haptic(); $('logCard').classList.toggle('collapsed'); };

  // The engine log for the chosen range, from Battman (GET /api/battman/log): Battman's log once
  // you've migrated, Smiggles' log file before that.
  let logRange = null;
  function load() {
    if (!logRange || FATAL) return;
    const q = '?start=' + encodeURIComponent(logRange[0]) + '&end=' + encodeURIComponent(logRange[1]);
    haObj().callApi('GET', 'battman/log' + q)
      .then(j => {
        const t = j.lines.join('\n');
        if (t !== last) {
          last = t;
          allLines = j.lines.filter(l => l.trim());
          renderLog();
        }
      })
      .catch(e => { $('log').innerHTML = '<div class="empty">' + escapeHtml(String((e && e.body && e.body.message) || (e && e.message) || 'No log found')) + '</div>'; });
  }

  // ------------------------------------------------------- range controls
  function setRangeAndLoad(start, end) {
    logRange = [fmtDt(start), fmtDt(end)];
    last = '';
    load();
  }

  // haptic feedback: Vibration API (Android/PWA) + the iOS switch-toggle trick
  function haptic() {
    try { if (navigator.vibrate) navigator.vibrate(8); } catch(e) {}
    try { const s = $('hapticSwitch'); if (s) s.click(); } catch(e) {}
  }

  // quick-range chips + always-visible From/To editor
  const rangePresets = [['5m', 5], ['10m', 10], ['15m', 15], ['30m', 30], ['1h', 60], ['2h', 120], ['4h', 240], ['8h', 480], ['12h', 720], ['24h', 1440]];
  const chipsEl = $('rangeChips');
  const fromEl = $('fromDt');
  const toEl = $('toDt');
  const fromLabel = $('fromLabel');
  const toLabel = $('toLabel');
  let curStart = null, curEnd = null;
  let presetMins = null;       // the quick range in use (null = a range you set): follows now on each run

  function fmtStamp(d) {
    return d.toLocaleString([], { weekday: 'short', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false });
  }
  function setActiveChip(chip) {
    chipsEl.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    if (chip) chip.classList.add('active');
  }
  function renderSummary() {
    fromLabel.textContent = curStart ? fmtStamp(curStart) : '—';
    toLabel.textContent = curEnd ? fmtStamp(curEnd) : '—';
  }
  function applyRange(start, end, chip) {
    curStart = start; curEnd = end;
    periodFilter = null;   // a new range/pill clears any tapped mode-period filter
    lastTapMs = null;      // and drops the tapped-point marker/anchor
    setActiveChip(chip);
    renderSummary();
    fromEl.value = toInputVal(start);
    toEl.value = toInputVal(end);
    setRangeAndLoad(start, end);
    refreshChart();   // keep the history chart on the same window as the log
    updatePager();
  }
  function loadPreset(mins, chip) {
    haptic();
    presetMins = mins;
    const now = new Date();
    applyRange(new Date(now.getTime() - mins * 60 * 1000), now, chip);
  }
  // a run was logged: on a quick range the window moves on to now (filters and the tapped point
  // stay); on a range you set, it stays put
  function follow() {
    if (presetMins == null || FATAL) return;
    const now = new Date();
    curStart = new Date(now.getTime() - presetMins * 60 * 1000); curEnd = now;
    renderSummary();
    fromEl.value = toInputVal(curStart);
    toEl.value = toInputVal(curEnd);
    setRangeAndLoad(curStart, curEnd);
    refreshChart();
    updatePager();
  }

  rangePresets.forEach(([label, mins]) => {
    const c = document.createElement('span');
    c.className = 'chip';
    c.textContent = label;
    c.onclick = () => loadPreset(mins, c);
    chipsEl.appendChild(c);
  });

  // The native pickers overlay the "Set" buttons, so a tap opens them directly (reliable on iOS);
  // showPicker() is a desktop convenience. Editing either end clears the active quick range (it's
  // now a range you set).
  function wirePicker(inp, isFrom) {
    inp.addEventListener('click', () => { haptic(); try { inp.showPicker && inp.showPicker(); } catch(e) {} });
    inp.addEventListener('change', () => {
      if (!inp.value) return;
      // iOS shows every minute regardless of step, so snap to nearest 5 min here.
      const picked = new Date(inp.value);
      picked.setSeconds(0, 0);
      picked.setMinutes(Math.round(picked.getMinutes() / 5) * 5);
      presetMins = null;
      if (isFrom) applyRange(picked, curEnd || new Date(), null);
      else applyRange(curStart || new Date(Date.now() - 15 * 60000), picked, null);
    });
  }
  wirePicker(fromEl, true);
  wirePicker(toEl, false);

  // ‹ › pager: step the window backward/forward by its own span (like HA history)
  const pagePrev = $('pagePrev');
  const pageNext = $('pageNext');
  const pgrSpan = $('pgrSpan');
  function fmtSpan(ms) {
    const m = Math.round(ms / 60000);
    if (m < 60) return m + 'm';
    if (m % 1440 === 0) return (m / 1440) + 'd';
    if (m % 60 === 0) return (m / 60) + 'h';
    return (m / 60).toFixed(1) + 'h';
  }
  function updatePager() {
    if (!curStart || !curEnd) { pgrSpan.textContent = ''; return; }
    pgrSpan.textContent = fmtSpan(curEnd.getTime() - curStart.getTime()) + ' window';
    pageNext.classList.toggle('disabled', (Date.now() - curEnd.getTime()) < 60000);
  }
  function shiftRange(dir) {
    if (!curStart || !curEnd) return;
    haptic();
    const D = curEnd.getTime() - curStart.getTime();
    const now = Date.now();
    let ns = curStart.getTime() + dir * D;
    let ne = curEnd.getTime() + dir * D;
    const live = ne >= now;
    if (live) { ne = now; ns = now - D; }   // don't page into the future; snap to live
    if (!live) presetMins = null;           // an earlier window stays where it is
    applyRange(new Date(ns), new Date(ne), live ? chipsEl.querySelector('.chip.active') : null);
  }
  pagePrev.onclick = () => shiftRange(-1);
  pageNext.onclick = () => shiftRange(1);

  // ----------------------------------------------------------- history chart
  // Same graph base as Curvy: Chart.js 4.4 (canvas), colours read from the theme.
  const charts = {};   // panel id -> Chart instance
  let modeStripState = null;   // { pts, t0, t1 } for the tap-readout on the mode strip
  let lastTapMs = null;        // last tapped/scrubbed time on the strip (for the marker + zoom anchor)
  let restoreScrub = null;     // re-applies the scrub guide after a refresh (set by the scrub block)
  let ChartLib = null;         // Chart.js, once loaded
  let chartProblem = null;     // why it couldn't be loaded

  // tap / drag on the mode strip -> show mode + time + price + SOC at that point, and
  // optionally limit the log below to that mode period.
  (function () {
    const strip = $('modeStrip');
    let lastReadSeg = null, lastT = null, downX = null, moved = false;

    // scrub guide = a thin line drawn inside each chart's own plot area (see drawChartLines)
    const reorder = $('reorder');

    // price + SOC come from the nearest log line at-or-before t (the 5-min price sensors are
    // recorder-excluded, so their history is empty — the log text is the only surviving
    // contemporaneous source).
    function nearestLine(t) {
      let best = null, bestDiff = Infinity;
      for (let i = 0; i < allLines.length; i++) {
        const p = allLines[i].indexOf('|'); if (p < 0) continue;
        const tt = Date.parse(allLines[i].slice(0, p));
        if (isNaN(tt)) continue;
        const diff = Math.abs(tt - t);
        if (diff < bestDiff) { bestDiff = diff; best = allLines[i]; }
      }
      return best;   // closest line in time, either side
    }
    function valsAt(t) {
      const line = nearestLine(t); if (!line) return {};
      const soc = (line.match(/Battery:\s*(-?[\d.]+)%/) || [])[1];
      const buy = (line.match(/Buy:\s*\$[^()]*\(Current:\s*\$(-?[\d.]+)\)/) || [])[1];
      const sell = (line.match(/Sell:\s*\$[^()]*\(Current:\s*\$(-?[\d.]+)\)/) || [])[1];
      return {
        soc: soc != null ? parseFloat(soc) : null,
        buy: buy != null ? parseFloat(buy) : null,
        sell: sell != null ? parseFloat(sell) : null,
      };
    }

    // Core scrub: given a wall-clock time, draw the strip marker + the guide line in each chart +
    // the readout. Time-based so the strip OR any chart can drive it, and so it can be re-applied
    // after a refresh (the strip bar is inset to the charts' plot area, so one screen-x maps to the
    // same time in all panels).
    function scrubToTime(t) {
      if (!modeStripState) return;
      const bar = strip.querySelector('.mbar');
      const out = strip.querySelector('#modeReadout');
      if (!bar || !out) return;
      const t0 = modeStripState.t0, t1 = modeStripState.t1, span = Math.max(1, t1 - t0);
      t = Math.max(t0, Math.min(t1, t));
      lastTapMs = t;
      const frac = (t - t0) / span;
      const mark = strip.querySelector('#modeMark');
      if (mark) { mark.style.left = (frac * 100).toFixed(3) + '%'; mark.style.opacity = '1'; }
      drawChartLines(frac);
      const pts = modeStripState.pts;
      let m = pts.length ? pts[0].m : '';
      let segStart = t0, segEnd = t1, idx = -1;
      for (let i = 0; i < pts.length; i++) {
        if (pts[i].t <= t) { m = pts[i].m; idx = i; segStart = Math.max(t0, pts[i].t); segEnd = (i + 1 < pts.length) ? pts[i + 1].t : t1; }
        else break;
      }
      segEnd = Math.min(t1, segEnd);
      lastReadSeg = { start: segStart, end: segEnd, mode: m };
      lastT = t;

      // how long this mode block runs before it switches, from the mode entity's real change
      // times (so it's the true length even if it spills past the window edges). Last block has
      // no next change yet → "so far"; a block whose start sits at the window's left edge may
      // have begun earlier → "+".
      let durTxt = '';
      if (idx >= 0) {
        const realStart = pts[idx].t;
        const realEnd = (idx + 1 < pts.length) ? pts[idx + 1].t : null;
        if (realEnd == null) {
          durTxt = Math.max(0, Math.round((t1 - realStart) / 60000)) + ' min so far';
        } else {
          durTxt = Math.max(1, Math.round((realEnd - realStart) / 60000)) + ' min' + (realStart <= t0 ? '+' : '');
        }
      }

      const cents = v => v == null ? '—' : (v * 100).toFixed(1) + 'c';
      const pct = v => v == null ? '—' : v.toFixed(1) + '%';
      const v = valsAt(t);
      // show the same 5-min block the tap would filter (anchored to the nearest log line)
      const line = nearestLine(t);
      let dispT = t;
      if (line) { const a = Date.parse(line.slice(0, line.indexOf('|'))); if (!isNaN(a)) dispT = Math.floor(a / 300000) * 300000; }
      out.innerHTML =
        '<span class="dot" style="background:' + (modeColor[m] || accentHex) + '"></span>' +
        hhmm(new Date(dispT)) + ' &middot; <b>' + escapeHtml(m) + '</b>' +
        (durTxt ? ' &middot; <span class="ro-dur">' + durTxt + '</span>' : '') +
        '<span class="ro-extra">buy ' + cents(v.buy) + ' · sell ' + cents(v.sell) + ' · SOC ' + pct(v.soc) + '</span>';
    }

    // keep the guide alive across a refresh (the refresh rebuilds the strip)
    restoreScrub = () => { if (lastTapMs != null) scrubToTime(lastTapMs); };

    // draw the guide as a thin line inside each visible chart's plot area (not across the whole
    // stack) — same x-fraction everywhere since all panels share the plot range.
    function drawChartLines(frac) {
      Object.keys(charts).forEach(id => {
        const ch = charts[id];
        const wrap = $('wrap-' + id);
        if (!wrap) return;
        let line = wrap.querySelector('.cline');
        if (!ch || !ch.chartArea || wrap.style.display === 'none') { if (line) line.style.opacity = '0'; return; }
        if (!line) { line = document.createElement('div'); line.className = 'cline'; wrap.appendChild(line); }
        const ca = ch.chartArea;
        line.style.left = (ca.left + frac * (ca.right - ca.left)).toFixed(1) + 'px';
        line.style.top = ca.top.toFixed(1) + 'px';
        line.style.height = Math.max(0, ca.bottom - ca.top).toFixed(1) + 'px';
        line.style.opacity = '1';
      });
    }

    // strip -> time (clientX within the strip bar)
    function readAt(clientX) {
      if (!modeStripState) return;
      const bar = strip.querySelector('.mbar'); if (!bar) return;
      const rect = bar.getBoundingClientRect();
      let frac = (clientX - rect.left) / rect.width;
      frac = Math.max(0, Math.min(1, frac));
      scrubToTime(modeStripState.t0 + frac * (modeStripState.t1 - modeStripState.t0));
    }

    // chart -> time (clientX within a chart's plot area; all panels share t0..t1)
    function chartUnder(e) {
      const wrap = e.target && e.target.closest && e.target.closest('.chartWrap');
      if (!wrap) return null;
      const ch = charts[wrap.id.replace(/^wrap-/, '')];
      return (ch && ch.chartArea) ? ch : null;
    }
    function readChart(ch, clientX) {
      if (!modeStripState) return;
      const r = ch.canvas.getBoundingClientRect(), ca = ch.chartArea;
      let frac = (clientX - r.left - ca.left) / Math.max(1, ca.right - ca.left);
      frac = Math.max(0, Math.min(1, frac));
      scrubToTime(modeStripState.t0 + frac * (modeStripState.t1 - modeStripState.t0));
    }

    // tap = filter the log to the 5-minute block around the tapped point; drag = just scrub.
    // Anchored to the NEAREST actual log line, ±2.5 min around it, so it never depends on
    // timestamps being exactly on the 5-min mark and always contains that line (never empty).
    // Pick a range up top to reset.
    function setFilter() {
      if (lastT == null) return;
      const line = nearestLine(lastT);
      if (!line) return;                       // nothing to anchor to -> leave the log as-is
      const anchor = Date.parse(line.slice(0, line.indexOf('|')));
      if (isNaN(anchor)) return;
      const HALF = 150 * 1000, FIVE = 300 * 1000;   // ±2.5 min window; label as its 5-min block
      const blk = Math.floor(anchor / FIVE) * FIVE;
      periodFilter = {
        start: anchor - HALF, end: anchor + HALF,
        mode: lastReadSeg ? lastReadSeg.mode : '',
        label: hhmm(new Date(blk)) + '–' + hhmm(new Date(blk + FIVE)),
      };
      renderLog();
    }
    strip.addEventListener('pointerdown', e => { downX = e.clientX; moved = false; readAt(e.clientX); });
    strip.addEventListener('pointermove', e => {
      if (!(e.buttons || e.pressure > 0)) return;
      if (downX != null && Math.abs(e.clientX - downX) > 6) moved = true;
      readAt(e.clientX);
    });
    strip.addEventListener('pointerup', e => { if (!moved) { setFilter(); readAt(e.clientX); } downX = null; });

    // scrub on the charts too: tap or horizontal-drag over any chart moves the guide line
    // (touch-action:pan-y keeps vertical scrolling working). Charts only scrub — they don't
    // touch the log filter (that stays the strip's tap job).
    reorder.addEventListener('pointerdown', e => { const ch = chartUnder(e); if (ch) readChart(ch, e.clientX); });
    reorder.addEventListener('pointermove', e => {
      if (!(e.buttons || e.pressure > 0)) return;
      const ch = chartUnder(e); if (ch) readChart(ch, e.clientX);
    });
  })();

  // a chart panel card per PANELS entry, appended into the reorder stack
  function buildPanelCards() {
    const host = $('reorder');
    PANELS.forEach(p => {
      const div = document.createElement('div');
      div.className = 'card reCard';
      div.setAttribute('data-block', p.id);
      div.innerHTML =
        '<div class="title cardHead"><span>' + p.title + '</span><span class="grip" data-grip></span></div>' +
        '<div class="chartWrap" id="wrap-' + p.id + '" style="display:none"><canvas id="cv-' + p.id + '"></canvas></div>' +
        '<div class="chart-empty" id="empty-' + p.id + '">Loading&hellip;</div>';
      host.appendChild(div);
    });
  }

  // the element that scrolls the dashboard (HA's view or the page), for scrolling while dragging
  function scrollParent() {
    for (let n = card.parentNode || card.host; n; n = n.parentNode || n.host) {
      if (n.nodeType !== 1) continue;
      const oy = getComputedStyle(n).overflowY;
      if ((oy === 'auto' || oy === 'scroll') && n.scrollHeight > n.clientHeight) return n;
    }
    return document.scrollingElement || document.documentElement;
  }

  // ---- drag-to-reorder (grip only) with per-device localStorage persistence ----
  function initReorder() {
    const container = $('reorder');
    const KEY = 'battman.logOrder';
    // one-time move of the order saved by the old Smiggles page
    try {
      const old = localStorage.getItem('smigglesLogOrderV1');
      if (old !== null) { if (localStorage.getItem(KEY) === null) localStorage.setItem(KEY, old); localStorage.removeItem('smigglesLogOrderV1'); }
    } catch (e) {}
    let dragEl = null, placeholder = null, startY = 0, startTop = 0, scroller = null;

    const cards = () => Array.from(container.querySelectorAll('.reCard'));

    function saveOrder() {
      try { localStorage.setItem(KEY, JSON.stringify(cards().map(c => c.getAttribute('data-block')))); } catch (e) {}
    }
    function applyOrder() {
      let order = null;
      try { order = JSON.parse(localStorage.getItem(KEY) || 'null'); } catch (e) {}
      if (!order || !order.length) return;
      order.forEach(id => {
        const el = container.querySelector('.reCard[data-block="' + id + '"]');
        if (el) container.appendChild(el);   // unknown/new ids just stay after, in default order
      });
    }

    // the dragged card is lifted out of the stack (absolute, inside it) and follows the pointer;
    // a dashed placeholder shows where it will land
    function placeAt(clientY) {
      const top = startTop + (clientY - startY) - container.getBoundingClientRect().top;
      dragEl.style.top = top + 'px';
    }
    function onDown(e) {
      const grip = e.target.closest('[data-grip]');
      if (!grip) return;
      const cardEl = grip.closest('.reCard');
      if (!cardEl) return;
      e.preventDefault(); e.stopPropagation();
      haptic();
      dragEl = cardEl;
      scroller = scrollParent();
      const rect = cardEl.getBoundingClientRect();
      startTop = rect.top; startY = e.clientY;
      placeholder = document.createElement('div');
      placeholder.className = 're-placeholder';
      placeholder.style.height = rect.height + 'px';
      cardEl.parentNode.insertBefore(placeholder, cardEl.nextSibling);
      cardEl.classList.add('dragging');
      cardEl.style.position = 'absolute'; cardEl.style.zIndex = '999';
      cardEl.style.left = '0'; cardEl.style.right = '0';
      cardEl.style.margin = '0'; cardEl.style.pointerEvents = 'none';
      placeAt(e.clientY);
      window.addEventListener('pointermove', onMove);
      window.addEventListener('pointerup', onUp, { once: true });
    }
    function onMove(e) {
      if (!dragEl) return;
      const y = e.clientY;
      placeAt(y);
      let inserted = false;
      for (const c of cards()) {
        if (c === dragEl) continue;
        const r = c.getBoundingClientRect();
        if (y < r.top + r.height / 2) { container.insertBefore(placeholder, c); inserted = true; break; }
      }
      if (!inserted) container.appendChild(placeholder);
      const vh = window.innerHeight;
      if (y < 70) scroller.scrollBy(0, -14);
      else if (y > vh - 70) scroller.scrollBy(0, 14);
    }
    function onUp() {
      window.removeEventListener('pointermove', onMove);
      if (!dragEl) return;
      container.insertBefore(dragEl, placeholder);
      placeholder.remove(); placeholder = null;
      dragEl.classList.remove('dragging');
      dragEl.style.position = ''; dragEl.style.zIndex = ''; dragEl.style.left = ''; dragEl.style.right = '';
      dragEl.style.top = ''; dragEl.style.margin = ''; dragEl.style.pointerEvents = '';
      dragEl = null;
      saveOrder();
      try { Object.values(charts).forEach(ch => ch && ch.resize()); requestAnimationFrame(alignModeStrip); } catch (e) {}
    }
    container.addEventListener('pointerdown', onDown);
    // a tap/click on the grip must not toggle the log collapse
    container.addEventListener('click', e => {
      if (e.target.closest('[data-grip]')) { e.stopPropagation(); e.preventDefault(); }
    }, true);

    applyOrder();
  }

  async function fetchHistoryRaw() {
    // the chart window is the log's selected range (last 5 h until one is picked)
    const end = curEnd ? new Date(curEnd) : new Date();
    const start = curStart ? new Date(curStart) : new Date(end.getTime() - HISTORY_HOURS * 3600 * 1000);
    const path = 'history/period/' + start.toISOString() +
      '?filter_entity_id=' + HISTORY_ENTITIES.join(',') +
      '&end_time=' + end.toISOString() + '&minimal_response';
    try {
      const arr = await haObj().callApi('GET', path);
      const out = {};
      (arr || []).forEach(ser => { if (ser && ser.length && ser[0].entity_id) out[ser[0].entity_id] = ser; });
      out[GRID_ID] = gridSeries(out[M.grid_import_power], out[M.grid_export_power]);
      return { out, start, end };
    } catch(e) { return null; }
  }

  // Grid power history from import / export history, with the same rule as Battman's grid power
  // sensor (and Smiggles' GridPower): whichever side flows over 50 W, import +, export -.
  // A point only where both are known: no made-up values.
  function gridSeries(imp, exp) {
    const ev = [];
    (imp || []).forEach(s => ev.push({ t: new Date(s.last_changed || s.last_updated).getTime(), k: 'i', v: parseFloat(s.state) }));
    (exp || []).forEach(s => ev.push({ t: new Date(s.last_changed || s.last_updated).getTime(), k: 'e', v: parseFloat(s.state) }));
    ev.sort((a, b) => a.t - b.t);
    let i = NaN, e = NaN; const out = [];
    for (const p of ev) {
      if (p.k === 'i') i = p.v; else e = p.v;
      let g = null;
      if (isFinite(i) && isFinite(e)) g = (i > 0.05 && i >= e) ? Math.round(i * 100) / 100 : (e > 0.05 && e > i) ? -Math.round(e * 100) / 100 : 0;
      out.push({ last_changed: new Date(p.t).toISOString(), state: g === null ? 'unavailable' : String(g) });
    }
    return out;
  }

  function bucketize(series, start, end, n, parse) {
    const pts = (series || []).map(s => ({ t: new Date(s.last_changed || s.last_updated).getTime(), raw: s.state }))
      .filter(p => !isNaN(p.t)).sort((a,b) => a.t - b.t);
    const t0 = start.getTime(), step = (end.getTime() - t0) / n;
    const out = []; let j = 0, cur = null;
    for (let i = 0; i < n; i++) {
      const tt = t0 + step * (i + 0.5);
      while (j < pts.length && pts[j].t <= tt) { cur = pts[j].raw; j++; }
      out.push(cur == null ? null : (parse ? parse(cur) : cur));
    }
    return out;
  }

  // Shared bucket grid so the Mode strip and every line panel cover an identical x-domain.
  // 5-min buckets (price/mode cadence); 1-min on sub-hour windows for detail (1 min divides 5, so
  // 5-min alignment still holds). Floors start / ceils end to whole buckets.
  function gridDomain(start, end) {
    const FIVE = 300000, ONE = 60000;
    const width = ((end.getTime() - start.getTime()) / FIVE >= 12) ? FIVE : ONE;
    const t0 = Math.floor(start.getTime() / width) * width;
    const n = Math.max(1, Math.ceil((end.getTime() - t0) / width));
    return { t0: t0, tEnd: t0 + n * width, width: width, n: n };
  }

  // Mode is its own state-timeline strip, not mixed into the price chart.
  function renderModeStrip(modeRaw, start, end) {
    const el = $('modeStrip');
    root.querySelectorAll('.cline').forEach(l => l.style.opacity = '0');
    // Lock the strip to the SAME grid the line panels use, so a time on the strip sits directly
    // above the same column in the charts below.
    const { t0, tEnd, width, n } = gridDomain(start, end);
    const t1 = tEnd, span = Math.max(1, t1 - t0);
    const pts = (modeRaw || []).map(s => ({ t: new Date(s.last_changed || s.last_updated).getTime(), m: s.state }))
      .filter(p => !isNaN(p.t)).sort((a, b) => a.t - b.t);
    if (!pts.length) { modeStripState = null; el.innerHTML = '<div class="chart-empty">No mode history</div>'; return; }
    modeStripState = { pts: pts, t0: t0, t1: t1 };

    let bar = '';
    const seen = [];
    for (let i = 0; i < pts.length; i++) {
      // back-fill the first mode across the leading <5-min sliver (t0..first point) so the bar
      // fills from the grid's left edge, mirroring the charts' first bucket.
      const segStart = (i === 0) ? t0 : Math.max(t0, pts[i].t);
      const segEnd = Math.min(t1, (i + 1 < pts.length) ? pts[i + 1].t : t1);
      if (segEnd <= segStart) continue;
      const w = ((segEnd - segStart) / span) * 100;
      const col = modeColor[pts[i].m] || accentHex;
      if (seen.indexOf(pts[i].m) < 0) seen.push(pts[i].m);
      bar += '<div class="mseg" style="width:' + w.toFixed(3) + '%;background:' + col + '" title="' +
             escapeHtml(pts[i].m) + '"></div>';
    }
    // ticks at the same bucket positions (band centres) + times as the chart x-labels
    const every = Math.max(1, Math.round(n / 8));
    let ticks = '';
    for (let i = 0; i < n; i += every) {
      const frac = ((i + 0.5) / n) * 100;
      ticks += '<span style="left:' + frac.toFixed(3) + '%">' + hhmm(new Date(t0 + width * i)) + '</span>';
    }
    let legend = seen.map(m =>
      '<span class="li"><span class="dot" style="background:' + (modeColor[m] || accentHex) + '"></span>' + escapeHtml(m) + '</span>'
    ).join('');
    el.innerHTML = '<div class="mbar">' + bar + '<div class="mmark" id="modeMark"></div></div><div class="mticks">' + ticks + '</div>' +
                   '<div class="mreadout" id="modeReadout"><span class="hint">Tap the timeline for the mode at a point</span></div>' +
                   '<div class="mlegend">' + legend + '</div>';
  }

  // Generic line panel (Curvy's Chart.js base); one or more series sharing a unit.
  function renderLinePanel(panel, data) {
    const wrap = $('wrap-' + panel.id);
    const empty = $('empty-' + panel.id);
    function showEmpty(msg) { if (empty) { empty.style.display = ''; empty.textContent = msg; } if (wrap) wrap.style.display = 'none'; }
    if (!ChartLib) return showEmpty('Chart library unavailable: ' + (chartProblem || 'not loaded yet'));
    if (!data) return showEmpty('History unavailable');
    const { out, start, end } = data;
    if (!panel.series.some(s => out[s.id] && out[s.id].length)) return showEmpty('No data in range');
    if (empty) empty.style.display = 'none';
    if (wrap) wrap.style.display = '';

    // One time grid for EVERY panel, aligned to the 5-min price/mode cadence so all panels line
    // up vertically.
    const { t0, tEnd, width, n } = gridDomain(start, end);
    const gStart = new Date(t0), gEnd = new Date(tEnd), step = width;
    const every = Math.max(1, Math.round(n / 8));
    const labels = Array.from({length: n}, (_, i) => (i % every === 0) ? hhmm(new Date(t0 + step * i)) : '');
    const grid = gc('--ha-border');
    const muted = gc('--battman-text-muted');

    const h = haObj();
    let unit = panel.unit;
    if (unit === '') { const st = h && h.states[panel.series[0].id]; unit = (st && st.attributes && st.attributes.unit_of_measurement) || ''; }

    const datasets = panel.series.map(s => {
      const col = gc(s.token);
      const arr = bucketize(out[s.id], gStart, gEnd, n, v => { const f = parseFloat(v); return isFinite(f) ? (s.mul ? f * s.mul : f) : null; });
      return {
        label: s.label, data: arr, borderColor: col, backgroundColor: col + '20',
        fill: panel.series.length === 1, tension: 0, stepped: true, pointRadius: 0, pointHoverRadius: 4, borderWidth: 2, spanGaps: true
      };
    });

    const cfg = {
      type: 'line',
      data: { labels: labels, datasets: datasets },
      options: {
        responsive: true, maintainAspectRatio: false, animation: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: panel.series.length > 1, position: 'top', labels: { boxWidth: 20, boxHeight: 3, padding: 10, color: muted, font: { size: 11 } } },
          tooltip: { callbacks: { label: c => c.dataset.label + ': ' + (c.parsed.y == null ? '—' : c.parsed.y.toFixed(1) + (unit ? ' ' + unit : '')) } }
        },
        scales: {
          // fixed y-axis width → every panel's plot area starts at the same x, so the panels line
          // up with each other AND the Mode strip can be inset to match.
          y: { afterFit: (s) => { s.width = 52; }, title: { display: !!unit, text: unit, font: { size: 11, weight: 'bold' }, color: muted }, ticks: { color: muted }, grid: { color: grid } },
          // offset:true centres each point in its time-band (band i → (i+0.5)/n), the same linear
          // mapping the Mode strip uses, so columns align across all of them.
          x: { offset: true, ticks: { color: muted, maxRotation: 0, autoSkip: false }, grid: { color: grid } }
        }
      }
    };

    if (charts[panel.id]) charts[panel.id].destroy();
    charts[panel.id] = new ChartLib($('cv-' + panel.id).getContext('2d'), cfg);
  }

  // Inset the Mode strip's bar + ticks to sit exactly over the charts' plot area (left = y-axis
  // gutter, right = chart's right padding), measured from a live chart. The strip card and the
  // chart cards share an identical content width, so chartArea pixels map 1:1 onto the strip.
  function alignModeStrip() {
    const strip = $('modeStrip');
    if (!strip) return;
    const bar = strip.querySelector('.mbar');
    const ticks = strip.querySelector('.mticks');
    const ref = Object.values(charts).find(c => c && c.chartArea && c.width);
    const apply = (l, r) => { [bar, ticks].forEach(elm => { if (elm) { elm.style.marginLeft = l; elm.style.marginRight = r; } }); };
    if (!bar || !ref) { apply('', ''); return; }
    const ca = ref.chartArea, cw = ref.width;
    apply(ca.left.toFixed(1) + 'px', Math.max(0, cw - ca.right).toFixed(1) + 'px');
  }

  async function refreshChart() {
    if (FATAL || !PANELS.length) return;
    const data = await fetchHistoryRaw();
    const modeEl = $('modeStrip');
    if (!data) {
      if (modeEl) modeEl.innerHTML = '<div class="chart-empty">History unavailable</div>';
      PANELS.forEach(p => renderLinePanel(p, null));
      return;
    }
    renderModeStrip(data.out[MODE_ENTITY], data.start, data.end);
    PANELS.forEach(p => renderLinePanel(p, data));
    // re-align the strip, then re-draw the scrub guide if one was active (range changes null
    // lastTapMs, so a new range clears it; a plain refresh keeps it).
    requestAnimationFrame(() => { alignModeStrip(); if (restoreScrub) restoreScrub(); });
  }

  // ----------------------------------------------------------------- boot
  // Startup checks: entity map + Battman theme. Problems are shown, never papered over.
  function showFatal(msg) {
    FATAL = msg;
    $('reorder').innerHTML =
      '<div class="card"><div class="title">Battman Log problem</div><div class="empty">' + escapeHtml(msg) + '</div></div>';
  }
  // live: each engine run reloads the log (and moves a quick range on to now)
  let unsubLive = null, liveTimer = null;
  function setLiveNote(text) {
    const n = $('liveNote');
    if (!n) return;
    n.hidden = !text;
    n.textContent = text || '';
  }
  function subscribeLive() {
    if (unsubLive || FATAL) return;
    const conn = haObj().connection;
    unsubLive = conn.subscribeEvents(() => {
      clearTimeout(liveTimer);
      // Battman writes the run into engine.log as the event arrives; read it a moment later
      liveTimer = setTimeout(() => { if (presetMins != null) follow(); else { last = ''; load(); } }, 1500);
    }, LOG_EVENT);
    unsubLive.then(() => setLiveNote(''), (e) => {
      unsubLive = null;
      setLiveNote('Live updates off: ' + ((e && e.message) || (e && e.code) || e) + '. Pick a range to reload.');
    });
  }
  function unsubscribeLive() {
    clearTimeout(liveTimer);
    if (unsubLive) { const u = unsubLive; unsubLive = null; u.then((f) => f && f()).catch(() => {}); }
  }

  let chartTimer = null;
  let started = false;
  let resizeObs = null;

  (async function start() {
    try {
      M = { ...await battmanMap(haObj(), NEEDS), ...SIGEN, ...AMBER, ...BATTMAN_SENSORS };
    } catch (e) { showFatal(e.message); return; }
    const problem = missingThemeVars(card, THEME_VARS) || missingEntities(haObj(), M, NEED_ENTITIES);
    if (problem) { showFatal(problem); return; }
    const lib = window.BattmanLib;
    if (!lib || !lib.modeHues) { showFatal("Battman's card library (battman-lib.js) isn't loaded on this HA page, so the mode colours aren't known. Refresh the page."); return; }
    const noMode = modes.filter(m => lib.MODES.indexOf(m) < 0);
    if (noMode.length) { showFatal('Battman mode colours have no colour for: ' + noMode.join(', ')); return; }
    try { ChartLib = await loadChartJs(); } catch (e) { chartProblem = e.message; }
    try { syncColors(); } catch (e) { showFatal('Battman mode colours: ' + e.message); return; }
    applyModeColors();
    buildPanels();
    buildPanelCards();
    initReorder();
    // default view: last 4 hours, no haptic on load
    const now = new Date();
    presetMins = 240;
    const chip4h = Array.from(chipsEl.querySelectorAll('.chip')).find(c => c.textContent === '4h');
    applyRange(new Date(now.getTime() - 4 * 60 * 60 * 1000), now, chip4h);
    resizeObs = new ResizeObserver(() => requestAnimationFrame(alignModeStrip));
    resizeObs.observe($('reorder'));
    started = true;
    if (card.isConnected) resume();
  })();

  let paused = false;
  function resume() {
    if (!started || FATAL) return;
    subscribeLive();
    if (!chartTimer) chartTimer = setInterval(refreshChart, 60000);
    // back on screen after another view: catch up (a quick range moves on to now)
    if (paused) { paused = false; if (presetMins != null) follow(); else refreshChart(); }
  }
  function pause() {
    paused = true;
    unsubscribeLive();
    clearInterval(chartTimer); chartTimer = null;
  }
  // the view's theme changed: redraw in the new colours
  function themeChanged() {
    if (!started || FATAL) return;
    try { syncColors(); } catch (e) { showFatal('Battman mode colours: ' + e.message); return; }
    applyModeColors();
    renderLog();
    refreshChart();
  }
  return { resume, pause, themeChanged };
}

class BattmanLogCard extends BattmanCardBase {
  static cardName = "Battman Log";
  static preview = "log.webp";
  static gridOptions = { columns: "full", rows: "auto" };
  static css = LOG_CSS;
  static html = LOG_HTML;

  getCardSize() {
    return 12;
  }

  run(root) {
    if (!window.battmanEngineLog) {
      this.problem("Battman's engine log renderer (battman-enginelog.js) isn't loaded on this HA page. Refresh the page.");
      return {};
    }
    return battmanLogRun(this, root);
  }
}
battmanDefine("battman-log", BattmanLogCard);
battmanPicker("battman-log", "Battman Log",
  "The engine log: each run's decisions, with power, prices and battery charge charted over the day.", "battman-log");
