"""v0.17.0: Battman's engine (Smiggles' engine ported like for like) and Migrate / Hand back.

The proof: Smiggles' original engine and Battman's port are loaded in the same test HA and
given the same world (SOC, prices, forecasts, solar, time, settings, overrides, curves);
they must make the same decisions and write the same run data and log line."""

import pytest
from homeassistant.core import HomeAssistant

from . import engine_harness as H


async def test_both_engines_load(hass: HomeAssistant, caplog) -> None:
    entry, _ = await H.start(hass)
    for ent in ("sensor.solarsystemcontrolparameters", "script.solarsystemcontrol", "automation.solarsystemcontrol",
                "input_select.solarsystemcontrolmode", "timer.solarsystemoverridetimer"):
        assert hass.states.get(ent) is not None, ent
    for ent in ("sensor.battman_parameters", "script.battman_engine", "script.battman_apply_scene",
                "input_select.battman_mode", "timer.battman_override_timer", "binary_sensor.battman_in_charge"):
        assert hass.states.get(ent) is not None, ent
    from custom_components.battman import engine
    ids = engine.entity_ids(hass)
    assert all(ids.values()), ids
    assert ids["battman_engine_loop"] == "automation.battman_engine_main_loop"
    assert all(hass.states.get(e).state == "on" for e in ids.values() if e.startswith("automation."))
    assert hass.states.get("binary_sensor.battman_in_charge").state == "off"
    # Battman's engine sensors don't move before migrating
    assert hass.states.get("sensor.battman_parameters").state == "unknown"
    # errors: only Smiggles' own (its copy-curves automation can't load; power provider without a tariff)
    bad = [r.getMessage() for r in caplog.records if r.levelname == "ERROR"
           and "Smiggles - Copy" not in r.getMessage() and "solarsystemcontrolpowerprovider" not in r.getMessage()
           and "None has no element" not in r.getMessage()]
    assert not bad, bad


# ── decision equivalence ───────────────────────────────────────────────────────────────
import random
from datetime import datetime
from zoneinfo import ZoneInfo

from custom_components.battman import migrate
from custom_components.battman.const import ENGINE_MAP, IN_CHARGE, SMIGGLES_NAMES

MODES = ["Self Consume", "Discharge", "Charge", "Charge Solar Off", "Float", "Float Solar Off", "Solar Soak", "Drain"]
# run data that's a time stamp, so differs by when each ran
TIME_ATTRS = {"lastRunAt"}


def scenarios(n: int = 300) -> list[dict]:
    rnd = random.Random(20261021)
    out = []
    for i in range(n):
        p: dict = {"action": "SetAttribute"}
        kind = i % 6
        if kind == 1:
            p.update(sellOverrideSOC=rnd.choice([20, 40, 60]), sellOverridePrice=rnd.choice([0, 10, 25]))
        elif kind == 2:
            p.update(buyAnytimeSOC=rnd.choice([30, 60, 90]), buyAnytimePrice=rnd.choice([5, 15, 30]))
        elif kind == 3:
            p.update(drainBatterySOC=rnd.choice([10, 30]), drainBatteryPrice=rnd.choice([0, 8]),
                     drainBatteryPlughole=rnd.choice([True, False]))
        elif kind == 4:
            p.update(sellSolarSOC=rnd.choice([50, 80]), sellSolarPrice=rnd.choice([5, 12]),
                     buyOverrideSOC=rnd.choice([20, 50]), buyOverridePrice=rnd.choice([5, 20]))
        elif kind == 5:
            p.update(netTargetSellPrice=rnd.choice([0, 1.5]), netTargetBuyPrice=rnd.choice([0, 0.5]),
                     needyTriggerConsumption=rnd.choice([0.5, 2, 6]), needyTriggerPVGap=rnd.choice([-5, 3, 15]))
        out.append({
            "params": p,
            "when": datetime(2026, rnd.choice([1, 4, 7, 10, 12]), rnd.randint(1, 27), rnd.randint(0, 23),
                             rnd.choice([0, 7, 22, 37, 52]), 10, tzinfo=ZoneInfo("Australia/Adelaide")),
            "world": {
                "seed": i,
                "sensor.sigen_plant_battery_state_of_charge": str(rnd.choice([3, 10, 25, 40, 55, 70, 85, 98, 100])),
                "buy": rnd.choice([-0.08, 0.0, 0.04, 0.12, 0.25, 0.45, 1.5]),
                "sell": rnd.choice([-0.05, 0.0, 0.03, 0.09, 0.2, 0.6, 2.5]),
                "estimate": rnd.choice([True, False]),
                "pv_remaining": rnd.choice([0, 2, 8, 20, 40]),
                "pv_next_hour": rnd.choice([0, 0.5, 3, 6]),
                "sensor.solarsystemcontrolload30m": str(rnd.choice([0.3, 1.2, 3.0, 7.5])),
                "sensor.sigen_plant_grid_connection_status": rnd.choice(["On Grid", "On Grid", "Off Grid"]),
            },
            "mode": rnd.choice(MODES),
            "no_export": rnd.choice(["on", "off"]),
            "rules": rnd.choice([True, False]),
            "curves_seed": rnd.randint(0, 3),
        })
    return out


