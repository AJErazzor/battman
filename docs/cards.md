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
A card file's top-level `grid_options` (e.g. `columns: full`) is its size in a sections view.
HA only reads `grid_options` on the card as placed, so Battman passes it on: Create
dashboard adds it, a card added from the card picker comes with it, and the card reports it
to HA once loaded. A `grid_options` you set on the placed card always wins.

**Theme.** Battman cards draw in a Battman theme's colours. Placed on a view, a card takes that
view's theme, like any card: on the Battman dashboard that's the one picked under Settings →
Dashboard theme. In the card picker (Add card) the previews are drawn in **Battman Coffee**, so you
can see them in colour; the card you add has no `theme:` and takes its view's.

To give one card its own colours (say on a view without a Battman theme), add `theme:` to it:

```yaml
type: custom:battman-state
theme: Battman Nord     # a theme by name
# theme: battman        # or the Battman dashboard's theme, following it when it changes
```

`theme: battman` uses the theme picked in Settings → Dashboard theme (or the theme studio's
Make Active), whether or not you've taken control of the dashboard. If no theme is picked or
it isn't there, the card says so instead of drawing.

A card with no tap action gets `pointer-events: none` from button-card, which also stops
scrolling inside it; cards that scroll (the forecast table) set `pointer-events: auto`.
The editor is only there on a dashboard you can edit. The Battman dashboard is an ordinary
dashboard you own, so every Battman card on it has the editor. (An older *managed* Battman
dashboard is built by Battman, so HA offers **Take control** instead.)

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
| `battman-curvy` | The SOC curve editor (Battman's Curvy page in a frame for now). Size it by dragging in a sections view; it fills a panel view | nothing |
| `battman-pricy` | The price curve editor (Battman's Pricy page in a frame for now). Sized like Curvy | nothing |
| `battman-settings` | Every Battman setting on one page; drag sections between two columns (order kept per device). Each change is checked: values Battman won't accept are refused, and it says if a change didn't take | nothing |
| `battman-log` | The engine log page (in a frame for now). Sized like Curvy | nothing |
| `battman-theme-studio` | The Theme studio (in a frame for now). Sized like Curvy | nothing |
| `battman-cost-chart` | Daily buy, sell and net cost with Sigen import / export (Battman's cost chart page in a frame) | card-mod |
| `battman-cost-compare` | This period against earlier ones (Battman's cost compare page in a frame) | card-mod |
| `battman-billing` | This billing period's buy, sell, days and income; network fee; bank / reset new income; **Correct totals** popup | button-card, browser_mod |
| `battman-solar-system` | Today's verdict, financials and the ROI timeline | button-card |
| `battman-image` | Any of Battman's images, or yours, with fit, position and size options (see [Battman Image](#battman-image)) | nothing |

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

## Battman Image

`custom:battman-image` shows one image: one of Battman's (`www/images/`, updated by releases) or
one of yours. It's built differently from the cards above (it has a real editor rather than a
card file), so there's no **Convert to plain YAML**: its settings are already plain YAML on the
card.

Add card → **Battman Image** → pick the image from the dropdown and set how it fills the card:

```yaml
type: custom:battman-image
image: battman-main.webp
fit: cover            # contain (whole image) | cover (fill, crop edges) | stretch | actual | shrink
position: bottom      # what's kept when cropping, or where it sits: center, top, bottom, left, right, top-left, …
height: fill          # auto (the image's own shape) | fill (the space you give it) | a number of px
background: none      # card | none | colour (then background_color: '#1e1e2e' or var(--battman-blue))
frame: false          # the card's border and shadow
padding: 0            # px
radius: 0             # px, the image's corners
flip: false           # mirror left to right
narrow:               # on a screen under 768 px wide (phones): any of the settings above except height
  fit: contain
dark:                 # in dark mode: the same. On a narrow screen in dark mode, narrow wins.
  image: battman-main.webp
```

- **Resizing.** With `height: fill`, drag the card's size in a sections view and the image follows
  it; `fit` and `position` decide what you see. `fill` needs a sections view (only there does a
  card get a height): anywhere else the card says so. `auto` and a number of px work anywhere.
- **Narrow** is the same line as HA's own *Mobile* visibility condition (under 768 px). It's the
  screen width, not the device: a phone turned sideways can count as wide. It changes live.
- **Your own images** go in `config/battman/images/` (png, jpg, webp or gif; no sub-folders). Battman
  never touches that folder, not on update and not when it's removed. Reopen the card editor to see a
  new one; the dropdown marks them *(yours)*. One with the same name as one of Battman's is used
  instead of Battman's, everywhere, and is marked *(yours, replaces Battman's)*.
- Images are served from `/api/battman/image/<name>` without a login (like `/local/`), because an
  image on a page can't send one. Don't put anything private in that folder.
- **Problems** show on the card: an image that isn't there (named), a setting it doesn't know, or
  `fill` with no height to fill. Never a blank space or a different image.
