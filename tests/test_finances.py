"""Finances view via the dashboard API, and the dependency check."""

import json

from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

DOMAIN = "battman"


async def _setup(hass):
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain=DOMAIN, title="Battman", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_dashboard_api_fills_the_map(hass: HomeAssistant, hass_client) -> None:
    await _setup(hass)
    client = await hass_client()
    r = await client.get("/api/battman/dashboard")
    assert r.status == 200
    data = await r.json()
    assert data["errors"] == []
    assert [v["path"] for v in data["views"]] == ["power", "finances", "correct-totals", "curvy", "pricy", "log", "settings", "theme"]
    view = data["views"][1]
    assert view["title"] == "Finances" and view["path"] == "finances"
    assert view["theme"] == "Battman Coffee"
    text = json.dumps(view)
    assert "{{" not in text                                  # every placeholder filled
    assert "sensor.solarsystemcontrolbuytotal" in text       # ...from the map
    assert "solarsystemcontrolparametersupdate" in text      # events too
    assert "--smiggles-" not in text                         # Battman colours only
    assert "/battman/cost-compare.html" in text and "/battman/images/battman-coins.webp" in text
    assert [b["entity"] for b in view["badges"]] == [
        "sensor.sigen_plant_battery_state_of_charge",
        "sensor.amber_5min_current_general_price",
        "sensor.amber_5min_current_feed_in_price",
    ]


async def test_static_files_served(hass: HomeAssistant, hass_client_no_auth) -> None:
    await _setup(hass)
    client = await hass_client_no_auth()
    for path in ("/battman/cost-compare.html", "/battman/images/finances-line.webp",
                 "/battman/log.html", "/battman/theme-studio.html", "/battman/correct-energy.html",
                 "/battman/curvy.html", "/battman/pricy.html", "/battman/images/battman-lying.webp",
                 "/battman/images/battman-money.webp", "/battman/images/soc-curve-editor-line.webp",
                 "/battman/images/price-curve-editor-line.webp",
                 "/battman/images/battman-wrench.webp", "/battman/images/settings-line.webp", "/battman/battman-lib.js",
                 "/battman/images/battman-toilet-mirror.webp", "/battman/images/logs-line.webp",
                 "/battman/images/battman-coins.webp", "/battman/battman-strategy.js",
                 "/battman/battman-cards.js"):
        r = await client.get(path)
        assert r.status == 200, path


async def test_missing_dependencies_repair(hass: HomeAssistant) -> None:
    await _setup(hass)
    issues = ir.async_get(hass)
    issue = issues.async_get_issue(DOMAIN, "missing_dependencies")
    assert issue is not None                                   # nothing installed in the test HA
    for name in ("button-card", "card-mod", "html-card", "modern-circular-gauge", "power-pie-card", "browser_mod"):
        assert name in issue.translation_placeholders["missing"]

    # install them as dashboard resources, check again -> Repair goes away
    res = hass.data[LOVELACE_DATA].resources
    await res.async_get_info()
    for url in ("/hacsfiles/button-card/button-card.js",
                "/hacsfiles/lovelace-card-mod/card-mod.js",
                "/hacsfiles/lovelace-html-card/html-card.js",
                "/hacsfiles/modern-circular-gauge/modern-circular-gauge.js",
                "/hacsfiles/power-pie-card/power-pie-card.js"):
        await res.async_create_item({"res_type": "module", "url": url})
    MockConfigEntry(domain="browser_mod", data={}).add_to_hass(hass)   # browser_mod: an integration
    from custom_components.battman import dependencies

    assert await dependencies.async_check(hass) == []
    assert issues.async_get_issue(DOMAIN, "missing_dependencies") is None