def _fire(hass, key: str, data: dict) -> None:
    hass.bus.async_fire(SMIGGLES_NAMES[key], data)
    hass.bus.async_fire(ENGINE_MAP[key], data)


# settings Battman added after the port (Smiggles never had them): left out of the like-for-like checks
BATTMAN_ONLY_ATTRS = {"dashboardTheme"}


def _strip(attrs) -> dict:
    return {k: v for k, v in attrs.items()
            if k not in ("friendly_name", "icon") and k not in TIME_ATTRS and k not in BATTMAN_ONLY_ATTRS}


async def _same_store(hass, key: str) -> None:
    a, b = hass.states.get(SMIGGLES_NAMES[key]), hass.states.get(ENGINE_MAP[key])
    assert a is not None and b is not None, key
    assert (a.state, _strip(a.attributes)) == (b.state, _strip(b.attributes)), key


async def test_engine_decides_like_smiggles(hass: HomeAssistant, freezer) -> None:
    await hass.config.async_set_time_zone("Australia/Adelaide")
    freezer.move_to(datetime(2026, 10, 21, 9, 0, 10, tzinfo=ZoneInfo("Australia/Adelaide")))
    entry, _rec = await H.start(hass)
    # only the scripts run here (each engine's automations are tested on their own below)
    await hass.services.async_call("automation", "turn_off", {"entity_id": "all"}, blocking=True)
    hass.config_entries.async_update_entry(entry, data={**entry.data, IN_CHARGE: True})
    await hass.async_block_till_done()

    seen_modes, compared = set(), 0
    tally = __import__("collections").Counter()
    for n, sc in enumerate(scenarios()):
        freezer.move_to(sc["when"])
        H.set_world(hass, sc["world"])
        soc, price = H.curves(random.Random(sc["curves_seed"]))
        _fire(hass, "soc_curves_update_event", {"curves": soc})
        _fire(hass, "price_curves_update_event", {"curves": price})
        for k in ("buy_rules_event", "sell_rules_event"):
            _fire(hass, k, {"attribute": "state", "value": sc["rules"]})
        _fire(hass, "parameters_update_event", sc["params"])
        await hass.async_block_till_done()
        for key in ("parameters", "soc_curves", "price_curves", "buy_rules", "sell_rules"):
            await _same_store(hass, key)
        for key in ("mode",):
            for ent in (SMIGGLES_NAMES[key], ENGINE_MAP[key]):
                await hass.services.async_call("input_select", "select_option",
                                               {"entity_id": ent, "option": sc["mode"]}, blocking=True)
        for ent in (SMIGGLES_NAMES["no_export"], ENGINE_MAP["no_export"]):
            await hass.services.async_call("input_boolean", f"turn_{sc['no_export']}", {"entity_id": ent}, blocking=True)

        await hass.services.async_call("script", "turn_on", {"entity_id": [SMIGGLES_NAMES["control_script"],
                                                                         ENGINE_MAP["control_script"]]}, blocking=True)
        await H.tick(hass, 3)
        await H.tick(hass, 1)
        for key in ("mode", "no_export"):
            a, b = hass.states.get(SMIGGLES_NAMES[key]).state, hass.states.get(ENGINE_MAP[key]).state
            assert a == b, (n, key, a, b, sc)
        await _same_store(hass, "run")
        la = hass.states.get(SMIGGLES_NAMES["debug_log"]).attributes["message"]
        lb = hass.states.get(ENGINE_MAP["debug_log"]).attributes["message"]
        assert la == lb, (n, la, lb)
        seen_modes.add(hass.states.get(ENGINE_MAP["mode"]).state)
        tally[(hass.states.get(ENGINE_MAP["mode"]).state, hass.states.get(ENGINE_MAP["no_export"]).state)] += 1
        compared += 1
    assert compared == len(scenarios())
    print("\nengine decisions (mode, no export):", dict(tally))
    # the scenarios reach most of the engine's decisions
    assert len(seen_modes) >= 4, seen_modes


