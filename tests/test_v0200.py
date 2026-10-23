"""v0.20.0: the Log is a real card (www/battman-log.js), and Chart.js ships with Battman.

- custom:battman-log draws itself (no frame): loaded on every HA page, talks to HA through the
  hass object it's handed (no borrowed login token), reads colours straight from the theme, and
  reloads the log when the engine logs a run (no 3-second polling).
- Chart.js 4.4.0 is in www/vendor/; nothing loads it from a CDN. (The datalabels plugin shipped
  here too until v0.21.0: no card used it.)
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

ROOT = Path(__file__).parents[1] / "custom_components/battman"
WWW = ROOT / "www"
JS = (WWW / "battman-log.js").read_text()


def test_log_card_is_a_real_card() -> None:
    assert subprocess.run(["node", "--check", str(WWW / "battman-log.js")]).returncode == 0
    assert 'battmanDefine("battman-log", BattmanLogCard)' in JS
    init = (ROOT / "__init__.py").read_text()
    assert '"log", ' in init and 'add_extra_js_url(hass, f"{STATIC_URL}/battman-{name}.js' in init
    assert not (WWW / "log.html").exists() and not (ROOT / "cards/log.yaml").exists()
    # HA's connection, not a token taken from the page around it, and no frame
    for gone in ("access_token", "parent.document", "frameElement", "fetch(", "haCall", "iframe"):
        assert gone not in JS, gone
    assert "callApi('GET', 'battman/log' + q)" in JS and "await battmanMap(haObj()," in JS
    assert 'hass.callApi("GET", "battman/entities")' in (WWW / "battman-card-base.js").read_text()
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
    assert "/vendor/chart.umd.min.js" in (WWW / "battman-card-base.js").read_text()   # every chart card's loader


def test_vendor_files_are_the_published_builds() -> None:
    chart = (WWW / "vendor/chart.umd.min.js").read_text()
    assert chart.startswith("/*!\n * Chart.js v4.4.0") and "Released under the MIT License" in chart[:300]
    readme = (WWW / "vendor/README.md").read_text()
    assert "4.4.0" in readme and "datalabels" not in readme
    assert not (WWW / "vendor/chartjs-plugin-datalabels.min.js").exists()


async def test_vendor_files_served(hass: HomeAssistant, hass_client_no_auth) -> None:
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain="battman", title="Battman", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_client_no_auth()
    for path in ("vendor/chart.umd.min.js", "battman-log.js"):
        r = await client.get(f"/battmanfiles/{path}")
        assert r.status == 200, path


def test_picker_shows_the_preview_picture() -> None:
    assert (WWW / "previews/log.webp").stat().st_size > 1000
    assert 'static preview = "log.webp";' in JS and 'battmanPicker("battman-log", "Battman Log",' in JS


CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
NODE_PATH = "/tmp/pwtest/node_modules"


def test_card_wrapper_leaves_the_log_to_its_script() -> None:
    cards_js = (WWW / "battman-cards.js").read_text()
    assert 'log: "battman-log.js"' in cards_js[cards_js.index("const OWN_SCRIPT_CARDS = {"):]


@pytest.mark.skipif(not (Path(CHROME).exists() and Path(NODE_PATH, "playwright").exists() and shutil.which("node")),
                    reason="needs Playwright and Chromium")
def test_older_card_list_still_gets_the_log_card() -> None:
    """A page open since before the update (its list of card files still names "log", and it has no
    battman-log.js of its own): the Log card still comes from battman-log.js."""
    r = subprocess.run(["node", str(Path(__file__).parent / "js/stale_list_check.js"), str(WWW)],
                       capture_output=True, text=True, timeout=120,
                       env={**os.environ, "NODE_PATH": NODE_PATH, "CHROME": CHROME})
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert out == {"real": dict.fromkeys(("log", "cost-compare", "cost-chart", "settings", "theme-studio", "curvy", "pricy"),
                                         "BattmanCardBase"),
                   "log": "BattmanLogCard", "state": "BattmanCard", "logPicker": 1}
