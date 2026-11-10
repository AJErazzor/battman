"""The Battman dashboard.

Create dashboard (on install, the button, or battman.create_dashboard) makes an ordinary
dashboard at /battman with Battman's views written into it (views/*.yaml, entity names
filled from the entity map). It's yours from the start: edit it like any dashboard. The
Battman cards on it (custom:battman-<id>) keep updating with releases; the views'
layout doesn't. For a fresh copy: delete the dashboard and press Create dashboard again.
If something is already at /battman, nothing is created and the message says so.

Create help view (the button, or battman.create_help_view) adds the Help view (views/40-help.yaml,
Battman's built-in guide) as the last tab of the dashboard at /battman, only if that dashboard has no
view at /battman/help. It never changes or removes anything else on the dashboard, and it does nothing
to a dashboard written in YAML or one with no saved views.

HA has no public API for an integration to create a dashboard. This uses the same two
steps HA uses for its own Map dashboard (create the dashboard item, then save its
config), reaching HA's dashboards collection through the `lovelace/dashboards/list`
command. If a future HA version changes that, DashboardUnavailable is raised and
Battman shows a Repair instead of failing.
"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

BASE_URL_PATH = "battman"
TITLE = "Battman"
ICON = "mdi:battery-charging-medium"
HELP_PATH = "help"

# What Create help view found (async_add_help_view)
ADDED = "added"                  # the Help view is now the dashboard's last tab
EXISTS = "exists"                # the dashboard already has a view at /battman/help: nothing changed
NO_DASHBOARD = "no_dashboard"    # nothing at /battman (or something that isn't a dashboard): nothing changed
NOT_EDITABLE = "not_editable"    # a YAML dashboard, or one with no saved views: nothing changed


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


async def async_add_help_view(hass: HomeAssistant) -> tuple[str, str]:
    """Add the Help view to the dashboard at /battman if it hasn't one. Returns (outcome, url_path).

    Only ever appends that one view; every other view, and the dashboard's own settings, stay as they are.
    """
    from homeassistant.components.lovelace.const import MODE_STORAGE, ConfigNotFound  # noqa: PLC0415

    from .api import async_build_view  # noqa: PLC0415

    url_path = BASE_URL_PATH
    dash = _lovelace(hass).dashboards.get(url_path)
    if dash is None:
        return NO_DASHBOARD, url_path
    if getattr(dash, "mode", None) != MODE_STORAGE:
        return NOT_EDITABLE, url_path
    try:
        config = await dash.async_load(False)
    except ConfigNotFound:
        return NOT_EDITABLE, url_path
    # a dashboard Home Assistant draws for you (no saved views, or one drawn by code) is left alone
    views = config.get("views") if isinstance(config, dict) else None
    if not isinstance(views, list):
        return NOT_EDITABLE, url_path
    if any(isinstance(v, dict) and v.get("path") == HELP_PATH for v in views):
        return EXISTS, url_path
    view = await async_build_view(hass, HELP_PATH)
    try:
        await dash.async_save({**config, "views": [*views, view]})
    except Exception as err:  # noqa: BLE001
        raise DashboardUnavailable(f"Saving the dashboard failed: {err}") from err
    _LOGGER.info("Added the Help view to the Battman dashboard at /%s", url_path)
    return ADDED, url_path
