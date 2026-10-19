"""v0.9.0: Live Activity switch and blueprints."""

import asyncio
from datetime import timedelta
from pathlib import Path

import yaml
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_capture_events, async_fire_time_changed

DOMAIN = "battman"
SW = "switch.battman_live_activity"
PUSH = "script.fake_push"
BP = Path(__file__).resolve().parent.parent / "custom_components" / "battman" / "blueprints"


async def _setup(hass, extra_scripts=None):
    assert await async_setup_component(hass, "homeassistant", {})
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain=DOMAIN, title="Battman", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    # stand-in for the script made from the push blueprint: records how it was called
    assert await async_setup_component(hass, "script", {"script": {**(extra_scripts or {}), "fake_push": {
        "fields": {"alert": {}, "clear": {}},
        "sequence": [{"event": "fake_push", "event_data": {
            "alert": "{{ alert | default(false) }}", "clear": "{{ clear | default(false) }}"}}]}}})
    return entry


async def _settle(hass):
    """Let triggered automations run up to their next delay (block_till_done would wait out the delay)."""
    for _ in range(20):
        await asyncio.sleep(0)


def _auto(name, **inputs):
    return {"alias": name, "use_blueprint": {"path": f"battman/battman_live_activity_{name}.yaml", "input": inputs}}


