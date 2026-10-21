# Battman Live Activity

Shows your battery on your phone's lock screen (iPhone Live Activity via the Home
Assistant Companion app): feed-in price, buy price, today's net $, battery SOC as
the progress bar, the battery mode as the icon and the mode's theme colour as the
bar colour.

## What Battman sets up for you

Nothing to build by hand. On first start Battman creates, from its own blueprints:

| Made by Battman | What it does |
|---|---|
| `script.battman_live_activity_push` | Sends or clears the Live Activity on the chosen phone |
| `automation.battman_live_activity_on_off` | Push when the switch turns on, clear when off, restart every 7 h (iOS ends them after ~8 h), alert on a feed-in spike |
| `automation.battman_live_activity_updates` | Push when SOC / prices / mode change, at most every 2 min, plus a trailing push |
| `automation.battman_live_activity_follow` | Flip the switch from another entity (e.g. a car's ignition), if you set one |

They read their settings from Battman entities, which you set on the Battman
dashboard under **Settings → Live Activity**:

| Setting | Entity | Default |
|---|---|---|
| On/off | `switch.battman_live_activity` | off |
| Phone | `select.battman_live_activity_phone` (HA's notify services, or Off) | **Off** |
| Follow entity | `text.battman_live_activity_follow` (blank = don't follow) | blank |
| On / off states | `text.battman_live_activity_follow_on` / `_follow_off` | `ON` / `OFF` |
| Off after | `number.battman_live_activity_follow_delay` (minutes) | 2 |
| Feed-in spike alert | `number.battman_live_activity_spike_alert` ($/kWh) | 0.30 |

With the phone on **Off** nothing is sent, so a new install is harmless until you pick one.

## Yours to edit; getting Battman's version back

- They're normal automations and a script (in `automations.yaml` / `scripts.yaml`).
  Edit them if you like: Battman never overwrites one that exists.
- **Create Live Activity automations** (button on the Battman device, or the action
  `battman.create_live_activity`) creates any that are **missing**. To reset one to
  Battman's version: delete it, then press the button. The Settings card shows if any are missing.
- Because they're made from Battman's blueprints, fixes in a Battman release reach them
  automatically (Battman updates the blueprints and reloads). If you **take control** of
  one, it stops following the blueprint.
- If HA can't load them (e.g. `automation: !include automations.yaml` was removed from
  configuration.yaml), a Repair says so.

Nothing is made up: a value that isn't available shows as "—", an unknown battery
mode shows a red "?" icon, and with no dashboard theme picked the bar is grey
(`sensor.battman_theme_mode_colours` says why in its `problem` attribute).

## Swapping over from the Smiggles automations

1. Update Battman and restart. Check Settings → Automations: the three
   "Battman Live Activity" automations and the script are there.
2. Battman dashboard → **Settings → Live Activity**: pick your phone, set Follow to your
   car's ignition sensor (`ON` / `OFF`, 2 min).
3. **Disable** (don't delete) the old ones: *Battery Live Activity – car, start, stop,
   update, keep-alive, FIT spike alert* and the script *Battery Live Activity – push*.
4. Pick a theme on the Battman dashboard (Settings → Dashboard options), or the bar is grey.
   This works on a dashboard you've taken control of too.
5. Flip the Live Activity switch on and off, and drive somewhere.
6. When you're happy: delete the old automations and script. Before deleting the helpers
   `input_boolean.battery_live_activity` and `input_text.theme_mode_colours`, open each one →
   ⋮ → **Related** to make sure nothing else uses them.

The tap-through opens `/battman`; change "Open when tapped" in the push script if you
want somewhere else.
