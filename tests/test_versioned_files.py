"""v0.29.1: Battman's scripts are served under the version in the path, so an update refreshes
every module (and the modules they import) instead of leaving stale siblings in the browser cache.

This checks the behaviour, not the source text: what HA serves, with which cache headers, and
which script URLs it hands the frontend.
"""

import re
from pathlib import Path

from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

DOMAIN = "battman"
WWW = Path(__file__).parents[1] / "custom_components/battman/www"


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


async def test_frontend_loads_the_one_versioned_script(hass: HomeAssistant, hass_client_no_auth) -> None:
    """HA is handed ONE Battman script, under the version in its path; it starts the rest (www/battman.js)."""
    ver = await _setup(hass)
    urls = list(hass.data[DATA_EXTRA_MODULE_URL].urls)
    ours = [u for u in urls if "battmanfiles" in u]
    assert len(ours) == 1 and ours[0].startswith(f"/battmanfiles-v{ver}/battman.js?cards="), ours
    # every script it starts is there to fetch, under the versioned folder, cached hard
    loader = (WWW / "battman.js").read_text()
    names = re.search(r"const SCRIPTS = \[([^\]]*)\]", loader).group(1)
    names = [n.strip().strip('"') for n in names.replace("\n", " ").split(",") if n.strip()]
    assert {"countdown", "lib", "enginelog", "house", "log", "settings", "curvy", "pricy", "forecast-view"} <= set(names)
    client = await hass_client_no_auth()
    for name in ["battman", "battman-cards", *(f"battman-{n}" for n in names)]:
        r = await client.get(f"/battmanfiles-v{ver}/{name}.js")
        assert r.status == 200 and "max-age" in r.headers.get("Cache-Control", ""), name


async def test_retired_version_path_still_serves(hass: HomeAssistant, hass_client_no_auth) -> None:
    """A tab open across an update imports lazy chunks from the OLD /battmanfiles-v.../ folder.

    That version is no longer mounted, so without a fallback it 404s ("Failed to fetch
    dynamically imported module"). The fallback serves the current file for any version path.
    """
    await _setup(hass)
    client = await hass_client_no_auth()
    # a version that is NOT the running one: a stale tab's import target after an update
    r = await client.get("/battmanfiles-v0.0.1/battman-help-panel.js")
    assert r.status == 200
    assert r.content_type in ("text/javascript", "application/javascript"), r.content_type
    assert "max-age" in r.headers.get("Cache-Control", "")
    assert (await r.read()) == (WWW / "battman-help-panel.js").read_bytes()
    # a file that doesn't exist still 404s, and the version path can't escape the www dir
    assert (await client.get("/battmanfiles-v0.0.1/nope.js")).status == 404
    assert (await client.get("/battmanfiles-v0.0.1/../const.py")).status == 404
