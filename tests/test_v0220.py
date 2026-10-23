"""v0.22.0: Curvy and Pricy are real cards, so no Battman card shows a page in a frame any more.

- Each draws itself (www/battman-curvy.js, www/battman-pricy.js, loaded on every HA page): no
  page in a frame, no login token taken from the page around it. The old pages and card files
  are gone, and with them the card files' picture support (# preview:), which only they used.
- What the two editors share is in battman-curve-editor.js: the button wiring (data-on-click=...),
  the save check, the debug box, the preset menus, the press feedback and the notes.
- Pricy no longer draws a made-up Amber curve when Amber has no prices: the overlay is empty and
  a note says so.
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
CARDS = {"curvy": "BattmanCurvyCard", "pricy": "BattmanPricyCard"}
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
NODE_PATH = "/tmp/pwtest/node_modules"


def test_each_card_is_a_real_card() -> None:
    init = (ROOT / "__init__.py").read_text()
    loaded = re.search(r'for name in \(([^)]*)\):\n\s+frontend\.add_extra_js_url', init).group(1)
    wrapper = (WWW / "battman-cards.js").read_text()
    own = wrapper[wrapper.index("const OWN_SCRIPT_CARDS = {"):]
    own = own[:own.index("};")]
    for cid, cls in CARDS.items():
        f = WWW / f"battman-{cid}.js"
        assert subprocess.run(["node", "--check", str(f)]).returncode == 0, cid
        js = f.read_text()
        assert f'battmanDefine("battman-{cid}", {cls})' in js and f"class {cls} extends BattmanCardBase" in js, cid
        assert f'static preview = "{cid}.webp";' in js and (WWW / f"previews/{cid}.webp").stat().st_size > 1000, cid
        assert f'battmanPicker("battman-{cid}",' in js and f'"{cid}"' in loaded and f'{cid}: "battman-{cid}.js"' in own, cid
        for gone in ("access_token", "parent.document", "frameElement", "window.parent", "fetch(", "iframe",
                     "document.getElementById", "document.querySelector", "document.documentElement",
                     ' onclick="', ' oninput="', ' onchange="', ' onmouseenter="', "event.target.classList"):
            assert gone not in js, (cid, gone)
        # every button the markup wires has its handler, and nothing else is wired
        named = set(re.findall(r'data-on-(?:click|change|input|mouseenter|mouseleave)="(\w+)\(', js))
        wired = set(re.search(r"wireHandlers\(root, \{ ([^}]*) \}\);", js).group(1).split(", "))
        assert named == wired, (cid, named ^ wired)
        # the Manage Presets window covers the screen: it sits outside the card (a size container)
        assert "</div></ha-card>\n<!-- Manage Presets Modal -->" in js, cid
    for page in CARDS:
        assert not (WWW / f"{page}.html").exists() and not (ROOT / f"cards/{page}.yaml").exists(), page


def test_no_framed_pages_left() -> None:
    assert not list(WWW.glob("*.html"))
    for f in (ROOT / "cards").glob("*.yaml"):
        text = f.read_text()
        assert "type: iframe" not in text and "# preview:" not in text, f.name
    cards_py = (ROOT / "cards.py").read_text()
    assert "preview" not in cards_py and "STATIC_URL" not in cards_py
    wrapper = (WWW / "battman-cards.js").read_text()
    assert "_showPreview" not in wrapper and "data.preview" not in wrapper and "this._data" not in wrapper


def test_shared_curve_editor_module() -> None:
    shared = (WWW / "battman-curve-editor.js").read_text()
    for name in ("wireHandlers", "savedIn", "debugBox", "presetMenus", "pressFeedback", "showNote", "hourLabel", "NOT_SAVED"):
        assert re.search(rf"^export (async )?(function |const ){name}\b", shared, re.M), name
    for cid in CARDS:
        js = (WWW / f"battman-{cid}.js").read_text()
        assert 'from "./battman-curve-editor.js"' in js, cid
        for gone in ("function sameData(", "function savedIn(", "function debugLog(", "function togglePresetMenu(",
                     "function fireHaptic("):
            assert gone not in js, (cid, gone)
    # HA's haptic event, on HA's own window (the page used to send it to the page around its frame)
    assert 'window.dispatchEvent(new CustomEvent("haptic", { detail: "selection" }))' in shared


def test_saved_in_waits_for_the_sensor() -> None:
    url = (WWW / "battman-curve-editor.js").as_uri()
    code = f"""
import {{ savedIn }} from "{url}";
const states = {{ "sensor.c": {{ attributes: {{ curves: {{ jan: [1, 2] }} }} }} }};
const hass = () => ({{ states }});
const yes = await savedIn(hass, "sensor.c", "curves", {{ jan: [1, 2.0000000001] }}, 300);
const no = await savedIn(hass, "sensor.c", "curves", {{ jan: [1, 3] }}, 300);
process.stdout.write(JSON.stringify([yes, no]));
"""
    r = subprocess.run(["node", "--input-type=module", "-e", code], capture_output=True, text=True, check=True)
    assert json.loads(r.stdout) == [True, False]


def test_pricy_draws_no_made_up_amber_prices() -> None:
    js = (WWW / "battman-pricy.js").read_text()
    assert "AMBER_SIM" not in js and "sim fallback" not in js
    assert "let AMBER_FIT = Array(24).fill(null);" in js and "let AMBER_BUY = Array(24).fill(null);" in js
    assert "showNote('No Amber prices for today" in js and "showNote('Amber prices unavailable (" in js


@pytest.mark.skipif(not (Path(CHROME).exists() and Path(NODE_PATH, "playwright").exists() and shutil.which("node")),
                    reason="needs Playwright and Chromium")
def test_buttons_reach_their_handlers_in_a_browser() -> None:
    r = subprocess.run(["node", str(Path(__file__).parent / "js/curve_handlers_check.js"), str(WWW)],
                       capture_output=True, text=True, timeout=120,
                       env={**os.environ, "NODE_PATH": NODE_PATH, "CHROME": CHROME})
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert out["errors"] == []
    assert out["calls"] == [["pick", "jan", 3, "b"], ["typed", 7, "42"], ["changed", "c"], ["enter", 5], ["leave"]]


async def test_cards_served(hass: HomeAssistant, hass_client_no_auth) -> None:
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain="battman", title="Battman", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_client_no_auth()
    for f in ("battman-curve-editor.js", "battman-curvy.js", "battman-pricy.js"):
        assert (await client.get(f"/battmanfiles/{f}")).status == 200, f
    for page in CARDS:
        assert (await client.get(f"/battmanfiles/{page}.html")).status == 404, page
