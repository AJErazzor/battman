"""v0.26.0: a tidier Battman device.

- The NEM sensors only exist while the OpenNEM integration is installed (made when it's added,
  removed when it's removed), and aren't on the Battman device: they're OpenNEM's figures, not
  Battman's settings or controls. Their entity IDs stay sensor.battman_nem_*.
"""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.battman.nem import ALL_KEYS

DOMAIN = "battman"


async def _setup(hass):
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain=DOMAIN, title="Battman", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _nem(hass) -> list[er.RegistryEntry]:
    return [e for e in er.async_get(hass).entities.values()
            if e.platform == DOMAIN and e.entity_id.startswith("sensor.battman_nem_")]


async def test_no_opennem_no_nem_sensors(hass: HomeAssistant) -> None:
    await _setup(hass)
    assert _nem(hass) == [] and hass.states.get("sensor.battman_nem_wind") is None


async def test_made_and_removed_with_opennem(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    opennem = MockConfigEntry(domain="opennem", title="OpenNEM")
    # OpenNEM installed (as HA adds a config entry; its own setup isn't part of this test): no restart needed
    from unittest.mock import patch
    with patch.object(hass.config_entries, "async_setup", return_value=True):
        await hass.config_entries.async_add(opennem)
    await hass.async_block_till_done()
    ids = sorted(e.entity_id for e in _nem(hass))
    assert ids == sorted(f"sensor.battman_nem_{k[4:]}" for k in ALL_KEYS)
    assert hass.states.get("sensor.battman_nem_wind").attributes["friendly_name"] == "Battman NEM wind"
    # not on the Battman device
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    assert device is not None and all(e.device_id is None for e in _nem(hass))
    assert [e for e in er.async_entries_for_device(er.async_get(hass), device.id) if "nem" in e.entity_id] == []
    # OpenNEM removed: so are they
    await hass.config_entries.async_remove(opennem.entry_id)
    await hass.async_block_till_done()
    assert _nem(hass) == [] and hass.states.get("sensor.battman_nem_wind") is None


async def test_moved_off_the_device_on_update(hass: HomeAssistant) -> None:
    """Before v0.26.0 they sat on the Battman device: the update moves them off, same entity."""
    MockConfigEntry(domain="opennem", title="OpenNEM").add_to_hass(hass)
    entry = MockConfigEntry(domain=DOMAIN, title="Battman", data={})
    entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(config_entry_id=entry.entry_id,
                                                      identifiers={(DOMAIN, entry.entry_id)}, name="Battman")
    er.async_get(hass).async_get_or_create("sensor", DOMAIN, f"{entry.entry_id}_nem_wind", config_entry=entry,
                                           device_id=device.id, suggested_object_id="battman_nem_wind")
    assert await async_setup_component(hass, "lovelace", {})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    e = er.async_get(hass).async_get("sensor.battman_nem_wind")
    assert e is not None and e.device_id is None


async def test_stale_ones_removed_without_opennem(hass: HomeAssistant) -> None:
    """OpenNEM uninstalled while HA was off: Battman's leftover NEM entities go at startup."""
    entry = MockConfigEntry(domain=DOMAIN, title="Battman", data={})
    entry.add_to_hass(hass)
    er.async_get(hass).async_get_or_create("sensor", DOMAIN, f"{entry.entry_id}_nem_wind", config_entry=entry,
                                           suggested_object_id="battman_nem_wind")
    assert await async_setup_component(hass, "lovelace", {})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert _nem(hass) == []


# ── the Live Activity settings move into the parameters sensor ───────────────────────────

from pathlib import Path

from homeassistant.core import State
from pytest_homeassistant_custom_component.common import mock_restore_cache

from custom_components.battman.const import IN_CHARGE

OLD = {  # the old entities: (domain, key) -> (entity_id, last state)
    ("switch", "live_activity"): ("switch.battman_live_activity", "on"),
    ("select", "live_activity_phone"): ("select.battman_live_activity_phone", "mobile_app_ajs_iphone"),
    ("text", "live_activity_follow"): ("text.battman_live_activity_follow", "binary_sensor.car_ignition"),
    ("text", "live_activity_follow_on"): ("text.battman_live_activity_follow_on", "on"),
    ("text", "live_activity_follow_off"): ("text.battman_live_activity_follow_off", "off"),
    ("number", "live_activity_follow_delay"): ("number.battman_live_activity_follow_delay", "3.0"),
    ("number", "live_activity_spike_alert"): ("number.battman_live_activity_spike_alert", "0.55"),
}


async def _updated_from_v025(hass, in_charge=True):
    """A v0.25.0 install with its Live Activity setting entities and their saved values, updated."""
    (Path(hass.config.config_dir) / "configuration.yaml").write_text("homeassistant:\n  packages: !include_dir_named packages\n")
    entry = MockConfigEntry(domain=DOMAIN, title="Battman", data={IN_CHARGE: in_charge})
    entry.add_to_hass(hass)
    reg = er.async_get(hass)
    for (domain, key), (entity_id, _v) in OLD.items():
        reg.async_get_or_create(domain, DOMAIN, f"{entry.entry_id}_{key}", config_entry=entry,
                                suggested_object_id=entity_id.split(".")[1])
    mock_restore_cache(hass, [State(e, v) for e, v in OLD.values()])
    assert await async_setup_component(hass, "lovelace", {})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_live_activity_settings_carried_over(hass: HomeAssistant) -> None:
    await _updated_from_v025(hass)
    a = hass.states.get("sensor.battman_parameters").attributes
    assert {k: a[k] for k in a if k.startswith("liveActivity")} == {
        "liveActivity": True, "liveActivityPhone": "mobile_app_ajs_iphone",
        "liveActivityFollow": "binary_sensor.car_ignition", "liveActivityFollowOn": "on", "liveActivityFollowOff": "off",
        "liveActivityFollowDelay": 3, "liveActivitySpikeAlert": 0.55}
    reg = er.async_get(hass)
    for entity_id, _v in OLD.values():
        e = reg.async_get(entity_id)
        if entity_id == "switch.battman_live_activity":
            assert e is not None and e.platform == "template"     # the same entity ID, now Battman's template switch
            assert hass.states.get(entity_id).state == "on"
        else:
            assert e is None and hass.states.get(entity_id) is None, entity_id


async def test_not_carried_over_when_not_in_charge(hass: HomeAssistant, caplog) -> None:
    await _updated_from_v025(hass, in_charge=False)
    assert hass.states.get("sensor.battman_parameters").attributes["liveActivityPhone"] == "Off"
    assert "couldn't be carried over" in caplog.text and "mobile_app_ajs_iphone" in caplog.text


async def test_battman_device_now(hass: HomeAssistant) -> None:
    """What's left on the Battman device: the in-charge sensor and the two buttons."""
    entry = await _setup(hass)
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    on = sorted(e.entity_id for e in er.async_entries_for_device(er.async_get(hass), device.id))
    assert on == ["binary_sensor.battman_in_charge", "button.battman_create_dashboard",
                  "button.battman_create_live_activity_automations"], on



# ── the theme mode colours: worked out by the browser, shown by a template sensor ────────────

import json
import subprocess

ROOT = Path(__file__).parents[1] / "custom_components/battman"
LIB = ROOT / "www/battman-lib.js"


def _node(script: str):
    page = ("globalThis.window = globalThis; globalThis.document = { querySelector: () => null };\n"
            "globalThis.setTimeout = () => 0; globalThis.setInterval = () => 0;\n")
    r = subprocess.run(["node", "-"], input=page + LIB.read_text() + "\n" + script, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def lib_colours(themes: dict, name: str) -> dict:
    """What an open Battman page saves for a theme (battman-lib.js themeModeColours)."""
    return _node(f"process.stdout.write(JSON.stringify(window.BattmanLib.themeModeColours({json.dumps(themes)}, {json.dumps(name)})));")


def test_theme_hex() -> None:
    t = {"a": "#ABC", "b": "#11223344", "c": "rgba(255, 0, 16, 0.5)", "d": "var(--a)", "e": "red", "f": "var(--f)"}
    out = _node(f"""const t = {json.dumps(t)}, r = {{}};
for (const k of ['a', 'b', 'c', 'd', 'e', 'f', 'zz']) {{ try {{ r[k] = window.BattmanLib.themeHex(t, k); }} catch (e) {{ r[k] = 'ERR ' + e.message; }} }}
process.stdout.write(JSON.stringify(r));""")
    assert (out["a"], out["b"], out["c"], out["d"]) == ("#AABBCC", "#112233", "#ff0010", "#AABBCC")
    assert out["e"] == "ERR e is 'red', not a colour Battman can read"
    assert out["f"] == "ERR f: var() chain too deep" and out["zz"] == "ERR zz not in theme"


async def test_template_sensor_and_keeper(hass: HomeAssistant) -> None:
    """The browser keeps the saved colours in step with the picked theme while Battman is in charge."""
    keeper = (LIB.read_text().split("(function keepThemeColours() {")[1])
    assert "inCharge.state !== 'on'" in keeper and "!hass.user.is_admin" in keeper
    assert "setInterval(check, 15000)" in keeper and "setTimeout(check, 3000)" in keeper
    sensors = (ROOT / "packages/battman_sensors.yaml").read_text()
    assert "unique_id: battman_theme_mode_colours" in sensors and "dashboardThemeColours" in sensors
    assert not (ROOT / "sensor.py").read_text().count("to_hex")


async def test_old_python_sensor_handed_over(hass: HomeAssistant) -> None:
    """Before v0.26.0 the colours sensor was Battman's own: the template one keeps its entity ID."""
    (Path(hass.config.config_dir) / "configuration.yaml").write_text("homeassistant:\n  packages: !include_dir_named packages\n")
    entry = MockConfigEntry(domain=DOMAIN, title="Battman", data={})
    entry.add_to_hass(hass)
    er.async_get(hass).async_get_or_create("sensor", DOMAIN, f"{entry.entry_id}_theme_mode_colours", config_entry=entry,
                                           suggested_object_id="battman_theme_mode_colours")
    assert await async_setup_component(hass, "lovelace", {})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    e = er.async_get(hass).async_get("sensor.battman_theme_mode_colours")
    assert e is not None and e.platform == "template"


def _keeper(in_charge: bool, saved, admin: bool = True) -> list:
    """Run battman-lib.js's keeper once on a fake page; returns the events it fired."""
    nord = {"battman-" + k: "#" + "%06x" % (i + 1) for i, k in
            enumerate(["green", "yellow", "blue", "orange", "red", "purple", "teal", "amber"])}
    page = f"""
const fired = [], timers = [];
globalThis.window = globalThis; globalThis.setTimeout = (f) => timers.push(f); globalThis.setInterval = () => 0;
const hass = {{
  user: {{ is_admin: {json.dumps(admin)} }},
  themes: {{ themes: {{ 'Battman Nord': {json.dumps(nord)} }} }},
  states: {{ 'binary_sensor.battman_in_charge': {{ state: {json.dumps('on' if in_charge else 'off')} }},
            'sensor.battman_parameters': {{ attributes: {{ dashboardTheme: 'Battman Nord', dashboardThemeColours: {json.dumps(saved)} }} }} }},
  callApi: () => Promise.resolve({{ entities: {{ parameters: 'sensor.battman_parameters', parameters_update_event: 'battman_parameters_update' }} }}),
  callWS: (m) => {{ fired.push(m); return Promise.resolve(); }},
}};
globalThis.document = {{ querySelector: (s) => (s === 'home-assistant' ? {{ hass }} : null) }};
"""
    script = page + LIB.read_text() + "\ntimers.forEach((f) => f());\nsetImmediate(() => process.stdout.write(JSON.stringify(fired)));"
    r = subprocess.run(["node", "-"], input=script, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_keeper_saves_only_what_changed() -> None:
    fired = _keeper(True, None)                       # nothing saved yet: saves the colours of the picked theme
    assert len(fired) == 1 and fired[0]["event_type"] == "battman_parameters_update"
    want = fired[0]["event_data"]["dashboardThemeColours"]
    assert want["theme"] == "Battman Nord" and want["green"] == "#000001" and want["amber"] == "#000008"
    assert _keeper(True, want) == []                  # already in step: nothing sent
    assert len(_keeper(True, {**want, "green": "#ffffff"})) == 1   # the theme changed (e.g. a Battman update)
    assert _keeper(False, None) == []                 # not in charge: settings don't change then
    assert _keeper(True, None, admin=False) == []     # a user who can't fire events



def test_packages_follow_no_map() -> None:
    """Migrate changes the entity map: a package that used it would be rewritten and reloaded in
    the middle of the migration (losing the values it copies). None does."""
    import re as _re
    for f in (ROOT / "packages").glob("*.yaml"):
        code = "\n".join(l for l in f.read_text().splitlines() if not l.lstrip().startswith("#"))
        assert not _re.search(r"\[\[map:", code), f.name
