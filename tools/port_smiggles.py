"""Port the Smiggles engine (its packages/, scripts/, automations/) into Battman.

Usage: python tools/port_smiggles.py <path to a Smiggles checkout>
Re-runnable: it rewrites Battman's ported files from the Smiggles originals. The test
suite runs the ported engine and the original side by side and checks they decide the same.

Like for like: only names change. Smiggles entities/events -> battman_*; Sigen / Amber /
Solcast entities -> [[map:...]] markers (filled from Battman's entity map when written).
Battman engine automations get one extra condition: binary_sensor.battman_in_charge is on.

Writes:
  custom_components/battman/packages/battman_*.yaml          (template sensors, helpers)
  custom_components/battman/blueprints/script/battman_*.yaml
  custom_components/battman/blueprints/automation/battman_engine_*.yaml
"""
import re
import sys
from pathlib import Path

import yaml

SM = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("Smiggles-main")
REPO = Path(__file__).resolve().parents[1] / "custom_components" / "battman"
PKG = REPO / "packages"
BP = REPO / "blueprints"

# ── Smiggles names -> Battman names (entities lower-cased; HA ids are case-insensitive here) ──
ENTITIES = {
    "sensor.solarsystemcontrolparameters": "sensor.battman_parameters",
    "sensor.solarsystemcontrolrun": "sensor.battman_run",
    "sensor.solarsystemcontrolbuyrules": "sensor.battman_buy_rules",
    "sensor.solarsystemcontrolsellrules": "sensor.battman_sell_rules",
    "sensor.solarsystemcontrolbuytotal": "sensor.battman_buy_total",
    "sensor.solarsystemcontrolselltotal": "sensor.battman_sell_total",
    "sensor.solarsystemcontrolnetworkaccessfee": "sensor.battman_network_fee",
    "sensor.solarsystemcontrolpowerproviderbuy": "sensor.battman_power_provider_buy",
    "sensor.solarsystemcontrolpowerprovidersell": "sensor.battman_power_provider_sell",
    "sensor.solar_system_control_soc_curves": "sensor.battman_soc_curves",
    "sensor.solar_system_control_price_curves": "sensor.battman_price_curves",
    "sensor.solar_system_control_debug_log": "sensor.battman_engine_log",
    "binary_sensor.solarsystemcontrolestimatedprice": "binary_sensor.battman_estimated_price",
    "sensor.solarsystemcontrolload30mavg": "sensor.battman_load_30m_avg",
    "input_boolean.solarsystemcontrolenable": "input_boolean.battman_enable",
    "input_boolean.solarsystemcontrolnoexport": "input_boolean.battman_no_export",
    "input_select.solarsystemcontrolmode": "input_select.battman_mode",
    "timer.solarsystemoverridetimer": "timer.battman_override_timer",
    "script.solarsystemcontrol": "script.battman_engine",
    "script.ssc_apply_scene": "script.battman_apply_scene",
}
EVENTS = {
    "solarsystemcontrolparametersupdate": "battman_parameters_update",
    "solarsystemcontrolrunupdate": "battman_run_update",
    "solarsystemcontrolbuyrulesattribute": "battman_buy_rules_update",
    "solarsystemcontrolsellrulesattribute": "battman_sell_rules_update",
    "solarsystemcontroltotalattribute": "battman_totals_update",
    "solarsystemcontrolpowerproviderupdate": "battman_power_provider_update",
    "solar_system_control_soc_curves_update": "battman_soc_curves_update",
    "solar_system_control_price_curves_update": "battman_price_curves_update",
    "SolarSystemControlDebugLog": "battman_engine_log",
}
# third-party entities -> entity map entries (stay on the map for good)
MAPPED = {
    "sensor.amber_5min_current_general_price": "buy_price",
    "sensor.amber_5min_current_feed_in_price": "feed_in_price",
    "sensor.amber_billing_interval_forecasts_general_price": "buy_forecast",
    "sensor.amber_billing_interval_forecasts_feed_in_price": "feed_in_forecast",
    "sensor.sigen_plant_battery_state_of_charge": "battery_soc",
    "sensor.sigen_plant_consumed_power": "home_power",
    "sensor.sigen_plant_grid_import_power": "grid_import_power",
    "sensor.sigen_plant_grid_export_power": "grid_export_power",
    "sensor.sigen_plant_rated_energy_capacity": "rated_energy_capacity",
    "sensor.sigen_plant_sigen_pv_power": "sigen_pv_power",
    "sensor.sigen_plant_third_party_pv_power": "third_party_pv",
    "sensor.sigen_inverter_rated_active_power": "inverter_rated_power",
    "sensor.sigen_plant_ess_rated_charging_power": "rated_charging_power",
    "sensor.sigen_plant_ess_rated_discharging_power": "rated_discharging_power",
    "sensor.sigen_plant_grid_connection_status": "grid_connection_status",
    "sensor.sigen_plant_total_imported_energy": "total_imported_energy",
    "sensor.sigen_plant_total_exported_energy": "total_exported_energy",
    "number.sigen_plant_grid_export_limitation": "grid_export_limit",
    "number.sigen_plant_pv_max_power_limit": "pv_max_limit",
    "number.sigen_plant_ess_max_charging_limit": "max_charge_limit",
    "select.sigen_plant_remote_ems_control_mode": "ems_control_mode",
    "sensor.solcast_pv_forecast_forecast_remaining_today": "solcast_remaining_today",
    "sensor.solcast_pv_forecast_forecast_next_hour": "solcast_next_hour",
    "sensor.solarsystemcontrolload30m": "load_30m",
}
# words in names, titles and log text
WORDS = [
    ("SolarSystemControlParameters", "Battman parameters"),
    ("SolarSystemControlRun", "Battman run"),
    ("SolarSystemControlBuyRules", "Battman buy rules"),
    ("SolarSystemControlSellRules", "Battman sell rules"),
    ("SolarSystemControlBuyTotal", "Battman buy total"),
    ("SolarSystemControlSellTotal", "Battman sell total"),
    ("SolarSystemControlNetworkAccessFee", "Battman network fee"),
    ("SolarSystemControlPowerProviderBuy", "Battman power provider buy"),
    ("SolarSystemControlPowerProviderSell", "Battman power provider sell"),
    ("Solar System Control SOC Curves", "Battman SOC curves"),
    ("Solar System Control Price Curves", "Battman price curves"),
    ("Solar System Control Debug Log", "Battman engine log"),
    ("SolarSystemControlEstimatedPrice", "Battman estimated price"),
    ("Solar System Control Watchdog", "Battman watchdog"),
    ("Solar System Control", "Battman"),
    ("Solar System Override Timer", "Battman override timer"),
    ("SolarSystem Override Timer", "Battman override timer"),
    ("SolarSystemControl", "Battman"),
    ("Smiggles Curves Updated", "Battman curves updated"),
    ("Battery Time scene", "Battman scene"),
    ("SSC Apply Scene", "Battman apply scene"),
    ("SSC Apply Armed Scene", "Battman apply armed scene"),
    ("automation ssc_apply_armed_scene", "the Battman armed-scene automation"),
    ("(packages/ssc_scenes.yaml)", "(blueprint battman_engine_armed_scene)"),
    ("ssc_apply_armed_scene", "battman_apply_armed_scene"),
    ("Smiggles", "Battman"),
    ("  ssc_apply_scene:", "  battman_apply_scene:"),
    (" (ssc_scenes.yaml v1.2.0)", ""),
    ("ssc_armed_scene_missing", "battman_armed_scene_missing"),
]
UNIQUE = {
    "solarsystemcontrolparameters": "battman_parameters",
    "solarsystemcontrolrun": "battman_run",
    "solarsystemcontrolbuyrules": "battman_buy_rules",
    "solarsystemcontrolsellrules": "battman_sell_rules",
    "solarsystemcontrolbuytotal": "battman_buy_total",
    "solarsystemcontrolselltotal": "battman_sell_total",
    "solarsystemcontrolnetworkaccessfee": "battman_network_fee",
    "solarsystemcontrolpowerproviderbuy": "battman_power_provider_buy",
    "solarsystemcontrolpowerprovidersell": "battman_power_provider_sell",
    "solarsystemsontrolsoccurves": "battman_soc_curves",
    "solarsystemcontrolpricecurves": "battman_price_curves",
    "SolarSystemControlDebugLog": "battman_engine_log",
}


