"""v0.22.3: the engine side uses Sigen's entities by name.

- The engine script, its automations, the Live Activity and the packages name Sigen's entities
  directly (no [[map:...]] for them). What Battman writes into HA is unchanged with the default names.
- Every Sigen (and Solcast) entity they name is checked at startup: a Repair names any missing.
- A Sigen integration older than 1.1.0 (the first with every name Battman uses) gets a Repair.
- A Configure choice for one of these entries no longer applies: a Repair names it.
"""

import re
from pathlib import Path
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.battman import required_entities as R
from custom_components.battman.const import ENTITY_MAP_DEFAULTS

ROOT = Path(__file__).parents[1] / "custom_components/battman"
DOMAIN = "battman"
ENGINE_SIDE = [*ROOT.glob("blueprints/*/*.yaml"), *ROOT.glob("packages/*.yaml")]


async def _setup(hass, options=None):
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain=DOMAIN, title="Battman", data={}, options=options or {})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def test_engine_side_names_sigen_directly() -> None:
    sigen_keys = [k for k, v in R.NAMED.items() if "sigen" in v]
    for f in ENGINE_SIDE:
        text = f.read_text()
        for k in sigen_keys:
            assert f"[[map:{k}]]" not in text, (f.name, k)
    engine = (ROOT / "blueprints/script/battman_engine.yaml").read_text()
    assert "states(''sensor.sigen_plant_battery_state_of_charge'')" in engine
    assert "states(''sensor.sigen_plant_rated_energy_capacity'')" in engine
    assert "select.sigen_plant_remote_ems_control_mode" in (ROOT / "blueprints/automation/battman_engine_sig_mode.yaml").read_text()
    assert "sensor.sigen_plant_total_imported_energy" in (ROOT / "packages/battman_cost.yaml").read_text()


def test_every_named_entity_is_checked() -> None:
    """Each Sigen / Solcast entity the engine side names is on the startup check's list,
    and each map entry Battman now uses by name points at what the files use."""
    named = set()
    for f in ENGINE_SIDE:
        named |= set(re.findall(r"(?:sensor|select|number)\.(?:sigen|solcast)_[a-z0-9_]+", f.read_text()))
    assert named and named <= set(R.REQUIRED), named - set(R.REQUIRED)
    optional = {"sigen_pv_power", "third_party_pv", "pv_string"}   # overlays / optional hardware (v0.23.0)
    own = {"grid_power", "load_30m_avg"}                            # Battman's own sensors (v0.23.1)
    for k, entity in R.NAMED.items():
        if k in own:
            assert entity.startswith("sensor.battman_"), k
            continue
        assert entity in R.REQUIRED or k in optional, k
        assert k not in ENTITY_MAP_DEFAULTS, k            # v0.23.0: off the map


async def test_missing_sigen_entities_named(hass: HomeAssistant) -> None:
    await _setup(hass)
    text = ir.async_get(hass).async_get_issue(DOMAIN, "missing_entities").translation_placeholders["missing"]
    assert ("- `sensor.sigen_plant_total_imported_energy` (grid energy bought, for the cost totals, "
            "from Sigenergy (Sigenergy-Local-Modbus)): not found") in text
    for e in R.REQUIRED:
        hass.states.async_set(e, "1")
    from homeassistant.helpers import entity_registry as er
    er.async_get(hass).async_get_or_create("sensor", "test", "nudge")      # a registry change: check again
    await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(DOMAIN, "missing_entities") is None


class _Integration:
    def __init__(self, version):
        self.version = version


async def _versions(hass, version):
    with patch.object(R, "async_get_integration", return_value=_Integration(version)):
        return await R.async_check_versions(hass)


