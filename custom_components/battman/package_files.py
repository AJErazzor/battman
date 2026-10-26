"""Battman's YAML package files: custom_components/battman/packages/*.yaml.

Battman writes them into <config>/packages/battman/ (HA reads that folder when
configuration.yaml has `homeassistant: packages: !include_dir_named packages`), with
[[map:name]] markers filled from the entity map and [[factory:soc]] / [[factory:price]] from
factory_curves.yaml, then reloads template entities and helpers,
so no restart is needed. They're rewritten on every Battman update and whenever the entity
map changes. Files Battman no longer ships are removed from that folder.

Template sensors live here (not in Battman's code) so a Smiggles template sensor can be
renamed into Battman's and keep its history: same unique ID, same entity.

If HA isn't reading the folder (packages not set up), a Repair says what to add.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any

import yaml

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.reload import async_reload_integration_platforms
from homeassistant.setup import async_setup_component

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SRC = Path(__file__).parent / "packages"
DST_PARTS = ("packages", "battman")
MAP_MARK = re.compile(r"\[\[map:([a-z0-9_]+)\]\]")
FACTORY = Path(__file__).parent / "factory_curves.yaml"
FACTORY_MARK = re.compile(r"\[\[factory:([a-z]+)\]\]")
ISSUE = "packages_not_loaded"
# helper domains a package file may define (reloaded with template when the files change)
HELPER_DOMAINS = ("input_boolean", "input_number", "input_select", "timer")
# YAML sensor platforms a package file may use (`sensor: - platform: statistics`)
PLATFORM_DOMAINS = ("statistics",)


def dst_dir(hass: HomeAssistant) -> Path:
    return Path(hass.config.path(*DST_PARTS))


def factory_curves() -> dict[str, Any]:
    """Battman's factory curves (factory_curves.yaml): {"soc": {...}, "price": {...}}."""
    return yaml.safe_load(FACTORY.read_text(encoding="utf-8"))


def render(emap: dict[str, str]) -> dict[str, str]:
    """File name -> text with the map and the factory curves filled in.

    Raises KeyError on an unknown map entry or factory curve set.
    """
    factory = {k: json.dumps(v, separators=(",", ":")) for k, v in factory_curves().items()}
    out = {}
    for f in sorted(SRC.glob("*.yaml")):
        text = MAP_MARK.sub(lambda m: emap[m.group(1)], f.read_text(encoding="utf-8"))
        out[f.name] = FACTORY_MARK.sub(lambda m: factory[m.group(1)], text)
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


def remove_files(dst: Path) -> list[str]:
    """Battman removed: delete its package files (and the folder, if nothing else is in it)."""
    if not dst.is_dir():
        return []
    gone = []
    for f in sorted(dst.glob("*.yaml")):
        f.unlink()
        gone.append(f.name)
    try:
        dst.rmdir()
    except OSError:
        pass
    return gone


def entities(files: dict[str, str]) -> list[tuple[str, str, str]]:
    """(domain, platform, unique_id) of every entity the files define with a unique ID:
    template sensors / binary sensors / switches, and sensors from a YAML platform (e.g. statistics)."""
    out = []
    for text in files.values():
        data = yaml.safe_load(text) or {}
        for block in data.get("template", []):
            for domain in ("sensor", "binary_sensor", "switch"):
                for ent in block.get(domain, []) or []:
                    if "unique_id" in ent:
                        out.append((domain, "template", ent["unique_id"]))
        for ent in data.get("sensor", []) or []:
            if "unique_id" in ent and "platform" in ent:
                out.append(("sensor", ent["platform"], ent["unique_id"]))
    return out


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


async def _reload_all(hass: HomeAssistant) -> None:
    """Re-read everything the files define: helpers, template entities, YAML sensor platforms."""
    for domain in (*HELPER_DOMAINS, "template"):
        await _reload(hass, domain)
    # statistics only has a reload action once a YAML statistics sensor exists, so set its
    # sensor platform up (or again) the way that action does
    for platform in PLATFORM_DOMAINS:
        await async_reload_integration_platforms(hass, platform, ["sensor"])


@callback
def _retire_template_entries(hass: HomeAssistant, files: dict[str, str]) -> list[str]:
    """Remove registry entries of Battman template entities the files no longer define.

    A Battman entity that moves from a template to another platform (e.g. the load average,
    now a statistics sensor) keeps its entity ID that way: HA would otherwise give the new one
    a _2 name, because the old registry entry still holds it. Battman's template entities are
    the ones whose unique ID starts with battman_.
    """
    current = set(entities(files))
    reg = er.async_get(hass)
    stale = [
        e.entity_id
        for e in list(reg.entities.values())
        if e.platform == "template"
        and str(e.unique_id).startswith("battman_")
        and (e.domain, "template", e.unique_id) not in current
    ]
    for entity_id in stale:
        reg.async_remove(entity_id)
    if stale:
        _LOGGER.info("Battman removed registry entries of retired template entities: %s", stale)
    return stale


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
    reg = er.async_get(hass)

    def _missing() -> list[str]:
        out = [f"{d}.{uid}" for d, p, uid in entities(files) if not reg.async_get_entity_id(d, p, uid)]
        return out + [h for h in helper_ids if hass.states.get(h) is None]

    if changed or not hass.services.has_service("template", "reload") or _missing():
        _retire_template_entries(hass, files)
        await _reload_all(hass)
        _LOGGER.info("Battman packages written to %s and reloaded", dst_dir(hass))
    missing = _missing()
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
