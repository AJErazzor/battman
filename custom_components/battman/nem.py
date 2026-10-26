"""NEM generation and demand sensors, from the OpenNEM integration's region sensor.

OpenNEM's region sensor (e.g. sensor.opennem_sa) holds each generation source as
an attribute. Battman finds it itself: an OpenNEM entity carrying those attributes.
One found: that's used. Several (more than one region): you pick one on Battman's
Configure screen, and a Repair asks you to until you do. None: the NEM sensors are
unknown and their `problem` attribute says so (OpenNEM is optional, so no Repair).
It looks again whenever an OpenNEM entity is added, removed or changes, so switching
OpenNEM to another region is followed without a restart. Dashboard cards like power-pie-card can only read entity states, so
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
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN
from .entity import device_info

OPENNEM = "opennem"            # the OpenNEM integration's domain
OPTION = "opennem"             # Configure: the region you picked (only asked when there are several)
REGION_ATTR = "solar_rooftop"  # an OpenNEM entity with this attribute is a region sensor
ISSUE_CHOOSE = "opennem_choose"
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


def find_regions(hass: HomeAssistant) -> list[str]:
    """The OpenNEM integration's region sensors: its entities that carry the generation figures."""
    found = []
    for entry in er.async_get(hass).entities.values():
        if entry.platform != OPENNEM:
            continue
        state = hass.states.get(entry.entity_id)
        if state is not None and REGION_ATTR in state.attributes:
            found.append(entry.entity_id)
    return sorted(found)


def _opennem_ids(hass: HomeAssistant) -> list[str]:
    return [e.entity_id for e in er.async_get(hass).entities.values() if e.platform == OPENNEM]


class NemSource:
    """Finds OpenNEM's region sensor, follows it, and tells the NEM sensors when anything changes."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.entity_id: str | None = None
        self.problem: str | None = None     # why there's no region sensor to read
        self._unsub_states = None
        self._watched: list[str] = []

    @callback
    def start(self) -> None:
        self._watch()
        self.entry.async_on_unload(self.hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, self._registry_changed))
        self.entry.async_on_unload(self.entry.add_update_listener(self._options_changed))
        self.entry.async_on_unload(self.stop)
        self._recheck()

    async def _options_changed(self, _hass: HomeAssistant, _entry: ConfigEntry) -> None:
        self._recheck()

    @callback
    def _registry_changed(self, _event: Event) -> None:
        self._watch()
        self._recheck()

    @callback
    def _watch(self) -> None:
        """Follow the state of every OpenNEM entity (a region sensor's figures, or one appearing)."""
        ids = _opennem_ids(self.hass)
        if ids == self._watched and self._unsub_states:
            return
        self.stop()
        self._watched = ids
        if ids:
            self._unsub_states = async_track_state_change_event(self.hass, ids, self._state_changed)

    @callback
    def _state_changed(self, _event: Event) -> None:
        self._recheck()

    @callback
    def _recheck(self) -> None:
        found = find_regions(self.hass)
        chosen = self.entry.options.get(OPTION)
        entity, problem = None, None
        if chosen in found:
            entity = chosen
        elif len(found) == 1:
            entity = found[0]
        elif not found and self.entity_id in self._watched:
            entity = self.entity_id          # the region sensor we read is still there, just unavailable for now
        elif not found:
            problem = "No OpenNEM region sensor found (is the OpenNEM integration set up?)"
        else:
            problem = f"Several OpenNEM regions ({', '.join(found)}): pick one under Battman → Configure"
        if len(found) > 1 and chosen not in found:
            ir.async_create_issue(
                self.hass, DOMAIN, ISSUE_CHOOSE, is_fixable=False, severity=ir.IssueSeverity.WARNING,
                translation_key=ISSUE_CHOOSE, translation_placeholders={"regions": ", ".join(found)},
            )
        else:
            ir.async_delete_issue(self.hass, DOMAIN, ISSUE_CHOOSE)
        self.entity_id, self.problem = entity, problem
        async_dispatcher_send(self.hass, SIGNAL)

    @callback
    def stop(self) -> None:
        if self._unsub_states:
            self._unsub_states()
            self._unsub_states = None

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
        # no region sensor to read (none found, or several to choose from): unknown, saying why
        # (HA drops an unavailable sensor's attributes, so the reason would be lost)
        self._attr_available = available or bool(self._source.problem)
        self._attr_native_value = values[self._key]
        attrs: dict[str, Any] = {"source": self._source.entity_id}
        if self._source.problem:
            attrs["problem"] = self._source.problem
        elif not available:
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
