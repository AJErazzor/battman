# Battman dependencies

Battman can't install other add-ons for you. Install these yourself (HACS → Frontend).
Battman checks for the dashboard cards at startup and raises a **Repair** naming any that are missing.

| Dependency | Type | Needed by | Get it |
|---|---|---|---|
| button-card | Dashboard card | Finances view (Billing, Financials/ROI cards) | https://github.com/custom-cards/button-card |
| card-mod | Dashboard card | All Battman views (full-bleed page cards, header) | https://github.com/thomasloven/lovelace-card-mod |
| html-card | Dashboard card | Finances view header | https://github.com/PiotrMachowski/Home-Assistant-Lovelace-HTML-card |

Coming with later moves (not checked yet):

| Dependency | Type | Needed by | Get it |
|---|---|---|---|
| browser_mod | Integration | Override cards (popups) | https://github.com/thomasloven/hass-browser_mod |

Battman pages also load from the internet:

- **Chart.js** (cdnjs / jsdelivr): charts on the cost, compare and log pages.
- **Google Fonts**: only the theme studio's font browser, and themes that turn on a custom font.

The Log and Theme views are plain iframe pages and need no extra cards.

Battman's own pieces that other parts rely on:

- **Entity map** (`/api/battman/entities`): every Battman page. Change it under Configure.
- **Battman theme** (`--battman-*` colours): every Battman page shows an error without one.
- **`battman-lib.js`**: the theme studio's live previews (the override cards still use Smiggles' `ssc-lib.js` until they move).
- **Debug log file + load script** (`debug_log_file`, `load_debug_log_script` in the map): the Log page's log panel. Both still come from Smiggles.
