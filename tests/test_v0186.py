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
NORD = {k: v for k, v in next(iter(__import__("yaml").safe_load(
    (Path(__file__).parents[1] / "custom_components/battman/themes/Battman Nord.yaml").read_text()).values())).items()
    if k in {"battman-" + h for h in ("red", "darkred", "orange", "amber", "yellow", "green", "teal", "sky",
                                       "blue", "purple", "darkpurple", "pink")}}
MODES = ["Self Consume", "Charge", "Discharge", "Float", "Drain", "Charge Solar Off", "Float Solar Off", "Solar Soak"]


async def _settle(hass: HomeAssistant) -> None:
    # the template sensor re-renders, then the colours sensor hears its state change
    for _ in range(3):
        await hass.async_block_till_done()


async def _set_theme(hass: HomeAssistant, name: str) -> None:
    hass.bus.async_fire("battman_parameters_update", {"action": "SetAttribute", "dashboardTheme": name})
    await _settle(hass)


async def test_theme_name_in_parameters_drives_the_colours(hass: HomeAssistant) -> None:
    """v0.26.0: the browser saves the picked theme's colours (dashboardThemeColours, see
    test_v0260 for the browser side); the template sensor shows them for the picked theme only."""
    from custom_components.battman.const import IN_CHARGE

    from .test_v0260 import lib_colours

    entry, _rec = await H.start(hass, smiggles=False)
    hass.config_entries.async_update_entry(entry, data={**entry.data, IN_CHARGE: True})
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
    st = hass.states.get(SENSOR)                             # picked, colours not saved yet: says so
    assert st.state == "unknown" and "haven't been saved yet" in st.attributes["problem"]
    saved = lib_colours({"Battman Nord": NORD}, "Battman Nord")   # what an open Battman page saves
    hass.bus.async_fire("battman_parameters_update", {"action": "SetAttribute", "dashboardThemeColours": saved})
    await _settle(hass)
    st = hass.states.get(SENSOR)
    assert json.loads(st.state) == saved["modes"] and list(json.loads(st.state)) == MODES
    assert json.loads(st.state)["Discharge"] == NORD["battman-green"]          # an everyday mode: its button's colour
    assert st.attributes["theme"] == "Battman Nord" and st.attributes["hues"]["Discharge"] == "green"
    assert st.attributes["problem"] is None

    # another setting changing, or a section's Reset to defaults, leaves the theme and colours alone
    hass.bus.async_fire("battman_parameters_update", {"action": "SetAttribute", "billInflation": 3})
    hass.bus.async_fire("battman_parameters_update", {"action": "SetDefaults", "defaults": {}})
    await _settle(hass)
    assert hass.states.get(PARAMS).attributes["dashboardTheme"] == "Battman Nord"
    assert json.loads(hass.states.get(SENSOR).state)["Discharge"] == NORD["battman-green"]

    # another theme picked: the old colours aren't shown for it
    await _set_theme(hass, "Battman Gone")
    st = hass.states.get(SENSOR)
    assert st.state == "unknown" and "haven't been saved yet" in st.attributes["problem"]
    hass.bus.async_fire("battman_parameters_update", {"action": "SetAttribute",
                        "dashboardThemeColours": lib_colours({}, "Battman Gone")})
    await _settle(hass)
    st = hass.states.get(SENSOR)
    assert st.state == "unknown" and "'Battman Gone' isn't loaded" in st.attributes["problem"]


def test_both_theme_pickers_save_the_name() -> None:
    settings = (ROOT / "www/battman-settings.js").read_text()      # the Settings page's Dashboard theme
    assert "setParam(el, 'dashboardTheme', theme" in settings
    studio = (ROOT / "www/battman-theme-studio.js").read_text()
    make_active = studio[studio.index("function doMakeActive(){"):]
    assert "saveThemeName(hass,name);" in make_active[:make_active.index("function reloadParent")]
    assert "dashboardTheme:name" in studio and "parameters_update_event" in studio
    assert "dashboardTheme" not in (ROOT / "sensor.py").read_text()      # a template sensor now
