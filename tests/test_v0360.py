"""v0.36.x: mode buttons that ask first when the press goes against the price; Active and Curtail always confirm;
the two settings (Dashboard options → Confirmations)."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant

from .test_v0100 import _la, _set, _setup

ROOT = Path(__file__).parents[1] / "custom_components/battman"
LIB = ROOT / "www/battman-lib.js"
needs_node = pytest.mark.skipif(not shutil.which("node"), reason="needs node")


def _node(script: str):
    page = ("globalThis.window = globalThis;\n"
            "globalThis.setTimeout = () => 0; globalThis.setInterval = () => 0;\n")
    r = subprocess.run(["node", "-"], input=page + LIB.read_text() + "\n" + script, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@needs_node
def test_when_a_mode_asks() -> None:
    cases = [  # option, buy c, feed-in c, extras -> asks?
        ("Discharge", 20, -4, {}), ("Discharge", 20, 12, {}), ("Float", 20, -0.1, {}), ("Float", 20, 0, {}),
        ("Charge Solar Off", 0, 5, {}), ("Charge Solar Off", -3, 5, {}), ("Float Solar Off", 8, 5, {}), ("Float Solar Off", -8, 5, {}),
        ("Charge", 42, 5, {"buyAbove": 30}), ("Charge", 25, 5, {"buyAbove": 30}), ("Charge", 42, 5, {}), ("Charge", -9, 5, {"buyAbove": 30}),
        ("Self Consume", 99, -9, {}), ("Drain", 99, -9, {}),
        ("Discharge", 20, -4, {"confirmPrice": False}),
        ("Discharge", 20, None, {}), ("Charge", None, 5, {"buyAbove": 30}),
    ]
    out = _node(f"""const cases = {json.dumps(cases)}; const nan = (v) => v === null ? NaN : v;
process.stdout.write(JSON.stringify(cases.map(([o, b, f, x]) => window.BattmanLib.modeWarning(Object.assign({{ option: o, buy: nan(b), fit: nan(f) }}, x)))));""")
    asks = [w is not None for w in out]
    assert asks == [True, False, True, False, True, False, True, False, True, False, False, False, False, False, False, False, False]
    assert out[0] == "Feed-in is -4.0c: you would pay to export. Sell anyway?"
    assert out[4] == "Buy is 0.0c: HOOOOVER is for negative prices. HOOOOVER anyway?"
    assert out[8] == "Buy is 42.0c, above your 30.0c limit. Buy anyway?"


@needs_node
def test_pressing_a_mode_button() -> None:
    """Asks in browser_mod's own dialog (native Cancel / confirm buttons); never stops a press it can't judge."""
    out = _node("""
const calls = [], popups = []; let native = 0;
const states = { 'sensor.amber_5min_current_general_price': { state: '0.42' }, 'sensor.amber_5min_current_feed_in_price': { state: '-0.04' },
  'sensor.p': { attributes: { confirmPriceMismatch: true, confirmBuyAbove: 30 } } };
globalThis.document = { body: {}, querySelector: () => ({ hass: { states, callService: (d, s, x) => calls.push(x.option) } }) };
globalThis.getComputedStyle = () => ({ getPropertyValue: () => '' });
window.confirm = () => { native++; return true; };
window.browser_mod = { showPopup: (o) => popups.push(o) };
const press = (option) => window.BattmanLib.setMode({ option, mode: 'input_select.m', parameters: 'sensor.p' }, {});
press('Self Consume');              // never asks: switches at once
press('Discharge');                 // negative feed-in: asks, nothing switched yet
const sellAsk = popups[0], afterAsk = calls.length;
sellAsk.right_button_action();      // the confirm button: sells
press('Charge'); const buyAsk = popups[1];   // Buy above the 30c limit
delete window.browser_mod;          // no browser_mod: the browser's own box, and Yes sets it
press('Float');
states['sensor.p'].attributes = { confirmPriceMismatch: false };   // the setting off and no Buy limit: no question
press('Discharge'); press('Charge');
globalThis.document = { querySelector: () => ({ hass: { get states() { throw new Error('boom'); }, callService: (d, s, x) => calls.push('fallback ' + x.option) } }) };
press('Charge');                    // anything failing in the check must not stop the press
process.stdout.write(JSON.stringify({ calls, afterAsk, popups: popups.length, native, title: sellAsk.title, buyTitle: buyAsk.title,
  content: sellAsk.content, left: sellAsk.left_button, right: sellAsk.right_button }));""")
    assert out["afterAsk"] == 1                                               # only Self Consume so far: asking switched nothing
    assert out["calls"] == ["Self Consume", "Discharge", "Float", "Discharge", "Charge", "fallback Charge"]
    assert out["popups"] == 2 and out["native"] == 1                          # two dialogs; the one without browser_mod used the box
    assert (out["title"], out["buyTitle"], out["left"], out["right"]) == ("Sell?", "Buy?", "Cancel", "Sell anyway")
    assert "Feed-in is -4.0c: you would pay to export. Sell anyway?" in out["content"]


def test_mode_card_buttons() -> None:
    yml = (ROOT / "cards/batterymode.yaml").read_text()
    for mode in ("Charge", "Discharge", "Float", "Charge Solar Off", "Float Solar Off"):
        assert re.search(rf"battman_mode:[^\n]*\n\s+option: {mode}\n", yml), mode
    assert yml.count("battman_mode:") == 7                                   # Buy, Sell, Sell Solar, HOOOOVER, House Party (+ the two simple-mode rows)
    for mode in ("Self Consume", "Drain"):                                   # no price rule: still a plain service call
        assert re.search(rf"service: input_select.select_option\n\s+service_data:\n\s+entity_id: '\[\[map:mode\]\]'\n\s+option: {mode}\n", yml), mode
    assert yml.count("confirmation:") == 2 and "Turn Active off?" in yml and "Turn Curtail on?" in yml


async def test_confirmation_settings(hass: HomeAssistant) -> None:
    await _setup(hass)
    assert _la(hass, "confirmPriceMismatch") is True and _la(hass, "confirmBuyAbove") == 0     # on; Buy never asks until you set a number
    await _set(hass, confirmBuyAbove=30, confirmPriceMismatch=False)
    assert _la(hass, "confirmBuyAbove") == 30 and _la(hass, "confirmPriceMismatch") is False
    await _set(hass, confirmBuyAbove=120)                                                      # out of range is ignored
    assert _la(hass, "confirmBuyAbove") == 30
