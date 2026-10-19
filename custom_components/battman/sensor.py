"""Battman sensors.

Theme mode colours: the six mode colours (green, yellow, blue, orange, red,
purple) of the Battman dashboard's theme, as hex. Phones can't read CSS
variables, so things like an iPhone Live Activity read this sensor instead.

It follows the theme set on the managed Battman dashboard (Settings → Dashboard
theme, or Make Active in the Theme studio), and updates whenever that dashboard
is saved or themes are reloaded. No fallbacks: if there's no Battman dashboard,
no theme picked, or a colour that isn't a colour, the state is unknown and the
`problem` attribute says why.
"""

from __future__ import annotations

import json
import re
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, Event, HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import dashboard
from .const import DOMAIN

MODE_HUES = ("green", "yellow", "blue", "orange", "red", "purple")
EVENT_LOVELACE_UPDATED = "lovelace_updated"
EVENT_THEMES_UPDATED = "themes_updated"
_HEX = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_RGB = re.compile(r"^rgba?\(([^)]+)\)$")
_VAR = re.compile(r"^var\(\s*--([a-z0-9-]+)\s*(?:,.*)?\)$")


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([BattmanThemeModeColoursSensor(entry)])


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


async def async_mode_colours(hass: HomeAssistant) -> tuple[dict[str, str] | None, dict[str, Any]]:
    """(colours or None, attributes). Attributes always say which dashboard/theme, or why not."""
    from homeassistant.components.frontend import DATA_THEMES  # noqa: PLC0415

    try:
        managed = await dashboard.async_find_managed(hass)
    except dashboard.DashboardUnavailable as err:
        return None, {"problem": f"Can't read dashboards: {err}"}
    if not managed:
        return None, {"problem": "No managed Battman dashboard (press Create dashboard on the Battman device)"}
    url_path = sorted(managed)[0]
    config = await dashboard._lovelace(hass).dashboards[url_path].async_load(False)  # noqa: SLF001
    theme_name = (config.get("strategy") or {}).get("theme")
    attrs: dict[str, Any] = {"dashboard": url_path}
    if not theme_name:
        attrs["problem"] = "No dashboard theme picked (Settings → Dashboard theme, or Make Active in the Theme studio)"
        return None, attrs
    attrs["theme"] = theme_name
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
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Battman",
            manufacturer="Battman",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        @callback
        def _changed(_event: Event) -> None:
            self.hass.async_create_task(self.async_refresh())

        self.async_on_remove(self.hass.bus.async_listen(EVENT_LOVELACE_UPDATED, _changed))
        self.async_on_remove(self.hass.bus.async_listen(EVENT_THEMES_UPDATED, _changed))
        if self.hass.state is CoreState.running:
            await self.async_refresh()
        else:
            self.async_on_remove(self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _changed))

    async def async_refresh(self) -> None:
        colours, attrs = await async_mode_colours(self.hass)
        self._attr_native_value = json.dumps(colours, separators=(",", ":")) if colours else None
        self._attr_extra_state_attributes = {**(colours or {}), **attrs}
        self.async_write_ha_state()
