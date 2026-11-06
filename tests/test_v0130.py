"""v0.13.0: Amber 5-min price grid, Amber forecast table, State card, <battman-countdown>,
browser_mod in the dependency check, and the Power view layout.

Each card is run (with node) on a scenario of states and its output recorded as a snapshot."""

import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from .dashboard_views import built
from .snapshots import assert_snapshot

DOMAIN = "battman"
FIX = Path(__file__).parent / "fixtures"
CARDS = Path(__file__).parents[1] / "custom_components/battman/cards"
needs_node = pytest.mark.skipif(not shutil.which("node"), reason="needs node to run the cards' JavaScript")

BUY_NOW, SELL_NOW = "sensor.amber_5min_current_general_price", "sensor.amber_5min_current_feed_in_price"
BUY_F, SELL_F = "sensor.amber_billing_interval_forecasts_general_price", "sensor.amber_billing_interval_forecasts_feed_in_price"
EST = "binary_sensor.battman_estimated_price"
HA_TZ = "Australia/Adelaide"      # the time zone the fake HA reports to cards
# For recorded snapshots node must draw the same everywhere: its local time zone and locale
# (cards use getHours() and toLocaleTimeString([])) pinned, and for the State card its clock.
PINNED = {"TZ": HA_TZ, "LC_ALL": "C.UTF-8", "LANG": "C.UTF-8"}
FIXED_NOW = datetime(2026, 10, 20, 3, 7, 10, tzinfo=timezone.utc)


def frozen_clock(when: datetime) -> str:
    """run_js prelude: Date.now() and new Date() return `when`."""
    ms = int(when.timestamp() * 1000)
    return ("{ const _D = Date, _T = " + str(ms) + ";\n"
            "  globalThis.Date = class extends _D { constructor(...a) { super(...(a.length ? a : [_T])); }"
            " static now() { return _T; } }; }")


async def _setup(hass):
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain=DOMAIN, title="Battman", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return await hass_client_holder["c"]()


hass_client_holder: dict = {}


@pytest.fixture(autouse=True)
def _client(hass_client):
    hass_client_holder["c"] = hass_client


async def _card(hass, card_id):
    client = await _setup(hass)
    return await (await client.get(f"/api/battman/cards/{card_id}")).json()


def run_js(jobs, prelude: str = "", env: dict | None = None):
    """Run button-card [[[ ]]] templates the way button-card does. jobs: [(src, states, entity_id)].
    All in one node process (same clock). Returns each output, or 'THROW: …'.
    prelude: JS run first (e.g. a script HA loads on every page). env: extra environment for node."""
    progs = []
    for src, states, ent in jobs:
        body = src.strip()
        assert body.startswith("[[[") and body.endswith("]]]")
        progs.append("(function(states, entity, hass, user, variables){" + body[3:-3] + "})"
                     f"({json.dumps(states)}, {json.dumps(states.get(ent))}, {{states: {json.dumps(states)}, config: {{time_zone: {json.dumps(HA_TZ)}}}}}, {{}}, {{}})")
    script = ("globalThis.window = globalThis;\n" + prelude + "\nconst out = [];\n" + "".join(
        f"try {{ out.push(String({p})); }} catch (e) {{ out.push('THROW: ' + e.message); }}\n" for p in progs)
        + "process.stdout.write(JSON.stringify(out));")
    r = subprocess.run(["node", "-"], input=script, capture_output=True, text=True, check=True,
                       env={**os.environ, **env} if env else None)
    return json.loads(r.stdout)


# ── shared fake data ─────────────────────────────────────────────────────────

def forecasts(start, per, sign=1, adv=None):
    out = []
    for i, p in enumerate(per):
        st = start + timedelta(minutes=30 * i)
        f = {"start_time": st.isoformat(), "end_time": (st + timedelta(minutes=30)).isoformat(), "duration": 30,
             "per_kwh": sign * p, "nem_date": (st + timedelta(minutes=30)).astimezone(timezone(timedelta(hours=10))).isoformat()}
        if adv is not None:
            f["advanced_price"] = {"predicted": sign * adv[i]} if i % 2 else None
            if i % 2 == 0 and i % 4 == 0:
                f.pop("advanced_price")
                f["advanced_price_predicted"] = sign * adv[i]
        out.append(f)
    return out


