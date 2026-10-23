// Battman Pricy: custom:battman-pricy. The price curve editor: the sell and buy prices the engine
// works to at each hour, for each month or season, with Sell / Buy and high-consumption curves. A
// real card (it used to be the Pricy page, /battmanfiles/pricy.html, in a frame): HA hands it its
// connection and theme directly.
//
//   type: custom:battman-pricy
//
// Same as the page it replaces: Month / Season, the four curve types, the two hour panels (the
// second can follow the first), Set All, the Amber price overlay (today's actual prices and the
// forecast) with hour details, Save, presets, copy / paste / export / import a period, Factory
// Defaults, Run Script and Auto-save.
//
// Entities and events come from Battman's entity map, colours from the Battman theme. Anything
// missing is shown on the card, never made up. The chart uses Chart.js, shipped with Battman.
// ---------------------------------------------------------------------------------------------

import { BattmanCardBase, battmanDefine, battmanMap, battmanPicker, cssVar, loadChartJs, missingEntities, missingThemeVars } from "./battman-card-base.js";
import { NOT_SAVED, debugBox, hourLabel, presetMenus, pressFeedback, savedIn, showNote as noteIn, wireHandlers } from "./battman-curve-editor.js";

const CSS = `
  :host { display: block; }
  ha-card { background: var(--primary-background-color); overflow: hidden; container-type: inline-size; }

    :host { color-scheme: light dark; }

    :host, .modal {
      font-family: var(--primary-font-family, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif);
      font-size: 16px; line-height: normal;
      color: var(--primary-text-color, #1a1a1a);
    }
    .page { padding: 20px; }

    .container {
      box-sizing: border-box;
      max-width: 2200px;
      margin: 0 auto;
      background: var(--card-background-color, #ffffff);
      border-radius: var(--ha-card-border-radius, 12px);
      padding: 24px;
      box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0,0,0,0.1));
    }

    h2 { margin: 0 0 24px 0; color: var(--primary-text-color, #1a1a1a); font-size: 24px; font-weight: 700; }

    .mode-toggle { display: flex; gap: 12px; margin-bottom: 20px; }
    .mode-btn {
      padding: 5px 14px; border: 1px solid var(--battman-border-neutral);
      border-radius: 8px; font-size: 12px; font-weight: 700; letter-spacing: 0.06em;
      text-transform: uppercase; cursor: pointer;
      transition: background 0.12s ease, border-color 0.12s ease, color 0.12s ease, transform 0.08s ease;
      background: var(--battman-surface-card); color: var(--battman-text-muted);
      display: flex; align-items: center; gap: 6px;
    }
    .mode-btn.pressed { transform: scale(0.95); }
    .mode-btn-month.active  { background: var(--battman-blue-soft-bg); border-color: var(--battman-blue-border-strong); color: var(--battman-blue); }
    .mode-btn-season.active { background: var(--battman-amber-soft-bg); border-color: var(--battman-amber-border-strong); color: var(--battman-amber); }

    .tabs {
      display: flex; gap: 10px 6px; margin-bottom: 20px;
      align-items: center; flex-wrap: wrap;
    }
    .tab {
      padding: 7px 13px; border: 1px solid transparent; background: none; cursor: pointer;
      font-size: 13px; font-weight: 500; color: var(--secondary-text-color, #666);
      font-family: inherit; transition: background .12s ease, border-color .12s ease, color .12s ease;
    }
    .tab:hover { color: var(--primary-text-color, #333); }
    /* Curve-type tabs → segmented ghost buttons (active glows in the curve colour) */
    .ctab {
      border: 1px solid var(--battman-border-neutral);
      border-radius: 8px;
      background: var(--battman-surface-card);
      color: var(--battman-text-muted);
      font-weight: 600;
    }
    .ctab.sell-active, .ctab.sell-high-active, .ctab.buy-active, .ctab.buy-high-active {
      background: color-mix(in srgb, var(--active-curve, var(--battman-blue)) 14%, transparent);
      border-color: var(--active-curve, var(--battman-blue));
      color: var(--active-curve, var(--battman-blue));
    }

    .month-tabs, .season-tabs {
      margin-left: auto; display: flex; gap: 6px 4px; flex-wrap: wrap;
    }
    .season-tabs { display: none; }
    /* Months → compact pills (active glows in the current curve colour) */
    .month-tabs .tab, .season-tabs .tab {
      padding: 4px 12px;
      border: 1px solid var(--battman-border-neutral);
      border-radius: 999px;
      background: var(--battman-surface-popup);
      color: var(--battman-text-muted);
      font-size: 12px;
    }
    .month-tabs .tab.active, .season-tabs .tab.active {
      background: color-mix(in srgb, var(--active-curve, var(--battman-blue)) 14%, transparent);
      border-color: var(--active-curve, var(--battman-blue));
      color: var(--active-curve, var(--battman-blue));
      font-weight: 600;
    }

    .chart-controls {
      display: flex; gap: 12px; margin-bottom: 12px;
      flex-wrap: wrap; align-items: center;
    }
    .chart-controls label {
      font-size: 13px; font-weight: 600; color: var(--secondary-text-color, #666);
      display: flex; align-items: center; gap: 6px; cursor: pointer;
    }
    .chart-controls input[type="checkbox"] {
      width: 16px; height: 16px; cursor: pointer;
      accent-color: var(--primary-color, #2563eb);
    }

    .debug-box {
      background: var(--battman-red-soft-bg);
      border: 1px solid var(--battman-red);
      padding: 12px 14px; border-radius: 10px; margin-bottom: 20px;
      font-size: 12px; line-height: 1.6; color: var(--battman-text-bright);
      font-family: 'Courier New', monospace; max-height: 200px; overflow-y: auto;
    }
    .debug-box .btn { font-family: var(--primary-font-family, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif); }
    /* Form controls don't inherit font-family by default — make them follow the theme */
    input, textarea, select, button { font-family: inherit; }

    .chart-container {
      height: 320px; margin-bottom: 24px;
      background: var(--secondary-background-color, #f9fafb);
      padding: 12px 16px;
      border-radius: 8px; position: relative;
      border: 1px solid var(--divider-color, rgba(0,0,0,0.06));
    }
    @container (min-width: 600px) { .chart-container { height: 360px; } }

    .chart-legend {
      display: flex; gap: 14px; margin-bottom: 8px;
      flex-wrap: wrap; align-items: center;
    }
    .legend-item { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--secondary-text-color, #666); }
    .legend-line { width: 22px; height: 3px; border-radius: 2px; }

    /* ── Hour Details Cards (matches SOC editor) ── */
    .hd-card {
      background: var(--battman-surface-popup);
      border: 1px solid var(--battman-border-neutral);
      border-radius: 10px;
      padding: 12px 14px;
      box-sizing: border-box;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 10px;
    }
    .hd-card-main { min-width: 0; }
    .hd-card-label {
      font-size: 11px; font-weight: 500; letter-spacing: 0.05em;
      text-transform: uppercase; margin-bottom: 6px;
    }
    .hd-card-value {
      font-size: 26px; font-weight: 500; line-height: 1.1;
      color: var(--battman-text-bright); white-space: nowrap;
    }
    .hd-card-value .unit {
      font-size: 14px; font-weight: 400;
      color: var(--battman-text-muted);
    }
    /* first card is split: value on the left, the hour standing out on the right */
    .hd-card.hd-card-hour { padding: 0; }
    .hd-card-hour .hd-thr-main { flex: 1; padding: 12px 14px; }
    .hd-card-hour .hd-thr-time {
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      padding: 12px 14px; min-width: 60px;
      border-left: 1px solid var(--battman-border-neutral);
    }
    .hd-thr-time-val {
      font-size: 24px; font-weight: 600; line-height: 1;
      color: var(--battman-text-bright);
    }
    .hd-thr-time-tag {
      font-size: 9px; font-weight: 500; letter-spacing: 0.08em; text-transform: uppercase;
      color: var(--battman-text-dim); margin-top: 4px;
    }

    /* ── Input hover highlight ─────────────────────────────────────────────── */
    .control-group .value-input.chart-hover {
      border-color: var(--primary-color, #2563eb) !important;
      background: color-mix(in srgb, var(--primary-color, #2563eb) 12%, var(--card-background-color, #fff)) !important;
      box-shadow: 0 0 0 3px color-mix(in srgb, var(--primary-color, #2563eb) 20%, transparent);
    }
    .control-group .value-input.chart-click {
      border-color: var(--accent-color, #f59e0b) !important;
      background: color-mix(in srgb, var(--accent-color, #f59e0b) 12%, var(--card-background-color, #fff)) !important;
      box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent-color, #f59e0b) 22%, transparent);
      animation: pulse-click 0.6s ease-out;
    }
    @keyframes pulse-click {
      0%   { box-shadow: 0 0 0 0px  color-mix(in srgb, var(--accent-color, #f59e0b) 50%, transparent); }
      60%  { box-shadow: 0 0 0 8px  color-mix(in srgb, var(--accent-color, #f59e0b)  0%, transparent); }
      100% { box-shadow: 0 0 0 3px  color-mix(in srgb, var(--accent-color, #f59e0b) 22%, transparent); }
    }

    /* Two-column input sections */
    .input-grid {
      display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px;
    }
    @container (max-width: 700px) { .input-grid { grid-template-columns: 1fr; } }

    .input-section {
      background: var(--secondary-background-color, #f8f9fa);
      border: 1px solid var(--divider-color, #e5e7eb);
      border-radius: 8px; padding: 14px;
      overflow: visible;
    }

    .controls {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(52px, 1fr));
      gap: 8px; margin-bottom: 0; padding: 4px;
    }
    .control-group { display: flex; flex-direction: column; gap: 5px; align-items: center; }
    .control-group label {
      font-size: 10px; font-weight: 600;
      color: var(--secondary-text-color, #888); text-align: center;
      font-variant-numeric: tabular-nums;
    }
    .control-group .value-input {
      width: 100%; text-align: center; font-size: 13px; font-weight: 600;
      color: var(--primary-text-color, #1a1a1a);
      background: var(--secondary-background-color, #f3f4f6);
      padding: 8px 2px; border-radius: 8px;
      border: 1.5px solid transparent;
      transition: border-color 0.18s, background 0.18s, box-shadow 0.18s;
      -moz-appearance: textfield;
      font-variant-numeric: tabular-nums;
    }
    .control-group .value-input::-webkit-outer-spin-button,
    .control-group .value-input::-webkit-inner-spin-button { -webkit-appearance: none; }
    .control-group .value-input:hover  { border-color: var(--divider-color, #d1d5db); }
    .control-group .value-input:focus  {
      outline: none; border-color: var(--primary-color, #2563eb);
      background: var(--card-background-color, #fff);
      box-shadow: 0 0 0 3px color-mix(in srgb, var(--primary-color, #2563eb) 15%, transparent);
    }

    .actions { display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }
    .btn {
      --c: var(--battman-blue); --c-fill: var(--battman-blue-soft-bg);
      padding: 8px 14px; border: 1px solid var(--battman-border-neutral);
      border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer;
      transition: background 0.12s ease, border-color 0.12s ease, transform 0.08s ease;
      background: var(--c-fill, transparent); color: var(--c, var(--primary-text-color));
      display: inline-flex; align-items: center; gap: 5px;
    }
    .btn:disabled { opacity: 0.4; cursor: not-allowed; }
    @media (hover: hover) { .btn:hover:not(:disabled) { border-color: var(--c, var(--divider-color)); } }
    .btn:active:not(:disabled), .btn.pressed:not(:disabled) { background: color-mix(in srgb, var(--c) 32%, transparent); border-color: var(--c); transform: scale(0.96); }
    /* Save — green primary */
    .btn-save { --c: var(--battman-green); --c-fill: var(--battman-green-soft-bg); border-color: var(--battman-green-border-strong); font-weight: 700; }
    /* Presets — purple */
    .btn-preset, .btn-manage-presets { --c: var(--battman-purple); --c-fill: var(--battman-purple-soft-bg); }
    /* Periods — teal */
    .btn-copy, .btn-paste, .btn-export, .btn-import { --c: var(--battman-teal); --c-fill: var(--battman-teal-soft-bg); }
    /* Factory Defaults — blue misc */
    .btn-factory { --c: var(--battman-blue); --c-fill: var(--battman-blue-soft-bg); }
    /* Run Script — red */
    .btn-run-script { --c: var(--battman-red); --c-fill: var(--battman-red-soft-bg); }

    .auto-save {
      display: flex; align-items: center; gap: 8px; padding: 8px 12px;
      background: var(--secondary-background-color, #f3f4f6);
      border-radius: 6px; font-size: 13px; color: var(--primary-text-color, #1a1a1a);
    }
    .auto-save input[type="checkbox"] { width: 18px; height: 18px; cursor: pointer; accent-color: var(--primary-color, #2563eb); }

    .preset-menu { position: relative; display: inline-block; }
    .preset-dropdown {
      display: none; position: absolute; bottom: 100%; left: 0;
      background: var(--card-background-color, white);
      border: 1px solid var(--divider-color, #e5e7eb);
      border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      padding: 8px; margin-bottom: 8px; min-width: 200px; z-index: 1000;
    }
    .preset-dropdown.show { display: block; }
    .preset-option {
      padding: 8px 12px; cursor: pointer; border-radius: 6px;
      font-size: 13px; transition: background 0.2s;
      display: flex; justify-content: space-between; align-items: center;
    }
    .preset-option:hover { background: var(--secondary-background-color, #f3f4f6); }
    .preset-option .preset-name { font-weight: 600; color: var(--primary-text-color, #1a1a1a); }
    .preset-option .preset-status { font-size: 11px; color: var(--secondary-text-color, #666); }

    .modal {
      display: none; position: fixed; z-index: 2000;
      left: 0; top: 0; width: 100%; height: 100%;
      background-color: rgba(0,0,0,0.5); animation: fadeIn 0.2s;
    }
    .modal.show { display: flex; align-items: center; justify-content: center; }
    .modal-content {
      background: var(--card-background-color, white); padding: 24px;
      border-radius: 12px; max-width: 500px; width: 90%;
      box-shadow: 0 8px 24px rgba(0,0,0,0.2);
    }
    .modal-header { font-size: 20px; font-weight: 700; margin-bottom: 20px; color: var(--primary-text-color, #1a1a1a); }
    .preset-list { display: flex; flex-direction: column; gap: 12px; }
    .preset-item {
      display: flex; align-items: center; gap: 12px; padding: 12px;
      background: var(--secondary-background-color, #f3f4f6); border-radius: 8px;
    }
    .preset-item label { font-size: 12px; font-weight: 600; color: var(--secondary-text-color, #666); min-width: 70px; }
    .preset-item input[type="text"] {
      flex: 1; padding: 8px 12px; border: 1px solid var(--divider-color, #e5e7eb);
      border-radius: 6px; background: var(--card-background-color, white);
      color: var(--primary-text-color, #1a1a1a); font-size: 14px;
    }
    .preset-item .preset-info { font-size: 11px; color: var(--secondary-text-color, #666); min-width: 80px; text-align: right; }
    .modal-actions { display: flex; gap: 12px; margin-top: 20px; justify-content: flex-end; }

    .status { display: inline-block; padding: 6px 12px; border-radius: 6px; font-size: 13px; font-weight: 600; margin-left: 12px; }
    .status.success { background: rgba(22,163,74,0.2);  color: var(--success-color, #15803d); }
    .status.error   { background: rgba(239,68,68,0.2);  color: var(--error-color, #991b1b); }
    .status.info    { background: rgba(59,130,246,0.2); color: var(--info-color, #1e40af); }

    .info-box {
      background: var(--battman-surface-popup);
      border: 1px solid var(--battman-green);
      padding: 12px 14px; border-radius: 10px; margin-top: 24px;
      font-size: 13px; line-height: 1.6; color: var(--battman-text-bright);
    }
    .info-box strong { color: var(--primary-color, #1e40af); }
    .info-box code {
      background: var(--code-background-color, rgba(0,0,0,0.1));
      color: var(--primary-text-color, #1a1a1a);
      padding: 2px 6px; border-radius: 3px;
      font-size: 12px; font-family: inherit;
    }

    #import-file { display: none; }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

    @media (prefers-color-scheme: dark) {
      .container { background: var(--card-background-color, #1f2937); }
      .input-section { background: var(--secondary-background-color, #1e2736); border-color: #374151; }
      .control-group .value-input { background: var(--secondary-background-color, #374151); border-color: #4b5563; }
      .chart-container { background: var(--secondary-background-color, #111827); }
    }
  `;

