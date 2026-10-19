# Battman

Home battery automation for Home Assistant.

> Early days: Battman is moving over from Smiggles one piece at a time. So far it
> ships themes, a managed dashboard (Finances, Log, Theme) and its pages; the
> battery engine still runs in Smiggles. See [docs/smiggles-inventory.md](docs/smiggles-inventory.md).

## Install (HACS)

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

When you first add the integration, Battman creates a **Battman** dashboard in the
sidebar. It's *managed*: its whole config is

```yaml
strategy:
  type: custom:battman
```

so Battman builds its views (from `custom_components/battman/views/*.yaml`), and
new or changed views arrive with Battman updates. Views so far: **Finances**,
**Curvy** (SOC curve editor), **Pricy** (price curve editor), **Log** and **Theme**
(the theme studio). **Correct Totals** is a hidden view (no
tab), opened from the button at the bottom of the Finances Billing card, for
fixing the buy/sell totals of a period. It asks before changing anything.

To theme the whole managed dashboard, use **Make Active** in the Theme view. It
sets one line in the dashboard config, so the dashboard stays managed:

```yaml
strategy:
  type: custom:battman
  theme: Battman Nord
```

- **Want to edit it?** Edit dashboard → **Take control**. It becomes a normal
  dashboard you own (rename it, change anything). Battman never touches it again.
- **Want a managed one back?** Press **Create dashboard** on the Battman device
  (Settings → Devices & services → Battman), or run the action
  `battman.create_dashboard`. It creates a new managed dashboard at the next free
  address (`/battman`, `/battman-2`, …) and does nothing if one already exists.
- **Removing Battman** deletes managed dashboards only; ones you've taken control
  of stay.

## Pages

Battman serves its pages and images from `/battman/` (`cost-chart.html`,
`cost-compare.html`, `log.html`, `theme-studio.html`, `images/…`), for example:

```yaml
type: iframe
url: /battman/cost-chart.html
```

Pages find their entities through Battman's **entity map** (Battman name →
entity in your HA) and take their colours from a **Battman theme**. If an entity
or theme colour is missing, the page shows an error saying exactly what.

## Entity map (Configure)

Battman names (`buy_total`, `battery_soc`, `pv_string`, …) point at entities in
your HA. The defaults match a Smiggles + Sigenergy + Amber setup. To change one
(say a different inverter): Settings → Devices & services → Battman →
**Configure**. Only the entries you change are stored, so new defaults in later
releases still reach the rest. `pv_string` is a pattern: `{n}` is the string
number (1–12), e.g. `sensor.sigen_inverter_pv{n}_power`.

## Dependencies

Battman's dashboard needs some HACS cards (button-card, card-mod, html-card).
See [DEPENDENCIES.md](DEPENDENCIES.md). Battman raises a Repair if any are missing.

## Updating

New versions appear in Home Assistant under **Settings → Updates** once HACS sees a new GitHub Release. Install the update, then restart Home Assistant.

If you forget the restart, Battman notices within 5 minutes and raises a
**Repair** ("Restart to finish updating Battman") with a Restart button.

## License

MIT
