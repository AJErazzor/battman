"""Battman: home battery automation for Home Assistant."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, Event, HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from . import (
    blueprint_install,
    cards,
    dependencies,
    engine,
    engine_log,
    migrate,
    package_files,
    required_entities,
    themes,
    uninstall,
    update_check,
)
from .api import (
    BattmanCardsView,
    BattmanCardView,
    BattmanEntityMapView,
    BattmanImagesView,
    BattmanImageView,
    BattmanThemeSaveView,
)
from .const import DOMAIN, STATIC_URL
from .services import (
    async_create_dashboard_and_report,
    async_create_live_activity_and_report,
    async_register_services,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["binary_sensor", "button", "number", "select", "sensor", "switch", "text"]

# Set in the config entry once the install-time dashboard has been made, so it
# only ever happens once. After that, use the button or battman.create_dashboard.
DASHBOARD_DONE = "dashboard_created_on_install"
# Same idea for the Live Activity automations/script (button: Create Live Activity automations).
LIVE_ACTIVITY_DONE = "live_activity_created_on_install"
# And the engine automations/scripts (they do nothing until you migrate). Migrate makes any missing.
ENGINE_DONE = "engine_created_on_install"

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

# Pages and scripts shipped inside the integration, served at STATIC_URL.
WWW_DIR = Path(__file__).parent / "www"

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Once per HA start: serve Battman's pages and its entity-map API."""
    integration = await async_get_integration(hass, DOMAIN)
    # cache_headers=False: browsers re-check files, so a new release shows up
    # without ?v= tricks on the URL.
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, str(WWW_DIR), cache_headers=False)]
    )
    hass.http.register_view(BattmanEntityMapView(str(integration.version)))
    hass.http.register_view(BattmanThemeSaveView())
    hass.http.register_view(BattmanCardsView())
    hass.http.register_view(BattmanCardView())
    hass.http.register_view(BattmanImagesView())
    hass.http.register_view(BattmanImageView())
    hass.http.register_view(engine_log.BattmanLogView())
    # <battman-countdown>: the 5-minute Amber countdown some Battman cards show.
    frontend.add_extra_js_url(hass, f"{STATIC_URL}/battman-countdown.js?v={integration.version}")
    # Battman's card library (window.BattmanLib): the Overrides card's rows and popups.
    # Loaded on every HA page so it's there before the first tap.
    frontend.add_extra_js_url(hass, f"{STATIC_URL}/battman-lib.js?v={integration.version}")
    # The engine log renderer: the Engine log popup and the Log page draw the log with it.
    frontend.add_extra_js_url(hass, f"{STATIC_URL}/battman-enginelog.js?v={integration.version}")
    # The Battman House card (custom:battman-house): the house picture with live numbers on it.
    frontend.add_extra_js_url(hass, f"{STATIC_URL}/battman-house.js?v={integration.version}")
    # The Battman cards that draw themselves (www/battman-card-base.js is what they share): Log,
    # Cost compare, Cost chart, Settings, Theme studio.
    for name in ("log", "cost-compare", "cost-chart", "settings", "theme-studio", "curvy", "pricy"):
        frontend.add_extra_js_url(hass, f"{STATIC_URL}/battman-{name}.js?v={integration.version}")
    # Battman cards (custom:battman-<id>), in HA's card picker. The card names known at
    # start are passed along so the cards exist before any dashboard draws them.
    local = cards.local_dir(hass)
    card_list = await hass.async_add_executor_job(cards.list_cards, local)
    cards.update_issue(hass, [c["id"] for c in card_list if c["source"] != "battman"])
    ids = ",".join(c["id"] for c in card_list)
    frontend.add_extra_js_url(hass, f"{STATIC_URL}/battman-cards.js?v={integration.version}&cards={ids}")
    async_register_services(hass)
    # "Battman updated, restart to finish" Repair, checked every few minutes
    update_check.async_start(hass, str(integration.version))
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Battman from a config entry."""
    dst = themes.dst_dir(hass)
    try:
        if await hass.async_add_executor_job(themes.install, dst):
            _LOGGER.info("Battman themes installed/updated in %s", dst)
            await themes.async_reload(hass)
    except OSError as err:
        _LOGGER.error("Could not install Battman themes into %s: %s", dst, err)
    await themes.async_check(hass)

    async def _themes_reloaded(_event: Event) -> None:
        await themes.async_check(hass)

    entry.async_on_unload(hass.bus.async_listen("themes_updated", _themes_reloaded))

    await blueprint_install.async_install(hass)

    await dependencies.async_check(hass)
    required_entities.async_start(hass, entry)

    if not entry.data.get(DASHBOARD_DONE):
        await async_create_dashboard_and_report(hass, notify=False)
        hass.config_entries.async_update_entry(entry, data={**entry.data, DASHBOARD_DONE: True})

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Battman's template sensors: packages/battman/*.yaml, written and reloaded once HA is up
    package_files.async_start(hass, entry)
    # the engine log file (engine.log): every battman_engine_log event is a line
    entry.async_on_unload(engine_log.async_start(hass))
    # while Battman is in charge, Smiggles' automations stay off
    entry.async_on_unload(migrate.async_guard(hass, entry))

    async def _map_changed(_hass: HomeAssistant, _entry: ConfigEntry) -> None:
        # the engine blueprints carry map entries: rewrite them when the map changes
        await blueprint_install.async_install(hass)

    entry.async_on_unload(entry.add_update_listener(_map_changed))

    if not entry.data.get(LIVE_ACTIVITY_DONE):
        result = await async_create_live_activity_and_report(hass, notify=False)
        _LOGGER.info("Battman Live Activity: %s", result["message"])
        if not result["message"].startswith("Could not"):
            hass.config_entries.async_update_entry(entry, data={**entry.data, LIVE_ACTIVITY_DONE: True})

    # the engine automations/scripts (written after Live Activity's: same files, one at a time)
    if not entry.data.get(ENGINE_DONE):
        try:
            await engine.async_write_missing(hass)
        except engine.EngineError as err:
            _LOGGER.error("Battman engine: %s", err)
        else:
            async def _check(*_args) -> None:
                try:
                    await engine.async_reload_and_check(hass)
                except engine.EngineError as err:
                    _LOGGER.error("Battman engine: %s", err)
                    return
                hass.config_entries.async_update_entry(entry, data={**entry.data, ENGINE_DONE: True})

            if hass.state is CoreState.running:
                hass.async_create_task(_check())
            else:
                entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _check))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Battman removed: take away what it wrote into your config (see uninstall.py)."""
    await uninstall.async_remove(hass)
