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

Battman pages also load **Chart.js** from the internet (cdnjs / jsdelivr), so the charts need internet access.
