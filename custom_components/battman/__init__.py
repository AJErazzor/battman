"""Battman: home battery automation for Home Assistant."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from . import blueprint_install, cards, dashboard, dependencies, themes, update_check
from .api import (
    BattmanCardsView,
    BattmanCardView,
    BattmanDashboardView,
    BattmanEntityMapView,
    BattmanThemeSaveView,
)
from .const import DOMAIN, STATIC_URL
from .services import (
    async_create_dashboard_and_report,
    async_create_live_activity_and_report,
    async_register_services,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["button", "number", "select", "sensor", "switch", "text"]

# Set in the config entry once the install-time dashboard has been made, so it
# only ever happens once. After that, use the button or battman.create_dashboard.
DASHBOARD_DONE = "dashboard_created_on_install"
# Same idea for the Live Activity automations/script (button: Create Live Activity automations).
LIVE_ACTIVITY_DONE = "live_activity_created_on_install"

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
    hass.http.register_view(BattmanDashboardView())
    hass.http.register_view(BattmanThemeSaveView())
    hass.http.register_view(BattmanCardsView())
    hass.http.register_view(BattmanCardView())
    # The dashboard strategy, loaded on every HA page (no Lovelace resource needed).
    frontend.add_extra_js_url(hass, f"{STATIC_URL}/battman-strategy.js?v={integration.version}")
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

    await blueprint_install.async_install(hass)

    await dependencies.async_check(hass)

    if not entry.data.get(DASHBOARD_DONE):
        await async_create_dashboard_and_report(hass, notify=False)
        hass.config_entries.async_update_entry(entry, data={**entry.data, DASHBOARD_DONE: True})

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not entry.data.get(LIVE_ACTIVITY_DONE):
        result = await async_create_live_activity_and_report(hass, notify=False)
        _LOGGER.info("Battman Live Activity: %s", result["message"])
        if not result["message"].startswith("Could not"):
            hass.config_entries.async_update_entry(entry, data={**entry.data, LIVE_ACTIVITY_DONE: True})
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Battman removed: take its shipped themes, blueprints and managed dashboards away too.

    Dashboards you've taken control of, and your own themes (themes/battman/custom/),
    are left alone.
    """
    try:
        removed = await dashboard.async_remove_managed(hass)
        if removed:
            _LOGGER.info("Removed managed Battman dashboard(s): %s", removed)
    except dashboard.DashboardUnavailable as err:
        _LOGGER.warning("Could not remove the managed Battman dashboard: %s", err)
    if await hass.async_add_executor_job(themes.remove_shipped, themes.dst_dir(hass)):
        await themes.async_reload(hass)
    await blueprint_install.async_remove(hass)
