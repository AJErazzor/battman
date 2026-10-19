# Battman Live Activity

Shows your battery on your phone's lock screen (iPhone Live Activity via the Home
Assistant Companion app): feed-in price, buy price, today's net $, battery SOC as
the progress bar, the battery mode as the icon and the mode's theme colour as the
bar colour.

Battman provides:

| Piece | What it is |
|---|---|
| `switch.battman_live_activity` | On/off switch on the Battman device (keeps its state over restarts) |
| `sensor.battman_theme_mode_colours` | The Battman dashboard theme's mode colours (pick a theme under Settings → Dashboard options) |
| **Battman Live Activity – push** (script blueprint) | Sends or clears the Live Activity on the phone you pick |
| **Battman Live Activity – on/off** (automation blueprint) | Push when the switch turns on, clear when off, restart every 7 h, alert on a feed-in spike |
| **Battman Live Activity – updates** (automation blueprint) | Push when SOC / prices / mode change, at most every 2 min, plus a trailing push |
| **Battman Live Activity – follow an entity** (automation blueprint) | Optional: flip the switch from another entity (e.g. a car's ignition) |

The blueprints are installed into `config/blueprints/automation/battman/` and
`config/blueprints/script/battman/` and updated with each Battman release.
What you make from them are normal automations and scripts: edit them like any other.

Nothing is made up: a value that isn't available shows as "—", an unknown battery
mode shows a red "?" icon, and with no dashboard theme picked the bar is grey.

## Set up

1. Settings → Automations & scenes → **Blueprints**.
2. **Battman Live Activity – push** → Create script. Pick your phone. The entities
   are pre-filled with Battman's defaults; change any that differ. Save.
3. **Battman Live Activity – on/off** → Create automation. Push script = the one from
   step 2. Save.
4. **Battman Live Activity – updates** → Create automation. Push script = the one from
   step 2. Save.
5. Optional: **Battman Live Activity – follow an entity** → Create automation, e.g.
   your car's ignition sensor, `ON` / `OFF`, 2 minutes.
6. Turn on `switch.battman_live_activity` to test. Turn it off to clear.

## Swapping over from the Smiggles automations

Do steps 1–5 above, then:

1. **Disable** (don't delete) the old ones: *Battery Live Activity – car, start, stop,
   update, keep-alive, FIT spike alert* and the script *Battery Live Activity – push*.
2. Make sure a theme is picked on the Battman dashboard (Settings → Dashboard options),
   or the bar will be grey.
3. Flip `switch.battman_live_activity` on and off, and drive somewhere.
4. When you're happy, delete the old automations and script, and the helpers
   `input_boolean.battery_live_activity` and `input_text.theme_mode_colours`.

Differences from the Smiggles version: the tap-through opens `/battman` (set "Open when
tapped" to `/battery-time` to keep the old one), the update automation also pushes when
a value goes unavailable (so the "—" shows), and the built-in iOS fallback colours are gone.
