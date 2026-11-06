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
    """Asks in a Battman dialog (no browser_mod); never stops a press it can't judge."""
    out = _node("""
// a minimal <dialog>: records what the lib builds, and lets the test press its buttons
const dialogs = [], docKeys = [], docEl = { style: { overflow: '' } };
const mkDialog = () => {
  const els = {}, ls = {}, d = { attrs: {}, children: [], open: false, removed: false,
    setAttribute(k, v) { d.attrs[k] = v; },
    querySelector(sel) { return els[sel] || (els[sel] = { textContent: '', ls: {}, addEventListener(n, f) { this.ls[n] = f; } }); },
    addEventListener(n, f) { ls[n] = f; },
    showModal() { d.open = true; },
    close() { if (!d.open) return; d.open = false; ls.close && ls.close(); },
    remove() { d.removed = true; }, els, ls };
  dialogs.push(d); return d;
};
const press = (d, sel) => d.els[sel].ls.click();
const calls = [];
const states = { 'sensor.amber_5min_current_general_price': { state: '0.42' }, 'sensor.amber_5min_current_feed_in_price': { state: '-0.04' },
  'sensor.p': { attributes: { confirmPriceMismatch: true, confirmBuyAbove: 30 } } };
let native = 0;
globalThis.document = { body: { appendChild() {} }, documentElement: docEl, createElement: mkDialog, addEventListener: (n, f) => docKeys.push(f), removeEventListener() {},
  querySelector: () => ({ hass: { states, callService: (d, s, x) => calls.push(x.option) } }) };
globalThis.getComputedStyle = () => ({ getPropertyValue: (k) => k === '--battman-orange' ? '#f90' : '' });
window.confirm = () => { native++; return true; };
const go = (option) => window.BattmanLib.setMode({ option, mode: 'input_select.m', parameters: 'sensor.p' }, {});
go('Self Consume');                 // never asks: switches at once
go('Discharge');                    // negative feed-in: asks, nothing switched yet
const sellAsk = dialogs[0], afterAsk = calls.length, overflowOpen = docEl.style.overflow;
press(sellAsk, '.no'); const cancelled = calls.length;      // Cancel: closes, switches nothing
go('Discharge');
press(dialogs[1], '.yes');          // the confirm button: closes and sells
const backdrop = (go('Charge'), dialogs[2]);                 // Buy above the 30c limit; a tap on the backdrop cancels
backdrop.ls.click({ target: backdrop }); const afterBackdrop = calls.length;
go('Float');                        // a new question while another is open closes the old one first
go('Charge'); const replaced = dialogs[3].open === false && dialogs[4].open === true;
docKeys[docKeys.length - 1]({ key: 'Escape' });   // Escape (real, or the synthetic one a popup's script sends): closes without switching
const escClosed = dialogs[4].open === false;
const afterEsc = calls.length;
states['sensor.p'].attributes = { confirmPriceMismatch: false };   // the setting off and no Buy limit: no question
go('Discharge'); go('Charge');
globalThis.document = { querySelector: () => ({ hass: { get states() { throw new Error('boom'); }, callService: (d, s, x) => calls.push('fallback ' + x.option) } }) };
go('Charge');                       // anything failing in the check must not stop the press
process.stdout.write(JSON.stringify({ calls, afterAsk, cancelled, afterBackdrop, afterEsc, replaced, native, n: dialogs.length,
  escClosed, overflowOpen, overflowAfter: docEl.style.overflow, theme: sellAsk.attrs.style,
  h: sellAsk.els['.h'].textContent, m: sellAsk.els['.m'].textContent, yes: sellAsk.els['.yes'].textContent, buyYes: dialogs[2].els['.yes'].textContent }));""")
    assert out["afterAsk"] == 1 and out["cancelled"] == 1                     # only Self Consume so far: asking and Cancel switched nothing
    assert out["afterBackdrop"] == 2 and out["afterEsc"] == 2                 # backdrop tap and Escape switched nothing either
    assert out["calls"] == ["Self Consume", "Discharge", "Discharge", "Charge", "fallback Charge"]
    assert out["escClosed"] is True
    assert out["replaced"] is True and out["native"] == 0                     # one question at a time; never the browser's box
    assert out["overflowOpen"] == "hidden" and out["overflowAfter"] == ""     # the page doesn't scroll behind it, and is released
    assert "--battman-orange:#f90" in out["theme"]                            # the dialog takes the tapped element's Battman colours
    assert out["h"] == "Sell?" and out["yes"] == "Sell anyway" and out["buyYes"] == "Buy anyway"
    assert out["m"] == "Feed-in is -4.0c: you would pay to export. Sell anyway?"


