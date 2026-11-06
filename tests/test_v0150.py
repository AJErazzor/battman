"""v0.15.0: Battery mode card (with the Engine log popup), and the forecast table scroll fix."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .dashboard_views import built
from .snapshots import assert_snapshot


DOMAIN = "battman"
ENGINELOG = (Path(__file__).parents[1] / "custom_components/battman/www/battman-enginelog.js").read_text()
FIX = Path(__file__).parent / "fixtures"
CARDS = Path(__file__).parents[1] / "custom_components/battman/cards"
LOG = "sensor.battman_engine_log"
needs_node = pytest.mark.skipif(not shutil.which("node"), reason="needs node to run the cards' JavaScript")


async def _card(hass, hass_client, cid):
    assert await async_setup_component(hass, "lovelace", {})
    MockConfigEntry(domain=DOMAIN, title="Battman", data={}).add_to_hass(hass)
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_client()
    return client, await (await client.get(f"/api/battman/cards/{cid}")).json()


def _popup(cfg):
    return cfg["cards"][0]["cards"][0]["cards"][2]["tap_action"]["battman_popup"]


async def test_batterymode_card(hass: HomeAssistant, hass_client) -> None:
    """The battery-mode card: entities, services, options, templates, styles, fx (snapshot)."""
    _client, card = await _card(hass, hass_client, "batterymode")
    assert card["missing_map"] == [] and card["needs"] == ["button-card"]
    raw = (CARDS / "batterymode.yaml").read_text().lower()
    for old in ("smiggles", "solarsystemcontrol", "solar_system_control", "ssc"):
        assert old not in raw, old
    m = json.loads(json.dumps(card["config"]))

    # every service call a button makes, listed
    def calls(x, out):
        if isinstance(x, dict):
            if x.get("action") == "call-service":
                out.append((x["service"], json.dumps(x["service_data"], sort_keys=True)))
            for v in x.values():
                calls(v, out)
        elif isinstance(x, list):
            for v in x:
                calls(v, out)
        return out
    got = calls(card["config"], [])
    # Self Consume and Drain are plain service calls; the five that can go against the price fire Battman's
    # "battman_mode" event instead (battman-lib.js asks when needed, then sets the mode: see test_v0360.py)
    assert len(got) == 3 and all(s == "input_select.select_option" for s, _ in got)
    assert {json.loads(d)["option"] for _, d in got} == {"Self Consume", "Drain"}
    # Battman's side, recorded so the comparison survives Smiggles' removal (popup emptied, as compared)
    assert_snapshot(__file__, "batterymode-config", m)
    assert_snapshot(__file__, "batterymode-service-calls", [[s, json.loads(d)] for s, d in got])


def _engine_log_popup(states):
    """Open the Engine log popup in node with a fake <dialog>; returns the dialog's markup and its settings."""
    lib = (Path(__file__).parents[1] / "custom_components/battman/www/battman-lib.js").read_text()
    script = ("globalThis.window = globalThis; globalThis.setTimeout = () => 0; globalThis.setInterval = () => 0;\n"
              + ENGINELOG + "\n" + lib + f"""
const states = {json.dumps(states)}; let shown = null;
const dlg = {{ attrs: {{}}, setAttribute(k, v) {{ this.attrs[k] = v; }}, querySelector: () => ({{ addEventListener() {{}} }}),
  addEventListener() {{}}, showModal() {{ shown = this; }}, remove() {{}}, close() {{}} }};
globalThis.document = {{ body: {{ appendChild() {{}} }}, documentElement: {{ style: {{}} }}, createElement: () => dlg,
  querySelector: () => ({{ hass: {{ states }} }}) }};
globalThis.getComputedStyle = () => ({{ getPropertyValue: (k) => k === '--battman-green' ? '#0f0' : '' }});
window.BattmanLib.showPopup({{ kind: 'enginelog', log: '{LOG}' }}, {{}});
process.stdout.write(JSON.stringify({{ html: dlg.innerHTML, style: dlg.attrs.style, open: !!shown }}));""")
    r = subprocess.run(["node", "-"], input=script, capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


@needs_node
async def test_engine_log_popup(hass: HomeAssistant, hass_client) -> None:
    _client, card = await _card(hass, hass_client, "batterymode")
    # the info button asks Battman's library to open it (no browser_mod)
    assert _popup(card["config"]) == {"kind": "enginelog", "log": LOG}
    assert "browser_mod" not in json.dumps(card["config"])
    msg = (FIX / "engine_log_sample.txt").read_text()
    full = _engine_log_popup({LOG: {"state": "x", "attributes": {"message": msg}}})
    assert full["open"] and "min(94vw,480px)" in full["style"] and "--battman-green:#0f0" in full["style"]
    full = full["html"]
    assert "Engine log" in full and "Last run 2026-10-20 16:10:34" in full
    for head in ("Mode", "Prices", "Battery", "SOC Limits", "Solar", "Actions", "Sell Forecasts", "Buy Forecasts",
                 "Version", "Debug"):
        assert f">{head}</span>" in full, head
    assert "100.0% (40.0 kWh)" in full and "Tracking Buy:" in full
    assert "color:var(--battman-darkred);'>$-0.1209</b>" in full                # negative $ red
    assert "color:var(--battman-green);'>True</b>" in full
    for emoji in ("🕐", "🔄", "💰", "🔋", "📊", "☀", "⚡", "📈", "📉", "ℹ"):
        assert emoji not in full                                               # emoji pick colours, aren't shown
    assert "max-height:82vh" in full and "var(--battman-surface-popup)" in full
    assert 'class="x"' in full                                                 # a close button (the page behind is dimmed)
    assert f"Engine log: missing {LOG}" in _engine_log_popup({})["html"]
    assert "has no log message yet" in _engine_log_popup({LOG: {"state": "x", "attributes": {"message": "  "}}})["html"]


async def test_forecast_table_scrolls(hass: HomeAssistant, hass_client) -> None:
    """button-card makes a card with no tap action pointer-events: none (no scrolling)."""
    _client, card = await _card(hass, hass_client, "amber24hourforecasttable")
    styles = card["config"]["cards"][0]["styles"]["card"]
    assert {"pointer-events": "auto"} in styles


async def test_power_view_section1(hass: HomeAssistant, hass_client) -> None:
    client, _card_ = await _card(hass, hass_client, "batterymode")
    power = (await built(hass))["views"][0]
    assert [c["type"] for c in power["sections"][0]["cards"]] == [
        "custom:battman-house", "custom:battman-batterymode", "custom:battman-state", "custom:battman-profitloss", "custom:battman-overrides"]
