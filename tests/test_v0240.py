"""v0.24.0: fixes, and Battman's own grid power and load average sensors off the map.

- The State card's look-ahead uses sell rules (it only knew buy rules), labelled "(sell rule)", with
  the same maths as the engine: checked against the engine's own figures on realistic forecasts.
"""

import json
import os
import random
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import yaml
from homeassistant.core import HomeAssistant

from custom_components.battman.const import ENTITY_MAP_DEFAULTS

from . import engine_harness as H

ROOT = Path(__file__).parents[1] / "custom_components/battman"
needs_node = pytest.mark.skipif(not shutil.which("node"), reason="needs node")
TZ = "Australia/Adelaide"


def _name(key: str) -> str:
    """An entity's name: Battman's engine entities from the entity map, the rest by name (v0.25.0)."""
    from custom_components.battman import required_entities as R

    return ENTITY_MAP_DEFAULTS.get(key) or R.NAMED[key]


def _state_card_rules_js() -> str:
    """The State card's rule functions (ruleOf / ruleAt / sellPriceAt), map markers filled in."""
    text = (ROOT / "cards/state.yaml").read_text()
    a, b = text.index("        const finList ="), text.index("        const isPeak = ms =>")
    return re.sub(r"\[\[map:(\w+)\]\]", lambda m: _name(m.group(1)), text[a:b])


def _card(states: dict, run: dict, cases: list[dict]) -> list[dict]:
    """Run the card's rule maths in node for each case {ms, loSell, curveSell}."""
    js = ("const states = " + json.dumps(states) + ";\n"
          "const attr = " + json.dumps(run) + ";\nconst a = k => parseFloat(attr[k]) || 0;\n"
          f"const par = states['{_name('parameters')}']?.attributes || {{}};\n"
          f"const gen = states['{_name('buy_forecast')}']?.attributes?.Forecasts || [];\n"
          + _state_card_rules_js()
          + "\nconst out = " + json.dumps(cases) + ".map(c => ({buy: ruleAt('buy', c.ms), sell: ruleAt('sell', c.ms),"
            " price: sellPriceAt(c.ms, {loSell: c.loSell}, c.curveSell)}));\n"
            "process.stdout.write(JSON.stringify(out));")
    r = subprocess.run(["node", "-"], input=js, capture_output=True, text=True, env={**os.environ, "TZ": TZ})
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_card_has_sell_rules() -> None:
    text = (ROOT / "cards/state.yaml").read_text()
    assert "const SR = sellPriceAt(from, T, P.sell);" in text
    assert text.count("' (sell rule)'") == 2 and "' (buy rule)'" in text
    # a forecast slot counts duration / 5 steps, as in the engine (none when it has no duration)
    assert "Math.floor((parseInt(f.duration)||0)/5)" in text and "||5)/5" not in text


