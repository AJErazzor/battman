"""Check the other integrations' entities Battman uses by name are there.

Battman's engine, packages and cards name these entities directly (no entity map), so if
one is missing (integration not installed, entity disabled or renamed) a Repair names it.
Checked once Home Assistant has started, and again whenever the entity registry changes.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN

ISSUE_MISSING = "missing_entities"

# entity -> (what Battman uses it for, the integration that provides it)
REQUIRED: dict[str, tuple[str, str]] = {
    "sensor.solcast_pv_forecast_forecast_today": ("solar forecast today", "Solcast PV Forecast"),
    "sensor.solcast_pv_forecast_forecast_tomorrow": ("solar forecast tomorrow", "Solcast PV Forecast"),
    "sensor.solcast_pv_forecast_forecast_remaining_today": ("solar still to come today", "Solcast PV Forecast"),
}


def missing(hass: HomeAssistant) -> dict[str, str]:
    """entity -> 'not found' / 'disabled', for each required entity that isn't usable."""
    reg = er.async_get(hass)
    out: dict[str, str] = {}
    for entity_id in REQUIRED:
        entry = reg.async_get(entity_id)
        if entry is not None and entry.disabled_by is not None:
            out[entity_id] = "disabled"
        elif entry is None and hass.states.get(entity_id) is None:
            out[entity_id] = "not found"
    return out


@callback
def async_check(hass: HomeAssistant) -> dict[str, str]:
    """Raise (or clear) the missing-entities Repair. Returns what's missing."""
    gone = missing(hass)
    if gone:
        ir.async_create_issue(
            hass, DOMAIN, ISSUE_MISSING, is_fixable=False, severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_MISSING,
            translation_placeholders={"missing": "\n".join(
                f"- `{e}` ({REQUIRED[e][0]}, from {REQUIRED[e][1]}): {why}" for e, why in gone.items())},
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_MISSING)
    return gone


@callback
def async_start(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Check once HA has started (other integrations are loaded by then), and on registry changes."""

    @callback
    def _check(_event: Event | None = None) -> None:
        async_check(hass)

    if hass.state is CoreState.running:
        _check()
    else:
        entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _check))
    entry.async_on_unload(hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, _check))
