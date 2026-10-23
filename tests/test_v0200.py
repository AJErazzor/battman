"""v0.20.0: the Log is a real card (www/battman-log.js), and Chart.js ships with Battman.

- custom:battman-log draws itself (no frame): loaded on every HA page, talks to HA through the
  hass object it's handed (no borrowed login token), reads colours straight from the theme, and
  reloads the log when the engine logs a run (no 3-second polling).
- Chart.js 4.4.0 and chartjs-plugin-datalabels 2.2.0 are in www/vendor/; nothing loads them from a CDN.
"""

import re
import subprocess
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

ROOT = Path(__file__).parents[1] / "custom_components/battman"
WWW = ROOT / "www"
JS = (WWW / "battman-log.js").read_text()


def test_log_card_is_a_real_card() -> None:
    assert subprocess.run(["node", "--check", str(WWW / "battman-log.js")]).returncode == 0
    assert 'battmanDefine("battman-log", BattmanLogCard)' in JS
    assert 'add_extra_js_url(hass, f"{STATIC_URL}/battman-log.js' in (ROOT / "__init__.py").read_text()
    assert not (WWW / "log.html").exists() and not (ROOT / "cards/log.yaml").exists()
    # HA's connection, not a token taken from the page around it, and no frame
    for gone in ("access_token", "parent.document", "frameElement", "fetch(", "haCall", "iframe"):
        assert gone not in JS, gone
    assert "callApi('GET', 'battman/log' + q)" in JS and "callApi('GET', 'battman/entities')" in JS
    # live: the engine's log event, not polling every 3 s
    assert 'const LOG_EVENT = "battman_engine_log";' in JS and "subscribeEvents(" in JS
    assert "setInterval(load" not in JS and "3000)" not in JS
    assert "setInterval(refreshChart, 60000)" in JS
    # same blocks, same per-device order key (and the one-time move from Smiggles' key)
    for block in ("controls", "log", "mode"):
        assert f'data-block="{block}"' in JS
    assert "'battman.logOrder'" in JS and "smigglesLogOrderV1" in JS


def test_log_card_on_the_log_view() -> None:
    view = (ROOT / "views/30-log.yaml").read_text()
    assert "- type: custom:battman-log" in view


def test_no_cdn_left() -> None:
    for f in [*WWW.glob("*.html"), *WWW.glob("*.js"), *(ROOT / "cards").glob("*.yaml")]:
        text = f.read_text()
        assert "cdnjs.cloudflare.com" not in text and "cdn.jsdelivr.net" not in text, f.name
    for page in ("curvy.html", "pricy.html", "cost-chart.html", "cost-compare.html"):
        assert '<script src="/battmanfiles/vendor/chart.umd.min.js"></script>' in (WWW / page).read_text(), page
    assert '<script src="/battmanfiles/vendor/chartjs-plugin-datalabels.min.js"></script>' in (WWW / "cost-chart.html").read_text()
    assert "/vendor/chart.umd.min.js" in JS


def test_vendor_files_are_the_published_builds() -> None:
    chart = (WWW / "vendor/chart.umd.min.js").read_text()
    labels = (WWW / "vendor/chartjs-plugin-datalabels.min.js").read_text()
    assert chart.startswith("/*!\n * Chart.js v4.4.0") and "Released under the MIT License" in chart[:300]
    assert labels.startswith("/*!\n * chartjs-plugin-datalabels v2.2.0") and "MIT" in labels[:300]
    readme = (WWW / "vendor/README.md").read_text()
    assert "4.4.0" in readme and "2.2.0" in readme


async def test_vendor_files_served(hass: HomeAssistant, hass_client_no_auth) -> None:
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain="battman", title="Battman", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_client_no_auth()
    for path in ("vendor/chart.umd.min.js", "vendor/chartjs-plugin-datalabels.min.js", "battman-log.js"):
        r = await client.get(f"/battmanfiles/{path}")
        assert r.status == 200, path


def test_picker_shows_the_preview_picture() -> None:
    assert (WWW / "previews/log.webp").stat().st_size > 1000
    assert re.search(r'previews/log\.webp', JS) and 'type: "battman-log", name: "Battman Log"' in JS
