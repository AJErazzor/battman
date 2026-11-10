"""Sigenergy-Local-Modbus 2.0 renamed a few entities, and a fresh 2.x install builds its entity IDs from
the names (an upgraded install keeps the old ones). Battman finds those four in the entity registry by the
integration's register key (the unique ID doesn't change), so the same files work on 1.x and 2.x:

- the engine blueprints, the Limits card and the Overrides card get the ID this HA has
- nothing found gives the 1.x ID, and the missing-entities Repair names it
- a Sigen set up after Battman rewrites the blueprints
"""

import re
from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.battman import api, blueprint_install, cards
from custom_components.battman import required_entities as R
from custom_components.battman import sigen_entities
from custom_components.battman.const import SIGEN_MAP

DOMAIN = "battman"

# register key -> (domain, the ID a 1.x install has, the ID a fresh 2.x install has)
IDS = {
    "plant_pv_max_power_limit": ("number", "number.sigen_plant_pv_max_power_limit", "number.sigen_plant_pv_maximum_power_limit"),
    "plant_ess_max_charging_limit": ("number", "number.sigen_plant_ess_max_charging_limit", "number.sigen_plant_ess_maximum_charging_power_limit"),
    "plant_grid_point_maximum_export_limitation": ("number", "number.sigen_plant_grid_export_limitation", "number.sigen_plant_grid_export_power_limit"),
    "plant_available_max_active_power": ("sensor", "sensor.sigen_plant_available_max_active_power", "sensor.sigen_plant_available_maximum_active_power"),
}
MAP_NAMES = {key: name for name, (_d, key, _i) in SIGEN_MAP.items()}


def _add_sigen(hass: HomeAssistant, version: int) -> None:
    """The four entities as a 1.x or 2.x install of Sigenergy-Local-Modbus registers them."""
    reg = er.async_get(hass)
    for key, (domain, old, new) in IDS.items():
        reg.async_get_or_create(domain, "sigen", f"01ABC_sigen_plant_{key}",
                                suggested_object_id=(old if version == 1 else new).split(".", 1)[1])


def test_the_four_are_the_whole_map() -> None:
    assert set(MAP_NAMES) == set(IDS)
    assert {v[2] for v in SIGEN_MAP.values()} == {v[1] for v in IDS.values()}        # the defaults are the 1.x IDs


def test_nothing_found_gives_the_1x_ids(hass: HomeAssistant) -> None:
    assert sigen_entities.resolve(hass) == {MAP_NAMES[k]: v[1] for k, v in IDS.items()}


@pytest.mark.parametrize("version", [1, 2])
def test_each_version_gives_its_own_ids(hass: HomeAssistant, version: int) -> None:
    _add_sigen(hass, version)
    assert sigen_entities.resolve(hass) == {MAP_NAMES[k]: v[version] for k, v in IDS.items()}
    assert {n: api.entity_map(hass)[n] for n in SIGEN_MAP} == sigen_entities.resolve(hass)


def test_another_integration_with_the_same_key_is_ignored(hass: HomeAssistant) -> None:
    er.async_get(hass).async_get_or_create("number", "other", "01ABC_sigen_plant_plant_pv_max_power_limit",
                                           suggested_object_id="not_sigen")
    assert sigen_entities.resolve(hass)["sigen_pv_max_power_limit"] == IDS["plant_pv_max_power_limit"][1]


@pytest.mark.parametrize("version", [1, 2])
def test_blueprints_get_the_ids(hass: HomeAssistant, tmp_path: Path, version: int) -> None:
    _add_sigen(hass, version)
    blueprint_install.install({"automation": tmp_path}, api.entity_map(hass))
    text = "".join(f.read_text() for f in tmp_path.glob("*.yaml"))
    assert not re.search(r"\[\[map:[a-z]", text)             # the header comment's "[[map:...]]" isn't a marker
    for _key, (_d, old, new) in IDS.items():
        if "available" in old:
            continue                                  # not used by a blueprint
        assert (new if version == 2 else old) in text
        assert (old if version == 2 else new) not in text


@pytest.mark.parametrize("version", [1, 2])
def test_limits_card_gets_the_ids(hass: HomeAssistant, version: int) -> None:
    _add_sigen(hass, version)
    card = cards.get_card(Path("/nonexistent"), "limits", api.entity_map(hass))
    text = str(card)
    assert "[[map:" not in text
    for key in ("plant_pv_max_power_limit", "plant_ess_max_charging_limit", "plant_grid_point_maximum_export_limitation"):
        assert IDS[key][version] in text and IDS[key][3 - version] not in text


@pytest.mark.parametrize("version", [1, 2])
def test_repair_names_the_id_this_ha_has(hass: HomeAssistant, version: int) -> None:
    _add_sigen(hass, version)
    reg = er.async_get(hass)
    reg.async_update_entity(IDS["plant_pv_max_power_limit"][version], disabled_by=er.RegistryEntryDisabler.USER)
    gone = R.missing(hass)
    assert gone[IDS["plant_pv_max_power_limit"][version]] == "disabled"
    assert IDS["plant_pv_max_power_limit"][3 - version] not in gone
    assert IDS["plant_ess_max_charging_limit"][version] not in gone             # present: not named


def test_repair_names_the_1x_id_when_there_is_none(hass: HomeAssistant) -> None:
    gone = R.missing(hass)
    for _key, (_d, old, new) in IDS.items():
        assert gone[old] == "not found" and new not in gone


async def test_sigen_set_up_after_battman_rewrites_the_blueprints(hass: HomeAssistant) -> None:
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain=DOMAIN, title="Battman", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    path = blueprint_install.dst_dir(hass, "automation") / "battman_engine_sig_mode.yaml"
    assert "number.sigen_plant_pv_max_power_limit" in path.read_text()                   # no Sigen yet: the 1.x IDs
    _add_sigen(hass, 2)
    await hass.async_block_till_done()
    text = path.read_text()
    assert "number.sigen_plant_pv_maximum_power_limit" in text
    assert "number.sigen_plant_pv_max_power_limit" not in text
    assert not any(i.issue_id == R.ISSUE_MISSING and "pv_maximum_power_limit" in str(i.translation_placeholders)
                   for i in ir.async_get(hass).issues.values())
