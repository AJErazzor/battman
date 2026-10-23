"""The Battman card wrapper (battman-cards.js, custom:battman-<id> for the card files): it passes HA's
view layout on to the card it draws, the card picker draws the card itself, and Battman's files are
served from /battmanfiles so a browser refresh on /battman/<view> reaches the dashboard. Also: each
view of Battman's real cards (the ones that draw themselves) places its card."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from .dashboard_views import built

ROOT = Path(__file__).parents[1] / "custom_components/battman"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
NODE_PATH = "/tmp/pwtest/node_modules"


async def _setup(hass):
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain="battman", title="Battman", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


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
    assert out["none"] is True                         # masonry: nothing passed
    assert out["picker"] == {"img": False, "inner": True}   # picker: the card itself


VIEWS = {"curvy": "curvy", "pricy": "pricy", "log": "log", "theme": "theme-studio", "settings": "settings"}


async def test_real_cards_on_their_views(hass: HomeAssistant, hass_client) -> None:
    await _setup(hass)
    client = await hass_client()
    listed = {c["id"] for c in (await (await client.get("/api/battman/cards")).json())["cards"]}
    views = {v["path"]: v for v in (await built(hass))["views"]}
    for path, card_id in VIEWS.items():
        assert card_id not in listed, card_id                 # its own script, not a card file
        assert [c["type"] for c in views[path]["cards"]] == [f"custom:battman-{card_id}"], path
        assert views[path]["type"] == "panel", path
    assert "iframe" not in json.dumps(views)


async def test_files_are_not_at_the_dashboard_address(hass: HomeAssistant, hass_client) -> None:
    """/battman is the dashboard's address: Battman's files live at /battmanfiles."""
    from custom_components.battman.const import STATIC_URL

    await _setup(hass)
    client = await hass_client()
    assert STATIC_URL == "/battmanfiles"
    assert (await client.get("/battmanfiles/battman-cards.js")).status == 200
    old = await client.get("/battman/battman-cards.js")       # HA's own page (or 404), not Battman's file
    assert old.status != 200 or "Battman cards" not in await old.text()
    # nothing Battman ships still points at the old address
    for f in ROOT.rglob("*"):
        if f.suffix in (".yaml", ".js", ".html", ".py") and f.is_file():
            text = f.read_text(encoding="utf-8")
            assert "\"/battman/" not in text and "'/battman/" not in text and "url: /battman/" not in text, f
