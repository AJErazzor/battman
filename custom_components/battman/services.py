"""Battman actions."""

from __future__ import annotations

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.helpers import issue_registry as ir

from . import dashboard
from .const import DOMAIN

SERVICE_CREATE_DASHBOARD = "create_dashboard"
ISSUE_DASHBOARD = "dashboard_unavailable"


async def async_create_dashboard_and_report(hass: HomeAssistant, notify: bool) -> dict:
    """Create the managed dashboard if needed and say what happened."""
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
            f"Created the Battman dashboard at /{url_path}."
            if created
            else f"A managed Battman dashboard already exists at /{url_path}; nothing changed."
        )
        result = {"created": created, "url_path": url_path, "message": message}
    if notify:
        persistent_notification.async_create(
            hass, result["message"], title="Battman dashboard", notification_id="battman_dashboard"
        )
    return result


def async_register_services(hass: HomeAssistant) -> None:
    async def _create(call: ServiceCall) -> ServiceResponse:
        result = await async_create_dashboard_and_report(hass, notify=not call.return_response)
        return result if call.return_response else None

    hass.services.async_register(
        DOMAIN, SERVICE_CREATE_DASHBOARD, _create, supports_response=SupportsResponse.OPTIONAL
    )