START = datetime(2026, 10, 20, 3, 0, tzinfo=timezone.utc)
SELLP = [0.031, 0.072, 0.161, 0.244, 0.311, -0.021, 0.004, 0.128, 0.187, 0.263]
BUYP = [0.052, 0.091, 0.143, 0.241, 0.377, -0.034, 0.071, 0.262, 0.611, 0.083]


def price_states(sell_now, buy_now, est="off", sell=SELLP, buy=BUYP):
    st = {SELL_NOW: {"state": str(sell_now), "attributes": {"start_time": START.isoformat()}},
          BUY_NOW: {"state": str(buy_now), "attributes": {"start_time": START.isoformat()}},
          SELL_F: {"state": "0", "attributes": {"Forecasts": forecasts(START, sell, -1, [p + 0.011 for p in sell])}},
          BUY_F: {"state": "0", "attributes": {"Forecasts": forecasts(START, buy, 1, [p - 0.013 for p in buy])}},
          EST: {"state": est, "attributes": {}}}
    return st


# ── cards API: every new card loads, filled in, with no old names ─────────────

async def test_new_cards_load(hass: HomeAssistant) -> None:
    client = await _setup(hass)
    listed = {c["id"]: c for c in (await (await client.get("/api/battman/cards")).json())["cards"]}
    for cid, needs in (("amber5minpricegrid", ["button-card"]), ("amber24hourforecasttable", ["button-card"]),
                       ("state", ["button-card"])):
        assert cid in listed and listed[cid]["source"] == "battman"
        card = await (await client.get(f"/api/battman/cards/{cid}")).json()
        assert card["missing_map"] == [] and card["needs"] == needs, cid
        text = yaml.safe_dump(card["config"])
        assert "[[map:" not in text
        raw = (CARDS / f"{cid}.yaml").read_text().lower()
        for old in ("smiggles", "solarsystemcontrol", "solar_system_control", "ssc", "amber-countdown"):
            assert old not in raw, (cid, old)


async def test_power_view_layout(hass: HomeAssistant) -> None:
    client = await _setup(hass)
    power = (await built(hass))["views"][0]
    s1 = [c["type"] for c in power["sections"][0]["cards"]]
    assert s1.index("custom:battman-state") + 1 == s1.index("custom:battman-profitloss")   # full order: test_v0160
    s2 = power["sections"][1]
    assert s2["column_span"] == 2
    assert [c["type"] for c in s2["cards"]] == ["custom:battman-amber5minpricegrid", "custom:battman-limits",
                                                "custom:battman-amber24hourforecasttable"]


async def test_countdown_and_no_browser_mod(hass: HomeAssistant) -> None:
    client = await _setup(hass)
    r = await client.get("/battmanfiles/battman-countdown.js")
    js = await r.text()
    assert r.status == 200 and "battmanDefine('battman-countdown'" in js
    orig = "(now.getMinutes() % 5) * 60 + now.getSeconds();\n    const totalSecs = 5 * 60 - secsInBlock;"
    assert orig in js                                            # same countdown maths as Smiggles
    issue = ir.async_get(hass).async_get_issue(DOMAIN, "missing_dependencies")
    assert "browser_mod" not in issue.translation_placeholders["missing"]   # Battman's popups are its own now


# ── amber5minpricegrid ───────────────────────────────────────────────────────

@needs_node
async def test_pricegrid(hass: HomeAssistant) -> None:
    m = (await _card(hass, "amber5minpricegrid"))["config"]
    js_m = m["cards"][0]["custom_fields"]["card"]
    scen = [price_states(-0.052, 0.183), price_states(-0.004, 0.071, "on"), price_states(0.021, -0.012),
            price_states(-0.27, 0.42, "on")]
    out = run_js([(js_m, s, None) for s in scen], env=PINNED)
    for o in out:
        assert not o.startswith("THROW") and "SELL" in o
    assert "Estimating" in out[1] and "Estimating" not in out[0]
    for n, o in enumerate(out):
        assert_snapshot(__file__, f"pricegrid-draw-{n}", o)

    def strip(x):
        if isinstance(x, dict):
            return {k: strip(v) for k, v in x.items() if k != "version"}
        if isinstance(x, list):
            return [strip(v) for v in x]
        return "JS" if isinstance(x, str) and x.strip().startswith("[[[") else x
    assert_snapshot(__file__, "pricegrid-layout", strip(m))


