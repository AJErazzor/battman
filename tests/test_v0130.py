"""v0.13.0: Amber 5-min price grid, Amber forecast table, State card, <battman-countdown>,
browser_mod in the dependency check, and the Power view in Smiggles order.

Each card is run (with node) next to the original Smiggles card on the same states:
with real values the output must be the same, apart from the intended renames."""

import json
import re
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.template import Template
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

DOMAIN = "battman"
FIX = Path(__file__).parent / "fixtures"
CARDS = Path(__file__).parents[1] / "custom_components/battman/cards"
needs_node = pytest.mark.skipif(not shutil.which("node"), reason="needs node to run the cards' JavaScript")

BUY_NOW, SELL_NOW = "sensor.amber_5min_current_general_price", "sensor.amber_5min_current_feed_in_price"
BUY_F, SELL_F = "sensor.amber_billing_interval_forecasts_general_price", "sensor.amber_billing_interval_forecasts_feed_in_price"
EST = "binary_sensor.solarsystemcontrolestimatedprice"
HA_TZ = "Australia/Adelaide"      # the time zone the fake HA reports to cards


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


def _orig(name):
    return yaml.safe_load((FIX / f"smiggles_{name}.yaml").read_text())[0]


def run_js(jobs):
    """Run button-card [[[ ]]] templates the way button-card does. jobs: [(src, states, entity_id)].
    All in one node process (same clock). Returns each output, or 'THROW: …'."""
    progs = []
    for src, states, ent in jobs:
        body = src.strip()
        assert body.startswith("[[[") and body.endswith("]]]")
        progs.append("(function(states, entity, hass, user, variables){" + body[3:-3] + "})"
                     f"({json.dumps(states)}, {json.dumps(states.get(ent))}, {{states: {json.dumps(states)}, config: {{time_zone: {json.dumps(HA_TZ)}}}}}, {{}}, {{}})")
    script = ("const out = [];\n" + "".join(
        f"try {{ out.push(String({p})); }} catch (e) {{ out.push('THROW: ' + e.message); }}\n" for p in progs)
        + "process.stdout.write(JSON.stringify(out));")
    r = subprocess.run(["node", "-"], input=script, capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def norm(s: str) -> str:
    return s.replace("--smiggles-", "--battman-")


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s)


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
    power = (await (await client.get("/api/battman/dashboard")).json())["views"][0]
    assert [c["type"] for c in power["sections"][0]["cards"]][-2:] == ["custom:battman-state", "custom:battman-profitloss"]
    s2 = power["sections"][1]
    assert s2["column_span"] == 2
    assert [c["type"] for c in s2["cards"]] == ["custom:battman-amber5minpricegrid", "custom:battman-limits",
                                                "custom:battman-amber24hourforecasttable"]


async def test_countdown_and_browser_mod(hass: HomeAssistant) -> None:
    client = await _setup(hass)
    r = await client.get("/battman/battman-countdown.js")
    js = await r.text()
    assert r.status == 200 and "customElements.define('battman-countdown'" in js
    orig = "(now.getMinutes() % 5) * 60 + now.getSeconds();\n    const totalSecs = 5 * 60 - secsInBlock;"
    assert orig in js                                            # same countdown maths as Smiggles
    issue = ir.async_get(hass).async_get_issue(DOMAIN, "missing_dependencies")
    assert "browser_mod" in issue.translation_placeholders["missing"]
    from custom_components.battman import dependencies

    MockConfigEntry(domain="browser_mod", data={}).add_to_hass(hass)
    assert "browser_mod" not in await dependencies.async_check(hass)


# ── amber5minpricegrid ───────────────────────────────────────────────────────

