"""The Solar card (custom:battman-solar-card).

- Two inverters (third party + Sigenergy) with live power, today's energy and Solcast's forecast.
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
    assert '"solar-card"' in (ROOT / "custom_components/battman/__init__.py").read_text()
    docs = (ROOT / "docs/cards.md").read_text()
    assert "`battman-solar-card`" in docs and "## Battman Solar" in docs


def test_card_options_and_defaults() -> None:
    js = CARD.read_text()
    assert 'battmanDefine("battman-solar-card"' in js
    for view in ("now", "forecast", "toggle", "both"):
        assert f'"{view}"' in js
    assert 'forecast_basis: "p10"' in js                      # 10% is the big figure until you tap the pill
    assert "sensor.sigen_plant_third_party_pv_power" in js and "sensor.sigen_inverter_pv_power" in js
    assert "sensor.solcast_pv_forecast_forecast_remaining_today" in js
    assert 'sparkline: "total"' in js and "detailedForecast" in js    # a total-only sparkline with the forecast dashed behind it


@pytest.mark.skipif(not shutil.which("node"), reason="needs node")
def test_card_parses_as_a_module() -> None:
    src = CARD.read_text()
    assert re.search(r'from "\./battman-card-base\.js"', src)
    subprocess.run(["node", "--check", "--input-type=module"], input=src, text=True, check=True)


@pytest.mark.skipif(not shutil.which("node"), reason="needs node")
def test_today_never_comes_from_another_inverters_default_sensor() -> None:
    """#60: picking your own power sensors (and not an energy sensor) must not leave Today reading the
    card's default Sigenergy energy sensors. Runs the real card against dummy states, no browser."""
    out = subprocess.run(["node", str(ROOT / "tests/js/solar_today_check.mjs"), str(CARD)],
                         capture_output=True, text=True, check=True).stdout.strip().splitlines()[-1]
    import json
    r = json.loads(out)
    assert r["powerOnly"] == ["– kWh"] * 4                                # no energy sensor chosen: blank, not 22.2
    assert r["withEnergy"] == ["8.7 kWh", "5.5 kWh", "3.2 kWh", "8.7 kWh"]  # hero, each inverter, total
    assert r["oneEnergy"] == ["– kWh", "5.5 kWh", "– kWh", "– kWh"]        # a total needs every inverter's figure
    assert r["defaults"][0] == "22.2 kWh"                                   # the defaults, together, still work
