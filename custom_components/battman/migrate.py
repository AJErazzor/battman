"""Migrate from Smiggles, and Hand back to Smiggles.

Only one engine ever controls the battery. Migrate:
  1. checks Battman is ready (its packages and engine automations are loaded) and
     creates any missing engine automations/scripts;
  2. turns OFF every Smiggles automation (and stops the Smiggles script), and records
     which were on, so Hand back can put them back;
  3. copies Smiggles' values into Battman's: settings, overrides, rules, curves, power
     provider, the cost odometers (state and attributes), the helpers (enable, no
     export, mode, high consumption, override timer), the engine log file, and the
     odometers' long-term statistics;
  4. turns Smiggles' enable off, then turns binary_sensor.battman_in_charge ON. The entity
     map switches the cards to Battman's entities, and the engine runs once.

Hand back does the reverse: Battman's in-charge off and its engine stopped, Battman's
values copied back into Smiggles', the recorded Smiggles automations and enable put back,
the map switched back. Battman's copies stay where they are, so you can migrate again.

Preview (dry run) shows exactly what each would do without changing anything.
"""

from __future__ import annotations

import logging
import re
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from . import engine, engine_log, package_files
from .const import ENGINE_MAP, IN_CHARGE, MIGRATED, SMIGGLES_NAMES, SMIGGLES_PROBE

_LOGGER = logging.getLogger(__name__)

# entity-map entries whose state + attributes are copied (trigger template sensors that
# keep their data in their own state/attributes)
SENSOR_KEYS = [
    "parameters", "run", "buy_rules", "sell_rules", "buy_total", "sell_total", "network_fee_total",
    "power_provider_buy", "power_provider_sell", "soc_curves", "price_curves", "debug_log",
]
# copied back on Hand back. Not the cost odometers: Smiggles' own keep counting the whole
# time (they're template sensors, not automations), so they're already up to date.
HAND_BACK_SENSOR_KEYS = [k for k in SENSOR_KEYS if k not in ("buy_total", "sell_total", "network_fee_total")]
HELPER_KEYS = ["enable", "no_export", "mode", "high_consumption", "override_timer"]
STATISTICS_KEYS = ["buy_total", "sell_total", "network_fee_total"]
# attributes that describe the entity rather than hold its data: the target keeps its own
OWN_ATTRS = {"friendly_name", "icon", "unit_of_measurement", "device_class", "state_class"}

# After copying a sensor's state in, each sensor is "nudged" with its own update event
# carrying no change: it re-renders from the copied values (`this`) and writes them as its
# own. Without that the copy is only in the state machine and a restart would bring back
# the sensor's old value. (Battman event, Smiggles event)
NUDGE_EVENTS = [
    ("battman_parameters_update", "solarsystemcontrolparametersupdate"),
    ("battman_run_update", "solarsystemcontrolrunupdate"),
    ("battman_buy_rules_update", "solarsystemcontrolbuyrulesattribute"),
    ("battman_sell_rules_update", "solarsystemcontrolsellrulesattribute"),
    ("battman_totals_update", "solarsystemcontroltotalattribute"),
    ("battman_power_provider_update", "solarsystemcontrolpowerproviderupdate"),
    ("battman_soc_curves_update", "solar_system_control_soc_curves_update"),
    ("battman_price_curves_update", "solar_system_control_price_curves_update"),
]
NUDGE = {"action": "BattmanMigrate", "attribute": "BattmanMigrate"}

SMIGGLES_AUTOMATION = re.compile(r"(?i)solar ?system|smiggles|^ssc[ _]")
WAS_ON = "smiggles_automations_were_on"
ENABLE_WAS = "smiggles_enable_was"


class MigrateError(HomeAssistantError):
    """Migrate / Hand back can't go ahead; the message says why."""


