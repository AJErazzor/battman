# Smiggles inventory (for the Battman migration)

Source: `Smiggles-main` zip, 2026-10-19 (progress updated for Battman v0.6.0).
Lists names and structure only — no values or secrets.
Folders named `delete/` are treated as retired and left out unless noted.

## 1. What Smiggles is made of

| Folder | Live files | What it is |
|---|---|---|
| `packages/` | 8 | The engine: helpers, template sensors, cost odometers, rules, Amber forecast, scenes |
| `automations/` | 9 | Main loop trigger, watchdog, Sigen mode/curtail, SAPN override, log writer/prune, curve copy, timer default |
| `scripts/` | 3 | `script.solarsystemcontrol` (the main control script, v1.0.22), timer add, load filtered log |
| `www/smiggles/` | 9 | HTML pages + `ssc-lib.js` (see section 5) |
| `UI/` | ~30 | Dashboard YAML: overrides, battery mode, state, limits, cost, logs, history, sandpit |
| `themes/` | 20 + 1 | ✅ Moved — shipped in Battman v0.2.0 |
| `.github/` | 1 | Release workflow (PR + squash merge; see section 8) |

## 2. Entities Smiggles creates (63 found in the repo)

**Core sensors**
- `sensor.solarsystemcontrolparameters` — the settings/override store (attributes, updated by event)
- `sensor.solarsystemcontrolrun` — run state
- `sensor.solarsystemcontrolbuyrules`, `sensor.solarsystemcontrolsellrules`
- `sensor.solarsystemcontrolbuytotal`, `…selltotal`, `…networkaccessfee` — cost odometers (long-term statistics matter)
- `sensor.solarsystemcontrolamberforecast`
- `sensor.solarsystemcontrolpowerproviderbuy`, `…powerprovidersell`
- `sensor.solarsystemcontrolload30mavg`, `…load30madv`
- `sensor.solarsystemcontrolestimatedpricetrue`, `binary_sensor.solarsystemcontrolestimatedprice`
- `sensor.solar_system_control_soc_curves`, `sensor.solar_system_control_price_curves` (note: underscore spelling)
- `sensor.solar_system_control_debug_log`, `sensor.solarsystemcontroldebuglogfiltered`
- `sensor.solarsystemstatus`, `sensor.gridpower`, `sensor.sockwh`, `sensor.solarremainingtoday10` (no prefix)

**Helpers** (all in `solarsystemcontrolmodule.yaml`)
- `input_number.solarsystemcontrol*` × 29 — prices, SOC targets/offsets, spike rules, soak, bill day, network charge, timing
- `input_boolean.solarsystemcontrol*` × 5 — enable, no-export, buy/sell SOC pro-rate, debug log load
- `input_datetime.solarsystemcontrol*` × 4 — last run, watchdog reset, debug log start/end
- `input_select.solarsystemcontrolmode`, `input_text.solarsystemcontrolstorage`
- `timer.solarsystemoverridetimer`

**Scripts**: `script.solarsystemcontrol`, `script.solarsystem_override_timer_add`,
`script.solarsystemcontrolloadfilteredsolarlog`, `script.ssc_apply_scene`

## 3. Events (the internal "message bus")

| Event | Used in |
|---|---|
| `solarsystemcontrolparametersupdate` | 9 files — cards, ssc-lib, packages (sets parameters attributes) |
| `solarsystemcontroltotalattribute` | 6 files — cost odometers |
| `solarsystemcontrolbuyrulesattribute`, `…sellrulesattribute` | 4 files each |
| `solarsystemcontrolpowerproviderupdate` | 2 files |
| `solarsystemcontrolrunupdate` | 1 file |
| `solar_system_control_soc_curves_update`, `…price_curves_update` | 2 files each — curve editors |

All of these get Battman names when the code that fires *and* the code that listens move together.

## 4. Other integrations Smiggles depends on (→ entity map, never renamed)

| Integration | Entities used | Examples |
|---|---|---|
| Sigenergy | 26 | `sensor.sigen_plant_battery_state_of_charge` (14 files), `…daily_grid_export/import_energy`, `…battery_power`, `number.sigen_plant_*_limit`, `select.sigen_plant_remote_ems_control_mode` |
| Amber | 23 | `sensor.amber_5min_current_general_price` / `…feed_in_price` (23 files each), `…billing_interval_forecasts_*`, `…5min_period_1..8_*` |
| Solcast | 4 | `sensor.solcast_pv_forecast_forecast_today` / `…remaining_today` / `…tomorrow` / `…next_hour` |
| OpenNEM | 8 | `sensor.opennem_sa_*` (SA energy mix card only) |
| Fronius | 1 | `switch.fronius_soft_limit_enable` |
| Core | 1 | `sun.sun` |