const HTML = `<ha-card><div class="page">
  <div class="container">
    <h2 style="display:flex;align-items:center;gap:10px;"><img src="/battmanfiles/images/battman-money.webp" alt="Battman" style="height:44px;width:auto;flex:none;"><img src="/battmanfiles/images/price-curve-editor-line.webp" alt="Price Curve Editor" style="width:330px;max-width:100%;min-width:0;height:auto;flex:0 1 auto;"><span id="status"></span></h2>

    <div class="mode-toggle">
      <button class="mode-btn mode-btn-month active" data-on-click="switchEditMode('month', this)">Month</button>
      <button class="mode-btn mode-btn-season"       data-on-click="switchEditMode('season', this)">Season</button>
    </div>

    <div class="tabs">
      <button class="tab ctab" data-on-click="switchCurveType('sell', this)">Sell</button>
      <button class="tab ctab" data-on-click="switchCurveType('sell_high', this)">Sell High Consumption</button>
      <button class="tab ctab" data-on-click="switchCurveType('buy', this)">Buy</button>
      <button class="tab ctab" data-on-click="switchCurveType('buy_high', this)">Buy High Consumption</button>
      <div class="month-tabs" id="month-tabs">
        <button class="tab" data-on-click="switchPeriod('jan')" id="tab-jan">Jan</button>
        <button class="tab" data-on-click="switchPeriod('feb')" id="tab-feb">Feb</button>
        <button class="tab" data-on-click="switchPeriod('mar')" id="tab-mar">Mar</button>
        <button class="tab" data-on-click="switchPeriod('apr')" id="tab-apr">Apr</button>
        <button class="tab" data-on-click="switchPeriod('may')" id="tab-may">May</button>
        <button class="tab" data-on-click="switchPeriod('jun')" id="tab-jun">Jun</button>
        <button class="tab" data-on-click="switchPeriod('jul')" id="tab-jul">Jul</button>
        <button class="tab" data-on-click="switchPeriod('aug')" id="tab-aug">Aug</button>
        <button class="tab" data-on-click="switchPeriod('sep')" id="tab-sep">Sep</button>
        <button class="tab" data-on-click="switchPeriod('oct')" id="tab-oct">Oct</button>
        <button class="tab" data-on-click="switchPeriod('nov')" id="tab-nov">Nov</button>
        <button class="tab" data-on-click="switchPeriod('dec')" id="tab-dec">Dec</button>
      </div>
      <div class="season-tabs" id="season-tabs">
        <button class="tab" data-on-click="switchPeriod('summer')" id="tab-summer">Summer</button>
        <button class="tab" data-on-click="switchPeriod('autumn')" id="tab-autumn">Autumn</button>
        <button class="tab" data-on-click="switchPeriod('winter')" id="tab-winter">Winter</button>
        <button class="tab" data-on-click="switchPeriod('spring')" id="tab-spring">Spring</button>
      </div>
    </div>

    <div class="chart-controls">
      <label>
        <input type="checkbox" id="amber-toggle" checked data-on-change="toggleAmber()">
        <span id="amber-label" style="color:#f97316;font-weight:600;">Amber FIT</span>
      </label>
      <label>
        <input type="checkbox" id="show-hour-details" checked data-on-change="toggleHourDetails()">
        Show Hour Details
      </label>
      <label>
        <input type="checkbox" id="show-debug" data-on-change="toggleDebugger()">
        Show Debug
      </label>
    </div>


    <div class="chart-legend">
      <div class="legend-item">
        <div class="legend-line" id="leg-high-line" style="background:#10b981;"></div>
        <span id="leg-high">Preferred Sell</span>
      </div>
      <div class="legend-item">
        <div class="legend-line" id="leg-low-line" style="background:#f59e0b;"></div>
        <span id="leg-low">Low Sell</span>
      </div>
      <div class="legend-item">
        <div style="width:14px;height:0;border-top:2.5px solid #f97316;"></div>
        <div style="width:10px;height:0;border-top:2.5px dashed #f97316;margin-left:1px;"></div>
        <span id="leg-amber" style="margin-left:4px;color:#f97316;">Amber FIT actual / forecast</span>
      </div>
    </div>

    <!-- Hour Details panel — above chart, matching SOC editor -->
    <div id="hour-details-panel" style="background:var(--card-background-color,#1f2937);border:1px solid var(--divider-color,rgba(255,255,255,0.1));border-radius:8px;padding:10px 14px;margin:6px 0;">
      <div id="hour-details-content" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;min-height:60px;">
        <span style="color:#6b7280;font-size:13px;align-self:center;">Hover over the chart or an input to see hour details</span>
      </div>
    </div>

    <div class="chart-container">
      <canvas id="chart"></canvas>
    </div>

    <div class="input-grid">
      <div class="input-section">
        <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;color:#10b981;padding-bottom:10px;border-bottom:1px solid var(--divider-color,#e5e7eb);margin-bottom:10px;" id="high-label-text">PREFERRED SELL (¢/KWH)</div>
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
          <input type="number" id="set-all-high" step="1" placeholder="value in ¢"
            style="width:100px;padding:5px 8px;border-radius:5px;border:1.5px solid var(--divider-color,#e5e7eb);background:var(--card-background-color,#fff);color:var(--primary-text-color,#1a1a1a);font-size:12px;">
          <button class="btn" data-on-click="setAll('high')" title="Set all 24 hours to this value" style="--c:var(--battman-green);--c-fill:var(--battman-green-soft-bg);padding:5px 14px;font-size:12px;font-weight:700;">Set All</button>
        </div>
        <div class="controls" id="controls-high"></div>
      </div>
      <div class="input-section">
        <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;color:#f59e0b;padding-bottom:10px;border-bottom:1px solid var(--divider-color,#e5e7eb);margin-bottom:10px;" id="low-label-text">LOW SELL (¢/KWH)</div>
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
          <input type="number" id="set-all-low" step="1" placeholder="value in ¢"
            style="width:100px;padding:5px 8px;border-radius:5px;border:1.5px solid var(--divider-color,#e5e7eb);background:var(--card-background-color,#fff);color:var(--primary-text-color,#1a1a1a);font-size:12px;">
          <button class="btn" data-on-click="setAll('low')" title="Set all 24 hours to this value" style="--c:var(--battman-amber);--c-fill:var(--battman-amber-soft-bg);padding:5px 14px;font-size:12px;font-weight:700;">Set All</button>
          <label id="follow-label" title="" style="display:flex;align-items:center;gap:5px;cursor:pointer;font-size:11px;color:var(--secondary-text-color,#888);">
            <input type="checkbox" id="follow-toggle" checked data-on-change="updateFollowLabel()"
              style="width:13px;height:13px;cursor:pointer;accent-color:#f59e0b;">
            <span id="follow-label-text">Linked to Preferred Sell</span>
          </label>
        </div>
        <div class="controls" id="controls-low"></div>
      </div>
    </div>

    <div class="actions">
      <button class="btn btn-save" data-on-click="saveToHA()">Save</button>
      <div class="preset-menu">
        <button class="btn btn-preset" data-on-click="togglePresetMenu('save')">Save Preset ▼</button>
        <div class="preset-dropdown" id="save-preset-menu">
          <div class="preset-option" data-on-click="savePreset(1)"><span class="preset-name" id="save-preset-1-name">Preset 1</span><span class="preset-status" id="save-preset-1-status">Empty</span></div>
          <div class="preset-option" data-on-click="savePreset(2)"><span class="preset-name" id="save-preset-2-name">Preset 2</span><span class="preset-status" id="save-preset-2-status">Empty</span></div>
          <div class="preset-option" data-on-click="savePreset(3)"><span class="preset-name" id="save-preset-3-name">Preset 3</span><span class="preset-status" id="save-preset-3-status">Empty</span></div>
          <div class="preset-option" data-on-click="savePreset(4)"><span class="preset-name" id="save-preset-4-name">Preset 4</span><span class="preset-status" id="save-preset-4-status">Empty</span></div>
          <div class="preset-option" data-on-click="savePreset(5)"><span class="preset-name" id="save-preset-5-name">Preset 5</span><span class="preset-status" id="save-preset-5-status">Empty</span></div>
        </div>
      </div>
      <div class="preset-menu">
        <button class="btn btn-preset" data-on-click="togglePresetMenu('load')">Load Preset ▼</button>
        <div class="preset-dropdown" id="load-preset-menu">
          <div class="preset-option" data-on-click="loadPreset(1)" id="load-preset-1"><span class="preset-name" id="load-preset-1-name">Preset 1</span><span class="preset-status" id="load-preset-1-status">Empty</span></div>
          <div class="preset-option" data-on-click="loadPreset(2)" id="load-preset-2"><span class="preset-name" id="load-preset-2-name">Preset 2</span><span class="preset-status" id="load-preset-2-status">Empty</span></div>
          <div class="preset-option" data-on-click="loadPreset(3)" id="load-preset-3"><span class="preset-name" id="load-preset-3-name">Preset 3</span><span class="preset-status" id="load-preset-3-status">Empty</span></div>
          <div class="preset-option" data-on-click="loadPreset(4)" id="load-preset-4"><span class="preset-name" id="load-preset-4-name">Preset 4</span><span class="preset-status" id="load-preset-4-status">Empty</span></div>
          <div class="preset-option" data-on-click="loadPreset(5)" id="load-preset-5"><span class="preset-name" id="load-preset-5-name">Preset 5</span><span class="preset-status" id="load-preset-5-status">Empty</span></div>
        </div>
      </div>
      <button class="btn btn-manage-presets" data-on-click="openManagePresets()">Manage Presets</button>
      <button class="btn btn-copy"           data-on-click="copyPeriod()">Copy Period</button>
      <button class="btn btn-paste"          data-on-click="pastePeriod()" id="paste-btn" disabled>Paste Period</button>
      <button class="btn btn-export"         data-on-click="exportPeriod()">Export Period</button>
      <button class="btn btn-import"         data-on-click="openImport()">Import Period</button>
      <input type="file" id="import-file" accept=".json" data-on-change="importPeriod(event)">
      <button class="btn btn-factory"        data-on-click="loadFactoryDefaults()">Factory Defaults</button>
      <button class="btn btn-run-script"     data-on-click="runScript()">Run Script</button>
      <div class="auto-save">
        <input type="checkbox" id="auto-save" data-on-change="toggleAutoSave()">
        <label for="auto-save">Auto-save</label>
      </div>
    </div>


    <div id="debug-box" class="debug-box" style="display:none;">
      <button class="btn" data-on-click="clearDebugLog()" style="float:right;margin-top:-4px;padding:4px 10px;font-size:11px;background:var(--battman-surface-popup);border-color:var(--battman-border-neutral);color:var(--battman-text-muted);">Clear</button>
      <div id="debug-content"></div>
    </div>
    <div class="info-box">
      <strong>Currently Editing:</strong><br>
      <span id="edit-info">Loading…</span>
    </div>
  </div>
</div></ha-card>
<!-- Manage Presets Modal -->
    <div class="modal" id="manage-presets-modal">
      <div class="modal-content">
        <div class="modal-header">Manage Presets</div>
        <div class="preset-list">
          <div class="preset-item"><label>Preset 1:</label><input type="text" id="preset-1-name-input" placeholder="e.g., Hot Weather"><span class="preset-info" id="preset-1-info">Empty</span></div>
          <div class="preset-item"><label>Preset 2:</label><input type="text" id="preset-2-name-input" placeholder="e.g., Rainy Day"><span class="preset-info" id="preset-2-info">Empty</span></div>
          <div class="preset-item"><label>Preset 3:</label><input type="text" id="preset-3-name-input" placeholder="e.g., Regular Day"><span class="preset-info" id="preset-3-info">Empty</span></div>
          <div class="preset-item"><label>Preset 4:</label><input type="text" id="preset-4-name-input" placeholder="e.g., Weekend"><span class="preset-info" id="preset-4-info">Empty</span></div>
          <div class="preset-item"><label>Preset 5:</label><input type="text" id="preset-5-name-input" placeholder="e.g., Special Event"><span class="preset-info" id="preset-5-info">Empty</span></div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-save" data-on-click="savePresetNames()">Save Names</button>
          <button class="btn" style="background:var(--battman-surface-popup);border-color:var(--battman-border-neutral);color:var(--battman-text-muted);" data-on-click="closeManagePresets()">Close</button>
        </div>
      </div>
    </div>
`;

