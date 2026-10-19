"""Constants for Battman."""

DOMAIN = "battman"

# URL the files in custom_components/battman/www/ are served from.
STATIC_URL = "/battman"

# Authenticated API that hands Battman pages the entity map.
ENTITY_MAP_URL = "/api/battman/entities"

# The entity map: the Battman name a page asks for -> the entity (or event) in
# this HA. Battman pages, cards and views use only the names on the left.
ENTITY_MAP_DEFAULTS: dict[str, str] = {
    # Smiggles entities: Battman takes these over later, then they leave the map
    "buy_total": "sensor.solarsystemcontrolbuytotal",
    "sell_total": "sensor.solarsystemcontrolselltotal",
    "network_fee_total": "sensor.solarsystemcontrolnetworkaccessfee",
    "parameters": "sensor.solarsystemcontrolparameters",
    "run": "sensor.solarsystemcontrolrun",
    "estimated_price": "binary_sensor.solarsystemcontrolestimatedprice",
    "override_timer": "timer.solarsystemoverridetimer",
    # Other integrations: these stay on the map
    "battery_soc": "sensor.sigen_plant_battery_state_of_charge",
    "buy_price": "sensor.amber_5min_current_general_price",
    "feed_in_price": "sensor.amber_5min_current_feed_in_price",
    "grid_export_today": "sensor.sigen_plant_daily_grid_export_energy",
    "grid_import_today": "sensor.sigen_plant_daily_grid_import_energy",
    "pv_power": "sensor.sigen_plant_pv_power",
    "home_power": "sensor.sigen_plant_consumed_power",
    "battery_power": "sensor.sigen_plant_battery_power",
    "third_party_pv": "sensor.sigen_plant_third_party_pv_power",
    # pattern: {n} = string number 1..12; the Log page shows the ones that exist
    "pv_string": "sensor.sigen_inverter_pv{n}_power",
    # Smiggles log helpers (Battman takes these over with the log engine)
    "mode": "input_select.solarsystemcontrolmode",
    "debug_log_start": "input_datetime.solarsystemcontroldebuglogstart",
    "debug_log_end": "input_datetime.solarsystemcontroldebuglogend",
    "load_debug_log_script": "script.solarsystemcontrolloadfilteredsolarlog",
    "load_30m": "sensor.solarsystemcontrolload30m",
    "grid_power": "sensor.gridpower",
    # not an entity: the URL of the filtered log file the Log page reads
    "debug_log_file": "/local/smiggles/solar_debug_filtered.txt",
    # Smiggles events (not entities): cards fire these to change settings / totals
    "parameters_update_event": "solarsystemcontrolparametersupdate",
    "totals_update_event": "solarsystemcontroltotalattribute",
    # Curvy (SOC curves) and Pricy (price curves): Smiggles curve stores, their
    # events, and the Smiggles control script the editors can run
    "soc_curves": "sensor.solar_system_control_soc_curves",
    "price_curves": "sensor.solar_system_control_price_curves",
    "soc_curves_update_event": "solar_system_control_soc_curves_update",
    "price_curves_update_event": "solar_system_control_price_curves_update",
    "control_script": "script.solarsystemcontrol",
    "load_30m_avg": "sensor.solarsystemcontrolload30mavg",
    "high_consumption": "input_number.solarsystemcontrolhighconsumption",
    # Settings: rules, power provider, and the events their cards fire
    "buy_rules": "sensor.solarsystemcontrolbuyrules",
    "sell_rules": "sensor.solarsystemcontrolsellrules",
    "buy_rules_event": "solarsystemcontrolbuyrulesattribute",
    "sell_rules_event": "solarsystemcontrolsellrulesattribute",
    "power_provider_buy": "sensor.solarsystemcontrolpowerproviderbuy",
    "power_provider_sell": "sensor.solarsystemcontrolpowerprovidersell",
    "power_provider_event": "solarsystemcontrolpowerproviderupdate",
    # Power view: Sigen limits (Limits card)
    "grid_export_limit": "number.sigen_plant_grid_export_limitation",
    "pv_max_limit": "number.sigen_plant_pv_max_power_limit",
    "max_charge_limit": "number.sigen_plant_ess_max_charging_limit",
    # Other integrations used by Curvy / Pricy
    # Sigen inverter solar only (pv_power is Sigen + third-party)
    "sigen_pv_power": "sensor.sigen_plant_sigen_pv_power",
    "solcast_today": "sensor.solcast_pv_forecast_forecast_today",
    "solcast_tomorrow": "sensor.solcast_pv_forecast_forecast_tomorrow",
    "battery_capacity": "sensor.sigen_inverter_rated_battery_capacity",
    "buy_forecast": "sensor.amber_billing_interval_forecasts_general_price",
    "feed_in_forecast": "sensor.amber_billing_interval_forecasts_feed_in_price",
}

# Entries that aren't entities (the Configure screen shows a text box for these).
MAP_TEXT_ENTRIES = {
    "pv_string",
    "debug_log_file",
    "parameters_update_event",
    "totals_update_event",
    "soc_curves_update_event",
    "price_curves_update_event",
    "buy_rules_event",
    "sell_rules_event",
    "power_provider_event",
}

# Authenticated, admin-only API the theme studio uses to save your own themes.
THEMES_URL = "/api/battman/themes"

# Battman cards (custom:battman-<id>): list, and one card with the map filled in.
CARDS_URL = "/api/battman/cards"

# Authenticated API that hands the managed dashboard its views (views/*.yaml with
# {{name}} placeholders filled from the entity map).
DASHBOARD_URL = "/api/battman/dashboard"