@needs_node
async def test_pricegrid_matches_smiggles(hass: HomeAssistant) -> None:
    m = (await _card(hass, "amber5minpricegrid"))["config"]
    o = _orig("amber5minpricegrid")
    js_m, js_o = m["cards"][0]["custom_fields"]["card"], o["cards"][0]["custom_fields"]["card"]
    scen = [price_states(-0.052, 0.183), price_states(-0.004, 0.071, "on"), price_states(0.021, -0.012),
            price_states(-0.27, 0.42, "on")]
    out = run_js([(j, s, None) for s in scen for j in (js_m, js_o)])
    for i in range(0, len(out), 2):
        assert not out[i].startswith("THROW") and "SELL" in out[i]
        assert out[i] == norm(out[i + 1]).replace("amber-countdown", "battman-countdown")
    assert "Estimating" in out[2] and "Estimating" not in out[0]

    # the rest of the card is the original's, renamed
    def strip(x):
        if isinstance(x, dict):
            return {k: strip(v) for k, v in x.items() if k != "version"}
        if isinstance(x, list):
            return [strip(v) for v in x]
        return "JS" if isinstance(x, str) and x.strip().startswith("[[[") else norm(x) if isinstance(x, str) else x
    assert strip(m) == strip(o)


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

def _jinja_table(hass):
    pkg = yaml.safe_load((FIX / "smiggles_amberforecast_sensor.yaml").read_text())
    return Template(pkg["template"][0]["sensor"][0]["attributes"]["friendly_table"], hass)


def times(html):
    return re.findall(r'<td class="at6t-td at6t-time"[^>]*>([^<—]+)</td>', html)


def local_label(iso):
    from zoneinfo import ZoneInfo
    return datetime.fromisoformat(iso).astimezone(ZoneInfo(HA_TZ)).strftime("%a %H:%M")


@needs_node
async def test_forecast_table_matches_smiggles(hass: HomeAssistant) -> None:
    js = (await _card(hass, "amber24hourforecasttable"))["config"]["cards"][0]["custom_fields"]["card"]
    tpl = _jinja_table(hass)
    for sell_p, buy_p in ((SELLP, BUYP), ([p * 1.7 - 0.05 for p in SELLP], [p * 0.6 for p in BUYP])):
        st = price_states(-0.05, 0.2, sell=sell_p, buy=buy_p)
        for e, v in st.items():
            hass.states.async_set(e, v["state"], v["attributes"])
        jin = tpl.async_render(parse_result=False)
        mine = run_js([(js, st, None)])[0]
        assert "at6t-tr" in mine and mine.count("<tr class=\"at6t-tr\">") == len(sell_p)
        # v0.14.0: the time column is the interval start in HA's time zone (Smiggles showed
        # NEM time), so compare everything else exactly and the times separately.
        cell1 = re.compile(r'(<td class="at6t-td at6t-time"[^>]*>)[^<]*(</td>)')
        assert squash(cell1.sub(r"\1T\2", norm(jin))) == squash(cell1.sub(r"\1T\2", mine))
        assert times(mine) == [local_label(f["start_time"]) for f in st[SELL_F]["attributes"]["Forecasts"]]

    # no forecasts: the same error naming both sensors
    for e in (SELL_F, BUY_F):
        hass.states.async_set(e, "0", {"Forecasts": []})
    st = price_states(-0.05, 0.2, sell=[], buy=[])
    assert squash(norm(tpl.async_render(parse_result=False))) == squash(run_js([(js, st, None)])[0])


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

