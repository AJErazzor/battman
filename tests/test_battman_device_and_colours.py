"""v0.26.0: a tidier Battman device.

- The NEM sensors only exist while the OpenNEM integration is installed (made when it's added,
  removed when it's removed), and aren't on the Battman device: they're OpenNEM's figures, not
  Battman's settings or controls. Their entity IDs stay sensor.battman_nem_*.
"""

from pathlib import Path

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


async def test_battman_device_now(hass: HomeAssistant) -> None:
    """What's on the Battman device: the two buttons (the old in-charge sensor is gone)."""
    entry = await _setup(hass)
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    on = sorted(e.entity_id for e in er.async_entries_for_device(er.async_get(hass), device.id))
    assert on == ["button.battman_create_automations", "button.battman_create_dashboard"], on



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
    """The browser keeps the saved colours in step with the picked theme (and needs no in-charge flag)."""
    keeper = (LIB.read_text().split("(function keepThemeColours() {")[1])
    assert "in_charge" not in keeper and "!hass.user.is_admin" in keeper
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


def _keeper(saved, admin: bool = True) -> list:
    """Run battman-lib.js's keeper once on a fake page; returns the events it fired."""
    nord = {"battman-" + k: "#" + "%06x" % ((i + 1) * 0x151515) for i, k in
            enumerate(["red", "darkred", "orange", "amber", "yellow", "green", "teal", "sky",
                       "blue", "purple", "darkpurple", "pink"])}
    page = f"""
const fired = [], timers = [];
globalThis.window = globalThis; globalThis.setTimeout = (f) => timers.push(f); globalThis.setInterval = () => 0;
const hass = {{
  user: {{ is_admin: {json.dumps(admin)} }},
  themes: {{ themes: {{ 'Battman Nord': {json.dumps(nord)} }} }},
  states: {{ 'sensor.battman_parameters': {{ attributes: {{ dashboardTheme: 'Battman Nord', dashboardThemeColours: {json.dumps(saved)} }} }} }},
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
    fired = _keeper(None)                             # nothing saved yet: saves the colours of the picked theme
    assert len(fired) == 1 and fired[0]["event_type"] == "battman_parameters_update"
    want = fired[0]["event_data"]["dashboardThemeColours"]
    assert want["theme"] == "Battman Nord" and want["modes"]["Discharge"] == "#7e7e7e"   # green, the 6th
    assert _keeper(want) == []                        # already in step: nothing sent
    changed = {**want, "modes": {**want["modes"], "Discharge": "#ffffff"}}
    assert len(_keeper(changed)) == 1                 # the theme changed (e.g. a Battman update)
    assert _keeper(None, admin=False) == []           # a user who can't fire events



def test_packages_follow_no_map() -> None:
    """Migrate changes the entity map: a package that used it would be rewritten and reloaded in
    the middle of the migration (losing the values it copies). None does."""
    import re as _re
    for f in (ROOT / "packages").glob("*.yaml"):
        code = "\n".join(l for l in f.read_text().splitlines() if not l.lstrip().startswith("#"))
        assert not _re.search(r"\[\[map:", code), f.name
