"""Check the other things Battman's dashboard needs are installed.

An integration can't install HACS cards for you, so Battman checks at startup and
raises a Repair naming anything missing. The full list lives in DEPENDENCIES.md.
"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

ISSUE_MISSING = "missing_dependencies"

# name -> (text found in its dashboard-resource URL, where to get it)
FRONTEND_CARDS: dict[str, tuple[str, str]] = {
    "button-card": ("button-card", "https://github.com/custom-cards/button-card"),
    "card-mod": ("card-mod", "https://github.com/thomasloven/lovelace-card-mod"),
    "html-card": ("html-card", "https://github.com/PiotrMachowski/Home-Assistant-Lovelace-HTML-card"),
}


async def _loaded_urls(hass: HomeAssistant) -> list[str]:
    urls: list[str] = []
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA  # noqa: PLC0415

        resources = hass.data[LOVELACE_DATA].resources
        await resources.async_get_info()  # makes sure storage resources are loaded
        urls += [str(item.get("url", "")) for item in resources.async_items()]
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Could not read dashboard resources: %s", err)
    try:
        from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL  # noqa: PLC0415

        urls += list(hass.data[DATA_EXTRA_MODULE_URL].urls)  # e.g. card-mod as a frontend module
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Could not read frontend modules: %s", err)
    return urls


async def async_check(hass: HomeAssistant) -> list[str]:
    """Raise (or clear) the missing-dependencies Repair. Returns the missing names."""
    urls = [u.lower() for u in await _loaded_urls(hass)]
    missing = [name for name, (needle, _) in FRONTEND_CARDS.items() if not any(needle in u for u in urls)]
    if missing:
        ir.async_create_issue(
            hass,
            DOMAIN,
            ISSUE_MISSING,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_MISSING,
            translation_placeholders={
                "missing": "\n".join(f"- **{n}**: {FRONTEND_CARDS[n][1]}" for n in missing)
            },
        )
        _LOGGER.warning("Battman is missing: %s", ", ".join(missing))
    else:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_MISSING)
    return missing
