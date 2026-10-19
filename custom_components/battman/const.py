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
    # Other integrations: these stay on the map
    "battery_soc": "sensor.sigen_plant_battery_state_of_charge",
    "buy_price": "sensor.amber_5min_current_general_price",
    "feed_in_price": "sensor.amber_5min_current_feed_in_price",
    "grid_export_today": "sensor.sigen_plant_daily_grid_export_energy",
    "grid_import_today": "sensor.sigen_plant_daily_grid_import_energy",
    # Smiggles events (not entities): cards fire these to change settings / totals
    "parameters_update_event": "solarsystemcontrolparametersupdate",
    "totals_update_event": "solarsystemcontroltotalattribute",
}

# Authenticated API that hands the managed dashboard its views (views/*.yaml with
# {{name}} placeholders filled from the entity map).
DASHBOARD_URL = "/api/battman/dashboard"
