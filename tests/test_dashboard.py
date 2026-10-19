"""Managed-dashboard behaviour against a real (test) Home Assistant."""

from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

DOMAIN = "battman"
STRATEGY = {"strategy": {"type": "custom:battman"}}


async def _cfg(hass, url_path):
    return await hass.data[LOVELACE_DATA].dashboards[url_path].async_load(False)


async def test_dashboard_lifecycle(hass: HomeAssistant) -> None:
    assert await async_setup_component(hass, "lovelace", {})

    entry = MockConfigEntry(domain=DOMAIN, title="Battman", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # 1. install creates a managed dashboard once, and records that it did
    assert await _cfg(hass, "battman") == STRATEGY
    assert entry.data.get("dashboard_created_on_install") is True
    item = hass.data[LOVELACE_DATA].dashboards["battman"].config
    assert item["title"] == "Battman" and item["show_in_sidebar"] is True

    # 2. action while a managed one exists: nothing changes
    r = await hass.services.async_call(DOMAIN, "create_dashboard", {}, blocking=True, return_response=True)
    assert r["created"] is False and r["url_path"] == "battman"

    # 3. take control + rename to Robin, then ask for a managed one again
    robin = {"title": "Robin", "views": [{"title": "Mine", "cards": []}]}
    await hass.data[LOVELACE_DATA].dashboards["battman"].async_save(robin)
    r = await hass.services.async_call(DOMAIN, "create_dashboard", {}, blocking=True, return_response=True)
    assert r["created"] is True and r["url_path"] == "battman-2"
    assert await _cfg(hass, "battman-2") == STRATEGY
    assert await _cfg(hass, "battman") == robin          # Robin untouched

    # 4. the button does the same (and says so in a notification)
    button = hass.states.get("button.battman_create_dashboard")
    assert button is not None
    await hass.services.async_call("button", "press", {"entity_id": button.entity_id}, blocking=True)
    assert "battman-3" not in hass.data[LOVELACE_DATA].dashboards

    # 5. reload: no second auto-create
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert "battman-3" not in hass.data[LOVELACE_DATA].dashboards

    # 6. removing Battman deletes managed dashboards only
    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert "battman-2" not in hass.data[LOVELACE_DATA].dashboards
    assert await _cfg(hass, "battman") == robin
