"""Constants for Battman."""

DOMAIN = "battman"

# URL the files in custom_components/battman/www/ are served from.
STATIC_URL = "/battman"

# Authenticated API that hands Battman pages the entity map.
ENTITY_MAP_URL = "/api/battman/entities"

# The entity map: the Battman name a page asks for -> the entity in this HA.
# Battman pages and cards use only the names on the left.
ENTITY_MAP_DEFAULTS: dict[str, str] = {
    # Smiggles entities: Battman takes these over later, then they leave the map
    "buy_total": "sensor.solarsystemcontrolbuytotal",
    "sell_total": "sensor.solarsystemcontrolselltotal",
    "network_fee_total": "sensor.solarsystemcontrolnetworkaccessfee",
    "parameters": "sensor.solarsystemcontrolparameters",
    # Other integrations: these stay on the map
    "grid_export_today": "sensor.sigen_plant_daily_grid_export_energy",
    "grid_import_today": "sensor.sigen_plant_daily_grid_import_energy",
}
