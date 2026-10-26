"""v0.19.0 (review round A/B):

- A2: a fresh install starts with every setting's default and the factory curves; yours are kept
  on start and template reloads; Curvy and Pricy read the factory curves from the sensors.
- A3: a Repair when Battman's themes aren't loaded.
- A4: the 30-minute load average is a Battman Statistics sensor; the engine says when it's missing
  instead of reading it as 0.
- A6: removing Battman takes away what it wrote (the engine log stays).
- B1/B2: the old managed-dashboard strategy is gone; the dashboard Repair points at Create dashboard.
- B4: the house card's defaults come from the entity map (no one's own devices or weather).
- B6: no strings.json, iot_class calculated, estimated price unavailable (not an error) without times.
"""

import json
import logging
import random
import re
from pathlib import Path

import yaml
from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from . import engine_harness as H

ROOT = Path(__file__).parents[1] / "custom_components/battman"
DOMAIN = "battman"
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
FACTORY = yaml.safe_load((ROOT / "factory_curves.yaml").read_text())


def _in_charge(hass, entry) -> None:
    from custom_components.battman.const import IN_CHARGE

    hass.config_entries.async_update_entry(entry, data={**entry.data, IN_CHARGE: True})


# ── A2 ───────────────────────────────────────────────────────────────────────────────────


async def test_fresh_install_has_every_setting_and_the_factory_curves(hass: HomeAssistant) -> None:
    await H.start(hass, smiggles=False)
    assert hass.states.get("binary_sensor.battman_in_charge").state == "off"
    params = hass.states.get("sensor.battman_parameters").attributes
    engine = (ROOT / "blueprints/script/battman_engine.yaml").read_text()
    read = set(re.findall(r"battman_parameters'{1,2},\s*'{1,2}(\w+)'{1,2}\)", engine))
    assert read and not read - set(params), read - set(params)
    assert params["needyTriggerPVGap"] == 3 and params["needyTriggerConsumption"] == 3.5
    soc = hass.states.get("sensor.battman_soc_curves").attributes
    price = hass.states.get("sensor.battman_price_curves").attributes
    assert soc["factory"] == FACTORY["soc"] and price["factory"] == FACTORY["price"]
    assert soc["curves"] == {m: FACTORY["soc"] for m in MONTHS}
    assert price["curves"] == {m: FACTORY["price"] for m in MONTHS}


async def test_your_settings_and_curves_are_kept(hass: HomeAssistant) -> None:
    entry, _rec = await H.start(hass, smiggles=False)
    _in_charge(hass, entry)
    soc, price = H.curves(random.Random(7))
    hass.bus.async_fire("battman_soc_curves_update", {"curves": soc})
    hass.bus.async_fire("battman_price_curves_update", {"curves": price})
    hass.bus.async_fire("battman_parameters_update", {"action": "SetAttribute", "needyTriggerPVGap": 7})
    await hass.async_block_till_done()
    await hass.services.async_call("template", "reload", blocking=True)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.battman_soc_curves").attributes["curves"] == soc
    assert hass.states.get("sensor.battman_price_curves").attributes["curves"] == price
    assert hass.states.get("sensor.battman_parameters").attributes["needyTriggerPVGap"] == 7
    # not in charge: changes are still ignored, the start fill-in isn't a way round that
    from custom_components.battman.const import IN_CHARGE

    hass.config_entries.async_update_entry(entry, data={**entry.data, IN_CHARGE: False})
    hass.bus.async_fire("battman_parameters_update", {"action": "SetAttribute", "needyTriggerPVGap": 9})
    await hass.async_block_till_done()
    assert hass.states.get("sensor.battman_parameters").attributes["needyTriggerPVGap"] == 7


def test_factory_curves_live_in_one_place() -> None:
    for page, attr in (("battman-curvy.js", "soc_curves_factory"), ("battman-pricy.js", "price_curves_factory")):
        text = (ROOT / "www" / page).read_text()
        assert f"M.{attr}" in text and "attributes.factory" in text, page
        assert "No factory curves" in text, page                        # says so, no hidden copy
    curvy = (ROOT / "www/battman-curvy.js").read_text()
    assert "[25,25,20,20,15,15" not in curvy and "sell: [...FACTORY.sell]" in curvy
    assert "makeDefault" not in (ROOT / "www/battman-pricy.js").read_text()
    for soc_type in ("sell", "sell_high", "buy", "buy_high"):
        assert len(FACTORY["soc"][soc_type]) == 24
        assert len(FACTORY["price"][soc_type]["low"]) == len(FACTORY["price"][soc_type]["high"]) == 24