def rename(text: str, where: str) -> str:
    for old, new in UNIQUE.items():
        text = re.sub(r"(unique_id:\s*)" + re.escape(old) + r"\b", r"\g<1>" + new, text)
    for old, new in sorted(ENTITIES.items(), key=lambda kv: -len(kv[0])):
        text = re.sub(re.escape(old) + r"(?![a-z0-9_])", new, text, flags=re.I)
    for old, key in sorted(MAPPED.items(), key=lambda kv: -len(kv[0])):
        text = re.sub(re.escape(old) + r"(?![a-z0-9_])", f"[[map:{key}]]", text, flags=re.I)
    for old, new in sorted(EVENTS.items(), key=lambda kv: -len(kv[0])):
        text = re.sub(r"(?<![a-z0-9_])" + re.escape(old) + r"(?![a-z0-9_])", new, text)
    for old, new in WORDS:
        text = text.replace(old, new)
    text = text.replace("notification_id: solar_system_control", "notification_id: battman_engine")
    text = text.replace("notification_id: solarsystemcontrol_watchdog", "notification_id: battman_watchdog")
    left = re.findall(r"(?i)[^\n]*(?:solarsystem|solar_system|smiggles|(?<![a-z])ssc)[^\n]*", text)
    if left:
        sys.exit(f"{where}: Smiggles names left:\n  " + "\n  ".join(x.strip()[:140] for x in left[:12]))
    return text


