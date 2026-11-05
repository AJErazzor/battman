"""The engine across 300 generated worlds: whatever the world, it must end with a valid decision.

Each world is run through the REAL engine script (read, decide, act) and checked for what must always
be true: the engine either completes and leaves a valid mode, a no-export switch and a full run record
and log, or it stops part-way because something it needs is missing. A sweep that always lands on one
mode proves nothing, so the worlds must reach most of the engine's decisions.

What a world is: battery level, buy and sell price now, whether the price is an estimate, the Amber
forecast (even 30-minute entries, or the live shape: 5-minute entries then 30-minute), Solcast, home
load, grid status, month and clock (including the tariff swap minutes and the edges of the peak and solar
windows), the curves, the rules, every override, spike, drain and net target, today's totals, the mode the
battery is in now, and gaps (load, Solcast or the forecast missing).

The decision logic itself was proved against the engine it replaced on a live system (every run compared
for days, including real mode changes); these worlds guard the whole chain from here on.

Not covered: the engine's own track of what you paid (trackingA, behind the "protected sell" floor) is
whatever the totals have built up during this test; the worlds don't set it.
"""

from __future__ import annotations

import collections
import random
from datetime import datetime
from zoneinfo import ZoneInfo

from homeassistant.core import HomeAssistant, callback

from . import engine_harness as H

TZ = "Australia/Adelaide"
MODES = ["Self Consume", "Discharge", "Charge", "Charge Solar Off", "Float", "Float Solar Off", "Solar Soak", "Drain"]
MONTHS = [1, 4, 7, 10, 12]
# clocks that sit on the edges of the engine's tariff windows and swap minutes (hour, minute, second)
EDGE_CLOCKS = [(9, 59, 59), (10, 0, 30), (10, 1, 5), (15, 58, 50), (15, 59, 30), (16, 0, 59), (16, 1, 10),
               (16, 59, 59), (17, 0, 5), (17, 1, 30), (20, 58, 30), (20, 59, 30), (21, 0, 10), (21, 1, 20),
               (23, 59, 59), (0, 0, 10)]
# the settings the worlds change, put back to these before every world so each world stands alone
BASE_PARAMS = {
    "sellOverridePrice": 0, "sellOverrideSOC": 0, "buyOverridePrice": 0, "buyOverrideSOC": 0,
    "buyAnytimePrice": 0, "buyAnytimeSOC": 0, "sellSolarPrice": 0, "sellSolarSOC": 0,
    "drainBatteryPrice": 0, "drainBatterySOC": 0, "drainBatteryPlughole": False,
    "sellSpikePrice1": 500, "sellSpikeSOC1": 10, "sellSpikePrice2": 100, "sellSpikeSOC2": 15,
    "needyTriggerConsumption": 3.5, "needyTriggerPVGap": 3,
}