def test_engine_reads_settings_without_fallbacks() -> None:
    engine = (ROOT / "blueprints/script/battman_engine.yaml").read_text()
    assert not re.findall(r"battman_parameters'{1,2},\s*'{1,2}\w+'{1,2}\)\s*\|\s*float\(", engine)


# ── A4 ───────────────────────────────────────────────────────────────────────────────────


async def _run_engine(hass, entry) -> str:
    _in_charge(hass, entry)
    soc, price = H.curves(random.Random(3))
    hass.bus.async_fire("battman_soc_curves_update", {"curves": soc})
    hass.bus.async_fire("battman_price_curves_update", {"curves": price})
    await hass.async_block_till_done()
    await hass.services.async_call("script", "turn_on", {"entity_id": "script.battman_engine"}, blocking=True)
    await H.tick(hass, 3)
    await H.tick(hass, 1)
    return hass.states.get("sensor.battman_engine_log").attributes["message"]


async def test_engine_says_when_the_load_average_is_missing(hass: HomeAssistant) -> None:
    entry, _rec = await H.start(hass, smiggles=False)
    hass.states.async_set(H.LOAD_AVG, "unavailable")
    msg = await _run_engine(hass, entry)
    assert "Load average: missing (sensor.battman_load_30m_avg has no value), high consumption check skipped" in msg
    assert "(On High Curve!)" not in msg


async def test_engine_uses_the_load_average_when_there(hass: HomeAssistant) -> None:
    entry, _rec = await H.start(hass, smiggles=False)
    hass.states.async_set(H.LOAD_AVG, "9.5")                    # over the 3.5 kW default
    msg = await _run_engine(hass, entry)
    assert "Load average: missing" not in msg and "(On High Curve!)" in msg


def test_load_30m_map_entry_gone() -> None:
    from custom_components.battman.const import ENTITY_MAP_DEFAULTS

    assert "load_30m" not in ENTITY_MAP_DEFAULTS
    for f in [*ROOT.rglob("*.yaml"), *ROOT.rglob("*.js"), *ROOT.rglob("*.html"), ROOT / "translations/en.json"]:
        assert not re.search(r"load_30m\b(?!_avg)|solarsystemcontrolload30m\b", f.read_text()), f


# ── A6 ───────────────────────────────────────────────────────────────────────────────────


async def test_removing_battman_takes_away_what_it_wrote(hass: HomeAssistant) -> None:
    from custom_components.battman import engine_log

    entry, _rec = await H.start(hass, smiggles=False)
    cfg = Path(hass.config.config_dir)
    autos = yaml.safe_load((cfg / "automations.yaml").read_text())
    assert any(a["id"] == "battman_engine_loop" for a in autos)
    mine = {"id": "my_lights", "alias": "My lights", "triggers": [], "actions": []}
    (cfg / "automations.yaml").write_text(yaml.safe_dump([*autos, mine], sort_keys=False))
    scripts = yaml.safe_load((cfg / "scripts.yaml").read_text())
    (cfg / "scripts.yaml").write_text(yaml.safe_dump({**scripts, "my_script": {"sequence": []}}, sort_keys=False))
    engine_log.append(engine_log.battman_path(hass), "2026-10-22T10:00:00|kept\n")
    assert (cfg / "packages/battman").is_dir()

    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    assert yaml.safe_load((cfg / "automations.yaml").read_text()) == [mine]
    assert yaml.safe_load((cfg / "scripts.yaml").read_text()) == {"my_script": {"sequence": []}}
    assert not (cfg / "packages/battman").exists()
    assert not (cfg / "blueprints/automation/battman").exists()
    assert engine_log.battman_path(hass).read_text() == "2026-10-22T10:00:00|kept\n"
    reg = er.async_get(hass)
    assert reg.async_get_entity_id("sensor", "template", "battman_parameters") is None
    assert reg.async_get_entity_id("sensor", "statistics", "battman_load_30m_avg") is None
    assert reg.async_get_entity_id("automation", "automation", "battman_engine_loop") is None
    assert hass.states.get("sensor.battman_parameters") is None
    assert hass.states.get("input_boolean.battman_enable") is None
    note = persistent_notification._async_get_or_create_notifications(hass)["battman_removed"]
    assert "battman_engine_loop" in note["message"] and "Kept: the engine log" in note["message"]
    assert "Couldn't remove" not in note["message"]


