"""v0.22.2: Solcast is named directly (no entity map), with a Repair if one of its sensors is missing.

- The engine, the State and Gauges cards and Curvy use Solcast's sensors by their names.
- The Solcast entries are gone from the entity map and the Configure screen.
- The engine's three Solcast values nothing used (remaining today's middle estimate, next hour's
  two figures) are gone; Battman doesn't read Solcast's next-hour sensor any more.
- Battman checks the Solcast sensors it uses are there and enabled; a Repair names any that isn't.
"""

import re
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

ROOT = Path(__file__).parents[1] / "custom_components/battman"
DOMAIN = "battman"
TODAY = "sensor.solcast_pv_forecast_forecast_today"
TOMORROW = "sensor.solcast_pv_forecast_forecast_tomorrow"
REMAIN = "sensor.solcast_pv_forecast_forecast_remaining_today"


async def _setup(hass):
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain=DOMAIN, title="Battman", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _solcast(hass, entity_id: str, disabled: bool = False) -> None:
    """One of the Solcast integration's sensors (registered as Solcast's, as the real ones are)."""
    er.async_get(hass).async_get_or_create(
        "sensor", "solcast_solar", entity_id.split(".")[1], suggested_object_id=entity_id.split(".")[1],
        disabled_by=er.RegistryEntryDisabler.USER if disabled else None)


def _solcast_lines(issue) -> str:
    """The Solcast lines of the missing-entities Repair (other integrations' lines aside)."""
    if issue is None:
        return ""
    return "\n".join(l for l in issue.translation_placeholders["missing"].split("\n") if "solcast" in l)


def test_solcast_named_directly() -> None:
    from custom_components.battman.const import ENTITY_MAP_DEFAULTS

    assert not [k for k in ENTITY_MAP_DEFAULTS if "solcast" in k]
    for f in ("blueprints/script/battman_engine.yaml", "cards/state.yaml", "cards/gauges.yaml", "www/battman-curvy.js",
              "translations/en.json"):
        assert not re.search(r"\[\[map:solcast|M\.solcast|['\"]solcast_(today|tomorrow|remaining|next)", (ROOT / f).read_text()), f
    engine = (ROOT / "blueprints/script/battman_engine.yaml").read_text()
    assert f"state_attr(''{REMAIN}'',''estimate10'')" in engine
    for gone in ("pvRemainingkwh", "pvNext1hr", "forecast_next_hour"):
        assert gone not in engine, gone
    assert TODAY in (ROOT / "cards/state.yaml").read_text() and TOMORROW in (ROOT / "cards/state.yaml").read_text()
    assert REMAIN in (ROOT / "cards/gauges.yaml").read_text()
    assert f"const SOLCAST_TODAY = '{TODAY}';" in (ROOT / "www/battman-curvy.js").read_text()


async def test_configure_has_no_solcast_fields(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    assert not [k for k in flow["data_schema"].schema if "solcast" in str(k)]


async def test_repair_names_missing_solcast_sensors(hass: HomeAssistant) -> None:
    await _setup(hass)
    issue = ir.async_get(hass).async_get_issue(DOMAIN, "missing_entities")
    assert issue is not None
    text = _solcast_lines(issue)
    for e in (TODAY, TOMORROW, REMAIN):
        assert f"`{e}`" in text and "from Solcast PV Forecast): not found" in text, e
    # Solcast installed: two found, one disabled -> only that one is named
    _solcast(hass, TODAY)
    _solcast(hass, TOMORROW)
    _solcast(hass, REMAIN, disabled=True)
    await hass.async_block_till_done()
    text = _solcast_lines(ir.async_get(hass).async_get_issue(DOMAIN, "missing_entities"))
    assert text == f"- `{REMAIN}` (solar still to come today, from Solcast PV Forecast): disabled"
    # enabled -> no Solcast line left
    er.async_get(hass).async_update_entity(REMAIN, disabled_by=None)
    await hass.async_block_till_done()
    assert _solcast_lines(ir.async_get(hass).async_get_issue(DOMAIN, "missing_entities")) == ""


async def test_no_repair_when_solcast_is_there(hass: HomeAssistant) -> None:
    for e in (TODAY, TOMORROW, REMAIN):
        _solcast(hass, e)
    await _setup(hass)
    assert _solcast_lines(ir.async_get(hass).async_get_issue(DOMAIN, "missing_entities")) == ""
