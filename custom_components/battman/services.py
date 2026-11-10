"""Battman actions."""

from __future__ import annotations

from homeassistant.components import persistent_notification

from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.service import async_register_admin_service

from . import dashboard, engine, notifications
from .const import DOMAIN

SERVICE_CREATE_DASHBOARD = "create_dashboard"
SERVICE_CREATE_AUTOMATIONS = "create_automations"
ISSUE_DASHBOARD = "dashboard_unavailable"
ISSUES_URL = "https://github.com/AJErazzor/battman/issues"


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
            translation_placeholders={"error": str(err), "issues_url": ISSUES_URL},
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


async def async_create_automations_and_report(hass: HomeAssistant, notify: bool) -> dict:
    """Create any missing Battman automations and scripts (notifications, then the engine) and say what happened."""
    created: list[str] = []
    problems: list[str] = []
    try:
        created += (await notifications.async_create_missing(hass))["created"]
    except notifications.NotificationsError as err:
        problems.append(str(err))
    try:
        created += await engine.async_create_missing(hass)
    except engine.EngineError as err:
        problems.append(str(err))
    if problems:
        message = "Could not create the Battman automations: " + "; ".join(problems)
    elif created:
        message = "Created: " + ", ".join(created) + "."
    else:
        message = "All Battman automations and scripts already exist; nothing changed."
    result = {"created": created, "message": message}
    if notify:
        persistent_notification.async_create(
            hass, message, title="Battman automations", notification_id="battman_automations"
        )
    return result


def async_register_services(hass: HomeAssistant) -> None:
    async def _create(call: ServiceCall) -> ServiceResponse:
        result = await async_create_dashboard_and_report(hass, notify=not call.return_response)
        return result if call.return_response else None

    # admin only, like editing a dashboard or the automations in Home Assistant itself (a script or automation
    # with no user behind it can still run them)
    async_register_admin_service(
        hass, DOMAIN, SERVICE_CREATE_DASHBOARD, _create, supports_response=SupportsResponse.OPTIONAL
    )

    async def _create_automations(call: ServiceCall) -> ServiceResponse:
        result = await async_create_automations_and_report(hass, notify=not call.return_response)
        return result if call.return_response else None

    async_register_admin_service(
        hass, DOMAIN, SERVICE_CREATE_AUTOMATIONS, _create_automations, supports_response=SupportsResponse.OPTIONAL
    )
