"""v0.10.0: Battman creates the Live Activity automations/script; end to end.
v0.26.0: its settings are attributes of sensor.battman_parameters and its switch is a template
switch (Battman's packages): set like every other Battman setting, while Battman is in charge."""

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
PARAMS = "sensor.battman_parameters"
IDS = ["automation.battman_live_activity_on_off", "automation.battman_live_activity_updates",
       "automation.battman_live_activity_follow", "script.battman_live_activity_push"]


async def _settle(hass):
    for _ in range(30):
        await asyncio.sleep(0)


def _write_config(hass, include=True):
    cfg = Path(hass.config.config_dir)
    (cfg / "configuration.yaml").write_text(
        "homeassistant:\n  packages: !include_dir_named packages\n"
        + ("automation: !include automations.yaml\nscript: !include scripts.yaml\n" if include else ""))
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
    # Battman is in charge, but these tests are about the Live Activity: its engine stays still
    engine = [s.entity_id for s in hass.states.async_all("automation") if s.entity_id.startswith("automation.battman_engine")]
    if engine:
        await hass.services.async_call("automation", "turn_off", {"entity_id": engine}, blocking=True)
    return entry


async def _set(hass, **settings):
    """Change Live Activity settings the way the Settings card does."""
    hass.bus.async_fire("battman_parameters_update", {"action": "SetAttribute", **settings})
    await _settle(hass)          # not block_till_done: it would wait out the automations' delays


def _la(hass, key):
    return hass.states.get(PARAMS).attributes[key]


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
    assert set(entry.data["automations_offered"]) >= {i.split(".", 1)[1] for i in IDS}   # made once, then remembered

    # edit one (it's yours now), delete another, press the button
    autos[0]["alias"] = "My on/off"
    autos = [a for a in autos if a["id"] != "battman_live_activity_updates"]
    Path(hass.config.path("automations.yaml")).write_text(yaml.safe_dump(autos, allow_unicode=True))
    await hass.services.async_call("automation", "reload", blocking=True)
    result = await hass.services.async_call(DOMAIN, "create_automations", {}, blocking=True, return_response=True)
    assert result["created"] == ["battman_live_activity_updates"]
    autos = yaml.safe_load(Path(hass.config.path("automations.yaml")).read_text())
    assert [a["alias"] for a in autos if a["id"] == "battman_live_activity_on_off"] == ["My on/off"]  # untouched
    await hass.async_block_till_done()
    assert hass.states.get("automation.battman_live_activity_updates") is not None
    again = await hass.services.async_call(DOMAIN, "create_automations", {}, blocking=True, return_response=True)
    assert again["created"] == [] and "nothing changed" in again["message"]


async def test_not_loaded_repair(hass: HomeAssistant) -> None:
    await _setup(hass, include=False)                          # configuration.yaml doesn't include them
    issue = ir.async_get(hass).async_get_issue(DOMAIN, "notifications_not_loaded")
    assert issue is not None and "battman_live_activity_push" in issue.translation_placeholders["missing"]


async def test_settings(hass: HomeAssistant) -> None:
    await _setup(hass)
    # the defaults (as the old setting entities had), and none of those entities any more
    assert (_la(hass, "liveActivity"), _la(hass, "liveActivityFollow"),
            _la(hass, "liveActivityFollowOn"), _la(hass, "liveActivityFollowOff"),
            _la(hass, "liveActivityFollowDelay"), _la(hass, "liveActivitySpikeAlert")) == (False, "", "ON", "OFF", 2, 0.3)
    assert "liveActivityPhone" not in hass.states.get(PARAMS).attributes     # the phone is the shared notify target now
    assert hass.states.get(SW).state == "off"
    for gone in ("select.battman_live_activity_phone", "text.battman_live_activity_follow",
                 "number.battman_live_activity_spike_alert"):
        assert hass.states.get(gone) is None, gone
    # the switch is the liveActivity setting, both ways
    await hass.services.async_call("switch", "turn_on", {"entity_id": SW}, blocking=True)
    await _settle(hass)
    assert _la(hass, "liveActivity") is True and hass.states.get(SW).state == "on"
    await _set(hass, liveActivity=False)
    assert hass.states.get(SW).state == "off"
    # out-of-range numbers are ignored, as for every Battman setting
    await _set(hass, liveActivityFollowDelay=99, liveActivitySpikeAlert=-1)
    assert (_la(hass, "liveActivityFollowDelay"), _la(hass, "liveActivitySpikeAlert")) == (2, 0.3)
    await _set(hass, liveActivityFollowDelay=5, liveActivitySpikeAlert=0.45)
    assert (_la(hass, "liveActivityFollowDelay"), _la(hass, "liveActivitySpikeAlert")) == (5, 0.45)


async def _states(hass, mode="Charge"):
    s = hass.states.async_set
    s("sensor.sigen_plant_battery_state_of_charge", "61.6")
    s("sensor.amber_5min_current_feed_in_price", "0.0512")
    s("sensor.amber_5min_current_general_price", "0.2349")
    await hass.services.async_call("input_select", "select_option",
                                   {"entity_id": "input_select.battman_mode", "option": mode}, blocking=True)
    s("sensor.battman_sell_total", "1", {"day": 1.20})
    s("sensor.battman_buy_total", "1", {"day": 2.45})
    await _set(hass, dailyNetworkCharge=0.60)


