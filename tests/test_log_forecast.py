"""The Log card's Forecast / Both views (issue #62).

The log lists predicted blocks in the Chill popup's own wording, using the same shared module (battman-forecast-core.js).
These tests check that there is one copy of it, that it works, and that the card is a clean node module.
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


def core_url() -> str:
    return (WWW / "battman-forecast-core.js").as_uri()


def test_log_and_forecast_share_one_copy_of_the_wording() -> None:
    """The Log's Forecast entries and the "Next hours" view both use battman-forecast-core.js: no second copy."""
    log = (WWW / "battman-log.js").read_text()
    view = (WWW / "battman-forecast-view.js").read_text()
    assert 'from "./battman-forecast-core.js"' in log and 'from "./battman-forecast-core.js"' in view
    assert "function group(" not in log and "function describe(" not in log and "const FP = { group, split, describe, money };" in log
    assert not (WWW / "battman-forecast.html").exists()
    core = WWW / "battman-forecast-core.js"
    assert subprocess.run(["node", "--input-type=module", "--check"], input=core.read_text(), text=True).returncode == 0


def test_forecast_core_groups_and_words_slots() -> None:
    """Run the shared code on a few slots: quiet, then a sell block with the battery draining."""
    script = f"""
import {{ group, describe, money }} from {json.dumps(core_url())};
const slot = (start, mode, o = {{}}) => Object.assign({{ start, minutes: 30, mode, live: false, soc_start: 50, soc_end: 50, buy_price: 0.2, sell_price: 0.1,
  buy_line: 0.1, sell_line: 0.3, buy_below: 20, sell_above: 90, sell_price_known: true, buy_reason: '', sell_reason: '', money: 0, battery_kwh: 0,
  export_kwh: 0, import_kwh: 0, load_kw: 1, pv_kw: 0 }}, o);
const slots = [slot('2026-11-07T10:00:00+10:30', 'Self Consume'), slot('2026-11-07T10:30:00+10:30', 'Self Consume'),
  slot('2026-11-07T11:00:00+10:30', 'Discharge', {{ soc_start: 80, soc_end: 70, sell_price: 0.5, export_kwh: 2, battery_kwh: -3, money: 1, sell_reason: 'Sell Above' }})];
const g = group(slots);
process.stdout.write(JSON.stringify({{ kinds: g.map(m => m.kind), spans: g.map(m => [m.start, m.end]), sell: describe(g[1]).head, money: money(1.5), neg: money(-0.25) }}));"""
    r = subprocess.run(["node", "--input-type=module"], input=script, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["kinds"] == ["idle", "sell"] and out["spans"] == [["10:00", "11:00"], ["11:00", "11:30"]]
    assert out["sell"] == "Sell 2.0 kWh, battery 80% → 70%" and out["money"] == "+$1.50" and out["neg"] == "−$0.25"


def test_log_card_forecast_views() -> None:
    js = (WWW / "battman-log.js").read_text()
    assert subprocess.run(["node", "--input-type=module", "--check"], input=js, text=True).returncode == 0
    assert "domain: 'script', service: 'battman_engine_forecast'" in js   # the same script the popup calls
    assert "'battman.logView'" in js and "battman.logFuture" not in js
    # a remembered Forecast / Both loads the forecast on entry
    assert re.search(r"started = true;\s+setFcStamp\(\);[^\n]*\n\s+if \(wantsFuture\(\) && !fc\) loadForecast\(\);", js)


CHROME = os.environ.get("BATTMAN_CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
NODE_PATH = os.environ.get("BATTMAN_NODE_PATH", "/tmp/pwtest/node_modules")


@pytest.mark.skipif(not (Path(CHROME).exists() and Path(NODE_PATH, "playwright").exists() and shutil.which("node")),
                    reason="needs Playwright and Chromium")
def test_forecast_view_in_a_browser() -> None:
    """<battman-forecast-view> draws a forecast, takes what-if changes, and opens (and closes) in Battman's dialog."""
    r = subprocess.run(["node", str(Path(__file__).parent / "js/forecast_view_check.js"), str(WWW)], capture_output=True, text=True,
                       timeout=120, env={**os.environ, "NODE_PATH": NODE_PATH, "CHROME": CHROME})
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert out["errors"] == []
    assert out["rows"] >= 2 and out["sellRow"] and out["title"].startswith("Next ")
    assert "+$1.00" in out["total"] and out["reminderOk"] is True
    assert out["callsBefore"] == 1 and out["whatIf"] is True and out["callsAfter"] >= 2   # the live picture once, then the what-if
    assert out["dialogOpen"] and out["viewInDialog"] and out["dialogRows"] >= 2 and out["hasClose"] and out["closed"]