Note: both `sensor.sigen_plant_battery_state_of_charge` and `sensor.sigen_inverter_battery_state_of_charge` are used — worth choosing one.

## 5. Web pages and what they need

| File (Smiggles) | Battman entities it reads | Events | `--smiggles-*` vars | Status |
|---|---|---|---|---|
| `cost-chartv7.html` | buy/sell/fee totals, parameters, Sigen daily export/import | — | 3 | ✅ `/battman/cost-chart.html` (v0.3.0) |
| `cost-comparev7.html` | buy/sell/fee totals, parameters | — | 3 | ✅ `/battman/cost-compare.html` (v0.5.0, Finances view) |
| `correct_energy4.html` | buy/sell totals | — | 0 | ✅ `/battman/correct-energy.html` (v0.7.0, Correct Totals subview from the Finances Billing card). Wasn't linked from any Smiggles dashboard. Writes the totals' attributes directly; becomes a Battman action when the odometers move |
| `solar_log_viewer.html` | debug log start/end | — | 0 | ✖ retired — not used by the log page, left behind |
| `smiggles-logv6.html` | debug log start/end + file, load-log script, mode, `gridpower`, `load30m`, Sigen power + PV strings, Amber current ×2 | — | 14 | ✅ `/battman/log.html` (v0.6.0, Log view) |
| `priceeditorv37.html` (live; zip had v35) | price curves, high consumption, load30mavg, Amber current + forecasts | price_curves_update | 23 | ✅ `/battman/pricy.html` (v0.7.0, Pricy view) |
| `editorv139.html` (live; zip had v137) | SOC curves, mode, high consumption, load30mavg, `script.solarsystemcontrol`, Sigen SOC + Sigen-only PV, Amber current, Solcast | soc_curves_update | 23 | ✅ `/battman/curvy.html` (v0.7.0, Curvy view) |
| `theme-studiov4.html` | — | — | 27 | ✅ `/battman/theme-studio.html` (v0.6.0, Theme view) |
| `ssc-lib.js` | (passed in by cards) | parameters update (via cards) | 88 | copy as `/battman/battman-lib.js` for the studio's previews (v0.6.0); the override cards still use Smiggles' copy |

## 6. Gaps — referenced but not in the repo

These live only in your HA (UI-created or in `configuration.yaml`):
- `sensor.solarsystemcontrolload30m` — used by the 30-min load averages, log page and history dashboard
- `shell_command.solar_debug_append`, `shell_command.solar_debug_load_filtered` — debug log
- Script IDs: the repo's script files are UI-format (no ID line), so their IDs come from `scripts.yaml` in HA
- Live dashboards: the repo's `UI/` YAML points at **older** page versions
  (`cost-chartv3`, `cost-comparev3`, `editorv42`, `priceeditorv9`) than `www/` holds (v7, v7, v137, v35),
  so the repo dashboards are behind what's on screen.

## 7. Move order (dependencies first)

1. ✅ Themes (v0.2.0)
2. ✅ Entity map + cost chart (v0.3.0)
3. ✅ Managed dashboard + Finances view with cost-compare (v0.4.0 – v0.5.0)
4. ✅ Configure screen (entity map) + restart prompt (v0.6.0)
5. ✅ Log page + Log view; Theme studio + Theme view, Save to HA (v0.6.0)
6. ✅ `correct_energy` → Correct Totals (v0.7.0)
7. Override cards (`battman-lib.js` in use by cards) — needs map entries for timer, parameters, SOC, capacity, forecast; browser_mod
8. ✅ Curve editors → Curvy and Pricy (v0.7.0)
9. Remaining dashboards as Battman views
   - ✅ Settings (v0.8.0). WLED colour code dropped. `input_text.theme_mode_colours` replaced by
     Battman's `sensor.battman_theme_mode_colours`.
   - ✅ First automation set: the iPhone Live Activity (6 automations + push script) → Battman
     blueprints + `switch.battman_live_activity` (v0.9.0). The car trigger became the generic
     "follow an entity" blueprint. See docs/live-activity.md.
10. Engine: packages, scripts, automations → blueprints / Battman entities, one area at a time, each with an entity cutover (Smiggles stays in charge of the battery until then)

## 8. Release conventions — Smiggles vs Battman

| | Smiggles | Battman |
|---|---|---|
| Path to main | PR + **squash and merge** | PR + squash and merge |
| Release | every merge (patch unless told) | only when a commit starts `major:` / `minor:` / `patch:` |
| Version in files | tag only | tag + `manifest.json` |
