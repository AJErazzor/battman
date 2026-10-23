// Battman Settings: custom:battman-settings. Every Battman setting on one page, in sections you
// can drag between two columns (one on a narrow card); the order is kept per device. Entities and
// events come from Battman's entity map, colours from a Battman theme (no fallbacks). Every change
// is checked: a value Battman won't accept is refused before it's sent, and after sending, the
// card waits for the setting to change and says so if it didn't.

import { BattmanCardBase, FILES, battmanDefine, battmanMap, battmanPicker, missingEntities, missingThemeVars } from "./battman-card-base.js";

class BattmanSettingsCard extends BattmanCardBase {
  static cardName = "Battman Settings";
  static preview = "settings.webp";
  static css = `
  * { margin: 0; padding: 0; box-sizing: border-box; }
  /* the same panel look as Curvy and Pricy: one rounded card on the theme's background,
     each section an inner panel */
  :host { display: block; }
  ha-card { background: var(--primary-background-color); overflow: hidden; container-type: inline-size; }
  .frame { color: var(--battman-text-bright); font-family: var(--primary-font-family, sans-serif);
           font-size: 15px; line-height: 1.5; padding: 8px; }
  @container (min-width: 600px) { .frame { padding: 20px; } }
  .page { max-width: 2200px; margin: 0 auto; background: var(--card-background-color);
          border-radius: var(--ha-card-border-radius, 14px); padding: 8px;
          box-shadow: var(--ha-card-box-shadow, 0 2px 4px rgba(0,0,0,0.08), 0 8px 24px rgba(0,0,0,0.06));
          border: 1px solid var(--divider-color); }
  @container (min-width: 600px) { .page { padding: 28px; } }
  input, select, button { font-family: inherit; }

  .hdr { margin: 0 0 16px; display: flex; align-items: center; gap: 10px; }
  .hdr .who { height: 44px; width: auto; flex: none; }
  .hdr .word { width: 230px; max-width: 100%; min-width: 0; height: auto; flex: 0 1 auto; }
  .cols { display: flex; gap: 16px; align-items: flex-start; position: relative; }
  .col { flex: 1 1 0; min-width: 0; display: flex; flex-direction: column; gap: 16px; min-height: 60px; }
  @container (max-width: 900px) { .cols { flex-direction: column; } .col { width: 100%; flex: none; } }

  .sec { background: var(--secondary-background-color); border: 1px solid var(--divider-color);
         border-radius: calc(var(--ha-card-border-radius, 14px) - 2px); padding-bottom: 12px; overflow: hidden; }
  .sec.dragging { box-shadow: 0 10px 30px rgba(0,0,0,0.45); opacity: 0.97; }
  .placeholder { border: 2px dashed var(--divider-color); border-radius: calc(var(--ha-card-border-radius, 14px) - 2px); }
  .glabel { display: flex; align-items: center; justify-content: space-between; gap: 8px;
            padding: 16px 16px 0; font-size: 15px; font-weight: 600; letter-spacing: 0.01em; }
  .glabel-left { display: flex; align-items: center; gap: 7px; }
  .glabel svg { width: 18px; height: 18px; fill: var(--battman-green); flex: none; }
  .gright { display: flex; align-items: center; gap: 10px; }
  .grip { width: 12px; height: 18px; flex: none; color: var(--battman-text-muted); opacity: 0.7; cursor: grab;
          touch-action: none; background-image: radial-gradient(circle at center, currentColor 1.3px, transparent 1.7px);
          background-size: 6px 6px; }
  .grip:hover { opacity: 1; }
  .note { font-size: 12px; line-height: 1.5; color: var(--battman-green); background: var(--battman-green-soft-bg);
          border: 1px solid var(--battman-green-border); border-radius: 8px; padding: 9px 12px; margin: 10px 16px 0; }
  .note.bad { color: var(--battman-red); background: var(--battman-red-soft-bg); border-color: var(--battman-red); }
  .rows { margin-top: 10px; border-top: 1px solid var(--battman-border-neutral); }
  .row { display: flex; align-items: center; gap: 16px; padding: 12px 16px; border-bottom: 1px solid var(--battman-border-neutral); min-height: 52px; }
  .row:last-child { border-bottom: none; }
  .lbl { flex: 1; min-width: 0; }
  .name { font-size: 14px; font-weight: 500; }
  .desc { font-size: 12px; color: var(--battman-text-muted); margin-top: 2px; line-height: 1.3; }
  .msg { font-size: 12px; margin-top: 3px; line-height: 1.3; min-height: 0; }
  .msg.ok { color: var(--battman-green); }
  .msg.bad { color: var(--battman-red); }
  .msg.busy { color: var(--battman-text-muted); }
  .subdiv { font-size: 11px; font-weight: 500; letter-spacing: 0.06em; text-transform: uppercase; color: var(--battman-text-muted);
            background: var(--battman-surface-popup); padding: 6px 16px; border-bottom: 1px solid var(--battman-border-neutral); }
  .field { display: inline-flex; align-items: center; width: 130px; flex: none; background: var(--battman-surface-popup);
           border: 1px solid var(--battman-border-neutral); border-radius: 8px; min-height: 40px; }
  .field input { background: transparent; border: none; outline: none; color: var(--battman-text-bright); font-size: 14px;
                 padding: 6px 8px; flex: 1; min-width: 0; width: 0; text-align: right; }
  .field .sfx { font-size: 12px; color: var(--battman-text-muted); padding: 0 8px 0 2px; white-space: nowrap; }
  .field:focus-within { border-color: var(--battman-green); }
  .field.saved { border-color: var(--battman-green); }
  .field.err { border-color: var(--battman-red); }
  /* the wide boxes (notify target, phone, follow entity, theme) give way on a phone: never more
     than half the row, so their label keeps room */
  .wide { width: 220px; max-width: 50%; }
  .wide input { text-align: left; }
  input[type=time], input[type=date], select { background: var(--battman-surface-popup); border: 1px solid var(--battman-border-neutral);
       border-radius: 8px; color: var(--battman-text-bright); font-size: 14px; padding: 6px 8px; width: 130px; flex: none; min-height: 40px; }
  select { width: 150px; cursor: pointer; }
  input[type=time]:focus, input[type=date]:focus, select:focus { outline: none; border-color: var(--battman-green); }
  button.rst { background: var(--battman-green-soft-bg); border: 1px solid var(--battman-border-neutral); border-radius: 8px;
               color: var(--battman-text-muted); font-size: 12px; padding: 4px 10px; cursor: pointer; flex: none; }
  button.rst:hover { border-color: var(--battman-green); color: var(--battman-green); }
  .hpick { display: flex; align-items: center; gap: 4px; flex: none; }
  .hbtn { width: 40px; height: 40px; background: var(--battman-surface-popup); border: 1px solid var(--battman-border-neutral);
          border-radius: 8px; color: var(--battman-text-muted); font-size: 18px; cursor: pointer; }
  .hbtn:hover { border-color: var(--battman-green); color: var(--battman-green); }
  .hval { min-width: 52px; text-align: center; font-size: 14px; padding: 8px; background: var(--battman-surface-popup);
          border: 1px solid var(--battman-border-neutral); border-radius: 8px; }
  .tabs { display: flex; gap: 2px; margin: 16px 16px 0; background: var(--battman-surface-popup); border-radius: 8px; padding: 3px;
          border: 1px solid var(--battman-border-neutral); }
  .tabs button { flex: 1; padding: 7px 0; border: none; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600;
                 background: transparent; color: var(--battman-text-muted); }
  .tabs button.on { background: var(--battman-green-border-strong); color: var(--battman-text-bright); }
  .chips { display: flex; flex-wrap: wrap; gap: 4px; padding: 6px 16px 0; }
  .chip { display: inline-flex; gap: 5px; align-items: center; padding: 4px 10px; background: var(--battman-green-soft-bg);
          border: 1px solid var(--battman-green-border); border-radius: 6px; font-size: 12px; color: var(--battman-text-muted); }
  .chip b { color: var(--battman-green); }
  .act { display: block; width: calc(100% - 32px); margin: 12px 16px 0; padding: 10px; border: none; border-radius: 8px;
         background: var(--battman-green-border-strong); color: var(--battman-text-bright); font-size: 13px; font-weight: 600; cursor: pointer; }
  .qdaily { font-size: 11px; color: var(--battman-text-muted); text-align: right; }
  .sw { position: relative; width: 46px; height: 26px; flex: none; cursor: pointer; }
  .sw input { opacity: 0; width: 0; height: 0; position: absolute; }
  .sw span { position: absolute; inset: 0; border-radius: 13px; background: var(--battman-surface-popup);
             border: 1px solid var(--battman-border-neutral); transition: background .15s; }
  .sw span::after { content: ""; position: absolute; width: 18px; height: 18px; left: 3px; top: 3px; border-radius: 50%;
                    background: var(--battman-text-muted); transition: transform .15s, background .15s; }
  .sw input:checked + span { background: var(--battman-green-border-strong); border-color: var(--battman-green-border-strong); }
  .sw input:checked + span::after { transform: translateX(20px); background: var(--battman-green); }
  .defs { display: none; }
  .defs.open { display: block; }
  .dhead { display: flex; align-items: center; gap: 10px; padding: 12px 16px 0; cursor: pointer; user-select: none;
           font-size: 13px; color: var(--battman-text-muted); }
  .dhead .chev { margin-left: auto; transition: transform .15s; }
  .dhead.open .chev { transform: rotate(90deg); }
`;
  static html = `<ha-card><div class="frame"><div class="page">
<h2 class="hdr"><img src="${FILES}/images/battman-wrench.webp" alt="Battman" class="who"><img src="${FILES}/images/settings-line.webp" alt="Settings" class="word"></h2>
<div class="cols" id="cols"><div class="col" data-col="0"></div><div class="col" data-col="1"></div></div>
</div></div></ha-card>`;

