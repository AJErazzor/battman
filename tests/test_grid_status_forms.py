"""Sigenergy-Local-Modbus stores the grid connection status as labels in 1.x ("On Grid",
"Off Grid (Auto)", "Off Grid (Manual)") and as keys in 2.x (on_grid, off_grid_auto, off_grid_manual).
Battman reads both the same way, and anything else is not on grid.

- the engine's `on_grid` (battman_engine_inputs.yaml)
- the Chill card's off-grid takeover (cards/state.yaml), checked in Node
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import Template

ROOT = Path(__file__).parents[1] / "custom_components/battman"


class _Loader(yaml.SafeLoader):
    pass


_Loader.add_multi_constructor("!", lambda loader, suffix, node: None)

ON = ["On Grid", "on_grid"]
AUTO = ["Off Grid (Auto)", "off_grid_auto"]
MANUAL = ["Off Grid (Manual)", "off_grid_manual"]
NOT_ON_GRID = ["unknown", "unavailable", "", "Off Grid", "Offline", "grid", "off_grid", "ON GRID LATER"]


def _inputs() -> tuple[dict, str]:
    """The engine's 'Which sensors' variables and the `on_grid` template it builds."""
    doc = yaml.load((ROOT / "blueprints/script/battman_engine_inputs.yaml").read_text(), Loader=_Loader)
    sensors = next(s["variables"] for s in doc["sequence"] if "grid_status" in s.get("variables", {}))
    params = next(s["variables"]["params"] for s in doc["sequence"] if "params" in s.get("variables", {}))
    return sensors, params["on_grid"]


def _on_grid(hass: HomeAssistant, state: str) -> bool:
    sensors, template = _inputs()
    hass.states.async_set(sensors["grid_status"], state)
    return Template(template, hass).async_render(
        {"grid_status": sensors["grid_status"], "grid_status_on": sensors["grid_status_on"]})


@pytest.mark.parametrize("state", ON)
def test_engine_is_on_grid(hass: HomeAssistant, state: str) -> None:
    assert _on_grid(hass, state) is True


@pytest.mark.parametrize("state", AUTO + MANUAL + NOT_ON_GRID)
def test_engine_is_not_on_grid(hass: HomeAssistant, state: str) -> None:
    assert _on_grid(hass, state) is False


def test_blueprint_triggers_have_both_forms() -> None:
    doc = yaml.load((ROOT / "blueprints/automation/battman_offgrid_alert.yaml").read_text().replace("[[map:parameters]]", "x"),
                    Loader=_Loader)
    off, restored = doc["triggers"]
    assert set(off["to"]) == set(AUTO + MANUAL)
    assert set(restored["from"]) == set(AUTO + MANUAL)
    assert set(restored["to"]) == set(ON)


def _card_grid_state() -> str:
    """The card's own `gridState` function, as written in cards/state.yaml."""
    m = re.search(r"const gridState = (\(s\) => .+?);\n", (ROOT / "cards/state.yaml").read_text())
    assert m, "cards/state.yaml has no gridState"
    return m.group(1)


@pytest.mark.skipif(shutil.which("node") is None, reason="needs Node")
def test_card_reads_both_forms() -> None:
    cases = {s: "on_grid" for s in ON} | {s: "off_grid_auto" for s in AUTO} | {s: "off_grid_manual" for s in MANUAL}
    script = f"const f = {_card_grid_state()}; const c = {json.dumps(cases)}; " \
             "const bad = Object.entries(c).filter(([k, v]) => f(k) !== v); " \
             "const other = [undefined, null, 'unknown', 'unavailable', 'Off Grid', 'off_grid'].map(f); " \
             "console.log(JSON.stringify({bad, other}));"
    out = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout)
    assert out["bad"] == []
    assert not {"off_grid_auto", "off_grid_manual"} & set(out["other"])      # nothing else counts as off-grid
