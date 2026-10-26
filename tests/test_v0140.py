"""v0.14.0: Gauges and NEM mix cards, Battman's NEM sensors, the forecast table in HA's
time zone, and plant rated capacity for battery capacity.

The gauges' text and the NEM sensors are checked against the originals they replace
(Smiggles card templates, the Smiggles package and the OpenNEM template sensors),
rendered by HA itself on the same states."""

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import yaml
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.template import Template
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .test_v0130 import run_js
from .dashboard_views import built

pytestmark = pytest.mark.usefixtures("smiggles_installed")

DOMAIN = "battman"
FIX = Path(__file__).parent / "fixtures"
CARDS = Path(__file__).parents[1] / "custom_components/battman/cards"
needs_node = pytest.mark.skipif(not shutil.which("node"), reason="needs node to run the cards' JavaScript")

GEN = {"wind": 812.4, "solar_rooftop": 1120.7, "solar_utility": 301.25, "imports": -0.0, "battery_discharging": 41.9,
       "gas_ccgt": 55.0, "gas_ocgt": 0, "distillate": 0.0, "gas_steam": 12.5, "gas_recip": -3.2,
       "exports": -455.123, "battery_charging": -77.456}
KEYS = {"wind": "wind", "rooftop_solar": "solar_rooftop", "utility_solar": "solar_utility", "imports": "imports",
        "battery": "battery_discharging", "gas_ccgt": "gas_ccgt", "gas_ocgt": "gas_ocgt", "distillate": "distillate",
        "gas_steam": "gas_steam", "gas_recip": "gas_recip"}


def _opennem(hass, region: str, attrs: dict | None = GEN, state: str = "ok") -> str:
    """A region sensor of the OpenNEM integration (registered as OpenNEM's, as the real one is)."""
    ent = er.async_get(hass).async_get_or_create("sensor", "opennem", region, suggested_object_id=f"opennem_{region}")
    hass.states.async_set(ent.entity_id, state, attrs or {})
    return ent.entity_id


async def _setup(hass, hass_client=None):
    # the OpenNEM integration is installed (v0.26.0: Battman's NEM sensors only exist then)
    if not hass.config_entries.async_entries("opennem"):
        MockConfigEntry(domain="opennem", title="OpenNEM").add_to_hass(hass)
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain=DOMAIN, title="Battman", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _orig_templates():
    """name -> state template, from A.J.'s OpenNEM template package."""
    pkg = yaml.safe_load((FIX / "opennem_templates.yaml").read_text())
    return {s["unique_id"]: s["state"] for s in pkg["template"][0]["sensor"]}


def _render(hass, tpl):
    return Template(tpl, hass).async_render(parse_result=False).strip()


# ── NEM sensors ──────────────────────────────────────────────────────────────

async def test_nem_sensors_match_templates(hass: HomeAssistant) -> None:
    _opennem(hass, "sa")
    await _setup(hass)
    orig = _orig_templates()
    # the original templates, rendered on the same OpenNEM state, in order (later ones read earlier ones)
    ids = {"opennem_sa_wind": "sensor.opennem_sa_wind", "opennem_sa_solar_rooftop": "sensor.opennem_sa_rooftop_solar",
           "opennem_sa_solar_utility": "sensor.opennem_sa_utility_solar", "opennem_sa_imports": "sensor.opennem_sa_imports",
           "opennem_sa_battery_discharging": "sensor.opennem_sa_battery", "opennem_sa_gas_ccgt": "sensor.opennem_sa_gas_ccgt",
           "opennem_sa_gas_ocgt": "sensor.opennem_sa_gas_ocgt", "opennem_sa_distillate": "sensor.opennem_sa_distillate",
           "opennem_sa_gas_steam": "sensor.opennem_sa_gas_steam", "opennem_sa_gas_recip": "sensor.opennem_sa_gas_recip",
           "sa_exports": "sensor.sa_exports", "sa_battery_charging": "sensor.sa_battery_charging",
           "sa_total_supply": "sensor.sa_total_supply", "sa_consumers": "sensor.sa_consumers"}
    for uid, eid in ids.items():
        hass.states.async_set(eid, _render(hass, orig[uid]))
    mine = {"wind": "opennem_sa_wind", "rooftop_solar": "opennem_sa_solar_rooftop", "utility_solar": "opennem_sa_solar_utility",
            "imports": "opennem_sa_imports", "battery": "opennem_sa_battery_discharging", "gas_ccgt": "opennem_sa_gas_ccgt",
            "gas_ocgt": "opennem_sa_gas_ocgt", "distillate": "opennem_sa_distillate", "gas_steam": "opennem_sa_gas_steam",
            "gas_recip": "opennem_sa_gas_recip", "exports": "sa_exports", "battery_charging": "sa_battery_charging",
            "total_supply": "sa_total_supply", "consumers": "sa_consumers"}
    for k, uid in mine.items():
        st = hass.states.get(f"sensor.battman_nem_{k}")
        assert st is not None, k
        assert float(st.state) == pytest.approx(float(hass.states.get(ids[uid]).state)), k
        assert st.attributes["unit_of_measurement"] == "MW" and "problem" not in st.attributes

    # OpenNEM changes -> Battman follows
    hass.states.async_set("sensor.opennem_sa", "ok", {**GEN, "wind": 900})
    await hass.async_block_till_done()
    assert float(hass.states.get("sensor.battman_nem_wind").state) == 900


