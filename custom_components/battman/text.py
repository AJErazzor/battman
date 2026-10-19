"""Battman text settings for the Live Activity "follow an entity" automation.

Follow: the entity to follow (blank = don't follow). If it doesn't exist, the
`problem` attribute says so. Follow on / off: the states that mean on and off.
"""

from __future__ import annotations

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, EntityCategory
from homeassistant.core import CoreState, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .entity import device_info

TEXTS = (
    # key, default, icon, checks that it names an entity
    ("live_activity_follow", "", "mdi:car-connected", True),
    ("live_activity_follow_on", "ON", "mdi:toggle-switch", False),
    ("live_activity_follow_off", "OFF", "mdi:toggle-switch-off", False),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([BattmanSettingText(entry, *t) for t in TEXTS])


class BattmanSettingText(TextEntity, RestoreEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = TextMode.TEXT
    _attr_native_min = 0
    _attr_native_max = 255
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, key: str, default: str, icon: str, is_entity: bool) -> None:
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = device_info(entry)
        self._attr_icon = icon
        self._attr_native_value = default
        self._is_entity = is_entity

    @callback
    def _check(self) -> None:
        value = (self._attr_native_value or "").strip()
        problem = None
        if self._is_entity and value and self.hass.states.get(value) is None:
            problem = f"{value} not found"
        self._attr_extra_state_attributes = {"problem": problem} if problem else {}

    async def async_added_to_hass(self) -> None:
        if (last := await self.async_get_last_state()) is not None and last.state not in ("unknown", "unavailable"):
            self._attr_native_value = last.state
        if self._is_entity and self.hass.state is not CoreState.running:
            # entities from other integrations may not exist yet: check once HA is up
            @callback
            def _started(_event) -> None:
                self._check()
                self.async_write_ha_state()

            self.async_on_remove(self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _started))
        self._check()

    async def async_set_value(self, value: str) -> None:
        self._attr_native_value = value.strip()
        self._check()
        self.async_write_ha_state()
