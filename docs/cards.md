# Battman cards

Battman cards are dashboard cards you can put on any view, on any dashboard, and
that update with Battman releases. Each one is a plain YAML card file.

## Using one

Edit dashboard → **Add card** → search **Battman** → pick one (each has a live
preview). On the dashboard its YAML is just:

```yaml
type: custom:battman-limits
```

Copy and paste it anywhere like any card. Every copy updates when Battman does.

**Make one copy your own:** open the card's editor → **Convert to plain YAML**. You
get the full card YAML with your entities filled in; that copy stops updating.
A card with no tap action gets `pointer-events: none` from button-card, which also stops
scrolling inside it; cards that scroll (the forecast table) set `pointer-events: auto`.
The editor is only there on a dashboard you can edit. Battman's own dashboard is built
by Battman, so HA offers **Take control** instead of an editor. Taking control makes it an
ordinary dashboard you can rearrange: its Battman cards keep updating, but changes to the
views themselves (new cards, layout) stop arriving. To go back, set its raw configuration
to `strategy: {type: custom:battman}`.

| Card | What it shows | Needs |
|---|---|---|
| `battman-limits` | Grid export, PV max and max charge limits; tap one to change it | button-card, card-mod |
| `battman-profitloss` | Today's sell, buy, gross, and net after the daily network charge | button-card |
| `battman-amber5minpricegrid` | SELL / BUY now with sparkline and 5-min countdown, then the next 8 periods | button-card |
| `battman-amber24hourforecasttable` | Every Amber forecast interval: Sell, SS, Buy, SS, colour banded (built from Amber's forecast sensors) | button-card |
| `battman-state` | What the engine is doing; tap for the next hours' projection | button-card, browser_mod |
| `battman-batterymode` | Active / Curtail switches, Engine log popup (info button), battery mode buttons | button-card, card-mod, browser_mod |
| `battman-overrides` | Override dock (Sell / Sell Solar / Buy / Buy Anytime / Drain), control centre (presets, scenes, Net Target), override timer | button-card, card-mod, browser_mod |
| `battman-gauges` | SOC, battery in/out, grid and home half gauges | modern-circular-gauge |
| `battman-nemmix` | Region generation mix and demand mix (Battman's NEM sensors) | power-pie-card |

`<battman-countdown></battman-countdown>` (the 5-min Amber countdown) is loaded by Battman on
every HA page, so you can also use it in your own cards. It takes its colour and font from
whatever it sits in.

## How a card is made

`custom_components/battman/cards/<id>.yaml` is ordinary card YAML, exactly what
you'd paste onto a view, with a two-line header:

```yaml
# name: Limits
# description: Grid export, PV max and max charge limits. Tap one to change it.
type: vertical-stack
cards:
  - type: custom:button-card
    entity: '[[map:grid_export_limit]]'
    ...
```

`[[map:name]]` is an entry in Battman's entity map (Battman → Configure). Quote it
when it's a whole value, as above. HA's own `{{ … }}` templates are left alone.

## Trying out changes on your own HA

1. Copy the card file to `config/battman/cards/<id>.yaml` (same name).
2. Edit that copy. On this HA it's used instead of Battman's, everywhere the card is.
3. Refresh the page to see the change.
4. While any file is in that folder, a **Repair** lists them, so a local copy is
   never forgotten.
5. When it's right, the file goes into the Battman repo (`custom_components/battman/cards/`)
   and out in the next release. Then delete your local copy.

A new file in that folder (a name Battman doesn't ship) is a new card of your own:
`custom:battman-<name>`, after restarting HA.

Problems show on the card itself: an unknown card, YAML that doesn't parse, a map
entry that doesn't exist, or a card type that isn't installed.
