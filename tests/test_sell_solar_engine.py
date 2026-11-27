"""Sell Solar by the hour, in the real engine: an Active sell rule with its Sell solar switch on puts the battery
in Float when the feed-in price, the battery level and the excess (Solcast's 10% remaining-today forecast less
what the battery still has room for) all clear the three settings, and only when nothing else wants to act.

Each case sets the world, runs the engine once and reads its run record (the engine's own record of the decision).
The Solcast forecast the world helper sets is estimate10 = 0.7 x remaining, so the cases give `remaining` and the
10% figure is worked out in the case."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from homeassistant.core import HomeAssistant

from . import engine_harness as H
from .test_engine_worlds import BASE_PARAMS, TZ, run_engine, start_worlds_ha

# 14:07 on a day in October, inside the solar sponge window, with 32 kWh of battery (the harness default)
WHEN = datetime(2026, 10, 21, 14, 7, 10, tzinfo=ZoneInfo(TZ))
SETTINGS = {"sellSolarRulePrice": 5, "sellSolarRuleSOC": 40, "sellSolarRuleExcess": 10}


async def _rules(hass: HomeAssistant, *, active: bool = True, sell_solar: bool = True, enabled: bool = True) -> None:
    ev = "battman_sell_rules_update"
    hass.bus.async_fire(ev, {"attribute": "state", "value": enabled})
    for item, value in {"isActive": active, "allowSellSolar": sell_solar, "hours_ahead": 0}.items():
        hass.bus.async_fire(ev, {"attribute": "rules", "hour": WHEN.hour, "item": item, "value": value})
    await hass.async_block_till_done()


async def _decide(hass: HomeAssistant, freezer, *, soc: int = 60, remaining: float = 60, sell: float = 0.09, buy: float = 0.2,
                  mode: str = "Self Consume", rules: dict | None = None, params: dict | None = None, gap: bool = False):
    hass.data["sell_solar_runs"] = n = hass.data.get("sell_solar_runs", 0) + 1
    freezer.move_to(WHEN + timedelta(minutes=n))          # the engine only records a run at a new time
    world = {"seed": 1, "shape": "uniform30", "sensor.sigen_plant_battery_state_of_charge": str(soc), "buy": buy, "sell": sell,
             "estimate": False, "pv_remaining": remaining, "load": "1.2"}
    H.set_world(hass, world)
    hass.bus.async_fire("battman_parameters_update", {"action": "SetAttribute", **BASE_PARAMS, **SETTINGS, **(params or {})})
    await _rules(hass, **(rules or {}))
    hass.bus.async_fire("battman_totals_update", {"attribute": "SetTotal", "period": "day", "buy": 0, "sell": 0})
    await hass.async_block_till_done()
    await hass.services.async_call("input_select", "select_option", {"entity_id": "input_select.battman_mode", "option": mode}, blocking=True)
    if gap:
        hass.states.async_remove("sensor.solcast_pv_forecast_forecast_remaining_today")
    await hass.async_block_till_done()
    ran, event = await run_engine(hass)
    assert ran and event
    return event, hass.states.get("input_select.battman_mode").state


# soc 60% of 32 kWh = 19.2 kWh held, 12.8 kWh to fill. remaining 60 -> 10% figure 42 -> excess 29.2 kWh
async def test_sells_solar_when_everything_clears(hass: HomeAssistant, freezer) -> None:
    await start_worlds_ha(hass, freezer)
    event, mode = await _decide(hass, freezer)
    assert mode == "Float" and event["sellReason"][:3] == [True, 14, "Solar Rule"]
    log = hass.states.get("sensor.battman_engine_log").attributes["message"]
    assert "Sell Solar rule: excess 29.2 kWh (needs 10.0, holds to 9.0), price 5.0c or more, battery 40.0% or more" in log


@pytest.mark.parametrize("what,kw", [
    ("the rule is not Active", {"rules": {"active": False}}),
    ("Sell solar is off for the hour", {"rules": {"sell_solar": False}}),
    ("Sell rules are switched off", {"rules": {"enabled": False}}),
    ("the price is under the minimum", {"sell": 0.04}),
    ("the battery is under the level", {"soc": 39}),
    ("there is not enough excess", {"remaining": 20}),           # 10% figure 14 kWh, 12.8 kWh to fill: 1.2 kWh
    ("Solcast has no forecast", {"gap": True}),
    ("the price is negative", {"sell": -0.02, "params": {"sellSolarRulePrice": 0}}),
])
async def test_does_not_sell_solar_when(hass: HomeAssistant, freezer, what, kw) -> None:
    await start_worlds_ha(hass, freezer)
    event, mode = await _decide(hass, freezer, **kw)
    assert mode == "Self Consume", what
    assert event["sellReason"][2] != "Solar Rule", what


async def test_price_and_level_are_at_or_above(hass: HomeAssistant, freezer) -> None:
    await start_worlds_ha(hass, freezer)
    event, mode = await _decide(hass, freezer, sell=0.05, soc=40)                 # exactly the settings
    assert mode == "Float" and event["sellReason"][2] == "Solar Rule"


async def test_excess_at_the_setting_sells(hass: HomeAssistant, freezer) -> None:
    await start_worlds_ha(hass, freezer)
    # 10% figure 0.7 x remaining; 12.8 kWh to fill; excess 10 needs 22.8 kWh -> remaining 32.57; use 33 (excess 10.3)
    assert (await _decide(hass, freezer, remaining=33))[1] == "Float"
    assert (await _decide(hass, freezer, remaining=32))[1] == "Self Consume"      # 9.6 kWh: just short


async def test_holds_until_the_excess_is_a_kwh_under(hass: HomeAssistant, freezer) -> None:
    await start_worlds_ha(hass, freezer)
    # already in Float: carries on within 1 kWh under the setting, even with the price and level now short
    held, mode = await _decide(hass, freezer, mode="Float", remaining=32, sell=0.03, soc=60)     # excess 9.6: within 1 kWh
    assert mode == "Float" and held["sellReason"][2] == "Solar Rule"
    gone, mode = await _decide(hass, freezer, mode="Float", remaining=30, sell=0.09)             # excess 8.2: past the hold
    assert mode == "Self Consume"
    cheap, mode = await _decide(hass, freezer, mode="Float", remaining=60, sell=-0.01)           # never while negative
    assert cheap["sellReason"][2] != "Solar Rule"


async def test_only_when_nothing_else_wants_to_act(hass: HomeAssistant, freezer) -> None:
    await start_worlds_ha(hass, freezer)
    # buying wins: a cheap buy price under the Anytime price with the battery under its level
    event, mode = await _decide(hass, freezer, soc=45, buy=0.03, params={"buyAnytimePrice": 8, "buyAnytimeSOC": 60})
    assert mode == "Charge"
    # another way of selling wins and keeps its own reason: a spike
    event, mode = await _decide(hass, freezer, sell=6.0, params={"sellSpikePrice1": 500, "sellSpikeSOC1": 10})
    assert event["sellReason"][2] != "Solar Rule"
    # the global Sell Solar settings win and keep theirs
    event, mode = await _decide(hass, freezer, params={"sellSolarPrice": 5, "sellSolarSOC": 50})
    assert event["sellReason"][2] == "Solar Only"
