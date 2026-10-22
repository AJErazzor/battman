"""Battman sensors.

Theme mode colours: the eight mode colours (green, yellow, blue, orange, red,
purple, teal, amber) of the Battman dashboard's theme, as hex. Phones can't read CSS
variables, so things like an iPhone Live Activity read this sensor instead.

It follows the Battman theme you picked (Settings → Dashboard theme, or Make
Active in the Theme studio): both save its name in the parameters sensor's
`dashboardTheme` attribute. It updates when that changes or themes are reloaded,
whether or not you've taken control of the dashboard. No fallbacks: if no theme
is picked, the theme isn't loaded, or a colour isn't a colour, the state is
unknown and the `problem` attribute says why.
"""

from __future__ import annotations

import json
import re
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, Event, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from . import nem
from .const import ENGINE_MAP, SMIGGLES_NAMES
from .entity import device_info

# every colour Battman's mode list uses (MODE_HUE in www/battman-lib.js)
MODE_HUES = ("green", "yellow", "blue", "orange", "red", "purple", "teal", "amber")
EVENT_THEMES_UPDATED = "themes_updated"
_HEX = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_RGB = re.compile(r"^rgba?\(([^)]+)\)$")
_VAR = re.compile(r"^var\(\s*--([a-z0-9-]+)\s*(?:,.*)?\)$")


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([BattmanThemeModeColoursSensor(entry), *nem.entities(hass, entry)])


def to_hex(theme: dict[str, Any], key: str, depth: int = 0) -> str:
    """Theme colour `key` as #rrggbb. Follows var(--other) inside the theme. Raises ValueError."""
    if depth > 5:
        raise ValueError(f"{key}: var() chain too deep")
    if key not in theme:
        raise ValueError(f"{key} not in theme")
    raw = str(theme[key]).strip()
    if m := _VAR.match(raw):
        return to_hex(theme, m.group(1), depth + 1)
    if _HEX.match(raw):
        h = raw[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return "#" + h[:6]
    if m := _RGB.match(raw):
        parts = [p.strip() for p in m.group(1).replace("/", ",").split(",")]
        try:
            rgb = [round(float(p)) for p in parts[:3]]
        except ValueError as err:
            raise ValueError(f"{key} is {raw!r}, not a colour") from err
        if len(rgb) == 3 and all(0 <= v <= 255 for v in rgb):
            return "#" + "".join(f"{v:02x}" for v in rgb)
    raise ValueError(f"{key} is {raw!r}, not a colour Battman can read")


THEME_ATTR = "dashboardTheme"
# the parameters sensor holds the theme name: Battman's, or Smiggles' while it's in charge
PARAMETER_SENSORS = (ENGINE_MAP["parameters"], SMIGGLES_NAMES["parameters"])


async def async_mode_colours(hass: HomeAssistant) -> tuple[dict[str, str] | None, dict[str, Any]]:
    """(colours or None, attributes). Attributes always say which theme, or why not."""
    from homeassistant.components.frontend import DATA_THEMES  # noqa: PLC0415

    from .api import entity_map  # noqa: PLC0415

    params_id = entity_map(hass)["parameters"]
    params = hass.states.get(params_id)
    if params is None:
        return None, {"problem": f"{params_id} doesn't exist (it holds the dashboard theme)"}
    theme_name = str(params.attributes.get(THEME_ATTR) or "").strip()
    if not theme_name:
        return None, {"problem": "No dashboard theme picked (Settings → Dashboard theme, or Make Active in the Theme studio)"}
    attrs: dict[str, Any] = {"theme": theme_name}
    theme = hass.data.get(DATA_THEMES, {}).get(theme_name)
    if theme is None:
        attrs["problem"] = f"Theme {theme_name!r} isn't loaded in Home Assistant"
        return None, attrs
    colours: dict[str, str] = {}
    bad: list[str] = []
    for hue in MODE_HUES:
        try:
            colours[hue] = to_hex(theme, f"battman-{hue}")
        except ValueError as err:
            bad.append(str(err))
    if bad:
        attrs["problem"] = "; ".join(bad)
        return None, attrs
    return colours, attrs


class BattmanThemeModeColoursSensor(SensorEntity):
    """The Battman dashboard theme's mode colours as JSON, e.g. {"green":"#a6e3a1",…}."""

    _attr_has_entity_name = True
    _attr_translation_key = "theme_mode_colours"
    _attr_icon = "mdi:palette"
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry) -> None:
        self._attr_unique_id = f"{entry.entry_id}_theme_mode_colours"
        self._attr_device_info = device_info(entry)

    async def async_added_to_hass(self) -> None:
        @callback
        def _changed(_event: Event) -> None:
            self.hass.async_create_task(self.async_refresh())

        self.async_on_remove(self.hass.bus.async_listen(EVENT_THEMES_UPDATED, _changed))
        self.async_on_remove(async_track_state_change_event(self.hass, list(PARAMETER_SENSORS), _changed))
        if self.hass.state is CoreState.running:
            await self.async_refresh()
        else:
            self.async_on_remove(self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _changed))

    async def async_refresh(self) -> None:
        colours, attrs = await async_mode_colours(self.hass)
        self._attr_native_value = json.dumps(colours, separators=(",", ":")) if colours else None
        self._attr_extra_state_attributes = {**(colours or {}), **attrs}
        self.async_write_ha_state()