# ── the automations: same Sigen actions, same store changes ─────────────────────────────
from datetime import timedelta

from homeassistant.util import dt as dt_util

SM_AUTO = {   # Smiggles automation entity -> Battman engine item
    "automation.solarsystemcontrolsigmode": "battman_engine_sig_mode",
    "automation.solarsystemcontrolsigcurtail": "battman_engine_sig_curtail",
    "automation.solarsystemcontrolsapnoverride": "battman_engine_sapn_override",
    "automation.solarsystem_override_timer_initial_duration": "battman_engine_timer_duration",
    "automation.solarsystemcontrolwatchdog": "battman_engine_watchdog",
    "automation.solarsystemcontrol": "battman_engine_loop",
}


async def _only(hass, entity_ids: list[str]) -> None:
    await hass.services.async_call("automation", "turn_off", {"entity_id": "all"}, blocking=True)
    if entity_ids:
        await hass.services.async_call("automation", "turn_on", {"entity_id": entity_ids}, blocking=True)


def _sigen(rec) -> list:
    return [c for c in rec.calls if c[0] in ("select", "number")]


async def _engines(hass):
    from custom_components.battman import engine

    entry, rec = await H.start(hass)
    hass.config_entries.async_update_entry(entry, data={**entry.data, IN_CHARGE: True})
    await hass.async_block_till_done()
    ids = engine.entity_ids(hass)
    for sm in SM_AUTO:
        assert hass.states.get(sm) is not None, sm
    for ent in (SMIGGLES_NAMES["enable"], ENGINE_MAP["enable"]):
        await hass.services.async_call("input_boolean", "turn_on", {"entity_id": ent}, blocking=True)
    return entry, rec, ids


async def _compare(hass, rec, ids, sm_auto: str, act, *, settle: float = 2) -> list:
    """Run act(side) with only Smiggles' automation on, then only Battman's: same Sigen calls."""
    out = []
    for side in ("smiggles", "battman"):
        H.set_world(hass, {})
        await _only(hass, [sm_auto if side == "smiggles" else ids[SM_AUTO[sm_auto]]])
        rec.calls.clear()
        await act(SMIGGLES_NAMES if side == "smiggles" else ENGINE_MAP)
        await H.tick(hass, settle)
        out.append(_sigen(rec))
    assert out[0] == out[1], (sm_auto, out)
    return out[0]


async def test_sigen_mode_like_smiggles(hass: HomeAssistant) -> None:
    _entry, rec, ids = await _engines(hass)
    for start_mode in ("Self Consume", "Charge"):
        for mode in MODES:
            if mode == start_mode:
                continue

            async def act(names, mode=mode, start_mode=start_mode):
                await _only(hass, [])
                await hass.services.async_call("input_select", "select_option",
                                               {"entity_id": names["mode"], "option": start_mode}, blocking=True)
                await H.tick(hass, 2)
                await _only(hass, ["automation.solarsystemcontrolsigmode" if names is SMIGGLES_NAMES
                                   else ids["battman_engine_sig_mode"]])
                rec.calls.clear()
                await hass.services.async_call("input_select", "select_option",
                                               {"entity_id": names["mode"], "option": mode}, blocking=True)

            calls = await _compare(hass, rec, ids, "automation.solarsystemcontrolsigmode", act)
            assert calls and calls[0][0] == "select", (mode, calls)


