"""The Solar card (custom:battman-solar-card).

- The inverters you list (none are assumed) with live power, today's energy and Solcast's forecast.
- view: toggle / both / now / forecast; the 10% pill picks which forecast figure is the big one.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
CARD = ROOT / "custom_components/battman/www/battman-solar-card.js"


def test_card_is_loaded_and_documented() -> None:
    assert '"solar-card"' in (ROOT / "custom_components/battman/www/battman.js").read_text()
    docs = (ROOT / "docs/cards.md").read_text()
    assert "`battman-solar-card`" in docs and "## Battman Solar" in docs


def test_card_options_and_defaults() -> None:
    js = CARD.read_text()
    assert 'battmanDefine("battman-solar-card"' in js
    for view in ("now", "forecast", "toggle", "both"):
        assert f'"{view}"' in js
    assert 'forecast_basis: "p10"' in js                      # 10% is the big figure until you tap the pill
    assert "sensor.sigen_" not in js and "sensor.solcast" not in js        # no inverter or forecast sensor is assumed
    assert "Symo" not in js and '"Sig"' not in js                           # nor an inverter name
    assert 'sparkline: "total"' in js and "detailedForecast" in js    # a total-only sparkline with the forecast dashed behind it


@pytest.mark.skipif(not shutil.which("node"), reason="needs node")
def test_card_parses_as_a_module() -> None:
    src = CARD.read_text()
    assert re.search(r'from "\./battman-card-base\.js"', src)
    subprocess.run(["node", "--check", "--input-type=module"], input=src, text=True, check=True)


@pytest.mark.skipif(not shutil.which("node"), reason="needs node")
def test_only_the_inverters_you_list_are_drawn_and_named() -> None:
    """#60 and its follow-up: nothing comes from a default. Another inverter's sensors in HA don't leak into Today,
    an unconfigured card draws nothing, and the name is the one you typed or else the device's.
    Runs the real card against dummy states, no browser."""
    out = subprocess.run(["node", str(ROOT / "tests/js/solar_today_check.mjs"), str(CARD)],
                         capture_output=True, text=True, check=True).stdout.strip().splitlines()[-1]
    import json
    r = json.loads(out)
    assert r["powerOnly"] == ["– kWh"] * 4                                  # no energy sensor chosen: blank, not 22.2
    assert r["withEnergy"] == ["8.7 kWh", "5.5 kWh", "3.2 kWh", "8.7 kWh"]  # hero, each inverter, total
    assert r["oneEnergy"] == ["– kWh", "5.5 kWh", "– kWh", "– kWh"]        # a total needs every inverter's figure
    assert r["nothing"]["today"] == [] and "No inverters set up" in r["nothing"]["msg"]
    assert r["legacy"] == ["5.5 kWh", "5.5 kWh"]                            # an old `sig` that names its sensor (headline + row); a bare `symo` adds nothing
    assert r["names"] == [True, True] and r["fallbackName"] is True
