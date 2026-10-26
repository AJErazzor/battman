"""Battman sensors.

The NEM sensors (nem.py), made while the OpenNEM integration is installed. The theme mode
colours sensor is a template sensor in Battman's packages since v0.26.0 (the browser works the
colours out: see battman-lib.js); its old registry entry is removed here so the template one
keeps sensor.battman_theme_mode_colours.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import nem
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    reg = er.async_get(hass)
    if old := reg.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_theme_mode_colours"):
        reg.async_remove(old)          # before v0.26.0: a Python sensor
    nem.async_setup(hass, entry, async_add_entities)