async def test_curtail_and_sapn_like_smiggles(hass: HomeAssistant) -> None:
    _entry, rec, ids = await _engines(hass)
    for state in ("on", "off", "on"):
        async def act(names, state=state):
            await hass.services.async_call("input_boolean", f"turn_{'off' if state == 'on' else 'on'}",
                                           {"entity_id": names["no_export"]}, blocking=False)
            await hass.async_block_till_done()
            rec.calls.clear()
            await hass.services.async_call("input_boolean", f"turn_{state}", {"entity_id": names["no_export"]},
                                           blocking=True)
        calls = await _compare(hass, rec, ids, "automation.solarsystemcontrolsigcurtail", act)
        assert calls[-1][2]["value"] == (0 if state == "on" else 18.2)

    async def sapn(names):
        await hass.services.async_call("input_boolean", "turn_on", {"entity_id": names["no_export"]}, blocking=True)
        hass.states.async_set("number.sigen_plant_grid_export_limitation", "0")
        await hass.async_block_till_done()
        hass.states.async_set("number.sigen_plant_grid_export_limitation", "5")   # SAPN puts it back up
    calls = await _compare(hass, rec, ids, "automation.solarsystemcontrolsapnoverride", sapn)
    assert calls == [("number", "set_value", {"value": 0, "entity_id": ["number.sigen_plant_grid_export_limitation"]})] \
        or calls[-1][2]["value"] == 0


async def test_timer_and_watchdog_like_smiggles(hass: HomeAssistant) -> None:
    _entry, rec, ids = await _engines(hass)
    over = {"action": "SetAttribute", "sellOverrideSOC": 40, "sellOverridePrice": 10, "sellOverrideAllowReset": True,
            "buyAnytimeSOC": 60, "buyAnytimePrice": 15, "buyAnytimeAllowReset": True}
    results = {}
    for side, names in (("smiggles", SMIGGLES_NAMES), ("battman", ENGINE_MAP)):
        await _only(hass, [a if side == "smiggles" else ids[b] for a, b in SM_AUTO.items()
                           if b in ("battman_engine_timer_duration", "battman_engine_watchdog")])
        hass.bus.async_fire(names["parameters_update_event"], over)
        await hass.async_block_till_done()
        await hass.services.async_call("timer", "start", {"entity_id": names["override_timer"]}, blocking=True)
        await H.tick(hass, 1)
        t = hass.states.get(names["override_timer"])
        assert t.state == "active"
        left = dt_util.parse_datetime(t.attributes["finishes_at"]) - dt_util.utcnow()
        assert timedelta(minutes=9) < left <= timedelta(minutes=10, seconds=1), (side, left)   # initial 10 min
        await H.tick(hass, 11 * 60)                                                               # timer ends
        await H.tick(hass, 61)
        p = hass.states.get(names["parameters"]).attributes
        results[side] = {k: p.get(k) for k in over if k != "action"}
        results[side]["mode"] = hass.states.get(names["mode"]).state
    assert results["smiggles"] == results["battman"], results


async def test_apply_scene_like_smiggles(hass: HomeAssistant) -> None:
    _entry, _rec, _ids = await _engines(hass)
    await _only(hass, [])
    presets = [{"name": "Morning BE", "values": {"sell": {"soc": 35, "price": 12}, "drain": {"soc": 20, "price": 0,
                                                 "allowReset": False}, "net": {"side": "sell", "price": 1.2}},
                "timer": 5400}]
    out = {}
    for side, names in (("smiggles", SMIGGLES_NAMES), ("battman", ENGINE_MAP)):
        hass.bus.async_fire(names["parameters_update_event"], {"action": "SetAttribute", "overridePresets": presets})
        await hass.async_block_till_done()
        await hass.services.async_call("script", "turn_on", {"entity_id": names["apply_scene_script"],
                                                             "variables": {"name": "Morning BE"}}, blocking=True)
        await H.tick(hass, 1)
        p = dict(hass.states.get(names["parameters"]).attributes)
        t = hass.states.get(names["override_timer"])
        out[side] = ({k: v for k, v in p.items() if "Override" in k or "drain" in k or "netTarget" in k
                      or "sellSolar" in k or "buyAnytime" in k}, t.state)
    assert out["smiggles"] == out["battman"], out
    assert out["battman"][1] == "active"


