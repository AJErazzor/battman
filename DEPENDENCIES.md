# Battman dependencies

Battman can't install other add-ons for you. Install these yourself (HACS → Frontend).
Battman checks for the dashboard cards and browser_mod at startup and raises a **Repair** naming any that are missing.

| Dependency | Type | Needed by | Get it |
|---|---|---|---|
| button-card | Dashboard card | Billing and Solar System cards; every Battman card on the Power view | https://github.com/custom-cards/button-card |
| card-mod | Dashboard card | Battery mode, Limits and Overrides cards | https://github.com/thomasloven/lovelace-card-mod |
| modern-circular-gauge | Dashboard card | Gauges card | https://github.com/selvalt7/modern-circular-gauge |
| power-pie-card | Dashboard card | NEM mix card | HACS → Frontend → power-pie-card |
| browser_mod | Integration (HACS) | State card (next-hours popup), Battery mode card (Engine log popup), Overrides card (every popup), Billing card (Correct totals popup) | https://github.com/thomasloven/hass-browser_mod |


Battman ships **Chart.js** 4.4.0 (`www/vendor/`), so the charts on the Log, Cost chart and Cost
compare, Curvy and Pricy cards work without the internet. The only
thing loaded from the internet is **Google Fonts**: the theme studio's font browser, and themes that
turn on a custom font.

The Log, Curvy, Pricy, Cost chart, Cost compare, Settings and Theme studio cards draw themselves.
None of them need extra cards.

Other integrations Battman's cards read (through the entity map):

| Integration | Used for | If it's missing |
|---|---|---|
| Sigenergy (Sigenergy-Local-Modbus), **v1.1.0 or newer** | The engine reads and sets the Sigen by name (`select.sigen_plant_remote_ems_control_mode`, the PV / charging / export limits, battery SOC and capacity, grid status, the battery's rated powers); the cost totals use its total import / export energy; battery power, solar, grid and house figures on the cards | A Repair names any Sigen entity Battman uses that's missing or disabled, and another says if the integration is older than v1.1.0 (the first with every name Battman uses). An install that predates v1.1.0 may keep older entity names after updating: rename them to the names the Repair gives |
| Amber | Current prices (all price views, price grid, State); price forecasts (Pricy overlay, price grid, forecast table, State projection) | Prices: error. Forecasts: Pricy shows a note and works without the forecast part of the overlay |
| HA Companion app | Live Activity blueprints (the phone it shows on) | Only needed if you use the Live Activity |
| Solcast (Solcast PV Forecast) | Solar forecast, by name: `sensor.solcast_pv_forecast_forecast_today` (Curvy overlay and badge; State projection), `sensor.solcast_pv_forecast_forecast_tomorrow` (State projection), `sensor.solcast_pv_forecast_forecast_remaining_today` (the engine's high-consumption check; Gauges) | A Repair names any that's missing or disabled. Curvy and the State popup show a note; Gauges show — |
| OpenNEM | Region generation and demand (its region sensor, e.g. `sensor.opennem_sa`, found by Battman): Battman's NEM sensors and the NEM mix card | The NEM sensors are unknown and say no OpenNEM region was found; the NEM mix card names them |

The Sigenergy integration ships some sensors **disabled**: enable **Available Max Active
Power** (Overrides card; Battman's Repair names it until you do), **Sigen PV Power** (Curvy's
actual-solar overlay), and **PV Power** and **Third-Party PV Power** if you have a third-party
solar inverter (Log card). Settings → Entities → search → Enable.

Battman's own pieces that other parts rely on:

- **Entity map** (`/api/battman/entities`): every Battman page. Change it under Configure.
- **Packages** (`homeassistant: packages: !include_dir_named packages` in configuration.yaml): Battman's
  engine sensors and helpers in `packages/battman/`. Without it, a Repair names what's missing.
- **Themes** (`frontend: themes: !include_dir_merge_named themes` in configuration.yaml): Battman's
  themes in `themes/battman/`. Without it, every Battman page says "no theme" and a Repair says what to add.
- **automations.yaml / scripts.yaml** included in configuration.yaml (HA's default): Battman's engine
  automations and scripts (and the Live Activity ones) are written there. Without them, a Repair.
- **Recorder** (HA's default): Migrate copies the cost odometers' long-term statistics. Without it,
  Migrate still runs and says the statistics weren't copied.
- **Engine log**: `<config>/battman/engine.log`, written by Battman. Before you migrate, the Log card
  reads Smiggles' `<config>/smiggles/solar_debug.log`.
- **NEM sensors** (`sensor.battman_nem_*`, 14 of them, MW): made by Battman from the OpenNEM sensor's
  attributes, because power-pie-card can only read states. They replace hand-made template sensors
  (`sensor.opennem_sa_*`, `sensor.sa_*`): once the NEM mix card checks out, those can go.
- **Battman theme** (`--battman-*` colours): every Battman page shows an error without one.
- **`battman-lib.js`** (`window.BattmanLib`): the Overrides card's rows and popups, the theme studio's dock previews,
  the Billing card's Correct totals popup, and the battery mode colours (`MODE_HUE`) the Log card uses.
