"""Curvy as a Battman card (custom:battman-curvy): the Curvy view places the card, and the card
wrapper passes HA's view layout on, so the frame fills a sections / panel view and resizes."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

ROOT = Path(__file__).parents[1] / "custom_components/battman"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
NODE_PATH = "/tmp/pwtest/node_modules"


async def _setup(hass):
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain="battman", title="Battman", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_curvy_card_and_view(hass: HomeAssistant, hass_client) -> None:
    await _setup(hass)
    client = await hass_client()
    cards = (await (await client.get("/api/battman/cards")).json())["cards"]
    assert {"id": "curvy", "name": "Curvy", "source": "battman"}.items() <= next(
        c for c in cards if c["id"] == "curvy").items()
    card = await (await client.get("/api/battman/cards/curvy")).json()
    assert card["config"]["type"] == "iframe" and card["config"]["url"] == "/battman/curvy.html"
    assert card["needs"] == [] and card["missing_map"] == []
    assert card["grid_options"] == {"columns": "full", "rows": 12, "min_rows": 6}
    # the page it shows is shipped with Battman
    assert (ROOT / "www/curvy.html").exists()
    # the Curvy view places the card (not the iframe directly)
    views = (await (await client.get("/api/battman/dashboard")).json())["views"]
    curvy = next(v for v in views if v["path"] == "curvy")
    assert curvy["type"] == "panel" and [c["type"] for c in curvy["cards"]] == ["custom:battman-curvy"]
    assert "iframe" not in json.dumps(curvy)


def test_curvy_card_file_header() -> None:
    text = (ROOT / "cards/curvy.yaml").read_text()
    assert text.startswith("# name: Curvy\n# description: ")
    assert yaml.safe_load(text)["type"] == "iframe"


@pytest.mark.skipif(not (Path(CHROME).exists() and Path(NODE_PATH, "playwright").exists() and shutil.which("node")),
                    reason="needs Chromium, Node and Playwright")
def test_card_wrapper_passes_layout_in_a_browser(tmp_path) -> None:
    r = subprocess.run(["node", str(Path(__file__).parent / "js/layout_check.js"), str(ROOT / "www/battman-cards.js"),
                        str(tmp_path)], capture_output=True, text=True, timeout=120,
                       env={**os.environ, "NODE_PATH": NODE_PATH, "CHROME": CHROME})
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert out["early"] == "grid"                      # set before the card was built
    assert out["later"] == ["panel", True]             # changed after
    assert out["grid"] == {"columns": "full", "rows": 12, "min_rows": 6}
    assert out["none"] is True                         # masonry: nothing passed, aspect_ratio applies