def smiggles_automations(hass: HomeAssistant) -> list[State]:
    """Every automation that belongs to Smiggles (by entity ID or name), Battman's excluded."""
    out = []
    for st in hass.states.async_all("automation"):
        object_id = st.entity_id.split(".", 1)[1]
        if object_id.startswith("battman"):
            continue
        name = str(st.attributes.get("friendly_name", ""))
        if SMIGGLES_AUTOMATION.search(object_id) or SMIGGLES_AUTOMATION.search(name):
            out.append(st)
    return sorted(out, key=lambda s: s.entity_id)


def _pairs(keys: list[str], reverse: bool = False) -> list[tuple[str, str, str]]:
    """(key, from entity, to entity)."""
    return [(k, ENGINE_MAP[k], SMIGGLES_NAMES[k]) if reverse else (k, SMIGGLES_NAMES[k], ENGINE_MAP[k]) for k in keys]


def _short(st: State | None) -> str:
    if st is None:
        return "missing"
    s = st.state if len(st.state) <= 40 else st.state[:37] + "..."
    return f"{s} (+{len(st.attributes)} attributes)" if st.attributes else s


def preview(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """What Migrate would do, and anything stopping it. Changes nothing."""
    problems: list[str] = []
    if entry.data.get(MIGRATED):
        problems.append("Already migrated: Battman is in charge. Use Hand back first to go back to Smiggles.")
    if hass.states.get(SMIGGLES_PROBE) is None:
        problems.append(f"Smiggles not found ({SMIGGLES_PROBE} doesn't exist).")
    reg_missing = []
    for _key, _src, dst in _pairs(SENSOR_KEYS) + _pairs(HELPER_KEYS):
        if hass.states.get(dst) is None:
            reg_missing.append(dst)
    if reg_missing:
        problems.append(
            "Battman's engine entities aren't loaded (is packages/battman/ being read? see Repairs): "
            + ", ".join(reg_missing)
        )
    autos = smiggles_automations(hass)
    return {
        "can_migrate": not problems,
        "problems": problems,
        "turn_off": [
            {"entity_id": a.entity_id, "name": a.attributes.get("friendly_name"), "state": a.state} for a in autos
        ],
        "stop_script": SMIGGLES_NAMES["control_script"],
        "engine_items_to_create": engine.missing(hass),
        "copy": [
            {"from": src, "to": dst, "value": _short(hass.states.get(src))}
            for _k, src, dst in _pairs(SENSOR_KEYS) + _pairs(HELPER_KEYS)
        ],
        "statistics": [{"from": src, "to": dst} for _k, src, dst in _pairs(STATISTICS_KEYS)],
        "log_file": {
            "from": str(engine_log.smiggles_path(hass)),
            "to": str(engine_log.battman_path(hass)),
            "exists": engine_log.smiggles_path(hass).exists(),
        },
        "then": "Smiggles enable off; binary_sensor.battman_in_charge on; cards switch to Battman's entities; the engine runs once.",
    }


async def _copy_sensor(hass: HomeAssistant, src: str, dst: str) -> str:
    st = hass.states.get(src)
    if st is None:
        return f"{src}: missing, not copied"
    own = hass.states.get(dst)
    attrs = {k: v for k, v in st.attributes.items() if k not in OWN_ATTRS}
    if own is not None:
        attrs.update({k: v for k, v in own.attributes.items() if k in OWN_ATTRS})
    hass.states.async_set(dst, st.state, attrs, force_update=True)
    return f"{src} → {dst}"


def _timer_remaining(st: State) -> timedelta | None:
    if st.state == "active" and (fin := st.attributes.get("finishes_at")):
        end = dt_util.parse_datetime(str(fin))
        if end is not None:
            return end - dt_util.utcnow()
    if st.state == "paused" and (rem := st.attributes.get("remaining")):
        return dt_util.parse_duration(str(rem))
    return None


async def _copy_helper(hass: HomeAssistant, key: str, src: str, dst: str) -> str:
    st = hass.states.get(src)
    if st is None or st.state in ("unknown", "unavailable"):
        return f"{src}: {'missing' if st is None else st.state}, not copied"
    call = hass.services.async_call
    domain = dst.split(".", 1)[0]
    if domain == "input_boolean":
        await call("input_boolean", "turn_on" if st.state == "on" else "turn_off", {"entity_id": dst}, blocking=True)
    elif domain == "input_select":
        await call("input_select", "select_option", {"entity_id": dst, "option": st.state}, blocking=True)
    elif domain == "input_number":
        await call("input_number", "set_value", {"entity_id": dst, "value": float(st.state)}, blocking=True)
    elif domain == "timer":
        await call("timer", "cancel", {"entity_id": dst}, blocking=True)
        left = _timer_remaining(st)
        if left is not None and left.total_seconds() >= 1:
            secs = int(left.total_seconds())
            dur = f"{secs // 3600}:{secs % 3600 // 60:02d}:{secs % 60:02d}"
            await call("timer", "start", {"entity_id": dst, "duration": dur}, blocking=True)
            if st.state == "paused":
                await call("timer", "pause", {"entity_id": dst}, blocking=True)
            return f"{src} → {dst} ({st.state}, {dur} left)"
    return f"{src} → {dst} ({st.state})"


async def _copy_statistics(hass: HomeAssistant, src: str, dst: str) -> str:
    """Copy src's hourly long-term statistics to dst, up to the last full hour.

    The sums are shifted so the last copied hour ends at 0: Battman's sensor starts its
    own sum from 0 when it starts recording, so the changes (what graphs show) carry on
    without a jump. The part-hour before migration isn't in any hourly row and isn't copied.
    """
    try:
        from homeassistant.components.recorder import get_instance  # noqa: PLC0415
        from homeassistant.components.recorder.statistics import (  # noqa: PLC0415
            async_import_statistics,
            get_metadata,
            statistics_during_period,
        )
    except ImportError:
        return f"{src}: recorder not available, statistics not copied"
    if "recorder" not in hass.config.components:
        return f"{src}: recorder not running, statistics not copied"
    rec = get_instance(hass)
    meta = await rec.async_add_executor_job(lambda: get_metadata(hass, statistic_ids={src, dst}))
    if src not in meta:
        return f"{src}: no long-term statistics to copy"
    if dst in meta:
        return f"{dst}: already has statistics, not copied (so nothing is doubled)"
    end = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)
    rows = await rec.async_add_executor_job(
        statistics_during_period, hass, dt_util.utc_from_timestamp(0), end, {src}, "hour", None, {"state", "sum"}
    )
    rows = rows.get(src, [])
    if not rows:
        return f"{src}: no hourly statistics to copy"
    last_sum = rows[-1].get("sum") or 0.0
    data = []
    for r in rows:
        item: dict[str, Any] = {"start": dt_util.utc_from_timestamp(r["start"])}
        if r.get("state") is not None:
            item["state"] = r["state"]
        if r.get("sum") is not None:
            item["sum"] = r["sum"] - last_sum
        data.append(item)
    new_meta = {k: v for k, v in meta[src][1].items() if k != "has_mean"}
    new_meta.update(statistic_id=dst, source="recorder", name=None)
    async_import_statistics(hass, new_meta, data)
    return f"{src} → {dst}: {len(data)} hours"


