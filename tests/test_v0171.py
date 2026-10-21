"""v0.17.1: the engine log without emoji (headings instead), one renderer for the Engine log
popup and the Log page, and the Battman cards' `theme:` option."""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant

from tools.smiggles_log_text import LOG_TEXT, plain_log

from . import engine_harness as H

ROOT = Path(__file__).parents[1]
WWW = ROOT / "custom_components/battman/www"
ENGINELOG = (WWW / "battman-enginelog.js").read_text()
SAMPLE = (Path(__file__).parent / "fixtures/engine_log_sample.txt").read_text()   # a Smiggles message
EMOJI = re.compile(r"[\U0001F300-\U0001FAFF☀-➿ℹ]")
HEADS = ["Mode", "Prices", "Battery", "SOC Limits", "Solar", "Actions", "Sell Forecasts", "Buy Forecasts",
         "Version", "Debug"]


def js(expr_list: list[str]) -> list:
    script = "globalThis.window = globalThis;\n" + ENGINELOG + "\nconst L = window.battmanEngineLog;\n" \
        + "process.stdout.write(JSON.stringify([" + ",".join(expr_list) + "]));"
    r = subprocess.run(["node", "-"], input=script, capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def test_engine_script_has_no_emoji() -> None:
    text = (ROOT / "custom_components/battman/blueprints/script/battman_engine.yaml").read_text()
    assert not EMOJI.findall(text)
    for head in ("Run: {{ now()", "Mode:", "Prices:", "Battery:", "SOC Limits:", "Solar:", "Actions:",
                 "Sell Forecasts:", "Buy Forecasts:", "Version:", "Debug: ", "(Spike 1)", "(Spike 2)", "(Bad!)"):
        assert head in text, head
    # the change is exactly the listed one, each once, on Smiggles' original
    orig = (Path(__file__).parent / "fixtures/smiggles_engine/scripts/SolarSystemControl.yaml").read_text()
    assert len(LOG_TEXT) == 16 and not EMOJI.findall(plain_log(orig)[orig.index("prettyMessage"):orig.index("alias: Debug Message")])


async def test_battman_log_reads_back_as_sections(hass: HomeAssistant) -> None:
    """A real Battman run: its message, and its line in engine.log, draw the same sections, no emoji."""
    from custom_components.battman import engine_log
    from custom_components.battman.const import IN_CHARGE

    entry, _rec = await H.start(hass, smiggles=False)
    hass.config_entries.async_update_entry(entry, data={**entry.data, IN_CHARGE: True})
    hass.bus.async_fire("battman_parameters_update", {"action": "SetAttribute"})
    import random
    soc, price = H.curves(random.Random(3))
    hass.bus.async_fire("battman_soc_curves_update", {"curves": soc})
    hass.bus.async_fire("battman_price_curves_update", {"curves": price})
    await hass.async_block_till_done()
    await hass.services.async_call("script", "turn_on", {"entity_id": "script.battman_engine"}, blocking=True)
    await H.tick(hass, 3)
    await H.tick(hass, 1)
    msg = hass.states.get("sensor.battman_engine_log").attributes["message"]
    assert not EMOJI.findall(msg) and msg.startswith("Run: ")
    line = engine_log.battman_path(hass).read_text().splitlines()[-1]
    assert "\n" not in line and "\\n" in line                       # one line per run, breaks kept as \n
    a, b, back = js([f"L.parse({json.dumps(msg)})", f"L.parse(L.fromFileLine({json.dumps(line)}).message)",
                     f"L.fromFileLine({json.dumps(line)}).message === {json.dumps(msg)}"])
    assert back and a == b
    assert [s["head"] for s in a["sections"]] == HEADS
    assert a["time"] and a["from"] and a["to"]


def test_smiggles_lines_still_read() -> None:
    """Smiggles' lines (copied in at migration): as a message, and flattened in the log file."""
    flat = "2026-10-20T16:10:34.1+10:30|" + SAMPLE.replace("\n", " ")
    a, b, html = js([f"L.parse({json.dumps(SAMPLE)})", f"L.parse(L.fromFileLine({json.dumps(flat)}).message)",
                     f"L.render({json.dumps(SAMPLE)}, {{title: 'Engine log'}})"])
    for p in (a, b):
        assert [s["head"] for s in p["sections"]] == HEADS, p
        assert p["time"] == "2026-10-20 16:10:34" and p["from"] == "Self Consume" and p["to"] == "Self Consume"
    assert not EMOJI.findall(html) and "Last run 2026-10-20 16:10:34" in html
    assert next(s for s in b["sections"] if s["head"] == "Battery")["value"] == "100.0% (40.0 kWh)"


def test_log_page_uses_the_popup_renderer() -> None:
    page = (WWW / "log.html").read_text()
    assert '<script src="/battman/battman-enginelog.js"></script>' in page
    assert "EL.render(p.message" in page and "emojiRegex" not in page
    card = (ROOT / "custom_components/battman/cards/batterymode.yaml").read_text()
    assert "R.render(raw, { title: 'Engine log' })" in card and "emojiOf" not in card
    init = (ROOT / "custom_components/battman/__init__.py").read_text()
    assert "battman-enginelog.js" in init


CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
NODE_PATH = "/tmp/pwtest/node_modules"


@pytest.mark.skipif(not (Path(CHROME).exists() and Path(NODE_PATH, "playwright").exists() and shutil.which("node")),
                    reason="needs Playwright and Chromium")
def test_card_theme_option_in_a_browser(tmp_path) -> None:
    r = subprocess.run(["node", str(Path(__file__).parent / "js/theme_check.js"), str(WWW / "battman-cards.js"),
                        str(tmp_path)], capture_output=True, text=True, timeout=120,
                       env={**os.environ, "NODE_PATH": NODE_PATH, "CHROME": CHROME})
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert out["stub"] == {"grid_options": {"columns": "full"}}                           # placed: the view's theme
    assert out["coffee"] == {"green": "#123456", "red": "#ff0000", "text": "#eeeeee"}    # theme + its dark mode
    assert out["nord"] == {"green": "#abcdef", "red": ""}                                 # follows a theme change
    assert "Theme “Battman Gone” isn't installed" in out["gone"]                          # no fallback
    assert "No dashboard theme picked" in out["unpicked"]
    assert out["back"] == "#123456"                                                       # and recovers
    assert out["named"] == "#abcdef"                                                      # theme: <name>
    assert out["plain"] == ""                                                             # no theme: the view's
    assert out["picker"] == "#123456"                     # card picker preview: Battman Coffee
    assert out["pickerNamed"] == "#abcdef"                # unless the card names a theme
    assert out["placed"] == ""                            # placed: the view's theme
