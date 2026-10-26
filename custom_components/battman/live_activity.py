"""Create the Battman Live Activity automations and script.

They're made from Battman's blueprints and written into automations.yaml and
scripts.yaml, exactly as if you'd made them from the blueprints in HA's editor.
Their settings live in Battman entities (Settings → Live Activity on the Battman
dashboard), so nothing personal is in them.

Rules:
- Battman creates them once, on first start after installing/updating.
- After that they're yours: Battman never edits or overwrites one that exists.
- "Create Live Activity automations" (button / battman.create_live_activity)
  creates any that are missing. To reset one: delete it, then press the button.

They're written into automations.yaml / scripts.yaml (automation_files.py), then
reloaded. If they don't load (e.g. automations.yaml isn't included in
configuration.yaml), a Repair says so.

Settings: since v0.26.0 they're attributes of sensor.battman_parameters (liveActivity*), like
every other Battman setting, and the on/off switch is a template switch in Battman's packages.
Before that they were six Battman entities (a switch, a phone select, three texts, two
numbers): on the first start after updating, their last values are carried over into the
parameters sensor and the old entities are removed (retire_old_settings).
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.restore_state import async_get as restore_state

from . import automation_files
from .const import DOMAIN, ENGINE_MAP

_LOGGER = logging.getLogger(__name__)

ISSUE_NOT_LOADED = "live_activity_not_loaded"
NOTE = (
    "Made by Battman from its blueprint. Settings are on the Battman dashboard "
    "(Settings → Live Activity). Edit freely: Battman won't overwrite it. "
    "Delete it and press 'Create Live Activity automations' on the Battman device to get Battman's version back."
)

SCRIPTS: dict[str, dict[str, Any]] = {
    "battman_live_activity_push": {
        "alias": "Battman Live Activity – push",
        "description": NOTE,
        "use_blueprint": {"path": "battman/battman_live_activity_push.yaml", "input": {}},
    },
}
AUTOMATIONS: list[dict[str, Any]] = [
    {
        "id": f"battman_live_activity_{name}",
        "alias": f"Battman Live Activity – {title}",
        "description": NOTE,
        "use_blueprint": {"path": f"battman/battman_live_activity_{name}.yaml", "input": {}},
    }
    for name, title in (("on_off", "on/off"), ("updates", "updates"), ("follow", "follow"))
]


class LiveActivityError(Exception):
    """automations.yaml / scripts.yaml couldn't be read or written."""


def _missing_after_load(hass: HomeAssistant, ids: list[str]) -> list[str]:
    reg = er.async_get(hass)
    missing = []
    for item in ids:
        domain = "script" if item in SCRIPTS else "automation"
        if reg.async_get_entity_id(domain, domain, item) is None:
            missing.append(item)
    return missing


async def _reload_and_check(hass: HomeAssistant, added: list[str]) -> None:
    for domain in ("script", "automation"):
        if hass.services.has_service(domain, "reload"):
            await hass.services.async_call(domain, "reload", blocking=True)
    if missing := _missing_after_load(hass, added):
        ir.async_create_issue(
            hass,
            DOMAIN,
            ISSUE_NOT_LOADED,
            is_fixable=False,
            severity=ir.IssueSeverity.ERROR,
            translation_key=ISSUE_NOT_LOADED,
            translation_placeholders={"missing": ", ".join(missing)},
        )
        _LOGGER.error("Battman wrote %s but Home Assistant didn't load them", missing)
    else:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_NOT_LOADED)


async def async_create_missing(hass: HomeAssistant) -> dict[str, list[str]]:
    """Create any missing Live Activity automations/script. {"created": [...], "existing": [...]}."""
    auto_path, script_path = automation_files.paths(hass)
    try:
        added = await hass.async_add_executor_job(
            automation_files.write_missing, auto_path, script_path, AUTOMATIONS, SCRIPTS
        )
    except automation_files.AutomationFileError as err:
        raise LiveActivityError(str(err)) from err
    every = [*SCRIPTS, *(a["id"] for a in AUTOMATIONS)]
    if added:
        _LOGGER.info("Battman created Live Activity automations/script: %s", ", ".join(added))
        if hass.state is CoreState.running:
            await _reload_and_check(hass, added)
        else:
            async def _later(_event: Event) -> None:
                await _reload_and_check(hass, added)

            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _later)
    return {"created": added, "existing": [i for i in every if i not in added]}


# The Live Activity settings before v0.26.0: (domain, unique ID key) -> (parameters attribute, value)
OLD_SETTINGS: dict[tuple[str, str], tuple[str, Any]] = {
    ("switch", "live_activity"): ("liveActivity", lambda s: s == "on"),
    ("select", "live_activity_phone"): ("liveActivityPhone", str),
    ("text", "live_activity_follow"): ("liveActivityFollow", str),
    ("text", "live_activity_follow_on"): ("liveActivityFollowOn", str),
    ("text", "live_activity_follow_off"): ("liveActivityFollowOff", str),
    ("number", "live_activity_follow_delay"): ("liveActivityFollowDelay", lambda s: int(float(s))),
    ("number", "live_activity_spike_alert"): ("liveActivitySpikeAlert", float),
}


@callback
def retire_old_settings(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Read the old Live Activity entities' last values and remove the entities (so the template
    switch can take switch.battman_live_activity). Returns parameters attribute -> value."""
    reg = er.async_get(hass)
    last = restore_state(hass).last_states
    values: dict[str, Any] = {}
    for (domain, key), (attr, convert) in OLD_SETTINGS.items():
        entity_id = reg.async_get_entity_id(domain, DOMAIN, f"{entry.entry_id}_{key}")
        if entity_id is None:
            continue
        stored = last.get(entity_id)
        if stored is not None and stored.state.state not in ("unknown", "unavailable"):
            try:
                values[attr] = convert(stored.state.state)
            except (TypeError, ValueError):
                _LOGGER.warning("Battman Live Activity: couldn't read %s (%s)", entity_id, stored.state.state)
        reg.async_remove(entity_id)
    return values


@callback
def async_carry_over(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Move the old Live Activity settings into the parameters sensor, once its package is loaded."""
    values = retire_old_settings(hass, entry)
    if not values:
        return
    from . import package_files  # noqa: PLC0415

    async def _apply(*_args) -> None:
        await package_files.async_sync(hass)          # the parameters sensor and the switch are loaded
        if hass.states.get("binary_sensor.battman_in_charge") is None or \
                hass.states.get("binary_sensor.battman_in_charge").state != "on":
            _LOGGER.warning("Battman Live Activity: your settings %s couldn't be carried over: Battman "
                            "isn't in charge, and its settings only change while it is", values)
            return
        hass.bus.async_fire(ENGINE_MAP["parameters_update_event"], {"action": "SetAttribute", **values})
        _LOGGER.info("Battman Live Activity: settings carried over into its parameters: %s", values)

    if hass.state is CoreState.running:
        hass.async_create_task(_apply())
    else:
        entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _apply))