async def test_nem_sensors_missing(hass: HomeAssistant) -> None:
    attrs = dict(GEN)
    del attrs["gas_recip"]
    _opennem(hass, "sa", attrs)
    await _setup(hass)
    recip = hass.states.get("sensor.battman_nem_gas_recip")
    assert recip.state == "unknown" and "gas_recip" in recip.attributes["problem"]      # not 0
    assert hass.states.get("sensor.battman_nem_total_supply").state == "unknown"
    assert hass.states.get("sensor.battman_nem_consumers").state == "unknown"
    assert hass.states.get("sensor.battman_nem_wind").state == "812.4"
    assert hass.states.get("sensor.battman_nem_exports").state == "455.12"

    # OpenNEM unavailable for a while: still its sensor, unavailable, and says so
    hass.states.async_set("sensor.opennem_sa", "unavailable", {})
    await hass.async_block_till_done()
    for k in ("wind", "exports", "consumers"):
        assert hass.states.get(f"sensor.battman_nem_{k}").state == "unavailable", k
    hass.states.async_set("sensor.opennem_sa", "ok", {**GEN, "wind": 700})
    await hass.async_block_till_done()
    assert hass.states.get("sensor.battman_nem_wind").state == "700.0"


async def test_nem_entity_ids(hass: HomeAssistant) -> None:
    await _setup(hass)
    reg = er.async_get(hass)
    ids = sorted(e.entity_id for e in reg.entities.values() if e.entity_id.startswith("sensor.battman_nem_"))
    assert len(ids) == 14
    text = (CARDS / "nemmix.yaml").read_text()
    for e in re.findall(r"sensor\.battman_nem_[a-z_]+", text):
        assert e in ids, e                              # every sensor the card uses exists


# ── nemmix card ──────────────────────────────────────────────────────────────

async def test_nemmix_matches_smiggles(hass: HomeAssistant, hass_client) -> None:
    await _setup(hass)
    card = await (await (await hass_client()).get("/api/battman/cards/nemmix")).json()
    assert card["missing_map"] == [] and card["needs"] == ["power-pie-card"]
    note, gen, dem = card["config"]["cards"]
    o_gen, o_dem = yaml.safe_load((FIX / "smiggles_nemmix.yaml").read_text())
    ren = {f"sensor.opennem_sa_{k}": f"sensor.battman_nem_{k}" for k in KEYS} | {
        "sensor.sa_consumers": "sensor.battman_nem_consumers", "sensor.sa_exports": "sensor.battman_nem_exports",
        "sensor.sa_battery_charging": "sensor.battman_nem_battery_charging"}
    for o, m in ((o_gen, gen), (o_dem, dem)):
        o = {k: v for k, v in o.items() if k != "version"}
        o["entities"] = [{**e, "entity": ren[e["entity"]], "color": e["color"].replace("--smiggles-", "--battman-")}
                         for e in o["entities"]]
        assert o == m

    # the note names every NEM sensor without a value
    content = note["card"]["content"]
    hass.states.async_set("sensor.battman_nem_gas_recip", "unknown", {"problem": "sensor.opennem_sa has no value for: gas_recip"})
    out = _render(hass, content)
    assert "sensor.battman_nem_gas_recip" in out and "gas_recip" in out
    assert {c["entity"] for c in note["conditions"][0]["conditions"]} == {
        f"sensor.battman_nem_{k}" for k in [*KEYS, "exports", "battery_charging", "total_supply", "consumers"]}


# ── gauges card ──────────────────────────────────────────────────────────────

