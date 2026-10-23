# Third-party libraries shipped with Battman

Served from `/battmanfiles/vendor/`, so Battman's charts work without the internet. Each file is
the library's own published build, unchanged (its licence banner is at the top of the file).

| File | Library | Version | Licence | From |
|---|---|---|---|---|
| `chart.umd.min.js` | Chart.js | 4.4.0 | MIT | npm `chart.js@4.4.0`, `dist/chart.umd.js` |

To update one: replace the file with the new version's published build, change the version here,
and check every card that draws a chart (the Log, Cost chart, Cost compare, Curvy and Pricy cards).
