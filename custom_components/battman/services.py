"""Battman actions."""

from __future__ import annotations

from homeassistant.components import persistent_notification

from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.helpers import issue_registry as ir

from . import dashboard, engine, notifications
from .const import DOMAIN

SERVICE_CREATE_DASHBOARD = "create_dashboard"
SERVICE_CREATE_AUTOMATIONS = "create_automations"
SERVICE_CREATE_HELP_VIEW = "create_help_view"
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


def _help_message(outcome: str, url_path: str) -> str:
    if outcome == dashboard.ADDED:
        return (f"Added the Help view to your Battman dashboard at /{url_path}. It's the last tab; "
                "nothing else on the dashboard changed.")
    if outcome == dashboard.EXISTS:
        return f"Your Battman dashboard already has a Help view (/{url_path}/{dashboard.HELP_PATH}), so nothing changed."
    if outcome == dashboard.NO_DASHBOARD:
        return (f"There's no Battman dashboard at /{url_path}, so nothing changed. Press Create dashboard on "
                "the Battman device: a new Battman dashboard includes the Help view.")
    return (f"Battman can't change the dashboard at /{url_path} (it's written in YAML, or it has no saved views "
            "yet), so nothing changed. To add the Help view yourself, add a view to it with the card "
            "type: custom:battman-guide.")


async def async_create_help_view_and_report(hass: HomeAssistant, notify: bool) -> dict:
    """Add the Help view to the Battman dashboard if it hasn't one, and say what happened."""
    try:
        outcome, url_path = await dashboard.async_add_help_view(hass)
    except dashboard.DashboardUnavailable as err:
        result = {"added": False, "outcome": "error", "url_path": dashboard.BASE_URL_PATH,
                  "message": f"Could not add the Help view: {err}"}
    else:
        result = {"added": outcome == dashboard.ADDED, "outcome": outcome, "url_path": url_path,
                  "message": _help_message(outcome, url_path)}
    if notify:
        persistent_notification.async_create(
            hass, result["message"], title="Battman help view", notification_id="battman_help_view"
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

    hass.services.async_register(
        DOMAIN, SERVICE_CREATE_DASHBOARD, _create, supports_response=SupportsResponse.OPTIONAL
    )

    async def _create_automations(call: ServiceCall) -> ServiceResponse:
        result = await async_create_automations_and_report(hass, notify=not call.return_response)
        return result if call.return_response else None

    hass.services.async_register(
        DOMAIN, SERVICE_CREATE_AUTOMATIONS, _create_automations, supports_response=SupportsResponse.OPTIONAL
    )

    async def _create_help_view(call: ServiceCall) -> ServiceResponse:
        result = await async_create_help_view_and_report(hass, notify=not call.return_response)
        return result if call.return_response else None

    hass.services.async_register(
        DOMAIN, SERVICE_CREATE_HELP_VIEW, _create_help_view, supports_response=SupportsResponse.OPTIONAL
    )
