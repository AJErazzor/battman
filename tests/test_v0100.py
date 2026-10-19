"""v0.10.0: Live Activity settings entities; Battman creates its automations/script; end to end."""

import asyncio
from datetime import timedelta
from pathlib import Path

import yaml
from homeassistant import config as conf_util
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

DOMAIN = "battman"
SW = "switch.battman_live_activity"
PHONE = "select.battman_live_activity_phone"
IDS = ["automation.battman_live_activity_on_off", "automation.battman_live_activity_updates",
       "automation.battman_live_activity_follow", "script.battman_live_activity_push"]


async def _settle(hass):
    for _ in range(30):
        await asyncio.sleep(0)


def _write_config(hass, include=True):
    cfg = Path(hass.config.config_dir)
    (cfg / "configuration.yaml").write_text(
        "automation: !include automations.yaml\nscript: !include scripts.yaml\n" if include else "")
    (cfg / "automations.yaml").write_text("[]\n")
    (cfg / "scripts.yaml").write_text("{}\n")


async def _setup(hass, include=True):
    _write_config(hass, include)
    config = await conf_util.async_hass_config_yaml(hass)
    assert await async_setup_component(hass, "homeassistant", {})
    assert await async_setup_component(hass, "lovelace", {})
    assert await async_setup_component(hass, "automation", config)
    assert await async_setup_component(hass, "script", config)
    entry = MockConfigEntry(domain=DOMAIN, title="Battman", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _phone(hass):
    """A fake phone: notify.test_phone, records every call."""
    calls = []

    async def handler(call: ServiceCall):
        calls.append(dict(call.data))

    hass.services.async_register("notify", "test_phone", handler)
    return calls


async def test_created_on_start_and_regenerate(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    for i in IDS:
        assert hass.states.get(i) is not None, i               # Battman made them, HA loaded them
    autos = yaml.safe_load(Path(hass.config.path("automations.yaml")).read_text())
    assert all(a["use_blueprint"]["input"] == {} for a in autos)  # nothing personal in them
    assert entry.data["live_activity_created_on_install"] is True

    # edit one (it's yours now), delete another, press the button
    autos[0]["alias"] = "My on/off"
    autos = [a for a in autos if a["id"] != "battman_live_activity_updates"]
    Path(hass.config.path("automations.yaml")).write_text(yaml.safe_dump(autos, allow_unicode=True))
    await hass.services.async_call("automation", "reload", blocking=True)
    result = await hass.services.async_call(DOMAIN, "create_live_activity", {}, blocking=True, return_response=True)
    assert result["created"] == ["battman_live_activity_updates"]
    autos = yaml.safe_load(Path(hass.config.path("automations.yaml")).read_text())
    assert [a["alias"] for a in autos if a["id"] == "battman_live_activity_on_off"] == ["My on/off"]  # untouched
    await hass.async_block_till_done()
    assert hass.states.get("automation.battman_live_activity_updates") is not None
    again = await hass.services.async_call(DOMAIN, "create_live_activity", {}, blocking=True, return_response=True)
    assert again["created"] == [] and "nothing changed" in again["message"]


async def test_not_loaded_repair(hass: HomeAssistant) -> None:
    await _setup(hass, include=False)                          # configuration.yaml doesn't include them
    issue = ir.async_get(hass).async_get_issue(DOMAIN, "live_activity_not_loaded")
    assert issue is not None and "battman_live_activity_push" in issue.translation_placeholders["missing"]


async def test_settings_entities(hass: HomeAssistant) -> None:
    await _setup(hass)
    assert hass.states.get(PHONE).state == "Off"
    assert hass.states.get("text.battman_live_activity_follow").state == ""
    assert hass.states.get("text.battman_live_activity_follow_on").state == "ON"
    assert hass.states.get("text.battman_live_activity_follow_off").state == "OFF"
    assert float(hass.states.get("number.battman_live_activity_follow_delay").state) == 2
    assert float(hass.states.get("number.battman_live_activity_spike_alert").state) == 0.3
    _phone(hass)
    await hass.async_block_till_done()
    assert "test_phone" in hass.states.get(PHONE).attributes["options"]   # follows HA's notify services
    await hass.services.async_call("select", "select_option", {"entity_id": PHONE, "option": "test_phone"}, blocking=True)
    hass.services.async_remove("notify", "test_phone")
    await hass.async_block_till_done()
    st = hass.states.get(PHONE)
    assert st.state == "test_phone" and st.attributes["problem"] == "notify.test_phone not found"  # flagged, not switched
    await hass.services.async_call("text", "set_value",
                                   {"entity_id": "text.battman_live_activity_follow", "value": "sensor.nope"}, blocking=True)
    assert hass.states.get("text.battman_live_activity_follow").attributes["problem"] == "sensor.nope not found"


async def _states(hass, mode="Charge"):
    s = hass.states.async_set
    s("sensor.sigen_plant_battery_state_of_charge", "61.6")
    s("sensor.amber_5min_current_feed_in_price", "0.0512")
    s("sensor.amber_5min_current_general_price", "0.2349")
    s("input_select.solarsystemcontrolmode", mode)
    s("sensor.solarsystemcontrolselltotal", "1", {"day": 1.20})
    s("sensor.solarsystemcontrolbuytotal", "1", {"day": 2.45})
    s("sensor.solarsystemcontrolparameters", "ok", {"dailyNetworkCharge": 0.60})


async def test_end_to_end(hass: HomeAssistant, freezer) -> None:
    await _setup(hass)
    await _states(hass)
    calls = _phone(hass)
    await hass.async_block_till_done()

    await hass.services.async_call("switch", "turn_on", {"entity_id": SW}, blocking=True)
    await _settle(hass)
    assert calls == []                                          # phone is Off: nothing sent
    await hass.services.async_call("switch", "turn_off", {"entity_id": SW}, blocking=True)
    await hass.services.async_call("select", "select_option", {"entity_id": PHONE, "option": "test_phone"}, blocking=True)

    await hass.services.async_call("switch", "turn_on", {"entity_id": SW}, blocking=True)
    await _settle(hass)
    assert calls[-1]["title"] == "FIT 5.1c" and calls[-1]["message"] == "23.5c·-$1.85"
    d = calls[-1]["data"]
    assert d["progress"] == 62 and d["notification_icon"] == "mdi:battery-arrow-up" and d["silent"] is True
    assert d["progress_bar_color"] == "#8E8E93"                 # no dashboard theme picked: grey

    n = len(calls)                                              # spike: read from the Battman setting
    await hass.services.async_call("number", "set_value",
                                   {"entity_id": "number.battman_live_activity_spike_alert", "value": 0.10}, blocking=True)
    hass.states.async_set("sensor.amber_5min_current_feed_in_price", "0.15")
    await _settle(hass)
    spikes = [c for c in calls[n:] if c.get("title", "").startswith("⚡")]
    assert spikes and spikes[0]["data"]["silent"] is False

    freezer.tick(timedelta(minutes=3))                          # let the updates automation's wait finish
    async_fire_time_changed(hass)
    await _settle(hass)
    await hass.services.async_call("switch", "turn_off", {"entity_id": SW}, blocking=True)
    await _settle(hass)
    assert calls[-1]["message"] == "clear_notification" and calls[-1]["data"]["tag"] == "battery_live"


async def test_follow_settings(hass: HomeAssistant, freezer) -> None:
    await _setup(hass)
    hass.states.async_set("sensor.ignition", "OFF")
    await hass.services.async_call("text", "set_value",
                                   {"entity_id": "text.battman_live_activity_follow", "value": "sensor.ignition"}, blocking=True)
    await _settle(hass)
    assert hass.states.get(SW).state == "off"
    hass.states.async_set("sensor.ignition", "ON")
    await _settle(hass)
    assert hass.states.get(SW).state == "on"
    hass.states.async_set("sensor.ignition", "OFF")
    await _settle(hass)
    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(hass)
    hass.states.async_set("sensor.ignition", "ON")              # quick stop: stays on
    await _settle(hass)
    freezer.tick(timedelta(minutes=3))
    async_fire_time_changed(hass)
    await _settle(hass)
    assert hass.states.get(SW).state == "on"
    hass.states.async_set("sensor.ignition", "OFF")
    await _settle(hass)
    freezer.tick(timedelta(minutes=2, seconds=1))
    async_fire_time_changed(hass)
    await _settle(hass)
    assert hass.states.get(SW).state == "off"
    await hass.services.async_call("text", "set_value",         # other states, from the settings
                                   {"entity_id": "text.battman_live_activity_follow_on", "value": "Driving"}, blocking=True)
    hass.states.async_set("sensor.ignition", "ON")
    await _settle(hass)
    assert hass.states.get(SW).state == "off"
    hass.states.async_set("sensor.ignition", "Driving")
    await _settle(hass)
    assert hass.states.get(SW).state == "on"
