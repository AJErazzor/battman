"""Battman number settings for the Live Activity."""

from __future__ import annotations

from homeassistant.components.number import NumberMode, RestoreNumber
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import device_info

NUMBERS = (
    # key, default, min, max, step, unit, icon
    ("live_activity_follow_delay", 2, 0, 60, 1, UnitOfTime.MINUTES, "mdi:timer-sand"),
    ("live_activity_spike_alert", 0.30, 0, 20, 0.01, "$/kWh", "mdi:flash-alert"),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([BattmanSettingNumber(entry, *n) for n in NUMBERS])


class BattmanSettingNumber(RestoreNumber):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_should_poll = False

    def __init__(self, entry, key, default, vmin, vmax, step, unit, icon) -> None:
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = device_info(entry)
        self._attr_native_value = default
        self._attr_native_min_value = vmin
        self._attr_native_max_value = vmax
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon

    async def async_added_to_hass(self) -> None:
        if (last := await self.async_get_last_number_data()) is not None and last.native_value is not None:
            self._attr_native_value = last.native_value

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()