async def test_main_loop_runs_the_engine_only_in_charge(hass: HomeAssistant) -> None:
    entry, rec, ids = await _engines(hass)
    await _only(hass, [ids["battman_engine_loop"]])
    hass.bus.async_fire(ENGINE_MAP["parameters_update_event"], {"action": "SetAttribute"})   # settings at defaults
    soc, price = H.curves(random.Random(1))
    hass.bus.async_fire(ENGINE_MAP["soc_curves_update_event"], {"curves": soc})
    hass.bus.async_fire(ENGINE_MAP["price_curves_update_event"], {"curves": price})
    await hass.async_block_till_done()
    await H.tick(hass, 3)
    runs = []
    hass.bus.async_listen("battman_run_update", lambda e: runs.append(e))
    hass.states.async_set("sensor.amber_5min_current_feed_in_price", "0.07",
                          {**hass.states.get("sensor.amber_5min_current_feed_in_price").attributes, "estimate": True})
    await hass.async_block_till_done()
    H.set_world(hass, {"estimate": False})
    await H.tick(hass, 3)
    await H.tick(hass, 1)
    assert len(runs) >= 1                                   # estimated-price change ran the engine
    # out of charge: nothing runs, nothing reaches Sigen, Battman's sensors stand still
    hass.config_entries.async_update_entry(entry, data={**entry.data, IN_CHARGE: False})
    await hass.async_block_till_done()
    await _only(hass, list(ids[k] for k in ids if k.startswith("battman_engine_")))
    runs.clear()
    rec.calls.clear()
    before = hass.states.get("sensor.battman_parameters")
    H.set_world(hass, {"estimate": True})
    await H.tick(hass, 3)
    await hass.services.async_call("input_select", "select_option",
                                   {"entity_id": ENGINE_MAP["mode"], "option": "Discharge"}, blocking=True)
    await hass.services.async_call("input_boolean", "turn_on", {"entity_id": ENGINE_MAP["no_export"]}, blocking=True)
    hass.bus.async_fire(ENGINE_MAP["parameters_update_event"], {"action": "SetAttribute", "sellOverrideSOC": 11})
    await H.tick(hass, 65)
    assert runs == [] and _sigen(rec) == []
    assert hass.states.get("sensor.battman_parameters").attributes == before.attributes


# ── Migrate and Hand back ─────────────────────────────────────────────────────────────
from pathlib import Path

from custom_components.battman.const import MIGRATED

SM_LOG = "2026-10-20T09:00:00.123456+10:30|first run\n2026-10-20T09:05:00.5+10:30|second run\n"


