"""Battman binary sensors.

binary_sensor.battman_in_charge: on when Battman's engine controls the battery.
Every Battman engine automation and engine sensor checks it first, so before you
migrate (or after Hand back) Battman's engine does nothing at all. Only Migrate from
Smiggles turns it on; only Hand back to Smiggles turns it off. It's stored in the
Battman config entry, so it survives restarts.
"""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import IN_CHARGE
from .entity import device_info


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([BattmanInChargeSensor(entry)])


class BattmanInChargeSensor(BinarySensorEntity):
    """binary_sensor.battman_in_charge"""

    _attr_has_entity_name = True
    _attr_translation_key = "in_charge"
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_in_charge"
        self._attr_device_info = device_info(entry)

    @property
    def is_on(self) -> bool:
        return bool(self._entry.data.get(IN_CHARGE))

    @property
    def icon(self) -> str:
        return "mdi:battery-check" if self.is_on else "mdi:battery-off-outline"

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._entry.add_update_listener(self._changed))

    async def _changed(self, _hass: HomeAssistant, _entry: ConfigEntry) -> None:
        self.async_write_ha_state()
