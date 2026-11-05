"""Create the Battman engine automations and scripts.

Battman's engine (see docs/engine.md) is a script that decides the battery mode, plus
automations that run it and act on Sigen. They're made
from Battman's blueprints and written into automations.yaml and scripts.yaml, exactly
as if you'd made them from the blueprints in HA's editor, so you can open them, see
their traces, and read every step.

- Battman creates any that are missing on install.
- It never edits or overwrites one that exists. Updates to the engine arrive through
  the blueprints (Battman replaces those on every update), so the automations follow.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir

from . import automation_files
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

ISSUE_NOT_LOADED = "engine_not_loaded"
NOTE = (
    "Battman engine, made by Battman from its blueprint. "
    "Battman won't overwrite it; delete it and reinstall to get Battman's version back."
)

# SHA-256 of the descriptions earlier versions wrote into these items (they mentioned things that
# no longer exist). A description that is exactly one of them is replaced with NOTE on setup; one you
# edited doesn't match and is left alone.
OLD_NOTE_HASHES = frozenset({
    "cd49a3806470b3133f1207bf74cb5f450ff152a3847854abc3f706ccc8b1d0b8",
    "a01f8b031888d4559aa2340d66aadc31d945b0d5f6620a6ecbf5484eb07ccfc7",
    "a6d5b1c5ffa1141530b7f8136ac257455bd62d5f3c33c0409dd5475c6e94141d",
})

SCRIPTS: dict[str, dict[str, Any]] = {
    "battman_engine": {
        "alias": "Battman engine",
        "description": NOTE,
        "icon": "mdi:battery-sync",
        "use_blueprint": {"path": "battman/battman_engine.yaml", "input": {}},
    },
    # the three scripts the engine is made of (the engine itself reads, decides, then acts)
    "battman_engine_inputs": {
        "alias": "Battman engine – inputs",
        "description": NOTE,
        "icon": "mdi:database-import-outline",
        "use_blueprint": {"path": "battman/battman_engine_inputs.yaml", "input": {}},
    },
    "battman_engine_decide": {
        "alias": "Battman engine – decide",
        "description": NOTE,
        "icon": "mdi:head-cog-outline",
        "use_blueprint": {"path": "battman/battman_engine_decide.yaml", "input": {}},
    },
    "battman_engine_forecast": {
        "alias": "Battman engine – forecast",
        "description": NOTE,
        "icon": "mdi:chart-timeline-variant",
        "use_blueprint": {"path": "battman/battman_engine_forecast.yaml", "input": {}},
    },
    "battman_apply_scene": {
        "alias": "Battman apply scene",
        "description": NOTE,
        "icon": "mdi:palette-swatch-variant",
        "use_blueprint": {"path": "battman/battman_apply_scene.yaml", "input": {}},
    },
}
AUTOMATION_NAMES = {
    "loop": "main loop",
    "watchdog": "watchdog",
    "sig_mode": "Sigen mode",
    "sig_curtail": "curtail",
    "sapn_override": "SAPN override",
    "timer_duration": "override timer start",
    "copy_curves": "copy curves to next month",
    "curve_switcher": "auto curve switcher",
    "armed_scene": "armed scene (00:01)",
}
AUTOMATIONS: list[dict[str, Any]] = [
    {
        "id": f"battman_engine_{name}",
        "alias": f"Battman engine – {title}",
        "description": NOTE,
        "use_blueprint": {"path": f"battman/battman_engine_{name}.yaml", "input": {}},
    }
    for name, title in AUTOMATION_NAMES.items()
]


# Engine automations added after the first release of the engine. An install that already has the
# engine gets each one made once, by the first start of a version that has it (so one you delete
# stays deleted); a fresh install gets them with the rest.
# The three engine scripts are in the same position (an install that already had the engine gets them once).
ADDED_LATER = ("battman_engine_curve_switcher", "battman_engine_inputs", "battman_engine_decide", "battman_engine_forecast")


class EngineError(Exception):
    """automations.yaml / scripts.yaml couldn't be read or written."""


def entity_ids(hass: HomeAssistant) -> dict[str, str | None]:
    """Engine item id -> its entity id (None if HA hasn't loaded it)."""
    reg = er.async_get(hass)
    out: dict[str, str | None] = {}
    for sid in SCRIPTS:
        out[sid] = reg.async_get_entity_id("script", "script", sid)
    for a in AUTOMATIONS:
        out[a["id"]] = reg.async_get_entity_id("automation", "automation", a["id"])
    return out


def missing(hass: HomeAssistant) -> list[str]:
    return [k for k, v in entity_ids(hass).items() if v is None]


async def async_write_missing(hass: HomeAssistant, only: set[str] | None = None) -> list[str]:
    """Write any missing engine automations/scripts into the files (no reload). Returns ids added.

    `only`: just these ids (automations and scripts), for the ones added after the first release.
    """
    auto_path, script_path = automation_files.paths(hass)
    autos = AUTOMATIONS if only is None else [a for a in AUTOMATIONS if a["id"] in only]
    scripts = SCRIPTS if only is None else {k: v for k, v in SCRIPTS.items() if k in only}
    try:
        added = await hass.async_add_executor_job(
            automation_files.write_missing, auto_path, script_path, autos, scripts
        )
    except automation_files.AutomationFileError as err:
        raise EngineError(str(err)) from err
    if added:
        _LOGGER.info("Battman wrote engine automations/scripts: %s", ", ".join(added))
    return added


async def async_reload_and_check(hass: HomeAssistant) -> None:
    """Reload automations/scripts and check every engine item loaded. Raises EngineError if not."""
    for domain in ("script", "automation"):
        if hass.services.has_service(domain, "reload"):
            await hass.services.async_call(domain, "reload", blocking=True)
    if gone := missing(hass):
        ir.async_create_issue(
            hass, DOMAIN, ISSUE_NOT_LOADED, is_fixable=False, severity=ir.IssueSeverity.ERROR,
            translation_key=ISSUE_NOT_LOADED, translation_placeholders={"missing": ", ".join(gone)},
        )
        raise EngineError(f"Home Assistant didn't load these Battman engine items: {', '.join(gone)}")
    ir.async_delete_issue(hass, DOMAIN, ISSUE_NOT_LOADED)


async def async_refresh_notes(hass: HomeAssistant) -> list[str]:
    """Bring the descriptions of Battman's engine items up to date where an older version wrote them.

    Only the description changes, and only where it is exactly one of OLD_NOTE_HASHES. Idempotent, and
    based on what's in the files, not on the version before. Any problem is logged, never raised.
    """
    auto_path, script_path = automation_files.paths(hass)
    try:
        changed = await hass.async_add_executor_job(
            automation_files.refresh_descriptions, auto_path, script_path,
            {a["id"] for a in AUTOMATIONS}, set(SCRIPTS), NOTE, OLD_NOTE_HASHES,
        )
    except (automation_files.AutomationFileError, OSError) as err:
        _LOGGER.warning("Battman couldn't update the descriptions of its engine items: %s", err)
        return []
    if changed:
        _LOGGER.info("Battman updated the descriptions of: %s", ", ".join(changed))
        for domain in ("script", "automation"):
            if hass.state is CoreState.running and hass.services.has_service(domain, "reload"):
                await hass.services.async_call(domain, "reload", blocking=True)
    return changed


async def async_create_missing(hass: HomeAssistant) -> list[str]:
    """Write any missing engine items, reload, check. Returns ids added. Raises EngineError."""
    added = await async_write_missing(hass)
    if added or missing(hass):
        await async_reload_and_check(hass)
    return added
