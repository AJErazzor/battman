"""Battman's automations and scripts in automations.yaml / scripts.yaml.

HA has no public API for an integration to add automations, so Battman edits the same two
files HA's automation and script editors write. It only ever adds items that are missing
and, when Battman is removed, takes out the items it made (by their ids). Everything else in
those files is left exactly as it was.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util.file import write_utf8_file_atomic
from homeassistant.util.yaml import dump, load_yaml


class AutomationFileError(Exception):
    """automations.yaml / scripts.yaml couldn't be read or written."""


def paths(hass: HomeAssistant) -> tuple[Path, Path]:
    return Path(hass.config.path("automations.yaml")), Path(hass.config.path("scripts.yaml"))


def _load(auto_path: Path, script_path: Path) -> tuple[list[Any], dict[str, Any]]:
    try:
        autos = load_yaml(str(auto_path)) if auto_path.exists() else []
        scripts = load_yaml(str(script_path)) if script_path.exists() else {}
    except Exception as err:  # noqa: BLE001  (HA's YAML errors vary)
        raise AutomationFileError(f"Couldn't read automations.yaml / scripts.yaml: {err}") from err
    autos = autos or []
    scripts = scripts or {}
    if not isinstance(autos, list):
        raise AutomationFileError("automations.yaml isn't a list of automations")
    if not isinstance(scripts, dict):
        raise AutomationFileError("scripts.yaml isn't a set of scripts")
    return autos, scripts


def write_missing(
    auto_path: Path, script_path: Path, automations: list[dict[str, Any]], scripts: dict[str, dict[str, Any]]
) -> list[str]:
    """Add the automations (by id) and scripts (by key) the files don't have. Returns the ids added."""
    autos, have_scripts = _load(auto_path, script_path)
    have = {a.get("id") for a in autos if isinstance(a, dict)}
    new_autos = [a for a in automations if a["id"] not in have]
    new_scripts = {k: v for k, v in scripts.items() if k not in have_scripts}
    added: list[str] = []
    if new_scripts:
        write_utf8_file_atomic(str(script_path), dump({**have_scripts, **new_scripts}))
        added += list(new_scripts)
    if new_autos:
        write_utf8_file_atomic(str(auto_path), dump([*autos, *new_autos]))
        added += [a["id"] for a in new_autos]
    return added


def remove(auto_path: Path, script_path: Path, automation_ids: set[str], script_ids: set[str]) -> list[str]:
    """Take out the automations and scripts with these ids. Returns the ids removed."""
    autos, scripts = _load(auto_path, script_path)
    kept = [a for a in autos if not (isinstance(a, dict) and a.get("id") in automation_ids)]
    gone_autos = [a["id"] for a in autos if isinstance(a, dict) and a.get("id") in automation_ids]
    gone_scripts = [k for k in scripts if k in script_ids]
    if gone_autos:
        write_utf8_file_atomic(str(auto_path), dump(kept))
    if gone_scripts:
        write_utf8_file_atomic(str(script_path), dump({k: v for k, v in scripts.items() if k not in script_ids}))
    return [*gone_scripts, *gone_autos]