async def _smiggles_running(hass):
    """Smiggles in charge with real values everywhere; Battman installed alongside."""
    entry, rec = await H.start(hass)
    hass.bus.async_fire("solarsystemcontrolparametersupdate", {"action": "SetAttribute", "sellOverrideSOC": 42,
                        "sellOverridePrice": 18, "needyTriggerConsumption": 4.5, "dailyNetworkCharge": 1.25})
    soc, price = H.curves(random.Random(7))
    hass.bus.async_fire("solar_system_control_soc_curves_update", {"curves": soc})
    hass.bus.async_fire("solar_system_control_price_curves_update", {"curves": price})
    hass.bus.async_fire("solarsystemcontrolbuyrulesattribute", {"attribute": "state", "value": True})
    await hass.async_block_till_done()
    # cost odometers mid-month, as Smiggles left them
    for ent in ("sensor.solarsystemcontrolbuytotal", "sensor.solarsystemcontrolselltotal",
                "sensor.solarsystemcontrolnetworkaccessfee"):
        hass.states.async_set(ent, "0")          # as after Smiggles' first day
    hass.bus.async_fire("solarsystemcontroltotalattribute", {})
    await hass.async_block_till_done()
    for ent, total in (("sensor.solarsystemcontrolbuytotal", "1234.5678"), ("sensor.solarsystemcontrolselltotal", "2345.25")):
        attrs = dict(hass.states.get(ent).attributes)
        assert "day" in attrs and "month" in attrs, attrs
        hass.states.async_set(ent, total, {**attrs, "day": 1.5, "month": 40.25, "last_energy": 12000.5})
    await hass.services.async_call("input_boolean", "turn_on", {"entity_id": "input_boolean.solarsystemcontrolenable"}, blocking=True)
    await hass.services.async_call("input_select", "select_option", {"entity_id": "input_select.solarsystemcontrolmode",
                                                                     "option": "Charge"}, blocking=True)
    await hass.services.async_call("input_boolean", "turn_on", {"entity_id": "input_boolean.solarsystemcontrolnoexport"}, blocking=True)
    await hass.services.async_call("timer", "start", {"entity_id": "timer.solarsystemoverridetimer"}, blocking=True)
    await H.tick(hass, 2)
    log = Path(hass.config.path("smiggles/solar_debug.log"))
    log.parent.mkdir(exist_ok=True)
    log.write_text(SM_LOG)
    return entry, rec


async def test_migrate_dry_run_changes_nothing(hass: HomeAssistant) -> None:
    entry, _rec = await _smiggles_running(hass)
    before = {s.entity_id: (s.state, dict(s.attributes)) for s in hass.states.async_all()
              if not s.entity_id.startswith(("sensor.amber", "binary_sensor.battman_estimated", "binary_sensor.solarsystem"))}
    plan = await hass.services.async_call("battman", "migrate_from_smiggles", {}, blocking=True, return_response=True)
    assert plan["dry_run"] and plan["can_migrate"], plan
    names = {a["entity_id"] for a in plan["turn_off"]}
    assert {"automation.solarsystemcontrol", "automation.solarsystemcontrolwatchdog", "automation.solarsystemcontrolsigmode",
            "automation.solarsystemcontrolsigcurtail", "automation.solarsystemcontrolsapnoverride",
            "automation.solarsystem_override_timer_initial_duration",
            "automation.ssc_apply_armed_scene_00_01"} <= names, names
    assert not any(n.startswith("automation.battman") for n in names)
    assert {"from": "sensor.solarsystemcontrolparameters", "to": "sensor.battman_parameters"} == {
        k: v for k, v in plan["copy"][0].items() if k != "value"}
    await hass.async_block_till_done()
    after = {s.entity_id: (s.state, dict(s.attributes)) for s in hass.states.async_all() if s.entity_id in before}
    changed = [e for e in before if before[e] != after.get(e) and not e.startswith(("timer.", "automation."))]
    assert changed == [], changed
    assert not entry.data.get(MIGRATED)