HEADER = """# Battman engine: ported like for like from Smiggles ({src}).
# Managed by Battman: written into your config and replaced on every Battman update.
# Don't edit this copy. [[map:...]] markers are filled from Battman's entity map.
"""


GATE_LINES = ("      - condition: state\n"
              "        entity_id: binary_sensor.battman_in_charge\n"
              "        state: \"on\"\n")


def gate_triggers(text: str, where: str) -> str:
    """Trigger-based template sensors only update while Battman is in charge (like the automations)."""
    parts = re.split(r"(?m)^(  - trigger:[^\n]*\n)", text)
    out, n = [parts[0]], 0
    for i in range(1, len(parts), 2):
        head, block = parts[i], parts[i + 1]
        m = re.search(r"(?m)^    condition:[ \t]*\n", block)
        if m:
            block = block[:m.end()] + GATE_LINES + block[m.end():]
        else:
            m = re.search(r"(?m)^    (sensor|binary_sensor):", block)
            assert m, f"{where}: trigger block without sensor"
            block = block[:m.start()] + "    condition:\n" + GATE_LINES + block[m.start():]
        out += [head, block]
        n += 1
    return "".join(out)


def write(path: Path, text: str) -> None:
    yaml.safe_load(re.sub(r"!\w+", "", text).replace("[[map:", "x").replace("]]", ""))   # parses
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def strip_header(text: str) -> str:
    """Drop the Smiggles '####' version banner at the top (kept in Battman's header line)."""
    lines = text.split("\n")
    while lines and (lines[0].startswith("#") or not lines[0].strip()):
        lines.pop(0)
    return "\n".join(lines)


def banner(text: str) -> str:
    m = re.search(r"#\s*version:?\s*([0-9.]+)", text)
    return m.group(1) if m else "?"


# ── packages ────────────────────────────────────────────────────────────────
for src, dst in [("solarsystemcontrolparameters.yaml", "battman_parameters.yaml"),
                 ("solarsystemcontrolrun.yaml", "battman_run.yaml"),
                 ("solarsystemcontrolrules.yaml", "battman_rules.yaml"),
                 ("solarsystemcontrolpowerprovider.yaml", "battman_power_provider.yaml"),
                 ("solarsystemcontrolcost.yaml", "battman_cost.yaml")]:
    raw = (SM / "packages" / src).read_text(encoding="utf-8").replace("\r\n", "\n")
    out = HEADER.format(src=f"packages/{src} v{banner(raw)}") + "\n" + gate_triggers(rename(strip_header(raw), src), src)
    write(PKG / dst, out)

