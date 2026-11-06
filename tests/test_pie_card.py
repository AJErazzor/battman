"""battman-pie-card: the NEM mix card draws its pies itself (no power-pie-card from HACS).

It's power-pie-card v0.3.2 renamed, with megawatt support. Stock power-pie-card reads `mw` as
milliwatts and only shows W or kW, which made the NEM mix card show 2.3 W instead of 2,285.9 MW.
"""

from pathlib import Path

ROOT = Path(__file__).parents[1]
JS = (ROOT / "custom_components/battman/www/battman-pie-card.js").read_text()
INIT = (ROOT / "custom_components/battman/__init__.py").read_text()


def test_pie_card_is_shipped_and_loaded() -> None:
    assert '"pie-card"' in INIT
    assert 'battmanDefine("battman-pie-card", ' in JS
    assert 'customElements.define("power-pie-card"' not in JS      # never claim the stock card's name


def test_megawatts() -> None:
    assert 'u === "mw") return value * 1000000' in JS               # MW is megawatts, not milliwatts
    assert '["kW", "MW"].includes(c.display_unit)' in JS
    assert "min_pct_label" in JS and "hide_legend_value" in JS


def test_nemmix_uses_it_and_needs_nothing_from_hacs() -> None:
    text = (ROOT / "custom_components/battman/cards/nemmix.yaml").read_text()
    assert "custom:battman-pie-card" in text and "custom:power-pie-card" not in text
    assert "power-pie-card" not in (ROOT / "custom_components/battman/dependencies.py").read_text()


def test_gas_group_solar_names_and_show_option() -> None:
    """#59: the four gas kinds are one "Gas" slice (the pie card sums them), the solar slices are
    Solar (S) / Solar (L), and the card's `show:` picks one pie."""
    text = (ROOT / "custom_components/battman/cards/nemmix.yaml").read_text()
    assert "name: Gas\n" in text and "name: Solar (S)" in text and "name: Solar (L)" in text
    assert "Gas (CCGT)" not in text and "Rooftop Solar" not in text
    assert "sensor.battman_nem_gas_recip" in text                # the warning line still names a missing member
    assert "Array.isArray(e.entities)" in JS and "parts.some((p) => !isFinite(p))" in JS   # a group needs every member
    cards = (ROOT / "custom_components/battman/www/battman-cards.js").read_text()
    for v in ('"both"', '"generation"', '"demand"'):
        assert v in cards
    assert "cardConfig(id, data, this._config)" in cards          # the dashboard card and Convert both apply it


# ── style: bar (#63) ─────────────────────────────────────────────────────────

import json
import os
import shutil
import subprocess

import pytest

CHROME = os.environ.get("BATTMAN_CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
NODE_PATH = os.environ.get("BATTMAN_NODE_PATH", "/tmp/pwtest/node_modules")


def test_bar_style_wiring() -> None:
    """The pie card takes `style: bar`; the NEM mix card passes it to both pies, and its editor offers it."""
    assert subprocess.run(["node", "--check", str(ROOT / "custom_components/battman/www/battman-pie-card.js")]).returncode == 0
    assert 'c.style = c.style === "bar" ? "bar" : "pie"' in JS
    cards = (ROOT / "custom_components/battman/www/battman-cards.js").read_text()
    assert 'name: "style"' in cards and '["pie", "Pies"], ["bar", "Bars"]' in cards
    assert '"bar"' in cards and "isn't one of pie, bar" in cards          # a bad value is said on the card
    assert "`style: bar`" in (ROOT / "custom_components/battman/cards/nemmix.yaml").read_text()


@pytest.mark.skipif(not (Path(CHROME).exists() and Path(NODE_PATH, "playwright").exists() and shutil.which("node")),
                    reason="needs Playwright and Chromium")
def test_bar_style_in_a_browser() -> None:
    r = subprocess.run(["node", str(Path(__file__).parent / "js/pie_bar_check.js"),
                        str(ROOT / "custom_components/battman/www")],
                       capture_output=True, text=True, timeout=120,
                       env={**os.environ, "NODE_PATH": NODE_PATH, "CHROME": CHROME})
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert out["errors"] == []
    bar = out["bar"]
    assert bar["isBar"] and bar["arcs"] == 0 and bar["total"] == "2,343.8 MW"
    # the same slices as the pie, largest first, Gas summed from its two sensors (55 + 12.5)
    assert bar["legend"] == ["Solar (S)", "Wind", "Solar (L)", "Gas", "Battery"]     # every block, small ones too
    assert [s["color"] for s in bar["segs"]][:2] == ["rgb(249, 160, 102)", "rgb(166, 227, 161)"]
    widths = [s["width"] for s in bar["segs"]]
    assert widths == sorted(widths, reverse=True) and sum(widths) == pytest.approx(100 - 5 * 0.8)   # slice_gap each
    assert [s["label"] for s in bar["segs"]] == ["48%", "35%", "13%", "", ""]           # under min_pct_label: none
    assert [s["shown"] for s in bar["segs"]][:3] == [True, True, True]
    # a pie is still a pie by default, and a bad style falls back to it
    assert out["pie"]["arcs"] == 5 and not out["pie"]["isBar"] and out["pie"]["total"] is None
    assert out["bad"]["arcs"] == 5 and not out["bad"]["isBar"]
    assert out["hover"][0].endswith("hot") and all(c.endswith("dim") for c in out["hover"][1:])
    # a sensor with no value drops its block and the rest fill the bar
    assert out["noWind"]["legend"] == ["Solar (S)", "Solar (L)", "Gas", "Battery"]
    assert sum(s["width"] for s in out["noWind"]["segs"]) == pytest.approx(100 - 4 * 0.8)