async def test_migrate_then_hand_back(hass: HomeAssistant, hass_client) -> None:
    entry, rec = await _smiggles_running(hass)
    sm_before = {k: hass.states.get(SMIGGLES_NAMES[k]) for k in migrate.SENSOR_KEYS}
    on_before = [a.entity_id for a in migrate.smiggles_automations(hass) if a.state == "on"]
    assert len(on_before) >= 7

    report = await hass.services.async_call("battman", "migrate_from_smiggles", {"confirm": True},
                                            blocking=True, return_response=True)
    await H.tick(hass, 3)
    await H.tick(hass, 1)
    assert not report["dry_run"]
    # Smiggles is off, completely
    assert all(hass.states.get(e).state == "off" for e in on_before)
    assert hass.states.get("input_boolean.solarsystemcontrolenable").state == "off"
    assert hass.states.get("binary_sensor.battman_in_charge").state == "on"
    assert entry.data[MIGRATED] is True
    # Battman has Smiggles' values
    for k in ("parameters", "soc_curves", "price_curves", "buy_rules", "buy_total", "sell_total"):
        a, b = sm_before[k], hass.states.get(ENGINE_MAP[k])
        if not k.endswith("_curves"):            # a curves sensor's state is just when it last changed
            assert b.state == a.state, k
        skip = migrate.OWN_ATTRS | BATTMAN_ONLY_ATTRS
        assert {x: y for x, y in a.attributes.items() if x not in skip} == \
               {x: y for x, y in b.attributes.items() if x not in skip}, k
    # ...as the sensors' own values, so they survive a restart (what HA saves to restore them)
    comp = hass.data["entity_components"]["sensor"]
    for k in ("parameters", "soc_curves", "price_curves", "buy_rules", "buy_total", "sell_total", "run"):
        ent = comp.get_entity(ENGINE_MAP[k])
        saved = ent.extra_restore_state_data.as_dict()["native_value"]
        assert str(saved) == hass.states.get(ENGINE_MAP[k]).state, (k, saved)
    assert hass.states.get(ENGINE_MAP["mode"]).state in MODES
    assert hass.states.get(ENGINE_MAP["no_export"]).state in ("on", "off")
    assert hass.states.get(ENGINE_MAP["enable"]).state == "on"
    t = hass.states.get(ENGINE_MAP["override_timer"])
    assert t.state == "active"
    left = dt_util.parse_datetime(t.attributes["finishes_at"]) - dt_util.utcnow()
    assert timedelta(minutes=9) < left < timedelta(minutes=10)          # Smiggles' timer, carried on
    log = Path(hass.config.path("battman/engine.log")).read_text()
    assert log.startswith(SM_LOG)
    # the engine ran once straight away, and logged
    assert hass.states.get(ENGINE_MAP["run"]).attributes.get("lastRunAt")
    assert log.count("\n") >= 3
    # the cards now point at Battman's entities
    client = await hass_client()
    emap = (await (await client.get("/api/battman/entities")).json())["entities"]
    assert emap["parameters"] == "sensor.battman_parameters" and emap["mode"] == "input_select.battman_mode"
    lines = (await (await client.get("/api/battman/log", params={"start": "2026-10-20 00:00:00",
                                                                  "end": "2026-10-20 09:01:00"})).json())["lines"]
    assert lines == ["2026-10-20T09:00:00.123456+10:30|first run"]

    # the Live Activity follows too (its blueprint defaults come from the map)
    bp = Path(hass.config.path("blueprints/script/battman/battman_live_activity_push.yaml")).read_text()
    assert "default: input_select.battman_mode" in bp and "solarsystemcontrol" not in bp
    # settings changes carry on from the copied values (one attribute changed, the rest kept)
    hass.bus.async_fire("battman_parameters_update", {"action": "SetAttribute", "sellOverridePrice": 22})
    await hass.async_block_till_done()
    p = hass.states.get("sensor.battman_parameters").attributes
    assert (p["sellOverridePrice"], p["sellOverrideSOC"], p["needyTriggerConsumption"], p["dailyNetworkCharge"]) == \
           (22.0, 42.0, 4.5, 1.25)
    # one engine acts on the battery: Battman's (Smiggles' automations never fire again)
    sm_triggered = {a.entity_id: a.attributes.get("last_triggered") for a in migrate.smiggles_automations(hass)}
    rec.calls.clear()
    await hass.services.async_call("input_select", "select_option", {"entity_id": ENGINE_MAP["mode"],
                                                                     "option": "Discharge"}, blocking=True)
    await H.tick(hass, 2)
    sel = [c for c in rec.calls if c[0] == "select"]
    assert sel and sel[0][2]["option"] == "Command Discharging (PV First)", rec.calls
    # changing Smiggles' mode now does nothing to Sigen
    rec.calls.clear()
    await hass.services.async_call("input_select", "select_option", {"entity_id": SMIGGLES_NAMES["mode"],
                                                                     "option": "Charge"}, blocking=True)
    await H.tick(hass, 2)
    assert [c for c in rec.calls if c[0] in ("select", "number")] == []
    await H.tick(hass, 120)                                    # watchdog minutes, engine runs
    assert {a.entity_id: a.attributes.get("last_triggered") for a in migrate.smiggles_automations(hass)} == sm_triggered
    # Smiggles can't sneak back on while Battman is in charge (by hand, or after a restart)
    await hass.services.async_call("automation", "turn_on", {"entity_id": "automation.solarsystemcontrolsigmode"},
                                   blocking=True)
    await hass.async_block_till_done()
    assert hass.states.get("automation.solarsystemcontrolsigmode").state == "off"
    # can't migrate twice
    plan = await hass.services.async_call("battman", "migrate_from_smiggles", {}, blocking=True, return_response=True)
    assert not plan["can_migrate"]

    # ── Hand back
    await hass.services.async_call("battman", "hand_back_to_smiggles", {"confirm": True}, blocking=True,
                                   return_response=True)
    await H.tick(hass, 2)
    assert hass.states.get("binary_sensor.battman_in_charge").state == "off"
    assert not entry.data[MIGRATED]
    assert sorted(a.entity_id for a in migrate.smiggles_automations(hass) if a.state == "on") == sorted(on_before)
    assert hass.states.get("input_boolean.solarsystemcontrolenable").state == "on"
    assert hass.states.get("sensor.solarsystemcontrolparameters").attributes["sellOverridePrice"] == 22.0
    assert hass.states.get(SMIGGLES_NAMES["mode"]).state == hass.states.get(ENGINE_MAP["mode"]).state
    emap = (await (await client.get("/api/battman/entities")).json())["entities"]
    assert emap["parameters"] == "sensor.solarsystemcontrolparameters"
    bp = Path(hass.config.path("blueprints/script/battman/battman_live_activity_push.yaml")).read_text()
    assert "default: input_select.solarsystemcontrolmode" in bp
    # Battman's engine is idle again
    rec.calls.clear()
    await hass.services.async_call("input_select", "select_option", {"entity_id": ENGINE_MAP["mode"],
                                                                     "option": "Float"}, blocking=True)
    await H.tick(hass, 2)
    assert [c for c in rec.calls if c[0] in ("select", "number")] == []


