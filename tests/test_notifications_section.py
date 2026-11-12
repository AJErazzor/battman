"""v0.34.0: one Notifications section and one shared notify target. Every alert starts off; the
Amber price alerts and the off-grid alert are Battman blueprints, made once per version that has
them (a deleted one stays deleted); the create action is generic."""

from datetime import timedelta
from pathlib import Path

import pytest
import yaml
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from .test_live_activity_install import PARAMS, _la, _phone, _set, _settle, _setup

NEW = ["automation.battman_amber_cheap_price_alert", "automation.battman_amber_negative_price_alert",
       "automation.battman_amber_charge_from_the_alert", "automation.battman_off_grid_alert",
       "automation.battman_spike_alert"]
NEW_IDS = ["battman_amber_buy_alert", "battman_amber_negative_alert", "battman_amber_charge_action",
           "battman_offgrid_alert", "battman_spike_alert"]
SWITCHES = ["liveActivity", "liveActivitySpikeAlertOn", "amberBuyAlert", "amberNegativeBuyAlert", "offGridAlert",
            "offGridRestoredAlert"]


async def test_every_notification_starts_off(hass: HomeAssistant) -> None:
    await _setup(hass)
    for key in SWITCHES:
        assert _la(hass, key) is False, key
    assert _la(hass, "alertNotifyTarget") == ""                     # the shared target is Off
    assert _la(hass, "offGridAlertDelay") == 1
    await _set(hass, offGridAlertDelay=31)                          # out-of-range numbers are ignored
    assert _la(hass, "offGridAlertDelay") == 1


async def test_blueprint_automations_are_made_and_loaded(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    for i in NEW:
        assert hass.states.get(i) is not None, i
        assert hass.states.get(i).state != "unavailable", i          # the blueprint made a valid automation
    assert set(entry.data["automations_offered"]) >= set(NEW_IDS)


async def test_each_is_made_once(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    path = Path(hass.config.path("automations.yaml"))
    autos = [a for a in yaml.safe_load(path.read_text()) if a["id"] != "battman_offgrid_alert"]
    path.write_text(yaml.safe_dump(autos, allow_unicode=True))
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert "battman_offgrid_alert" not in {a["id"] for a in yaml.safe_load(path.read_text())}   # deleted stays deleted
    # a version that has a new one: it isn't in the offered list yet, so it arrives by itself
    hass.config_entries.async_update_entry(
        entry, data={**entry.data, "automations_offered": [i for i in entry.data["automations_offered"] if i != "battman_offgrid_alert"]})
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert "battman_offgrid_alert" in {a["id"] for a in yaml.safe_load(path.read_text())}


async def test_create_automations_action(hass: HomeAssistant) -> None:
    await _setup(hass)
    path = Path(hass.config.path("automations.yaml"))
    autos = [a for a in yaml.safe_load(path.read_text()) if a["id"] != "battman_amber_buy_alert"]
    path.write_text(yaml.safe_dump(autos, allow_unicode=True))
    result = await hass.services.async_call("battman", "create_automations", {}, blocking=True, return_response=True)
    assert result["created"] == ["battman_amber_buy_alert"]
    assert not hass.services.has_service("battman", "create_live_activity")


async def test_cheap_price_alert(hass: HomeAssistant) -> None:
    await _setup(hass)
    calls = _phone(hass)
    s = hass.states.async_set
    s("sensor.sigen_plant_battery_state_of_charge", "50")
    s("sensor.amber_5min_current_general_price", "0.20")
    await _set(hass, alertNotifyTarget="test_phone")
    await _settle(hass)
    s("sensor.amber_5min_current_general_price", "0.05")
    await _settle(hass)
    assert calls == []                                              # the alert's switch is off
    s("sensor.amber_5min_current_general_price", "0.20")
    await _set(hass, amberBuyAlert=True)
    s("sensor.amber_5min_current_general_price", "0.05")
    await _settle(hass)
    assert calls and calls[-1]["title"] == "⚡ Cheap Power" and "Buy 5.0c" in calls[-1]["message"]
    n = len(calls)
    await _set(hass, alertNotifyTarget="")                          # target Off silences it
    s("sensor.amber_5min_current_general_price", "0.20")
    await _settle(hass)
    s("sensor.amber_5min_current_general_price", "0.05")
    await _settle(hass)
    assert len(calls) == n


# Sigenergy-Local-Modbus 1.x stores the labels, 2.x stores the keys: the alert works with both
GRID_FORMS = [("On Grid", "Off Grid (Auto)", "Off Grid (Manual)"), ("on_grid", "off_grid_auto", "off_grid_manual")]


@pytest.mark.parametrize("on,auto,manual", GRID_FORMS)
async def test_offgrid_alert(hass: HomeAssistant, freezer, on: str, auto: str, manual: str) -> None:
    await _setup(hass)
    calls = _phone(hass)
    s = hass.states.async_set
    s("sensor.sigen_plant_battery_state_of_charge", "50")
    s("sensor.sigen_plant_rated_energy_capacity", "40")
    s("sensor.sigen_plant_consumed_power", "2")
    s("sensor.sigen_plant_grid_connection_status", on)
    await _set(hass, alertNotifyTarget="test_phone", offGridAlertDelay=0)
    s("sensor.sigen_plant_grid_connection_status", auto)
    await _settle(hass)
    freezer.tick(timedelta(seconds=2))
    async_fire_time_changed(hass)
    await _settle(hass)
    assert calls == []                                              # off-grid alert is off
    s("sensor.sigen_plant_grid_connection_status", on)
    await _set(hass, offGridAlert=True)
    s("sensor.sigen_plant_grid_connection_status", auto)
    await _settle(hass)
    freezer.tick(timedelta(seconds=2))
    async_fire_time_changed(hass)
    await _settle(hass)
    assert calls and calls[-1]["title"] == "🔌 Power outage"
    assert calls[-1]["message"] == "Battery 50% · about 10 h at 2.0 kW"          # 40 kWh × 50% ÷ 2 kW
    assert calls[-1]["data"]["push"] == {"interruption-level": "time-sensitive"}
    n = len(calls)
    s("sensor.sigen_plant_grid_connection_status", on)
    await _settle(hass)
    assert len(calls) == n                                          # restored alert is off
    await _set(hass, offGridRestoredAlert=True)
    s("sensor.sigen_plant_grid_connection_status", manual)
    await _settle(hass)
    freezer.tick(timedelta(seconds=2))
    async_fire_time_changed(hass)
    await _settle(hass)
    assert calls[-1]["title"] == "🔌 Switched to off-grid"
    s("sensor.sigen_plant_grid_connection_status", on)
    await _settle(hass)
    assert calls[-1]["title"] == "✅ Grid is back" and calls[-1]["message"] == "Battery 50%"
