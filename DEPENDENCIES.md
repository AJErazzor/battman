# Battman dependencies

Battman can't install other add-ons for you. Install these yourself (HACS → Frontend).
Battman checks for the dashboard cards and browser_mod at startup and raises a **Repair** naming any that are missing.

| Dependency | Type | Needed by | Get it |
|---|---|---|---|
| button-card | Dashboard card | Finances view (Billing, Financials/ROI cards); every Battman card on the Power view | https://github.com/custom-cards/button-card |
| card-mod | Dashboard card | All Battman views (full-bleed page cards, header); Limits card | https://github.com/thomasloven/lovelace-card-mod |
| html-card | Dashboard card | Finances view header | https://github.com/PiotrMachowski/Home-Assistant-Lovelace-HTML-card |
| modern-circular-gauge | Dashboard card | Gauges card | https://github.com/selvalt7/modern-circular-gauge |
| power-pie-card | Dashboard card | NEM mix card | HACS → Frontend → power-pie-card |
| browser_mod | Integration (HACS) | State card (tap opens the next-hours popup) | https://github.com/thomasloven/hass-browser_mod |

browser_mod is also what the battery mode stack and override cards will use when they move.

Battman pages also load from the internet:

- **Chart.js** (cdnjs / jsdelivr): charts on the cost, compare, log, Curvy and Pricy pages.
- **Google Fonts**: only the theme studio's font browser, and themes that turn on a custom font.

The Log and Theme views are plain iframe pages and need no extra cards.

Other integrations Battman's pages read (through the entity map):

| Integration | Used for | If it's missing |
|---|---|---|
| Sigenergy (Sigenergy-Local-Modbus) | Battery SOC, power, grid, solar (Log, Finances, Curvy) | Page shows which entity is missing |
| Amber | Current prices (all price views, price grid, State); price forecasts (Pricy overlay, price grid, forecast table, State projection) | Prices: error. Forecasts: Pricy shows a note and works without the overlay |
| HA Companion app | Live Activity blueprints (the phone it shows on) | Only needed if you use the Live Activity |
| Solcast | Solar forecast (Curvy overlay and badge; State projection; Gauges' remaining-today 10% figure) | Curvy and the State popup show a note and work without it; Gauges show — |
| OpenNEM | Region generation and demand (`opennem` in the map, e.g. `sensor.opennem_sa`): Battman's NEM sensors and the NEM mix card | The NEM sensors are unavailable and the NEM mix card names them |

The Sigenergy integration ships some sensors **disabled**: enable **Sigen PV Power**
(Curvy's actual-solar overlay), and **PV Power** and **Third-Party PV Power** if you
have a third-party solar inverter (Log page). Settings → Entities → search → Enable.

Battman's own pieces that other parts rely on:

- **Entity map** (`/api/battman/entities`): every Battman page. Change it under Configure.
- **NEM sensors** (`sensor.battman_nem_*`, 14 of them, MW): made by Battman from the OpenNEM sensor's
  attributes, because power-pie-card can only read states. They replace hand-made template sensors
  (`sensor.opennem_sa_*`, `sensor.sa_*`): once the NEM mix card checks out, those can go.
- **Battman theme** (`--battman-*` colours): every Battman page shows an error without one.
- **`battman-lib.js`**: the theme studio's live previews (the override cards still use Smiggles' `ssc-lib.js` until they move).
- **Smiggles curve stores, events and control script** (`soc_curves`, `price_curves`, their `…_update_event`s, `control_script`): Curvy and Pricy read and save curves through Smiggles, which stays in charge of the battery.
- **Debug log file + load script** (`debug_log_file`, `load_debug_log_script` in the map): the Log page's log panel. Both still come from Smiggles.
