"""Constants for Battman."""

DOMAIN = "battman"

# URL the files in custom_components/battman/www/ are served from. Not /battman: that's the
# dashboard's address, and a browser refresh on /battman/<view> must reach the dashboard.
STATIC_URL = "/battmanfiles"

# Authenticated API that hands Battman pages the entity map.
ENTITY_MAP_URL = "/api/battman/entities"

# The entity map: the Battman name a page asks for -> the entity (or event) in
# this HA. Battman pages, cards and views use only the names on the left.
ENGINE_MAP: dict[str, str] = {
    # Battman's engine: its own entities and events (packages/battman/ and the engine
    # blueprints). Before you migrate, these point at Smiggles' (SMIGGLES_NAMES below)
    # so the cards work on the engine that's in charge. Not on the Configure screen.
    "parameters": "sensor.battman_parameters",
    "run": "sensor.battman_run",
    "buy_total": "sensor.battman_buy_total",
    "sell_total": "sensor.battman_sell_total",
    "network_fee_total": "sensor.battman_network_fee",
    "estimated_price": "binary_sensor.battman_estimated_price",
    "override_timer": "timer.battman_override_timer",
    "enable": "input_boolean.battman_enable",
    "no_export": "input_boolean.battman_no_export",
    "mode": "input_select.battman_mode",
    "high_consumption": "input_number.battman_high_consumption",
    "debug_log": "sensor.battman_engine_log",
    "control_script": "script.battman_engine",
    "apply_scene_script": "script.battman_apply_scene",
    "soc_curves": "sensor.battman_soc_curves",
    "price_curves": "sensor.battman_price_curves",
    "buy_rules": "sensor.battman_buy_rules",
    "sell_rules": "sensor.battman_sell_rules",
    "power_provider_buy": "sensor.battman_power_provider_buy",
    "power_provider_sell": "sensor.battman_power_provider_sell",
    # events (not entities): cards fire these to change settings, totals, curves, rules
    "parameters_update_event": "battman_parameters_update",
    "totals_update_event": "battman_totals_update",
    "soc_curves_update_event": "battman_soc_curves_update",
    "price_curves_update_event": "battman_price_curves_update",
    "buy_rules_event": "battman_buy_rules_update",
    "sell_rules_event": "battman_sell_rules_update",
    "power_provider_event": "battman_power_provider_update",
}

# The same entries in Smiggles. Used while Smiggles is in charge (Battman not migrated
# and sensor.solarsystemcontrolparameters exists), and by Migrate / Hand back.
SMIGGLES_NAMES: dict[str, str] = {
    "parameters": "sensor.solarsystemcontrolparameters",
    "run": "sensor.solarsystemcontrolrun",
    "buy_total": "sensor.solarsystemcontrolbuytotal",
    "sell_total": "sensor.solarsystemcontrolselltotal",
    "network_fee_total": "sensor.solarsystemcontrolnetworkaccessfee",
    "estimated_price": "binary_sensor.solarsystemcontrolestimatedprice",
    "override_timer": "timer.solarsystemoverridetimer",
    "enable": "input_boolean.solarsystemcontrolenable",
    "no_export": "input_boolean.solarsystemcontrolnoexport",
    "mode": "input_select.solarsystemcontrolmode",
    "high_consumption": "input_number.solarsystemcontrolhighconsumption",
    "debug_log": "sensor.solar_system_control_debug_log",
    "control_script": "script.solarsystemcontrol",
    "apply_scene_script": "script.ssc_apply_scene",
    "soc_curves": "sensor.solar_system_control_soc_curves",
    "price_curves": "sensor.solar_system_control_price_curves",
    "buy_rules": "sensor.solarsystemcontrolbuyrules",
    "sell_rules": "sensor.solarsystemcontrolsellrules",
    "power_provider_buy": "sensor.solarsystemcontrolpowerproviderbuy",
    "power_provider_sell": "sensor.solarsystemcontrolpowerprovidersell",
    "parameters_update_event": "solarsystemcontrolparametersupdate",
    "totals_update_event": "solarsystemcontroltotalattribute",
    "soc_curves_update_event": "solar_system_control_soc_curves_update",
    "price_curves_update_event": "solar_system_control_price_curves_update",
    "buy_rules_event": "solarsystemcontrolbuyrulesattribute",
    "sell_rules_event": "solarsystemcontrolsellrulesattribute",
    "power_provider_event": "solarsystemcontrolpowerproviderupdate",
}
# Smiggles is installed if this exists (and Battman hasn't taken over).
SMIGGLES_PROBE = "sensor.solarsystemcontrolparameters"
# Config entry data: True once Migrate from Smiggles has run (until Hand back).
MIGRATED = "migrated_from_smiggles"
# Config entry data: True while Battman's engine controls the battery (binary_sensor.battman_in_charge).
IN_CHARGE = "engine_in_charge"

# Amber's entities: the only other integration's that stay on the map. You can change them on the
# Configure screen. Sigen's and Solcast's entities, and Battman's own grid power and load average
# sensors, are named directly where they're used.
OTHER_MAP_DEFAULTS: dict[str, str] = {
    "buy_price": "sensor.amber_5min_current_general_price",
    "feed_in_price": "sensor.amber_5min_current_feed_in_price",
    "buy_forecast": "sensor.amber_billing_interval_forecasts_general_price",
    "feed_in_forecast": "sensor.amber_billing_interval_forecasts_feed_in_price",
}

# Battman's own curve sensors, whichever engine is in charge: Curvy and Pricy read the factory
# curves from their `factory` attribute (Smiggles' curve sensors don't have one).
FACTORY_MAP: dict[str, str] = {
    "soc_curves_factory": "sensor.battman_soc_curves",
    "price_curves_factory": "sensor.battman_price_curves",
}

# Every map entry with its Battman default.
ENTITY_MAP_DEFAULTS: dict[str, str] = {**ENGINE_MAP, **FACTORY_MAP, **OTHER_MAP_DEFAULTS}

# Authenticated, admin-only API the theme studio uses to save your own themes.
THEMES_URL = "/api/battman/themes"

# Battman cards (custom:battman-<id>): list, and one card with the map filled in.
CARDS_URL = "/api/battman/cards"

# The Battman Image card: the list of images (authenticated), and one image by name (not
# authenticated, like /local/, because an <img> can't send a login).
IMAGES_URL = "/api/battman/images"
IMAGE_URL = "/api/battman/image"
