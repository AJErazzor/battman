"""Shared bits for Battman's entities."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .const import DOMAIN


def device_info(entry: ConfigEntry) -> DeviceInfo:
    """The Battman device every Battman entity sits on."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Battman",
        manufacturer="Battman",
        entry_type=DeviceEntryType.SERVICE,
    )
