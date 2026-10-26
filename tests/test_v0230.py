"""v0.23.0: Sigen is off the entity map on the cards side too (release 2 of 2).

- The YAML cards and views name Sigen's entities directly; the JS cards take them from one list
  (SIGEN in battman-card-base.js), the House card names them as its defaults.
- Battman uses the whole plant's battery SOC everywhere (Gauges and Overrides used the inverter's).
- The battery temperature and inverter SOC entries are gone; the House card's battery temperature
  has no default (like the outside temperature).
- Configure shows only Amber's prices and Battman's own sensors. A Sigen choice saved before is
  named by a Repair until Configure is saved again.
"""

import json
import re
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.battman import required_entities as R
from custom_components.battman.const import ENTITY_MAP_DEFAULTS

ROOT = Path(__file__).parents[1] / "custom_components/battman"
DOMAIN = "battman"
BASE = (ROOT / "www/battman-card-base.js").read_text()
_S = BASE.index("export const SIGEN")
SIGEN = dict(re.findall(r'^  (\w+): "([^"]+)",$', BASE[_S:BASE.index("};", _S)], re.M))
GONE = set(R.NAMED) | R.DROPPED
PLANT_SOC = "sensor.sigen_plant_battery_state_of_charge"


async def _setup(hass, options=None):
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain=DOMAIN, title="Battman", data={}, options=options or {})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def test_map_has_only_amber_and_battmans_own() -> None:
    assert not [v for v in ENTITY_MAP_DEFAULTS.values() if "sigen" in v]
    assert not GONE & set(ENTITY_MAP_DEFAULTS)


def test_no_sigen_map_lookups_left() -> None:
    keys = "|".join(sorted(GONE))
    for f in [*ROOT.glob("cards/*.yaml"), *ROOT.glob("views/*.yaml"), *ROOT.glob("www/*.js"),
              *ROOT.glob("blueprints/*/*.yaml"), *ROOT.glob("packages/*.yaml")]:
        text = f.read_text()
        assert not re.search(rf"\[\[map:({keys})\]\]|\{{\{{({keys})\}}\}}|\"map:({keys})\"", text), f.name


def test_one_sigen_list_for_the_js_cards() -> None:
    """SIGEN (the JS cards) and NAMED (the startup check / Repair) say the same, and every JS card
    that looks up a Sigen name gets it from SIGEN."""
    assert SIGEN and set(SIGEN) <= set(R.NAMED)
    for k, v in SIGEN.items():
        assert R.NAMED[k] == v, k
    for f in ROOT.glob("www/*.js"):
        text = f.read_text()
        used = set(re.findall(r"\bM\.(\w+)", text)) & set(SIGEN)
        if used:
            assert re.search(r"import \{[^}]*\bSIGEN\b", text), f.name
            assert "...SIGEN" in text, f.name                   # the map plus SIGEN
    house = (ROOT / "www/battman-house.js").read_text()
    defaults = set(re.findall(r'"(sensor\.sigen_[a-z0-9_]+)"', house))
    pv = re.compile(SIGEN["pv_string"].replace("{n}", r"\d+"))
    assert defaults and all(d in SIGEN.values() or pv.fullmatch(d) for d in defaults), defaults


def test_plant_soc_everywhere() -> None:
    for f in [*ROOT.rglob("*.yaml"), *ROOT.glob("www/*.js")]:
        assert "sigen_inverter_battery_state_of_charge" not in f.read_text(), f.name
        assert "battery_maximum_temperature" not in f.read_text(), f.name
    gauges = (ROOT / "cards/gauges.yaml").read_text()
    assert f"entity: '{PLANT_SOC}'" in gauges and f"states('{PLANT_SOC}')" in gauges
    overrides = (ROOT / "cards/overrides.yaml").read_text()
    assert overrides.count(f"- '{PLANT_SOC}'") == 5                    # each row redraws on the SOC
    assert f"entity: {PLANT_SOC}" in (ROOT / "views/20-finances.yaml").read_text()
    house = (ROOT / "www/battman-house.js").read_text()
    assert '{ key: "battery_temp", title: "Battery temperature", ent: { entity: "" }' in house


async def test_cards_and_views_need_nothing_from_the_map(hass: HomeAssistant, hass_client) -> None:
    from .dashboard_views import built

    await _setup(hass)
    client = await hass_client()
    for card in ("gauges", "overrides", "state", "limits"):
        c = await (await client.get(f"/api/battman/cards/{card}")).json()
        assert c["missing_map"] == [], card
        assert "[[map:" not in json.dumps(c["config"]), card
    assert (await built(hass))["errors"] == []


async def test_configure_choices_from_before(hass: HomeAssistant) -> None:
    """Sigen choices saved before v0.23.0 (now off Configure) are named until Configure is saved."""
    entry = await _setup(hass, options={"inverter_soc": "sensor.my_inv_soc", "pv_power": "sensor.my_pv",
                                        "battery_soc": PLANT_SOC, "buy_price": "sensor.my_buy"})
    issue = ir.async_get(hass).async_get_issue(DOMAIN, "map_choice_ignored")
    assert issue.translation_placeholders["choices"] == (
        "- inverter_soc: you picked `sensor.my_inv_soc`; Battman no longer uses this\n"
        "- pv_power: you picked `sensor.my_pv`; Battman now uses `sensor.sigen_plant_pv_power`\n"
        "- buy_price: you picked `sensor.my_buy`; Battman now uses `sensor.amber_5min_current_general_price`")
    # saving Configure drops them all (v0.25.0: Amber came off the map too)
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(flow["flow_id"], {})
    await hass.async_block_till_done()
    assert entry.options == {}
    assert ir.async_get(hass).async_get_issue(DOMAIN, "map_choice_ignored") is None


def test_configure_text() -> None:
    en = json.loads((ROOT / "translations/en.json").read_text())
    data = en["options"]["step"]["init"]["data"]
    assert set(data) == {"opennem"}
    assert "error" not in en["options"]                                  # the PV pattern check is gone
    assert "{marker}" not in en["options"]["step"]["init"]["description"]
