"""A test Home Assistant with Smiggles' engine (the originals, tests/fixtures/smiggles_engine)
and Battman's ported engine loaded side by side, the way A.J.'s HA will be on migration day.

Sigen / Amber / Solcast are plain states; Sigen's select / number actions are recorded.
"""

from __future__ import annotations

import random
from datetime import timedelta
from pathlib import Path
from typing import Any

import yaml

from tools.smiggles_log_text import plain_log
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

SM = Path(__file__).parent / "fixtures" / "smiggles_engine"
DOMAIN = "battman"

CONFIG = """homeassistant:
  packages: !include_dir_named packages
frontend:
  themes: !include_dir_merge_named themes
automation: !include automations.yaml
script: !include scripts.yaml
"""

LOAD_AVG = "sensor.battman_load_30m_avg"
SMIGGLES_LOAD = "sensor.solarsystemcontrolload30m"

HELPER_DOMAINS = ("input_boolean", "input_number", "input_select", "input_datetime", "input_text", "timer")

AUTOMATION_FILES = [
    "SolarSystemControl.yaml", "SolarSystemControlWatchdog.yaml", "SolarSystemControlSigMode.yaml",
    "SolarSystemControlSigCurtail.yaml", "SolarSystemControlSAPNOverride.yaml",
    "SolarSystemOverrideTimerInitialDuration.yaml", "SolarSystemControlCopyCurve.yaml",
]

# the outside world both engines read
WORLD_DEFAULTS: dict[str, Any] = {
    "sensor.sigen_plant_battery_state_of_charge": "50",
    "sensor.sigen_plant_rated_energy_capacity": "32",
    "sensor.sigen_inverter_rated_active_power": "10",
    "sensor.sigen_plant_ess_rated_charging_power": "10",
    "sensor.sigen_plant_ess_rated_discharging_power": "10",
    "sensor.sigen_plant_grid_connection_status": "On Grid",
    "sensor.sigen_plant_consumed_power": "1.2",
    "sensor.sigen_plant_grid_import_power": "0.5",
    "sensor.sigen_plant_grid_export_power": "0",
    "sensor.sigen_plant_sigen_pv_power": "3",
    "sensor.sigen_plant_third_party_pv_power": "0",
    "sensor.sigen_plant_total_imported_energy": "12000.5",
    "sensor.sigen_plant_total_exported_energy": "18000.25",
    SMIGGLES_LOAD: "1.1",
    "number.sigen_plant_grid_export_limitation": "10",
    "number.sigen_plant_pv_max_power_limit": "20",
    "number.sigen_plant_ess_max_charging_limit": "10",
    "select.sigen_plant_remote_ems_control_mode": "Maximum Self Consumption",
}


def smiggles_files() -> dict[str, Any]:
    """Smiggles' packages (as package files), script and automations, as on A.J.'s HA."""
    pkgs = {}
    for f in sorted((SM / "packages").glob("*.yaml")):
        data = yaml.safe_load(f.read_text())
        # the parts that only run shell commands / command-line sensors (not the engine)
        data.pop("shell_command", None)
        data.pop("sensor", None)
        pkgs[f.name] = data
    # the one text change Battman made to the engine (log headings instead of emoji), applied to
    # Smiggles' original too, so both engines' logs can be compared exactly
    script = yaml.safe_load(plain_log((SM / "scripts/SolarSystemControl.yaml").read_text()))
    autos = []
    for name in AUTOMATION_FILES:
        a = yaml.safe_load((SM / "automations" / name).read_text())
        a["id"] = "smiggles_" + name.split(".")[0].lower()
        autos.append(a)
    return {"packages": pkgs, "scripts": {"solarsystemcontrol": script}, "automations": autos}


def write_config(cfg: Path, smiggles: bool = True) -> None:
    (cfg / "configuration.yaml").write_text(CONFIG)
    (cfg / "packages").mkdir(exist_ok=True)
    if smiggles:
        files = smiggles_files()
        (cfg / "packages/smiggles").mkdir(exist_ok=True)
        for name, data in files["packages"].items():
            (cfg / "packages/smiggles" / name).write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
        (cfg / "scripts.yaml").write_text(yaml.safe_dump(files["scripts"], sort_keys=False, allow_unicode=True))
        (cfg / "automations.yaml").write_text(yaml.safe_dump(files["automations"], sort_keys=False, allow_unicode=True))
    else:
        (cfg / "scripts.yaml").write_text("{}\n")
        (cfg / "automations.yaml").write_text("[]\n")


