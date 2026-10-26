"""Check the other integrations' entities Battman uses by name (Sigen, Amber, Solcast) are there,
and new enough.

Battman's engine, packages and cards name these entities directly (no entity map), so if
one is missing (integration not installed, entity disabled or renamed) a Repair names it.
An integration older than the version whose entity names Battman uses gets its own Repair.
Checked once Home Assistant has started, and again whenever the entity registry changes.
"""

from __future__ import annotations

from awesomeversion import AwesomeVersion

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.loader import IntegrationNotFound, async_get_integration

from .const import DOMAIN

ISSUE_MISSING = "missing_entities"
ISSUE_TOO_OLD = "integration_too_old"
ISSUE_OVERRIDDEN = "map_choice_ignored"

# Entity map entries Battman now uses by name: map name -> the entity it uses. A different
# entity picked for one of these on the Configure screen no longer applies, so a Repair says so.
NAMED: dict[str, str] = {
    "solcast_today": "sensor.solcast_pv_forecast_forecast_today",
    "solcast_tomorrow": "sensor.solcast_pv_forecast_forecast_tomorrow",
    "solcast_remaining_today": "sensor.solcast_pv_forecast_forecast_remaining_today",
    "ems_control_mode": "select.sigen_plant_remote_ems_control_mode",
    "pv_max_limit": "number.sigen_plant_pv_max_power_limit",
    "max_charge_limit": "number.sigen_plant_ess_max_charging_limit",
    "grid_export_limit": "number.sigen_plant_grid_export_limitation",
    "rated_charging_power": "sensor.sigen_plant_ess_rated_charging_power",
    "rated_discharging_power": "sensor.sigen_plant_ess_rated_discharging_power",
    "grid_connection_status": "sensor.sigen_plant_grid_connection_status",
    "battery_soc": "sensor.sigen_plant_battery_state_of_charge",
    "rated_energy_capacity": "sensor.sigen_plant_rated_energy_capacity",
    "total_imported_energy": "sensor.sigen_plant_total_imported_energy",
    "total_exported_energy": "sensor.sigen_plant_total_exported_energy",
    "home_power": "sensor.sigen_plant_consumed_power",
    "grid_import_power": "sensor.sigen_plant_grid_import_power",
    "grid_export_power": "sensor.sigen_plant_grid_export_power",
    "battery_power": "sensor.sigen_plant_battery_power",
    "available_max_power": "sensor.sigen_plant_available_max_active_power",
    "pv_power": "sensor.sigen_plant_pv_power",
    "sigen_pv_power": "sensor.sigen_plant_sigen_pv_power",
    "third_party_pv": "sensor.sigen_plant_third_party_pv_power",
    "pv_string": "sensor.sigen_inverter_pv{n}_power",
    "solar_today": "sensor.sigen_plant_daily_pv_energy",
    "home_today": "sensor.sigen_plant_daily_load_consumption",
    "grid_import_today": "sensor.sigen_plant_daily_grid_import_energy",
    "grid_export_today": "sensor.sigen_plant_daily_grid_export_energy",
    "buy_price": "sensor.amber_5min_current_general_price",
    "feed_in_price": "sensor.amber_5min_current_feed_in_price",
    "buy_forecast": "sensor.amber_billing_interval_forecasts_general_price",
    "feed_in_forecast": "sensor.amber_billing_interval_forecasts_feed_in_price",
    # Battman's own sensors (its packages)
    "grid_power": "sensor.battman_grid_power",
    "load_30m_avg": "sensor.battman_load_30m_avg",
}

# Entity map entries Battman no longer has (a Configure choice for one of these is just ignored):
# the inverter's own SOC (Battman uses the whole plant's) and the battery temperature.
DROPPED: set[str] = {"inverter_soc", "battery_temperature"}

SIGEN = "Sigenergy (Sigenergy-Local-Modbus)"
AMBER = "Amber (amber2mqtt, through MQTT)"

# integration domain -> (its name, the oldest version with every entity name Battman uses)
MIN_VERSIONS: dict[str, tuple[str, str]] = {
    "sigen": (SIGEN, "1.1.0"),   # 1.1.0 (Aug 2025) added Total Imported / Exported Energy and Daily Load Consumption
}