@needs_node
def test_active_and_curtail_ask_first() -> None:
    """Active / Curtail ask in the same dialog; only the confirm button flips the switch."""
    out = _node("""
// a minimal <dialog>: records what the lib builds, and lets the test press its buttons
const dialogs = [], docKeys = [], docEl = { style: { overflow: '' } };
const mkDialog = () => {
  const els = {}, ls = {}, d = { attrs: {}, children: [], open: false, removed: false,
    setAttribute(k, v) { d.attrs[k] = v; },
    querySelector(sel) { return els[sel] || (els[sel] = { textContent: '', ls: {}, addEventListener(n, f) { this.ls[n] = f; } }); },
    addEventListener(n, f) { ls[n] = f; },
    showModal() { d.open = true; },
    close() { if (!d.open) return; d.open = false; ls.close && ls.close(); },
    remove() { d.removed = true; }, els, ls };
  dialogs.push(d); return d;
};
const press = (d, sel) => d.els[sel].ls.click();
const calls = [];
const states = { 'input_boolean.a': { state: 'on' } };
globalThis.document = { body: { appendChild() {} }, documentElement: docEl, createElement: mkDialog, addEventListener() {}, removeEventListener() {},
  querySelector: () => ({ hass: { states, callService: (d, s, x) => calls.push(d + '.' + s + ' ' + x.entity_id) } }) };
globalThis.getComputedStyle = () => ({ getPropertyValue: () => '' });
const T = { entity: 'input_boolean.a', name: 'Turn Active', ask_off: 'Off msg', ask_on: 'On msg' };
window.BattmanLib.setToggle(T, {});
const before = calls.length;
press(dialogs[0], '.no'); const cancelled = calls.length;
window.BattmanLib.setToggle(T, {});
press(dialogs[1], '.yes');
states['input_boolean.a'].state = 'on'; states['sensor.fit'] = { state: '-0.04' };   // Curtail on, feed-in negative: says why off costs money
const C = { entity: 'input_boolean.a', name: 'Turn Curtail', ask_off: 'Off msg', ask_on: 'On msg', ask_off_negative: 'Feed-in is {price}. Pay.', price: 'sensor.fit' };
window.BattmanLib.setToggle(C, {});
states['sensor.fit'].state = '0.10';                                                      // positive: the plain off message
window.BattmanLib.setToggle(C, {});
process.stdout.write(JSON.stringify({ before, cancelled, calls, h: dialogs[0].els['.h'].textContent, m: dialogs[0].els['.m'].textContent,
  yes: dialogs[0].els['.yes'].textContent, neg: dialogs[2].els['.m'].textContent, pos: dialogs[3].els['.m'].textContent }));""")
    assert out["before"] == 0 and out["cancelled"] == 0
    assert out["calls"] == ["homeassistant.toggle input_boolean.a"]
    assert out["h"] == "Turn Active?" and out["m"] == "Off msg" and out["yes"] == "Turn off"
    assert out["neg"] == "Feed-in is -4.0c. Pay." and out["pos"] == "Off msg"


def test_mode_card_buttons() -> None:
    yml = (ROOT / "cards/batterymode.yaml").read_text()
    for mode in ("Charge", "Discharge", "Float", "Charge Solar Off", "Float Solar Off"):
        assert re.search(rf"battman_mode:[^\n]*\n\s+option: {mode}\n", yml), mode
    assert yml.count("battman_mode:") == 7                                   # Buy, Sell, Sell Solar, HOOOOVER, House Party (+ the two simple-mode rows)
    for mode in ("Self Consume", "Drain"):                                   # no price rule: still a plain service call
        assert re.search(rf"service: input_select.select_option\n\s+service_data:\n\s+entity_id: '\[\[map:mode\]\]'\n\s+option: {mode}\n", yml), mode
    assert yml.count("battman_toggle:") == 2 and "This will stop any exports." in yml and "Turning off means you pay to export" in yml   # Active / Curtail ask in the same popup
    assert "confirmation:" not in yml
    assert yml.count("visibility:") == 3                                     # the simple row and the two full rows are rows of the one stack, so hiding leaves no gap


async def test_confirmation_settings(hass: HomeAssistant) -> None:
    await _setup(hass)
    assert _la(hass, "confirmPriceMismatch") is True and _la(hass, "confirmBuyAbove") == 0     # on; Buy never asks until you set a number
    await _set(hass, confirmBuyAbove=30, confirmPriceMismatch=False)
    assert _la(hass, "confirmBuyAbove") == 30 and _la(hass, "confirmPriceMismatch") is False
    await _set(hass, confirmBuyAbove=120)                                                      # out of range is ignored
    assert _la(hass, "confirmBuyAbove") == 30
