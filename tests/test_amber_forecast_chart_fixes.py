"""v0.27.1: Amber forecast chart fixes.

- No gaps between intervals: Amber's intervals start a second past the boundary (17:30:01 to 18:00:00),
  so a point on the boundary fell between two intervals and the line broke for 5 minutes there. Each
  interval's times are taken on the whole minute.
- The chart starts at "now": the interval under way isn't in Amber's forecasts, so until the first one
  the Price lines show Amber's current prices (sensor.amber_5min_current_*, Sell already positive).
- Every line solid, in its own theme colour (Buy warm, Sell cool).
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

WWW = Path(__file__).parents[1] / "custom_components/battman/www"
DATA = WWW / "battman-amber-forecast-data.js"
CHROME = os.environ.get("BATTMAN_CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
NODE_PATH = os.environ.get("BATTMAN_NODE_PATH", "/tmp/pwtest/node_modules")


def test_amber_intervals_join_and_current_price_leads() -> None:
    code = f"""
import {{ forecastSeries, intervals }} from "{DATA.as_uri()}";
const T0 = Date.parse("2026-10-27T06:30:00Z");
const at = (m, s = 0) => new Date(T0 + m * 60000 + s * 1000).toISOString();
const fc = (m, raw) => ({{ start_time: at(m, 1), end_time: at(m + 30), per_kwh: raw, advanced_price_predicted: raw }});
const buy = [fc(30, 0.4), fc(60, 0.5)], sell = [fc(30, -0.1), fc(60, -0.2)];
const S = forecastSeries(buy, sell, T0 + 2 * 60000, T0 + 90 * 60000, {{ buy: "0.3", sell: "0.08" }});
const pick = (id, m) => S.data[id][S.times.indexOf(T0 + m * 60000)];
console.log(JSON.stringify({{
  starts: intervals(buy).map((x) => (x.s - T0) / 60000),
  buyNow: pick("buy", 2), sellNow: pick("sell", 25), predictedNow: pick("buy_predicted", 25),
  buyAt30: pick("buy", 30), buyAt60: pick("buy", 60), sellAt60: pick("sell", 60), buyAt90: pick("buy", 90),
  gaps: S.times.filter((t) => t >= T0 + 30 * 60000).filter((t, i) => S.data.buy[S.times.indexOf(t)] === null).length,
  noCurrent: forecastSeries(buy, sell, T0 + 2 * 60000, T0 + 90 * 60000).data.buy[0],
}}));
"""
    out = json.loads(subprocess.run(["node", "--input-type=module", "-e", code], capture_output=True, text=True, check=True).stdout)
    assert out["starts"] == [30, 60]                                  # 07:00:01 -> 07:00
    assert out["buyNow"] == 30 and out["sellNow"] == 8                # current prices until the first forecast
    assert out["predictedNow"] is None                                # only the Price lines have a "now"
    assert out["buyAt30"] == 40 and out["buyAt60"] == 50 and out["sellAt60"] == 20
    assert out["buyAt90"] == 50                                       # the last forecast's end closes the line
    assert out["gaps"] == 0
    assert out["noCurrent"] is None                                   # no current price given: a gap, not 0


def test_card_reads_the_current_price_sensors_and_draws_solid_lines() -> None:
    js = (WWW / "battman-amber-forecast-chart.js").read_text()
    assert '"buy_price", "feed_in_price"' in js and "borderDash" not in js
    for v in ("amber", "orange", "yellow", "red", "green", "teal", "sky", "blue"):
        assert f'"--battman-{v}"' in js, v


@pytest.mark.skipif(not (Path(CHROME).exists() and Path(NODE_PATH, "playwright").exists() and shutil.which("node")),
                    reason="needs Playwright and Chromium")
def test_amber_shape_in_a_browser() -> None:
    r = subprocess.run(["node", str(Path(__file__).parent / "js/amber_forecast_check.js"), str(WWW)],
                       capture_output=True, text=True, timeout=120,
                       env={**os.environ, "NODE_PATH": NODE_PATH, "CHROME": CHROME})
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert out["errors"] == []
    shape = out["amberShape"]
    assert (shape["firstBuy"], shape["firstSell"], shape["firstPredicted"]) == (31, 12, None)
    assert shape["gaps"] == [0] * 8
    assert shape["dashed"] == 0 and shape["colours"] == 8