@needs_node
async def test_card_rules_match_the_engine(hass: HomeAssistant, freezer) -> None:
    await hass.config.async_set_time_zone(TZ)
    freezer.move_to(datetime(2026, 10, 21, 9, 0, 10, tzinfo=ZoneInfo(TZ)))
    from .test_finances_cards import _start_totals

    await _start_totals(hass)                       # Battman in charge, its totals running
    await hass.services.async_call("automation", "turn_off", {"entity_id": "all"}, blocking=True)
    names = {k: _name(k) for k in ("buy_rules", "sell_rules", "parameters", "buy_forecast",
                                                  "feed_in_forecast", "buy_total", "sell_total", "run")}
    rnd = random.Random(2310)
    checked, used = 0, {"sell": 0, "buy": 0, "raised": 0, "last_chance": 0}
    for n in range(200):
        when = datetime(2026, rnd.choice([1, 4, 7, 10]), rnd.randint(1, 27), rnd.randint(0, 23),
                        rnd.choice([0, 7, 22, 37, 52]), 10, tzinfo=ZoneInfo(TZ))
        freezer.move_to(when)
        H.set_world(hass, {"seed": n, "buy": rnd.choice([0.04, 0.12, 0.3]), "sell": rnd.choice([0.03, 0.09, 0.3]),
                           "sensor.sigen_plant_battery_state_of_charge": str(rnd.choice([30, 60, 90]))})
        soc, price = H.curves(random.Random(n % 4))
        hass.bus.async_fire(ENTITY_MAP_DEFAULTS["soc_curves_update_event"], {"curves": soc})
        hass.bus.async_fire(ENTITY_MAP_DEFAULTS["price_curves_update_event"], {"curves": price})
        # today in the red or not (a sell rule's "last chance")
        hass.bus.async_fire(ENTITY_MAP_DEFAULTS["totals_update_event"],
                            {"attribute": "SetTotal", "period": "day", "buy": rnd.choice([0, 6]), "sell": 1})
        for side in ("buy", "sell"):
            ev = ENTITY_MAP_DEFAULTS[side + "_rules_event"]
            hass.bus.async_fire(ev, {"attribute": "state", "value": rnd.random() < 0.85})
            rule = {"isActive": rnd.random() < 0.85, "hours_ahead": rnd.choice([0, 1, 3, 6]),
                    "grouping_minutes": rnd.choice([5, 15, 30, 60]), "offset": rnd.choice([-3, 0, 2]),
                    "roundTo": rnd.choice([0, 2]), "roundtype": rnd.choice(["floor", "ceil", "common"])}
            if side == "sell":
                rule["allowLastChance"] = rnd.random() < 0.5
            for item, value in rule.items():
                hass.bus.async_fire(ev, {"attribute": "rules", "hour": when.hour, "item": item, "value": value})
        await hass.async_block_till_done()
        await hass.services.async_call("script", "turn_on", {"entity_id": ENTITY_MAP_DEFAULTS["control_script"]},
                                       blocking=True)
        await H.tick(hass, 3)
        await H.tick(hass, 1)
        run = dict(hass.states.get(names["run"]).attributes)
        states = {e: {"state": hass.states.get(e).state, "attributes": dict(hass.states.get(e).attributes)}
                  for e in names.values()}
        states = json.loads(json.dumps(states, default=str))
        ms = int(datetime.now(ZoneInfo(TZ)).timestamp() * 1000)
        f = lambda k: float(run[k])
        out = _card(states, json.loads(json.dumps(run, default=str)),
                    [{"ms": ms, "loSell": f("sellPriceLow") * 100, "curveSell": f("sellPriceCalc") * 100}])[0]
        srule = states[names["sell_rules"]]["attributes"]["rules"][when.hour]
        # no look-ahead but "last chance": the engine reports its low price as the rule's figure, which
        # can't change the sell price (a rule has to be above the low price); the card leaves it out
        lc_only = int(srule["hours_ahead"]) == 0 and abs(f("sellPriceRule") - f("sellPriceLow")) < 1e-9
        assert abs(out["sell"] - (0 if lc_only else f("sellPriceRule"))) < 1e-9, (n, out, run["sellPriceRule"], run["sellPriceForecast"],
                                                               states[names["sell_rules"]]["attributes"]["rules"][when.hour])
        assert abs(out["buy"] - f("buyPriceRule")) < 1e-9, (n, out, run["buyPriceRule"])
        assert abs(out["price"]["sp"] - f("sellPrice") * 100) < 1e-6, (n, out, run["sellPrice"], run["sellPriceCalc"])
        used["sell"] += f("sellPriceRule") > 0
        used["buy"] += f("buyPriceRule") > 0
        used["raised"] += out["price"]["ruled"] and f("sellPrice") > f("sellPriceCalc")
        used["last_chance"] += out["price"]["ruled"] and f("sellPrice") < f("sellPriceCalc")
        checked += 1
    print("\nrules used:", used)
    assert checked == 200 and used["sell"] >= 10 and used["buy"] >= 10 and used["raised"] >= 2


