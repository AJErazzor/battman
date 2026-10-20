"""NEM generation and demand sensors, from the OpenNEM sensor in the entity map.

OpenNEM's region sensor (e.g. sensor.opennem_sa) holds each generation source as
an attribute. Dashboard cards like power-pie-card can only read entity states, so
Battman re-exposes them as sensors (MW), plus where the power goes:

    exports, battery charging   OpenNEM reports these negative: shown as positive
    total supply                the positive generation sources added up
    consumers                   total supply - exports - battery charging (never < 0)

No fallbacks: if the OpenNEM sensor is unavailable, every NEM sensor is unavailable.
If one category is missing from it, that sensor is unknown (not 0), and so are the
totals that need it; the `problem` attribute says which.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, UnitOfPower
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event

from .entity import device_info

MAP_KEY = "opennem"
SIGNAL = "battman_nem_update"

# sensor key -> (OpenNEM attribute, icon)
GENERATION: dict[str, tuple[str, str]] = {
    "nem_wind": ("wind", "mdi:wind-turbine"),
    "nem_rooftop_solar": ("solar_rooftop", "mdi:solar-panel"),
    "nem_utility_solar": ("solar_utility", "mdi:solar-power-variant"),
    "nem_imports": ("imports", "mdi:transmission-tower-import"),
    "nem_battery": ("battery_discharging", "mdi:battery-arrow-down"),
    "nem_gas_ccgt": ("gas_ccgt", "mdi:fire"),
    "nem_gas_ocgt": ("gas_ocgt", "mdi:fire"),
    "nem_distillate": ("distillate", "mdi:barrel"),
    "nem_gas_steam": ("gas_steam", "mdi:fire"),
    "nem_gas_recip": ("gas_recip", "mdi:fire"),
}
DEMAND: dict[str, str] = {
    "nem_exports": "mdi:transmission-tower-export",
    "nem_battery_charging": "mdi:battery-arrow-up",
    "nem_total_supply": "mdi:sigma",
    "nem_consumers": "mdi:home-city",
}
ALL_KEYS = [*GENERATION, *DEMAND]


def _num(attrs: dict[str, Any], name: str) -> float | None:
    v = attrs.get(name)
    if v is None or isinstance(v, bool):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def compute(state: Any) -> tuple[bool, dict[str, float | None], list[str]]:
    """(available, values by sensor key, missing OpenNEM attributes) for an OpenNEM state."""
    if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
        return False, dict.fromkeys(ALL_KEYS), []
    attrs = dict(state.attributes)
    out: dict[str, float | None] = {}
    missing: list[str] = []
    for key, (attr, _icon) in GENERATION.items():
        out[key] = _num(attrs, attr)
        if out[key] is None:
            missing.append(attr)
    for key, attr in (("nem_exports", "exports"), ("nem_battery_charging", "battery_charging")):
        v = _num(attrs, attr)
        out[key] = round(abs(v), 2) if v is not None else None
        if v is None:
            missing.append(attr)
    gen = [out[k] for k in GENERATION]
    out["nem_total_supply"] = None if None in gen else round(sum(max(0.0, v) for v in gen), 2)
    parts = (out["nem_total_supply"], out["nem_exports"], out["nem_battery_charging"])
    out["nem_consumers"] = None if None in parts else round(max(0.0, parts[0] - parts[1] - parts[2]), 2)
    return True, out, missing


class NemSource:
    """Follows the mapped OpenNEM sensor and tells the NEM sensors when it changes."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._unsub = None
        self.entity_id: str | None = None

    def _mapped(self) -> str:
        from .api import entity_map  # noqa: PLC0415

        return entity_map(self.hass)[MAP_KEY]

    @callback
    def start(self) -> None:
        self._follow()
        self.entry.async_on_unload(self.entry.add_update_listener(self._options_changed))
        self.entry.async_on_unload(self.stop)

    async def _options_changed(self, _hass: HomeAssistant, _entry: ConfigEntry) -> None:
        if self._mapped() != self.entity_id:
            self._follow()
            async_dispatcher_send(self.hass, SIGNAL)

    @callback
    def _follow(self) -> None:
        self.stop()
        self.entity_id = self._mapped()

        @callback
        def _changed(_event: Event) -> None:
            async_dispatcher_send(self.hass, SIGNAL)

        self._unsub = async_track_state_change_event(self.hass, [self.entity_id], _changed)

    @callback
    def stop(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None

    def read(self) -> tuple[bool, dict[str, float | None], list[str]]:
        return compute(self.hass.states.get(self.entity_id) if self.entity_id else None)


class BattmanNemSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_native_unit_of_measurement = UnitOfPower.MEGA_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, entry: ConfigEntry, source: NemSource, key: str) -> None:
        self._source = source
        self._key = key
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_icon = GENERATION[key][1] if key in GENERATION else DEMAND[key]
        self._attr_device_info = device_info(entry)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL, self._refresh))
        self._refresh()

    @callback
    def _refresh(self) -> None:
        available, values, missing = self._source.read()
        self._attr_available = available
        self._attr_native_value = values[self._key]
        attrs: dict[str, Any] = {"source": self._source.entity_id}
        if not available:
            attrs["problem"] = f"{self._source.entity_id} is missing or unavailable"
        elif values[self._key] is None:
            attrs["problem"] = f"{self._source.entity_id} has no value for: {', '.join(missing)}"
        self._attr_extra_state_attributes = attrs
        if self.hass and self.entity_id:
            self.async_write_ha_state()


def entities(hass: HomeAssistant, entry: ConfigEntry) -> list[BattmanNemSensor]:
    source = NemSource(hass, entry)
    source.start()
    return [BattmanNemSensor(entry, source, k) for k in ALL_KEYS]