# entity -> (what Battman uses it for, the integration that provides it)
REQUIRED: dict[str, tuple[str, str]] = {
    "sensor.solcast_pv_forecast_forecast_today": ("solar forecast today", "Solcast PV Forecast"),
    "sensor.solcast_pv_forecast_forecast_tomorrow": ("solar forecast tomorrow", "Solcast PV Forecast"),
    "sensor.solcast_pv_forecast_forecast_remaining_today": ("solar still to come today", "Solcast PV Forecast"),
    # Amber: the prices and forecasts the engine decides on
    "sensor.amber_5min_current_general_price": ("the buy price now", AMBER),
    "sensor.amber_5min_current_feed_in_price": ("the feed-in price now", AMBER),
    "sensor.amber_billing_interval_forecasts_general_price": ("the buy price forecast", AMBER),
    "sensor.amber_billing_interval_forecasts_feed_in_price": ("the feed-in price forecast", AMBER),
    # Sigen: the engine and its automations (they control the battery)
    "select.sigen_plant_remote_ems_control_mode": ("the inverter's mode, set by the engine", SIGEN),
    "number.sigen_plant_pv_max_power_limit": ("the PV limit, set by the engine", SIGEN),
    "number.sigen_plant_ess_max_charging_limit": ("the charging limit, set by the engine", SIGEN),
    "number.sigen_plant_grid_export_limitation": ("the export limit, set by the engine", SIGEN),
    "sensor.sigen_plant_ess_rated_charging_power": ("the battery's rated charging power", SIGEN),
    "sensor.sigen_plant_ess_rated_discharging_power": ("the battery's rated discharging power", SIGEN),
    "sensor.sigen_plant_grid_connection_status": ("on or off grid", SIGEN),
    "sensor.sigen_plant_battery_state_of_charge": ("the battery's charge (SOC)", SIGEN),
    "sensor.sigen_plant_rated_energy_capacity": ("the battery's capacity", SIGEN),
    # Sigen: the cost totals and Battman's own sensors are built on these
    "sensor.sigen_plant_total_imported_energy": ("grid energy bought, for the cost totals", SIGEN),
    "sensor.sigen_plant_total_exported_energy": ("grid energy sold, for the cost totals", SIGEN),
    "sensor.sigen_plant_consumed_power": ("the house load, for the 30-minute load average", SIGEN),
    "sensor.sigen_plant_grid_import_power": ("grid import, for Battman's grid power", SIGEN),
    "sensor.sigen_plant_grid_export_power": ("grid export, for Battman's grid power", SIGEN),
    # Sigen: shown on the cards
    "sensor.sigen_plant_battery_power": ("battery power, on the cards", SIGEN),
    "sensor.sigen_plant_available_max_active_power": ("available power, on the Overrides card", SIGEN),
    "sensor.sigen_plant_pv_power": ("solar power, on the cards", SIGEN),
    "sensor.sigen_plant_daily_pv_energy": ("solar today, on the House card", SIGEN),
    "sensor.sigen_plant_daily_load_consumption": ("house use today, on the House card", SIGEN),
    "sensor.sigen_plant_daily_grid_import_energy": ("grid bought today, on the Cost chart", SIGEN),
    "sensor.sigen_plant_daily_grid_export_energy": ("grid sold today, on the Cost chart", SIGEN),
}


def missing(hass: HomeAssistant) -> dict[str, str]:
    """entity -> 'not found' / 'disabled', for each required entity that isn't usable."""
    reg = er.async_get(hass)
    out: dict[str, str] = {}
    for entity_id in REQUIRED:
        entry = reg.async_get(entity_id)
        if entry is not None and entry.disabled_by is not None:
            out[entity_id] = "disabled"
        elif entry is None and hass.states.get(entity_id) is None:
            out[entity_id] = "not found"
    return out


@callback
def async_check(hass: HomeAssistant) -> dict[str, str]:
    """Raise (or clear) the missing-entities Repair. Returns what's missing."""
    gone = missing(hass)
    if gone:
        ir.async_create_issue(
            hass, DOMAIN, ISSUE_MISSING, is_fixable=False, severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_MISSING,
            translation_placeholders={"missing": "\n".join(
                f"- `{e}` ({REQUIRED[e][0]}, from {REQUIRED[e][1]}): {why}" for e, why in gone.items())},
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_MISSING)
    return gone


async def async_check_versions(hass: HomeAssistant) -> dict[str, tuple[str, str]]:
    """Raise (or clear) the too-old Repair. Returns name -> (installed, needed), for each one too old."""
    old: dict[str, tuple[str, str]] = {}
    for domain, (name, minimum) in MIN_VERSIONS.items():
        if not hass.config_entries.async_entries(domain):
            continue                      # not installed: the missing-entities Repair says so
        try:
            version = (await async_get_integration(hass, domain)).version
        except IntegrationNotFound:
            continue
        if version is None or AwesomeVersion(str(version)) < AwesomeVersion(minimum):
            old[name] = (str(version or "unknown"), minimum)
    if old:
        ir.async_create_issue(
            hass, DOMAIN, ISSUE_TOO_OLD, is_fixable=False, severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_TOO_OLD,
            translation_placeholders={"old": "\n".join(
                f"- **{name}**: version {have} installed, Battman needs {need} or newer"
                for name, (have, need) in old.items())},
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_TOO_OLD)
    return old


@callback
def async_check_choices(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, str]:
    """Raise (or clear) the Repair for Configure choices Battman no longer uses. Returns map name -> your choice."""
    ignored = {k: v for k, v in entry.options.items() if v and (k in DROPPED or (k in NAMED and v != NAMED[k]))}
    if ignored:
        ir.async_create_issue(
            hass, DOMAIN, ISSUE_OVERRIDDEN, is_fixable=False, severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_OVERRIDDEN,
            translation_placeholders={"choices": "\n".join(
                f"- {k}: you picked `{v}`; " + (f"Battman now uses `{NAMED[k]}`" if k in NAMED else "Battman no longer uses this")
                for k, v in ignored.items())},
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_OVERRIDDEN)
    return ignored


@callback
def async_start(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Check once HA has started (other integrations are loaded by then), and on registry changes."""

    @callback
    def _check(_event: Event | None = None) -> None:
        async_check(hass)
        async_check_choices(hass, entry)
        hass.async_create_task(async_check_versions(hass))

    if hass.state is CoreState.running:
        _check()
    else:
        entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _check))
    entry.async_on_unload(hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, _check))

    async def _options_saved(_hass: HomeAssistant, _entry: ConfigEntry) -> None:
        async_check_choices(hass, entry)

    entry.async_on_unload(entry.add_update_listener(_options_saved))
