"""Retake the guide's card pictures from the real cards.

    BATTMAN_CHROME=<chromium> BATTMAN_NODE_PATH=<node_modules with playwright> \
        python tools/guide-screenshots/shoot.py [name ...]

Draws the real Settings card (www/battman-settings.js) and the real Amber forecast table template
(cards/amber24hourforecasttable.yaml) in headless Chrome, in the Battman Coffee theme, and writes the
pictures into www/guide-images/ at twice the size they are shown. Nothing is drawn by hand:

- the settings come from what the parameters and rules packages produce with nothing saved, so the
  pictures show the real defaults, labels and limits;
- the sample data (which hours have a rule, the prices) lives here, in one place, and the clock is
  fixed (Wed 25 Nov 2026, 14:07 Adelaide), so a retake only differs when a card does.

Pictures made: settings-sell-rules, settings-sell-solar, power-amber24hourforecasttable.
Add one by adding a SHOTS entry here and its drawing in shoot.mjs.
"""
import ast
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jinja2
import yaml

ROOT = Path(__file__).resolve().parents[2]
BATTMAN = ROOT / "custom_components/battman"
TZ = "Australia/Adelaide"
NOW = datetime(2026, 11, 25, 14, 7, tzinfo=timezone(timedelta(hours=10, minutes=30)))   # ACDT

# name -> what to draw: the section of the Settings card, or the forecast table
SHOTS = {
    "settings-sell-rules":            {"kind": "settings", "section": "sellRules", "width": 420},
    "settings-sell-solar":            {"kind": "settings", "section": "sellSolar", "width": 420},
    "power-amber24hourforecasttable": {"kind": "table", "width": 600, "height": 392},
}


def theme(name: str = "Battman Coffee") -> dict:
    doc = yaml.safe_load((BATTMAN / "themes" / f"{name}.yaml").read_text(encoding="utf-8"))
    return {k: str(v) for k, v in doc[name].items() if isinstance(v, (str, int, float))}


