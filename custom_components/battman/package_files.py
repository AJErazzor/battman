"""Battman's YAML package files: custom_components/battman/packages/*.yaml.

Battman writes them into <config>/packages/battman/ (HA reads that folder when
configuration.yaml has `homeassistant: packages: !include_dir_named packages`), with
[[map:name]] markers filled from the entity map, then reloads template entities and helpers,
so no restart is needed. They're rewritten on every Battman update and whenever the entity
map changes. Files Battman no longer ships are removed from that folder.

Template sensors live here (not in Battman's code) so a Smiggles template sensor can be
renamed into Battman's and keep its history: same unique ID, same entity.

If HA isn't reading the folder (packages not set up), a Repair says what to add.
"""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path

import yaml

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SRC = Path(__file__).parent / "packages"
DST_PARTS = ("packages", "battman")
MAP_MARK = re.compile(r"\[\[map:([a-z0-9_]+)\]\]")
ISSUE = "packages_not_loaded"
# helper domains a package file may define (reloaded with template when the files change)
HELPER_DOMAINS = ("input_boolean", "input_number", "input_select", "timer")


def dst_dir(hass: HomeAssistant) -> Path:
    return Path(hass.config.path(*DST_PARTS))


def render(emap: dict[str, str]) -> dict[str, str]:
    """File name -> text with the map filled in. Raises KeyError on an unknown map entry."""
    out = {}
    for f in sorted(SRC.glob("*.yaml")):
        out[f.name] = MAP_MARK.sub(lambda m: emap[m.group(1)], f.read_text(encoding="utf-8"))
    return out


def write(dst: Path, files: dict[str, str]) -> bool:
    """Write the files that differ, remove ones Battman no longer ships. True if anything changed."""
    dst.mkdir(parents=True, exist_ok=True)
    changed = False
    for name, text in files.items():
        target = dst / name
        if not target.exists() or target.read_text(encoding="utf-8") != text:
            target.write_text(text, encoding="utf-8")
            changed = True
    for old in dst.glob("*.yaml"):
        if old.name not in files:
            old.unlink()
            changed = True
    return changed


def unique_ids(files: dict[str, str]) -> list[tuple[str, str]]:
    """(domain, unique_id) of every template entity in the files."""
    ids = []
    for text in files.values():
        for block in (yaml.safe_load(text) or {}).get("template", []):
            for domain in ("sensor", "binary_sensor"):
                for ent in block.get(domain, []) or []:
                    if "unique_id" in ent:
                        ids.append((domain, ent["unique_id"]))
    return ids


def helpers(files: dict[str, str]) -> list[str]:
    """Entity IDs of the helpers (input_boolean, timer, ...) the files define."""
    out = []
    for text in files.values():
        for domain, items in (yaml.safe_load(text) or {}).items():
            if domain in HELPER_DOMAINS:
                out += [f"{domain}.{object_id}" for object_id in items]
    return out


async def _reload(hass: HomeAssistant, domain: str) -> None:
    if not hass.services.has_service(domain, "reload"):
        await async_setup_component(hass, domain, {})
    if hass.services.has_service(domain, "reload"):
        await hass.services.async_call(domain, "reload", blocking=True)


async def async_sync(hass: HomeAssistant) -> list[str]:
    """Write the packages, reload what they define, check it loaded. Returns missing entities.

    One at a time: a second sync waits, so it never checks while the first is reloading.
    """
    lock = hass.data.setdefault(f"{DOMAIN}_packages_lock", asyncio.Lock())
    async with lock:
        return await _sync(hass)


async def _sync(hass: HomeAssistant) -> list[str]:
    from .api import entity_map  # noqa: PLC0415

    files = await hass.async_add_executor_job(render, entity_map(hass))
    changed = await hass.async_add_executor_job(write, dst_dir(hass), files)
    helper_ids = helpers(files)
    if changed or not hass.services.has_service("template", "reload") or any(
        hass.states.get(h) is None for h in helper_ids
    ):
        for domain in (*HELPER_DOMAINS, "template"):
            await _reload(hass, domain)
        _LOGGER.info("Battman packages written to %s and reloaded", dst_dir(hass))
    reg = er.async_get(hass)
    missing = [f"{d}.{uid}" for d, uid in unique_ids(files) if not reg.async_get_entity_id(d, "template", uid)]
    missing += [h for h in helper_ids if hass.states.get(h) is None]
    if missing:
        ir.async_create_issue(
            hass, DOMAIN, ISSUE, is_fixable=False, severity=ir.IssueSeverity.ERROR, translation_key=ISSUE,
            translation_placeholders={"folder": "/".join(DST_PARTS), "missing": ", ".join(missing)},
        )
        _LOGGER.error("Battman packages in %s aren't loaded by Home Assistant: %s", dst_dir(hass), missing)
    else:
        ir.async_delete_issue(hass, DOMAIN, ISSUE)
    return missing


@callback
def async_start(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Sync once HA has started, and again whenever the entity map (Configure) changes."""

    async def _sync(*_args) -> None:
        try:
            await async_sync(hass)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Battman couldn't write its packages")

    if hass.state is CoreState.running:
        hass.async_create_task(_sync())
    else:
        entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _sync))

    async def _options(_hass: HomeAssistant, _entry: ConfigEntry) -> None:
        await _sync()

    entry.async_on_unload(entry.add_update_listener(_options))