def scenarios(n: int = 300) -> list[dict]:
    rnd = random.Random(20261105)
    out = []
    for i in range(n):
        p: dict = {}
        kind = i % 9
        if kind == 1:
            p.update(sellOverrideSOC=rnd.choice([20, 40, 60]), sellOverridePrice=rnd.choice([0, 10, 25]))
        elif kind == 2:
            p.update(buyAnytimeSOC=rnd.choice([30, 60, 90]), buyAnytimePrice=rnd.choice([5, 15, 30]))
        elif kind == 3:
            p.update(drainBatterySOC=rnd.choice([10, 30]), drainBatteryPrice=rnd.choice([0, 8]),
                     drainBatteryPlughole=rnd.choice([True, False]))
        elif kind == 4:
            p.update(sellSolarSOC=rnd.choice([50, 80]), sellSolarPrice=rnd.choice([5, 12]),
                     buyOverrideSOC=rnd.choice([20, 50]), buyOverridePrice=rnd.choice([5, 20, -3]))
        elif kind == 5:
            p.update(needyTriggerConsumption=rnd.choice([0.5, 2, 6]), needyTriggerPVGap=rnd.choice([-5, 3, 15]))
        elif kind == 6:   # spikes, including a price of 0 (the engine has no guard for that)
            p.update(sellSpikePrice1=rnd.choice([0, 15, 40]), sellSpikeSOC1=rnd.choice([5, 30]),
                     sellSpikePrice2=rnd.choice([0, 8]), sellSpikeSOC2=rnd.choice([10, 45]))
        elif kind == 7:   # an override that is only a price, or only a SOC
            p.update(sellOverridePrice=rnd.choice([0, 18]), buyOverrideSOC=rnd.choice([0, 35]))
        # kind 0 and 8: nothing changed from the base settings
        when = None
        if i % 5 == 0:
            h, m, s = EDGE_CLOCKS[(i // 5) % len(EDGE_CLOCKS)]
            when = datetime(2026, rnd.choice(MONTHS), rnd.randint(1, 27), h, m, s, tzinfo=ZoneInfo(TZ))
        elif i % 97 == 3:    # the days Adelaide's clocks change
            when = rnd.choice([datetime(2026, 10, 4, 3, 30, 10, tzinfo=ZoneInfo(TZ)),
                               datetime(2026, 4, 5, 4, 0, 10, tzinfo=ZoneInfo(TZ))])
        if when is None:
            when = datetime(2026, rnd.choice(MONTHS), rnd.randint(1, 27), rnd.randint(0, 23),
                            rnd.choice([0, 7, 22, 37, 52]), 10, tzinfo=ZoneInfo(TZ))
        gaps = []
        if i % 11 == 4:
            gaps.append(rnd.choice(["load", "solcast", "forecast"]))
        out.append({
            "params": p,
            "when": when,
            "world": {
                "seed": i,
                "shape": rnd.choice(["real", "uniform30"]),
                "sensor.sigen_plant_battery_state_of_charge": str(rnd.choice([0, 3, 10, 25, 40, 55, 70, 85, 98, 100])),
                "buy": rnd.choice([-0.08, 0.0, 0.04, 0.12, 0.25, 0.45, 1.5]),
                "sell": rnd.choice([-0.05, 0.0, 0.03, 0.09, 0.2, 0.6, 2.5]),
                "estimate": rnd.choice([True, False]),
                "pv_remaining": rnd.choice([0, 2, 8, 20, 40]),
                "pv_next_hour": rnd.choice([0, 0.5, 3, 6]),
                "load": str(rnd.choice([0.3, 1.2, 3.0, 7.5])),
                "sensor.sigen_plant_grid_connection_status": rnd.choice(["On Grid", "On Grid", "On Grid", "Off Grid"]),
            },
            "day": rnd.choice([(0, 0), (2.5, 1.0), (1.0, 4.0), (8.0, 0.5)]),   # today's (buy, sell) totals, $
            "mode": rnd.choice(MODES),
            "no_export": rnd.choice(["on", "off"]),
            "rules": rnd.choice([None, "buy", "sell", "both"]),
            "curves_seed": rnd.randint(0, 3),
            "gaps": gaps,
        })
    return out


async def _rule(hass, kind: str, hour: int, active: bool, rnd: random.Random) -> None:
    """Switch the buy or sell rule for this hour on (with a look-ahead) or off."""
    ev = f"battman_{kind}_rules_update"
    hass.bus.async_fire(ev, {"attribute": "state", "value": True})
    items = {"isActive": active, "hours_ahead": rnd.choice([1, 3, 6]), "grouping_minutes": rnd.choice([30, 60]),
             "offset": rnd.choice([-2, 0, 3]), "roundTo": 2, "roundtype": rnd.choice(["floor", "ceil", "none"])}
    if kind == "sell":
        items["allowLastChance"] = rnd.choice([True, False])
    for item, value in items.items():
        hass.bus.async_fire(ev, {"attribute": "rules", "hour": hour, "item": item, "value": value})
    await hass.async_block_till_done()


async def set_up_world(hass: HomeAssistant, freezer, n: int, sc: dict) -> None:
    """Put the test HA into world `sc` (number `n`): clock, sensors, curves, rules, settings, totals, mode,
    no-export, and any gaps. Everything the engine reads is then in place; nothing has run yet."""
    rnd = random.Random(900000 + n)
    freezer.move_to(sc["when"])
    H.set_world(hass, sc["world"])
    soc, price = H.curves(random.Random(sc["curves_seed"]))
    hass.bus.async_fire("battman_soc_curves_update", {"curves": soc})
    hass.bus.async_fire("battman_price_curves_update", {"curves": price})
    hour = sc["when"].hour
    for kind in ("buy", "sell"):
        await _rule(hass, kind, hour, sc["rules"] in (kind, "both"), rnd)
    hass.bus.async_fire("battman_parameters_update", {"action": "SetAttribute", **BASE_PARAMS, **sc["params"]})
    buy_day, sell_day = sc["day"]
    hass.bus.async_fire("battman_totals_update", {"attribute": "SetTotal", "period": "day",
                                                  "buy": buy_day, "sell": sell_day})
    await hass.async_block_till_done()
    await hass.services.async_call("input_select", "select_option",
                                   {"entity_id": "input_select.battman_mode", "option": sc["mode"]}, blocking=True)
    await hass.services.async_call("input_boolean", f"turn_{sc['no_export']}",
                                   {"entity_id": "input_boolean.battman_no_export"}, blocking=True)
    for gap in sc["gaps"]:
        if gap == "load":
            hass.states.async_set(H.LOAD_AVG, "unavailable")
        elif gap == "solcast":
            hass.states.async_remove("sensor.solcast_pv_forecast_forecast_remaining_today")
        elif gap == "forecast":
            for ent in ("sensor.amber_billing_interval_forecasts_general_price",
                        "sensor.amber_billing_interval_forecasts_feed_in_price"):
                hass.states.async_set(ent, "0", {"Forecasts": []})
    await hass.async_block_till_done()


async def run_engine(hass: HomeAssistant) -> tuple[bool, dict | None]:
    """Run the real engine once (as the loop would). Returns (did it complete, the battman_run_update
    event data it fired). The event is the engine's own record: sensor.battman_run shows a copy of it
    with some numbers cut to whole numbers (buyBelow, for one)."""
    events: list[dict] = []

    @callback
    def keep(event) -> None:
        events.append(dict(event.data))

    stop = hass.bus.async_listen("battman_run_update", keep)
    before = hass.states.get("sensor.battman_run").attributes.get("lastRunAt")
    await hass.services.async_call("script", "turn_on", {"entity_id": "script.battman_engine"}, blocking=True)
    await H.tick(hass, 3)
    await H.tick(hass, 1)
    stop()
    ran = hass.states.get("sensor.battman_run").attributes.get("lastRunAt") != before
    return ran, (events[-1] if events else None)


async def start_oracle_ha(hass: HomeAssistant, freezer) -> None:
    from .test_finances_cards import _start_totals

    await hass.config.async_set_time_zone(TZ)
    freezer.move_to(datetime(2026, 10, 21, 9, 0, 10, tzinfo=ZoneInfo(TZ)))
    await _start_totals(hass)
    # only the engine script runs here (the automations around it have their own tests)
    await hass.services.async_call("automation", "turn_off", {"entity_id": "all"}, blocking=True)
    await hass.async_block_till_done()


async def test_engine_across_300_worlds(hass: HomeAssistant, freezer) -> None:
    await start_oracle_ha(hass, freezer)

    seen_modes: set[str] = set()
    tally: collections.Counter = collections.Counter()
    worlds = scenarios()
    for n, sc in enumerate(worlds):
        await set_up_world(hass, freezer, n, sc)
        ran, event = await run_engine(hass)
        tally["ran" if ran else "did not run"] += 1
        if not ran:
            continue          # stopped part-way (something it needs was missing): no decision, no change

        mode = hass.states.get("input_select.battman_mode").state
        no_export = hass.states.get("input_boolean.battman_no_export").state
        log = hass.states.get("sensor.battman_engine_log").attributes["message"]
        assert mode in hass.states.get("input_select.battman_mode").attributes["options"], f"world {n}: mode {mode!r}"
        assert no_export in ("on", "off"), f"world {n}: no-export {no_export!r}"
        assert log.startswith("Run: ") and "Mode:" in log and "Actions:" in log, f"world {n}: log {log[:80]!r}"
        assert event and len(event) >= 36, f"world {n}: run record {sorted(event or {})}"
        for key in ("sellPrice", "buyPrice", "sellReason", "buyReason", "sellAbove", "buyBelow"):
            assert key in event, f"world {n}: run record has no {key}"
        seen_modes.add(mode)
        tally[(mode, no_export)] += 1

    print("\nengine decisions (mode, no export):", dict(tally))
    assert len(worlds) == 300
    assert tally["ran"] > len(worlds) // 2, tally     # some worlds are meant to be missing something
    # the worlds reach most of the engine's decisions (a sweep that always lands on one mode proves nothing)
    assert len(seen_modes) >= 4, seen_modes
