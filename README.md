# Battman

Home battery automation for Home Assistant.

Battman controls a Sigenergy battery from Amber prices and a Solcast solar forecast. It ships its
engine (as Home Assistant blueprints and packages you can open and trace), a dashboard (Power,
Curvy, Pricy, Finances, Settings, Log, Theme), its cards, pages and themes. It started as
[Smiggles](https://github.com/biggls73/Smiggles) and can take over from it (see below).

## Install (HACS)

Before you start, have these in place (the full list, and why: [DEPENDENCIES.md](DEPENDENCIES.md)):

- The integrations it reads: Sigenergy (Sigenergy-Local-Modbus), Amber, Solcast, and optionally OpenNEM.
- The HACS cards it draws with (button-card, card-mod, modern-circular-gauge, power-pie-card) and browser_mod.
- These lines in `configuration.yaml` (Battman writes its engine and themes into these folders; a
  Repair tells you if a line is missing):

```yaml
homeassistant:
  packages: !include_dir_named packages
frontend:
  themes: !include_dir_merge_named themes
```

Then:

1. HACS → ⋮ → **Custom repositories** → add `https://github.com/AJErazzor/battman`, category **Integration**.
2. Install **Battman**, then restart Home Assistant.
3. Settings → Devices & services → **Add integration** → Battman.

## Themes

Battman installs its themes (Battman Coffee, Battman OG, Battman Abyss, …) into
`config/themes/battman/` and reloads themes automatically. Your `configuration.yaml`
needs:

```yaml
frontend:
  themes: !include_dir_merge_named themes
```

The shipped themes in that folder belong to Battman and are replaced on every
update, so don't edit them.

**Your own themes** go in `config/themes/battman/custom/`. Battman never touches
that folder, not on update and not when Battman is removed. The Theme studio's
**Save to HA** button writes there for you (admins only) and reloads themes.
Names must start with `Battman `, and can't be the name of a theme Battman ships. Battman themes define only `--battman-*` colours: anything still using
`--smiggles-*` won't get colours on a Battman theme, so keep Smiggles views on
Smiggles themes until they move.

## The Battman dashboard

When you first add the integration, Battman creates a **Battman** dashboard at
`/battman` in the sidebar, with all of Battman's views written into it
(from `custom_components/battman/views/*.yaml`, entity names filled from the entity map).
It's an ordinary dashboard and it's **yours from the start**: edit, rearrange, delete views.

Views, in order: **Power** (your control centre, built from Battman cards), **Curvy** (SOC
curve editor), **Pricy** (price curve editor), **Finances** (cost chart, cost compare,
Billing and Solar System cards), **Settings** (every setting on one page: drag its sections
between two columns, the order is kept per device), **Log** and **Theme** (the theme studio).
To fix a period's buy and sell totals, use **Correct Totals** on the Billing card: it opens a
popup and asks before changing anything.

What updates with Battman releases: every **Battman card** on it (`custom:battman-<id>`,
including Curvy, Pricy, Log, the Theme studio and the Finances cards) and the pages they show. What doesn't:
the views themselves (which cards are on them, and their layout). Battman is moving
everything into cards so less and less of it is fixed.

- **Want a fresh one?** Delete the dashboard (Settings → Dashboards), then press
  **Create dashboard** on the Battman device (Settings → Devices & services → Battman),
  or run the action `battman.create_dashboard`. If something is already at `/battman`,
  nothing is created and the message says so.
- **Theme:** pick one under **Settings → Dashboard options**, or use **Make Active** in
  the Theme view (they do the same thing).

## Pages

Battman serves its pages and images from `/battmanfiles/` (`curvy.html`, `pricy.html`,
`images/…`), for example:

```yaml
type: iframe
url: /battmanfiles/curvy.html
```

The Log, Cost chart, Cost compare, Settings and Theme studio are cards that draw themselves
(`custom:battman-log` and so on): add them like any card, no frame needed.

Pages and cards find their entities through Battman's **entity map** (Battman name →
entity in your HA) and take their colours from a **Battman theme**. If an entity
or theme colour is missing, the page or card shows an error saying exactly what.

## Theme mode colours sensor

