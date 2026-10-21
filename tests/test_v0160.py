"""v0.16.0: Overrides card on battman-lib.js.

Every button-card template in the card is run twice on the same states: the original
Smiggles card with its own ssc-lib.js (v8), and Battman's card with battman-lib.js. After
the renames, the outputs must be the same; the only allowed differences are Battman's
"no made-up values" fixes (marked isNaN / NTBAD / ntBlocked) and the scene script going
through the entity map."""

import difflib
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("smiggles_installed")

DOMAIN = "battman"
FIX = Path(__file__).parent / "fixtures"
WWW = Path(__file__).parents[1] / "custom_components/battman/www"
CARDS = Path(__file__).parents[1] / "custom_components/battman/cards"
needs_node = pytest.mark.skipif(not shutil.which("node"), reason="needs node to run the cards' JavaScript")
PARAMS = "sensor.solarsystemcontrolparameters"

# the page stand-in the templates need (window, document, localStorage, getComputedStyle)
SHIM = """
globalThis.window = globalThis;
const _ls = {}; globalThis.localStorage = { getItem: k => (k in _ls ? _ls[k] : null), setItem: (k, v) => { _ls[k] = String(v); } };
globalThis.getComputedStyle = () => ({ getPropertyValue: () => '' });
globalThis.setTimeout = () => 0; globalThis.clearTimeout = () => {}; globalThis.setInterval = () => 0;
globalThis.document = { querySelector: () => ({ hass: globalThis.__hass }), querySelectorAll: () => [],
  createElement: () => ({ style: {} }), head: { appendChild() {} }, body: {}, documentElement: {}, dispatchEvent() {} };
"""


