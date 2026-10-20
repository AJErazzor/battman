"""v0.16.1: a Battman card's own grid_options (e.g. columns: full) reach HA.

HA reads grid_options only on the card as placed (custom:battman-<id>), never inside the
card file, so the managed dashboard, the card picker and the wrapper pass it on."""

from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.battman import api

DOMAIN = "battman"
JS = Path(__file__).parents[1] / "custom_components/battman/www/battman-cards.js"
FULL = ("profitloss", "amber5minpricegrid", "amber24hourforecasttable")


async def _client(hass, hass_client):
    assert await async_setup_component(hass, "lovelace", {})
    MockConfigEntry(domain=DOMAIN, title="Battman", data={}).add_to_hass(hass)
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return await hass_client()


def _cards(view):
    return {c["type"][len("custom:battman-"):]: c for s in view["sections"] for c in s["cards"]
            if c["type"].startswith("custom:battman-")}


async def test_power_view_cards_full_width(hass: HomeAssistant, hass_client) -> None:
    client = await _client(hass, hass_client)
    power = (await (await client.get("/api/battman/dashboard")).json())["views"][0]
    cards = _cards(power)
    for cid in FULL:
        assert cards[cid]["grid_options"]["columns"] == "full", cid
    assert "grid_options" not in cards["limits"]           # its card file sets none: HA's default, as before
    assert power["sections"][1]["column_span"] == 2


async def test_card_api_gives_grid_options(hass: HomeAssistant, hass_client) -> None:
    client = await _client(hass, hass_client)
    for cid in FULL:
        card = await (await client.get(f"/api/battman/cards/{cid}")).json()
        assert card["grid_options"]["columns"] == "full"
    assert (await (await client.get("/api/battman/cards/limits")).json())["grid_options"] is None


def test_placed_grid_options_win() -> None:
    view = {"sections": [{"cards": [{"type": "custom:battman-profitloss", "grid_options": {"columns": 6}},
                                    {"type": "custom:battman-profitloss"}, {"type": "markdown"}]}]}
    out = api._card_sizes(view, {"profitloss": {"columns": "full"}})["sections"][0]["cards"]
    assert out[0]["grid_options"] == {"columns": 6}           # yours stays
    assert out[1]["grid_options"] == {"columns": "full"}
    assert "grid_options" not in out[2]


def test_wrapper_passes_grid_options() -> None:
    js = JS.read_text()
    assert "static async getStubConfig(hass)" in js and "{ grid_options: data.grid_options }" in js
    assert "if (this._gridOptions) return this._gridOptions;" in js
    assert "this._gridOptions = data.grid_options || null;" in js
