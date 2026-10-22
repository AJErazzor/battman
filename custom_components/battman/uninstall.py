"""Removing Battman: take away everything Battman wrote into your config.

Removed: Battman's engine and Live Activity automations and scripts (by their ids, from
automations.yaml / scripts.yaml), its package files (packages/battman/) and the entities
they made, its blueprints and its shipped themes.

Kept: the engine log (battman/engine.log), your own cards, images and themes
(battman/cards/, battman/images/, themes/battman/custom/), your Battman dashboard, and
everything else in automations.yaml / scripts.yaml.

A notification lists what was removed, and anything that couldn't be.
"""

from __future__ import annotations

import logging

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from . import automation_files, blueprint_install, engine, live_activity, package_files, themes

_LOGGER = logging.getLogger(__name__)

AUTOMATION_IDS = {a["id"] for a in (*engine.AUTOMATIONS, *live_activity.AUTOMATIONS)}
SCRIPT_IDS = {*engine.SCRIPTS, *live_activity.SCRIPTS}


async def _reload(hass: HomeAssistant, domain: str) -> None:
    if not hass.services.has_service(domain, "reload"):
        return
    try:
        await hass.services.async_call(domain, "reload", blocking=True)
    except Exception as err:  # noqa: BLE001  (removal carries on; the notification says so)
        _LOGGER.error("Battman couldn't reload %s while being removed: %s", domain, err)


async def async_remove(hass: HomeAssistant) -> None:
    from .api import entity_map  # noqa: PLC0415

    done: list[str] = []
    problems: list[str] = []
    reg = er.async_get(hass)

    # automations and scripts first: they're made from the blueprints removed below
    auto_path, script_path = automation_files.paths(hass)
    try:
        gone = await hass.async_add_executor_job(
            automation_files.remove, auto_path, script_path, AUTOMATION_IDS, SCRIPT_IDS
        )
    except automation_files.AutomationFileError as err:
        problems.append(f"automations and scripts: {err}")
    else:
        if gone:
            done.append(f"{len(gone)} automations and scripts: {', '.join(gone)}")
        for domain in ("automation", "script"):
            await _reload(hass, domain)
        for item in [*AUTOMATION_IDS, *SCRIPT_IDS]:
            domain = "script" if item in SCRIPT_IDS else "automation"
            if entity_id := reg.async_get_entity_id(domain, domain, item):
                reg.async_remove(entity_id)

    # the package files, then the entities they made
    try:
        files = await hass.async_add_executor_job(package_files.render, entity_map(hass))
        made = package_files.entities(files)
        gone = await hass.async_add_executor_job(package_files.remove_files, package_files.dst_dir(hass))
    except (OSError, KeyError) as err:
        problems.append(f"packages/battman/: {err}")
    else:
        if gone:
            done.append(f"packages/battman/ ({len(gone)} files)")
        for domain in (*package_files.HELPER_DOMAINS, "template", *package_files.PLATFORM_DOMAINS):
            await _reload(hass, domain)
        for domain, platform, unique_id in made:
            if entity_id := reg.async_get_entity_id(domain, platform, unique_id):
                reg.async_remove(entity_id)

    await blueprint_install.async_remove(hass)
    done.append("Battman's blueprints")
    if await hass.async_add_executor_job(themes.remove_shipped, themes.dst_dir(hass)):
        await themes.async_reload(hass)
        done.append("Battman's shipped themes")

    lines = ["Removed: " + "; ".join(done) + "."]
    if problems:
        lines.append("Couldn't remove: " + "; ".join(problems) + ". Remove these by hand.")
    lines.append(
        "Kept: the engine log (battman/engine.log), your own cards, images and themes, "
        "and your Battman dashboard."
    )
    message = "\n\n".join(lines)
    _LOGGER.info("Battman removed. %s", message.replace("\n\n", " "))
    persistent_notification.async_create(
        hass, message, title="Battman removed", notification_id="battman_removed"
    )
