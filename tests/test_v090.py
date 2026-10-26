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
    adir = Path(hass.config.path("blueprints/automation/battman"))
    sdir = Path(hass.config.path("blueprints/script/battman"))
    assert {"battman_live_activity_follow.yaml", "battman_live_activity_on_off.yaml",
            "battman_live_activity_updates.yaml"} <= {p.name for p in adir.glob("*.yaml")}
    assert "battman_live_activity_push.yaml" in {p.name for p in sdir.glob("*.yaml")}
    (adir / "old_one.yaml").write_text("x: 1\n")
    from custom_components.battman import blueprint_install
    await blueprint_install.async_install(hass)
    assert not (adir / "old_one.yaml").exists()                 # files Battman no longer ships go
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert not adir.exists() and not sdir.exists()


async def test_blueprints_valid(hass: HomeAssistant) -> None:
    from homeassistant.components.blueprint import models, schemas

    for domain in ("automation", "script"):
        for f in (BP / domain).glob("*.yaml"):
            from homeassistant.util.yaml import load_yaml_dict
            models.Blueprint(load_yaml_dict(str(f)), expected_domain=domain, schema=schemas.BLUEPRINT_SCHEMA)