GAUGE_STATES = {
    "sensor.sigen_inverter_battery_state_of_charge": ("57.5", {}),   # what Smiggles' card read
    "sensor.sigen_plant_battery_state_of_charge": ("57.5", {}),      # what Battman's reads (v0.23.0: plant SOC)
    "sensor.sigen_plant_rated_energy_capacity": ("40.3", {}),
    "sensor.solcast_pv_forecast_forecast_remaining_today": ("20.1", {"estimate10": 14.62}),
    "sensor.sigen_plant_battery_power": ("-2.4", {}),
    "sensor.sigen_plant_pv_power": ("5.437", {}),
    "sensor.gridpower": ("1.2", {}),
    "sensor.sigen_plant_consumed_power": ("1.9", {}),
    "sensor.amber_5min_current_feed_in_price": ("-0.0812", {}),
    "sensor.amber_5min_current_general_price": ("0.1734", {}),
    "binary_sensor.solarsystemcontrolestimatedprice": ("on", {}),
    "sensor.solarsystemcontrolload30mavg": ("1.4567", {}),      # what Smiggles' card read
    "sensor.battman_load_30m_avg": ("1.46", {}),                # what Battman's card reads (v0.17.0: renamed)
    "sensor.solarsystemcontrolrun": ("ok", {"needPower": True}),
}


def _package_sensor(name):
    pkg = yaml.safe_load((FIX / "smiggles_package.yaml").read_text())
    return next(s for s in pkg["template"][0]["sensor"] if s["name"] == name)["state"]


async def test_gauges_match_smiggles(hass: HomeAssistant, hass_client) -> None:
    await _setup(hass)
    card = await (await (await hass_client()).get("/api/battman/cards/gauges")).json()
    assert card["missing_map"] == [] and card["needs"] == ["modern-circular-gauge"]
    for est in ("on", "off"):
        for e, (s, a) in GAUGE_STATES.items():
            hass.states.async_set(e, est if e.startswith("binary_sensor") else s, a)
        # the Smiggles template sensors the original gauges read, rendered by the Smiggles package
        hass.states.async_set("sensor.sockwh", _render(hass, _package_sensor("SOCkwh")))
        hass.states.async_set("sensor.solarremainingtoday10", _render(hass, _package_sensor("SolarRemainingToday10")))
        await hass.async_block_till_done()
        o_rows = yaml.safe_load((FIX / "smiggles_gauges.yaml").read_text())[0]["cards"]
        m_rows = card["config"]["cards"]
        for o_row, m_row in zip(o_rows, m_rows, strict=True):
            for o, m in zip(o_row["cards"], m_row["cards"], strict=True):
                assert _render(hass, o["secondary"]) == _render(hass, m["secondary"]), o["name"]
                rest_o = {k: v for k, v in o.items() if k not in ("secondary",)}
                rest_o = json.loads(json.dumps(rest_o).replace("--smiggles-", "--battman-")
                                    .replace('"sensor.gridpower"', '"sensor.battman_grid_power"')   # v0.17.0
                                    .replace('"sensor.sigen_inverter_battery_state_of_charge"',
                                             '"sensor.sigen_plant_battery_state_of_charge"'))       # v0.23.0
                assert rest_o == {k: v for k, v in m.items() if k != "secondary"}


async def test_gauges_unavailable(hass: HomeAssistant, hass_client) -> None:
    await _setup(hass)
    card = await (await (await hass_client()).get("/api/battman/cards/gauges")).json()
    for e, (s, a) in GAUGE_STATES.items():
        hass.states.async_set(e, "unavailable", {})
    texts = [_render(hass, g["secondary"]) for row in card["config"]["cards"] for g in row["cards"]]
    assert texts[0] == "— kWh (+—kWh)"
    assert texts[1] == "Current Solar —kW"
    assert texts[2].startswith("— ") and texts[2].endswith(" —") and "$0.00" not in texts[2]
    assert texts[3] == "Avg 30m — kW"


# ── forecast table: HA's time zone, summer and winter ────────────────────────

@needs_node
@pytest.mark.parametrize("day", ["2026-01-14", "2026-07-14"])
async def test_forecast_table_local_time(hass: HomeAssistant, hass_client, day) -> None:
    await _setup(hass)
    card = await (await (await hass_client()).get("/api/battman/cards/amber24hourforecasttable")).json()
    js = card["config"]["cards"][0]["custom_fields"]["card"]
    start = datetime.fromisoformat(f"{day}T03:00:00+00:00")
    fc = [{"start_time": start.replace(minute=m).isoformat(), "per_kwh": -0.1, "nem_date": "x"} for m in (0, 30)]
    bc = [{**f, "per_kwh": 0.2} for f in fc]
    st = {"sensor.amber_billing_interval_forecasts_feed_in_price": {"state": "0", "attributes": {"Forecasts": fc}},
          "sensor.amber_billing_interval_forecasts_general_price": {"state": "0", "attributes": {"Forecasts": bc}}}
    out = run_js([(js, st, None)])[0]
    shown = re.findall(r'<td class="at6t-td at6t-time"[^>]*>([^<—]+)</td>', out)
    want = [start.replace(minute=m).astimezone(ZoneInfo("Australia/Adelaide")).strftime("%a %H:%M") for m in (0, 30)]
    assert shown == want            # 13:30 in summer (UTC+10:30), 12:30 in winter (UTC+9:30)


