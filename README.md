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
files there. Every theme also defines the old `--smiggles-*` names, pointing at the
`--battman-*` ones, so existing Smiggles cards keep working.

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
