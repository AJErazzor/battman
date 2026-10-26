# Battman's engine

Battman's engine is Smiggles' engine, ported like for like: the same templates, the same
decisions, the same Sigen actions. Only the names changed. `tools/port_smiggles.py` does the
port from a Smiggles checkout, and the tests run both engines side by side to prove they decide
the same (see *How it's proved* below).

## Where the pieces live

| Piece | In Battman | Was in Smiggles |
|---|---|---|
| Settings, overrides, run data, rules, power provider, cost odometers, curves, engine log sensor, estimated price | Template sensors in `packages/battman/` (written by Battman) | `packages/solarsystemcontrol*.yaml` |
| Helpers: enable, no export, mode, high consumption, override timer | Same package folder, `battman_helpers.yaml` | `solarsystemcontrolmodule.yaml` |
| The engine script and the apply-scene script | `scripts.yaml`, made from Battman's blueprints | `scripts/SolarSystemControl.yaml`, `ssc_scenes.yaml` |
| The automations (main loop, watchdog, Sigen mode, curtail, SAPN override, override timer start, copy curves, armed scene) | `automations.yaml`, made from Battman's blueprints | `automations/` |
| The log file | `<config>/battman/engine.log`, written by Battman itself | `shell_command` + LogWriter / PruneLog |

Battman rewrites `packages/battman/` and the blueprints on every update. The automations and
scripts made from the blueprints follow the blueprints. Battman never edits those automations or
scripts after making them, so you can open one, see its traces, or take control of it.

## In charge, or not

`binary_sensor.battman_in_charge` decides whether Battman's engine does anything. Every engine
automation checks it first, and so does every trigger-based engine sensor. Until you migrate it's
off, and Battman's engine does nothing at all: no runs, no Sigen actions, no sensor changes.

- **Migrate from Smiggles** turns it on (see [migration.md](migration.md)).
- **Hand back to Smiggles** turns it off.
- While it's on, a Smiggles automation that comes back on (by hand, or after a restart) is turned
  straight back off, with a notification.

The entity map follows the engine in charge. Before you migrate, the engine entries (settings,
odometers, mode, curves, rules, events) point at Smiggles' entities, so the cards work on Smiggles.
After you migrate they point at Battman's. Amber's entries are on the Configure screen as before;
Sigen and Solcast are used by name, and OpenNEM's region sensor is found automatically.

## Names

| Smiggles | Battman |
|---|---|
| sensor.solarsystemcontrolparameters | sensor.battman_parameters |
| sensor.solarsystemcontrolrun | sensor.battman_run |
| sensor.solarsystemcontrolbuyrules / sellrules | sensor.battman_buy_rules / sell_rules |
| sensor.solarsystemcontrolbuytotal / selltotal | sensor.battman_buy_total / sell_total |
| sensor.solarsystemcontrolnetworkaccessfee | sensor.battman_network_fee |
| sensor.solarsystemcontrolpowerproviderbuy / sell | sensor.battman_power_provider_buy / sell |
| sensor.solar_system_control_soc_curves / price_curves | sensor.battman_soc_curves / price_curves |
| sensor.solar_system_control_debug_log | sensor.battman_engine_log |
| binary_sensor.solarsystemcontrolestimatedprice | binary_sensor.battman_estimated_price |
| sensor.gridpower, sensor.solarsystemcontrolload30mavg | sensor.battman_grid_power, sensor.battman_load_30m_avg (a Statistics sensor of home power since v0.19.0) |
| input_boolean.solarsystemcontrolenable / noexport | input_boolean.battman_enable / no_export |
| input_select.solarsystemcontrolmode | input_select.battman_mode |
| input_number.solarsystemcontrolhighconsumption | input_number.battman_high_consumption |
| timer.solarsystemoverridetimer | timer.battman_override_timer |
| script.solarsystemcontrol, script.ssc_apply_scene | script.battman_engine, script.battman_apply_scene |
| events solarsystemcontrolparametersupdate, …runupdate, …buyrulesattribute, …sellrulesattribute, …totalattribute, …powerproviderupdate, solar_system_control_*_curves_update, SolarSystemControlDebugLog | battman_parameters_update, battman_run_update, battman_buy_rules_update, battman_sell_rules_update, battman_totals_update, battman_power_provider_update, battman_*_curves_update, battman_engine_log |

Amber's entities come from the entity map, so another install can point them elsewhere.
Sigen's and Solcast's are named directly, in the engine and on the cards (e.g. `select.sigen_plant_remote_ems_control_mode`,
`sensor.solcast_pv_forecast_forecast_remaining_today`); at startup Battman checks each one it
uses is there, and a Repair names any that isn't. Sigen needs its integration at v1.1.0 or newer.
If Solcast's remaining-today figure has no value, the engine skips its "enough sun left?" check (it
used to read it as 0 kWh, which could set off the No Sun panic) and its log says so.
Removed as unused: the inverter rated power (`inverterRatedPower`), next-hour solar.

