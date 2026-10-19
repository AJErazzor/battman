"""Battman selects.

Live Activity phone: which notify service the Live Activity goes to, or Off.
The list follows the notify services HA has (phones come and go). A phone that
was chosen but has since gone stays selected and is flagged in `problem`, so
it's obvious rather than quietly switching to something else.
"""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_SERVICE_REGISTERED, EVENT_SERVICE_REMOVED, EntityCategory
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .entity import device_info

OFF = "Off"
# notify services that aren't a "send to this device" target
NOT_TARGETS = {"send_message", "persistent_notification"}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([BattmanLiveActivityPhone(entry)])


class BattmanLiveActivityPhone(SelectEntity, RestoreEntity):
    """select.battman_live_activity_phone"""

    _attr_has_entity_name = True
    _attr_translation_key = "live_activity_phone"
    _attr_icon = "mdi:cellphone-arrow-down"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry) -> None:
        self._attr_unique_id = f"{entry.entry_id}_live_activity_phone"
        self._attr_device_info = device_info(entry)
        self._attr_current_option = OFF
        self._attr_options = [OFF]

    def _services(self) -> list[str]:
        return sorted(s for s in self.hass.services.async_services_for_domain("notify") if s not in NOT_TARGETS)

    @callback
    def _refresh(self) -> None:
        services = self._services()
        current = self._attr_current_option
        options = [OFF, *services]
        problem = None
        if current not in options:
            options.append(current)                      # keep showing what was chosen…
            problem = f"notify.{current} not found"      # …and say it's gone
        self._attr_options = options
        self._attr_extra_state_attributes = {"problem": problem} if problem else {}

    async def async_added_to_hass(self) -> None:
        if (last := await self.async_get_last_state()) is not None and last.state not in ("unknown", "unavailable"):
            self._attr_current_option = last.state

        @callback
        def _services_changed(event: Event) -> None:
            if event.data.get("domain") == "notify":
                self._refresh()
                self.async_write_ha_state()

        self.async_on_remove(self.hass.bus.async_listen(EVENT_SERVICE_REGISTERED, _services_changed))
        self.async_on_remove(self.hass.bus.async_listen(EVENT_SERVICE_REMOVED, _services_changed))
        self._refresh()

    async def async_select_option(self, option: str) -> None:
        self._attr_current_option = option
        self._refresh()
        self.async_write_ha_state()