def state_states(scen):
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
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
        "sensor.solarsystemcontrolrun": {"state": "ok", "attributes": run},
        "sensor.solarsystemcontrolparameters": {"state": "ok", "attributes": params},
        "sensor.solarsystemcontrolbuyrules": {"state": "true", "attributes": {"rules": rules}},
        "sensor.solarsystemcontrolsellrules": {"state": "true", "attributes": {"rules": rules}},
        "sensor.solar_system_control_soc_curves": {"state": "ok", "attributes": {"curves": {m: curve for m in
                                                   ("jan feb mar apr may jun jul aug sep oct nov dec").split()}}},
        "sensor.solar_system_control_price_curves": {"state": "ok", "attributes": {"curves": {}}},
        "input_select.solarsystemcontrolmode": {"state": ["Self Consume", "Self Consume", "Charge", "Discharge", "Charge"][scen], "attributes": {}},
        "timer.solarsystemoverridetimer": {"state": "idle", "attributes": {}},
        SELL_NOW: {"state": "-0.081", "attributes": {}}, BUY_NOW: {"state": "0.172", "attributes": {}},
        SELL_F: {"state": "0", "attributes": {"Forecasts": fin}}, BUY_F: {"state": "0", "attributes": {"Forecasts": gen}},
        "sensor.sigen_plant_battery_state_of_charge": {"state": "57", "attributes": {}},
        "sensor.sigen_plant_battery_power": {"state": "-2.4", "attributes": {}},
        "sensor.sigen_inverter_rated_battery_capacity": {"state": "40.3", "attributes": {}},   # what Smiggles read
        "sensor.sigen_plant_rated_energy_capacity": {"state": "40.3", "attributes": {}},      # what Battman reads (v0.14.0)
        "sensor.solcast_pv_forecast_forecast_today": {"state": "20", "attributes": {"detailedForecast": [
            {"period_start": (now + timedelta(minutes=30 * i)).isoformat(), "pv_estimate": max(0, 6 - abs(i - 6))} for i in range(48)]}},
        "sensor.solcast_pv_forecast_forecast_tomorrow": {"state": "20", "attributes": {"detailedForecast": []}},
    }


@needs_node
async def test_state_matches_smiggles(hass: HomeAssistant) -> None:
    m = (await _card(hass, "state"))["config"]
    o = _orig("state")
    main_m, main_o = m["custom_fields"]["content"], o["custom_fields"]["content"]
    pop_m, pop_o = (x["tap_action"]["browser_mod"]["data"]["content"] for x in (m, o))
    jobs = []
    for scen in range(5):
        st = state_states(scen)
        jobs += [(main_m, st, "sensor.solarsystemcontrolparameters"), (main_o, st, "sensor.solarsystemcontrolparameters"),
                 (pop_m, st, None), (pop_o, st, None)]
    out = run_js(jobs)
    for i in range(0, len(out), 2):
        assert not out[i].startswith("THROW"), out[i]
        assert len(out[i]) > 500
        assert out[i] == norm(out[i + 1])
    assert len({out[i] for i in range(0, len(out), 4)}) > 2            # the scenarios really differ

    def strip(x):
        if isinstance(x, dict):
            return {k: strip(v) for k, v in x.items() if k != "version"}
        if isinstance(x, list):
            return [strip(v) for v in x]
        if isinstance(x, str):
            return "JS" if x.strip().startswith("[[[") else norm(x).strip()
        return x
    so = strip(o)
    so["entity"] = "sensor.solarsystemcontrolparameters"
    assert strip(m) == so


@needs_node
async def test_state_missing(hass: HomeAssistant) -> None:
    m = (await _card(hass, "state"))["config"]
    main = m["custom_fields"]["content"]
    pop = m["tap_action"]["browser_mod"]["data"]["content"]
    gone = state_states(0)
    del gone["sensor.solarsystemcontrolrun"]
    no_cap = state_states(0)
    no_cap["sensor.sigen_plant_rated_energy_capacity"]["state"] = "unavailable"
    no_sun = state_states(0)
    del no_sun["sensor.solcast_pv_forecast_forecast_tomorrow"]
    out = run_js([(main, gone, None), (pop, gone, None), (pop, no_cap, None), (pop, no_sun, None)])
    assert "State: missing sensor.solarsystemcontrolrun" in out[0]
    assert "Next hours: missing sensor.solarsystemcontrolrun" in out[1]
    assert "battery capacity (sensor.sigen_plant_rated_energy_capacity) unavailable" in out[2]
    assert "40.3" not in out[2]
    assert out[3].startswith('<div style="padding:4px') and "assumes no solar" in out[3]