  run(root) {
    const card = this;

    const ICON = {"buy": "M11.39 5.45L9.61 4.55L10.87 2H19.34L20.61 4.55L18.83 5.44L18.11 4H12.11L11.39 5.45M21.73 8H17.2L16.41 5H13.81L13 8H8.5L7.21 10.55L9 11.44L9.73 10H20.5L21.21 11.45L23 10.56L21.73 8M20.88 22H18.81L18.57 21.1L15.11 15.9L11.64 21.1L11.41 22H9.34L12.23 11H14.3L13.94 12.35L15.11 14.1L16.27 12.35L15.92 11H18L20.88 22M14.5 15L13.61 13.65L12.43 18.13L14.5 15M17.79 18.12L16.61 13.64L15.71 15L17.79 18.12M9 16L5 12V15H1V17H5V20L9 16Z", "buyRules": "M11 15H6L13 1V9H18L11 23V15Z", "needy": "M20 13C20.6 13 21.1 13.2 21.5 13.6C21.8 14 22 14.5 22 15L14 18L7 16V7H8.9L16.2 9.7C16.7 9.9 17 10.3 17 10.8C17 11.1 16.9 11.4 16.7 11.6S16.1 12 15.8 12H13L11.2 11.3L10.9 12.2L13 13H20M1 7H5V18H1V7Z", "watchdog": "M10,17L6,13L7.41,11.59L10,14.17L16.59,7.58L18,9M12,1L3,5V11C3,16.55 6.84,21.74 12,23C17.16,21.74 21,16.55 21,11V5L12,1Z", "billing": "M5,6H23V18H5V6M14,9A3,3 0 0,1 17,12A3,3 0 0,1 14,15A3,3 0 0,1 11,12A3,3 0 0,1 14,9M9,8A2,2 0 0,1 7,10V14A2,2 0 0,1 9,16H19A2,2 0 0,1 21,14V10A2,2 0 0,1 19,8H9M1,10H3V20H19V22H1V10Z", "system": "M7,15H9C9,16.08 10.37,17 12,17C13.63,17 15,16.08 15,15C15,13.9 13.96,13.5 11.76,12.97C9.64,12.44 7,11.78 7,9C7,7.21 8.47,5.69 10.5,5.18V3H13.5V5.18C15.53,5.69 17,7.21 17,9H15C15,7.92 13.63,7 12,7C10.37,7 9,7.92 9,9C9,10.1 10.04,10.5 12.24,11.03C14.36,11.56 17,12.22 17,15C17,16.79 15.53,18.31 13.5,18.82V21H10.5V18.82C8.47,18.31 7,16.79 7,15Z", "sell": "M5.18 5.45L3.4 4.55L4.66 2H13.13L14.4 4.55L12.62 5.44L11.9 4H5.9L5.18 5.45M15.5 8H11L10.2 5H7.6L6.81 8H2.28L1 10.55L2.79 11.44L3.5 10H14.28L15 11.45L16.79 10.56L15.5 8M14.67 22H12.6L12.36 21.1L8.9 15.9L5.43 21.1L5.2 22H3.13L6 11H8.09L7.73 12.35L8.9 14.1L10.06 12.35L9.71 11H11.78L14.67 22M8.3 15L7.4 13.65L6.22 18.13L8.3 15M11.58 18.12L10.4 13.64L9.5 15L11.58 18.12M23 16L19 12V15H15V17H19V20L23 16Z", "sellRules": "M2.3,20.28L11.9,10.68L10.5,9.26L9.78,9.97C9.39,10.36 8.76,10.36 8.37,9.97L7.66,9.26C7.27,8.87 7.27,8.24 7.66,7.85L13.32,2.19C13.71,1.8 14.34,1.8 14.73,2.19L15.44,2.9C15.83,3.29 15.83,3.92 15.44,4.31L14.73,5L16.15,6.43C16.54,6.04 17.17,6.04 17.56,6.43C17.95,6.82 17.95,7.46 17.56,7.85L18.97,9.26L19.68,8.55C20.07,8.16 20.71,8.16 21.1,8.55L21.8,9.26C22.19,9.65 22.19,10.29 21.8,10.68L16.15,16.33C15.76,16.72 15.12,16.72 14.73,16.33L14.03,15.63C13.63,15.24 13.63,14.6 14.03,14.21L14.73,13.5L13.32,12.09L3.71,21.7C3.32,22.09 2.69,22.09 2.3,21.7C1.91,21.31 1.91,20.67 2.3,20.28M20,19A2,2 0 0,1 22,21V22H12V21A2,2 0 0,1 14,19H20Z", "spike": "M7,2V13H10V22L17,10H13L17,2H7Z", "protection": "M10 12C10 10.9 10.9 10 12 10C13.1 10 14 10.9 14 12C14 13.1 13.1 14 12 14C10.9 14 10 13.1 10 12M7.8 17.7L6.3 16.3L7.8 14.8C7.3 14 7 13 7 12C7 11 7.3 10 7.8 9.3L6.3 7.8L7.8 6.3L9.2 7.8C10 7.3 11 7 12 7C13 7 14 7.3 14.8 7.8L16.3 6.3L17.7 7.7L16.2 9.2C16.7 10 17 11 17 12C17 13 16.7 14 16.2 14.8L17.7 16.3L16.3 17.7L14.8 16.2C14 16.7 13 17 12 17C11 17 10 16.7 9.3 16.2L7.8 17.7M12 9C10.3 9 9 10.3 9 12C9 13.7 10.3 15 12 15C13.7 15 15 13.7 15 12C15 10.3 13.7 9 12 9M20 2C21.1 2 22 2.9 22 4V20C22 21.1 21.1 22 20 22H19V23H15V22H9V23H5V22H4C2.9 22 2 21.1 2 20V4C2 2.9 2.9 2 4 2H20M20 20V4H4V20H20Z", "provider": "M8.28,5.45L6.5,4.55L7.76,2H16.23L17.5,4.55L15.72,5.44L15,4H9L8.28,5.45M18.62,8H14.09L13.3,5H10.7L9.91,8H5.38L4.1,10.55L5.89,11.44L6.62,10H17.38L18.1,11.45L19.89,10.56L18.62,8M17.77,22H15.7L15.46,21.1L12,15.9L8.53,21.1L8.3,22H6.23L9.12,11H11.19L10.83,12.35L12,14.1L13.16,12.35L12.81,11H14.88L17.77,22M11.4,15L10.5,13.65L9.32,18.13L11.4,15M14.68,18.12L13.5,13.64L12.6,15L14.68,18.12Z", "alert": "M21,19V20H3V19L5,17V11C5,7.9 7.03,5.17 10,4.29C10,4.19 10,4.1 10,4A2,2 0 0,1 12,2A2,2 0 0,1 14,4C14,4.1 14,4.19 14,4.29C16.97,5.17 19,7.9 19,11V17L21,19M14,21A2,2 0 0,1 12,23A2,2 0 0,1 10,21M19.75,3.19L18.33,4.61C20.04,6.3 21,8.6 21,11H23C23,8.07 21.84,5.25 19.75,3.19M1,11H3C3,8.6 3.96,6.3 5.67,4.61L4.25,3.19C2.16,5.25 1,8.07 1,11Z", "liveActivity": "M13 7H11V9H13V7M13 11H11V17H13V11M17 1H7C5.9 1 5 1.9 5 3V21C5 22.1 5.9 23 7 23H17C18.1 23 19 22.1 19 21V3C19 1.9 18.1 1 17 1M17 19H7V5H17V19Z", "dashboard": "M13,3V9H21V3M13,21H21V11H13M3,21H11V15H3M3,13H11V3H3V13Z", "defaults": "M12,15.5A3.5,3.5 0 0,1 8.5,12A3.5,3.5 0 0,1 12,8.5A3.5,3.5 0 0,1 15.5,12A3.5,3.5 0 0,1 12,15.5M19.43,12.97C19.47,12.65 19.5,12.33 19.5,12C19.5,11.67 19.47,11.34 19.43,11L21.54,9.37C21.73,9.22 21.78,8.95 21.66,8.73L19.66,5.27C19.54,5.05 19.27,4.96 19.05,5.05L16.56,6.05C16.04,5.66 15.5,5.32 14.87,5.07L14.5,2.42C14.46,2.18 14.25,2 14,2H10C9.75,2 9.54,2.18 9.5,2.42L9.13,5.07C8.5,5.32 7.96,5.66 7.44,6.05L4.95,5.05C4.73,4.96 4.46,5.05 4.34,5.27L2.34,8.73C2.21,8.95 2.27,9.22 2.46,9.37L4.57,11C4.53,11.34 4.5,11.67 4.5,12C4.5,12.33 4.53,12.65 4.57,12.97L2.46,14.63C2.27,14.78 2.21,15.05 2.34,15.27L4.34,18.73C4.46,18.95 4.73,19.03 4.95,18.95L7.44,17.94C7.96,18.34 8.5,18.68 9.13,18.93L9.5,21.58C9.54,21.82 9.75,22 10,22H14C14.25,22 14.46,21.82 14.5,21.58L14.87,18.93C15.5,18.67 16.04,18.34 16.56,17.94L19.05,18.95C19.27,19.03 19.54,18.95 19.66,18.73L21.66,15.27C21.78,15.05 21.73,14.78 21.54,14.63L19.43,12.97Z"};
    const NEEDS = ['parameters', 'parameters_update_event', 'buy_rules', 'buy_rules_event', 'sell_rules', 'sell_rules_event',
                   'buy_total', 'totals_update_event', 'power_provider_buy', 'power_provider_sell', 'power_provider_event'];
    const NEED_ENTITIES = ['parameters', 'buy_rules', 'sell_rules', 'buy_total', 'power_provider_buy', 'power_provider_sell'];
    // what the parameters sensor accepts (packages/battman_parameters.yaml): [int?, min, max, min exclusive?]
    const RANGE = {
      buyProrateSOCOffset: [1, 0, 100], buyHighSOCOffset: [1, 0, 100], sellProrateSOCOffset: [1, 0, 100], sellLowSOCOffset: [1, 0, 100],
      sellSpikePrice1: [0, 0, 10000], sellSpikeSOC1: [1, 0, 100], sellSpikePrice2: [0, 0, 10000], sellSpikeSOC2: [1, 0, 100],
      needyTriggerPVGap: [0, -40, 40], needyTriggerConsumption: [0, 0, 20],
      watchdogScriptNotRunLimit: [1, 0, 60], watchdogScriptDisabledLimit: [1, 0, 360],
      dailyNetworkCharge: [0, 0, 5], billDayOfMonth: [1, 0, 31, true],
      systemCost: [0, 0, 100000], systemIncome: [0, 0, 50000], systemExpenses: [0, 0, 50000],
      preSystemBillQ1: [0, 0, 5000], preSystemBillQ2: [0, 0, 5000], preSystemBillQ3: [0, 0, 5000], preSystemBillQ4: [0, 0, 5000],
      billInflation: [1, 0, 100], amberBuyAlertThreshold: [0, 0, 99],
    };
    const DEFAULT_KEYS = {   // the defaults each section's Reset restores (parameters' `defaults`)
      gridChargingPositive: ['buyProrateSOCOffset', 'buyHighSOCOffset'], gridDischarging: ['sellProrateSOCOffset', 'sellLowSOCOffset'],
      spikeSelling: ['sellSpikePrice1', 'sellSpikeSOC1', 'sellSpikePrice2', 'sellSpikeSOC2'],
      needyCurve: ['needyTriggerPVGap', 'needyTriggerConsumption'], watchdog: ['watchdogScriptNotRunLimit', 'watchdogScriptDisabledLimit'],
      billing: ['dailyNetworkCharge', 'billDayOfMonth'],
    };
    const LA = { sw: 'switch.battman_live_activity', phone: 'select.battman_live_activity_phone',
                 follow: 'text.battman_live_activity_follow', on: 'text.battman_live_activity_follow_on',
                 off: 'text.battman_live_activity_follow_off', delay: 'number.battman_live_activity_follow_delay',
                 spike: 'number.battman_live_activity_spike_alert' };
    const LA_MADE = ['script.battman_live_activity_push', 'automation.battman_live_activity_on_off',
                     'automation.battman_live_activity_updates', 'automation.battman_live_activity_follow'];
    const HOURS = ['12am','1am','2am','3am','4am','5am','6am','7am','8am','9am','10am','11am',
                   '12pm','1pm','2pm','3pm','4pm','5pm','6pm','7pm','8pm','9pm','10pm','11pm'];
    const ORDER_KEY = 'battman.settingsOrder';
    const UI = { rulesHour: { buy: new Date().getHours(), sell: new Date().getHours() }, rulesTab: { buy: 'single', sell: 'single' },
                 ppHour: new Date().getHours(), ppTab: 'buy', defsOpen: false, cascade: { buy: null, sell: null } };
    let M = null;

    // ---------------------------------------------------------------- basics
    const esc = (v) => String(v == null ? '' : v).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
    const getHass = () => card.hass;
    const st = (id) => { const h = getHass(); return h && h.states[id]; };
    const attrs = (key) => (st(M[key]) || {}).attributes || {};
    function icon(id) { return '<svg viewBox="0 0 24 24"><path d="' + ICON[id] + '"/></svg>'; }

    // the Battman theme colours the card uses (no fallbacks: missing ones are named)
    const THEME_VARS = ['battman-surface-card', 'battman-surface-popup', 'battman-text-bright', 'battman-text-muted', 'battman-border-neutral',
                        'battman-green', 'battman-green-soft-bg', 'battman-green-border', 'battman-green-border-strong', 'battman-red', 'battman-red-soft-bg'].map((k) => '--' + k);
    async function loadMap() {
      M = await battmanMap(getHass(), NEEDS);
      const bad = missingEntities(getHass(), M, NEED_ENTITIES);
      if (bad) throw new Error(bad);
    }

    // ---------------------------------------------------------------- saving, and checking it took
    // A message next to a control ("Saving…", "✓ Saved", or why not). Kept per control, so a
    // redraw (the new value arriving) doesn't wipe it.
    const MSGS = {};
    const ctlKey = (el) => el.tagName + '|' + Object.entries(el.dataset).map(([k, v]) => k + '=' + v).sort().join('|');
    function msgHost(el) {
      const row = el.closest('.row'); if (row) return row.querySelector('.lbl');
      if (el.nextElementSibling && el.nextElementSibling.classList.contains('lbl')) return el.nextElementSibling;
      const sec = el.closest('.sec');
      let host = sec.querySelector(':scope > .gmsg');
      if (!host) { host = document.createElement('div'); host.className = 'lbl gmsg'; host.style.padding = '0 16px'; sec.insertBefore(host, sec.querySelector('.body')); }
      return host;
    }
    function show(el, text, cls) {
      const host = msgHost(el);
      let m = host.querySelector(':scope > .msg');
      if (!m) { m = document.createElement('div'); host.appendChild(m); }
      m.className = 'msg ' + cls; m.textContent = text;
      const f = el.closest('.field'); if (f) { f.classList.toggle('saved', cls === 'ok'); f.classList.toggle('err', cls === 'bad'); }
    }
    function say(el, text, cls) {
      const key = ctlKey(el);
      MSGS[key] = { text: text, cls: cls, at: Date.now() };
      show(el, text, cls);
      if (cls === 'ok') setTimeout(() => {
        if (MSGS[key] && MSGS[key].text === text) {
          delete MSGS[key];
          const cur = root.querySelector('[data-sec] ' + el.tagName.toLowerCase() + Object.entries(el.dataset).map(([k, v]) => '[data-' + k.replace(/[A-Z]/g, (c) => '-' + c.toLowerCase()) + '="' + CSS.escape(v) + '"]').join(''));
          const t = cur || el; const host = msgHost(t); const m = host && host.querySelector(':scope > .msg');
          if (m && m.textContent === text) { m.textContent = ''; m.className = 'msg'; }
          const f = t.closest('.field'); if (f) f.classList.remove('saved');
        }
      }, 3000);
    }
    function reapplyMessages(container) {
      container.querySelectorAll('input, select, button').forEach((el) => {
        const m = MSGS[ctlKey(el)];
        if (m && (m.cls !== 'ok' || Date.now() - m.at < 3000)) show(el, m.text, m.cls);
      });
    }
    // send (a promise), then wait for check() to be true; say what happened next to `el`
    async function apply(el, send, check, what) {
      say(el, 'Saving…', 'busy');
      try { await send(); } catch (e) { say(el, 'Not saved: ' + ((e && e.message) || e), 'bad'); return false; }
      const t0 = Date.now();
      while (Date.now() - t0 < 5000) {
        try { if (check()) { say(el, '✓ Saved', 'ok'); return true; } } catch (e) {}
        await new Promise((r) => setTimeout(r, 250));
      }
      say(el, 'Not saved: ' + (what || 'the setting') + " didn't change. Battman ignores changes while it isn't in charge of the battery.", 'bad');
      return false;
    }
    const fire = (key, data) => getHass().callWS({ type: 'fire_event', event_type: M[key], event_data: data });
    const near = (a, b) => Math.abs(Number(a) - Number(b)) < 1e-6;
    function parseNum(text, range) {
      const t = String(text).trim();
      if (t === '' || !isFinite(Number(t))) return { err: 'Enter a number' };
      let v = Number(t);
      if (range) {
        const [isInt, lo, hi, loOpen] = range;
        if (isInt) v = Math.trunc(v);
        if (loOpen ? v <= lo : v < lo) return { err: 'Must be ' + (loOpen ? 'more than ' : 'at least ') + lo };
        if (v > hi) return { err: 'Must be at most ' + hi };
      }
      return { v };
    }
    function setParam(el, key, value, check) {
      return apply(el, () => fire('parameters_update_event', { action: 'SetAttribute', [key]: value }),
                   check || (() => near(attrs('parameters')[key], value)), key);
    }

    // ---------------------------------------------------------------- building blocks (data-* drive the handlers)
    const has = (v) => v !== undefined && v !== null && v !== '';
    function numParam(key, label, desc, unit, extra) {
      const p = attrs('parameters');
      const val = has(p[key]) ? p[key] : '';
      return row(label, desc, '<div class="field"><input inputmode="decimal" data-param="' + key + '" value="' + esc(val) + '"><span class="sfx">' + esc(unit) + '</span></div>' + (extra || ''),
                 has(p[key]) ? '' : 'Not set yet');
    }
    function swHtml(attrsStr, on) { return '<label class="sw"><input type="checkbox" ' + attrsStr + (on ? ' checked' : '') + '><span></span></label>'; }
    function row(label, desc, ctrl, problem) {
      return '<div class="row"><div class="lbl"><div class="name">' + label + '</div>' + (desc ? '<div class="desc">' + desc + '</div>' : '')
        + (problem ? '<div class="msg bad">' + esc(problem) + '</div>' : '') + '</div>' + ctrl + '</div>';
    }
    function resetBtn(section) { return '<button class="rst" data-reset="' + section + '">&#8635; Reset</button>'; }
    function note(text, bad) { return '<div class="note' + (bad ? ' bad' : '') + '">' + text + '</div>'; }

    // ---------------------------------------------------------------- the sections
    function rulesSection(side) {
      const key = side + '_rules', ent = st(M[key]);
      const a = ent.attributes, rules = a.rules;
      const h = UI.rulesHour[side];
      if (!Array.isArray(rules) || rules.length !== 24) return note(M[key] + ' has no rules yet (Battman sets them up the first time it saves a rule).', true)
        + '<div class="rows">' + row(side === 'buy' ? 'Buy rules enabled' : 'Sell rules enabled', 'Master switch', swHtml('data-rules-state="' + side + '"', /^true$/i.test(ent.state))) + '</div>';
      const r = rules[h];
      const tab = UI.rulesTab[side];
      const numRule = (item, val, unit) => '<div class="field"><input inputmode="decimal" data-rule="' + side + '" data-item="' + item + '" value="' + esc(val) + '"><span class="sfx">' + unit + '</span></div>';
      const casStart = UI.cascade[side] ? UI.cascade[side].start : h, casLa = UI.cascade[side] ? UI.cascade[side].la : 4;
      const chips = Array.from({ length: Math.max(1, Math.min(12, casLa)) }, (_, i) => '<span class="chip">' + HOURS[(casStart + i) % 24] + ' <b>' + (casLa - i) + 'h</b></span>').join('');
      return note(side === 'buy'
          ? 'Fine-grained control over the buy price target each hour. Pick an hour and set its rule, or apply a cascade.'
          : 'Fine-grained control over the sell price target each hour. Pick an hour and set its rule, or apply a cascade.')
        + '<div class="rows">'
        + row(side === 'buy' ? 'Buy rules enabled' : 'Sell rules enabled', 'Master switch for all ' + side + ' rule processing', swHtml('data-rules-state="' + side + '"', /^true$/i.test(ent.state)))
        + row('Hour', 'Hour to configure', '<div class="hpick"><button class="hbtn" data-hour="' + side + '" data-d="-1">&#8249;</button><div class="hval">' + HOURS[h] + '</div><button class="hbtn" data-hour="' + side + '" data-d="1">&#8250;</button></div>')
        + '</div><div class="tabs"><button class="' + (tab === 'single' ? 'on' : '') + '" data-rtab="' + side + '" data-t="single">Single hour</button><button class="' + (tab === 'cascade' ? 'on' : '') + '" data-rtab="' + side + '" data-t="cascade">⚡ Cascade</button></div>'
        + (tab === 'single'
          ? '<div class="rows">'
            + row('Active', 'Use this rule at ' + HOURS[h], swHtml('data-rule="' + side + '" data-item="isActive"', !!r.isActive))
            + (side === 'sell' ? row('Allow last chance to sell low', 'Override the minimum price in the final window', swHtml('data-rule="sell" data-item="allowLastChance"', !!r.allowLastChance)) : '')
            + row('Look ahead', 'Hours of future prices to consider', numRule('hours_ahead', r.hours_ahead, 'hrs'))
            + row('Grouping', 'Interval for grouping dispatch windows', numRule('grouping_minutes', r.grouping_minutes, 'min'))
            + row('Round to', 'Decimal places for the price target', numRule('roundTo', r.roundTo, 'places'))
            + row('Round type', 'Direction to round the price target', '<select data-rule="' + side + '" data-item="roundtype">'
                + [['none', 'None'], ['floor', 'Down (floor)'], ['ceil', 'Up (ceil)']].map(([v, l]) => '<option value="' + v + '"' + (r.roundtype === v ? ' selected' : '') + '>' + l + '</option>').join('') + '</select>')
            + row('Offset by', 'Fixed adjustment added to the price target', numRule('offset', r.offset, 'c/kWh'))
            + '</div>'
          : '<div class="desc" style="padding:12px 16px 0">From the start hour, each hour is switched on with a look-ahead counting down to 1. Its other settings stay as they are.</div>'
            + '<div class="rows">'
            + row('Start hour', '', '<select data-cas="' + side + '" data-k="start">' + HOURS.map((l, i) => '<option value="' + i + '"' + (i === casStart ? ' selected' : '') + '>' + l + '</option>').join('') + '</select>')
            + row('Max look-ahead', '1 to 12 hours', '<div class="field"><input inputmode="numeric" data-cas="' + side + '" data-k="la" value="' + casLa + '"><span class="sfx">hrs</span></div>')
            + '</div><div class="chips">' + chips + '</div><button class="act" data-cascade="' + side + '">Apply cascade</button><div class="lbl" style="padding:0 16px"></div>');
    }

    function protectionSection() {
      const a = attrs('buy_total');
      const num = (ev, attr, label, desc, unit) => row(label, desc, '<div class="field"><input inputmode="decimal" data-track="' + ev + '" data-attr="' + attr + '" value="' + esc(has(a[attr]) ? a[attr] : '') + '"><span class="sfx">' + unit + '</span></div>',
                                                    has(a[attr]) ? '' : 'Not set yet');
      return note('Stops selling below a margin over what you\'ve been paying, once today\'s grid import and average buy price are both above these thresholds.')
        + '<div class="rows">'
        + num('buy_trackingA_CutOffKwh', 'trackingA_CutOffKwh', 'When import above', 'Daily grid import that turns protection on', 'kWh')
        + num('buy_trackingA_CutOffcKwh', 'trackingA_CutOffcKwh', 'And average buy above', 'Average buy price that turns protection on', 'c/kWh')
        + num('buy_trackingA_Offset', 'trackingA_Offset', 'Minimum sell is average buy plus', 'Margin above the average buy price', 'c/kWh')
        + row('Allow last chance to sell lower', 'Let last-chance discharge intervals ignore protection', swHtml('data-track="buy_trackingA_AllowLastChance" data-attr="trackingA_AllowLastChance"', parseInt(a.trackingA_AllowLastChance, 10) === 1))
        + num('buy_trackingA_ResetHour', 'trackingA_ResetHour', 'Reset hour', 'Hour of day the import tracking starts again (0 to 23)', 'h')
        + '</div>';
    }

    function providerSection() {
      const b = attrs('power_provider_buy'), s = attrs('power_provider_sell');
      const provider = b.provider;
      const h = UI.ppHour, side = UI.ppTab;
      const t = ((side === 'buy' ? b : s).tariff || [])[h];
      const tf = (item, unit, dp) => '<div class="field"><input inputmode="decimal" data-tariff="' + side + '" data-item="' + item + '" value="' + esc(t ? Number(t[item]).toFixed(dp) : '') + '"><span class="sfx">' + unit + '</span></div>';
      let html = note('Your electricity retailer and its hourly rates. Retail uses these rates instead of live Amber prices.')
        + '<div class="rows">' + row('Provider', 'Where buy and sell prices come from', '<select data-provider>'
          + (['Amber', 'Retail'].includes(provider) ? '' : '<option value="" selected disabled>Not set</option>')
          + '<option value="Amber"' + (provider === 'Amber' ? ' selected' : '') + '>Amber (live)</option><option value="Retail"' + (provider === 'Retail' ? ' selected' : '') + '>Retail (fixed)</option></select>');
      if (provider !== 'Retail') return html + '</div>';
      html += row('Hour', 'Hour to configure', '<div class="hpick"><button class="hbtn" data-pphour="-1">&#8249;</button><div class="hval">' + HOURS[h] + '</div><button class="hbtn" data-pphour="1">&#8250;</button></div>') + '</div>'
        + '<div class="tabs"><button class="' + (side === 'buy' ? 'on' : '') + '" data-pptab="buy">Buy tariff</button><button class="' + (side === 'sell' ? 'on' : '') + '" data-pptab="sell">Sell tariff</button></div>';
      if (!t) return html + note(M['power_provider_' + side] + ' has no tariff yet.', true);
      return html + '<div class="rows">'
        + row('Normal price', side === 'buy' ? 'Standard buy rate for this hour' : 'Standard sell (feed-in) rate for this hour', tf('priceNormal', 'c/kWh', 4))
        + row('Bonus price', side === 'buy' ? 'Cheaper rate while usage is under the limit' : 'Better feed-in while export is under the limit', tf('priceBonus', 'c/kWh', 4))
        + row('Bonus limit', side === 'buy' ? 'Usage (kWh) that gets the bonus price' : 'Export (kWh) that gets the bonus price', tf('limit', 'kWh', 1))
        + '</div>';
    }

    function prettyNotify(h, svc) {
      const slug = (x) => (x || '').replace(/['’]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
      const devs = {}; try { Object.values(h.devices || {}).forEach((d) => { const n = d.name_by_user || d.name; if (n) devs[slug(n)] = n; }); } catch (e) {}
      const title = (s) => s.split('_').map((w) => w ? w[0].toUpperCase() + w.slice(1) : w).join(' ');
      if (svc.indexOf('mobile_app_') === 0) return devs[svc.slice(11)] || title(svc.slice(11));
      if (svc.indexOf('alexa_media_') === 0) return title(svc.slice(12)) + ' (Alexa)';
      return title(svc);
    }

    function alertSection() {
      const h = getHass(), p = attrs('parameters');
      const list = Object.keys((h.services && h.services.notify) || {}).sort();
      const target = has(p.alertNotifyTarget) || p.alertNotifyTarget === '' ? p.alertNotifyTarget : null;
      const opts = (target === null ? '<option value="" disabled selected>Not set</option>' : '')
        + (target && list.indexOf(target) < 0 ? '<option value="' + esc(target) + '" selected>' + esc(target) + ' (not found)</option>' : '')
        + '<option value=""' + (target === '' ? ' selected' : '') + '>— Off (no alerts) —</option>'
        + list.map((n) => '<option value="' + esc(n) + '"' + (n === target ? ' selected' : '') + '>' + esc(prettyNotify(h, n)) + '</option>').join('');
      return note('Alerts when the live buy price is cheap, with quick-charge actions. Set Notify target to Off to turn alerts off.')
        + '<div class="rows">'
        + numParam('amberBuyAlertThreshold', 'Alert threshold', 'Notify when the buy price drops below this', 'c/kWh')
        + row('Notify target', 'Which notify service gets the alerts', '<select class="wide" data-notify>' + opts + '</select>')
        + row('Alert on negative price', 'Also notify when the buy price goes below zero', swHtml('data-pswitch="amberNegativeBuyAlert"', !!p.amberNegativeBuyAlert))
        + '</div>';
    }

    function liveActivitySection() {
      const h = getHass();
      const gone = Object.values(LA).filter((id) => !h.states[id]);
      if (gone.length) return note('Battman setting not found: ' + esc(gone.join(', ')) + '. Is Battman set up?', true);
      const S = (id) => h.states[id];
      const prob = (id) => S(id).attributes.problem ? '⚠ ' + S(id).attributes.problem : '';
      const ph = S(LA.phone);
      const phoneOpts = (ph.attributes.options || []).map((o) => '<option value="' + esc(o) + '"' + (o === ph.state ? ' selected' : '') + '>'
        + esc(o === 'Off' ? '— Off —' : prettyNotify(h, o) + (o === ph.state && ph.attributes.problem ? ' (not found)' : '')) + '</option>').join('');
      const txt = (id, w) => '<div class="field ' + (w ? 'wide' : '') + '"><input data-la-text="' + id + '" value="' + esc(S(id).state) + '"></div>';
      const num = (id, unit) => '<div class="field"><input inputmode="decimal" data-la-num="' + id + '" value="' + esc(S(id).state) + '"><span class="sfx">' + unit + '</span></div>';
      const f = (S(LA.follow).state || '').trim(), fe = f ? h.states[f] : null;
      const followNow = !f ? 'Blank: not following anything (use the switch)' : fe ? 'Now: ' + esc((fe.attributes && fe.attributes.friendly_name) || f) + ' is ' + esc(fe.state) : '';
      const notMade = LA_MADE.filter((id) => !h.states[id]);
      return note("Your battery on your phone's lock screen. Pick a phone, then switch it on, or let it follow something like your car's ignition.")
        + '<div class="rows">'
        + row('Live Activity', 'On shows it, off clears it', swHtml('data-la-switch', S(LA.sw).state === 'on'))
        + row('Phone', 'Which notify service gets it (Off sends nothing)', '<select class="wide" data-la-select="' + LA.phone + '">' + phoneOpts + '</select>', prob(LA.phone))
        + '<div class="subdiv">Follow an entity</div>'
        + row('Entity', followNow, txt(LA.follow, true), prob(LA.follow))
        + row('On when it becomes', '', txt(LA.on))
        + row('Off when it becomes', '…and has stayed that way for the time below', txt(LA.off))
        + row('Off after', "So a quick stop doesn't restart it", num(LA.delay, 'min'))
        + '<div class="subdiv">Alerts</div>'
        + row('Feed-in spike alert', 'Push with a sound when feed-in rises above this', num(LA.spike, '$/kWh'))
        + '<div class="subdiv">Automations</div>'
        + row("Battman's automations", notMade.length ? '<span style="color:var(--battman-red)">Not found: ' + esc(notMade.join(', ')) + '</span>' : 'The script and 3 automations Battman made are all there',
              '<button class="rst" data-la-create>Create missing</button>')
        + '</div>';
    }

    function dashboardSection() {
      const h = getHass(), p = attrs('parameters');
      const names = Object.keys((h.themes && h.themes.themes) || {}).filter((n) => /^battman /i.test(n)).sort();
      const cur = p.dashboardTheme || '';
      const opts = (cur ? '' : '<option value="" disabled selected>Not set</option>')
        + (cur && names.indexOf(cur) < 0 ? '<option value="' + esc(cur) + '" selected>' + esc(cur) + ' (not installed)</option>' : '')
        + names.map((n) => '<option value="' + esc(n) + '"' + (n === cur ? ' selected' : '') + '>' + esc(n.replace(/^battman /i, '')) + '</option>').join('');
      return note('How the dashboard shows battery controls, and its theme.')
        + '<div class="rows">'
        + row('Simple battery mode', 'Simple buy / sell / self-consume buttons instead of the full mode controls', swHtml('data-pswitch="simpleBatteryMode"', !!p.simpleBatteryMode))
        + row('Always show override timer', 'Keep the override timer visible even when no timer is running', swHtml('data-pswitch="alwaysShowOverrideTimer" data-showhide', p.alwaysShowOverrideTimer === 'show'))
        + row('Dashboard theme', 'Every view of this dashboard, the Live Activity colours, and theme: battman cards', '<select class="wide" data-theme>' + opts + '</select>')
        + '</div>';
    }

    function defaultsSection() {
      const d = attrs('parameters').defaults || {};
      const LABEL = { buyProrateSOCOffset: ['Buy: prorate price SOC offset', '%'], buyHighSOCOffset: ['Buy: high price SOC offset', '%'],
        sellProrateSOCOffset: ['Sell: prorate price SOC offset', '%'], sellLowSOCOffset: ['Sell: low price SOC offset', '%'],
        sellSpikePrice1: ['Spike tier 1 price', 'c/kWh'], sellSpikeSOC1: ['Spike tier 1 above SOC', '%'],
        sellSpikePrice2: ['Spike tier 2 price', 'c/kWh'], sellSpikeSOC2: ['Spike tier 2 above SOC', '%'],
        needyTriggerPVGap: ['Needy: PV to full battery gap', 'kWh'], needyTriggerConsumption: ['Needy: house power above', 'kW'],
        watchdogScriptNotRunLimit: ['Watchdog: not run limit', 'min'], watchdogScriptDisabledLimit: ['Watchdog: disabled limit', 'min'],
        dailyNetworkCharge: ['Billing: daily network charge', '$'], billDayOfMonth: ['Billing: bill day of month', 'day'] };
      let rows = '';
      Object.entries(DEFAULT_KEYS).forEach(([sec, keys]) => keys.forEach((k) => {
        const v = (d[sec] || {})[k];
        rows += row(LABEL[k][0], '', '<div class="field"><input inputmode="decimal" data-def="' + sec + '" data-k="' + k + '" value="' + esc(has(v) ? v : '') + '"><span class="sfx">' + LABEL[k][1] + '</span></div>', has(v) ? '' : 'Not set');
      }));
      return '<div class="dhead' + (UI.defsOpen ? ' open' : '') + '" data-defs-toggle><span>The values each &#8635; Reset button puts back</span><span class="chev">&#8250;</span></div>'
        + '<div class="defs' + (UI.defsOpen ? ' open' : '') + '"><div class="rows">' + rows + '</div><button class="act" data-defs-save>Save defaults</button><div class="lbl" style="padding:0 16px"></div></div>';
    }

    function systemSection() {
      const p = attrs('parameters');
      const daily = (k, days) => has(p[k]) && Number(p[k]) ? '<div class="qdaily">$' + (Number(p[k]) / days).toFixed(2) + '/day</div>' : '';
      const q = (k, label, days) => '<div class="row"><div class="lbl"><div class="name">' + label + '</div></div><div style="display:flex;flex-direction:column;align-items:flex-end;gap:2px">'
        + '<div class="field"><input inputmode="decimal" data-param="' + k + '" value="' + esc(has(p[k]) ? p[k] : '') + '"><span class="sfx">$</span></div>' + daily(k, days) + '</div></div>';
      return note('Install details, income, expenses and pre-solar bills, for payback and lifetime savings (the Solar System card).')
        + '<div class="rows"><div class="subdiv">System</div>'
        + numParam('systemCost', 'Install cost', 'Total cost of solar + battery', '$')
        + row('Install date', 'When the system was switched on', '<input type="date" data-date="systemInstallDate" value="' + esc(has(p.systemInstallDate) ? String(p.systemInstallDate).slice(0, 10) : '') + '">')
        + '<div class="subdiv">Other income &amp; expenses</div>'
        + numParam('systemIncome', 'Other income', 'Rebates, credits, incentives: lifetime total', '$')
        + numParam('systemExpenses', 'Other expenses', 'Maintenance, repairs, parts: lifetime total', '$')
        + '<div class="subdiv">Pre-solar quarterly bills</div>'
        + q('preSystemBillQ1', 'Q1 · Jul – Sep', 92) + q('preSystemBillQ2', 'Q2 · Oct – Dec', 92)
        + q('preSystemBillQ3', 'Q3 · Jan – Mar', 90) + q('preSystemBillQ4', 'Q4 · Apr – Jun', 91)
        + '<div class="subdiv">Inflation adjustment</div>'
        + numParam('billInflation', 'Bill inflation', 'Yearly rise in electricity prices', '%')
        + '</div>';
    }

    function watchdogSection() {
      const p = attrs('parameters');
      let t = '';
      if (has(p.watchdogResetOverridesAt)) { const d = new Date(p.watchdogResetOverridesAt); if (!isNaN(d)) t = d.toTimeString().slice(0, 5); }
      return note('Keeps an eye on the engine. If its script stops running or stays disabled, Battman alerts and recovers it.')
        + '<div class="rows">'
        + numParam('watchdogScriptNotRunLimit', 'Script not run limit', "Alert if the script hasn't run within this time", 'min')
        + numParam('watchdogScriptDisabledLimit', 'Script disabled limit', 'Turn it back on if disabled longer than this', 'min')
        + row('Reset overrides at', 'Daily time to clear manual overrides', '<input type="time" data-time="watchdogResetOverridesAt" value="' + esc(t) + '">', t ? '' : 'Not set yet')
        + '</div>';
    }

    const SECTIONS = {
      buy:        { title: 'Buy', reset: 'gridChargingPositive', deps: ['parameters'], render: () => note('How hard the battery charges when grid prices are positive. Higher offsets mean more cautious charging.') + '<div class="rows">'
                    + numParam('buyProrateSOCOffset', 'Prorate price SOC offset', 'SOC target offset when prorating by price', '%')
                    + numParam('buyHighSOCOffset', 'High price SOC offset', 'SOC offset at high buy prices', '%') + '</div>' },
      buyRules:   { title: 'Buy rules', deps: ['buy_rules'], render: () => rulesSection('buy') },
      needy:      { title: 'Needy curve triggers', reset: 'needyCurve', deps: ['parameters'], render: () => note('Switches to a more aggressive charging curve when the house uses a lot, or solar won\'t fill the battery before sunset.') + '<div class="rows">'
                    + numParam('needyTriggerPVGap', 'PV to full battery gap', 'Remaining solar needed to fill the battery', 'kWh')
                    + numParam('needyTriggerConsumption', 'House power above', 'Use that triggers the needy curve', 'kW') + '</div>' },
      watchdog:   { title: 'Watchdog', reset: 'watchdog', deps: ['parameters'], render: watchdogSection },
      billing:    { title: 'Billing', reset: 'billing', deps: ['parameters'], render: () => note('For your net electricity costs. Set these to match your retailer\'s bill.') + '<div class="rows">'
                    + numParam('dailyNetworkCharge', 'Daily network charge', "Your retailer's fixed daily supply charge", '$')
                    + numParam('billDayOfMonth', 'Bill day of month', 'Day your billing period starts each month', 'day') + '</div>' },
      system:     { title: 'System &amp; financials', deps: ['parameters'], render: systemSection },
      sell:       { title: 'Sell', reset: 'gridDischarging', deps: ['parameters'], render: () => note('When and how much the battery exports. SOC offsets stop it running too low.') + '<div class="rows">'
                    + numParam('sellProrateSOCOffset', 'Prorate price SOC offset', 'SOC offset when prorating the sell price', '%')
                    + numParam('sellLowSOCOffset', 'Low price SOC offset', 'SOC offset at low sell prices', '%') + '</div>' },
      sellRules:  { title: 'Sell rules', deps: ['sell_rules'], render: () => rulesSection('sell') },
      spike:      { title: 'Spike selling', reset: 'spikeSelling', deps: ['parameters'], render: () => note('When prices spike the battery can export at a profit. Two tiers let it sell harder at higher prices.') + '<div class="rows">'
                    + '<div class="subdiv">Tier 1</div>' + numParam('sellSpikePrice1', 'Spike sell price', '', 'c/kWh') + numParam('sellSpikeSOC1', 'Sell above SOC', '', '%')
                    + '<div class="subdiv">Tier 2</div>' + numParam('sellSpikePrice2', 'Spike sell price', '', 'c/kWh') + numParam('sellSpikeSOC2', 'Sell above SOC', '', '%') + '</div>' },
      protection: { title: 'Sell price protection', deps: ['buy_total'], render: protectionSection },
      provider:   { title: 'Power provider', deps: ['power_provider_buy', 'power_provider_sell'], render: providerSection },
      alert:      { title: 'Amber buy alert', deps: ['parameters'], render: alertSection, services: true },
      liveActivity: { title: 'Live Activity', deps: [], extra: () => Object.values(LA).concat(LA_MADE), render: liveActivitySection, services: true },
      dashboard:  { title: 'Dashboard options', deps: ['parameters'], render: dashboardSection, themes: true },
      defaults:   { title: 'Reset defaults', deps: ['parameters'], render: defaultsSection },
    };
    const DEFAULT_ORDER = [['buy', 'buyRules', 'needy', 'watchdog', 'billing', 'system'],
                           ['sell', 'sellRules', 'spike', 'protection', 'provider', 'alert', 'liveActivity', 'dashboard', 'defaults']];

    // ---------------------------------------------------------------- layout, drawing and keeping up to date
    function loadOrder() {
      let saved = null; try { saved = JSON.parse(localStorage.getItem(ORDER_KEY) || 'null'); } catch (e) {}
      if (!Array.isArray(saved) || saved.length !== 2) return DEFAULT_ORDER.map((c) => c.slice());
      const seen = new Set(), out = [[], []];
      saved.forEach((col, i) => (col || []).forEach((id) => { if (SECTIONS[id] && !seen.has(id)) { out[i].push(id); seen.add(id); } }));
      DEFAULT_ORDER.forEach((col, i) => col.forEach((id) => { if (!seen.has(id)) out[i].push(id); }));   // new sections land in their default column
      return out;
    }
    function saveOrder() {
      const order = [0, 1].map((i) => Array.from(root.querySelectorAll('.col[data-col="' + i + '"] .sec')).map((s) => s.dataset.sec));
      try { localStorage.setItem(ORDER_KEY, JSON.stringify(order)); } catch (e) {}
    }
    const sig = {};
    function signature(id) {
      const def = SECTIONS[id], h = getHass();
      const ents = def.deps.map((k) => M[k]).concat(def.extra ? def.extra() : []);
      return JSON.stringify([ents.map((e) => { const s = h.states[e]; return s ? s.last_updated + s.state : '-'; }),
        def.services ? Object.keys((h.services && h.services.notify) || {}).length : 0,
        def.themes ? Object.keys((h.themes && h.themes.themes) || {}).length : 0]);
    }
    function draw(id, force) {
      const el = root.querySelector('.sec[data-sec="' + id + '"] .body');
      if (!el) return;
      const s = signature(id) + JSON.stringify(UI);
      if (!force && s === sig[id]) return;
      if (!force && el.contains(root.activeElement)) return;           // never redraw over what you're typing
      if (!force && el.querySelector('.msg.busy')) return;                  // or while a save is being checked
      sig[id] = s;
      try { el.innerHTML = SECTIONS[id].render(); reapplyMessages(el); }
      catch (e) { el.innerHTML = note('This section couldn\'t be drawn: ' + esc(e.message), true); }
    }
    function build() {
      const order = loadOrder();
      order.forEach((ids, i) => {
        const col = root.querySelector('.col[data-col="' + i + '"]');
        ids.forEach((id) => {
          const def = SECTIONS[id];
          const sec = document.createElement('div');
          sec.className = 'sec'; sec.dataset.sec = id;
          sec.innerHTML = '<div class="glabel"><div class="glabel-left">' + icon(id) + def.title + '</div><div class="gright">'
            + (def.reset ? resetBtn(def.reset) : '') + '<span class="grip" data-grip title="Drag to move"></span></div></div><div class="body"></div>';
          col.appendChild(sec);
          draw(id, true);
        });
      });
    }
    const redrawAll = () => Object.keys(SECTIONS).forEach((id) => draw(id));
    const secOf = (el) => el.closest('.sec').dataset.sec;

    // ---------------------------------------------------------------- handlers
    async function onChange(e) {
      const t = e.target;
      if (t.dataset.param) {
        const key = t.dataset.param, n = parseNum(t.value, RANGE[key]);
        if (n.err) return say(t, n.err, 'bad');
        t.value = n.v;
        return setParam(t, key, n.v);
      }
      if (t.dataset.date) {
        if (!t.value) return say(t, 'Pick a date', 'bad');
        const iso = t.value + 'T00:00:00';
        return setParam(t, t.dataset.date, iso, () => String(attrs('parameters')[t.dataset.date] || '').slice(0, 10) === t.value);
      }
      if (t.dataset.time) {
        if (!t.value) return say(t, 'Pick a time', 'bad');
        const d = new Date(), pad = (x) => ('0' + x).slice(-2);
        const iso = d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + 'T' + t.value + ':00';
        return setParam(t, t.dataset.time, iso, () => { const v = new Date(attrs('parameters')[t.dataset.time]); return !isNaN(v) && v.toTimeString().slice(0, 5) === t.value; });
      }
      if (t.dataset.pswitch) {
        const key = t.dataset.pswitch, on = t.checked;
        if ('showhide' in t.dataset) return setParam(t, key, on, () => attrs('parameters')[key] === (on ? 'show' : 'hide'));
        return setParam(t, key, on, () => !!attrs('parameters')[key] === on);
      }
      if ('notify' in t.dataset) return setParam(t, 'alertNotifyTarget', t.value, () => (attrs('parameters').alertNotifyTarget || '') === t.value);
      if (t.dataset.rulesState) {
        const side = t.dataset.rulesState, on = t.checked;
        return apply(t, () => fire(side + '_rules_event', { attribute: 'state', value: on }), () => /^true$/i.test(st(M[side + '_rules']).state) === on, side + ' rules');
      }
      if (t.dataset.rule) {
        const side = t.dataset.rule, item = t.dataset.item, h = UI.rulesHour[side];
        let value;
        if (t.type === 'checkbox') value = t.checked;
        else if (item === 'roundtype') value = t.value;
        else { const n = parseNum(t.value, [1, -1e6, 1e6]); if (n.err) return say(t, n.err, 'bad'); value = n.v; t.value = value; }
        return apply(t, () => fire(side + '_rules_event', { attribute: 'rules', hour: h, item: item, value: value }),
                     () => { const r = (attrs(side + '_rules').rules || [])[h] || {}; return typeof value === 'number' ? near(r[item], value) : r[item] === value; }, item);
      }
      if (t.dataset.cas) {
        const side = t.dataset.cas, c = UI.cascade[side] || { start: UI.rulesHour[side], la: 4 };
        if (t.dataset.k === 'start') c.start = parseInt(t.value, 10);
        else { const n = parseNum(t.value, [1, 1, 12]); if (n.err) return say(t, n.err, 'bad'); c.la = n.v; }
        UI.cascade[side] = c; return draw(secOf(t), true);
      }
      if (t.dataset.track) {
        const ev = t.dataset.track, attr = t.dataset.attr;
        if (t.type === 'checkbox') {
          const v = t.checked ? '1' : '0';
          return apply(t, () => fire('totals_update_event', { attribute: ev, value: v }), () => parseInt(attrs('buy_total')[attr], 10) === Number(v), attr);
        }
        const range = attr === 'trackingA_ResetHour' ? [1, 0, 23] : [0, 0, 1e6];
        const n = parseNum(t.value, range); if (n.err) return say(t, n.err, 'bad'); t.value = n.v;
        return apply(t, () => fire('totals_update_event', { attribute: ev, value: n.v }), () => near(attrs('buy_total')[attr], n.v), attr);
      }
      if ('provider' in t.dataset) {
        const v = t.value;
        return apply(t, () => fire('power_provider_event', { action: 'SetValue', provider: v }), () => attrs('power_provider_buy').provider === v, 'the provider')
          .then(() => draw('provider', true));
      }
      if (t.dataset.tariff) {
        const side = t.dataset.tariff, item = t.dataset.item, h = UI.ppHour;
        const n = parseNum(t.value, [0, -1e6, 1e6]); if (n.err) return say(t, n.err, 'bad');
        return apply(t, () => fire('power_provider_event', { attribute: side === 'buy' ? 'tariffBuy' : 'tariffSell', hour: h, item: item, value: n.v }),
                     () => near(((attrs('power_provider_' + side).tariff || [])[h] || {})[item], n.v), item);
      }
      if (t.dataset.laText) {
        const id = t.dataset.laText, v = t.value.trim();
        return apply(t, () => getHass().callService('text', 'set_value', { entity_id: id, value: v }), () => st(id).state === v, 'the setting');
      }
      if (t.dataset.laNum) {
        const id = t.dataset.laNum, s = st(id), a = s.attributes;
        const n = parseNum(t.value, [0, a.min, a.max]); if (n.err) return say(t, n.err, 'bad');
        return apply(t, () => getHass().callService('number', 'set_value', { entity_id: id, value: n.v }), () => near(st(id).state, n.v), 'the setting');
      }
      if (t.dataset.laSelect) {
        const id = t.dataset.laSelect, v = t.value;
        return apply(t, () => getHass().callService('select', 'select_option', { entity_id: id, option: v }), () => st(id).state === v, 'the phone');
      }
      if ('laSwitch' in t.dataset) {
        const on = t.checked;
        return apply(t, () => getHass().callService('switch', on ? 'turn_on' : 'turn_off', { entity_id: LA.sw }), () => (st(LA.sw).state === 'on') === on, 'the switch');
      }
      if ('theme' in t.dataset) return applyTheme(t, t.value);
    }

    async function onClick(e) {
      const t = e.target.closest('button, .dhead');
      if (!t) return;
      if (t.dataset.reset) {
        const sec = t.dataset.reset, defs = (attrs('parameters').defaults || {})[sec];
        if (!defs || !Object.keys(defs).length) return say(t, 'No defaults saved for this section (see Reset defaults)', 'bad');
        const data = Object.assign({ action: 'SetAttribute' }, defs);
        return apply(t, () => fire('parameters_update_event', data),
                     () => DEFAULT_KEYS[sec].every((k) => !(k in defs) || near(attrs('parameters')[k], RANGE[k] && RANGE[k][0] ? Math.trunc(defs[k]) : defs[k])), 'the values')
          .then(() => draw(secOf(t), true));
      }
      if (t.dataset.hour) { const side = t.dataset.hour; UI.rulesHour[side] = (UI.rulesHour[side] + Number(t.dataset.d) + 24) % 24; return draw(secOf(t), true); }
      if (t.dataset.rtab) { UI.rulesTab[t.dataset.rtab] = t.dataset.t; return draw(secOf(t), true); }
      if (t.dataset.pphour) { UI.ppHour = (UI.ppHour + Number(t.dataset.pphour) + 24) % 24; return draw('provider', true); }
      if (t.dataset.pptab) { UI.ppTab = t.dataset.pptab; return draw('provider', true); }
      if (t.dataset.cascade) return applyCascade(t, t.dataset.cascade);
      if ('defsToggle' in t.dataset) { UI.defsOpen = !UI.defsOpen; return draw('defaults', true); }
      if ('defsSave' in t.dataset) return saveDefaults(t);
      if ('laCreate' in t.dataset) {
        return apply(t, () => getHass().callService('battman', 'create_live_activity', {}), () => LA_MADE.every((id) => st(id)), "Battman's automations");
      }
    }

    async function applyCascade(btn, side) {
      const c = UI.cascade[side] || { start: UI.rulesHour[side], la: 4 };
      const steps = [];
      for (let i = 0; i < c.la; i++) steps.push({ hour: (c.start + i) % 24, ahead: c.la - i });
      // one hour at a time: each change waits for the rules to show it, so none is lost
      for (const s of steps) {
        const ok = await apply(btn, async () => {
          await fire(side + '_rules_event', { attribute: 'rules', hour: s.hour, item: 'isActive', value: true });
          await fire(side + '_rules_event', { attribute: 'rules', hour: s.hour, item: 'hours_ahead', value: s.ahead });
        }, () => { const r = (attrs(side + '_rules').rules || [])[s.hour] || {}; return r.isActive === true && near(r.hours_ahead, s.ahead); }, HOURS[s.hour]);
        if (!ok) return;
      }
      say(btn, '✓ Cascade applied to ' + steps.length + ' hours', 'ok');
    }

    function saveDefaults(btn) {
      const box = btn.closest('.sec'), nd = {};
      for (const inp of box.querySelectorAll('input[data-def]')) {
        const n = parseNum(inp.value, RANGE[inp.dataset.k]);
        if (n.err) return say(inp, n.err, 'bad');
        (nd[inp.dataset.def] = nd[inp.dataset.def] || {})[inp.dataset.k] = n.v;
      }
      const cur = attrs('parameters').defaults || {};
      Object.keys(cur).forEach((sec) => { nd[sec] = Object.assign({}, cur[sec], nd[sec] || {}); });   // keep defaults not shown here
      return apply(btn, () => fire('parameters_update_event', { action: 'SetDefaults', defaults: nd }),
                   () => { const d = attrs('parameters').defaults || {}; return Object.entries(nd).every(([s, kv]) => Object.entries(kv).every(([k, v]) => near((d[s] || {})[k], v))); }, 'the defaults');
    }

    async function applyTheme(el, theme) {
      const h = getHass();
      let urlPath = '';
      try { urlPath = window.location.pathname.split('/').filter(Boolean)[0]; } catch (e) {}
      if (!theme) return;
      // Battman keeps the name (parameters' dashboardTheme): the mode colours sensor reads it
      const saved = await setParam(el, 'dashboardTheme', theme, () => attrs('parameters').dashboardTheme === theme);
      if (!saved || !urlPath) return;
      try {
        const cfg = await h.connection.sendMessagePromise({ type: 'lovelace/config', url_path: urlPath });
        (cfg.views || []).forEach((v) => { v.theme = theme; });
        await h.connection.sendMessagePromise({ type: 'lovelace/config/save', url_path: urlPath, config: cfg });
      } catch (e) { return say(el, 'Theme name saved, but the dashboard could not be changed: ' + ((e && e.message) || e), 'bad'); }
      say(el, '✓ Theme applied', 'ok');
      // redraw the dashboard in place (no app reload)
      try {
        const find = (r, d) => { if (!r || d > 6) return null; const e = r.querySelector && r.querySelector('ha-panel-lovelace'); if (e) return e;
          for (const x of (r.querySelectorAll ? r.querySelectorAll('*') : [])) { if (x.shadowRoot) { const f = find(x.shadowRoot, d + 1); if (f) return f; } } return null; };
        const panel = find(document, 0);
        if (panel && typeof panel._fetchConfig === 'function') panel._fetchConfig(false); else window.location.reload();
      } catch (e) {}
    }

    // ---------------------------------------------------------------- drag between and within the two columns
    // the element that scrolls the dashboard (HA's view or the page), for scrolling while dragging
    function scrollParent() {
      for (let n = card.parentNode || card.host; n; n = n.parentNode || n.host) {
        if (n.nodeType !== 1) continue;
        const oy = getComputedStyle(n).overflowY;
        if ((oy === 'auto' || oy === 'scroll') && n.scrollHeight > n.clientHeight) return n;
      }
      return document.scrollingElement || document.documentElement;
    }
    function initDrag() {
      const box = root.querySelector('.cols');
      let drag = null, ph = null, dy = 0, dx = 0, scroller = null;
      const place = (e) => { const b = box.getBoundingClientRect(); drag.style.top = (e.clientY - dy - b.top) + 'px'; drag.style.left = (e.clientX - dx - b.left) + 'px'; };
      const move = (e) => {
        if (!drag) return;
        place(e);
        const cols = Array.from(root.querySelectorAll('.col'));
        // the column under the pointer (side by side on a wide screen, one above the other on a phone)
        const inside = (c, padY) => { const r = c.getBoundingClientRect(); return e.clientX >= r.left && e.clientX <= r.right && e.clientY >= r.top - padY && e.clientY <= r.bottom + padY; };
        const col = cols.find((c) => inside(c, 0)) || cols.find((c) => inside(c, 40)) || ph.parentNode;
        const others = Array.from(col.querySelectorAll('.sec')).filter((x) => x !== drag);
        const before = others.find((x) => { const r = x.getBoundingClientRect(); return e.clientY < r.top + r.height / 2; });
        if (before) col.insertBefore(ph, before); else col.appendChild(ph);
        if (e.clientY < 60) scroller.scrollBy(0, -14); else if (e.clientY > window.innerHeight - 60) scroller.scrollBy(0, 14);
      };
      const up = () => {
        window.removeEventListener('pointermove', move);
        if (!drag) return;
        ph.parentNode.insertBefore(drag, ph); ph.remove();
        drag.classList.remove('dragging');
        Object.assign(drag.style, { position: '', zIndex: '', width: '', left: '', top: '', pointerEvents: '' });
        drag = null; ph = null;
        saveOrder();
      };
      root.addEventListener('pointerdown', (e) => {
        const grip = e.target.closest('[data-grip]'); if (!grip) return;
        e.preventDefault();
        drag = grip.closest('.sec');
        scroller = scrollParent();
        const r = drag.getBoundingClientRect();
        dy = e.clientY - r.top; dx = e.clientX - r.left;
        ph = document.createElement('div'); ph.className = 'placeholder'; ph.style.height = r.height + 'px';
        drag.parentNode.insertBefore(ph, drag);
        Object.assign(drag.style, { position: 'absolute', zIndex: 999, width: r.width + 'px', pointerEvents: 'none' });
        place(e);
        drag.classList.add('dragging');
        try { if (navigator.vibrate) navigator.vibrate(8); } catch (x) {}
        window.addEventListener('pointermove', move);
        window.addEventListener('pointerup', up, { once: true });
      });
    }

    // ---------------------------------------------------------------- start
    let started = false, redrawTimer = null;
    (async function start() {
      try { await loadMap(); } catch (e) { return card.problem(e.message); }
      const problem = missingThemeVars(card, THEME_VARS); if (problem) return card.problem(problem);
      build();
      root.addEventListener('change', (e) => { onChange(e).catch((x) => console.error('Battman settings', x)); });
      root.addEventListener('click', (e) => { onClick(e).catch((x) => console.error('Battman settings', x)); });
      root.addEventListener('keydown', (e) => { if (e.key === 'Enter' && e.target.matches('input')) e.target.blur(); });
      initDrag();
      started = true;
    })();

    // a setting changed in HA (or a save landed): redraw the sections it shows, at most every 250 ms
    function hassChanged() {
      if (!started || redrawTimer) return;
      redrawTimer = setTimeout(() => { redrawTimer = null; redrawAll(); }, 250);
    }
    return { hassChanged, themeChanged: hassChanged };
  }
}
battmanDefine("battman-settings", BattmanSettingsCard);
battmanPicker("battman-settings", "Battman Settings",
  "Every Battman setting on one page, in sections you can drag between two columns.", "battman-settings");
