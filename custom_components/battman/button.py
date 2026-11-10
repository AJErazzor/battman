"""Battman buttons."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import device_info
from .services import async_create_automations_and_report, async_create_dashboard_and_report


async def _require_admin(button: ButtonEntity) -> None:
    """Only an administrator can press Battman's buttons (a script or automation with no user behind it can)."""
    user_id = button._context.user_id if button._context else None
    if user_id is None:
        return
    user = await button.hass.auth.async_get_user(user_id)
    if user is None or not user.is_admin:
        raise HomeAssistantError(translation_domain=DOMAIN, translation_key="admin_only")


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    # Create help view is gone (Settings → Dashboard options → Show help does it): its registry entry goes too
    reg = er.async_get(hass)
    if old := reg.async_get_entity_id("button", DOMAIN, f"{entry.entry_id}_create_help_view"):
        reg.async_remove(old)
    async_add_entities([BattmanCreateDashboardButton(entry), BattmanCreateAutomationsButton(entry)])


class BattmanCreateDashboardButton(ButtonEntity):
    """Create the Battman dashboard at /battman (does nothing if /battman is taken)."""

    _attr_has_entity_name = True
    _attr_translation_key = "create_dashboard"
    _attr_icon = "mdi:view-dashboard-edit"

    def __init__(self, entry: ConfigEntry) -> None:
        self._attr_unique_id = f"{entry.entry_id}_create_dashboard"
        self._attr_device_info = device_info(entry)

    async def async_press(self) -> None:
        await _require_admin(self)
        await async_create_dashboard_and_report(self.hass, notify=True)


class BattmanCreateAutomationsButton(ButtonEntity):
    """Create any missing Battman automations and scripts (never touches existing ones)."""

    _attr_has_entity_name = True
    _attr_translation_key = "create_automations"
    _attr_icon = "mdi:robot-outline"

    def __init__(self, entry: ConfigEntry) -> None:
        self._attr_unique_id = f"{entry.entry_id}_create_automations"
        self._attr_device_info = device_info(entry)

    async def async_press(self) -> None:
        await _require_admin(self)
        await async_create_automations_and_report(self.hass, notify=True)
