"""Battman switches.

Live Activity: the on/off switch the Battman Live Activity blueprints hang off
(push while on, clear when turned off, keep-alive restart). Anything can flip it:
you, the dashboard, or the "follow an entity" blueprint (e.g. a car's ignition).
It keeps its state across restarts.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([BattmanLiveActivitySwitch(entry)])


class BattmanLiveActivitySwitch(SwitchEntity, RestoreEntity):
    """switch.battman_live_activity"""

    _attr_has_entity_name = True
    _attr_translation_key = "live_activity"
    _attr_icon = "mdi:cellphone-information"
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry) -> None:
        self._attr_unique_id = f"{entry.entry_id}_live_activity"
        self._attr_is_on = False
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Battman",
            manufacturer="Battman",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        if (last := await self.async_get_last_state()) is not None:
            self._attr_is_on = last.state == STATE_ON

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._attr_is_on = False
        self.async_write_ha_state()
