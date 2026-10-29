"""v0.28.0: OpenNEM not installed raises a Repair.

The NEM mix card (on the default Power view) needs the OpenNEM integration and power-pie-card.
power-pie-card already had a Repair; OpenNEM now has one too, so a new user isn't left with an
empty card and no reason. It's optional, so the Repair can be ignored (and stays ignored across
restarts), and it goes as soon as OpenNEM is installed. The card itself says OpenNEM is needed
when Battman's NEM sensors don't exist.
"""

from pathlib import Path
from unittest.mock import patch

import yaml
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.template import Template
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

DOMAIN = "battman"
ISSUE = "opennem_missing"
CARDS = Path(__file__).parents[1] / "custom_components/battman/cards"


async def _setup(hass):
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain=DOMAIN, title="Battman", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _issue(hass):
    return ir.async_get(hass).async_get_issue(DOMAIN, ISSUE)


async def test_repair_without_opennem_goes_when_installed(hass: HomeAssistant) -> None:
    await _setup(hass)
    issue = _issue(hass)
    assert issue is not None and issue.severity == ir.IssueSeverity.WARNING and not issue.is_fixable
    # OpenNEM installed: the Repair goes, no restart
    opennem = MockConfigEntry(domain="opennem", title="OpenNEM")
    with patch.object(hass.config_entries, "async_setup", return_value=True):
        await hass.config_entries.async_add(opennem)
    await hass.async_block_till_done()
    assert _issue(hass) is None
    # removed again: it's back
    await hass.config_entries.async_remove(opennem.entry_id)
    await hass.async_block_till_done()
    assert _issue(hass) is not None


async def test_no_repair_with_opennem(hass: HomeAssistant) -> None:
    MockConfigEntry(domain="opennem", title="OpenNEM").add_to_hass(hass)
    await _setup(hass)
    assert _issue(hass) is None


async def test_ignored_stays_ignored_after_restart(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    ir.async_ignore_issue(hass, DOMAIN, ISSUE, True)
    assert _issue(hass).dismissed_version is not None
    # Battman reloads (as at a restart): still ignored
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert _issue(hass) is not None and _issue(hass).dismissed_version is not None


def test_repair_text_exists() -> None:
    import json

    issues = json.loads((Path(__file__).parents[1] / "custom_components/battman/translations/en.json").read_text())["issues"]
    assert "OpenNEM" in issues[ISSUE]["title"] and "Ignore" in issues[ISSUE]["description"]


async def test_card_says_opennem_needed(hass: HomeAssistant) -> None:
    card = yaml.safe_load((CARDS / "nemmix.yaml").read_text())
    content = card["cards"][0]["card"]["content"]

    def render():
        return Template(content, hass).async_render(parse_result=False).strip()

    # no NEM sensors at all (OpenNEM not installed)
    assert "needs the OpenNEM integration" in render()
    # sensors there, one without a value: names it, as before
    hass.states.async_set("sensor.battman_nem_wind", "812.4", {})
    hass.states.async_set("sensor.battman_nem_gas_recip", "unknown", {"problem": "sensor.opennem_sa has no value for: gas_recip"})
    out = render()
    assert "OpenNEM integration" not in out and "sensor.battman_nem_gas_recip" in out and "gas_recip" in out
