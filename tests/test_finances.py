import pytest
"""Finances view via the dashboard API, and the dependency check."""

import json

from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from .dashboard_views import built

pytestmark = pytest.mark.usefixtures("smiggles_installed")

DOMAIN = "battman"


async def _setup(hass):
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain=DOMAIN, title="Battman", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_dashboard_views_fill_the_map(hass: HomeAssistant, hass_client) -> None:
    await _setup(hass)
    client = await hass_client()
    data = await built(hass)
    assert data["errors"] == []
    assert [v["path"] for v in data["views"]] == ["power", "curvy", "pricy", "finances", "settings", "log", "theme"]
    view = data["views"][3]
    assert view["title"] == "Finances" and view["path"] == "finances"
    assert view["theme"] == "Battman Coffee"
    text = json.dumps(view)
    assert "{{" not in text                                  # every placeholder filled
    assert "--smiggles-" not in text                         # Battman colours only
    # the Finances cards fill the map themselves (Smiggles' entities here: it's in charge)
    billing = await (await client.get("/api/battman/cards/billing")).json()
    btext = json.dumps(billing["config"])
    assert "sensor.solarsystemcontrolbuytotal" in btext and "solarsystemcontrolparametersupdate" in btext
    assert [b["entity"] for b in view["badges"]] == [
        "sensor.sigen_plant_battery_state_of_charge",
        "sensor.amber_5min_current_general_price",
        "sensor.amber_5min_current_feed_in_price",
    ]


async def test_static_files_served(hass: HomeAssistant, hass_client_no_auth) -> None:
    await _setup(hass)
    client = await hass_client_no_auth()
    for path in ("/battmanfiles/battman-cost-compare.js", "/battmanfiles/images/finances-line.webp",
                 "/battmanfiles/battman-log.js", "/battmanfiles/battman-theme-studio.js",
                 "/battmanfiles/battman-curvy.js", "/battmanfiles/battman-pricy.js", "/battmanfiles/images/battman-lying.webp",
                 "/battmanfiles/images/battman-money.webp", "/battmanfiles/images/soc-curve-editor-line.webp",
                 "/battmanfiles/images/price-curve-editor-line.webp",
                 "/battmanfiles/images/battman-wrench.webp", "/battmanfiles/images/settings-line.webp", "/battmanfiles/battman-lib.js",
                 "/battmanfiles/images/battman-toilet-mirror.webp", "/battmanfiles/images/logs-line.webp",
                 "/battmanfiles/images/battman-coins.webp", "/battmanfiles/battman-cards.js"):
        r = await client.get(path)
        assert r.status == 200, path


async def test_missing_dependencies_repair(hass: HomeAssistant) -> None:
    await _setup(hass)
    issues = ir.async_get(hass)
    issue = issues.async_get_issue(DOMAIN, "missing_dependencies")
    assert issue is not None                                   # nothing installed in the test HA
    for name in ("button-card", "card-mod", "modern-circular-gauge", "power-pie-card", "browser_mod"):
        assert name in issue.translation_placeholders["missing"]
    assert "html-card" not in issue.translation_placeholders["missing"]       # not needed since v0.18.9

    # install them as dashboard resources, check again -> Repair goes away
    res = hass.data[LOVELACE_DATA].resources
    await res.async_get_info()
    for url in ("/hacsfiles/button-card/button-card.js",
                "/hacsfiles/lovelace-card-mod/card-mod.js",
                "/hacsfiles/modern-circular-gauge/modern-circular-gauge.js",
                "/hacsfiles/power-pie-card/power-pie-card.js"):
        await res.async_create_item({"res_type": "module", "url": url})
    MockConfigEntry(domain="browser_mod", data={}).add_to_hass(hass)   # browser_mod: an integration
    from custom_components.battman import dependencies

    assert await dependencies.async_check(hass) == []
    assert issues.async_get_issue(DOMAIN, "missing_dependencies") is None