async def test_end_to_end(hass: HomeAssistant, freezer) -> None:
    await _setup(hass)
    await _states(hass)
    calls = _phone(hass)
    await _settle(hass)

    await hass.services.async_call("switch", "turn_on", {"entity_id": SW}, blocking=True)
    await _settle(hass)
    assert calls == []                                          # notify target is Off: nothing sent
    await hass.services.async_call("switch", "turn_off", {"entity_id": SW}, blocking=True)
    await _set(hass, alertNotifyTarget="test_phone")

    await hass.services.async_call("switch", "turn_on", {"entity_id": SW}, blocking=True)
    await _settle(hass)
    assert calls[-1]["title"] == "FIT 5.1c" and calls[-1]["message"] == "23.5c·-$1.85"
    d = calls[-1]["data"]
    assert d["progress"] == 62 and d["notification_icon"] == "mdi:battery-arrow-up" and d["silent"] is True
    assert d["progress_bar_color"] == "#8E8E93"                 # no dashboard theme picked: grey

    n = len(calls)                                              # spike: read from the Battman setting
    await _set(hass, liveActivitySpikeAlert=0.10, liveActivitySpikeAlertOn=True)
    hass.states.async_set("sensor.amber_5min_current_feed_in_price", "0.15")
    await _settle(hass)
    spikes = [c for c in calls[n:] if c.get("title", "").startswith("⚡")]
    assert len(spikes) == 1 and spikes[0]["title"] == "⚡ Feed-in spike 15.0c"   # a plain push, with a sound
    assert spikes[0]["data"]["push"]["sound"] == "default" and "live_update" not in spikes[0]["data"]

    freezer.tick(timedelta(minutes=3))                          # let the updates automation's wait finish
    async_fire_time_changed(hass)
    await _settle(hass)
    await hass.services.async_call("switch", "turn_off", {"entity_id": SW}, blocking=True)
    await _settle(hass)
    assert calls[-1]["message"] == "clear_notification" and calls[-1]["data"]["tag"] == "battery_live"


async def test_follow_settings(hass: HomeAssistant, freezer) -> None:
    await _setup(hass)
    hass.states.async_set("sensor.ignition", "OFF")
    await _set(hass, liveActivityFollow="sensor.ignition")
    await _settle(hass)
    assert hass.states.get(SW).state == "off"
    hass.states.async_set("sensor.ignition", "ON")
    await hass.async_block_till_done()
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
    await _set(hass, liveActivityFollowOn="Driving")            # other states, from the settings
    hass.states.async_set("sensor.ignition", "ON")
    await _settle(hass)
    assert hass.states.get(SW).state == "off"
    hass.states.async_set("sensor.ignition", "Driving")
    await _settle(hass)
    assert hass.states.get(SW).state == "on"


async def test_spike_alert_is_independent_of_the_live_activity(hass: HomeAssistant) -> None:
    """The spike alert needs only its own switch and a notify target: not the Live Activity switch, not the car."""
    await _setup(hass)
    await _states(hass)
    calls = _phone(hass)
    assert hass.states.get(SW).state == "off"
    await _set(hass, liveActivitySpikeAlert=0.30)
    hass.states.async_set("sensor.amber_5min_current_feed_in_price", "0.05")
    await _set(hass, alertNotifyTarget="test_phone")                # the alert switch is still off: no push
    hass.states.async_set("sensor.amber_5min_current_feed_in_price", "0.50")
    await _settle(hass)
    assert calls == []
    hass.states.async_set("sensor.amber_5min_current_feed_in_price", "0.05")
    await _set(hass, liveActivitySpikeAlertOn=True)
    hass.states.async_set("sensor.amber_5min_current_feed_in_price", "0.50")
    await _settle(hass)
    assert [c["title"] for c in calls] == ["⚡ Feed-in spike 50.0c"]
    assert hass.states.get(SW).state == "off"                       # and it didn't start the Live Activity
    # no notify target (Off): the alert is silent and doesn't error
    hass.states.async_set("sensor.amber_5min_current_feed_in_price", "0.05")
    await _set(hass, alertNotifyTarget="")
    hass.states.async_set("sensor.amber_5min_current_feed_in_price", "0.50")
    await _settle(hass)
    assert len(calls) == 1


async def test_live_activity_enabled_is_the_master_setting(hass: HomeAssistant) -> None:
    await _setup(hass)
    assert _la(hass, "liveActivityEnabled") is True                 # on to begin with: an existing follow keeps working
    await hass.services.async_call("switch", "turn_on", {"entity_id": SW}, blocking=True)
    await _settle(hass)
    assert hass.states.get(SW).state == "on"
    await _set(hass, liveActivityEnabled=False)                     # off: a running one is cleared
    assert hass.states.get(SW).state == "off"
    await hass.services.async_call("switch", "turn_on", {"entity_id": SW}, blocking=True)
    await _settle(hass)
    assert hass.states.get(SW).state == "off"                       # and the switch can't start it
    hass.states.async_set("sensor.ignition", "OFF")
    await _set(hass, liveActivityFollow="sensor.ignition")
    hass.states.async_set("sensor.ignition", "ON")                  # nor can the car
    await _settle(hass)
    assert hass.states.get(SW).state == "off"
    await _set(hass, liveActivityEnabled=True)
    hass.states.async_set("sensor.ignition", "OFF")
    hass.states.async_set("sensor.ignition", "ON")
    await hass.async_block_till_done()
    assert hass.states.get(SW).state == "on"
