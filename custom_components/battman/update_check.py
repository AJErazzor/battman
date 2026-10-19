"""Tell you when Battman has been updated and HA needs a restart.

HACS writes the new files, but the old code keeps running until HA restarts.
Every few minutes Battman compares the version on disk with the one it started
with; when they differ it raises a Repair with a Restart button.
"""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN

ISSUE_RESTART = "restart_required"
MANIFEST = Path(__file__).parent / "manifest.json"
INTERVAL = timedelta(minutes=5)


def _disk_version() -> str | None:
    try:
        return str(json.loads(MANIFEST.read_text(encoding="utf-8")).get("version"))
    except (OSError, ValueError):
        return None


async def async_check_once(hass: HomeAssistant, running: str) -> bool:
    """Raise the restart Repair if the files on disk are a different version."""
    on_disk = await hass.async_add_executor_job(_disk_version)
    if on_disk and on_disk != running:
        ir.async_create_issue(
            hass,
            DOMAIN,
            ISSUE_RESTART,
            is_fixable=True,
            is_persistent=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_RESTART,
            translation_placeholders={"running": running, "new": on_disk},
        )
        return True
    return False


@callback
def async_start(hass: HomeAssistant, running: str):
    """Start the periodic check. Returns the function that stops it."""
    # a fresh start runs the current files, so any old notice is out of date
    ir.async_delete_issue(hass, DOMAIN, ISSUE_RESTART)

    async def _tick(_now) -> None:
        await async_check_once(hass, running)

    unsub = async_track_time_interval(hass, _tick, INTERVAL)
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, lambda _e: unsub())
    return unsub