class Recorder:
    """Records Sigen select / number calls (and logbook lines)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def __call__(self, call: ServiceCall) -> None:
        data = {k: v for k, v in call.data.items()}
        self.calls.append((call.domain, call.service, data))
        ent = data.get("entity_id")
        if isinstance(ent, list):
            ent = ent[0] if ent else None
        if call.domain == "select" and ent:
            call.hass.states.async_set(ent, data["option"])
        if call.domain == "number" and ent:
            call.hass.states.async_set(ent, str(data["value"]))


async def start(hass: HomeAssistant, smiggles: bool = True, world: dict | None = None) -> tuple[MockConfigEntry, Recorder]:
    cfg = Path(hass.config.config_dir)
    write_config(cfg, smiggles)
    rec = Recorder()
    hass.services.async_register("select", "select_option", rec)
    hass.services.async_register("number", "set_value", rec)
    hass.services.async_register("logbook", "log", rec)
    set_world(hass, world or {})
    assert await async_setup_component(hass, "homeassistant", {})
    assert await async_setup_component(hass, "lovelace", {})
    for domain in (*HELPER_DOMAINS, "template", "automation", "script"):
        assert await async_setup_component(hass, domain, {})
    for domain in (*HELPER_DOMAINS, "template", "script", "automation"):
        await hass.services.async_call(domain, "reload", blocking=True)
    await hass.async_block_till_done()
    entry = MockConfigEntry(domain=DOMAIN, title="Battman", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    # the load average is set by hand (set_world) to the value Smiggles' helper has
    er.async_get(hass).async_update_entity(LOAD_AVG, disabled_by=er.RegistryEntryDisabler.USER)
    await hass.async_block_till_done()
    set_world(hass, world or {})
    # Battman's own select / number entities load HA's select and number integrations, whose
    # actions replace the recorders: put the recorders back (the Sigen entities are plain states)
    hass.services.async_register("select", "select_option", rec)
    hass.services.async_register("number", "set_value", rec)
    return entry, rec


def set_world(hass: HomeAssistant, world: dict) -> None:
    now = dt_util.now()
    states = {**WORLD_DEFAULTS, **{k: v for k, v in world.items() if "." in k}}
    for ent, val in states.items():
        hass.states.async_set(ent, val)
    # Smiggles reads its 30-minute load helper; Battman works its own out from home power over
    # 30 minutes (a Statistics sensor, switched off by start() for these runs). For a like-for-like
    # run both engines see the same average.
    entry = er.async_get(hass).async_get(LOAD_AVG)
    if entry is not None and entry.disabled_by is not None:
        hass.states.async_set(LOAD_AVG, states[SMIGGLES_LOAD], {"unit_of_measurement": "kW"})
    buy = float(world.get("buy", 0.2))
    sell = float(world.get("sell", 0.05))
    rnd = random.Random(world.get("seed", 1))
    start_ = now.replace(second=0, microsecond=0) - timedelta(minutes=now.minute % 5)
    est = world.get("estimate", False)
    price_attrs = {"start_time": (start_).isoformat(), "end_time": (start_ + timedelta(minutes=5)).isoformat(),
                   "estimate": est}
    hass.states.async_set("sensor.amber_5min_current_general_price", str(buy), {**price_attrs, "per_kwh": buy})
    hass.states.async_set("sensor.amber_5min_current_feed_in_price", str(sell), {**price_attrs, "per_kwh": -sell})

    def fc(base: float, sign: float) -> list[dict]:
        out = []
        for i in range(48):
            st = start_ + timedelta(minutes=30 * i)
            v = round(base * (0.5 + rnd.random() * 1.5), 4)
            out.append({"start_time": st.isoformat(), "end_time": (st + timedelta(minutes=30)).isoformat(),
                        "duration": 30, "per_kwh": round(sign * v, 4), "spot_per_kwh": v, "estimate": True})
        return out

    hass.states.async_set("sensor.amber_billing_interval_forecasts_general_price", str(buy),
                          {"Forecasts": fc(buy, 1)})
    hass.states.async_set("sensor.amber_billing_interval_forecasts_feed_in_price", str(sell),
                          {"Forecasts": fc(sell, -1)})
    rem = float(world.get("pv_remaining", 10))
    hass.states.async_set("sensor.solcast_pv_forecast_forecast_remaining_today", str(rem),
                          {"estimate": rem, "estimate10": rem * 0.7, "estimate90": rem * 1.2})
    nh = float(world.get("pv_next_hour", 1.5))
    hass.states.async_set("sensor.solcast_pv_forecast_forecast_next_hour", str(nh),
                          {"estimate": nh, "estimate10": nh * 0.7, "estimate90": nh * 1.2})


async def tick(hass: HomeAssistant, seconds: float = 3) -> None:
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=seconds))
    await hass.async_block_till_done()


def curves(rnd: random.Random) -> tuple[dict, dict]:
    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    soc, price = {}, {}
    for m in months:
        soc[m] = {k: [rnd.randint(lo, hi) for _ in range(24)] for k, lo, hi in
                  (("sell", 20, 95), ("buy", 5, 60), ("sell_high", 30, 99), ("buy_high", 10, 70))}
        price[m] = {k: {"high": [rnd.randint(5, 60) for _ in range(24)], "low": [rnd.randint(0, 30) for _ in range(24)]}
                    for k in ("sell", "buy", "sell_high", "buy_high")}
    return soc, price