async def test_migrate_refuses_without_smiggles(hass: HomeAssistant) -> None:
    await H.start(hass, smiggles=False)
    plan = await hass.services.async_call("battman", "migrate_from_smiggles", {}, blocking=True, return_response=True)
    assert not plan["can_migrate"] and "Smiggles not found" in plan["problems"][0]
    with pytest.raises(Exception, match="Smiggles not found"):
        await hass.services.async_call("battman", "migrate_from_smiggles", {"confirm": True}, blocking=True,
                                       return_response=True)
    assert hass.states.get("binary_sensor.battman_in_charge").state == "off"



async def test_log_page_reads_smiggles_log_before_migrating(hass: HomeAssistant, hass_client) -> None:
    await _smiggles_running(hass)
    client = await hass_client()
    r = await client.get("/api/battman/log", params={"start": "2026-10-20 09:04:00", "end": "2026-10-20 09:06:00"})
    assert (await r.json())["lines"] == ["2026-10-20T09:05:00.5+10:30|second run"]
    assert (await client.get("/api/battman/log")).status == 400
    page = (Path(__file__).parents[1] / "custom_components/battman/www/log.html").read_text()
    assert "/api/battman/log" in page and "debug_log_file" not in page and "load_debug_log_script" not in page


async def test_engine_log_file_written_and_pruned(hass: HomeAssistant) -> None:
    from custom_components.battman import engine_log

    await H.start(hass, smiggles=False)
    for i in range(3):
        hass.bus.async_fire("battman_engine_log", {"message": f"run {i}\nline two"})
    await hass.async_block_till_done()
    path = engine_log.battman_path(hass)
    lines = path.read_text().splitlines()
    assert [l.split("|", 1)[1] for l in lines] == ["run 0\\nline two", "run 1\\nline two", "run 2\\nline two"]
    path.write_text("".join(f"2026-01-01T00:00:00|{i}\n" for i in range(5000)))
    engine_log.prune(path)
    kept = path.read_text().splitlines()
    assert len(kept) == 4032 and kept[-1].endswith("|4999")
