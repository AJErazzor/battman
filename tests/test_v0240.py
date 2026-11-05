"""v0.24.0: fixes, and Battman's own grid power and load average sensors off the map.

(The State card's look-ahead used to have its own copy of the sell-rule maths, checked here against
the engine. The popup now shows the engine's own forecast, so those checks are gone.)
"""

import json
import random
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import yaml
from homeassistant.core import HomeAssistant

from custom_components.battman.const import ENTITY_MAP_DEFAULTS

from . import engine_harness as H

ROOT = Path(__file__).parents[1] / "custom_components/battman"
needs_node = pytest.mark.skipif(not shutil.which("node"), reason="needs node")
TZ = "Australia/Adelaide"


def _lib(script: str) -> dict:
    """Run battman-lib.js in node with a fake page, then script; returns what script prints."""
    page = """
const calls = [], toasts = [];
const hass = { states: {}, themes: { themes: {} }, callService: (...a) => calls.push(['server', ...a]) };
globalThis.window = globalThis;
globalThis.getComputedStyle = () => ({ getPropertyValue: () => '' });
globalThis.CustomEvent = class { constructor(t, o) { this.type = t; this.detail = o.detail; } };
globalThis.document = { querySelector: (s) => (s === 'home-assistant' ? { hass, dispatchEvent: (e) => toasts.push(e.detail.message) } : null) };
const btn = { tagName: 'BUTTON', dispatchEvent: (e) => toasts.push(e.detail.message) };
"""
    js = page + LIB.read_text() + "\n" + script
    r = subprocess.run(["node", "-"], input=js, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@needs_node
def test_correct_totals_opens_on_this_device() -> None:
    """It used to ask the server for a browser_mod popup with no browser named, which only reaches
    browsers registered with browser_mod (so nothing on an unregistered phone)."""
    out = _lib("""
window.browser_mod = { service: (s, d) => calls.push(['local', s, d.title, d.content.type]) };
window.BattmanLib.correctTotals(btn, {buy: 'sensor.b', sell: 'sensor.s', event: 'e'});
process.stdout.write(JSON.stringify({calls, toasts}));""")
    assert out == {"calls": [["local", "popup", "Correct totals", "custom:button-card"]], "toasts": []}
    out = _lib("""
window.BattmanLib.correctTotals(btn, {buy: 'sensor.b', sell: 'sensor.s', event: 'e'});
process.stdout.write(JSON.stringify({calls, toasts}));""")
    assert out["calls"] == [] and out["toasts"] == ["Correct totals needs browser_mod, which isn't loaded on this device."]


def test_no_server_popups_left() -> None:
    lib = LIB.read_text()
    assert "callService('browser_mod'" not in lib and 'callService("browser_mod"' not in lib
    for gone in ("openPopup", "renderDock", "isVisible", "BattmanLib.CFG"):
        assert gone not in lib, gone


# ── grid power and load average off the map ──────────────────────────────────────────────

def test_battmans_own_sensors_by_name() -> None:
    from custom_components.battman import required_entities as R

    base = (ROOT / "www/battman-card-base.js").read_text()
    s = base.index("export const BATTMAN_SENSORS")
    own = dict(re.findall(r'^  (\w+): "([^"]+)",$', base[s:base.index("};", s)], re.M))
    assert own == {"grid_power": "sensor.battman_grid_power", "load_30m_avg": "sensor.battman_load_30m_avg"}
    for k, v in own.items():
        assert R.NAMED[k] == v and k not in ENTITY_MAP_DEFAULTS, k
    for f in [*ROOT.glob("cards/*.yaml"), *ROOT.glob("views/*.yaml"), *ROOT.glob("www/*.js")]:
        text = f.read_text()
        assert not re.search(r"\[\[map:(grid_power|load_30m_avg)\]\]|\{\{(grid_power|load_30m_avg)\}\}", text), f.name
        if re.search(r"\bM\.(grid_power|load_30m_avg)\b", text):
            assert "...BATTMAN_SENSORS" in text and re.search(r"import \{[^}]*\bBATTMAN_SENSORS\b", text), f.name
        for k in own:
            assert f"'{k}'" not in text.split("const NEEDS")[1].split(";")[0] if "const NEEDS" in text else True, (f.name, k)


# ── Solcast missing: no made-up 0 ────────────────────────────────────────────────────────

SOLCAST_REMAIN = "sensor.solcast_pv_forecast_forecast_remaining_today"


async def _engine_run(hass, freezer):
    """Battman's engine at 11am (solar sponge time), the battery half full; the run's figures and log."""
    from .test_finances_cards import _start_totals

    await hass.config.async_set_time_zone(TZ)
    freezer.move_to(datetime(2026, 10, 21, 11, 0, 10, tzinfo=ZoneInfo(TZ)))
    await _start_totals(hass)
    await hass.services.async_call("automation", "turn_off", {"entity_id": "all"}, blocking=True)
    soc, price = H.curves(random.Random(3))
    hass.bus.async_fire("battman_soc_curves_update", {"curves": soc})
    hass.bus.async_fire("battman_price_curves_update", {"curves": price})
    hass.states.async_set("sensor.sigen_plant_battery_state_of_charge", "50")
    await hass.async_block_till_done()

    async def run():
        await hass.services.async_call("script", "turn_on", {"entity_id": "script.battman_engine"}, blocking=True)
        await H.tick(hass, 3)
        await H.tick(hass, 1)
        return (hass.states.get("sensor.battman_run").attributes,
                hass.states.get("sensor.battman_engine_log").attributes["message"])
    return run


async def test_engine_skips_the_sun_check_without_solcast(hass: HomeAssistant, freezer) -> None:
    run = await _engine_run(hass, freezer)
    # Solcast says no sun left: half the battery to fill is more than the gap allowed -> No Sun
    hass.states.async_set(SOLCAST_REMAIN, "0", {"estimate": 0, "estimate10": 0, "estimate90": 0})
    attrs, msg = await run()
    assert str(attrs["needSun"]).lower() == "true" and "Remaining (10%): 0.0 kWh" in msg
    # Solcast missing: it used to be read as 0 kWh (the same No Sun panic); now the check is skipped
    for gone in ("unavailable", None):
        if gone is None:
            hass.states.async_remove(SOLCAST_REMAIN)
        else:
            hass.states.async_set(SOLCAST_REMAIN, gone, {})
        attrs, msg = await run()
        assert str(attrs["needSun"]).lower() == "false", gone
        assert ("Remaining (10%): missing (sensor.solcast_pv_forecast_forecast_remaining_today has no estimate10), "
                "sun check skipped") in msg, gone
    # back: used again
    hass.states.async_set(SOLCAST_REMAIN, "30", {"estimate": 30, "estimate10": 25.5, "estimate90": 33})
    attrs, msg = await run()
    assert str(attrs["needSun"]).lower() == "false" and "Remaining (10%): 25.5 kWh" in msg


def test_engine_has_no_made_up_solar() -> None:
    inputs = (ROOT / "blueprints/script/battman_engine_inputs.yaml").read_text()
    decide = (ROOT / "blueprints/script/battman_engine_decide.yaml").read_text()
    assert "estimate10') | float(0)" not in inputs and "estimate10'') | float(0)" not in inputs
    assert "pvRemainingNotGood: '{{ pvRemainingKnown and" in decide
