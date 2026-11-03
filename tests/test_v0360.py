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
    assert out[0] == "Feed-in is -4.0c: you would pay to export.\n\nSell anyway?"
    assert out[4] == "Buy is 0.0c: HOOOOVER is for negative prices.\n\nHOOOOVER anyway?"
    assert out[8] == "Buy is 42.0c, above your 30.0c limit.\n\nBuy anyway?"


@needs_node
def test_pressing_a_mode_button() -> None:
    out = _node("""
const calls = []; let asked = [];
const states = { 'sensor.amber_5min_current_general_price': { state: '0.42' }, 'sensor.amber_5min_current_feed_in_price': { state: '-0.04' },
  'sensor.p': { attributes: { confirmPriceMismatch: true, confirmBuyAbove: 30 } } };
globalThis.document = { querySelector: () => ({ hass: { states, callService: (d, s, x) => calls.push([d, s, x.entity_id, x.option]) } }) };
const press = (option, answer) => { window.confirm = (m) => { asked.push(m); return answer; };
  window.BattmanLib.setMode({ option, mode: 'input_select.m', parameters: 'sensor.p' }); };
press('Discharge', false);       // feed-in is negative: asks, you say no -> nothing happens
press('Discharge', true);        // ... you say yes -> sells
press('Self Consume', false);    // never asks
press('Float', true);            // an override running makes no difference: still asks (and you said yes)
globalThis.document = { querySelector: () => ({ hass: { get states() { throw new Error('boom'); }, callService: (d, s, x) => calls.push(['fallback', x.option]) } }) };
press('Charge', false);          // anything failing in the check must not stop the press
process.stdout.write(JSON.stringify({ calls, asked: asked.length }));""")
    assert out["calls"] == [["input_select", "select_option", "input_select.m", "Discharge"],
                            ["input_select", "select_option", "input_select.m", "Self Consume"],
                            ["input_select", "select_option", "input_select.m", "Float"],
                            ["fallback", "Charge"]]
    assert out["asked"] == 3


@needs_node
def test_the_question_is_a_themed_popup() -> None:
    """With browser_mod the question is a popup with Cancel and '<Mode> anyway'; no box from the browser."""
    out = _node("""
const calls = [], popups = [], closed = []; let nativeAsked = 0;
const states = { 'sensor.amber_5min_current_general_price': { state: '0.42' }, 'sensor.amber_5min_current_feed_in_price': { state: '-0.04' },
  'sensor.p': { attributes: {} } };
globalThis.document = { body: {}, querySelector: () => ({ hass: { states, callService: (d, s, x) => calls.push(x.option) } }) };
globalThis.getComputedStyle = () => ({ getPropertyValue: () => '' });
window.confirm = () => { nativeAsked++; return true; };
window.browser_mod = { service: (n, d) => (n === 'popup' ? popups.push(d) : closed.push(n)) };
const press = () => window.BattmanLib.setMode({ option: 'Discharge', mode: 'input_select.m', parameters: 'sensor.p' }, {});
press();                                    // negative feed-in: asks, in a popup
const first = popups[0];
window.BattmanLib.answerMode(false);        // Cancel: nothing happens
press(); window.BattmanLib.answerMode(true);  // "Sell anyway": sells
process.stdout.write(JSON.stringify({ calls, popups: popups.length, closed, nativeAsked, title: first.title,
  body: first.content.custom_fields.body.replace(/<[^>]+>/g, '|').replace(/\\|+/g, '|') }));""")
    assert out["calls"] == ["Discharge"] and out["popups"] == 2 and out["nativeAsked"] == 0
    assert out["closed"] == ["close_popup", "close_popup"]
    assert out["title"] == "Sell?"
    assert "Feed-in is -4.0c: you would pay to export." in out["body"] and "Cancel" in out["body"] and "Sell anyway" in out["body"]
    assert "[[[" not in out["body"]


def test_mode_card_buttons() -> None:
    yml = (ROOT / "cards/batterymode.yaml").read_text()
    for mode in ("Charge", "Discharge", "Float", "Charge Solar Off", "Float Solar Off"):
        assert f"battman_mode:" in yml and re.search(rf"battman_mode:[^\n]*\n\s+option: {mode}\n", yml), mode
        assert f"service: input_select.select_option\n        service_data:\n          entity_id: '[[map:mode]]'\n          option: {mode}\n" not in yml
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