function pricyRun(card, root) {
  const $ = (id) => root.getElementById(id);
  const getHass = () => card.hass;
  // ── Constants ─────────────────────────────────────────────────────────────
  const MONTHS      = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'];
  const MONTH_NAMES = ['January','February','March','April','May','June','July','August','September','October','November','December'];
  const SEASON_MONTHS = { summer:['dec','jan','feb'], autumn:['mar','apr','may'], winter:['jun','jul','aug'], spring:['sep','oct','nov'] };
  const SEASON_NAMES  = { summer:'Summer (Dec–Feb)', autumn:'Autumn (Mar–May)', winter:'Winter (Jun–Aug)', spring:'Spring (Sep–Nov)' };

  const COLORS = {
    sell:      { low:'#f59e0b', high:'#10b981', fill:'rgba(16,185,129,0.12)'  },
    sell_high: { low:'#fb923c', high:'#a78bfa', fill:'rgba(167,139,250,0.12)' },
    buy:       { low:'#ef4444', high:'#3b82f6', fill:'rgba(59,130,246,0.12)'  },
    buy_high:  { low:'#f472b6', high:'#34d399', fill:'rgba(52,211,153,0.12)'  }
  };
  const TYPE_LABELS = {
    sell:      { low:'Low Sell',    high:'Preferred Sell' },
    sell_high: { low:'Low Sell',    high:'Preferred Sell' },
    buy:       { low:'Preferred Buy', high:'High Buy'     },
    buy_high:  { low:'Preferred Buy', high:'High Buy'     }
  };
  const TYPE_NAMES = {
    sell:'Sell (Normal)', sell_high:'Sell (High Consumption)',
    buy:'Buy (Normal)',   buy_high:'Buy (High Consumption)'
  };

  // today's Amber prices by hour (¢/kWh): actual up to now, then the forecast; null where Amber has none
  let AMBER_FIT = Array(24).fill(null);
  let AMBER_BUY = Array(24).fill(null);


  // ── Defaults ──────────────────────────────────────────────────────────────
  // Battman's factory curves (factory_curves.yaml), read from the curves sensor's `factory` attribute
  let FACTORY = null;
  const CURVE_TYPES = ['sell', 'sell_high', 'buy', 'buy_high'];
  const factoryFor = type => ({ low: [...FACTORY[type].low], high: [...FACTORY[type].high] });

  // ── Data ──────────────────────────────────────────────────────────────────
  const data = {};
  function factoryMonths(months) {
    months.forEach(m => { data[m] = {}; CURVE_TYPES.forEach(type => { data[m][type] = factoryFor(type); }); });
  }

  // ── State ─────────────────────────────────────────────────────────────────
  let editMode         = 'month';
  let currentPeriod    = MONTHS[new Date().getMonth()];
  let currentType      = 'sell';
  let clipboard        = null;
  let chart            = null;
  let autoSave         = false;
  let saveTimeout      = null;
  let showDebugBox     = false;
  let lastLoadedPreset = {};
  let followMode       = true;
  let modifiedPeriods  = {};
  let showHourDetails  = true;
  let _inputHoverHour  = null;

  // ── Helpers ───────────────────────────────────────────────────────────────
  const getMonths  = p => editMode === 'season' ? SEASON_MONTHS[p] : [p];
  const getCurve   = lh => [...data[getMonths(currentPeriod)[0]][currentType][lh]];
  const periodName = () => editMode === 'season' ? SEASON_NAMES[currentPeriod] : MONTH_NAMES[MONTHS.indexOf(currentPeriod)];
  const sign       = v => (v > 0 ? '+' : '') + v;

  function setCurveBand(lh, values) {
    getMonths(currentPeriod).forEach(m => { data[m][currentType][lh] = [...values]; });
  }

  // ── Hour Details Panel ────────────────────────────────────────────────────
  function toggleHourDetails() {
    showHourDetails = $('show-hour-details').checked;
    $('hour-details-panel').style.display = showHourDetails ? 'block' : 'none';
  }

  function updateHourDetailsPanel(hour) {
    if (!showHourDetails) return;
    const content = $('hour-details-content');
    if (hour === null || hour === undefined) {
      content.innerHTML = '<span style="color:#6b7280;font-size:13px;align-self:center;">Hover over the chart or an input to see hour details</span>';
      return;
    }

    // accent = the curve line colour (from COLORS, themed); value uses the text token
    function valueHtml(value, muted) {
      return value !== null && value !== undefined
        ? `<div class="hd-card-value">${sign(value)}<span class="unit">¢</span></div>`
        : `<div class="hd-card-value" style="opacity:0.35;">—</div>`;
    }
    function hdCard(label, value, accent) {
      return `<div class="hd-card" style="border-color:${accent}">
        <div class="hd-card-main">
          <div class="hd-card-label" style="color:${accent}">${label}</div>
          ${valueHtml(value)}
        </div>
      </div>`;
    }
    // first card: value on the left half, the hour standing out on the right
    function firstCard(label, value, accent, time) {
      return `<div class="hd-card hd-card-hour" style="border-color:${accent}">
        <div class="hd-thr-main">
          <div class="hd-card-label" style="color:${accent}">${label}</div>
          ${valueHtml(value)}
        </div>
        <div class="hd-thr-time">
          <div class="hd-thr-time-val">${time}</div>
          <div class="hd-thr-time-tag">Hour</div>
        </div>
      </div>`;
    }

    const c       = COLORS[currentType];
    const lbl     = TYPE_LABELS[currentType];
    const prefVal = getCurve(pKey())[hour];
    const secVal  = getCurve(sKey())[hour];
    const prefLbl = isBuyType() ? lbl.low  : lbl.high;
    const secLbl  = isBuyType() ? lbl.high : lbl.low;
    const prefCol = isBuyType() ? c.low    : c.high;
    const secCol  = isBuyType() ? c.high   : c.low;
    const isSell  = !isBuyType();
    const ambVal  = (isSell ? AMBER_FIT : AMBER_BUY)[hour];
    const amberLbl = isSell ? 'Amber FIT' : 'Amber Buy';

    let html = firstCard(prefLbl, prefVal, prefCol, hourLabel(hour));
    html += hdCard(secLbl, secVal, secCol);
    if (ambVal !== null && ambVal !== undefined) {
      html += hdCard(amberLbl, ambVal, 'var(--battman-orange)');
    }
    content.innerHTML = html;
  }

  // ───────────── Battman: entity map + startup checks (no fallbacks) ─────────────
  let M = null;                 // Battman entity map
  let CURVE_GAPS = [];
  let OPTIONAL_MISSING = [];
  const NEEDS = ['price_curves', 'price_curves_factory', 'price_curves_update_event', 'control_script', 'buy_price', 'feed_in_price',
                 'buy_forecast', 'feed_in_forecast', 'load_30m_avg', 'high_consumption'];
  const NEED_ENTITIES = ['price_curves', 'control_script', 'buy_price', 'feed_in_price', 'load_30m_avg', 'high_consumption'];
  // shown if missing, but the editor still works without them (they only add the forecast overlay)
  const OPTIONAL_ENTITIES = { buy_forecast: 'buy price forecast', feed_in_forecast: 'feed-in price forecast' };
  const THEME_VARS = ['--battman-amber', '--battman-amber-border-strong', '--battman-amber-soft-bg', '--battman-blue', '--battman-blue-border-strong', '--battman-blue-soft-bg', '--battman-border-neutral', '--battman-green', '--battman-green-border-strong', '--battman-green-soft-bg', '--battman-orange', '--battman-pink', '--battman-purple', '--battman-purple-soft-bg', '--battman-red', '--battman-red-soft-bg', '--battman-surface-card', '--battman-surface-popup', '--battman-teal', '--battman-teal-soft-bg', '--battman-text-bright', '--battman-text-dim', '--battman-text-muted'];
  let Chart = null;             // Chart.js (shipped with Battman), loaded at start

  // what stops the editor from starting, or null
  async function startupProblem() {
    try { M = await battmanMap(card.hass, NEEDS); } catch (e) { return e.message; }
    const problem = missingThemeVars(card, THEME_VARS) || missingEntities(card.hass, M, NEED_ENTITIES);
    if (problem) return problem;
    const h = card.hass;
    const fac = h.states[M.price_curves_factory];
    FACTORY = fac && fac.attributes.factory;
    if (!FACTORY || CURVE_TYPES.some(t => !FACTORY[t] || [FACTORY[t].low, FACTORY[t].high].some(a => !Array.isArray(a) || a.length !== 24)))
      return 'No factory curves: ' + M.price_curves_factory + ' has no factory attribute (are Battman\'s packages loaded? see Repairs).';
    OPTIONAL_MISSING = Object.keys(OPTIONAL_ENTITIES).filter(k => !h.states[M[k]])
      .map(k => 'No ' + OPTIONAL_ENTITIES[k] + ': ' + k + ' → ' + M[k] + ' not found');
    try { Chart = await loadChartJs(); } catch (e) { return 'Chart library unavailable: ' + e.message; }
    return null;
  }
  const showNote = (msg) => noteIn(root.querySelector('.container'), msg);
  const { toggle: toggleDebugger, log: debugLog, clear: clearDebugLog } = debugBox($);
  const togglePresetMenu = presetMenus($);
  function openImport() { $('import-file').click(); }

  // Canvas/Chart.js can't resolve CSS var() — read the resolved value in JS.
  // Battman colours are checked at startup, so no fallback for them here.
  function gc(name, fallback) {
    const v = cssVar(card, name);
    if (v) return v;
    if (fallback === undefined) throw new Error('Theme colour ' + name + ' not found');
    return fallback;
  }
  // Repopulate the chart COLORS from the live theme (mutates the const object).
  function buildColors() {
    COLORS.sell      = { low: gc('--battman-amber'),  high: gc('--battman-green'),  fill: gc('--battman-green-soft-bg') };
    COLORS.sell_high = { low: gc('--battman-orange'), high: gc('--battman-purple'), fill: gc('--battman-purple-soft-bg') };
    COLORS.buy       = { low: gc('--battman-red'),    high: gc('--battman-blue'),   fill: gc('--battman-blue-soft-bg') };
    COLORS.buy_high  = { low: gc('--battman-pink'),   high: gc('--battman-teal'),   fill: gc('--battman-teal-soft-bg') };
  }


  // ── Amber ─────────────────────────────────────────────────────────────────
  function toggleAmber() {
    const show = $('amber-toggle').checked;
    chart.data.datasets.filter(d => d.label.startsWith('Amber')).forEach(ds => { ds.hidden = !show; });
    chart.update();
  }

  function splitAtHour(arr, h) {
    return {
      actual:   arr.map((v, i) => i <= h ? v : null),
      forecast: arr.map((v, i) => i >= h ? v : null)
    };
  }

  function updateAmberDatasets() {
    const h = new Date().getHours();
    const arr = (currentType === 'sell' || currentType === 'sell_high') ? AMBER_FIT : AMBER_BUY;
    const { actual, forecast } = splitAtHour(arr, h);
    chart.data.datasets[3].data = actual;
    chart.data.datasets[4].data = forecast;
  }

  async function loadAmberHistory() {
    const hass = getHass();
    try {
      const now         = new Date();
      const midnight    = new Date(now); midnight.setHours(0,0,0,0);
      const currentHour = now.getHours();
      const histResult  = await hass.callWS({
        type: 'history/history_during_period',
        start_time: midnight.toISOString(), end_time: now.toISOString(),
        entity_ids: [M.feed_in_price, M.buy_price],
        minimal_response: true, no_attributes: true
      });
      function toHourlyAvg(history, label) {
        if (!history || !history.length) { debugLog(`⚠️ ${label}: no history`); return Array(24).fill(null); }
        const buckets = Array.from({length:24}, () => []);
        history.forEach(s => {
          const v = parseFloat(s.s); if (isNaN(v)) return;
          const cents = Math.abs(v) < 5 ? v * 100 : v;
          buckets[new Date(s.lu * 1000).getHours()].push(cents);
        });
        return buckets.map(b => b.length ? Math.round(b.reduce((a,c)=>a+c,0)/b.length) : null);
      }
      function forecastSensorToHourly(entityId, label, negateFIT = false) {
        const state = hass.states[entityId];
        if (!state) { debugLog(`⚠️ ${label}: not found`); return Array(24).fill(null); }
        const attrs = state.attributes || {};
        const fcs = attrs.Forecasts ?? attrs.forecasts ?? attrs.forecast ?? null;
        if (!Array.isArray(fcs) || fcs.length === 0) { debugLog(`⚠️ ${label}: no forecast array`); return Array(24).fill(null); }
        const buckets = Array.from({length:24}, () => []);
        fcs.forEach(f => {
          const raw = parseFloat(f.per_kwh ?? f.spot_per_kwh ?? f.value);
          if (isNaN(raw)) return;
          let v = Math.abs(raw) < 5 ? raw * 100 : raw;
          if (negateFIT) v = -v;
          let h = f.start_time_time ? parseInt(f.start_time_time.split(':')[0]) : new Date(f.start_time ?? f.startTime ?? f.start).getHours();
          if (h >= 0 && h < 24) buckets[h].push(v);
        });
        return buckets.map(b => b.length ? Math.round(b.reduce((a,c)=>a+c,0)/b.length) : null);
      }
      function stitch(actual, forecast) {
        return Array.from({length:24}, (_,h) => h <= currentHour ? (actual[h] ?? forecast[h] ?? null) : (forecast[h] ?? null));
      }
      function fillNulls(arr) {
        return arr.map((v, i, a) => {
          if (v !== null) return v;
          const prev = a.slice(0,i).reverse().find(x=>x!==null) ?? null;
          const next = a.slice(i+1).find(x=>x!==null) ?? null;
          if (prev === null || next === null) return null;
          return Math.round((prev+next)/2);
        });
      }
      const fitActual   = toHourlyAvg(histResult[M.feed_in_price], 'FIT');
      const buyActual   = toHourlyAvg(histResult[M.buy_price], 'Buy');
      const fitForecast = forecastSensorToHourly(M.feed_in_forecast, 'FIT forecast', true);
      const buyForecast = forecastSensorToHourly(M.buy_forecast, 'Buy forecast', false);
      const stitchedFIT = stitch(fitActual, fitForecast);
      const stitchedBUY = stitch(buyActual, buyForecast);
      AMBER_FIT = fillNulls(stitchedFIT);
      AMBER_BUY = fillNulls(stitchedBUY);
      const hours = AMBER_FIT.filter(v => v !== null).length;
      if (!hours) { showNote('No Amber prices for today (price history and forecast are empty): no Amber overlay'); return false; }
      debugLog(`✅ Amber loaded: ${hours} hours (actual 0–${currentHour}h, then forecast)`);
      return true;
    } catch(e) { showNote('Amber prices unavailable (' + e.message + '): no Amber overlay'); return false; }
  }

  // ── HA load/save ──────────────────────────────────────────────────────────
  async function loadFromHA() {
    factoryMonths(MONTHS);   // months or curves missing from the sensor show the factory curves (and say so)
    const hass = getHass();
    try {
      const entity = hass.states[M.price_curves];
      if (!entity?.attributes?.curves) { debugLog('❌ Entity or curves not found'); return false; }
      const curves = entity.attributes.curves;
      MONTHS.forEach(m => {
        if (!curves[m]) { CURVE_GAPS.push(m); return; }
        ['sell','sell_high','buy','buy_high'].forEach(type => {
          const c = curves[m][type];
          if (!c || !Array.isArray(c.low) || !Array.isArray(c.high)) { CURVE_GAPS.push(m + '.' + type); return; }
          data[m][type].low  = [...c.low];
          data[m][type].high = [...c.high];
        });
      });
      debugLog('✅ Curves loaded from sensor');
      const pt = entity.attributes.preset_tracking || {};
      Object.keys(pt).forEach(key => {
        if (pt[key].preset) { lastLoadedPreset[key] = pt[key].preset; modifiedPeriods[key] = pt[key].modified || false; }
      });
      return true;
    } catch(e) { debugLog(`❌ Load error: ${e.message}`); return false; }
  }


  async function saveToHA(silent = false) {
    const hass = getHass();
    if (!silent) showStatus('Saving…', 'info');
    try {
      const curvesData = {};
      MONTHS.forEach(m => {
        curvesData[m] = {
          sell:      { low:[...data[m].sell.low],      high:[...data[m].sell.high]      },
          sell_high: { low:[...data[m].sell_high.low], high:[...data[m].sell_high.high] },
          buy:       { low:[...data[m].buy.low],        high:[...data[m].buy.high]       },
          buy_high:  { low:[...data[m].buy_high.low],   high:[...data[m].buy_high.high]  }
        };
      });
      debugLog(`📤 Firing event (${JSON.stringify(curvesData).length} bytes)`);
      await hass.callWS({ type:'fire_event', event_type:M.price_curves_update_event, event_data:{ curves: curvesData } });
      if (!(await savedIn(getHass, M.price_curves, 'curves', curvesData))) { showStatus(NOT_SAVED, 'error'); debugLog('❌ Not saved'); return; }
      if (!silent) { showStatus('💾 Saved!', 'success'); debugLog('✅ Saved'); }
    } catch(e) { showStatus('Save failed', 'error'); debugLog(`❌ Save error: ${e.message}`); }
  }

  async function savePresetTracking() {
    const hass = getHass();
    try {
      const pt = {};
      Object.keys(lastLoadedPreset).forEach(k => { pt[k] = { preset: lastLoadedPreset[k], modified: modifiedPeriods[k] || false }; });
      await hass.callWS({ type:'fire_event', event_type:M.price_curves_update_event, event_data:{ preset_tracking: pt } });
    } catch(e) { debugLog(`❌ Preset tracking error: ${e.message}`); }
  }

  async function loadPresetInfo() {
    const hass = getHass();
    try {
      const entity = hass.states[M.price_curves];
      if (!entity) return;
      const presets = entity.attributes.presets || {};
      const presetNames = entity.attributes.preset_names || {};
      for (let i = 1; i <= 5; i++) {
        const name = presetNames[i] || `Preset ${i}`;
        const hasData = !!(presets[i] && Object.keys(presets[i]).length > 0);
        const status = hasData ? '✓ Saved' : 'Empty';
        ['save','load'].forEach(t => {
          $(`${t}-preset-${i}-name`).textContent   = name;
          $(`${t}-preset-${i}-status`).textContent = status;
        });
        const loadOpt = $(`load-preset-${i}`);
        if (loadOpt) { loadOpt.style.opacity = hasData ? '1' : '0.5'; loadOpt.style.cursor = hasData ? 'pointer' : 'not-allowed'; }
        $(`preset-${i}-name-input`).value = name;
        $(`preset-${i}-info`).textContent = hasData ? '✓ Has Data' : 'Empty';
      }
    } catch(e) { debugLog(`❌ loadPresetInfo: ${e.message}`); }
  }


  async function savePreset(num) {
    const hass = getHass();
    $('save-preset-menu').classList.remove('show');
    const presetName = $(`save-preset-${num}-name`).textContent;
    if (!confirm(`Save current price curves for "${periodName()}" to "${presetName}"?`)) return;
    try {
      const entity = hass.states[M.price_curves];
      const presets = { ...(entity?.attributes?.presets || {}) };
      const m = getMonths(currentPeriod)[0];
      presets[num] = {
        sell:      { low:[...data[m].sell.low],      high:[...data[m].sell.high]      },
        sell_high: { low:[...data[m].sell_high.low], high:[...data[m].sell_high.high] },
        buy:       { low:[...data[m].buy.low],        high:[...data[m].buy.high]       },
        buy_high:  { low:[...data[m].buy_high.low],   high:[...data[m].buy_high.high]  }
      };
      showStatus('Saving…', 'info');
      await hass.callWS({ type:'fire_event', event_type:M.price_curves_update_event, event_data:{ presets } });
      if (!(await savedIn(getHass, M.price_curves, 'presets', { [num]: presets[num] }))) { showStatus(NOT_SAVED, 'error'); return; }
      showStatus(`Saved to ${presetName}!`, 'success');
      loadPresetInfo();
    } catch(e) { showStatus('Save failed', 'error'); }
  }

  async function loadPreset(num) {
    const hass = getHass();
    $('load-preset-menu').classList.remove('show');
    try {
      const entity = hass.states[M.price_curves];
      const presets = entity?.attributes?.presets || {};
      const preset  = presets[num];
      if (!preset) { showStatus('Preset is empty', 'error'); return; }
      const presetName = $(`load-preset-${num}-name`).textContent;
      if (!confirm(`Load "${presetName}" to "${periodName()}"?`)) return;
      getMonths(currentPeriod).forEach(m => {
        ['sell','sell_high','buy','buy_high'].forEach(type => {
          if (preset[type]) {
            data[m][type].low  = [...(preset[type].low  || factoryFor(type).low)];
            data[m][type].high = [...(preset[type].high || factoryFor(type).high)];
          }
        });
      });
      const presetKey = editMode === 'season' ? `season_${currentPeriod}` : `month_${currentPeriod}`;
      lastLoadedPreset[presetKey] = presetName; delete modifiedPeriods[presetKey];
      updateChart(); renderAll(); updateDisplay();
      showStatus(`Loaded ${presetName}!`, 'success');
      await savePresetTracking();
    } catch(e) { showStatus('Load failed', 'error'); }
  }

  function openManagePresets()  { loadPresetInfo(); $('manage-presets-modal').classList.add('show'); }
  function closeManagePresets() { $('manage-presets-modal').classList.remove('show'); }

  async function savePresetNames() {
    const hass = getHass();
    try {
      const presetNames = {};
      for (let i = 1; i <= 5; i++) { presetNames[i] = $(`preset-${i}-name-input`).value || `Preset ${i}`; }
      await hass.callWS({ type:'fire_event', event_type:M.price_curves_update_event, event_data:{ preset_names: presetNames } });
      if (!(await savedIn(getHass, M.price_curves, 'preset_names', presetNames))) { showStatus(NOT_SAVED, 'error'); return; }
      showStatus('Preset names saved!', 'success');
      await loadPresetInfo(); closeManagePresets();
    } catch(e) { showStatus('Save failed', 'error'); }
  }

  async function loadFactoryDefaults() {
    if (!confirm(`Load factory defaults for ${periodName()}?\n\nThis resets all 4 curve types.`)) return;
    getMonths(currentPeriod).forEach(m => {
      CURVE_TYPES.forEach(type => { data[m][type] = factoryFor(type); });
    });
    const presetKey = editMode === 'season' ? `season_${currentPeriod}` : `month_${currentPeriod}`;
    delete lastLoadedPreset[presetKey]; delete modifiedPeriods[presetKey];
    updateChart(); renderAll(); updateDisplay();
    showStatus('Factory defaults loaded', 'success');
    await savePresetTracking();
  }

  function copyPeriod() {
    const m = getMonths(currentPeriod)[0];
    clipboard = {
      periodName: periodName(),
      sell:      { low:[...data[m].sell.low],      high:[...data[m].sell.high]      },
      sell_high: { low:[...data[m].sell_high.low], high:[...data[m].sell_high.high] },
      buy:       { low:[...data[m].buy.low],        high:[...data[m].buy.high]       },
      buy_high:  { low:[...data[m].buy_high.low],   high:[...data[m].buy_high.high]  }
    };
    $('paste-btn').disabled = false;
    showStatus(`📋 Copied: ${periodName()} (all types)`, 'success');
    updateDisplay();
  }

  function pastePeriod() {
    if (!clipboard) return;
    if (!confirm(`Paste all curve types from "${clipboard.periodName}" to "${periodName()}"?`)) return;
    getMonths(currentPeriod).forEach(m => {
      ['sell','sell_high','buy','buy_high'].forEach(type => {
        data[m][type].low  = [...clipboard[type].low];
        data[m][type].high = [...clipboard[type].high];
      });
    });
    const presetKey = editMode === 'season' ? `season_${currentPeriod}` : `month_${currentPeriod}`;
    delete lastLoadedPreset[presetKey]; delete modifiedPeriods[presetKey];
    updateChart(); renderAll(); updateDisplay();
    showStatus(`📌 Pasted all types to ${periodName()}`, 'success');
    savePresetTracking();
  }

  function exportPeriod() {
    const m = getMonths(currentPeriod)[0];
    const exportData = {
      editor: 'price-curve-editor-v34', mode: editMode, period: currentPeriod,
      periodName: periodName(), exported: new Date().toISOString(),
      data: {
        sell:      { low:[...data[m].sell.low],      high:[...data[m].sell.high]      },
        sell_high: { low:[...data[m].sell_high.low], high:[...data[m].sell_high.high] },
        buy:       { low:[...data[m].buy.low],        high:[...data[m].buy.high]       },
        buy_high:  { low:[...data[m].buy_high.low],   high:[...data[m].buy_high.high]  }
      }
    };
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type:'application/json' });
    const a = Object.assign(document.createElement('a'), {
      href: URL.createObjectURL(blob),
      download: `price_curves_${currentPeriod}_${new Date().toISOString().split('T')[0]}.json`
    });
    root.appendChild(a); a.click(); a.remove();
    showStatus(`📤 Exported: ${periodName()}`, 'success');
  }

  function importPeriod(event) {
    const file = event.target.files[0]; if (!file) return;
    const reader = new FileReader();
    reader.onload = e => {
      try {
        const imp = JSON.parse(e.target.result);
        if (!imp.data?.sell || !imp.data?.buy) { showStatus('Invalid file format', 'error'); return; }
        if (!confirm(`Import from "${imp.periodName || 'Unknown'}" to "${periodName()}"?`)) return;
        getMonths(currentPeriod).forEach(m => {
          ['sell','sell_high','buy','buy_high'].forEach(type => {
            if (imp.data[type]) {
              data[m][type].low  = [...(imp.data[type].low  || factoryFor(type).low)];
              data[m][type].high = [...(imp.data[type].high || factoryFor(type).high)];
            }
          });
        });
        const presetKey = editMode === 'season' ? `season_${currentPeriod}` : `month_${currentPeriod}`;
        delete lastLoadedPreset[presetKey]; delete modifiedPeriods[presetKey];
        updateChart(); renderAll(); updateDisplay();
        showStatus(`📥 Imported from ${imp.periodName || 'file'}`, 'success');
        savePresetTracking();
      } catch(err) { showStatus('Import failed: ' + err.message, 'error'); }
    };
    reader.readAsText(file);
    event.target.value = '';
  }

  async function runScript() {
    const hass = getHass();
    try {
      showStatus('Running script…', 'info');
      await hass.callService('script', M.control_script.split('.').slice(1).join('.'), {});
      showStatus('✅ Script executed', 'success');
    } catch(e) { showStatus('Script failed', 'error'); }
  }

  function toggleAutoSave() {
    autoSave = $('auto-save').checked;
    if (autoSave) showStatus('Auto-save enabled', 'info');
  }

  // ── Canvas plugin: vertical column when hovering an input box ─────────────
  const inputHoverColumnPlugin = {
    id: 'inputHoverColumn',
    afterDraw(chartInst) {
      if (_inputHoverHour === null) return;
      const meta = chartInst.getDatasetMeta(0);
      if (!meta || !meta.data[_inputHoverHour]) return;
      const pt  = meta.data[_inputHoverHour];
      const { top, bottom, left, right } = chartInst.chartArea;
      const ctx = chartInst.ctx;
      const barW = (right - left) / 24;
      ctx.save();
      ctx.fillStyle = 'rgba(59,130,246,0.07)';
      ctx.fillRect(pt.x - barW / 2, top, barW, bottom - top);
      ctx.strokeStyle = 'rgba(59,130,246,0.28)';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 3]);
      ctx.beginPath(); ctx.moveTo(pt.x, top); ctx.lineTo(pt.x, bottom); ctx.stroke();
      ctx.restore();
    }
  };

  // ── Chart init ────────────────────────────────────────────────────────────
  function initChart() {
    chart = new Chart($('chart').getContext('2d'), {
      type: 'line',
      plugins: [inputHoverColumnPlugin],
      data: {
        labels: Array.from({length:24}, (_,i) => hourLabel(i)),
        datasets: [
          { label:'High Price',     data:getCurve('high'), borderColor:COLORS.sell.high, backgroundColor:COLORS.sell.fill, borderWidth:2.5, tension:0.4, pointRadius:3, pointHoverRadius:5, fill:'+1', order:2 },
          { label:'Low Price',      data:getCurve('low'),  borderColor:COLORS.sell.low,  backgroundColor:'transparent',    borderWidth:2.5, tension:0.4, pointRadius:3, pointHoverRadius:5, fill:false, order:3 },
          { label:'Zero',           data:Array(24).fill(0), borderColor:'rgba(128,128,128,0.2)', borderWidth:1, pointRadius:0, borderDash:[3,3], order:5 },
          { label:'Amber Actual',   data:Array(24).fill(null), borderColor:'#f97316', borderWidth:2, borderDash:[],    tension:0.5, pointRadius:2, pointHoverRadius:5, fill:false, order:1 },
          { label:'Amber Forecast', data:Array(24).fill(null), borderColor:'#f97316', borderWidth:2, borderDash:[6,3], tension:0.5, pointRadius:2, pointHoverRadius:5, fill:false, order:1 }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        interaction: { mode:'index', intersect:false },
        onHover: function(event, elements) {
          root.querySelectorAll('.value-input.chart-hover').forEach(el => el.classList.remove('chart-hover'));
          if (elements && elements.length > 0) {
            const hour = elements[0].index;
            const hi = $(`val-high-${hour}`);
            const lo = $(`val-low-${hour}`);
            if (hi) hi.classList.add('chart-hover');
            if (lo) lo.classList.add('chart-hover');
            $('chart').style.cursor = 'pointer';
            updateHourDetailsPanel(hour);
          } else {
            $('chart').style.cursor = '';
            updateHourDetailsPanel(new Date().getHours());
          }
        },
        onClick: function(event, elements) {
          if (!elements || elements.length === 0) return;
          const hour = elements[0].index;
          ['high','low'].forEach(lh => {
            const inp = $(`val-${lh}-${hour}`);
            if (!inp) return;
            inp.classList.remove('chart-click');
            void inp.offsetWidth;
            inp.classList.add('chart-click');
            setTimeout(() => inp.classList.remove('chart-click'), 1200);
          });
          const target = $(`val-high-${hour}`);
          if (target) target.scrollIntoView({ behavior:'smooth', block:'nearest' });
        },
        plugins: {
          legend: { display:false },
          tooltip: { enabled: false }
        },
        scales: {
          y: { title: { display:true, text:'¢/kWh', font:{size:14, weight:'bold'} }, ticks: { callback: v => (v>=0?'+':'')+v+'¢' } },
          x: { title: { display:true, text:'Hour of Day', font:{size:14, weight:'bold'} } }
        }
      }
    });
  }

  function updateChart() {
    const c = COLORS[currentType];
    chart.data.datasets[0].data = getCurve(pKey());
    chart.data.datasets[0].borderColor = isBuyType() ? c.low : c.high;
    chart.data.datasets[0].backgroundColor = c.fill;
    chart.data.datasets[1].data = getCurve(sKey());
    chart.data.datasets[1].borderColor = isBuyType() ? c.high : c.low;
    updateAmberDatasets();
    chart.update();
  }

  // ── Controls render ───────────────────────────────────────────────────────
  const isBuyType  = () => currentType === 'buy' || currentType === 'buy_high';
  const pKey = () => isBuyType() ? 'low'  : 'high'; // preferred panel data key
  const sKey = () => isBuyType() ? 'high' : 'low';  // secondary panel data key

  function renderAll() { renderBand(pKey(), 'high'); renderBand(sKey(), 'low'); }

  function renderBand(dataKey, panelId) {
    const curve = getCurve(dataKey);
    const el    = $('controls-' + panelId);
    el.innerHTML = curve.map((val, h) => `
      <div class="control-group">
        <label>${hourLabel(h)}</label>
        <input type="number" step="1" value="${val}"
               class="value-input" id="val-${panelId}-${h}"
               data-on-input="updateValue('${panelId}', ${h}, this.value)"
               data-on-mouseenter="onInputHover(${h})"
               data-on-mouseleave="onInputLeave()">
      </div>`).join('');
  }

  function onInputHover(hour) {
    _inputHoverHour = hour;
    chart.update('none');
    updateHourDetailsPanel(hour);
  }

  function onInputLeave() {
    _inputHoverHour = null;
    chart.update('none');
    updateHourDetailsPanel(new Date().getHours());
  }

  function updateValue(panelId, hour, raw) {
    let v = parseInt(raw);
    if (isNaN(v)) v = 0;
    const dk  = panelId === 'high' ? pKey() : sKey(); // actual data key
    const sdk = panelId === 'high' ? sKey() : pKey(); // secondary data key
    // Follow: if editing the preferred (left) panel, drag secondary along on equal hours
    if (panelId === 'high' && followMode && $('follow-toggle')?.checked) {
      const oldPref = getCurve(dk)[hour];
      const oldSec  = getCurve(sdk)[hour];
      if (oldSec === oldPref) {
        const secCurve = [...getCurve(sdk)];
        secCurve[hour] = v;
        setCurveBand(sdk, secCurve);
        const secInput = $(`val-low-${hour}`);
        if (secInput) secInput.value = v;
        chart.data.datasets[1].data = getCurve(sdk);
      }
    }
    const curve = [...getCurve(dk)];
    curve[hour] = v;
    setCurveBand(dk, curve);
    $(`val-${panelId}-${hour}`).value = v;
    chart.data.datasets[panelId === 'high' ? 0 : 1].data = getCurve(dk);
    chart.update('none');
    const presetKey = editMode === 'season' ? `season_${currentPeriod}` : `month_${currentPeriod}`;
    modifiedPeriods[presetKey] = true;
    updateDisplay();
    if (lastLoadedPreset[presetKey]) savePresetTracking();
    if (autoSave) { clearTimeout(saveTimeout); saveTimeout = setTimeout(() => saveToHA(true), 1000); }
  }

  function updateFollowLabel() {
    const checked = $('follow-toggle')?.checked;
    const span = $('follow-label-text');
    if (!span) return;
    const isSell = currentType === 'sell' || currentType === 'sell_high';
    const linkedTo = isSell ? 'Preferred Sell' : 'Preferred Buy';
    span.textContent = checked ? `Linked to ${linkedTo}` : 'Unlinked';
  }

  function setAll(panelId) {
    const inputEl = $('set-all-' + panelId);
    const v = parseInt(inputEl.value);
    if (isNaN(v)) { inputEl.focus(); return; }
    const dk  = panelId === 'high' ? pKey() : sKey();
    const sdk = panelId === 'high' ? sKey() : pKey();
    if (panelId === 'high' && $('follow-toggle')?.checked) {
      const prefCurve = getCurve(dk);
      const secCurve  = [...getCurve(sdk)];
      for (let h = 0; h < 24; h++) { if (secCurve[h] === prefCurve[h]) secCurve[h] = v; }
      setCurveBand(sdk, secCurve);
      renderBand(sdk, 'low');
      chart.data.datasets[1].data = getCurve(sdk);
    }
    const flat = Array(24).fill(v);
    setCurveBand(dk, flat);
    renderBand(dk, panelId);
    chart.data.datasets[panelId === 'high' ? 0 : 1].data = getCurve(dk);
    chart.update('none');
    inputEl.value = '';
    const presetKey = editMode === 'season' ? `season_${currentPeriod}` : `month_${currentPeriod}`;
    modifiedPeriods[presetKey] = true;
    updateDisplay();
    if (lastLoadedPreset[presetKey]) savePresetTracking();
    if (autoSave) { clearTimeout(saveTimeout); saveTimeout = setTimeout(() => saveToHA(true), 1000); }
    const lbl = TYPE_LABELS[currentType];
    showStatus(`Set all ${panelId === 'high' ? (isBuyType() ? lbl.low : lbl.high) : (isBuyType() ? lbl.high : lbl.low)} to ${v}¢`, 'success');
  }

  // ── Switching ─────────────────────────────────────────────────────────────
  function applyTypeUI(type) {
    const c   = COLORS[type];
    const lbl = TYPE_LABELS[type];
    const isBuy = type === 'buy' || type === 'buy_high';
    const prefLbl = isBuy ? lbl.low  : lbl.high;
    const secLbl  = isBuy ? lbl.high : lbl.low;
    const prefCol = isBuy ? c.low    : c.high;
    const secCol  = isBuy ? c.high   : c.low;
    // Chart legend: dataset 0 = preferred (left), dataset 1 = secondary (right)
    $('leg-high-line').style.background = prefCol;
    $('leg-low-line').style.background  = secCol;
    $('leg-high').textContent = prefLbl;
    $('leg-low').textContent  = secLbl;
    // Left panel header
    $('high-label-text').style.color = prefCol;
    $('high-label-text').textContent = prefLbl.toUpperCase() + ' (¢/KWH)';
    // Right panel header
    $('low-label-text').style.color  = secCol;
    $('low-label-text').textContent  = secLbl.toUpperCase()  + ' (¢/KWH)';
    const lowBtn  = root.querySelector('#controls-low')?.closest('.input-section')?.querySelector('button');
    const highBtn = root.querySelector('#controls-high')?.closest('.input-section')?.querySelector('button');
    // Wash look (matches the other .btn buttons) but tinted to the current
    // curve colour: coloured text + a faint fill, not a solid background.
    if (highBtn) { highBtn.style.background = ''; highBtn.style.setProperty('--c', prefCol); highBtn.style.setProperty('--c-fill', 'color-mix(in srgb, ' + prefCol + ' 14%, transparent)'); }
    if (lowBtn)  { lowBtn.style.background  = ''; lowBtn.style.setProperty('--c', secCol);  lowBtn.style.setProperty('--c-fill', 'color-mix(in srgb, ' + secCol + ' 14%, transparent)'); }
    const isSell = type === 'sell' || type === 'sell_high';
    const followLabel = $('follow-label');
    if (followLabel) followLabel.style.display = 'flex';
    const followLabelTitle = isSell
      ? 'When linked: editing Preferred Sell also updates Low Sell for any hour where both values are currently equal.'
      : 'When linked: editing Preferred Buy also updates High Buy for any hour where both values are currently equal.';
    if (followLabel) followLabel.title = followLabelTitle;
    updateFollowLabel();
    $('amber-label').textContent = isSell ? 'Amber FIT' : 'Amber Buy Price';
    const legAmber = $('leg-amber');
    if (legAmber) legAmber.textContent = isSell ? 'Amber FIT actual / forecast' : 'Amber Buy Price actual / forecast';
  }

  function switchCurveType(type, btn) {
    currentType = type;
    root.querySelectorAll('.tabs > .tab').forEach(t =>
      t.classList.remove('sell-active','sell-high-active','buy-active','buy-high-active','active')
    );
    btn.classList.add(type.replace('_','-') + '-active');
    { const CC={sell:'--battman-green',sell_high:'--battman-purple',buy:'--battman-blue',buy_high:'--battman-teal'};
      card.style.setProperty('--active-curve', gc(CC[type]||'--battman-blue')); }
    applyTypeUI(type);
    updateChart(); renderAll(); updateDisplay();
    updateHourDetailsPanel(new Date().getHours());
  }

  function switchPeriod(period) {
    currentPeriod = period;
    const tabGroup = editMode === 'season' ? 'season-tabs' : 'month-tabs';
    root.querySelectorAll(`#${tabGroup} .tab`).forEach(t => t.classList.remove('active'));
    $('tab-' + period).classList.add('active');
    updateChart(); renderAll(); updateDisplay();
    updateHourDetailsPanel(new Date().getHours());
  }

  function switchEditMode(mode, btn) {
    if (mode === 'season' && editMode === 'month') {
      if (!confirm('⚠️ Switching to Season mode will group months together.\n\nAll months in a season will share the same values.\nSeason curves will be initialised from the first month of each season.\n\nContinue?')) return;
      Object.entries(SEASON_MONTHS).forEach(([s, mths]) => {
        const src = mths[0];
        mths.forEach(m => {
          ['sell','sell_high','buy','buy_high'].forEach(type => {
            data[m][type] = { low:[...data[src][type].low], high:[...data[src][type].high] };
          });
        });
      });
      const cm = MONTHS[new Date().getMonth()];
      for (const [s, mths] of Object.entries(SEASON_MONTHS)) {
        if (mths.includes(cm)) { currentPeriod = s; break; }
      }
    } else if (mode === 'month') {
      currentPeriod = MONTHS[new Date().getMonth()];
    }
    editMode = mode;
    root.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    $('month-tabs').style.display  = mode === 'month'  ? 'flex' : 'none';
    $('season-tabs').style.display = mode === 'season' ? 'flex' : 'none';
    root.querySelectorAll('[id^="tab-"]').forEach(t => t.classList.remove('active'));
    $('tab-' + currentPeriod).classList.add('active');
    updateChart(); renderAll(); updateDisplay();
  }

  function updateDisplay() {
    const presetKey  = editMode === 'season' ? `season_${currentPeriod}` : `month_${currentPeriod}`;
    const presetInfo = lastLoadedPreset[presetKey];
    let txt = '';
    if (editMode === 'month') {
      txt = `Mode: <code>Month</code><br>Editing: <code>${MONTH_NAMES[MONTHS.indexOf(currentPeriod)]}</code><br>Curve: <code>${TYPE_NAMES[currentType]}</code><br>Affects: <code>1 month</code>`;
    } else {
      const aff = SEASON_MONTHS[currentPeriod].map(m => MONTH_NAMES[MONTHS.indexOf(m)]).join(', ');
      txt = `Mode: <code>Season</code> ⚠️ Edits apply to all months in season<br>Editing: <code>${SEASON_NAMES[currentPeriod]}</code><br>Curve: <code>${TYPE_NAMES[currentType]}</code><br>Affects: <code>${aff}</code>`;
    }
    if (presetInfo) {
      txt += `<br>Based on: <code>${presetInfo}</code>`;
      if (modifiedPeriods[presetKey]) txt += ' <span style="color:#f59e0b;font-weight:700;">✏️ modified</span>';
    }
    if (clipboard) txt += `<br><br>📋 Clipboard: <code>${clipboard.periodName}</code> (ready to paste)`;
    $('edit-info').innerHTML = txt;
  }

  function showStatus(msg, type) {
    const el = $('status');
    el.textContent = msg; el.className = 'status ' + type;
    clearTimeout(showStatus.t);
    showStatus.t = setTimeout(() => { el.textContent = ''; el.className = ''; }, type === 'error' ? 8000 : 3000);
  }

  async function checkHighConsumption() {
    const hass = getHass();
    try {
      const load      = parseFloat(hass.states[M.load_30m_avg].state);
      const threshold = parseFloat(hass.states[M.high_consumption].state);
      if (isNaN(load) || isNaN(threshold)) {
        showNote('load_30m_avg or high_consumption has no number (' + hass.states[M.load_30m_avg].state + ' / ' + hass.states[M.high_consumption].state + ') — starting on the normal curve');
        return false;
      }
      return load > threshold;
    } catch(e) { return false; }
  }

  async function determineDefaultCurveType() {
    const hour = new Date().getHours();
    const high = await checkHighConsumption();
    return hour >= 17 && hour < 22 ? (high ? 'sell_high' : 'sell') : (high ? 'buy_high' : 'buy');
  }

  // ── Init ──────────────────────────────────────────────────────────────────
  async function start() {
    const problem = await startupProblem();
    if (problem) return card.problem(problem);
    buildColors();
    debugLog('Initializing…');
    const loaded      = await loadFromHA();
    if (!loaded) showNote(M.price_curves + ' has no curves yet — showing factory defaults; Save to store them');
    else if (CURVE_GAPS.length) showNote('Curves missing in ' + M.price_curves + ': ' + CURVE_GAPS.slice(0, 6).join(', ') + (CURVE_GAPS.length > 6 ? ' …' : '') + ' — showing factory defaults there; fix and Save');
    if (OPTIONAL_MISSING.length) showNote(OPTIONAL_MISSING.join(' · '));
    const amberLoaded = await loadAmberHistory();
    currentType = await determineDefaultCurveType();
    { const CC={sell:'--battman-green',sell_high:'--battman-purple',buy:'--battman-blue',buy_high:'--battman-teal'};
      card.style.setProperty('--active-curve', gc(CC[currentType]||'--battman-blue')); }
    debugLog(`🎯 Default curve type: ${currentType}`);

    // Canvas text can't read CSS var() — set Chart.js's font from the live theme font.
    Chart.defaults.font.family = gc('--primary-font-family', '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif');
    initChart();

    root.querySelectorAll('.tabs > .tab').forEach(t =>
      t.classList.remove('sell-active','sell-high-active','buy-active','buy-high-active','active')
    );
    const tabTextMap = { sell:'Sell', sell_high:'Sell High Consumption', buy:'Buy', buy_high:'Buy High Consumption' };
    root.querySelectorAll('.tabs > .tab').forEach(btn => {
      if (btn.textContent.trim() === tabTextMap[currentType]) btn.classList.add(currentType.replace('_','-') + '-active');
    });

    applyTypeUI(currentType);
    $('tab-' + currentPeriod).classList.add('active');

    updateAmberDatasets();
    updateChart();
    renderAll();
    updateDisplay();
    loadPresetInfo();

    showStatus(loaded ? ('✓ Loaded from HA' + (amberLoaded ? ' + Amber' : '')) : 'Ready', loaded || amberLoaded ? 'success' : 'info');

    // Show current hour in details panel on load
    updateHourDetailsPanel(new Date().getHours());

    debugLog('Init complete');

    pressFeedback(root);
    started = true;
  }

  // the view's theme changed: the chart's colours follow (the rest of the card follows by itself)
  function themeChanged() {
    if (!started) return;
    buildColors();
    const CC = { sell: '--battman-green', sell_high: '--battman-purple', buy: '--battman-blue', buy_high: '--battman-teal' };
    card.style.setProperty('--active-curve', gc(CC[currentType]));
    applyTypeUI(currentType);
    updateChart();
  }

  let started = false;
  wireHandlers(root, { clearDebugLog, closeManagePresets, copyPeriod, exportPeriod, importPeriod, loadFactoryDefaults, loadPreset, onInputHover, onInputLeave, openImport, openManagePresets, pastePeriod, runScript, savePreset, savePresetNames, saveToHA, setAll, switchCurveType, switchEditMode, switchPeriod, toggleAmber, toggleAutoSave, toggleDebugger, toggleHourDetails, togglePresetMenu, updateFollowLabel, updateValue });
  start();
  return { themeChanged };
}

class BattmanPricyCard extends BattmanCardBase {
  static cardName = "Battman Pricy";
  static preview = "pricy.webp";
  static css = CSS;
  static html = HTML;

  getCardSize() {
    return 12;
  }

  run(root) {
    return pricyRun(this, root);
  }
}
battmanDefine("battman-pricy", BattmanPricyCard);
battmanPicker("battman-pricy", "Battman Pricy",
  "The price curve editor: the sell and buy prices the engine works to at each hour, by month or season.", "battman-pricy");