# ── layout ───────────────────────────────────────────────────────────────────

async def test_power_view_section3(hass: HomeAssistant, hass_client) -> None:
    await _setup(hass)
    power = (await built(hass))["views"][0]
    assert [c["type"] for c in power["sections"][2]["cards"]] == ["custom:battman-gauges", "custom:battman-nemmix"]


# ── OpenNEM's region sensor, found by Battman (v0.22.1) ─────────────────────

async def test_opennem_found_without_configure(hass: HomeAssistant) -> None:
    from custom_components.battman.const import ENTITY_MAP_DEFAULTS

    assert "opennem" not in ENTITY_MAP_DEFAULTS                      # not on the Configure screen any more
    _opennem(hass, "sa", {**GEN, "wind": 640})
    hass.states.async_set("sensor.opennem_sa_wind", "640", {})      # OpenNEM-looking, but not OpenNEM's: ignored
    await _setup(hass)
    wind = hass.states.get("sensor.battman_nem_wind")
    assert wind.state == "640.0" and wind.attributes["source"] == "sensor.opennem_sa" and "problem" not in wind.attributes


async def test_opennem_none(hass: HomeAssistant) -> None:
    from homeassistant.helpers import issue_registry as ir

    await _setup(hass)
    wind = hass.states.get("sensor.battman_nem_wind")
    assert wind.state == "unknown" and wind.attributes["source"] is None
    assert wind.attributes["problem"] == "No OpenNEM region sensor found (is the OpenNEM integration set up?)"
    assert ir.async_get(hass).async_get_issue(DOMAIN, "opennem_choose") is None   # optional: no Repair
    # OpenNEM set up later: found and followed, no restart
    _opennem(hass, "sa", {**GEN, "wind": 300})
    await hass.async_block_till_done()
    assert hass.states.get("sensor.battman_nem_wind").state == "300.0"


async def test_opennem_switched_to_another_region(hass: HomeAssistant) -> None:
    _opennem(hass, "sa")
    await _setup(hass)
    assert hass.states.get("sensor.battman_nem_wind").attributes["source"] == "sensor.opennem_sa"
    # OpenNEM switched to VIC: the SA sensor goes, a VIC one comes
    er.async_get(hass).async_remove("sensor.opennem_sa")
    hass.states.async_remove("sensor.opennem_sa")
    _opennem(hass, "vic", {**GEN, "wind": 1500})
    await hass.async_block_till_done()
    wind = hass.states.get("sensor.battman_nem_wind")
    assert wind.state == "1500.0" and wind.attributes["source"] == "sensor.opennem_vic"
    # ...or the SA sensor lingers, unavailable with no figures: still VIC
    _opennem(hass, "sa", {}, state="unavailable")
    await hass.async_block_till_done()
    assert hass.states.get("sensor.battman_nem_wind").attributes["source"] == "sensor.opennem_vic"


async def test_opennem_several_regions(hass: HomeAssistant) -> None:
    from homeassistant.helpers import issue_registry as ir

    _opennem(hass, "sa", {**GEN, "wind": 100})
    _opennem(hass, "vic", {**GEN, "wind": 200})
    entry = await _setup(hass)
    wind = hass.states.get("sensor.battman_nem_wind")
    assert wind.state == "unknown"
    assert wind.attributes["problem"] == ("Several OpenNEM regions (sensor.opennem_sa, sensor.opennem_vic): "
                                          "pick one under Battman → Configure")
    issue = ir.async_get(hass).async_get_issue(DOMAIN, "opennem_choose")
    assert issue is not None and issue.translation_placeholders == {"regions": "sensor.opennem_sa, sensor.opennem_vic"}
    # Configure offers just the two regions
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    field = next(k for k in flow["data_schema"].schema if k == "opennem")
    sel = flow["data_schema"].schema[field]
    assert sel.config["options"] == ["sensor.opennem_sa", "sensor.opennem_vic"]
    # pick VIC -> followed, Repair gone
    hass.config_entries.async_update_entry(entry, options={"opennem": "sensor.opennem_vic"})
    await hass.async_block_till_done()
    assert hass.states.get("sensor.battman_nem_wind").state == "200.0"
    assert ir.async_get(hass).async_get_issue(DOMAIN, "opennem_choose") is None


async def test_configure_has_no_opennem_field_with_one_region(hass: HomeAssistant) -> None:
    _opennem(hass, "sa")
    entry = await _setup(hass)
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    assert "opennem" not in [str(k) for k in flow["data_schema"].schema]
