"""The Mode history strip card, the Amber forecast's eight pills, and the House card's second solar sensor."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
WWW = ROOT / "custom_components/battman/www"
needs_node = pytest.mark.skipif(not shutil.which("node"), reason="needs node")


def _node(code: str) -> dict:
    out = subprocess.run(["node", "--input-type=module", "-e", code], capture_output=True, text=True, check=True).stdout
    return json.loads(out.strip().splitlines()[-1])


def test_strip_is_loaded_and_documented() -> None:
    assert '"mode-history-strip"' in (ROOT / "custom_components/battman/__init__.py").read_text()
    docs = (ROOT / "docs/cards.md").read_text()
    assert "`battman-mode-history-strip`" in docs and "## Battman Mode history strip" in docs
    js = (WWW / "battman-mode-history-strip.js").read_text()
    assert 'battmanDefine("battman-mode-history-strip"' in js and 'battmanMap(card.hass, ["mode"])' in js


@needs_node
def test_strip_pills_and_blocks() -> None:
    uri = (WWW / "battman-mode-history-data.js").as_uri()
    out = _node(f"""
import {{ RANGES_MIN, DEFAULT_RANGE_MIN, rangeLabel, modeBlocks, blockAt, tickTimes }} from "{uri}";
const T0 = Date.parse("2026-10-30T00:00:00Z"), M = (m) => T0 + m * 60000;
const rows = [
  {{ state: "Charge", last_changed: new Date(M(-30)).toISOString() }},      // began before the window
  {{ state: "unavailable", last_changed: new Date(M(20)).toISOString() }},  // a gap, not a mode
  {{ state: "Float", last_changed: new Date(M(30)).toISOString() }},
];
const b = modeBlocks(rows, M(0), M(60));
console.log(JSON.stringify({{
  labels: RANGES_MIN.map(rangeLabel), def: DEFAULT_RANGE_MIN,
  modes: b.map((x) => x.mode), starts: b.map((x) => (x.start - T0) / 60000), ends: b.map((x) => (x.end - T0) / 60000),
  firstFrom: (b[0].from - T0) / 60000, lastTo: b[1].to, at40: blockAt(b, M(40)).mode, at10: blockAt(b, M(10)).mode,
  ticks: tickTimes(M(0), M(240), 0).length <= 7,
}}));
""")
    assert out["labels"] == ["15m", "30m", "1h", "2h", "4h", "8h", "12h", "24h"] and out["def"] == 240
    assert out["modes"] == ["Charge", "Float"]                  # the unavailable stretch is a gap
    assert out["starts"] == [0, 30] and out["ends"] == [20, 60]  # clipped to the window
    assert out["firstFrom"] == -30 and out["lastTo"] is None     # real start kept; the last block is still running
    assert out["at40"] == "Float" and out["at10"] == "Charge"
    assert out["ticks"]


@needs_node
def test_amber_has_seven_pills() -> None:
    uri = (WWW / "battman-amber-forecast-data.js").as_uri()
    assert _node(f'import {{ RANGES_H }} from "{uri}"; console.log(JSON.stringify(RANGES_H));') == [0.5, 1, 2, 4, 8, 12, 24]
    js = (WWW / "battman-amber-forecast-chart.js").read_text()
    assert "const DEFAULT_RANGE_H = 8" in js
    for h in ("0.5", "1", "2", "4", "8", "12", "24"):
        assert re.search(rf"\b{re.escape(h)}: ", js.split("const TICK_H")[1].split("\n")[0]), h   # each range has its label spacing


def test_house_solar_can_add_a_second_sensor() -> None:
    js = (WWW / "battman-house.js").read_text()
    assert 'ent: { entity: "sensor.sigen_plant_daily_pv_energy", entity2: "" }' in js
    assert 'ent: { entity: "sensor.sigen_plant_pv_power", entity2: "" }' in js
    assert 'solar2: ""' in js and "sum2()" in js
    assert subprocess.run(["node", "--check", str(WWW / "battman-house.js")]).returncode == 0


@needs_node
def test_strip_and_log_page_share_the_logged_figures() -> None:
    """The strip's readout is the Log page's: buy / sell price and SOC from the engine log's nearest line,
    the mode's length worded the same way."""
    uri = (WWW / "battman-mode-history-data.js").as_uri()
    out = _node(f"""
import {{ logValuesAt, centsText, percentText, modeLengthText }} from "{uri}";
const lines = [
  "2026-10-30T14:15:02.214+10:30|Run: x\\nBuy: $0.2400 (Current: $0.2350)\\nSell: $-0.0700 (Current: $-0.0700)\\nBattery: 86.1% (34.7 kWh)",
  "2026-10-30T14:20:02.214+10:30|Run: y\\nBattery: 85.9% (34.6 kWh)",
  "no bar here",
];
const ms = (s) => Date.parse(s);
const a = logValuesAt(lines, ms("2026-10-30T14:16:00+10:30")), b = logValuesAt(lines, ms("2026-10-30T14:19:00+10:30"));
console.log(JSON.stringify({{
  a: [a.soc, a.buy, a.sell, a.at], b: [b.soc, b.buy, b.sell], none: logValuesAt([], 0),
  txt: [centsText(a.sell), centsText(null), percentText(a.soc), percentText(null)],
  len: [modeLengthText(0, 90000, 0, -1), modeLengthText(0, 30000, 0, 0), modeLengthText(0, null, 5 * 60000, -1)],
}}));
""")
    assert out["a"] == [86.1, 0.235, -0.07, 1793331902214]    # 14:15:02.214 +10:30 as ms
    assert out["b"] == [85.9, None, None]                      # the nearer line has no prices: a gap, not the other line's
    assert out["none"] == {"at": None, "soc": None, "buy": None, "sell": None}
    assert out["txt"] == ["-7.0c", "—", "86.1%", "—"]
    assert out["len"] == ["2 min", "1 min+", "5 min so far"]
