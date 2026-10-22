"""The Battman dashboard against a real (test) Home Assistant: an ordinary dashboard you own,
made at /battman with Battman's views written in."""

import json

from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

DOMAIN = "battman"
STRATEGY = {"strategy": {"type": "custom:battman"}}


async def _cfg(hass, url_path):
    return await hass.data[LOVELACE_DATA].dashboards[url_path].async_load(False)


async def _create(hass):
    return await hass.services.async_call(DOMAIN, "create_dashboard", {}, blocking=True, return_response=True)


async def _delete(hass, url_path):
    from custom_components.battman import dashboard

    item_id = hass.data[LOVELACE_DATA].dashboards[url_path].config["id"]
    await dashboard._collection(hass).async_delete_item(item_id)
    await hass.async_block_till_done()


async def test_dashboard_lifecycle(hass: HomeAssistant) -> None:
    assert await async_setup_component(hass, "lovelace", {})

    entry = MockConfigEntry(domain=DOMAIN, title="Battman", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # 1. install creates the dashboard once, at /battman: views written in (not the strategy)
    cfg = await _cfg(hass, "battman")
    assert "strategy" not in cfg and cfg["title"] == "Battman"
    assert [v["path"] for v in cfg["views"]] == ["power", "curvy", "pricy", "finances", "settings", "log", "theme"]
    assert "{{" not in json.dumps(cfg)                       # entity names filled in
    curvy = next(v for v in cfg["views"] if v["path"] == "curvy")
    assert curvy["cards"][0]["type"] == "custom:battman-curvy"
    assert entry.data.get("dashboard_created_on_install") is True
    item = hass.data[LOVELACE_DATA].dashboards["battman"].config
    assert item["title"] == "Battman" and item["show_in_sidebar"] is True

    # 2. /battman taken (yours now, edited): asking again changes nothing, and says why
    mine = {"title": "Robin", "views": [{"title": "Mine", "cards": []}]}
    await hass.data[LOVELACE_DATA].dashboards["battman"].async_save(mine)
    r = await _create(hass)
    assert r["created"] is False and r["url_path"] == "battman" and "delete that one first" in r["message"]
    assert await _cfg(hass, "battman") == mine
    assert "battman-2" not in hass.data[LOVELACE_DATA].dashboards

    # 3. delete it, create again: a fresh copy at /battman
    await _delete(hass, "battman")
    r = await _create(hass)
    assert r["created"] is True and r["url_path"] == "battman"
    assert (await _cfg(hass, "battman"))["views"][0]["path"] == "power"

    # 4. the button does the same (and says so in a notification): /battman is taken, nothing new
    button = hass.states.get("button.battman_create_dashboard")
    assert button is not None
    await hass.services.async_call("button", "press", {"entity_id": button.entity_id}, blocking=True)
    assert "battman-2" not in hass.data[LOVELACE_DATA].dashboards

    # 5. reload: no second auto-create (even after deleting it)
    await _delete(hass, "battman")
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert "battman" not in hass.data[LOVELACE_DATA].dashboards

    # 6. an older managed dashboard is still removed with Battman; yours is never touched
    await _create(hass)
    mine_cfg = await _cfg(hass, "battman")
    from custom_components.battman import dashboard

    await dashboard._collection(hass).async_create_item(
        {"allow_single_word": True, "icon": "mdi:battery", "title": "Old", "url_path": "battman-old",
         "require_admin": False, "show_in_sidebar": True})
    await hass.data[LOVELACE_DATA].dashboards["battman-old"].async_save(STRATEGY)
    assert await dashboard.async_find_managed(hass) == ["battman-old"]
    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert "battman-old" not in hass.data[LOVELACE_DATA].dashboards
    assert await _cfg(hass, "battman") == mine_cfg
