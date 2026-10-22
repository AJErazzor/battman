"""Battman actions."""

from __future__ import annotations

from homeassistant.components import persistent_notification
import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import issue_registry as ir

from . import dashboard, live_activity, migrate
from .const import DOMAIN

SERVICE_CREATE_DASHBOARD = "create_dashboard"
SERVICE_CREATE_LIVE_ACTIVITY = "create_live_activity"
SERVICE_MIGRATE = "migrate_from_smiggles"
SERVICE_HAND_BACK = "hand_back_to_smiggles"
CONFIRM_SCHEMA = vol.Schema({vol.Optional("confirm", default=False): cv.boolean})
ISSUE_DASHBOARD = "dashboard_unavailable"


async def async_create_dashboard_and_report(hass: HomeAssistant, notify: bool) -> dict:
    """Create the Battman dashboard if /battman is free and say what happened."""
    try:
        created, url_path = await dashboard.async_create(hass)
    except dashboard.DashboardUnavailable as err:
        ir.async_create_issue(
            hass,
            DOMAIN,
            ISSUE_DASHBOARD,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_DASHBOARD,
            translation_placeholders={"error": str(err)},
        )
        result = {"created": False, "url_path": None, "message": f"Could not create the Battman dashboard: {err}"}
    else:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_DASHBOARD)
        message = (
            f"Created the Battman dashboard at /{url_path}. It's yours: edit it like any dashboard."
            if created
            else f"There's already a dashboard at /{url_path}, so nothing was created. "
            "For a fresh Battman dashboard, delete that one first."
        )
        result = {"created": created, "url_path": url_path, "message": message}
    if notify:
        persistent_notification.async_create(
            hass, result["message"], title="Battman dashboard", notification_id="battman_dashboard"
        )
    return result


async def async_create_live_activity_and_report(hass: HomeAssistant, notify: bool) -> dict:
    """Create any missing Live Activity automations/script and say what happened."""
    try:
        result = await live_activity.async_create_missing(hass)
    except live_activity.LiveActivityError as err:
        result = {"created": [], "existing": [], "message": f"Could not create the Live Activity automations: {err}"}
    else:
        if result["created"]:
            result["message"] = "Created: " + ", ".join(result["created"]) + "."
        else:
            result["message"] = "All Live Activity automations and the script already exist; nothing changed."
    if notify:
        persistent_notification.async_create(
            hass, result["message"], title="Battman Live Activity", notification_id="battman_live_activity"
        )
    return result


def async_register_services(hass: HomeAssistant) -> None:
    async def _create(call: ServiceCall) -> ServiceResponse:
        result = await async_create_dashboard_and_report(hass, notify=not call.return_response)
        return result if call.return_response else None

    hass.services.async_register(
        DOMAIN, SERVICE_CREATE_DASHBOARD, _create, supports_response=SupportsResponse.OPTIONAL
    )

    async def _create_live(call: ServiceCall) -> ServiceResponse:
        result = await async_create_live_activity_and_report(hass, notify=not call.return_response)
        return result if call.return_response else None

    hass.services.async_register(
        DOMAIN, SERVICE_CREATE_LIVE_ACTIVITY, _create_live, supports_response=SupportsResponse.OPTIONAL
    )

    def _entry():
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            raise migrate.MigrateError("Battman isn't set up")
        return entries[0]

    async def _migrate(call: ServiceCall) -> ServiceResponse:
        entry = _entry()
        if not call.data["confirm"]:
            # dry run: what would happen, nothing changed
            return {"dry_run": True, **migrate.preview(hass, entry)}
        report = await migrate.async_migrate(hass, entry)
        persistent_notification.async_create(
            hass,
            "Battman is now in charge of the battery. Smiggles' automations are off "
            f"({len(report['turned_off'])} turned off) and its values are copied into Battman. "
            "To go back: action battman.hand_back_to_smiggles.",
            title="Battman: migrated from Smiggles",
            notification_id="battman_migrate",
        )
        return {"dry_run": False, **report}

    hass.services.async_register(
        DOMAIN, SERVICE_MIGRATE, _migrate, schema=CONFIRM_SCHEMA, supports_response=SupportsResponse.OPTIONAL
    )

    async def _hand_back(call: ServiceCall) -> ServiceResponse:
        entry = _entry()
        if not call.data["confirm"]:
            return {
                "dry_run": True,
                "would_turn_on": entry.data.get(migrate.WAS_ON, []),
                "would_copy_back": [f"{a} → {b}" for _k, a, b in migrate._pairs(migrate.HAND_BACK_SENSOR_KEYS, True)]
                + [f"{a} → {b}" for _k, a, b in migrate._pairs(migrate.HELPER_KEYS, True)],
            }
        report = await migrate.async_hand_back(hass, entry)
        persistent_notification.async_create(
            hass,
            "Smiggles is back in charge of the battery. Battman's engine is off "
            f"and {len(report['turned_on'])} Smiggles automations are back on.",
            title="Battman: handed back to Smiggles",
            notification_id="battman_migrate",
        )
        return {"dry_run": False, **report}

    hass.services.async_register(
        DOMAIN, SERVICE_HAND_BACK, _hand_back, schema=CONFIRM_SCHEMA, supports_response=SupportsResponse.OPTIONAL
    )
