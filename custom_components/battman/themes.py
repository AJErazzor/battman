"""Battman themes: the shipped ones, and your own (saved by the theme studio).

<config>/themes/battman/          shipped themes; Battman replaces these on every
                                  update (files it no longer ships are removed)
<config>/themes/battman/custom/   your themes; Battman never touches these on
                                  update or removal
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import yaml

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SHIPPED_SRC = Path(__file__).parent / "themes"
DST_PARTS = ("themes", "battman")
CUSTOM_DIR = "custom"
NAME_RE = re.compile(r"^Battman [A-Za-z0-9][A-Za-z0-9 _-]{0,47}$")
MAX_YAML_BYTES = 200_000


class ThemeSaveError(Exception):
    """A theme couldn't be saved; the message says why (shown to the user)."""

    def __init__(self, message: str, status: int = 400, exists: bool = False) -> None:
        super().__init__(message)
        self.status = status
        self.exists = exists


def dst_dir(hass: HomeAssistant) -> Path:
    return Path(hass.config.path(*DST_PARTS))


def shipped_names() -> set[str]:
    """Theme names (the key HA uses) of every theme Battman ships."""
    names: set[str] = set()
    for f in SHIPPED_SRC.glob("*.yaml"):
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        names.update(data.keys())
    return names


def install(dst: Path) -> bool:
    """Copy shipped themes into dst (top level only). True if anything changed."""
    dst.mkdir(parents=True, exist_ok=True)
    changed = False
    shipped = {f.name: f for f in SHIPPED_SRC.glob("*.yaml")}
    for name, src in shipped.items():
        target = dst / name
        data = src.read_bytes()
        if not target.exists() or target.read_bytes() != data:
            target.write_bytes(data)
            changed = True
    for old in dst.glob("*.yaml"):          # top level only: custom/ is never touched
        if old.name not in shipped:
            old.unlink()
            changed = True
    return changed


def remove_shipped(dst: Path) -> bool:
    """Battman removed: delete the shipped themes, keep custom/ (your work)."""
    changed = False
    if not dst.exists():
        return False
    for f in dst.glob("*.yaml"):
        f.unlink()
        changed = True
    try:
        dst.rmdir()                         # only succeeds if nothing (e.g. custom/) is left
    except OSError:
        pass
    return changed


def save_custom(dst: Path, name: str, text: str, overwrite: bool) -> Path:
    """Validate and write one of your themes into dst/custom/. Returns the file path."""
    name = (name or "").strip()
    if not NAME_RE.match(name):
        raise ThemeSaveError(
            "Theme name must start with “Battman ” and use only letters, numbers, spaces, - and _ (max 56 characters)."
        )
    if name in shipped_names():
        raise ThemeSaveError(f"“{name}” is a theme Battman ships. Pick another name for your own theme.", status=409)
    if len((text or "").encode("utf-8")) > MAX_YAML_BYTES:
        raise ThemeSaveError("Theme YAML is too large.")
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as err:
        raise ThemeSaveError(f"Theme YAML doesn't parse: {err}") from err
    if not isinstance(data, dict) or list(data.keys()) != [name] or not isinstance(data[name], dict):
        raise ThemeSaveError(f"Theme YAML must contain exactly one theme, named “{name}”.")
    if not any(str(k).startswith("battman-") for k in data[name]):
        raise ThemeSaveError("That doesn't look like a Battman theme (no battman-* colours).")

    folder = dst / CUSTOM_DIR
    target = folder / f"{name}.yaml"
    if target.exists() and not overwrite:
        raise ThemeSaveError(f"You already have a theme called “{name}”.", status=409, exists=True)
    folder.mkdir(parents=True, exist_ok=True)
    target.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    return target


ISSUE_NOT_LOADED = "themes_not_loaded"


async def async_check(hass: HomeAssistant) -> list[str]:
    """Raise (or clear) the Repair for Battman themes HA hasn't loaded. Returns the missing names.

    HA only reads themes/battman/ when configuration.yaml has
    `frontend: themes: !include_dir_merge_named themes`.
    """
    from homeassistant.components.frontend import DATA_THEMES  # noqa: PLC0415

    shipped = await hass.async_add_executor_job(shipped_names)
    loaded = hass.data.get(DATA_THEMES, {})
    missing = sorted(n for n in shipped if n not in loaded)
    if missing:
        ir.async_create_issue(
            hass, DOMAIN, ISSUE_NOT_LOADED, is_fixable=False, severity=ir.IssueSeverity.ERROR,
            translation_key=ISSUE_NOT_LOADED,
            translation_placeholders={"folder": "/".join(DST_PARTS), "count": str(len(missing))},
        )
        _LOGGER.error("Battman themes in %s aren't loaded by Home Assistant (%d missing)", dst_dir(hass), len(missing))
    else:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_NOT_LOADED)
    return missing


async def async_reload(hass: HomeAssistant) -> None:
    """Ask HA to re-read themes. Never lets a failure stop anything else."""
    if not hass.services.has_service("frontend", "reload_themes"):
        return
    try:
        await hass.services.async_call("frontend", "reload_themes", blocking=True)
    except Exception as err:  # noqa: BLE001
        _LOGGER.error("Battman could not reload themes: %s", err)
