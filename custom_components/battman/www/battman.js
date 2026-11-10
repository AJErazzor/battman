// Battman: the one script Home Assistant loads on every page. It starts each of Battman's scripts, every one in
// its own import, so one that fails to load is reported in the browser console and the others carry on.
//
// The scripts share what they need through battman-card-base.js (registering a card, the entity map, escaping
// text and so on), which the browser fetches once. A new Battman script is added to SCRIPTS below.
// "guide" is only the Help card's stub: the guide itself (battman-guide-view.js) loads when the Help view is opened.
//
// "?cards=a,b,c" on this script's own URL names the Battman cards that existed when Home Assistant started: it is
// passed on to battman-cards.js, so those cards exist before any dashboard draws them.

const SCRIPTS = ["countdown", "lib", "enginelog", "house", "overrides", "log", "cost-compare", "cost-chart", "settings", "theme-studio", "curvy",
  "pricy", "amber-forecast-chart", "solar-card", "mode-history-strip", "pie-card", "forecast-view", "guide"];

const start = (file) => import(file).catch((e) => console.error(`Battman: ${file} didn't load: ${(e && e.message) || e}`));

for (const name of SCRIPTS) start(`./battman-${name}.js`);
start(`./battman-cards.js${new URL(import.meta.url).search}`);
