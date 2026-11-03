# Battman's engine

Battman's engine decides the battery mode from Amber prices and the Solcast forecast, and acts on
the Sigenergy battery. It's template sensors and helpers plus a script and automations — all plain
Home Assistant you can open, trace and take control of.

## Where the pieces live

| Piece | Where |
|---|---|
| Settings, overrides, run data, rules, power provider, cost odometers, curves, engine log sensor, estimated price | Template sensors in `packages/battman/` (written by Battman) |
| Helpers: enable, no export, mode, high consumption, override timer | `packages/battman/battman_helpers.yaml` |
| The engine script and the apply-scene script | `scripts.yaml`, made from Battman's blueprints |
| The automations (main loop, watchdog, Sigen mode, curtail, SAPN override, override timer start, copy curves, armed scene) | `automations.yaml`, made from Battman's blueprints |
| The log file | `<config>/battman/engine.log`, written by Battman itself |

Battman rewrites `packages/battman/` and the blueprints on every update. The automations and
scripts made from the blueprints follow the blueprints. Battman never edits those automations or
scripts after making them, so you can open one, see its traces, or take control of it.

## Enabled, or not

The engine runs while **Active** (`input_boolean.battman_enable`) is on.

The entity map holds Battman's engine entities (settings, odometers, mode, curves, rules, events),
pointing at Battman's own entities; cards and pages use the names on it. Sigen, Amber and Solcast
are used by name, and OpenNEM's region sensor is found automatically.

## Entities it uses by name

Sigen's, Amber's (amber2mqtt) and Solcast's entities are named directly, in the engine and on the
cards (e.g. `select.sigen_plant_remote_ems_control_mode`, `sensor.amber_5min_current_general_price`,
`sensor.solcast_pv_forecast_forecast_remaining_today`); at startup Battman checks each one it
uses is there, and a Repair names any that isn't. Sigen needs its integration at v1.1.0 or newer.
If Solcast's remaining-today figure has no value, the engine skips its "enough sun left?" check and
its log says so.

## Behaviours worth knowing

1. **The log** is written by Battman: `time|message`, with the message's line breaks kept as `\n`;
   a 4032-line weekly trim (Sundays 03:00). The Log card reads it through `/api/battman/log`.
2. **The log text has headings**: `Run:`, `Mode:`, `Prices:`, `Battery:`, `SOC Limits:`, `Solar:`,
   `Actions:`, `Sell Forecasts:`, `Buy Forecasts:`, `Version:`, `Debug:`; price spikes are
   `(Spike 1)` / `(Spike 2)`. The Engine log popup and the Log card draw it with one renderer
   (`www/battman-enginelog.js`).
3. **Grid power and load average** are unavailable (not 0) when what they're made from is missing.
4. **The load average** is a Statistics sensor of home power (mean, 30 minutes, 2 decimals). When it
   has no value the engine skips the high-consumption check and the log's SOC Limits section says
   `Load average: missing`.
5. **Settings and curves have starting values**: the parameters and curve sensors work themselves
   out when HA starts or templates reload, so a fresh install has every setting's default and the
   factory curves (`factory_curves.yaml`). Values you have are kept. The engine reads its settings
   with no fallback numbers of its own.
6. **Fixed numbers**: the curtail automation sets the export limit back to **18.2 kW** and Sigen
   mode resets the PV limit to **20 kW**.

The high-consumption threshold the engine uses is the parameters sensor's `needyTriggerConsumption`.
The Curvy and Pricy pages read `input_number.battman_high_consumption` instead.

## How it's tested

The tests drive the engine across 300 generated worlds (battery level, buy and sell prices,
estimates, forecasts, solar, home load, grid status, month and time of day, curves, rules, every
override and net target) and snapshot its decisions — mode, no-export, the full run record and the
log text — so any change that moves a decision is caught. Separate tests cover Sigen mode (every
mode), curtail, SAPN override, override-timer start, watchdog (overrides cleared when the timer
ends) and apply scene: the Sigen actions and settings changes they produce.
