"""The Battman dashboard.

Create dashboard (on install, the button, or battman.create_dashboard) makes an ordinary
dashboard at /battman with Battman's views written into it (views/*.yaml, entity names
filled from the entity map). It's yours from the start: edit it like any dashboard. The
Battman cards on it (custom:battman-<id>) keep updating with releases; the views'
layout doesn't. For a fresh copy: delete the dashboard and press Create dashboard again.
If something is already at /battman, nothing is created and the message says so.

The Help view (views/40-help.yaml, Battman's built-in guide) follows Settings → Dashboard options →
Show help (the showHelp setting, help_setting.py). Turning it on adds the Help view as the last tab of
the dashboard at /battman if that dashboard has no view at /battman/help; turning it off removes the
Help view (a view at /battman/help holding the guide card). Nothing else on the dashboard changes, and
a dashboard written in YAML or one with no saved views is left alone. While it's off, Create dashboard
leaves the Help view out.

HA has no public API for an integration to create a dashboard. This uses the same two
steps HA uses for its own Map dashboard (create the dashboard item, then save its
config), reaching HA's dashboards collection through the `lovelace/dashboards/list`
command. If a future HA version changes that, DashboardUnavailable is raised and
Battman shows a Repair instead of failing.
"""

from __future__ import annotations

import asyncio
import logging

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

BASE_URL_PATH = "battman"
TITLE = "Battman"
ICON = "mdi:battery-charging-medium"
HELP_PATH = "help"

PARAMETERS = "sensor.battman_parameters"
SHOW_HELP = "showHelp"

# What adding or removing the Help view found (async_add_help_view, async_remove_help_view)
ADDED = "added"                  # the Help view is now the dashboard's last tab
EXISTS = "exists"                # the dashboard already has a view at /battman/help: nothing changed
REMOVED = "removed"              # the Help view was taken off the dashboard
ABSENT = "absent"                # no Help view to take off: nothing changed
NO_DASHBOARD = "no_dashboard"    # nothing at /battman (or something that isn't a dashboard): nothing changed
NOT_EDITABLE = "not_editable"    # a YAML dashboard, one with no saved views, or not a dashboard: nothing changed


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
    if not help_shown(hass):
        built["views"] = [v for v in built["views"] if not (isinstance(v, dict) and v.get("path") == HELP_PATH)]
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


def help_shown(hass: HomeAssistant) -> bool:
    """Settings → Dashboard options → Show help (on until it's turned off, and while the setting can't be read)."""
    state = hass.states.get(PARAMETERS)
    value = state.attributes.get(SHOW_HELP) if state else None
    return value is not False


def _is_help_view(view) -> bool:
    """A view at /battman/help that holds Battman's guide card (one of yours at that path is left alone)."""
    if not (isinstance(view, dict) and view.get("path") == HELP_PATH):
        return False
    cards = list(view.get("cards") or [])
    for section in view.get("sections") or []:
        cards += list((section or {}).get("cards") or [])
    return any(isinstance(c, dict) and c.get("type") == "custom:battman-guide" for c in cards)


def _lock(hass: HomeAssistant) -> asyncio.Lock:
    # one change at a time: two together must not both find the view missing and add it twice
    return hass.data.setdefault(f"{__name__}.help_lock", asyncio.Lock())


async def _editable(hass: HomeAssistant):
    """(outcome, dashboard, config, views): outcome is None when the dashboard at /battman can be changed."""
    from homeassistant.components.lovelace.const import MODE_STORAGE, ConfigNotFound  # noqa: PLC0415

    dash = _lovelace(hass).dashboards.get(BASE_URL_PATH)
    if dash is None:
        # something that isn't a dashboard (a panel) at /battman can't take a view; Create dashboard wouldn't help
        return (NOT_EDITABLE if _taken(hass, BASE_URL_PATH) else NO_DASHBOARD), None, None, None
    if getattr(dash, "mode", None) != MODE_STORAGE:
        return NOT_EDITABLE, None, None, None
    try:
        config = await dash.async_load(False)
    except ConfigNotFound:
        return NOT_EDITABLE, None, None, None
    # a dashboard Home Assistant draws for you (no saved views, or one drawn by code) is left alone
    views = config.get("views") if isinstance(config, dict) else None
    if not isinstance(views, list):
        return NOT_EDITABLE, None, None, None
    return None, dash, config, views


async def _save(dash, config: dict) -> None:
    try:
        await dash.async_save(config)
    except Exception as err:  # noqa: BLE001
        raise DashboardUnavailable(f"Saving the dashboard failed: {err}") from err


async def async_add_help_view(hass: HomeAssistant) -> tuple[str, str]:
    """Add the Help view to the dashboard at /battman if it hasn't one. Returns (outcome, url_path).

    Only ever appends that one view; every other view, and the dashboard's own settings, stay as they are.
    """
    from .api import async_build_view  # noqa: PLC0415

    async with _lock(hass):
        outcome, dash, config, views = await _editable(hass)
        if outcome:
            return outcome, BASE_URL_PATH
        if any(isinstance(v, dict) and v.get("path") == HELP_PATH for v in views):
            return EXISTS, BASE_URL_PATH
        view = await async_build_view(hass, HELP_PATH)
        await _save(dash, {**config, "views": [*views, view]})
    _LOGGER.info("Added the Help view to the Battman dashboard at /%s", BASE_URL_PATH)
    return ADDED, BASE_URL_PATH


async def async_remove_help_view(hass: HomeAssistant) -> tuple[str, str]:
    """Take the Help view (the guide card's view at /battman/help) off the dashboard. Returns (outcome, url_path).

    Every other view, and the dashboard's own settings, stay as they are.
    """
    async with _lock(hass):
        outcome, dash, config, views = await _editable(hass)
        if outcome:
            return (ABSENT if outcome == NO_DASHBOARD else outcome), BASE_URL_PATH
        keep = [v for v in views if not _is_help_view(v)]
        if len(keep) == len(views):
            return ABSENT, BASE_URL_PATH
        await _save(dash, {**config, "views": keep})
    _LOGGER.info("Removed the Help view from the Battman dashboard at /%s", BASE_URL_PATH)
    return REMOVED, BASE_URL_PATH