@needs_node
async def test_pricegrid_missing(hass: HomeAssistant) -> None:
    js = (await _card(hass, "amber5minpricegrid"))["config"]["cards"][0]["custom_fields"]["card"]
    unavailable = price_states("unavailable", "unavailable")
    no_fc = price_states(-0.05, 0.2)
    no_fc[BUY_F]["attributes"]["Forecasts"] = []
    gone = price_states(-0.05, 0.2)
    del gone[EST]
    out = run_js([(js, unavailable, None), (js, no_fc, None), (js, gone, None)])
    hero = out[0].split("SELL", 1)[1][:3000]
    assert "—" in out[0] and "NaN" not in out[0]
    assert "purple-soft-bg" not in out[0].split("BUY")[0].split("<div style='grid-column:1/-1;'>")[1].split("</svg>")[0]
    assert "text-muted" in hero                                   # neutral, not a price band
    assert "No BUY forecast from " + BUY_F in out[1]
    assert "Price grid: missing " + EST in out[2] and "SELL" not in out[2]


# ── amber24hourforecasttable ─────────────────────────────────────────────────

def times(html):
    return re.findall(r'<td class="at6t-td at6t-time"[^>]*>([^<—]+)</td>', html)


def local_label(iso):
    from zoneinfo import ZoneInfo
    return datetime.fromisoformat(iso).astimezone(ZoneInfo(HA_TZ)).strftime("%a %H:%M")


@needs_node
async def test_forecast_table(hass: HomeAssistant) -> None:
    js = (await _card(hass, "amber24hourforecasttable"))["config"]["cards"][0]["custom_fields"]["card"]
    for n, (sell_p, buy_p) in enumerate(((SELLP, BUYP), ([p * 1.7 - 0.05 for p in SELLP], [p * 0.6 for p in BUYP]))):
        st = price_states(-0.05, 0.2, sell=sell_p, buy=buy_p)
        mine = run_js([(js, st, None)])[0]
        assert "at6t-tr" in mine and mine.count("<tr class=\"at6t-tr\">") == len(sell_p)
        # v0.14.0: the time column is the interval start in HA's time zone
        assert times(mine) == [local_label(f["start_time"]) for f in st[SELL_F]["attributes"]["Forecasts"]]
        assert_snapshot(__file__, f"forecast-table-{n}", mine)

    # no forecasts: the error naming both sensors
    st = price_states(-0.05, 0.2, sell=[], buy=[])
    empty = run_js([(js, st, None)])[0]
    assert_snapshot(__file__, "forecast-table-empty", empty)


@needs_node
async def test_forecast_table_missing_values(hass: HomeAssistant) -> None:
    js = (await _card(hass, "amber24hourforecasttable"))["config"]["cards"][0]["custom_fields"]["card"]
    st = price_states(-0.05, 0.2)
    st[SELL_F]["attributes"]["Forecasts"][0].pop("per_kwh")                 # no price
    st[BUY_F]["attributes"]["Forecasts"] = st[BUY_F]["attributes"]["Forecasts"][1:]   # no buy row for the first time
    out = run_js([(js, st, None)])[0]
    first = out.split('<tr class="at6t-tr">')[1]
    cells = re.findall(r"<td[^>]*>([^<]*)</td>", first)
    assert cells[1] == "—" and cells[3] == "—" and cells[4] == "—"      # Sell price, Buy, Buy SS
    assert cells[2].endswith("c") and "0.00c" not in first           # the Sell SS prediction is real, so it shows
    gone = price_states(-0.05, 0.2)
    del gone[BUY_F]
    out = run_js([(js, gone, None)])[0]
    assert "Missing Amber forecast data" in out and BUY_F in out


# ── state ────────────────────────────────────────────────────────────────────

