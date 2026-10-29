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


@pytest.mark.skipif(not shutil.which("node"), reason="needs node")
def test_card_parses_as_a_module() -> None:
    src = CARD.read_text()
    assert re.search(r'from "\./battman-card-base\.js"', src)
    subprocess.run(["node", "--check", "--input-type=module"], input=src, text=True, check=True)
