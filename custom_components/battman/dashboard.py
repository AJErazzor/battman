"""The managed Battman dashboard.

A dashboard is "managed" when its whole config is the Battman strategy
({"strategy": {"type": "custom:battman"}}). Battman only ever creates managed
dashboards and only ever deletes managed ones; a dashboard you've taken control
of (its config now has views) is never touched.

HA has no public API for an integration to create a dashboard. This uses the
same two steps HA uses for its own Map dashboard (create the dashboard item,
then save the strategy config), reaching HA's dashboards collection through the
`lovelace/dashboards/list` command. If a future HA version changes that,
DashboardUnavailable is raised and Battman shows a Repair instead of failing.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

STRATEGY_CONFIG: dict[str, Any] = {"strategy": {"type": "custom:battman"}}
BASE_URL_PATH = "battman"
TITLE = "Battman"
ICON = "mdi:battery-heart-variant"


class DashboardUnavailable(Exception):
    """HA's dashboard internals aren't where Battman expects them."""


def _lovelace(hass: HomeAssistant):
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA  # noqa: PLC0415

        return hass.data[LOVELACE_DATA]
    except (ImportError, KeyError) as err:
        raise DashboardUnavailable(f"Lovelace data not found: {err}") from err


def _collection(hass: HomeAssistant):
    try:
        handler = hass.data["websocket_api"]["lovelace/dashboards/list"][0]
        return handler.__self__.storage_collection
    except (KeyError, IndexError, AttributeError, TypeError) as err:
        raise DashboardUnavailable(f"Dashboards collection not found: {err}") from err


def _is_managed(config: Any) -> bool:
    return (
        isinstance(config, dict)
        and isinstance(config.get("strategy"), dict)
        and config["strategy"].get("type") == STRATEGY_CONFIG["strategy"]["type"]
    )


async def async_find_managed(hass: HomeAssistant) -> list[str]:
    """URL paths of every managed Battman dashboard."""
    found = []
    for url_path, dash in list(_lovelace(hass).dashboards.items()):
        if not url_path or not hasattr(dash, "async_load"):
            continue
        try:
            config = await dash.async_load(False)
        except Exception:  # noqa: BLE001  (empty / never-saved dashboards raise)
            continue
        if _is_managed(config):
            found.append(url_path)
    return found


def _free_url_path(hass: HomeAssistant) -> str:
    taken = set(_lovelace(hass).dashboards)
    try:
        from homeassistant.components import frontend  # noqa: PLC0415

        taken |= set(hass.data.get(frontend.DATA_PANELS, {}))
    except Exception:  # noqa: BLE001
        pass
    if BASE_URL_PATH not in taken:
        return BASE_URL_PATH
    n = 2
    while f"{BASE_URL_PATH}-{n}" in taken:
        n += 1
    return f"{BASE_URL_PATH}-{n}"


async def async_create(hass: HomeAssistant) -> tuple[bool, str]:
    """Create a managed dashboard unless one exists.

    Returns (created, url_path): created is False when one already existed.
    """
    existing = await async_find_managed(hass)
    if existing:
        return False, existing[0]

    collection = _collection(hass)
    url_path = _free_url_path(hass)
    try:
        await collection.async_create_item(
            {
                "allow_single_word": True,
                "icon": ICON,
                "title": TITLE,
                "url_path": url_path,
                "require_admin": False,
                "show_in_sidebar": True,
            }
        )
        await _lovelace(hass).dashboards[url_path].async_save(dict(STRATEGY_CONFIG))
    except DashboardUnavailable:
        raise
    except Exception as err:  # noqa: BLE001
        raise DashboardUnavailable(f"Creating the dashboard failed: {err}") from err
    _LOGGER.info("Created managed Battman dashboard at /%s", url_path)
    return True, url_path


async def async_remove_managed(hass: HomeAssistant) -> list[str]:
    """Delete every managed Battman dashboard; leave all others alone."""
    removed = []
    lovelace = _lovelace(hass)
    collection = _collection(hass)
    for url_path in await async_find_managed(hass):
        item_id = (lovelace.dashboards[url_path].config or {}).get("id")
        if not item_id:
            continue
        await collection.async_delete_item(item_id)
        removed.append(url_path)
    return removed