## What's different from Smiggles

Only these:

1. **Names**, as above.
2. **The in-charge check** at the top of every engine automation and trigger sensor.
3. **Copy curves to next month** calls `persistent_notification.create`. The Smiggles repo's version
   calls `notify. Notify`, which HA rejects, so with that file the automation doesn't load. (A.J.'s
   own copy does load, so it has been running.) Battman's copies this month's curves into next
   month at 8pm on the last day of the month. Turn
   `automation.battman_engine_copy_curves_to_next_month` off if you don't want that.
4. **The log** is written by Battman (no shell commands): `time|message` as before, but with the
   message's line breaks kept as `\n`; same 4032-line weekly trim (Sundays 03:00). The Log card reads it through `/api/battman/log`.
5. **The log text has headings instead of emoji** (v0.17.1): `Run:`, `Mode:`, `Prices:`, `Battery:`,
   `SOC Limits:`, `Solar:`, `Actions:`, `Sell Forecasts:`, `Buy Forecasts:`, `Version:`, `Debug:`;
   the price-spike 💰 markers are `(Spike 1)` / `(Spike 2)`, `(Bad! ⛅)` is `(Bad!)`. The exact list is
   `tools/smiggles_log_text.py`; the tests apply it to Smiggles' original too and compare the logs.
   The Engine log popup and the Log card draw the log with one renderer (`www/battman-enginelog.js`),
   which also reads Smiggles' emoji lines (the ones copied in at migration).
6. **Grid power and load average** are unavailable (not 0) when what they're made from is missing.
7. **The load average is Battman's own** (v0.19.0): a Statistics sensor of home power with the
   settings Smiggles' helper had (mean, 30 minutes, 2 decimals), not a copy of that helper. When it
   has no value the engine skips the high-consumption check (Smiggles read it as 0) and the log's
   SOC Limits section says `Load average: missing`.
8. **Settings and curves have starting values** (v0.19.0): the parameters and curve sensors also
   work themselves out when HA starts or templates reload, so a fresh install has every setting's
   default and the factory curves (`factory_curves.yaml`). Values you have are kept. The engine
   reads its settings with no fallback numbers of its own.

Kept as they are (worth knowing): the curtail automation sets the export limit back to **18.2 kW**
and Sigen mode resets the PV limit to **20 kW**: both are fixed numbers in Smiggles (your system's).

## Not ported (unused by the engine)

From Smiggles' module package: the 27 other `input_number`s (the engine reads its settings from
the parameters sensor), the prorate and debug-log-load booleans, the last-run / watchdog-reset /
debug-log-range datetimes, the storage text, SOCkwh, Load30mAdv, EstimatedPriceTrue,
SolarRemainingToday10, SolarSystemStatus, the shell commands and the command-line sensor. Also
the Amber forecast package (Battman's cards don't use it). They stay in Smiggles until you remove it.

The high-consumption threshold the engine uses is the parameters sensor's
`needyTriggerConsumption`. The Curvy and Pricy pages read `input_number…highconsumption` instead;
that's how Smiggles is too (ported as `input_number.battman_high_consumption`).

## How it's proved

`tests/test_v0170_engine.py` loads Smiggles' original files (`tests/fixtures/smiggles_engine/`) and
Battman's port into one test Home Assistant:

- **The engine script**: 300 worlds (battery level, buy and sell prices, estimates, forecasts,
  solar forecast, home load, grid status, month and time of day, curves, rules, every override
  and net target). Both engines run on each; mode, no-export, the full run record and the log
  text must be identical. All 8 modes are reached. A one-line change to Battman's copy makes it fail.
- **Sigen mode** (every mode from two starting modes), **curtail**, **SAPN override**, **override
  timer start**, **watchdog** (overrides cleared when the timer ends), **apply scene**: the same
  Sigen actions and the same settings changes.
- **In charge off**: nothing runs and nothing reaches Sigen.
- **Migrate and Hand back**: see [migration.md](migration.md).
