"""Battman: home battery automation for Home Assistant."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .api import BattmanEntityMapView
from .const import DOMAIN, STATIC_URL

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = []

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

# Pages and scripts shipped inside the integration, served at STATIC_URL.
WWW_DIR = Path(__file__).parent / "www"

# Themes shipped inside the integration, installed into <config>/themes/battman/.
THEMES_SRC = Path(__file__).parent / "themes"
THEMES_DST_PARTS = ("themes", "battman")


def _install_themes(dst: Path) -> bool:
    """Copy shipped themes into dst. Returns True if anything changed.

    dst is Battman-owned: files there that Battman no longer ships are removed.
    """
    dst.mkdir(parents=True, exist_ok=True)
    changed = False
    shipped = {f.name: f for f in THEMES_SRC.glob("*.yaml")}
    for name, src in shipped.items():
        target = dst / name
        data = src.read_bytes()
        if not target.exists() or target.read_bytes() != data:
            target.write_bytes(data)
            changed = True
    for old in dst.glob("*.yaml"):
        if old.name not in shipped:
            old.unlink()
            changed = True
    return changed


def _remove_themes(dst: Path) -> bool:
    if dst.exists():
        shutil.rmtree(dst)
        return True
    return False


async def _reload_themes(hass: HomeAssistant) -> None:
    if hass.services.has_service("frontend", "reload_themes"):
        await hass.services.async_call("frontend", "reload_themes", blocking=True)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Once per HA start: serve Battman's pages and its entity-map API."""
    integration = await async_get_integration(hass, DOMAIN)
    # cache_headers=False: browsers re-check files, so a new release shows up
    # without ?v= tricks on the URL.
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, str(WWW_DIR), cache_headers=False)]
    )
    hass.http.register_view(BattmanEntityMapView(str(integration.version)))
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Battman from a config entry."""
    dst = Path(hass.config.path(*THEMES_DST_PARTS))
    try:
        if await hass.async_add_executor_job(_install_themes, dst):
            _LOGGER.info("Battman themes installed/updated in %s", dst)
            await _reload_themes(hass)
    except OSError as err:
        _LOGGER.error("Could not install Battman themes into %s: %s", dst, err)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Battman removed: take its themes away too."""
    dst = Path(hass.config.path(*THEMES_DST_PARTS))
    if await hass.async_add_executor_job(_remove_themes, dst):
        await _reload_themes(hass)
