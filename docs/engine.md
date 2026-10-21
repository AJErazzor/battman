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
After you migrate they point at Battman's. The other integrations' entries (Sigen, Amber, Solcast,
OpenNEM) are on the Configure screen as before.

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
| sensor.gridpower, sensor.solarsystemcontrolload30mavg | sensor.battman_grid_power, sensor.battman_load_30m_avg |
| input_boolean.solarsystemcontrolenable / noexport | input_boolean.battman_enable / no_export |
| input_select.solarsystemcontrolmode | input_select.battman_mode |
| input_number.solarsystemcontrolhighconsumption | input_number.battman_high_consumption |
| timer.solarsystemoverridetimer | timer.battman_override_timer |
| script.solarsystemcontrol, script.ssc_apply_scene | script.battman_engine, script.battman_apply_scene |
| events solarsystemcontrolparametersupdate, …runupdate, …buyrulesattribute, …sellrulesattribute, …totalattribute, …powerproviderupdate, solar_system_control_*_curves_update, SolarSystemControlDebugLog | battman_parameters_update, battman_run_update, battman_buy_rules_update, battman_sell_rules_update, battman_totals_update, battman_power_provider_update, battman_*_curves_update, battman_engine_log |

Sigen, Amber and Solcast entities come from the entity map, so another install can point them
elsewhere. New map entries for the engine: `ems_control_mode`, `rated_charging_power`,
`rated_discharging_power`, `inverter_rated_power`, `grid_connection_status`,
`total_imported_energy`, `total_exported_energy`, `solcast_next_hour`.

## What's different from Smiggles

Only these:

1. **Names**, as above.
2. **The in-charge check** at the top of every engine automation and trigger sensor.
3. **Copy curves to next month** calls `persistent_notification.create`. Smiggles' version calls
   `notify. Notify`, which HA rejects, so in Smiggles that automation never loads and has never run.
   In Battman it loads, so **at 8pm on the last day of each month it will copy this month's curves
   into next month**, as Smiggles intended. Turn `automation.battman_engine_copy_curves_to_next_month`
   off if you don't want that.
4. **The log** is written by Battman (no shell commands); same line format, same 4032-line
   weekly trim (Sundays 03:00). The Log page reads it through `/api/battman/log`.
5. **Grid power and load average** are unavailable (not 0) when what they're made from is missing.

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
