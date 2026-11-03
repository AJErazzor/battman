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
def test_what_the_button_asks() -> None:
    """The card's confirmation: HA's own dialog text, or false (just switch). Never stops a press it can't judge."""
    out = _node("""
const P = 'sensor.p';
const states = (buy, fit, attrs) => ({ 'sensor.amber_5min_current_general_price': { state: String(buy) }, 'sensor.amber_5min_current_feed_in_price': { state: String(fit) },
  [P]: { attributes: attrs } });
const ask = (st, o) => window.BattmanLib.modeConfirmation(st, o, P);
process.stdout.write(JSON.stringify({
  sell: ask(states(0.42, -0.04, {}), 'Discharge'), sellOk: ask(states(0.42, 0.12, {}), 'Discharge'),
  buy: ask(states(0.42, 0.05, { confirmBuyAbove: 30 }), 'Charge'), buyNever: ask(states(0.42, 0.05, { confirmBuyAbove: 0 }), 'Charge'),
  party: ask(states(0.08, 0.05, { confirmPriceMismatch: true }), 'Float Solar Off'), partyOff: ask(states(0.08, 0.05, { confirmPriceMismatch: false }), 'Float Solar Off'),
  noPrice: ask({ [P]: { attributes: {} } }, 'Discharge'), noParams: ask({}, 'Charge'), broken: window.BattmanLib.modeConfirmation(null, 'Discharge', P),
}));""")
    assert out["sell"] == {"text": "Feed-in is -4.0c: you would pay to export. Sell anyway?"} and out["sellOk"] is False
    assert out["buy"] == {"text": "Buy is 42.0c, above your 30.0c limit. Buy anyway?"} and out["buyNever"] is False
    assert out["party"] == {"text": "Buy is 8.0c: House Party is for negative prices. House Party anyway?"} and out["partyOff"] is False
    assert out["noPrice"] is False and out["noParams"] is False and out["broken"] is False


def test_mode_card_buttons() -> None:
    yml = (ROOT / "cards/batterymode.yaml").read_text()
    for mode in ("Charge", "Discharge", "Float", "Charge Solar Off", "Float Solar Off"):   # the five that can go against the price
        m = re.search(rf"option: {mode}\n +confirmation: '\[\[\[ return window.BattmanLib && window.BattmanLib.modeConfirmation \? "
                      rf'window.BattmanLib.modeConfirmation\(states, "{mode}", "\[\[map:parameters\]\]"\) : false; \]\]\]\'', yml)
        assert m, mode
    assert yml.count("window.BattmanLib.modeConfirmation(states") == 7                     # (Buy, Sell, Sell Solar, HOOOOVER, House Party + the two simple-mode rows)
    for mode in ("Self Consume", "Drain"):                                                   # no price rule: no confirmation
        assert not re.search(rf"option: {mode}\n +confirmation:", yml), mode
    assert "fire-dom-event" in yml and "battman_mode" not in yml                              # (only the info button's popup)
    assert yml.count("confirmation:") == 9 and "Turn Active off?" in yml and "Turn Curtail on?" in yml


async def test_confirmation_settings(hass: HomeAssistant) -> None:
    await _setup(hass)
    assert _la(hass, "confirmPriceMismatch") is True and _la(hass, "confirmBuyAbove") == 0     # on; Buy never asks until you set a number
    await _set(hass, confirmBuyAbove=30, confirmPriceMismatch=False)
    assert _la(hass, "confirmBuyAbove") == 30 and _la(hass, "confirmPriceMismatch") is False
    await _set(hass, confirmBuyAbove=120)                                                      # out of range is ignored
    assert _la(hass, "confirmBuyAbove") == 30