# module package: only what the engine and Battman use (the rest is unused legacy, see docs/engine.md)
mod = yaml.safe_load((SM / "packages/solarsystemcontrolmodule.yaml").read_text(encoding="utf-8"))
helpers = {
    "input_boolean": {"battman_enable": {**mod["input_boolean"]["solarsystemcontrolenable"], "name": "Battman enable"},
                      "battman_no_export": {**mod["input_boolean"]["solarsystemcontrolnoexport"], "name": "Battman no export"}},
    "input_select": {"battman_mode": {**mod["input_select"]["solarsystemcontrolmode"], "name": "Battman mode"}},
    "input_number": {"battman_high_consumption": {**mod["input_number"]["solarsystemcontrolhighconsumption"],
                                                  "name": "Battman high consumption"}},
    "timer": {"battman_override_timer": {**mod["timer"]["solarsystemoverridetimer"], "name": "Battman override timer"}},
}
write(PKG / "battman_helpers.yaml",
      HEADER.format(src="packages/solarsystemcontrolmodule.yaml v1.0.14: helpers the engine uses") + "\n"
      + yaml.safe_dump(helpers, sort_keys=False, allow_unicode=True))

mod_text = (SM / "packages/solarsystemcontrolmodule.yaml").read_text(encoding="utf-8").replace("\r\n", "\n")
tpl = mod_text[mod_text.index("  - binary_sensor:"):mod_text.index("\n# Solar System Override Timer Helper")]
sensors_src = (PKG / "battman_sensors.yaml").read_text(encoding="utf-8")
sensors_src = sensors_src.split("\n\n  # ── ported from packages/solarsystemcontrolmodule")[0]   # re-runnable
assert "  - binary_sensor:" not in sensors_src
port = gate_triggers(rename(tpl, "module template blocks"), "module").rstrip() + "\n"
# the estimated-price binary sensor gets a unique ID (Smiggles' had none) so it's a proper entity
port = port.replace('      - name: "Battman estimated price"\n',
                    '      - name: "Battman estimated price"\n        unique_id: battman_estimated_price\n', 1)
assert "unique_id: battman_estimated_price" in port
write(PKG / "battman_sensors.yaml", sensors_src.rstrip() + "\n\n  # ── ported from packages/solarsystemcontrolmodule.yaml v1.0.14 ──\n" + port)


# ── blueprints ──────────────────────────────────────────────────────────────
GATE = {"condition": "state", "entity_id": "binary_sensor.battman_in_charge", "state": "on"}


class D(yaml.SafeDumper):
    pass


def _s(d, s):
    # multi-line text as a | block, kept exactly. (Lines ending in spaces can't be a block in
    # YAML, so those strings stay quoted: exact matters, the log text is compared to Smiggles'.)
    if "\n" in s and not any(x != x.rstrip() for x in s.split("\n")):
        return d.represent_scalar("tag:yaml.org,2002:str", s, style="|")
    return d.represent_scalar("tag:yaml.org,2002:str", s)


D.add_representer(str, _s)


def blueprint(domain: str, name: str, desc: str, body: dict, src: str) -> str:
    bp = {"blueprint": {"name": name, "description": desc, "domain": domain,
                        "source_url": "https://github.com/AJErazzor/battman", "input": {}}}
    text = (HEADER.format(src=src) + "\n"
            + yaml.dump(bp, Dumper=D, sort_keys=False, allow_unicode=True, width=10000)
            + yaml.dump(body, Dumper=D, sort_keys=False, allow_unicode=True, width=10000))
    return re.sub(r"BMMAPx([a-z0-9_]+)xBMMAP", r"[[map:\1]]", text)


def load(text: str):
    """Parse with [[map:x]] markers kept as plain strings (unquoted they'd read as YAML lists)."""
    return yaml.safe_load(re.sub(r"\[\[map:([a-z0-9_]+)\]\]", r"BMMAPx\1xBMMAP", text))


# The only non-rename change: Smiggles' copy-curves automation calls "notify. Notify", which
# HA rejects (not a valid action name), so that automation never loads in Smiggles.
# Battman uses a persistent notification instead (always available).
FIXES = {"SolarSystemControlCopyCurve.yaml": [("    action: notify. Notify\n", "    action: persistent_notification.create\n")]}