async def test_switch_and_install(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    assert hass.states.get(SW).state == "off"
    await hass.services.async_call("switch", "turn_on", {"entity_id": SW}, blocking=True)
    assert hass.states.get(SW).state == "on"
    adir = Path(hass.config.path("blueprints/automation/battman"))
    sdir = Path(hass.config.path("blueprints/script/battman"))
    assert sorted(p.name for p in adir.glob("*.yaml")) == [
        "battman_live_activity_follow.yaml", "battman_live_activity_on_off.yaml", "battman_live_activity_updates.yaml"]
    assert [p.name for p in sdir.glob("*.yaml")] == ["battman_live_activity_push.yaml"]
    (adir / "old_one.yaml").write_text("x: 1\n")
    from custom_components.battman import blueprint_install
    await blueprint_install.async_install(hass)
    assert not (adir / "old_one.yaml").exists()                 # files Battman no longer ships go
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert not adir.exists() and not sdir.exists()


async def test_on_off_blueprint(hass: HomeAssistant, freezer) -> None:
    await _setup(hass)
    hass.states.async_set("sensor.fit", "0.10")
    assert await async_setup_component(hass, "automation", {"automation": [
        _auto("on_off", push_script=PUSH, feed_in_price="sensor.fit", keep_alive_hours=7)]})
    await hass.async_block_till_done()
    pushes = async_capture_events(hass, "fake_push")

    async def flip(service):
        await hass.services.async_call("switch", service, {"entity_id": SW}, blocking=True)
        await hass.async_block_till_done()

    await flip("turn_on")
    assert [(e.data["alert"], e.data["clear"]) for e in pushes] == [(False, False)]
    hass.states.async_set("sensor.fit", "0.35")                 # spike above 0.30 while on
    await hass.async_block_till_done()
    assert (pushes[-1].data["alert"], pushes[-1].data["clear"]) == (True, False)
    await flip("turn_off")
    assert (pushes[-1].data["alert"], pushes[-1].data["clear"]) == (False, True)
    n = len(pushes)
    hass.states.async_set("sensor.fit", "0.05")
    hass.states.async_set("sensor.fit", "0.40")                 # spike while off: nothing
    await hass.async_block_till_done()
    assert len(pushes) == n

    await flip("turn_on")                                       # keep-alive: off/on after 7 h
    freezer.tick(timedelta(hours=7, seconds=1))
    async_fire_time_changed(hass)
    await _settle(hass)
    assert hass.states.get(SW).state == "off"
    freezer.tick(timedelta(seconds=6))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(SW).state == "on"
    assert [e.data["clear"] for e in pushes[n:]] == [False, True, False]   # on, cleared, on again


async def test_updates_blueprint(hass: HomeAssistant, freezer) -> None:
    await _setup(hass)
    hass.states.async_set("sensor.soc", "50")
    assert await async_setup_component(hass, "automation", {"automation": [
        _auto("updates", push_script=PUSH, watch=["sensor.soc"], min_gap=2)]})
    await hass.async_block_till_done()
    pushes = async_capture_events(hass, "fake_push")
    hass.states.async_set("sensor.soc", "51")                   # switch off: nothing
    await hass.async_block_till_done()
    assert pushes == []
    await hass.services.async_call("switch", "turn_on", {"entity_id": SW}, blocking=True)
    hass.states.async_set("sensor.soc", "52")
    await _settle(hass)
    assert len(pushes) == 1
    hass.states.async_set("sensor.soc", "53")                   # within the 2 min: dropped
    hass.states.async_set("sensor.soc", "53", {"x": 1})         # attribute-only: never a trigger
    await _settle(hass)
    assert len(pushes) == 1
    freezer.tick(timedelta(minutes=2, seconds=1))
    async_fire_time_changed(hass)
    await _settle(hass)
    assert len(pushes) == 2                                     # trailing push lands the latest
    hass.states.async_set("sensor.soc", "unavailable")          # shows as "—", so it's pushed too
    await _settle(hass)
    assert len(pushes) == 3
    freezer.tick(timedelta(minutes=2, seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_follow_blueprint(hass: HomeAssistant, freezer) -> None:
    await _setup(hass)
    hass.states.async_set("sensor.ignition", "OFF")
    assert await async_setup_component(hass, "automation", {"automation": [
        _auto("follow", follow="sensor.ignition", on_state="ON", off_state="OFF", off_after=2)]})
    await hass.async_block_till_done()
    hass.states.async_set("sensor.ignition", "ON")
    await hass.async_block_till_done()
    assert hass.states.get(SW).state == "on"
    hass.states.async_set("sensor.ignition", "OFF")
    await hass.async_block_till_done()
    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(hass)
    hass.states.async_set("sensor.ignition", "ON")              # quick stop: stays on
    await hass.async_block_till_done()
    freezer.tick(timedelta(minutes=2))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(SW).state == "on"
    hass.states.async_set("sensor.ignition", "OFF")
    await hass.async_block_till_done()
    freezer.tick(timedelta(minutes=2, seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(SW).state == "off"
    hass.states.async_set("sensor.ignition", "unavailable")     # back from unavailable: ignored
    hass.states.async_set("sensor.ignition", "ON")
    await hass.async_block_till_done()
    assert hass.states.get(SW).state == "off"


class _Input(str):
    pass


def _load_push(inputs: dict) -> dict:
    """The push blueprint with inputs filled in and the phone steps swapped for a test event."""
    class L(yaml.SafeLoader):
        pass
    L.add_constructor("!input", lambda loader, node: _Input(loader.construct_scalar(node)))
    bp = yaml.load((BP / "script" / "battman_live_activity_push.yaml").read_text(), Loader=L)

    defaults = {}
    def walk_inputs(d):
        for k, v in d.items():
            if "input" in v:
                walk_inputs(v["input"])
            elif "default" in v:
                defaults[k] = v["default"]
    walk_inputs(bp["blueprint"]["input"])
    values = {**defaults, **inputs}

    def sub(x):
        if isinstance(x, _Input):
            return values[str(x)]
        if isinstance(x, dict):
            if x.get("domain") == "mobile_app":               # the send-to-phone step
                return {"event": "phone", "event_data": {
                    "title": x.get("title", ""), "message": x["message"], "data": x.get("data", {})}}
            return {k: sub(v) for k, v in x.items()}
        if isinstance(x, list):
            return [sub(v) for v in x]
        return x
    return {"fields": bp["fields"], "mode": bp["mode"], "sequence": sub(bp["sequence"])}


async def test_push_blueprint_templates(hass: HomeAssistant) -> None:
    await _setup(hass, {"bm_push": _load_push({"phone": "x"})})
    s = hass.states.async_set
    s("sensor.sigen_plant_battery_state_of_charge", "61.6")
    s("sensor.amber_5min_current_feed_in_price", "0.0512")
    s("sensor.amber_5min_current_general_price", "0.2349")
    s("input_select.solarsystemcontrolmode", "Charge")
    s("sensor.solarsystemcontrolselltotal", "1", {"day": 1.20})
    s("sensor.solarsystemcontrolbuytotal", "1", {"day": 2.45})
    s("sensor.solarsystemcontrolparameters", "ok", {"dailyNetworkCharge": 0.60})
    s("sensor.battman_theme_mode_colours", '{"green":"#a3be8c","yellow":"#e9d8a6","blue":"#81a1c1","orange":"#d08770","red":"#a85560","purple":"#b48ead"}')
    sent = async_capture_events(hass, "phone")

    async def push(**fields):
        await hass.services.async_call("script", "bm_push", fields, blocking=True)
        await hass.async_block_till_done()
        return sent[-1].data

    p = await push()
    assert p["title"] == "FIT 5.1c" and p["message"] == "23.5c·-$1.85"
    d = p["data"]
    assert d["progress"] == 62 and d["progress_max"] == 100 and d["progress_bar_color"] == "#e9d8a6"
    assert d["notification_icon"] == "mdi:battery-arrow-up" and d["silent"] is True and d["tag"] == "battery_live"

    assert (await push(alert=True))["title"] == "⚡ FIT 5.1c"
    assert (await push(clear=True))["message"] == "clear_notification"

    # nothing made up: unavailable values show "—", unknown mode "?" in red, no theme = grey
    s("sensor.sigen_plant_battery_state_of_charge", "unavailable")
    s("sensor.amber_5min_current_feed_in_price", "unknown")
    s("sensor.solarsystemcontrolbuytotal", "1", {})
    s("input_select.solarsystemcontrolmode", "Turbo")
    s("sensor.battman_theme_mode_colours", "unknown")
    p = await push()
    assert p["title"] == "FIT —" and p["message"] == "SOC — · 23.5c·$—"
    d = p["data"]
    assert "progress" not in d and d["notification_icon"] == "mdi:help-circle"
    assert d["notification_icon_color"] == "#FF453A" and d["progress_bar_color"] == "#8E8E93"


async def test_blueprints_valid(hass: HomeAssistant) -> None:
    from homeassistant.components.blueprint import models, schemas

    for domain in ("automation", "script"):
        for f in (BP / domain).glob("*.yaml"):
            from homeassistant.util.yaml import load_yaml_dict
            models.Blueprint(load_yaml_dict(str(f)), expected_domain=domain, schema=schemas.BLUEPRINT_SCHEMA)