# ── A3 ───────────────────────────────────────────────────────────────────────────────────


async def _setup_with(hass, config: str) -> None:
    (Path(hass.config.config_dir) / "configuration.yaml").write_text(config)
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain=DOMAIN, title="Battman", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_repair_when_themes_arent_loaded(hass: HomeAssistant) -> None:
    await _setup_with(hass, "")
    issue = ir.async_get(hass).async_get_issue(DOMAIN, "themes_not_loaded")
    assert issue is not None and issue.translation_placeholders["folder"] == "themes/battman"
    text = json.loads((ROOT / "translations/en.json").read_text())["issues"]["themes_not_loaded"]["description"]
    assert "themes: !include_dir_merge_named themes" in text


async def test_no_repair_when_themes_are_loaded(hass: HomeAssistant) -> None:
    await _setup_with(hass, "frontend:\n  themes: !include_dir_merge_named themes\n")
    assert ir.async_get(hass).async_get_issue(DOMAIN, "themes_not_loaded") is None


def test_themes_line_in_dependencies() -> None:
    deps = (ROOT.parents[1] / "DEPENDENCIES.md").read_text()
    assert "frontend: themes: !include_dir_merge_named themes" in deps


# ── B1 / B2 ──────────────────────────────────────────────────────────────────────────────


def test_old_dashboard_strategy_gone() -> None:
    assert not (ROOT / "www/battman-strategy.js").exists()
    for f in [*ROOT.glob("*.py"), ROOT / "www/battman-settings.js", ROOT / "www/battman-theme-studio.js"]:
        assert "strategy" not in f.read_text(), f
    text = json.loads((ROOT / "translations/en.json").read_text())["issues"]["dashboard_unavailable"]["description"]
    assert "Create dashboard" in text and "battman.create_dashboard" in text and "strategy" not in text


# ── B4 ───────────────────────────────────────────────────────────────────────────────────


def test_house_card_defaults_are_battmans() -> None:
    from custom_components.battman.const import ENTITY_MAP_DEFAULTS

    js = (ROOT / "www/battman-house.js").read_text()
    items = js[js.index("const HOUSE_ITEMS"):js.index("const HOUSE_BY_KEY")]
    # every default entity is an entity map entry, one of Sigen's entities (as the other cards name
    # them, battman-card-base.js SIGEN, v0.23.0), a PV string of Sigen's pattern, or nothing
    base = (ROOT / "www/battman-card-base.js").read_text()
    sigen = dict(re.findall(r'^  (\w+): "([^"]+)",$', base[base.index("export const SIGEN"):], re.M))
    defaults = re.findall(r'(\w+): "([^"]*)"', items[items.index("ent:"):])
    for field, value in defaults:
        if field in ("key", "title", "label", "suffix", "image"):
            continue
        assert value == "" or value.startswith("map:") or value in sigen.values() \
            or re.fullmatch(sigen["pv_string"].replace("{n}", r"\d"), value), (field, value)
    assert set(re.findall(r'"map:(\w+)"', items)) <= set(ENTITY_MAP_DEFAULTS)
    assert re.findall(r'"sensor.sigen_inverter_pv(\d)_power"', items) == ["2", "1", "3"]
    assert not re.search(r"(?i)athelstone|malachy|noah|hamish|\b(East|North|West)\b", js)
    assert '"pv:' not in js and "battery_temperature" not in js


# ── B6 ───────────────────────────────────────────────────────────────────────────────────


def test_tidy_ups() -> None:
    assert not (ROOT / "strings.json").exists()
    assert json.loads((ROOT / "manifest.json").read_text())["iot_class"] == "calculated"
    for name in ("button.py", "sensor.py", "switch.py"):
        text = (ROOT / name).read_text()
        assert "DeviceInfo(" not in text and "device_info(entry)" in text, name


async def test_estimated_price_unavailable_without_times(hass: HomeAssistant, caplog) -> None:
    await H.start(hass, smiggles=False)
    fip = "sensor.amber_5min_current_feed_in_price"
    assert hass.states.get("binary_sensor.battman_estimated_price").state in ("on", "off")
    caplog.clear()
    with caplog.at_level(logging.ERROR):
        hass.states.async_set(fip, "0.05", {"estimate": False})
        await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.battman_estimated_price").state == "unavailable"
    assert not [r for r in caplog.records if r.levelname == "ERROR" and "estimated" in r.getMessage().lower()]
