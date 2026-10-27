"""v0.27.0: the Amber forecast chart card (custom:battman-amber-forecast-chart).

- A Chart.js card like Cost chart (draws itself, in the card picker with its preview picture), in
  place of the four ApexCharts cards and the input_select.amber_chart_time_span helper.
- Buy and Sell: price, Amber Advanced's predicted, low and high, from Amber's two forecast sensors
  (named directly, AMBER in battman-card-base.js). Sell is negated (positive = earning), so its Low /
  High come from the raw high / low. A missing figure is a gap, never 0.
- 4h / 8h / 12h / 24h pills; tap a name under the chart to hide or show a line. Both kept per device.
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1] / "custom_components/battman"
WWW = ROOT / "www"
CARD = WWW / "battman-amber-forecast-chart.js"
DATA = WWW / "battman-amber-forecast-data.js"
CHROME = os.environ.get("BATTMAN_CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
NODE_PATH = os.environ.get("BATTMAN_NODE_PATH", "/tmp/pwtest/node_modules")


def test_a_real_card_in_the_picker() -> None:
    for f in (CARD, DATA):
        assert subprocess.run(["node", "--check", str(f)]).returncode == 0, f.name
    js = CARD.read_text()
    assert "class BattmanAmberForecastChartCard extends BattmanCardBase" in js
    assert 'battmanDefine("battman-amber-forecast-chart", BattmanAmberForecastChartCard)' in js
    assert 'battmanPicker("battman-amber-forecast-chart",' in js
    assert 'static preview = "amber-forecast-chart.webp";' in js
    assert (WWW / "previews/amber-forecast-chart.webp").stat().st_size > 1000
    assert 'from "./battman-card-base.js"' in js and "loadChartJs" in js and "AMBER" in js
    init = (ROOT / "__init__.py").read_text()
    loaded = re.search(r'for name in \(([^)]*)\):\n\s+frontend\.add_extra_js_url', init).group(1)
    assert '"amber-forecast-chart"' in loaded
    # no ApexCharts, no helper, no frame or token, no outside CDN
    for gone in ("apexcharts", "input_select", "access_token", "iframe", "fetch(", "cdn."):
        assert gone not in js.lower(), gone
    docs = (Path(__file__).parents[1] / "docs/cards.md").read_text()
    assert "`battman-amber-forecast-chart`" in docs and "## Battman Amber forecast chart" in docs


def _node(code: str):
    r = subprocess.run(["node", "--input-type=module", "-e", code], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def test_forecast_figures() -> None:
    out = _node(f"""
import {{ forecastSeries, amberValue, SERIES }} from "{DATA.as_uri()}";
const T0 = Date.parse("2026-10-27T06:00:00Z");
const at = (m) => new Date(T0 + m * 60000).toISOString();
const buy = [
  {{ start_time: at(0), end_time: at(30), per_kwh: 0.25, advanced_price: {{ low: 0.2, predicted: 0.26, high: 0.3 }} }},
  {{ start_time: at(30), duration: 30, per_kwh: 0.5, advanced_price_low: 0.4, advanced_price_predicted: null, advanced_price_high: 0.6 }},
];
const sell = [
  {{ start_time: at(0), end_time: at(60), per_kwh: -0.1, advanced_price_low: -0.15, advanced_price_predicted: -0.09, advanced_price_high: -0.05 }},
];
const S = forecastSeries(buy, sell, T0 + 10 * 60000, T0 + 90 * 60000);
const pick = (id, m) => S.data[id][S.times.indexOf(T0 + m * 60000)];
console.log(JSON.stringify({{
  ids: SERIES.map((s) => s.id),
  times5: S.times.slice(0, 4).map((t) => (t - T0) / 60000),
  buyAt10: pick("buy", 10), buyAt30: pick("buy", 30), buyPredAt30: pick("buy_predicted", 30),
  buyHighAt0: pick("buy_high", 10), sellAt10: pick("sell", 10), sellLow: pick("sell_low", 10), sellHigh: pick("sell_high", 10),
  sellAt60: pick("sell", 60), buyAt60: pick("buy", 60), buyAt65: pick("buy", 65), buyAt90: pick("buy", 90),
  nested: amberValue({{ advanced_price: {{ predicted: "0.3" }} }}, "predicted"), flat: amberValue({{ advanced_price_low: 0.1 }}, "low"),
  none: amberValue({{ per_kwh: "" }}, "per_kwh"),
}}));
""")
    assert out["ids"] == ["buy", "buy_predicted", "buy_low", "buy_high", "sell", "sell_predicted", "sell_low", "sell_high"]
    assert out["times5"] == [10, 15, 20, 25]               # starts at "now", then every 5 minutes
    assert out["buyAt10"] == 25 and out["buyAt30"] == 50   # c/kWh, the interval covering each point
    assert out["buyPredAt30"] is None                       # missing: a gap, not 0
    assert out["buyHighAt0"] == 30
    assert out["sellAt10"] == 10                            # Sell negated: positive = earning
    assert out["sellLow"] == 5 and out["sellHigh"] == 15    # High stays the upper line after negating
    assert out["sellAt60"] == 10 and out["buyAt60"] == 50   # the last forecast's end closes its line
    assert out["buyAt65"] is None and out["buyAt90"] is None   # past the forecasts: nothing drawn
    assert out["nested"] == 0.3 and out["flat"] == 0.1 and out["none"] is None


@pytest.mark.skipif(not (Path(CHROME).exists() and Path(NODE_PATH, "playwright").exists() and shutil.which("node")),
                    reason="needs Playwright and Chromium")
def test_amber_forecast_chart_in_a_browser() -> None:
    r = subprocess.run(["node", str(Path(__file__).parent / "js/amber_forecast_check.js"), str(WWW)],
                       capture_output=True, text=True, timeout=120,
                       env={**os.environ, "NODE_PATH": NODE_PATH, "CHROME": CHROME})
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert out["errors"] == []
    first = out["first"]
    assert first["msg"] == "" and first["active"] == ["8h"] and first["title"].endswith("next 8 hours")
    assert first["labels"] == ["Buy Price", "Buy Predicted", "Buy Low", "Buy High",
                               "Sell Price", "Sell Predicted", "Sell Low", "Sell High"]
    assert (first["firstBuy"], first["firstSell"], first["sellLow"], first["sellHigh"]) == (25, 10, 7, 12)
    taps = out["afterTaps"]
    assert taps["hidden"] == ["Buy Low"] and taps["active"] == ["24h"]
    assert taps["saved"] == {"range": 24, "hidden": ["buy_low"]}
    assert out["reloaded"]["hidden"] == ["Buy Low"] and out["reloaded"]["active"] == ["24h"]   # kept per device
    assert re.fullmatch(r"\w{3} \d\d:\d\d – \d\d:\d\d", out["tooltip"]["title"][0])          # the interval
    assert " Buy Price: 25.00c" in out["tooltip"]["lines"]
    assert not any(line.startswith(" Buy Low") for line in out["tooltip"]["lines"])           # hidden: not listed
    assert out["missing"].startswith("Entity not found: feed_in_forecast")
    assert out["empty"].startswith("No Amber forecasts yet")
    assert "no time zone" in out["noTz"]
    assert out["back"] == ""
    assert out["picker"] == [{"name": "Battman Amber forecast chart", "preview": True}]