def state_states(scen, now: datetime | None = None):
    now = (now or datetime.now(timezone.utc)).replace(minute=0, second=0, microsecond=0)
    fin = forecasts(now, SELLP * 5, -1)
    gen = forecasts(now, BUYP * 5, 1)
    rules = [{"isActive": h % 3 == 0, "hours_ahead": 4, "grouping_minutes": 30, "offset": 1, "roundTo": 2,
              "roundtype": "floor"} for h in range(24)]
    run = {"needSun": scen == 1, "needPower": scen == 2, "needy": scen == 2,
           "sellReason": [scen == 3, 1 if scen == 3 else 0, "Sell" if scen == 3 else "No Sell"],
           "buyReason": [scen == 4, 1 if scen == 4 else 0, "Cheap" if scen == 4 else "No Buy"],
           "sellAbove": 40, "buyBelow": 30, "sellPricePreferred": 0.25, "sellPriceLow": 0.12, "buyPriceHigh": 0.08,
           "buyPricePreferred": 0.04, "sellPriceOverride": 0.3 if scen == 3 else 0, "sellAboveOverride": 20 if scen == 3 else 0}
    params = {"sellOverridePrice": 30 if scen == 3 else 0, "sellOverrideSOC": 20 if scen == 3 else 0,
              "buyAnytimePrice": 6 if scen == 4 else 0, "buyAnytimeSOC": 80 if scen == 4 else 0,
              "dailyNetworkCharge": 1.1, "buyProrateSOCOffset": 1, "sellProrateSOCOffset": 30}
    curve = {"buy": [10, 20, 30], "sell": [60, 50, 40]}
    return {
        "sensor.battman_run": {"state": "ok", "attributes": run},
        "sensor.battman_parameters": {"state": "ok", "attributes": params},
        "sensor.battman_buy_rules": {"state": "true", "attributes": {"rules": rules}},
        "sensor.battman_sell_rules": {"state": "true", "attributes": {"rules": rules}},
        "sensor.battman_soc_curves": {"state": "ok", "attributes": {"curves": {m: curve for m in
                                      ("jan feb mar apr may jun jul aug sep oct nov dec").split()}}},
        "sensor.battman_price_curves": {"state": "ok", "attributes": {"curves": {}}},
        "input_select.battman_mode": {"state": ["Self Consume", "Self Consume", "Charge", "Discharge", "Charge"][scen], "attributes": {}},
        "timer.battman_override_timer": {"state": "idle", "attributes": {}},
        SELL_NOW: {"state": "-0.081", "attributes": {}}, BUY_NOW: {"state": "0.172", "attributes": {}},
        SELL_F: {"state": "0", "attributes": {"Forecasts": fin}}, BUY_F: {"state": "0", "attributes": {"Forecasts": gen}},
        "sensor.sigen_plant_battery_state_of_charge": {"state": "57", "attributes": {}},
        "sensor.sigen_plant_battery_power": {"state": "-2.4", "attributes": {}},
        "sensor.sigen_plant_rated_energy_capacity": {"state": "40.3", "attributes": {}},
        "sensor.solcast_pv_forecast_forecast_today": {"state": "20", "attributes": {"detailedForecast": [
            {"period_start": (now + timedelta(minutes=30 * i)).isoformat(), "pv_estimate": max(0, 6 - abs(i - 6))} for i in range(48)]}},
        "sensor.solcast_pv_forecast_forecast_tomorrow": {"state": "20", "attributes": {"detailedForecast": []}},
    }


@needs_node
async def test_state(hass: HomeAssistant) -> None:
    m = (await _card(hass, "state"))["config"]
    main_m = m["custom_fields"]["content"]
    # the tap opens the forecast page (the engine's own forecast): there is no popup text to draw here
    assert m["tap_action"]["battman_popup"] == {"kind": "forecast", "url": "/battmanfiles/battman-forecast.html"}
    assert "browser_mod" not in json.dumps(m["tap_action"])

    def jobs_for(now=None):
        return [(main_m, state_states(scen, now), "sensor.battman_parameters") for scen in range(5)]

    out = run_js(jobs_for())
    for o in out:
        assert not o.startswith("THROW"), o
    assert all(len(out[s]) > 500 for s in range(5))
    assert len({out[s] for s in range(5)}) > 2                # the scenarios really differ

    # at a fixed time, zone and locale, recorded as snapshots
    out = run_js(jobs_for(FIXED_NOW), prelude=frozen_clock(FIXED_NOW), env=PINNED)
    for scen in range(5):
        assert not out[scen].startswith("THROW"), out[scen]
        assert len(out[scen]) > 500
        assert_snapshot(__file__, f"state-main-{scen}", out[scen])

    def strip(x):
        if isinstance(x, dict):
            return {k: strip(v) for k, v in x.items() if k != "version"}
        if isinstance(x, list):
            return [strip(v) for v in x]
        if isinstance(x, str):
            return "JS" if x.strip().startswith("[[[") else x.strip()
        return x
    assert_snapshot(__file__, "state-layout", strip(m))


@needs_node
async def test_state_missing(hass: HomeAssistant) -> None:
    m = (await _card(hass, "state"))["config"]
    main = m["custom_fields"]["content"]
    gone = state_states(0)
    del gone["sensor.battman_run"]
    out = run_js([(main, gone, None)])
    assert "State: missing sensor.battman_run" in out[0]
