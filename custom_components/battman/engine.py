"""Create the Battman engine automations and scripts.

The engine is Smiggles' engine ported like for like (see docs/engine.md): a script that
decides the battery mode, plus automations that run it and act on Sigen. They're made
from Battman's blueprints and written into automations.yaml and scripts.yaml, exactly
as if you'd made them from the blueprints in HA's editor, so you can open them, see
their traces, and read every step.

- Battman creates any that are missing on install, and again when you Migrate.
- It never edits or overwrites one that exists. Updates to the engine arrive through
  the blueprints (Battman replaces those on every update), so the automations follow.
- Every one of them checks binary_sensor.battman_in_charge first: they do nothing
  until you migrate, and nothing again after Hand back.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.util.file import write_utf8_file_atomic
from homeassistant.util.yaml import dump, load_yaml

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

ISSUE_NOT_LOADED = "engine_not_loaded"
NOTE = (
    "Battman engine, made by Battman from its blueprint (ported like for like from Smiggles). "
    "Does nothing unless Battman is in charge (binary_sensor.battman_in_charge). "
    "Battman won't overwrite it; delete it and run Migrate (or reinstall) to get Battman's version back."
)

SCRIPTS: dict[str, dict[str, Any]] = {
    "battman_engine": {
        "alias": "Battman engine",
        "description": NOTE,
        "icon": "mdi:battery-sync",
        "use_blueprint": {"path": "battman/battman_engine.yaml", "input": {}},
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


class EngineError(Exception):
    """automations.yaml / scripts.yaml couldn't be read or written."""


def _paths(hass: HomeAssistant) -> tuple[Path, Path]:
    return Path(hass.config.path("automations.yaml")), Path(hass.config.path("scripts.yaml"))


def _write_missing(auto_path: Path, script_path: Path) -> list[str]:
    added: list[str] = []
    try:
        autos = load_yaml(str(auto_path)) if auto_path.exists() else []
        scripts = load_yaml(str(script_path)) if script_path.exists() else {}
    except Exception as err:  # noqa: BLE001
        raise EngineError(f"Couldn't read automations.yaml / scripts.yaml: {err}") from err
    autos = autos or []
    scripts = scripts or {}
    if not isinstance(autos, list):
        raise EngineError("automations.yaml isn't a list of automations")
    if not isinstance(scripts, dict):
        raise EngineError("scripts.yaml isn't a set of scripts")
    have = {a.get("id") for a in autos if isinstance(a, dict)}
    new_autos = [a for a in AUTOMATIONS if a["id"] not in have]
    new_scripts = {k: v for k, v in SCRIPTS.items() if k not in scripts}
    if new_scripts:
        write_utf8_file_atomic(str(script_path), dump({**scripts, **new_scripts}))
        added += list(new_scripts)
    if new_autos:
        write_utf8_file_atomic(str(auto_path), dump([*autos, *new_autos]))
        added += [a["id"] for a in new_autos]
    return added


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


async def async_write_missing(hass: HomeAssistant) -> list[str]:
    """Write any missing engine automations/scripts into the files (no reload). Returns ids added."""
    auto_path, script_path = _paths(hass)
    added = await hass.async_add_executor_job(_write_missing, auto_path, script_path)
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


async def async_create_missing(hass: HomeAssistant) -> list[str]:
    """Write any missing engine items, reload, check. Returns ids added. Raises EngineError."""
    added = await async_write_missing(hass)
    if added or missing(hass):
        await async_reload_and_check(hass)
    return added
