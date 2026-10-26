"""v0.25.0: Amber off the entity map too.

- Amber's 4 entities (amber2mqtt, through MQTT) are named directly in the engine side, the cards,
  the views and the JS cards (AMBER in battman-card-base.js), and checked at startup: a Repair
  names any that's missing or disabled.
- The entity map is only Battman's engine entities now (Smiggles' until you migrate).
- Configure shows nothing but the OpenNEM region (when there are several); saving it clears choices
  made by older versions, which a Repair names until then.
"""

import json
import re
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.battman import required_entities as R
from custom_components.battman.const import ENGINE_MAP, ENTITY_MAP_DEFAULTS, FACTORY_MAP

ROOT = Path(__file__).parents[1] / "custom_components/battman"
DOMAIN = "battman"
AMBER = {"buy_price": "sensor.amber_5min_current_general_price",
         "feed_in_price": "sensor.amber_5min_current_feed_in_price",
         "buy_forecast": "sensor.amber_billing_interval_forecasts_general_price",
         "feed_in_forecast": "sensor.amber_billing_interval_forecasts_feed_in_price"}


async def _setup(hass, options=None):
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain=DOMAIN, title="Battman", data={}, options=options or {})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def test_map_is_only_the_engine() -> None:
    assert ENTITY_MAP_DEFAULTS == {**ENGINE_MAP, **FACTORY_MAP}
    assert not [v for v in ENTITY_MAP_DEFAULTS.values() if v.startswith(("sensor.amber", "sensor.sigen", "sensor.solcast"))]


def test_amber_by_name_everywhere() -> None:
    keys = "|".join(AMBER)
    for f in [*ROOT.glob("blueprints/*/*.yaml"), *ROOT.glob("packages/*.yaml"), *ROOT.glob("cards/*.yaml"),
              *ROOT.glob("views/*.yaml"), *ROOT.glob("www/*.js")]:
        text = f.read_text()
        assert not re.search(rf"\[\[map:({keys})\]\]|\{{\{{({keys})\}}\}}|\"map:({keys})\"", text), f.name
        if re.search(rf"\bM\.({keys})\b", text) or "OPTIONAL_ENTITIES = { buy_forecast" in text:
            assert "...AMBER" in text and re.search(r"import \{[^}]*\bAMBER\b", text), f.name
    engine = (ROOT / "blueprints/script/battman_engine.yaml").read_text()
    assert "general_price: sensor.amber_5min_current_general_price" in engine
    assert "feed_in_forecast: sensor.amber_billing_interval_forecasts_feed_in_price" in engine
    base = (ROOT / "www/battman-card-base.js").read_text()
    s = base.index("export const AMBER")
    assert dict(re.findall(r'^  (\w+): "([^"]+)",$', base[s:base.index("};", s)], re.M)) == AMBER
    house = (ROOT / "www/battman-house.js").read_text()
    assert f'"{AMBER["buy_price"]}"' in house and "battman/entities" not in house and '"map:' not in house


def test_amber_checked_at_startup() -> None:
    for k, v in AMBER.items():
        assert R.NAMED[k] == v and R.REQUIRED[v][1] == R.AMBER == "Amber (amber2mqtt, through MQTT)", k
    deps = (ROOT.parents[1] / "DEPENDENCIES.md").read_text()
    assert "amber2mqtt" in deps and all(v in deps for v in AMBER.values())


async def test_missing_amber_named(hass: HomeAssistant) -> None:
    await _setup(hass)
    text = ir.async_get(hass).async_get_issue(DOMAIN, "missing_entities").translation_placeholders["missing"]
    assert ("- `sensor.amber_5min_current_general_price` (the buy price now, from Amber (amber2mqtt, through "
            "MQTT)): not found") in text


async def test_configure_has_only_the_opennem_region(hass: HomeAssistant) -> None:
    entry = await _setup(hass, options={"feed_in_price": "sensor.my_fit"})
    issue = ir.async_get(hass).async_get_issue(DOMAIN, "map_choice_ignored")
    assert issue.translation_placeholders["choices"] == (
        "- feed_in_price: you picked `sensor.my_fit`; Battman now uses `sensor.amber_5min_current_feed_in_price`")
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    assert list(flow["data_schema"].schema) == []                   # one OpenNEM region (or none): nothing to set
    await hass.config_entries.options.async_configure(flow["flow_id"], {})
    await hass.async_block_till_done()
    assert entry.options == {} and ir.async_get(hass).async_get_issue(DOMAIN, "map_choice_ignored") is None
    # several OpenNEM regions: the choice is there, and kept when saved
    from homeassistant.helpers import entity_registry as er

    from custom_components.battman.nem import OPENNEM, REGION_ATTR
    for r in ("sa", "vic"):
        er.async_get(hass).async_get_or_create("sensor", OPENNEM, r, suggested_object_id=f"opennem_{r}")
        hass.states.async_set(f"sensor.opennem_{r}", "1", {REGION_ATTR: r.upper()})
    await hass.async_block_till_done()
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    assert [str(k) for k in flow["data_schema"].schema] == ["opennem"]
    en = json.loads((ROOT / "translations/en.json").read_text())["options"]["step"]["init"]
    assert set(en["data"]) == {"opennem"} and "Nothing to set here" in en["description"]
