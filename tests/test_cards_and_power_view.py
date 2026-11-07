"""v0.11.0: Battman cards (card files, map filling, local overrides) and the Power view."""

from pathlib import Path

import yaml
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from .dashboard_views import built
from .snapshots import assert_snapshot

DOMAIN = "battman"


async def _setup(hass):
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain=DOMAIN, title="Battman", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_power_view_first(hass: HomeAssistant, hass_client) -> None:
    await _setup(hass)
    data = await built(hass)
    power = data["views"][0]
    assert power["path"] == "power" and power["title"] == "Power" and power["theme"] == "Battman Nord"
    assert {"type": "custom:battman-limits"} in power["sections"][1]["cards"]   # layout: test_amber_grid_state_card_countdown


async def test_cards_api(hass: HomeAssistant, hass_client) -> None:
    await _setup(hass)
    client = await hass_client()
    cards = (await (await client.get("/api/battman/cards")).json())["cards"]
    assert {"id": "limits", "name": "Limits", "source": "battman",
            "description": "Grid export, PV max and max charge limits. Tap one to change it."} in cards
    card = await (await client.get("/api/battman/cards/limits")).json()
    assert card["missing_map"] == [] and card["needs"] == ["button-card"] and card["source"] == "battman"
    text = yaml.safe_dump(card["config"])
    assert "[[map:" not in text and "smiggles" not in text
    for e in ("number.sigen_plant_grid_export_limitation", "number.sigen_plant_pv_max_power_limit",
              "number.sigen_plant_ess_max_charging_limit"):
        assert e in text
    r = await client.get("/api/battman/cards/nope")
    assert r.status == 404 and "no Battman card called" in (await r.json())["message"]
    r = await client.get("/api/battman/cards/..%2Fsecrets")
    assert r.status in (400, 404)                               # never read outside the card folders


async def test_limits_card(hass: HomeAssistant, hass_client) -> None:
    """The filled-in Battman limits card: every tile, its fields and its JS (snapshot)."""
    await _setup(hass)
    card = await (await (await hass_client()).get("/api/battman/cards/limits")).json()
    m = card["config"]
    tiles = m["cards"][0]["cards"]
    assert len(tiles) == 3
    for t in tiles:
        assert t["entity"] and "c" in t["custom_fields"]
    assert_snapshot(__file__, "limits-config", m)


async def test_local_override_and_repair(hass: HomeAssistant, hass_client) -> None:
    await _setup(hass)
    client = await hass_client()
    issues = ir.async_get(hass)
    assert issues.async_get_issue(DOMAIN, "local_cards") is None
    local = Path(hass.config.path("battman/cards"))
    local.mkdir(parents=True)
    (local / "limits.yaml").write_text("# name: My limits\ntype: markdown\ncontent: '[[map:parameters]]'\n")
    (local / "mine.yaml").write_text("type: markdown\ncontent: '[[map:no_such_thing]]'\n")
    card = await (await client.get("/api/battman/cards/limits")).json()
    assert card["source"] == "local override" and card["config"] == {"type": "markdown", "content": "sensor.battman_parameters"}
    mine = await (await client.get("/api/battman/cards/mine")).json()
    assert mine["source"] == "local" and mine["missing_map"] == ["no_such_thing"]   # shown on the card, not hidden
    issue = issues.async_get_issue(DOMAIN, "local_cards")
    assert issue.translation_placeholders["cards"] == "limits, mine"
    (local / "mine.yaml").write_text("type: [oops")
    r = await client.get("/api/battman/cards/mine")
    assert r.status == 400 and "isn't valid YAML" in (await r.json())["message"]
    for f in local.glob("*.yaml"):
        f.unlink()
    await client.get("/api/battman/cards")
    assert issues.async_get_issue(DOMAIN, "local_cards") is None                    # back to Battman's: Repair goes


def test_jinja_left_alone() -> None:
    from custom_components.battman import cards

    missing: set[str] = set()
    out = cards._fill({"a": "{{ states('sensor.x') }} [[map:pv]]", "b": ["{{ x }}"]}, {"pv": "sensor.pv"}, missing)
    assert out == {"a": "{{ states('sensor.x') }} sensor.pv", "b": ["{{ x }}"]} and missing == set()
