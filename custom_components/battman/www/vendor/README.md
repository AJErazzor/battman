# Third-party libraries shipped with Battman

Served from `/battmanfiles/vendor/`, so Battman's charts work without the internet. Each file is
the library's own published build, unchanged (its licence banner is at the top of the file).

| File | Library | Version | Licence | From |
|---|---|---|---|---|
| `chart.umd.min.js` | Chart.js | 4.4.0 | MIT | npm `chart.js@4.4.0`, `dist/chart.umd.js` |
| `chartjs-plugin-datalabels.min.js` | chartjs-plugin-datalabels | 2.2.0 | MIT | npm `chartjs-plugin-datalabels@2.2.0`, `dist/chartjs-plugin-datalabels.min.js` |

To update one: replace the file with the new version's published build, change the version here,
and check every page that draws a chart (Log card, Curvy, Pricy, Cost chart, Cost compare).
