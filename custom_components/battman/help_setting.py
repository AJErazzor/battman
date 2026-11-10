"""Settings → Dashboard options → Show help: the Help view follows the setting.

The setting is showHelp on sensor.battman_parameters, saved like every other setting (on unless it's
been turned off). When it changes, Battman adds the Help view to the dashboard at /battman (on) or
takes it off (off). Nothing happens at start-up or while it stays the same, so a Help view you delete
or add by hand stays as you left it until the setting next changes. When Battman can't do it (a YAML
dashboard, no dashboard to add it to, a save that fails), a notification says so.
"""

from __future__ import annotations

import logging

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from . import dashboard

_LOGGER = logging.getLogger(__name__)

NOTIFICATION_ID = "battman_help_view"
TITLE = "Battman help view"


def _message(show: bool, outcome: str, url_path: str) -> str | None:
    """What to tell you, or None when it worked (or there was nothing to do)."""
    if show and outcome == dashboard.NO_DASHBOARD:
        return (f"Show help is on, but there's no Battman dashboard at /{url_path} to add the Help view to. "
                "Press Create dashboard on the Battman device: a new Battman dashboard includes it.")
    if outcome == dashboard.NOT_EDITABLE and show:
        return (f"Show help is on, but Battman can't change what's at /{url_path} (a dashboard written in YAML, one "
                "with no saved views yet, or something that isn't a dashboard), so nothing changed. To add the Help "
                "view yourself, add a view with the card type: custom:battman-guide.")
    if outcome == dashboard.NOT_EDITABLE:
        # only a YAML dashboard comes back this way when turning it off (the others can't hold a Help view)
        return (f"Show help is off, but the dashboard at /{url_path} is written in YAML, so Battman can't change it. "
                "Remove the Help view yourself if you don't want it.")
    return None


async def async_apply(hass: HomeAssistant, show: bool) -> str:
    """Add or remove the Help view to match the setting. Returns the outcome."""
    try:
        outcome, url_path = await (dashboard.async_add_help_view if show else dashboard.async_remove_help_view)(hass)
    except dashboard.DashboardUnavailable as err:
        persistent_notification.async_create(
            hass, f"Could not {'add' if show else 'remove'} the Help view: {err}", title=TITLE,
            notification_id=NOTIFICATION_ID)
        return "error"
    if msg := _message(show, outcome, url_path):
        persistent_notification.async_create(hass, msg, title=TITLE, notification_id=NOTIFICATION_ID)
    else:
        persistent_notification.async_dismiss(hass, NOTIFICATION_ID)
    return outcome


@callback
def async_start(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Follow the setting while Battman is set up."""

    @callback
    def _changed(event: Event[EventStateChangedData]) -> None:
        old, new = event.data["old_state"], event.data["new_state"]
        if old is None or new is None:
            return
        was, now = old.attributes.get(dashboard.SHOW_HELP), new.attributes.get(dashboard.SHOW_HELP)
        if was is None or now is None or bool(was) == bool(now):
            return
        hass.async_create_task(async_apply(hass, bool(now)), "battman show help")

    entry.async_on_unload(async_track_state_change_event(hass, [dashboard.PARAMETERS], _changed))
