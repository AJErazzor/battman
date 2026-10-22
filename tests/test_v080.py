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

NORD = {"battman-green": "#a3be8c", "battman-yellow": "#e9d8a6", "battman-blue": "#81a1c1",
        "battman-orange": "#d08770", "battman-red": "#a85560", "battman-purple": "#b48ead",
        "battman-teal": "#8fbcbb", "battman-amber": "#ebcb8b"}


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
    """The theme name comes from the parameters sensor (Smiggles' here: it's in charge)."""
    from homeassistant.components.frontend import DATA_THEMES

    await _setup(hass)
    hass.data[DATA_THEMES] = {
        "Battman Nord": NORD,
        "Battman HA": {**{f"battman-{k}": "var(--x-%s)" % k for k in ("green", "yellow", "blue", "orange", "red", "teal", "amber")},
                       "battman-purple": "var(--primary-color)",
                       **{f"x-{k}": "rgb(1, 2, 3)" for k in ("green", "yellow", "blue", "orange", "red", "teal", "amber")}},
    }

    async def _pick(theme=None):
        hass.states.async_set(SMIGGLES_PARAMS, "on", {"dashboardTheme": theme} if theme else {})
        await hass.async_block_till_done()

    # no theme picked yet -> unknown, and says why
    await _pick()
    st = hass.states.get(SENSOR)
    assert st.state == "unknown" and "No dashboard theme picked" in st.attributes["problem"]

    await _pick("Battman Nord")                                 # parameters change -> refresh
    st = hass.states.get(SENSOR)
    assert json.loads(st.state) == {k[8:]: v for k, v in NORD.items()}
    assert st.attributes["theme"] == "Battman Nord" and st.attributes["green"] == "#a3be8c"
    assert list(json.loads(st.state)) == ["green", "yellow", "blue", "orange", "red", "purple", "teal", "amber"]

    await _pick("Battman HA")                                   # var() followed; one can't be resolved
    st = hass.states.get(SENSOR)
    assert st.state == "unknown" and "battman-purple" not in st.attributes["problem"]
    assert "primary-color not in theme" in st.attributes["problem"]

    await _pick("Battman Gone")
    assert "isn't loaded" in hass.states.get(SENSOR).attributes["problem"]


def test_to_hex() -> None:
    from custom_components.battman.sensor import to_hex

    t = {"a": "#ABC", "b": "#11223344", "c": "rgba(255, 0, 16, 0.5)", "d": "var(--a)", "e": "red", "f": "var(--f)"}
    assert to_hex(t, "a") == "#AABBCC" and to_hex(t, "b") == "#112233"
    assert to_hex(t, "c") == "#ff0010" and to_hex(t, "d") == "#AABBCC"
    for bad in ("e", "f", "zz"):
        try:
            to_hex(t, bad)
        except ValueError:
            continue
        raise AssertionError(bad)


def test_brand_icon() -> None:
    from PIL import Image

    for name, size in (("icon.png", 256), ("icon@2x.png", 512)):
        im = Image.open(COMPONENT / "brand" / name)
        assert im.size == (size, size) and im.mode == "RGBA"
        assert im.getchannel("A").getextrema()[0] == 0          # transparent background
