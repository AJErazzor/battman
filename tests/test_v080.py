import pytest
"""v0.8.0: Settings view, theme mode colours sensor, brand icon."""

import json
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from .dashboard_views import built

pytestmark = pytest.mark.usefixtures("smiggles_installed")

DOMAIN = "battman"
SENSOR = "sensor.battman_theme_mode_colours"
SMIGGLES_PARAMS = "sensor.solarsystemcontrolparameters"   # the map's parameters while Smiggles is in charge
COMPONENT = Path(__file__).resolve().parent.parent / "custom_components" / "battman"

NORD = {k: v for k, v in next(iter(__import__("yaml").safe_load(
    (Path(__file__).parents[1] / "custom_components/battman/themes/Battman Nord.yaml").read_text()).values())).items()
    if k in {"battman-" + h for h in ("red", "darkred", "orange", "amber", "yellow", "green", "teal", "sky",
                                       "blue", "purple", "darkpurple", "pink")}}
MODES = ["Self Consume", "Charge", "Discharge", "Float", "Drain", "Charge Solar Off", "Float Solar Off", "Solar Soak"]


async def _setup(hass):
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain=DOMAIN, title="Battman", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_settings_view(hass: HomeAssistant, hass_client) -> None:
    """Settings is one Battman card now (custom:battman-settings: see test_settings_card)."""
    await _setup(hass)
    data = await built(hass)
    assert data["errors"] == []
    settings = {v["path"]: v for v in data["views"]}["settings"]
    assert settings["type"] == "panel" and [c["type"] for c in settings["cards"]] == ["custom:battman-settings"]


async def test_mode_colours_sensor(hass: HomeAssistant) -> None:
    """The theme and its saved colours come from Battman's own parameters sensor (v0.26.0: named
    directly, whichever engine is in charge, so Migrate doesn't rewrite Battman's packages)."""
    from .test_v0260 import lib_colours

    (Path(hass.config.config_dir) / "configuration.yaml").write_text("homeassistant:\n  packages: !include_dir_named packages\n")
    await _setup(hass)
    themes = {
        "Battman Nord": NORD,
        "Battman HA": {**{k: "var(--x-%s)" % k[8:] for k in NORD if k != "battman-purple"},
                       "battman-purple": "var(--primary-color)",
                       **{"x-" + k[8:]: "rgb(1, 2, 3)" for k in NORD if k != "battman-purple"}},
    }

    async def _pick(theme=None):
        attrs = {"dashboardTheme": theme, "dashboardThemeColours": lib_colours(themes, theme)} if theme else {}
        hass.states.async_set("sensor.battman_parameters", "on", attrs)   # as the settings sensor would hold them
        await hass.async_block_till_done()

    # no theme picked yet -> unknown, and says why
    await _pick()
    st = hass.states.get(SENSOR)
    assert st.state == "unknown" and "No dashboard theme picked" in st.attributes["problem"]

    await _pick("Battman Nord")                                 # parameters change -> refresh
    st = hass.states.get(SENSOR)
    assert list(json.loads(st.state)) == MODES and json.loads(st.state)["Self Consume"] == NORD["battman-blue"]
    assert st.attributes["theme"] == "Battman Nord" and st.attributes["hues"]["Self Consume"] == "blue"
    assert len(set(json.loads(st.state).values())) == 8                     # all eight different

    await _pick("Battman HA")                                   # var() followed; one can't be resolved
    st = hass.states.get(SENSOR)
    assert st.state == "unknown" and "battman-purple" not in st.attributes["problem"]
    assert "primary-color not in theme" in st.attributes["problem"]

    await _pick("Battman Gone")
    assert "isn't loaded" in hass.states.get(SENSOR).attributes["problem"]


def test_brand_icon() -> None:
    from PIL import Image

    for name, size in (("icon.png", 256), ("icon@2x.png", 512)):
        im = Image.open(COMPONENT / "brand" / name)
        assert im.size == (size, size) and im.mode == "RGBA"
        assert im.getchannel("A").getextrema()[0] == 0          # transparent background