def automation(file: str, name: str, out: str, desc: str, gate: bool = True) -> None:
    raw = (SM / "automations" / file).read_text(encoding="utf-8").replace("\r\n", "\n")
    for old, new in FIXES.get(file, []):
        assert raw.count(old) == 1, (file, old)
        raw = raw.replace(old, new)
    a = load(rename(raw, file))
    body = {k: v for k, v in a.items() if k not in ("alias", "description", "id")}
    if gate:
        conds = body.get("conditions") or []
        body["conditions"] = [GATE, *conds]
        body = {k: body[k] for k in [*[x for x in body if x != "conditions" and x != "actions" and x not in ("mode", "variables")],
                                      "conditions", "actions", *[x for x in ("variables", "mode") if x in body]]}
    write(BP / "automation" / f"{out}.yaml",
          blueprint("automation", name, desc, body, f"automations/{file}{' ' + banner(a.get('description', '')) if banner(a.get('description', '')) != '?' else ''}"))


GATED = " Only runs while Battman is in charge (binary_sensor.battman_in_charge)."
automation("SolarSystemControl.yaml", "Battman engine – main loop", "battman_engine_loop",
           "Runs the Battman engine script when the price estimate or parameters change, while Battman enable is on." + GATED)
automation("SolarSystemControlWatchdog.yaml", "Battman engine – watchdog", "battman_engine_watchdog",
           "Forces Self Consume if the engine stops running, and clears overrides / net targets when their timer, target or reset time says so." + GATED)
automation("SolarSystemControlSigMode", "Battman engine – Sigen mode", "battman_engine_sig_mode",
           "Sets the Sigen EMS mode and limits whenever Battman mode changes." + GATED)
automation("SolarSystemControlSigCurtail.yaml", "Battman engine – curtail", "battman_engine_sig_curtail",
           "Sets the Sigen grid export limit when Battman no export changes." + GATED)
automation("SolarSystemControlSAPNOverride.yaml", "Battman engine – SAPN override", "battman_engine_sapn_override",
           "Puts the export limit back to 0 if it's raised while curtailing." + GATED)
automation("SolarSystemOverrideTimerInitialDuration.yaml", "Battman engine – override timer start", "battman_engine_timer_duration",
           "Starts the override timer at 10 minutes when it's started from idle." + GATED)
automation("SolarSystemControlCopyCurve.yaml", "Battman engine – copy curves to next month", "battman_engine_copy_curves",
           "At 8pm on the last day of the month, copies this month's SOC and price curves into next month." + GATED)

# main script
raw = (SM / "scripts/SolarSystemControl.yaml").read_text(encoding="utf-8").replace("\r\n", "\n")
s = load(rename(raw, "scripts/SolarSystemControl.yaml"))
body = {k: v for k, v in s.items() if k not in ("alias", "description")}
write(BP / "script" / "battman_engine.yaml",
      blueprint("script", "Battman engine", "The Battman engine: works out the battery mode, curtailment and limits, logs the run.",
                body, f"scripts/SolarSystemControl.yaml v{s['sequence'][1]['variables']['version']}"))

# scenes: script + armed-scene automation
raw = (SM / "packages/ssc_scenes.yaml").read_text(encoding="utf-8").replace("\r\n", "\n")
sc = load(rename(strip_header(raw), "packages/ssc_scenes.yaml"))
scr = sc["script"]["battman_apply_scene"]
write(BP / "script" / "battman_apply_scene.yaml",
      blueprint("script", "Battman apply scene", scr["description"],
                {k: v for k, v in scr.items() if k not in ("alias", "description")}, "packages/ssc_scenes.yaml v1.2.0"))
au = sc["automation"][0]
body = {k: v for k, v in au.items() if k not in ("alias", "description", "id")}
body["conditions"] = [GATE, *(body.get("conditions") or [])]
write(BP / "automation" / "battman_engine_armed_scene.yaml",
      blueprint("automation", "Battman engine – armed scene (00:01)", au["description"] + GATED, body,
                "packages/ssc_scenes.yaml v1.2.0"))
print("ported OK")
