"""Battman binary sensors.

binary_sensor.battman_in_charge: always on. Battman's engine is the only engine, so it
always controls the battery. The engine automations and sensors still check it first (a
harmless always-true condition), and cards read it, so the entity stays. It can be
dropped in a later release once nothing references it.
"""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import device_info


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([BattmanInChargeSensor(entry)])


class BattmanInChargeSensor(BinarySensorEntity):
    """binary_sensor.battman_in_charge: always on."""

    _attr_has_entity_name = True
    _attr_translation_key = "in_charge"
    _attr_should_poll = False
    _attr_is_on = True
    _attr_icon = "mdi:battery-check"

    def __init__(self, entry: ConfigEntry) -> None:
        self._attr_unique_id = f"{entry.entry_id}_in_charge"
        self._attr_device_info = device_info(entry)
