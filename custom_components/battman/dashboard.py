"""The Battman dashboard.

Create dashboard (on install, the button, or battman.create_dashboard) makes an ordinary
dashboard at /battman with Battman's views written into it (views/*.yaml, entity names
filled from the entity map). It's yours from the start: edit it like any dashboard. The
Battman cards on it (custom:battman-<id>) keep updating with releases; the views'
layout doesn't. For a fresh copy: delete the dashboard and press Create dashboard again.
If something is already at /battman, nothing is created and the message says so.

Older Battman versions made "managed" dashboards (their whole config is the Battman
strategy, {"strategy": {"type": "custom:battman"}}). Those still work, and removing
Battman deletes them; a dashboard you own is never touched.

HA has no public API for an integration to create a dashboard. This uses the same two
steps HA uses for its own Map dashboard (create the dashboard item, then save its
config), reaching HA's dashboards collection through the `lovelace/dashboards/list`
command. If a future HA version changes that, DashboardUnavailable is raised and
Battman shows a Repair instead of failing.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

STRATEGY_CONFIG: dict[str, Any] = {"strategy": {"type": "custom:battman"}}
BASE_URL_PATH = "battman"
TITLE = "Battman"
ICON = "mdi:battery-charging-medium"


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


def _taken(hass: HomeAssistant, url_path: str) -> bool:
    if url_path in _lovelace(hass).dashboards:
        return True
    try:
        from homeassistant.components import frontend  # noqa: PLC0415

        return url_path in hass.data.get(frontend.DATA_PANELS, {})
    except Exception:  # noqa: BLE001
        return False


async def async_create(hass: HomeAssistant) -> tuple[bool, str]:
    """Create the Battman dashboard at /battman unless something is already there.

    Returns (created, url_path): created is False when /battman was taken.
    """
    from .api import async_build_dashboard  # noqa: PLC0415

    url_path = BASE_URL_PATH
    if _taken(hass, url_path):
        return False, url_path
    built = await async_build_dashboard(hass)
    if built["errors"]:
        raise DashboardUnavailable("; ".join(built["errors"]))
    collection = _collection(hass)
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
        await _lovelace(hass).dashboards[url_path].async_save({"title": TITLE, "views": built["views"]})
    except DashboardUnavailable:
        raise
    except Exception as err:  # noqa: BLE001
        raise DashboardUnavailable(f"Creating the dashboard failed: {err}") from err
    _LOGGER.info("Created the Battman dashboard at /%s", url_path)
    return True, url_path


async def async_remove_managed(hass: HomeAssistant) -> list[str]:
    """Delete every managed (older-style) Battman dashboard; leave all others alone."""
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
