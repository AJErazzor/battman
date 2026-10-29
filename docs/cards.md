# Battman cards

Battman cards are dashboard cards you can put on any view, on any dashboard, and
that update with Battman releases. Most are plain YAML card files; the ones that draw themselves
(Log, Curvy, Pricy, Cost chart, Cost compare, Settings, Theme studio, House, Image) are scripts.

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
dashboard you own, so every Battman card on it has the editor.

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
| `battman-curvy` | The SOC curve editor (see [Battman Curvy](#battman-curvy)). Draws itself; no options | nothing |
| `battman-pricy` | The price curve editor (see [Battman Pricy](#battman-pricy)). Draws itself; no options | nothing |
| `battman-settings` | Every Battman setting on one card; drag sections between two columns (order kept per device). Each change is checked: values Battman won't accept are refused, and it says if a change didn't take. Draws itself; no options | nothing |
| `battman-log` | The engine log, mode timeline and charts (see [Battman Log](#battman-log)) | nothing |
| `battman-theme-studio` | The Theme studio: edit a Battman theme with a live preview (including the real State card), save it to HA or make it the dashboard's theme. Draws itself; no options | nothing |
| `battman-cost-chart` | Daily buy, sell and net cost with Sigen import / export, over N days, a bill cycle or From / To (the range is kept per device; it starts on 5 days on a narrow card, 10 on a wide one). Draws itself; no options | nothing |
| `battman-cost-compare` | This bill cycle against the last: the running net cost day by day, and how far ahead or behind you are. Draws itself; no options | nothing |
| `battman-amber-forecast-chart` | Amber's buy and sell price forecasts (price, predicted, low and high) for the next 4, 8, 12 or 24 hours; tap a name to hide a line (see [Battman Amber forecast chart](#battman-amber-forecast-chart)). Draws itself; no options | nothing |
| `battman-solar-card` | Live power, today's generation and Solcast's forecast for one or two inverters, as Now / Forecast pills, two stacked tables, or either alone (see [Battman Solar](#battman-solar)) | nothing |
| `battman-billing` | This billing period's buy, sell, days and income; network fee; bank / reset new income; **Correct totals** popup | button-card, browser_mod |
| `battman-solar-system` | Today's verdict, financials and the ROI timeline | button-card |
| `battman-house` | The house picture with live prices, solar, PV strings, home, grid, battery, temperature and three of your own devices, with moving flow lines (see [Battman House](#battman-house)) | nothing |
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
    entity: number.sigen_plant_grid_export_limitation
  - type: custom:button-card
    entity: '[[map:parameters]]'
    ...
```

Sigen's, Amber's and Solcast's entities are written by name. `[[map:name]]` is one of Battman's
engine entities from its entity map (Smiggles' before you migrate, Battman's after). Quote it when
it's a whole value, as above. HA's own `{{ … }}` templates are left alone.

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

## Battman Log

`custom:battman-log` is the engine log with the mode timeline and the price, power, grid, battery and
solar charts over the same window. It used to be the Log page in a frame; it's now a card that
draws itself, so it grows to fit (no size to set) and takes the view's theme directly. It has no
options. It looks and works as the page did:

- **Filter Log**: quick ranges (5m to 24h), the ‹ › pager, and From / To.
- **Log**: collapsed to start; tick modes on or off, or Changes Only.
- **Mode**: tap the timeline for the mode, price and battery at that point, and to limit the log to
  that 5-minute block; drag to scrub (the charts show the same point).
- **Order**: drag any block by its grip; the order is kept per device.
- **Live**: when the engine logs a run the log reloads, and on a quick range the window moves on to
  now (your filters stay). The charts also refresh every minute.

## Battman Curvy

`custom:battman-curvy` is the SOC curve editor: the battery charge the engine aims for at each hour,
for each month (or season), on four curves: Sell, Sell High Consumption, Buy and Buy High
Consumption. Edit the hour boxes, or tap a point on the chart to jump to its box. Actual SOC
(yesterday, an average, or dates you pick) and today's SOC are drawn over it, with each hour's
mode, prices and solar in the hour details. **Save** sends the curves to Battman and checks they
took. Presets, copy / paste / export / import a period, Factory Defaults and Match Actual work on
the period you're editing. It has no options.

## Battman Pricy

`custom:battman-pricy` is the price curve editor: the sell and buy prices the engine works to at
each hour, for each month (or season), on the same four curves. Each curve has two lines (for Sell:
Preferred and Low), edited in two panels; with **Linked** on, changing Preferred also moves Low at
any hour where they were equal. **Set All** sets every hour at once. Today's Amber prices (actual so
far, then the forecast) are drawn over it; if Amber has no prices for today, the overlay is empty
and a note says so. Save, presets and the period tools work as in Curvy. It has no options.

## Battman Cost chart

`custom:battman-cost-chart` is each day's buy, sell and network fee, the net cost, and your Sigen
import and export, from the cost totals' long-term statistics (so it reaches back past the
recorder's purge). Pick 5 to 30 days, this or last bill cycle, or From / To; the range is kept per
device. A "bank it" day is rebuilt from that day's hourly figures. It has no options.

## Battman Cost compare

`custom:battman-cost-compare` is this bill cycle against the last: the running net cost day by day
from your bill day, with how far ahead or behind you are today. It refreshes every minute. It has
no options.

## Battman Amber forecast chart

`custom:battman-amber-forecast-chart` is Amber's price forecasts as a chart, in c/kWh, from now to 4,
8, 12 or 24 hours ahead. Each side has four lines, each solid in its own theme colour (Buy in the
warm colours, Sell in the cool ones): the forecast price, Amber Advanced's prediction and its low and
high. Until the first forecast (the interval under way isn't in Amber's forecasts) the price lines
show Amber's current prices. Sell is shown as what you're paid (positive = earning), as the engine
works it out, so Sell High is always the upper line.
Tap a name under the chart to hide or show that line; the range and the hidden lines are kept per
device. Hover or tap the chart for every shown line's price in that interval. It reads Amber's two
forecast sensors and two current-price sensors (amber2mqtt) and says so on the card if one is missing or has no forecasts. It
refreshes every minute and whenever Amber updates. It has no options.

## Battman Solar

`custom:battman-solar-card` shows up to two inverters (Inverter 1 is for a third-party inverter such as a
Fronius, Inverter 2 is your Sigenergy): live power, today's generation and Solcast's forecast. An
inverter whose power sensor doesn't exist isn't drawn, so a one-inverter home just works.

- `view`: `toggle` (default; Now / Forecast pills), `both` (the two tables stacked), `now` or `forecast`.
  `default_view` picks the pill selected first.
- The **10%** pill (shown unless `show_10: false`) chooses which Solcast figure is the big one: 10% (the
  pessimistic case, the default) or the estimate. Tap it to switch; it then reads **Est** and is lit.
  The other figure stays beside it in small text, tagged "est" or "10%". `forecast_basis: p10 | est` sets
  the default. It applies to every figure on the card, in every layout, and is kept per device.
- Now: total kW, today's kWh, what's left today (Solcast's remaining-today forecast) and a progress bar
  of the day done. Forecast: today and tomorrow per inverter, as bars. Tap a row for its sensor.
- Each inverter (`symo`, `sig`) takes `show`, `label`, `power`, `today` and `site`. `site` is the
  Solcast site id (the part after `estimate_` in the sensor's attributes, for example
  `fc06_f7f8_d429_86e2`); leave it blank for a single inverter and the whole forecast is used. With two
  inverters a blank site shows a dash. W and Wh sensors are converted to kW and kWh.
- `forecast_remaining`, `forecast_today` and `forecast_tomorrow` name the Solcast sensors.
  `no_export_entity` (an orange "No export" flag while it's on) and `soft_limit_entity` (a red
  "Soft limit" flag) are optional; leave either empty to hide it.
- `show_total`, `show_10` and `show_progress` turn the Total row, the 10% figures and the progress bars on or off.

## Battman Settings

`custom:battman-settings` is every Battman setting on one card, in sections you can drag between
two columns (the order is kept per device). Each change is sent to Battman and checked: it shows
**✓ Saved**, or why not (a value out of range, or Battman not in charge of the battery). It has no
options.

## Battman Theme studio

`custom:battman-theme-studio` edits a Battman theme: the palette, surfaces, fonts and mode
effects, with a live preview that includes the real State card. **Save to HA** saves it as one of
your themes; **Make Active** makes it the dashboard's theme. It has no options.

## Battman House

`custom:battman-house` is the house picture from the Smiggles Power view, drawn by Battman
itself (no button-card, mushroom or card-mod). It's the first card on the Power view.

Every item has a **Show** switch and its own entity, all set in the card's editor. Leave them
alone and the card uses Sigen's and Amber's entities by name.
The outside temperature, the battery temperature and the three devices have no default: they're drawn once you pick their
entity. An item whose entity doesn't exist isn't drawn. The three devices (the "PC" rows) also
take your own text and what goes after the value (e.g. `W`). The pictures are Battman's;
point House / Battery / Gateway picture at your own (e.g. `/local/house.png`) to change them.

Only what you change is written to the card's YAML, e.g.:

```yaml
type: custom:battman-house
buy:
  show: false
pc1:
  label: Office PC
  entity: sensor.office_pc_power
  suffix: W
```
