"""v0.15.0: Battery mode card (with the Engine log popup), and the forecast table scroll fix."""

import json
import shutil
from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .test_v0130 import run_js
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
    return cfg["cards"][0]["cards"][2]["tap_action"]["browser_mod"]["data"]


async def test_batterymode_card(hass: HomeAssistant, hass_client) -> None:
    """The battery-mode card: entities, services, options, templates, styles, fx (snapshot)."""
    _client, card = await _card(hass, hass_client, "batterymode")
    assert card["missing_map"] == [] and card["needs"] == ["button-card"]
    raw = (CARDS / "batterymode.yaml").read_text().lower()
    for old in ("smiggles", "solarsystemcontrol", "solar_system_control", "ssc"):
        assert old not in raw, old
    m = json.loads(json.dumps(card["config"]))
    _popup(m).clear()

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
    assert len(got) == 10 and all(s == "input_select.select_option" for s, _ in got)
    assert {json.loads(d)["option"] for _, d in got} == {"Charge", "Discharge", "Self Consume", "Float", "Drain",
                                                          "Float Solar Off", "Charge Solar Off"}
    # Battman's side, recorded so the comparison survives Smiggles' removal (popup emptied, as compared)
    assert_snapshot(__file__, "batterymode-config", m)
    assert_snapshot(__file__, "batterymode-service-calls", [[s, json.loads(d)] for s, d in got])


@needs_node
async def test_engine_log_popup(hass: HomeAssistant, hass_client) -> None:
    _client, card = await _card(hass, hass_client, "batterymode")
    pop = _popup(card["config"])
    assert pop["title"] == " " and "min(94vw,480px)" in pop["style"]
    msg = (FIX / "engine_log_sample.txt").read_text()
    out = run_js([(pop["content"], {LOG: {"state": "x", "attributes": {"message": msg}}}, None),
                  (pop["content"], {}, None),
                  (pop["content"], {LOG: {"state": "x", "attributes": {"message": "  "}}}, None)], prelude=ENGINELOG)
    # without Battman's log renderer it says so
    assert "isn't loaded" in run_js([(pop["content"], {LOG: {"state": "x", "attributes": {"message": msg}}}, None)])[0]
    full = out[0]
    assert not full.startswith("THROW")
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
    assert f"Engine log: missing {LOG}" in out[1] and "No data" not in out[1]
    assert "has no log message yet" in out[2]
    # the engine log popup: recorded as it draws
    assert_snapshot(__file__, "enginelog-popup", {k: v for k, v in pop.items() if k != "content"})
    assert_snapshot(__file__, "enginelog-popup-template", pop["content"])
    for name, text in zip(("sample", "no-sensor", "blank-message"), out, strict=True):
        assert_snapshot(__file__, f"enginelog-draw-{name}", text)


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