def run_templates(lib_js, jobs, states):
    """jobs: [(template, variables, entity_id)] -> outputs (strings, or 'THROW: …')."""
    hass = {"states": states, "user": {"name": "A.J."}, "config": {"time_zone": "Australia/Adelaide"}}
    parts = [SHIM, f"globalThis.__hass = {json.dumps(hass)};", lib_js, "const out = [];"]
    for src, variables, ent in jobs:
        body = src.strip()[3:-3]
        parts.append(
            "try { out.push(String((function(states, entity, user, hass, variables){" + body + "})"
            f"({json.dumps(states)}, {json.dumps(states.get(ent))}, {{name:'A.J.'}}, globalThis.__hass, "
            f"{json.dumps(variables)}))); }} catch (e) {{ out.push('THROW: ' + e.message); }}")
    parts.append("process.stdout.write(JSON.stringify(out));")
    r = subprocess.run(["node", "-"], input="\n".join(parts), capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def templates(card, variables=None, entity=None, path=()):
    """Every [[[ ]]] template with the button-card variables / entity it runs with."""
    if isinstance(card, dict):
        if card.get("type") == "custom:button-card":
            variables, entity = card.get("variables", {}), card.get("entity")
        for k, v in card.items():
            yield from templates(v, variables, entity, (*path, k))
    elif isinstance(card, list):
        for i, v in enumerate(card):
            yield from templates(v, variables, entity, (*path, i))
    elif isinstance(card, str) and card.strip().startswith("[[["):
        yield path, card, variables, entity


def norm(s: str) -> str:
    """Rename the original's names to Battman's (what the card port did)."""
    s = s.replace("/local/smiggles/ssc-lib.js?v=8", "/battman/battman-lib.js").replace("/local/smiggles/ssc-lib.js?v=1", "/battman/battman-lib.js")
    s = s.replace("ssc_timer_unit", "battman_timer_unit")
    s = s.replace("__ssclibLoad", "__battmanLibLoad").replace("SSCLIB", "BattmanLib").replace("variables.ssc", "variables.battman")
    s = re.sub(r"\bssc(?=[A-Za-z_-])", "bm", s)
    return s.replace("--smiggles-", "--battman-")


def fc(n=40):
    from datetime import datetime, timedelta, timezone
    t0 = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    return [{"start_time": (t0 + timedelta(minutes=30 * i)).isoformat(), "end_time": (t0 + timedelta(minutes=30 * i + 30)).isoformat(),
             "duration": 30, "per_kwh": 0.05 + (i % 9) * 0.03, "advanced_price_predicted": 0.04 + (i % 9) * 0.03} for i in range(n)]


def scenario(kind):
    p = {"sellOverrideSOC": 0, "sellOverridePrice": 0, "sellSolarSOC": 0, "sellSolarPrice": 0, "buyOverrideSOC": 0,
         "buyOverridePrice": 0, "buyAnytimeSOC": 0, "buyAnytimePrice": 0, "drainBatterySOC": 0, "drainBatteryPrice": 0,
         "dailyNetworkCharge": 1.1, "netTargetSellPrice": 0, "netTargetBuyPrice": 0, "pinnedOverrides": [],
         "overridePresets": [{"name": "Cheap", "timer": 7200, "values": {"any": {"soc": 80, "price": 9, "allowReset": True}}},
                             {"name": "Evening", "timer_at": "21:00", "values": {"sell": {"soc": 30, "price": 25}}}]}
    if kind == "set":
        p.update(sellOverrideSOC=30, sellOverridePrice=25.5, buyAnytimeSOC=80, buyAnytimePrice=9, buyAnytimeAllowReset=False,
                 drainBatterySOC=20, drainBatteryPrice=4, drainBatteryPlughole=True, netTargetSellPrice=3.5, sellSolarPinned="show")
    states = {
        PARAMS: {"entity_id": PARAMS, "state": "ok", "attributes": p},
        "sensor.sigen_plant_battery_state_of_charge": {"state": "57.4", "attributes": {}},
        "sensor.sigen_inverter_battery_state_of_charge": {"state": "57.4", "attributes": {}},
        "sensor.sigen_plant_rated_energy_capacity": {"state": "40.3", "attributes": {}},
        "sensor.sigen_plant_available_max_active_power": {"state": "15", "attributes": {}},
        "sensor.amber_billing_interval_forecasts_general_price": {"state": "0.1", "attributes": {"Forecasts": fc()}},
        "sensor.amber_5min_current_general_price": {"state": "0.12", "attributes": {}},
        "sensor.solarsystemcontrolselltotal": {"state": "1", "attributes": {"day": 4.21}},
        "sensor.solarsystemcontrolbuytotal": {"state": "1", "attributes": {"day": 1.37}},
        "sensor.solarsystemcontrolrun": {"state": "ok", "attributes": {}},
        "input_select.solarsystemcontrolmode": {"state": "Self Consume", "attributes": {}},
        "timer.solarsystemoverridetimer": {"state": "active" if kind == "set" else "idle",
                                            "attributes": {"finishes_at": "2099-01-01T10:00:00+10:30", "remaining": "1:00:00"}},
        "sun.sun": {"state": "above_horizon", "attributes": {"next_rising": "2099-01-01T06:00:00+10:30",
                                                             "next_setting": "2099-01-01T19:30:00+10:30"}},
    }
    return states


async def _served(hass, hass_client):
    assert await async_setup_component(hass, "lovelace", {})
    MockConfigEntry(domain=DOMAIN, title="Battman", data={}).add_to_hass(hass)
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_client()
    card = await (await client.get("/api/battman/cards/overrides")).json()
    return client, card


async def test_overrides_card_loads(hass: HomeAssistant, hass_client) -> None:
    client, card = await _served(hass, hass_client)
    assert card["missing_map"] == [] and card["needs"] == ["button-card"]
    raw = (CARDS / "overrides.yaml").read_text()
    for old in (r"smiggles", r"solarsystemcontrol", r"(?<![a-z])ssc", r"kwh_per_pct:"):
        assert not re.search(old, raw, re.I), old
    text = json.dumps(card["config"])
    assert "/battman/battman-lib.js" in text and "script.ssc_apply_scene" in text      # the map's scene script
    power = (await (await client.get("/api/battman/dashboard")).json())["views"][0]
    assert power["sections"][0]["cards"][-1] == {"type": "custom:battman-overrides"}


async def test_overrides_structure_matches(hass: HomeAssistant, hass_client) -> None:
    """Everything except the templates is the original's, renamed (kwh_per_pct dropped)."""
    _c, card = await _served(hass, hass_client)
    o = yaml.safe_load((FIX / "smiggles_overrides.yaml").read_text())[0]

    def strip(x):
        if isinstance(x, dict):
            return {("battman" if k == "ssc" else k): strip(v) for k, v in x.items() if k not in ("version", "kwh_per_pct")}
        if isinstance(x, list):
            return [strip(v) for v in x]
        if isinstance(x, str):
            return "JS" if x.strip().startswith("[[[") else norm(x)
        return x
    so, sm = strip(o), strip(card["config"])
    # net_src (Net Target maths): the only change is "missing total = unknown, not $0"
    ns = so["cards"][0]["variables"]["battman"]["net_src"]
    for old, new in (("return x && x.attributes ? (parseFloat(x.attributes.day) || 0) : 0; }",
                      "return x && x.attributes ? parseFloat(x.attributes.day) : NaN; }  /* Battman: missing total = unknown, not $0 */"),
                     ("function money(v) { var n", 'function money(v) { if (isNaN(v)) return "\u2014"; var n')):
        assert ns.count(old) == 1
        ns = ns.replace(old, new)
    so["cards"][0]["variables"]["battman"]["net_src"] = ns
    def diff(a, b, p=""):
        if isinstance(a, dict) and isinstance(b, dict):
            return [d for k in sorted(set(a) | set(b)) for d in diff(a.get(k), b.get(k), f"{p}/{k}")]
        if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
            return [d for i, (x, y) in enumerate(zip(a, b)) for d in diff(x, y, f"{p}[{i}]")]
        return [] if a == b else [(p, str(a)[:120], str(b)[:120])]
    assert diff(so, sm) == []


def _unexplained(a, b, allowed):
    """Changed chunks (split at ;) whose Battman side carries none of the fix markers."""
    A, B = a.split(";"), b.split(";")
    bad = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, A, B, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        new = ";".join(B[j1:j2])
        if op == "delete" or not any(w in new for w in allowed):
            bad.append((";".join(A[i1:i2])[:150], new[:150]))
    return bad


@needs_node
@pytest.mark.parametrize("kind", ["empty", "set"])
async def test_overrides_output_matches(hass: HomeAssistant, hass_client, kind) -> None:
    _c, card = await _served(hass, hass_client)
    o = yaml.safe_load((FIX / "smiggles_overrides.yaml").read_text())[0]
    t_o, t_m = list(templates(o)), list(templates(card["config"]))
    assert len(t_o) == len(t_m) > 20
    states = scenario(kind)
    out_o = run_templates((FIX / "smiggles_ssc_lib.js").read_text(), [(s, v, e) for _p, s, v, e in t_o], states)
    out_m = run_templates((WWW / "battman-lib.js").read_text(), [(s, v, e) for _p, s, v, e in t_m], states)
    allowed = ("isNaN", ":NaN", "NTBAD", "ntBlocked", "apply_scene", "libWait")   # libWait: v0.18.2, waits for the library
    for (path, *_), a, b in zip(t_o, out_o, out_m, strict=True):
        assert not b.startswith("THROW"), (path, b)
        a = norm(a)
        if a == b:
            continue
        bad = _unexplained(a, b, allowed)
        assert not bad, (path, bad[:6])
    # the rows really drew something
    rows = [b for (p, *_), b in zip(t_m, out_m) if p[-2:] == ("custom_fields", "content") and p[1] in range(1, 7) and "SOC" in b]
    assert rows
    if kind == "set":
        assert any("57% → 30%" in r and "11.0 kWh" in r for r in rows)     # (57.4-30) x 40.3/100


@needs_node
async def test_rows_no_made_up_values(hass: HomeAssistant, hass_client) -> None:
    lib = (WWW / "battman-lib.js").read_text()
    _c, card = await _served(hass, hass_client)
    row = next((v, s) for p, s, v, e in templates(card["config"]) if "renderRow" in s)
    states = scenario("set")
    states["sensor.sigen_plant_battery_state_of_charge"]["state"] = "unavailable"
    no_cap = scenario("set")
    no_cap["sensor.sigen_plant_rated_energy_capacity"]["state"] = "unavailable"
    (v, src) = row
    out = run_templates(lib, [(src, v, PARAMS)], states)[0] + run_templates(lib, [(src, v, PARAMS)], no_cap)[0]
    assert "—% → 30%" in out and "— kWh" in out and "target met" not in out and "NaN" not in out


@needs_node
async def test_net_target_without_totals(hass: HomeAssistant, hass_client) -> None:
    _c, card = await _served(hass, hass_client)
    states = scenario("set")
    del states["sensor.solarsystemcontrolbuytotal"]
    head = next((s, v) for p, s, v, e in templates(card["config"]) if p[:3] == ("cards", 0, "custom_fields"))
    out = run_templates((WWW / "battman-lib.js").read_text(), [(head[0], head[1], PARAMS)], states)[0]
    assert "$NaN" not in out and "NaN" not in out and "—" in out


def test_lib_open_popup_fixed() -> None:
    js = (WWW / "battman-lib.js").read_text()
    assert "var variables = {battman: cfg};" in js and "{bmc: cfg}" not in js