@needs_node
def test_slots_without_duration_count_for_nothing() -> None:
    """Amber's forecast slots carry their length (duration); the engine counts none without it, and
    now so does the card (it used to assume 5 minutes, so the two could disagree)."""
    now = datetime(2026, 10, 21, 18, 5, tzinfo=ZoneInfo(TZ))
    ms = int(now.timestamp() * 1000)
    fc = [{"start_time": now.replace(minute=30 * i % 60, hour=18 + (30 * i) // 60).isoformat(),
           "end_time": now.replace(minute=30 * (i + 1) % 60, hour=18 + (30 * (i + 1)) // 60).isoformat(),
           "per_kwh": -0.2 - i / 100} for i in range(4)]
    rules = [{"hour": h, "isActive": True, "hours_ahead": 2, "grouping_minutes": 30, "roundTo": 0, "roundtype": "floor",
              "offset": 0, "allowLastChance": False} for h in range(24)]
    st = lambda withd: {_name("sell_rules"): {"state": "True", "attributes": {"rules": rules}},
                        _name("feed_in_forecast"): {"state": "0", "attributes": {
                            "Forecasts": [{**f, "duration": 30} if withd else f for f in fc]}}}
    case = [{"ms": ms, "loSell": 5, "curveSell": 10}]
    assert _card(st(False), {}, case)[0]["sell"] == 0
    assert _card(st(True), {}, case)[0]["sell"] == pytest.approx(0.23)    # the best of 18:00–20:00


# ── Correct totals on a phone ───────────────────────────────────────────────────────────

LIB = ROOT / "www/battman-lib.js"


def _lib(script: str) -> dict:
    """Run battman-lib.js in node with a fake page, then script; returns what script prints."""
    page = """
const calls = [], toasts = [];
const hass = { states: {}, themes: { themes: {} }, callService: (...a) => calls.push(['server', ...a]) };
globalThis.window = globalThis;
globalThis.getComputedStyle = () => ({ getPropertyValue: () => '' });
globalThis.CustomEvent = class { constructor(t, o) { this.type = t; this.detail = o.detail; } };
globalThis.document = { querySelector: (s) => (s === 'home-assistant' ? { hass, dispatchEvent: (e) => toasts.push(e.detail.message) } : null) };
const btn = { tagName: 'BUTTON', dispatchEvent: (e) => toasts.push(e.detail.message) };
"""
    js = page + LIB.read_text() + "\n" + script
    r = subprocess.run(["node", "-"], input=js, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@needs_node
def test_correct_totals_opens_on_this_device() -> None:
    """It used to ask the server for a browser_mod popup with no browser named, which only reaches
    browsers registered with browser_mod (so nothing on an unregistered phone)."""
    out = _lib("""
window.browser_mod = { service: (s, d) => calls.push(['local', s, d.title, d.content.type]) };
window.BattmanLib.correctTotals(btn, {buy: 'sensor.b', sell: 'sensor.s', event: 'e'});
process.stdout.write(JSON.stringify({calls, toasts}));""")
    assert out == {"calls": [["local", "popup", "Correct totals", "custom:button-card"]], "toasts": []}
    out = _lib("""
window.BattmanLib.correctTotals(btn, {buy: 'sensor.b', sell: 'sensor.s', event: 'e'});
process.stdout.write(JSON.stringify({calls, toasts}));""")
    assert out["calls"] == [] and out["toasts"] == ["Correct totals needs browser_mod, which isn't loaded on this device."]


def test_no_server_popups_left() -> None:
    lib = LIB.read_text()
    assert "callService('browser_mod'" not in lib and 'callService("browser_mod"' not in lib
    for gone in ("openPopup", "renderDock", "isVisible", "BattmanLib.CFG"):
        assert gone not in lib, gone


# ── grid power and load average off the map ──────────────────────────────────────────────

def test_battmans_own_sensors_by_name() -> None:
    from custom_components.battman import required_entities as R

    base = (ROOT / "www/battman-card-base.js").read_text()
    s = base.index("export const BATTMAN_SENSORS")
    own = dict(re.findall(r'^  (\w+): "([^"]+)",$', base[s:base.index("};", s)], re.M))
    assert own == {"grid_power": "sensor.battman_grid_power", "load_30m_avg": "sensor.battman_load_30m_avg"}
    for k, v in own.items():
        assert R.NAMED[k] == v and k not in ENTITY_MAP_DEFAULTS, k
    for f in [*ROOT.glob("cards/*.yaml"), *ROOT.glob("views/*.yaml"), *ROOT.glob("www/*.js")]:
        text = f.read_text()
        assert not re.search(r"\[\[map:(grid_power|load_30m_avg)\]\]|\{\{(grid_power|load_30m_avg)\}\}", text), f.name
        if re.search(r"\bM\.(grid_power|load_30m_avg)\b", text):
            assert "...BATTMAN_SENSORS" in text and re.search(r"import \{[^}]*\bBATTMAN_SENSORS\b", text), f.name
        for k in own:
            assert f"'{k}'" not in text.split("const NEEDS")[1].split(";")[0] if "const NEEDS" in text else True, (f.name, k)


# ── Solcast missing: no made-up 0 ────────────────────────────────────────────────────────

SOLCAST_REMAIN = "sensor.solcast_pv_forecast_forecast_remaining_today"


async def _engine_run(hass, freezer):
    """Battman's engine at 11am (solar sponge time), the battery half full; the run's figures and log."""
    from .test_finances_cards import _start_totals

    await hass.config.async_set_time_zone(TZ)
    freezer.move_to(datetime(2026, 10, 21, 11, 0, 10, tzinfo=ZoneInfo(TZ)))
    await _start_totals(hass)
    await hass.services.async_call("automation", "turn_off", {"entity_id": "all"}, blocking=True)
    soc, price = H.curves(random.Random(3))
    hass.bus.async_fire("battman_soc_curves_update", {"curves": soc})
    hass.bus.async_fire("battman_price_curves_update", {"curves": price})
    hass.states.async_set("sensor.sigen_plant_battery_state_of_charge", "50")
    await hass.async_block_till_done()

    async def run():
        await hass.services.async_call("script", "turn_on", {"entity_id": "script.battman_engine"}, blocking=True)
        await H.tick(hass, 3)
        await H.tick(hass, 1)
        return (hass.states.get("sensor.battman_run").attributes,
                hass.states.get("sensor.battman_engine_log").attributes["message"])
    return run


async def test_engine_skips_the_sun_check_without_solcast(hass: HomeAssistant, freezer) -> None:
    run = await _engine_run(hass, freezer)
    # Solcast says no sun left: half the battery to fill is more than the gap allowed -> No Sun
    hass.states.async_set(SOLCAST_REMAIN, "0", {"estimate": 0, "estimate10": 0, "estimate90": 0})
    attrs, msg = await run()
    assert str(attrs["needSun"]).lower() == "true" and "Remaining (10%): 0.0 kWh" in msg
    # Solcast missing: it used to be read as 0 kWh (the same No Sun panic); now the check is skipped
    for gone in ("unavailable", None):
        if gone is None:
            hass.states.async_remove(SOLCAST_REMAIN)
        else:
            hass.states.async_set(SOLCAST_REMAIN, gone, {})
        attrs, msg = await run()
        assert str(attrs["needSun"]).lower() == "false", gone
        assert ("Remaining (10%): missing (sensor.solcast_pv_forecast_forecast_remaining_today has no estimate10), "
                "sun check skipped") in msg, gone
    # back: used again
    hass.states.async_set(SOLCAST_REMAIN, "30", {"estimate": 30, "estimate10": 25.5, "estimate90": 33})
    attrs, msg = await run()
    assert str(attrs["needSun"]).lower() == "false" and "Remaining (10%): 25.5 kWh" in msg


def test_engine_has_no_made_up_solar() -> None:
    engine = (ROOT / "blueprints/script/battman_engine.yaml").read_text()
    assert "estimate10'') | float(0)" not in engine
    assert "pvRemainingNotGood: '{{ pvRemainingKnown and" in engine


@needs_node
async def test_state_popup_shows_sell_rules(hass: HomeAssistant, hass_client) -> None:
    """With sell rules on, the look-ahead holds out for the better price ahead and says why."""
    from custom_components.battman.const import ENGINE_MAP, SMIGGLES_NAMES

    from .test_v0130 import _card, hass_client_holder, run_js, state_states

    hass_client_holder["c"] = hass_client
    pop = (await _card(hass, "state"))["config"]["tap_action"]["browser_mod"]["data"]["content"]
    to_battman = {SMIGGLES_NAMES[k]: v for k, v in ENGINE_MAP.items() if k in SMIGGLES_NAMES}

    def world(sell_rules_on: bool) -> dict:
        st = {to_battman.get(e, e): v for e, v in state_states(0).items()}
        st["sensor.sigen_plant_battery_state_of_charge"]["state"] = "95"      # plenty to sell
        st[ENGINE_MAP["sell_rules"]]["state"] = "true" if sell_rules_on else "false"
        return st
    on, off = run_js([(pop, world(True), None), (pop, world(False), None)])
    assert "missing" not in on and "(sell rule)" in on and "(sell rule)" not in off