def entity_map() -> dict:
    spec = importlib.util.spec_from_file_location("battman_const", BATTMAN / "const.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return dict(mod.ENTITY_MAP_DEFAULTS)


def render_defaults(attributes: dict) -> dict:
    """What a template sensor's attributes come to with nothing saved and no event (a fresh install)."""
    env = jinja2.Environment()
    env.globals["now"] = lambda: NOW
    out = {}
    for key, tpl in attributes.items():
        if not isinstance(tpl, str):
            out[key] = tpl
            continue
        text = ""
        try:
            text = env.from_string(tpl).render(this={"attributes": {}}).strip()
            out[key] = ast.literal_eval(text)
        except Exception:
            out[key] = text or None                          # plain text, or a template that needs a live HA
    return {k: v for k, v in out.items() if v is not None}


def sensor_attributes(package: str, name: str) -> dict:
    doc = yaml.safe_load((BATTMAN / "packages" / package).read_text(encoding="utf-8"))
    for block in doc["template"]:
        for s in block.get("sensor", []):
            if s.get("name") == name:
                return s["attributes"]
    raise SystemExit(f"{name} not found in {package}")


def settings_fixture() -> dict:
    params = render_defaults(sensor_attributes("battman_parameters.yaml", "Battman parameters"))
    rules = render_defaults(sensor_attributes("battman_rules.yaml", "Battman sell rules"))["rules"]
    # sample rules: a morning rule, a run of daytime hours that also sell solar, an evening peak, and one
    # hour switched off that still has Sell solar on (it stays grey: an inactive rule does nothing)
    def set_(h, **kw):
        rules[h].update(kw)
    for h in (7, 8, 9):
        set_(h, isActive=True, hours_ahead=4, roundTo=1)
    for h in range(10, 16):
        set_(h, isActive=True, allowSellSolar=True, hours_ahead=6, offset=1)
    for h in range(16, 22):
        set_(h, isActive=True, allowLastChance=True, hours_ahead=3, grouping_minutes=30, roundtype="ceil")
    set_(22, allowSellSolar=True)
    return {
        "params": params,
        "sell_rules": {"state": "true", "attributes": {"rules": rules, "selected_hour": NOW.hour}},
        "buy_rules": {"state": "true", "attributes": {"rules": render_defaults(sensor_attributes("battman_rules.yaml", "Battman buy rules"))["rules"]}},
    }


def table_fixture() -> dict:
    card = yaml.safe_load((BATTMAN / "cards/amber24hourforecasttable.yaml").read_text(encoding="utf-8"))
    body = card["card"]["custom_fields"]["card"] if "card" in card else None
    if body is None:                                         # the card file's layout, found by looking for the template
        def find(o):
            if isinstance(o, dict):
                if "custom_fields" in o and "card" in o["custom_fields"]:
                    return o["custom_fields"]["card"]
                for v in o.values():
                    r = find(v)
                    if r:
                        return r
            elif isinstance(o, list):
                for v in o:
                    r = find(v)
                    if r:
                        return r
        body = find(card)
    assert body and "[[[" in body, "couldn't find the forecast table's template"
    start = NOW.replace(minute=0, second=0, microsecond=0)                                   # the current half hour
    earn = [11, 11, 11, 5.4, 5, 4.8, 1, 1, -2, -2, -2, -2, 1, 1, 3, 6, 9, 12, 14, 14, 11, 11, 8, 5]  # c/kWh you earn
    pay = [30, 30, 30, 22, 18, 18, 6, 6, -1, -1, -1, -1, 6, 6, 9, 14, 24, 30, 36, 36, 30, 30, 26, 22]  # c/kWh you pay

    def rows(values, sign, ratio):
        out = []
        for i, v in enumerate(values):
            st = start + timedelta(minutes=30 * i)
            raw = sign * v / 100
            out.append({"start_time": st.astimezone(timezone.utc).isoformat(), "duration": 30, "per_kwh": raw,
                        "nem_date": (st + timedelta(minutes=30)).astimezone(timezone(timedelta(hours=10))).isoformat(),
                        "advanced_price": {"predicted": round(raw * ratio, 5)}})
        return out
    return {"js": body, "states": {
        "sensor.amber_billing_interval_forecasts_feed_in_price": {"state": "0", "attributes": {"Forecasts": rows(earn, -1, 1.06)}},
        "sensor.amber_billing_interval_forecasts_general_price": {"state": "0", "attributes": {"Forecasts": rows(pay, 1, 1.04)}},
        "sensor.amber_5min_current_feed_in_price": {"state": "0.108", "attributes": {}},      # positive = earning
        "sensor.amber_5min_current_general_price": {"state": "0.312", "attributes": {}},
    }}


def main() -> None:
    wanted = sys.argv[1:] or list(SHOTS)
    unknown = [w for w in wanted if w not in SHOTS]
    if unknown:
        raise SystemExit(f"unknown picture(s): {', '.join(unknown)}; choose from {', '.join(SHOTS)}")
    cfg = {"theme": theme(), "now": NOW.isoformat(), "tz": TZ, "map": entity_map(), "settings": settings_fixture(),
           "table": table_fixture(), "www": str(BATTMAN / "www"),
           "out": os.environ.get("BATTMAN_SHOTS_OUT") or str(BATTMAN / "www/guide-images"),      # the tests draw into a temp folder
           "shots": {k: SHOTS[k] for k in wanted}}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(cfg, f)
    env = {**os.environ}
    if os.environ.get("BATTMAN_NODE_PATH"):
        env["NODE_PATH"] = os.environ["BATTMAN_NODE_PATH"]
    try:
        subprocess.run(["node", str(Path(__file__).with_name("shoot.mjs")), f.name], check=True, env=env)
    finally:
        os.unlink(f.name)


if __name__ == "__main__":
    main()