`sensor.battman_theme_mode_colours` holds the eight mode colours (green, yellow, blue,
orange, red, purple, teal, amber) of the Battman dashboard's theme as hex, e.g. `{"green":"#a3be8c","yellow":"#e9d8a6",…}`, with each
colour also as an attribute. It's for things that can't read theme colours, like an
iPhone Live Activity. It updates by itself when the dashboard theme changes. Until a
dashboard theme is picked (or if a colour can't be read) it's `unknown`, and the
`problem` attribute says why.

## The engine, and moving from Smiggles

Battman's engine is Smiggles' engine ported like for like (same decisions, renamed): template
sensors and helpers in `packages/battman/`, and automations and scripts made from Battman's
blueprints. It runs while `binary_sensor.battman_in_charge` is on. Today the way to put it in
charge is **Migrate from Smiggles** (`battman.migrate_from_smiggles`), which turns Smiggles off,
copies everything across and puts Battman in charge. **Hand back to Smiggles** reverses it.
Details: [docs/engine.md](docs/engine.md). Step by step: [docs/migration.md](docs/migration.md).

**Starting values.** On a fresh install every setting starts at its default and the SOC and price
curves start as Battman's factory curves (`custom_components/battman/factory_curves.yaml`, the same
ones Curvy's and Pricy's **Factory defaults** buttons load). Your own settings and curves are never
replaced by them.

**30-minute load average.** `sensor.battman_load_30m_avg` is a Statistics sensor Battman makes from
home power (`home_power` in the entity map): the mean over the last 30 minutes. When it has no
value the engine skips its high-consumption check and says so in the engine log.

Battman writes `packages/battman/` on every update (don't edit those files). HA reads that folder
when `configuration.yaml` has `homeassistant: packages: !include_dir_named packages`; if it doesn't,
a Repair says so.

## NEM sensors

`sensor.battman_nem_*` (MW): the region's generation by source (wind, rooftop and utility
solar, imports, battery, gas CCGT / OCGT / steam / recip, distillate) and where it goes
(exports, battery charging, total supply, consumers), made from the OpenNEM sensor picked
as `opennem` under Configure. A source OpenNEM doesn't report is unknown, never 0.

## Battman cards

Cards you can add to any dashboard (Add card → search "Battman"), and that update
with Battman releases. Each is a plain YAML file you can copy and try changes on.
See [docs/cards.md](docs/cards.md).

**Battman Image** (`custom:battman-image`) shows any of Battman's images, or your own from
`config/battman/images/`, with fit, position and size options, and different settings for phones
or dark mode. See [Battman Image](docs/cards.md#battman-image).

## Live Activity

Your battery on your phone's lock screen. Battman creates the automations and script
for it (from its own blueprints) and keeps them updated; you pick the phone and what
it follows on the Battman dashboard, **Settings → Live Activity**. See
[docs/live-activity.md](docs/live-activity.md).

## Entity map (Configure)

Battman names (`buy_total`, `battery_soc`, `pv_string`, …) point at entities in
your HA. The defaults match a Sigenergy + Amber + Solcast setup. To change one
(say a different inverter): Settings → Devices & services → Battman →
**Configure**. Only the entries you change are stored, so new defaults in later
releases still reach the rest. `pv_string` is a pattern: `{n}` is the string
number (1–12), e.g. `sensor.sigen_inverter_pv{n}_power`.

## Dependencies

Battman's dashboard needs some HACS cards (button-card, card-mod, and a few more) and browser_mod.
See [DEPENDENCIES.md](DEPENDENCIES.md). Battman raises a Repair if any are missing.

## Removing Battman

Deleting the Battman integration takes away what Battman wrote: its engine and Live Activity
automations and scripts (by their ids; everything else in `automations.yaml` / `scripts.yaml`
stays), `packages/battman/` and the entities it made, its blueprints and its shipped themes. It
keeps the engine log (`battman/engine.log`), your own cards, images and themes, and your Battman
dashboard. A notification lists what was removed.

## Updating

New versions appear in Home Assistant under **Settings → Updates** once HACS sees a new GitHub Release. Install the update, then restart Home Assistant.

If you forget the restart, Battman notices within 5 minutes and raises a
**Repair** ("Restart to finish updating Battman") with a Restart button.

## License

MIT
