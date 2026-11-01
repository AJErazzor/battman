"""v0.29.1: Battman's scripts are served under the version in the path, so an update refreshes
every module (and the modules they import) instead of leaving stale siblings in the browser cache.

This checks the behaviour, not the source text: what HA serves, with which cache headers, and
which script URLs it hands the frontend.
"""

import pytest
from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

DOMAIN = "battman"


async def _setup(hass: HomeAssistant) -> str:
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain=DOMAIN, title="Battman", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return str((await async_get_integration(hass, DOMAIN)).version)


async def test_modules_served_under_the_version(hass: HomeAssistant, hass_client_no_auth) -> None:
    ver = await _setup(hass)
    client = await hass_client_no_auth()
    # a card module and a sibling it imports, under the versioned folder: cached hard
    for name in ("battman-house.js", "battman-card-base.js", "battman-amber-forecast-data.js"):
        r = await client.get(f"/battmanfiles-v{ver}/{name}")
        assert r.status == 200, name
        assert "max-age" in r.headers.get("Cache-Control", ""), name
    # the unversioned folder still serves images and the fallback loader, without long caching
    r = await client.get("/battmanfiles/battman-lib.js")
    assert r.status == 200
    assert "max-age" not in r.headers.get("Cache-Control", "")


@pytest.mark.parametrize(
    "name",
    ["battman-countdown.js", "battman-lib.js", "battman-enginelog.js", "battman-house.js", "battman-log.js",
     "battman-settings.js", "battman-curvy.js", "battman-pricy.js"],
)
async def test_frontend_loads_the_versioned_urls(hass: HomeAssistant, name: str) -> None:
    ver = await _setup(hass)
    urls = list(hass.data[DATA_EXTRA_MODULE_URL].urls)
    assert f"/battmanfiles-v{ver}/{name}" in urls
    assert not any(u.startswith(f"/battmanfiles/{name}") for u in urls)
