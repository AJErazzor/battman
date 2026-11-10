# Third-party libraries shipped with Battman

Served from `/battmanfiles/vendor/`, so Battman's charts and its built-in guide work without the internet. Each file is
the library's own published build, unchanged (its licence banner is at the top of the file).

| File | Library | Version | Licence | From |
|---|---|---|---|---|
| `chart.umd.min.js` | Chart.js | 4.4.0 | MIT | npm `chart.js@4.4.0`, `dist/chart.umd.js` |
| `marked.esm.js` | marked (Markdown to HTML, for the guide) | 18.1.2 | MIT | npm `marked@18.1.2`, `lib/marked.esm.js` (SHA-256 `e7b0919876c54c2d9ca6b927db18420a081f6fee8cf1ecfd7cb6ea97a3b55309`) |

To update one: replace the file with the new version's published build, change the version here,
and check every card that draws a chart (the Log, Cost chart, Cost compare, Curvy and Pricy cards).

For marked: check the Help view (the guide's pages, links and code blocks), and run the guide tests
(`tests/test_guide.py`), which render every page with it.
