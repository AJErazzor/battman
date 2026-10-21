"""v0.18.6: the dashboard theme's name is kept in Battman (parameters' dashboardTheme), so the
mode colours sensor (Live Activity bar, theme: battman cards) works on a dashboard you've
taken control of."""

import json
from pathlib import Path

from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.core import HomeAssistant

from . import engine_harness as H

ROOT = Path(__file__).parents[1] / "custom_components/battman"
SENSOR = "sensor.battman_theme_mode_colours"
PARAMS = "sensor.battman_parameters"
NORD = {"battman-green": "#a3be8c", "battman-yellow": "#e9d8a6", "battman-blue": "#81a1c1",
        "battman-orange": "#d08770", "battman-red": "#a85560", "battman-purple": "#b48ead"}


async def _settle(hass: HomeAssistant) -> None:
    # the template sensor re-renders, then the colours sensor hears its state change
    for _ in range(3):
        await hass.async_block_till_done()


async def _set_theme(hass: HomeAssistant, name: str) -> None:
    hass.bus.async_fire("battman_parameters_update", {"action": "SetAttribute", "dashboardTheme": name})
    await _settle(hass)


async def test_theme_name_in_parameters_drives_the_colours(hass: HomeAssistant) -> None:
    from homeassistant.components.frontend import DATA_THEMES

    from custom_components.battman.const import IN_CHARGE

    entry, _rec = await H.start(hass, smiggles=False)
    hass.config_entries.async_update_entry(entry, data={**entry.data, IN_CHARGE: True})
    hass.data[DATA_THEMES] = {"Battman Nord": NORD}
    hass.bus.async_fire("battman_parameters_update", {"action": "SetAttribute"})
    await hass.async_block_till_done()

    # the dashboard is yours now (has views, not the strategy): no managed dashboard at all
    dashboards = hass.data[LOVELACE_DATA].dashboards
    for url_path, dash in dashboards.items():
        if url_path:
            await dash.async_save({"views": [{"title": "Power", "theme": "Battman Nord", "cards": []}]})
    await hass.async_block_till_done()

    # nothing picked yet: unknown, and says why (no fallback colours)
    assert hass.states.get(PARAMS).attributes["dashboardTheme"] == ""
    st = hass.states.get(SENSOR)
    assert st.state == "unknown" and "No dashboard theme picked" in st.attributes["problem"]

    await _set_theme(hass, "Battman Nord")
    assert hass.states.get(PARAMS).attributes["dashboardTheme"] == "Battman Nord"
    st = hass.states.get(SENSOR)
    assert json.loads(st.state) == {k[8:]: v for k, v in NORD.items()}
    assert st.attributes["theme"] == "Battman Nord" and "problem" not in st.attributes

    # another setting changing, or a section's Reset to defaults, leaves the theme alone
    hass.bus.async_fire("battman_parameters_update", {"action": "SetAttribute", "billInflation": 3})
    hass.bus.async_fire("battman_parameters_update", {"action": "SetDefaults", "defaults": {}})
    await hass.async_block_till_done()
    assert hass.states.get(PARAMS).attributes["dashboardTheme"] == "Battman Nord"

    # editing the theme's colours (same name) reaches the sensor on the themes reload
    hass.data[DATA_THEMES] = {"Battman Nord": {**NORD, "battman-green": "#000001"}}
    hass.bus.async_fire("themes_updated")
    await _settle(hass)
    assert json.loads(hass.states.get(SENSOR).state)["green"] == "#000001"

    # a theme that isn't loaded: unknown, named
    await _set_theme(hass, "Battman Gone")
    st = hass.states.get(SENSOR)
    assert st.state == "unknown" and "'Battman Gone' isn't loaded" in st.attributes["problem"]


def test_both_theme_pickers_save_the_name() -> None:
    settings = (ROOT / "views/25-settings.yaml").read_text()
    assert "event_type: '{{parameters_update_event}}', event_data: {action: 'SetAttribute', dashboardTheme: theme}" in settings
    studio = (ROOT / "www/theme-studio.html").read_text()
    make_active = studio[studio.index("function doMakeActive(){"):]
    assert "saveThemeName(hass,name);" in make_active[:make_active.index("function reloadParent")]
    assert "dashboardTheme:name" in studio and "parameters_update_event" in studio
    sensor = (ROOT / "sensor.py").read_text()
    assert "lovelace" not in sensor and "async_find_managed" not in sensor
