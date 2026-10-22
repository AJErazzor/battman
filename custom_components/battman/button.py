"""Battman buttons."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import device_info
from .services import async_create_dashboard_and_report, async_create_live_activity_and_report


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([BattmanCreateDashboardButton(entry), BattmanCreateLiveActivityButton(entry)])


class BattmanCreateDashboardButton(ButtonEntity):
    """Create the Battman dashboard at /battman (does nothing if /battman is taken)."""

    _attr_has_entity_name = True
    _attr_translation_key = "create_dashboard"
    _attr_icon = "mdi:view-dashboard-edit"

    def __init__(self, entry: ConfigEntry) -> None:
        self._attr_unique_id = f"{entry.entry_id}_create_dashboard"
        self._attr_device_info = device_info(entry)

    async def async_press(self) -> None:
        await async_create_dashboard_and_report(self.hass, notify=True)


class BattmanCreateLiveActivityButton(ButtonEntity):
    """Create any missing Live Activity automations/script (never touches existing ones)."""

    _attr_has_entity_name = True
    _attr_translation_key = "create_live_activity"
    _attr_icon = "mdi:cellphone-cog"

    def __init__(self, entry: ConfigEntry) -> None:
        self._attr_unique_id = f"{entry.entry_id}_create_live_activity"
        self._attr_device_info = device_info(entry)

    async def async_press(self) -> None:
        await async_create_live_activity_and_report(self.hass, notify=True)