async def test_sigen_version_check(hass: HomeAssistant) -> None:
    await _setup(hass)
    # Sigen not installed: no version Repair (the missing-entities Repair covers it)
    assert await _versions(hass, "1.0.4") == {}
    assert ir.async_get(hass).async_get_issue(DOMAIN, "integration_too_old") is None
    MockConfigEntry(domain="sigen", title="Sigen").add_to_hass(hass)
    assert await _versions(hass, "1.0.4") == {R.SIGEN: ("1.0.4", "1.1.0")}
    issue = ir.async_get(hass).async_get_issue(DOMAIN, "integration_too_old")
    assert issue.translation_placeholders["old"] == (
        "- **Sigenergy (Sigenergy-Local-Modbus)**: version 1.0.4 installed, Battman needs 1.1.0 or newer")
    for ok in ("1.1.0", "1.3.0", "1.3.0b9"):
        assert await _versions(hass, ok) == {}, ok
        assert ir.async_get(hass).async_get_issue(DOMAIN, "integration_too_old") is None
    assert await _versions(hass, None) == {R.SIGEN: ("unknown", "1.1.0")}


async def test_configure_choices_no_longer_used(hass: HomeAssistant) -> None:
    # a Solcast choice from before v0.22.2 and a Sigen one; one that's the entity Battman uses is fine
    entry = await _setup(hass, options={"solcast_today": "sensor.my_solar", "battery_soc": "sensor.my_soc",
                                        "buy_price": "sensor.amber_5min_current_general_price"})
    issue = ir.async_get(hass).async_get_issue(DOMAIN, "map_choice_ignored")
    assert issue.translation_placeholders["choices"] == (
        "- solcast_today: you picked `sensor.my_solar`; Battman now uses `sensor.solcast_pv_forecast_forecast_today`\n"
        "- battery_soc: you picked `sensor.my_soc`; Battman now uses `sensor.sigen_plant_battery_state_of_charge`")
    hass.config_entries.async_update_entry(entry, options={"buy_price": "sensor.amber_5min_current_general_price"})
    await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(DOMAIN, "map_choice_ignored") is None


async def test_no_choice_repair_on_defaults(hass: HomeAssistant) -> None:
    await _setup(hass)
    assert ir.async_get(hass).async_get_issue(DOMAIN, "map_choice_ignored") is None


async def test_cost_totals_follow_sigen_meters(hass: HomeAssistant) -> None:
    """The money path with Sigen named directly: Battman's buy / sell totals grow by what Sigen's
    import / export meters moved, at the price of that interval."""
    from . import engine_harness as H
    from .test_finances_cards import _start_totals

    await _start_totals(hass)
    imp, exp = "sensor.sigen_plant_total_imported_energy", "sensor.sigen_plant_total_exported_energy"
    st = hass.states.get
    b0, s0 = float(st("sensor.battman_buy_total").state), float(st("sensor.battman_sell_total").state)
    assert st("sensor.battman_buy_total").attributes["last_energy"] == float(st(imp).state)
    assert st("sensor.battman_sell_total").attributes["last_energy"] == float(st(exp).state)
    buy = float(st("sensor.amber_5min_current_general_price").state)
    sell = float(st("sensor.amber_5min_current_feed_in_price").state)
    meters = {imp: str(float(st(imp).state) + 1.5), exp: str(float(st(exp).state) + 0.25)}
    H.set_world(hass, {"estimate": False, **meters})
    await hass.async_block_till_done()
    H.set_world(hass, {"estimate": True, **meters})          # next price interval: the totals add up
    await hass.async_block_till_done()
    await H.tick(hass, 1)                                    # HA writes trigger-template results a moment later
    b1, s1 = float(st("sensor.battman_buy_total").state), float(st("sensor.battman_sell_total").state)
    assert round(b1 - b0, 4) == round(1.5 * 1000 * buy, 4), (b0, b1, buy)
    assert round(s1 - s0, 4) == round(0.25 * 1000 * sell, 4), (s0, s1, sell)
    assert b1 != b0 and s1 != s0
    assert st("sensor.battman_buy_total").attributes["last_energy"] == float(st(imp).state)
