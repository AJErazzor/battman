"""v0.17.0: Battman's package files (packages/battman/), with the grid power template sensor
(Smiggles' GridPower, renamed so history carries over) and the 30-minute load average (a
Statistics sensor of home power since v0.19.0), the Log page's grid graph from import / export
history."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.template import Template
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

DOMAIN = "battman"
FIX = Path(__file__).parent / "fixtures"
LOG = Path(__file__).parents[1] / "custom_components/battman/www/battman-log.js"
IMP, EXP = "sensor.sigen_plant_grid_import_power", "sensor.sigen_plant_grid_export_power"
HOME = "sensor.sigen_plant_consumed_power"
CASES = [("2.345", "0"), ("0.04", "0.01"), ("0", "3.217"), ("1.5", "1.5"), ("0.06", "0.02"), ("0.02", "0.06"), ("0", "0")]


PACKAGES = "homeassistant:\n  packages: !include_dir_named packages\n"


async def _setup(hass, packages=True):
    cfg = Path(hass.config.config_dir)
    (cfg / "configuration.yaml").write_text(PACKAGES if packages else "")
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain=DOMAIN, title="Battman", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _smiggles(name):
    pkg = yaml.safe_load((FIX / "smiggles_package.yaml").read_text())
    return next(s for s in pkg["template"][0]["sensor"] if s["name"] == name)["state"]


async def test_grid_power_matches_smiggles(hass: HomeAssistant) -> None:
    await _setup(hass)
    tpl = Template(_smiggles("GridPower"), hass)
    for imp, exp in CASES:
        hass.states.async_set(IMP, imp)
        hass.states.async_set(EXP, exp)
        await hass.async_block_till_done()
        st = hass.states.get("sensor.battman_grid_power")
        assert float(st.state) == float(tpl.async_render(parse_result=False).strip()), (imp, exp)
        assert st.attributes["unit_of_measurement"] == "kW" and st.attributes["device_class"] == "power"
    hass.states.async_set(EXP, "unavailable")
    await hass.async_block_till_done()
    assert hass.states.get("sensor.battman_grid_power").state == "unavailable"     # Smiggles showed 0


async def test_load_30m_avg_is_the_mean_of_home_power(hass: HomeAssistant) -> None:
    """v0.19.0: a Statistics sensor of home power (the same settings as Smiggles' helper:
    mean, 30 minutes, 2 decimals), not a copy of that helper."""
    await _setup(hass)
    for v in ("2.0", "3.456"):
        hass.states.async_set(HOME, v, {"unit_of_measurement": "kW"})
        await hass.async_block_till_done()
    st = hass.states.get("sensor.battman_load_30m_avg")
    assert float(st.state) == round((2.0 + 3.456) / 2, 2)
    assert st.attributes["unit_of_measurement"] == "kW"
    reg = er.async_get(hass)
    assert reg.async_get_entity_id("sensor", "statistics", "battman_load_30m_avg") == "sensor.battman_load_30m_avg"


async def test_follows_the_map(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    hass.states.async_set("sensor.my_power", "2.5", {"unit_of_measurement": "kW"})
    hass.config_entries.async_update_entry(entry, options={"home_power": "sensor.my_power"})
    await hass.async_block_till_done()
    for v in ("3.5", "4.5"):
        hass.states.async_set("sensor.my_power", v, {"unit_of_measurement": "kW"})
        await hass.async_block_till_done()
    assert float(hass.states.get("sensor.battman_load_30m_avg").state) == 4.0
    text = (Path(hass.config.config_dir) / "packages/battman/battman_sensors.yaml").read_text()
    assert "sensor.my_power" in text and "[[map:" not in text


async def test_package_file_and_unique_ids(hass: HomeAssistant) -> None:
    await _setup(hass)
    f = Path(hass.config.config_dir) / "packages/battman/battman_sensors.yaml"
    assert f.exists() and "Managed by Battman" in f.read_text()
    reg = er.async_get(hass)
    assert reg.async_get_entity_id("sensor", "template", "battman_grid_power") == "sensor.battman_grid_power"
    assert reg.async_get_entity_id("sensor", "statistics", "battman_load_30m_avg") == "sensor.battman_load_30m_avg"
    assert ir.async_get(hass).async_get_issue(DOMAIN, "packages_not_loaded") is None


async def test_load_avg_keeps_its_entity_when_it_moves_off_template(hass: HomeAssistant) -> None:
    """Updating from v0.18: the old template entry held sensor.battman_load_30m_avg. Battman
    removes it, so the Statistics sensor takes the same entity ID (same history), not a _2."""
    reg = er.async_get(hass)
    reg.async_get_or_create("sensor", "template", "battman_load_30m_avg", suggested_object_id="battman_load_30m_avg")
    await _setup(hass)
    assert reg.async_get_entity_id("sensor", "template", "battman_load_30m_avg") is None
    assert reg.async_get_entity_id("sensor", "statistics", "battman_load_30m_avg") == "sensor.battman_load_30m_avg"
    assert reg.async_get_entity_id("sensor", "template", "battman_grid_power") == "sensor.battman_grid_power"


async def test_renamed_smiggles_sensor_keeps_its_entity(hass: HomeAssistant) -> None:
    """The rename path: a sensor already registered with this unique ID under another entity
    ID (as after adding the unique_id to Smiggles' GridPower and renaming it) is the same entity."""
    reg = er.async_get(hass)
    reg.async_get_or_create("sensor", "template", "battman_grid_power", suggested_object_id="gridpower")
    await _setup(hass)
    assert reg.async_get_entity_id("sensor", "template", "battman_grid_power") == "sensor.gridpower"
    assert hass.states.get("sensor.gridpower") is not None          # same entity, so same history


async def test_repair_without_packages(hass: HomeAssistant) -> None:
    await _setup(hass, packages=False)
    issue = ir.async_get(hass).async_get_issue(DOMAIN, "packages_not_loaded")
    assert issue is not None and "battman_grid_power" in issue.translation_placeholders["missing"]


async def test_map_and_views(hass: HomeAssistant, hass_client) -> None:
    await _setup(hass)
    client = await hass_client()
    emap = (await (await client.get("/api/battman/entities")).json())["entities"]
    assert emap["grid_power"] == "sensor.battman_grid_power"
    assert emap["load_30m_avg"] == "sensor.battman_load_30m_avg"
    # Battman's grid power sensor feeds the Gauges card (the History view that also used it is gone)
    gauges = await (await client.get("/api/battman/cards/gauges")).json()
    text = json.dumps(gauges["config"])
    assert "sensor.battman_grid_power" in text and "sensor.gridpower" not in text and "[[map:" not in text


@pytest.mark.skipif(not shutil.which("node"), reason="needs node")
def test_log_card_grid_from_import_export() -> None:
    html = LOG.read_text()
    a = html.index("  function gridSeries(imp, exp) {")
    b = html.index("\n  }\n", a) + 4
    fn = html[a:b]
    pts = lambda vals: [{"last_changed": f"2026-10-20T0{i}:00:00Z", "state": v} for i, v in enumerate(vals)]
    imp = pts(["2.345", "0", "0.06", "unavailable"])
    exp = pts(["0", "3.217", "0.02", "0"])
    js = fn + f"process.stdout.write(JSON.stringify(gridSeries({json.dumps(imp)}, {json.dumps(exp)})));"
    out = json.loads(subprocess.run(["node", "-"], input=js, capture_output=True, text=True, check=True).stdout)
    states = [p["state"] for p in out]
    # import/export arrive as separate points; the last value at each time is the rule's result
    assert states[1] == "2.35" and states[3] == "-3.22" and states[5] == "0.06" and states[6] == "unavailable"
    assert "Grid (kW)" in html and "M.grid_power" not in html
