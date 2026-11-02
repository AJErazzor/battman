"""Setup drops config entry data Battman no longer uses (left by older versions), keeps its own flags,
and does the same whatever version the install came from."""

import pytest
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.battman import DASHBOARD_DONE, ENGINE_DONE, ENTRY_DATA_KEYS, LIVE_ACTIVITY_DONE

DONE = {DASHBOARD_DONE: True, LIVE_ACTIVITY_DONE: True, ENGINE_DONE: True}
# what the 0.29.x Migrate action stored in the entry
LEGACY = {
    "migrated_from_smiggles": True,
    "engine_in_charge": True,
    "smiggles_automations_were_on": ["automation.example"],
    "smiggles_enable_was": "on",
}


async def _setup(hass, data):
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain="battman", title="Battman", data=data)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


@pytest.mark.parametrize("data", [{**DONE, **LEGACY}, {**LEGACY}, dict(DONE), {}])
async def test_every_starting_state_ends_the_same(hass, data) -> None:
    entry = await _setup(hass, data)
    assert set(entry.data) <= ENTRY_DATA_KEYS
    for k in DONE:
        if k in data:
            assert entry.data[k] is True      # Battman's own flags survive


async def test_second_setup_changes_nothing(hass) -> None:
    entry = await _setup(hass, {**DONE, **LEGACY})
    before = dict(entry.data)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert dict(entry.data) == before
