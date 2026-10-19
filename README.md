# Battman

Home battery automation for Home Assistant.

> Early days: this is a skeleton integration. No entities yet.

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

That folder belongs to Battman and is replaced on every update, so don't edit the
files there. Battman themes define only `--battman-*` colours: anything still using
`--smiggles-*` won't get colours on a Battman theme, so keep Smiggles views on
Smiggles themes until they move.

## The Battman dashboard

When you first add the integration, Battman creates a **Battman** dashboard in the
sidebar. It's *managed*: its whole config is

```yaml
strategy:
  type: custom:battman
```

so Battman builds its views, and new or changed views arrive with Battman updates.

- **Want to edit it?** Edit dashboard → **Take control**. It becomes a normal
  dashboard you own (rename it, change anything). Battman never touches it again.
- **Want a managed one back?** Press **Create dashboard** on the Battman device
  (Settings → Devices & services → Battman), or run the action
  `battman.create_dashboard`. It creates a new managed dashboard at the next free
  address (`/battman`, `/battman-2`, …) and does nothing if one already exists.
- **Removing Battman** deletes managed dashboards only; ones you've taken control
  of stay.

## Pages

Battman serves its pages from `/battman/`, for example the cost chart:

```yaml
type: iframe
url: /battman/cost-chart.html
```

Pages find their entities through Battman's **entity map** (Battman name →
entity in your HA) and take their colours from a **Battman theme**. If an entity
or theme colour is missing, the page shows an error saying exactly what.

## Updating

New versions appear in Home Assistant under **Settings → Updates** once HACS sees a new GitHub Release. Install the update, then restart Home Assistant.

## License

MIT
