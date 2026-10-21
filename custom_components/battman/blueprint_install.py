"""Battman blueprints: shipped in this integration, installed into your config.

<config>/blueprints/automation/battman/   Battman's automation blueprints
<config>/blueprints/script/battman/       Battman's script blueprints

Battman replaces these files on every update (files it no longer ships are
removed), then reloads automations and scripts so ones made from them pick up
the new version. [[map:name]] markers in them (the engine's Sigen / Amber / Solcast
entities) are filled from the entity map, and they're rewritten when the map changes.
Your own automations and scripts made from them are yours;
Battman never edits those. If you want to change a blueprint itself, copy it to
another folder first, or take control of the automation.
"""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, Event, HomeAssistant

_LOGGER = logging.getLogger(__name__)

SRC = Path(__file__).parent / "blueprints"
DOMAINS = ("automation", "script")
MAP_MARK = re.compile(r"\[\[map:([a-z0-9_]+)\]\]")


def dst_dir(hass: HomeAssistant, domain: str) -> Path:
    return Path(hass.config.path("blueprints", domain, "battman"))


def install(hass_config_dirs: dict[str, Path], emap: dict[str, str] | None = None) -> list[str]:
    """Write shipped blueprints (map filled) into each domain's battman folder. Returns the domains that changed.

    Raises KeyError naming an unknown map entry.
    """
    emap = emap or {}
    changed: list[str] = []
    for domain, dst in hass_config_dirs.items():
        shipped = {f.name: f for f in (SRC / domain).glob("*.yaml")}
        dst.mkdir(parents=True, exist_ok=True)
        did = False
        for name, src in shipped.items():
            target = dst / name
            data = MAP_MARK.sub(lambda m: emap[m.group(1)], src.read_text(encoding="utf-8")).encode("utf-8")
            if not target.exists() or target.read_bytes() != data:
                target.write_bytes(data)
                did = True
        for old in dst.glob("*.yaml"):
            if old.name not in shipped:
                old.unlink()
                did = True
        if did:
            changed.append(domain)
    return changed


def remove_shipped(hass_config_dirs: dict[str, Path]) -> bool:
    """Battman removed: delete its blueprints (automations made from them will show an error)."""
    removed = False
    for dst in hass_config_dirs.values():
        if not dst.exists():
            continue
        for f in dst.glob("*.yaml"):
            f.unlink()
            removed = True
        try:
            dst.rmdir()
        except OSError:
            pass
    return removed


async def async_install(hass: HomeAssistant) -> None:
    """Install (one at a time, so an older map never overwrites a newer one)."""
    lock = hass.data.setdefault("battman_blueprints_lock", asyncio.Lock())
    async with lock:
        await _install(hass)


async def _install(hass: HomeAssistant) -> None:
    from .api import entity_map  # noqa: PLC0415

    dirs = {d: dst_dir(hass, d) for d in DOMAINS}
    try:
        changed = await hass.async_add_executor_job(install, dirs, entity_map(hass))
    except (OSError, KeyError) as err:
        _LOGGER.error("Could not install Battman blueprints: %s", err)
        return
    if not changed:
        return
    _LOGGER.info("Battman blueprints installed/updated: %s", ", ".join(changed))

    async def _reload(_event: Event | None = None) -> None:
        for domain in changed:
            if hass.services.has_service(domain, "reload"):
                try:
                    await hass.services.async_call(domain, "reload", blocking=True)
                except Exception as err:  # noqa: BLE001
                    _LOGGER.error("Battman could not reload %s after updating blueprints: %s", domain, err)

    if hass.state is CoreState.running:
        await _reload()
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _reload)


async def async_remove(hass: HomeAssistant) -> None:
    dirs = {d: dst_dir(hass, d) for d in DOMAINS}
    await hass.async_add_executor_job(remove_shipped, dirs)