async def _nudge(hass: HomeAssistant, battman: bool) -> None:
    for b, sm in NUDGE_EVENTS:
        hass.bus.async_fire(b if battman else sm, dict(NUDGE))
    await hass.async_block_till_done()


async def _set_entry(hass: HomeAssistant, entry: ConfigEntry, **data: Any) -> None:
    hass.config_entries.async_update_entry(entry, data={**entry.data, **data})


async def async_migrate(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    plan = preview(hass, entry)
    if not plan["can_migrate"]:
        raise MigrateError("Migrate can't go ahead: " + " ".join(plan["problems"]))
    report: dict[str, Any] = {"created": [], "turned_off": [], "copied": [], "statistics": [], "log": ""}

    # 1. Battman's engine exists (gated: does nothing yet)
    try:
        report["created"] = await engine.async_create_missing(hass)
    except engine.EngineError as err:
        raise MigrateError(str(err)) from err
    missing = await package_files.async_sync(hass)
    if missing:
        raise MigrateError("Battman's packages aren't loaded: " + ", ".join(missing))

    # 2. Smiggles stops: every automation off, its script stopped
    was_on = [a.entity_id for a in smiggles_automations(hass) if a.state == "on"]
    if was_on:
        await hass.services.async_call(
            "automation", "turn_off", {"entity_id": was_on, "stop_actions": True}, blocking=True
        )
    report["turned_off"] = was_on
    if hass.states.get(SMIGGLES_NAMES["control_script"]) is not None:
        await hass.services.async_call(
            "script", "turn_off", {"entity_id": SMIGGLES_NAMES["control_script"]}, blocking=True
        )
    enable_was = (hass.states.get(SMIGGLES_NAMES["enable"]) or State("x.x", "off")).state
    await _set_entry(hass, entry, **{WAS_ON: was_on, ENABLE_WAS: enable_was})

    # 3. copy everything across
    for _k, src, dst in _pairs(SENSOR_KEYS):
        report["copied"].append(await _copy_sensor(hass, src, dst))
    for k, src, dst in _pairs(HELPER_KEYS):
        report["copied"].append(await _copy_helper(hass, k, src, dst))
    for _k, src, dst in _pairs(STATISTICS_KEYS):
        try:
            report["statistics"].append(await _copy_statistics(hass, src, dst))
        except Exception as err:  # noqa: BLE001  (statistics are nice to have; never block the move)
            _LOGGER.exception("Battman couldn't copy statistics %s → %s", src, dst)
            report["statistics"].append(f"{src}: couldn't copy statistics ({err})")
    lines = await hass.async_add_executor_job(
        engine_log.copy_in, engine_log.smiggles_path(hass), engine_log.battman_path(hass)
    )
    report["log"] = f"{lines} log lines copied"

    # 4. Smiggles' enable off, Battman in charge
    if hass.states.get(SMIGGLES_NAMES["enable"]) is not None:
        await hass.services.async_call(
            "input_boolean", "turn_off", {"entity_id": SMIGGLES_NAMES["enable"]}, blocking=True
        )
    await _set_entry(hass, entry, **{MIGRATED: True, IN_CHARGE: True})
    await hass.async_block_till_done()
    await _nudge(hass, battman=True)
    await _save_now(hass)
    loop = engine.entity_ids(hass).get("battman_engine_loop")
    if loop:
        await hass.services.async_call(
            "automation", "trigger", {"entity_id": loop, "skip_condition": False}, blocking=True
        )
    _LOGGER.warning("Battman is now in charge of the battery (migrated from Smiggles)")
    return report


async def async_hand_back(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    if not entry.data.get(MIGRATED):
        raise MigrateError("Nothing to hand back: Battman isn't in charge (it was never migrated).")
    if hass.states.get(SMIGGLES_PROBE) is None:
        raise MigrateError(f"Smiggles not found ({SMIGGLES_PROBE} doesn't exist), so there's nothing to hand back to.")
    report: dict[str, Any] = {"copied": [], "turned_on": []}

    # 1. Battman stops
    await _set_entry(hass, entry, **{IN_CHARGE: False})
    for sid in engine.SCRIPTS:
        if hass.states.get(f"script.{sid}") is not None:
            await hass.services.async_call("script", "turn_off", {"entity_id": f"script.{sid}"}, blocking=True)

    # 2. Battman's values back into Smiggles'
    for _k, src, dst in _pairs(HAND_BACK_SENSOR_KEYS, reverse=True):
        report["copied"].append(await _copy_sensor(hass, src, dst))
    for k, src, dst in _pairs([k for k in HELPER_KEYS if k != "enable"], reverse=True):
        report["copied"].append(await _copy_helper(hass, k, src, dst))
    await _nudge(hass, battman=False)

    # 3. Smiggles back on, as it was
    was_on = [e for e in entry.data.get(WAS_ON, []) if hass.states.get(e) is not None]
    if was_on:
        await hass.services.async_call("automation", "turn_on", {"entity_id": was_on}, blocking=True)
    report["turned_on"] = was_on
    battman_enable = hass.states.get(ENGINE_MAP["enable"])
    enable = battman_enable.state if battman_enable is not None else entry.data.get(ENABLE_WAS, "off")
    if hass.states.get(SMIGGLES_NAMES["enable"]) is not None:
        await hass.services.async_call(
            "input_boolean", "turn_on" if enable == "on" else "turn_off",
            {"entity_id": SMIGGLES_NAMES["enable"]}, blocking=True,
        )
    report["copied"].append(f"{ENGINE_MAP['enable']} → {SMIGGLES_NAMES['enable']} ({enable})")
    await _set_entry(hass, entry, **{MIGRATED: False})
    await _save_now(hass)
    _LOGGER.warning("Battman handed the battery back to Smiggles")
    return report


async def _save_now(hass: HomeAssistant) -> None:
    """Save on/off states straight away (HA saves them every 15 minutes and at shutdown),
    so a power cut right after Migrate can't bring Smiggles' automations back on."""
    from homeassistant.helpers.restore_state import async_get as restore_data  # noqa: PLC0415

    try:
        await restore_data(hass).async_dump_states()
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Battman couldn't save automation states after migrating")


def async_guard(hass: HomeAssistant, entry: ConfigEntry):
    """While Battman is in charge, Smiggles stays off: any Smiggles automation that comes on
    (at start, by hand, or from a restore) is turned straight back off, with a notification
    saying to use Hand back instead. Returns an unsubscribe callable."""
    from homeassistant.components import persistent_notification  # noqa: PLC0415
    from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, EVENT_STATE_CHANGED  # noqa: PLC0415
    from homeassistant.core import CoreState, Event, callback  # noqa: PLC0415

    async def _enforce(entity_ids: list[str]) -> None:
        if not (entry.data.get(MIGRATED) and entry.data.get(IN_CHARGE)) or not entity_ids:
            return
        await hass.services.async_call("automation", "turn_off", {"entity_id": entity_ids, "stop_actions": True},
                                       blocking=True)
        _LOGGER.warning("Battman is in charge: turned Smiggles automations back off: %s", entity_ids)
        persistent_notification.async_create(
            hass,
            "Battman is in charge of the battery, so these Smiggles automations were turned back off: "
            + ", ".join(entity_ids)
            + ". To give the battery back to Smiggles, use the action battman.hand_back_to_smiggles.",
            title="Battman: Smiggles kept off",
            notification_id="battman_smiggles_kept_off",
        )

    async def _check_all(*_args) -> None:
        await _enforce([a.entity_id for a in smiggles_automations(hass) if a.state == "on"])

    @callback
    def _changed(event: Event) -> None:
        new = event.data.get("new_state")
        if new is None or new.domain != "automation" or new.state != "on":
            return
        old = event.data.get("old_state")
        if old is not None and old.state == "on":
            return
        if any(s.entity_id == new.entity_id for s in smiggles_automations(hass)):
            hass.async_create_task(_enforce([new.entity_id]))

    unsubs = [hass.bus.async_listen(EVENT_STATE_CHANGED, _changed)]
    if hass.state is CoreState.running:
        hass.async_create_task(_check_all())
    else:
        unsubs.append(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _check_all))

    def _stop() -> None:
        for u in unsubs:
            try:
                u()
            except ValueError:
                pass

    return _stop
