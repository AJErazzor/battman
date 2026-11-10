"""HA 2026.10 sends the tap event (ll-custom) from <home-assistant>, not from the tapped button, so the popup's
colours can't be read off the event's element (it's above the themed view). The popup then finds a Battman card
on the page that carries the theme. HA 2026.11 sends it from the button; that case is unchanged."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

LIB = Path(__file__).parents[1] / "custom_components/battman/www/battman-lib.js"
needs_node = pytest.mark.skipif(not shutil.which("node"), reason="needs node")


def _node(script: str):
    page = ("globalThis.window = globalThis;\n"
            "globalThis.setTimeout = () => 0; globalThis.setInterval = () => 0;\n")
    r = subprocess.run(["node", "-"], input=page + LIB.read_text() + "\n" + script, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


SETUP = """
const THEME = { 'battman-surface-popup': '#050d12', 'battman-surface-card': '#0a1a22', 'battman-orange': '#f90', 'battman-text-bright': '#eaf6fa' };
const themed = (extra) => ({ nodeType: 1, localName: 'battman-state', vars: Object.assign({}, THEME, extra || {}), querySelectorAll: () => [] });
const bare = (name) => ({ nodeType: 1, localName: name, vars: {}, querySelectorAll: () => [] });
const dialogs = [];
const mk = () => { const d = { attrs: {}, open: false, setAttribute(k, v) { d.attrs[k] = v; }, querySelector: () => ({ addEventListener() {} }),
  addEventListener() {}, showModal() { d.open = true; }, close() { d.open = false; }, remove() {} }; dialogs.push(d); return d; };
globalThis.getComputedStyle = (n) => ({ getPropertyValue: (k) => (n.vars || {})[k.replace(/^--/, '')] || '' });
const page = (card, ha) => {   // <home-assistant> > (shadow) hui-card > (shadow) the Battman card
  const huiCard = { nodeType: 1, localName: 'hui-card', vars: {}, querySelectorAll: () => [], shadowRoot: { querySelectorAll: () => card ? [card] : [] } };
  Object.assign(ha, { querySelectorAll: () => [bare('div'), huiCard], hass: { themes: { themes: { 'Battman Abyss': THEME } }, states: {} } });
  globalThis.document = { body: { appendChild() {} }, documentElement: { style: { overflow: '' } }, createElement: mk,
    addEventListener() {}, removeEventListener() {}, querySelector: (s) => s === 'home-assistant' ? ha : null };
};
const style = () => dialogs[dialogs.length - 1].attrs.style;
"""


@needs_node
def test_popup_colours_when_the_event_comes_from_home_assistant() -> None:
    out = _node(SETUP + """
const L = window.BattmanLib, ha = bare('home-assistant'), card = themed();
page(card, ha);
L.modal(ha, { html: 'x' });          // HA 2026.10: the event's element is <home-assistant>, which has no Battman colours
const fromHa = style();
L.modal(card, { html: 'x' });        // HA 2026.11: the tapped element is inside the themed view
const fromCard = style(), picked = L.themedEl(ha) === card, keeps = L.themedEl(card) === card;
page(null, ha);                      // nothing themed on the page at all: no crash, no colours, as before
L.modal(ha, { html: 'x' });
const none = style();
L.modal(undefined, { html: 'x' });   // and no element at all
process.stdout.write(JSON.stringify({ fromHa, fromCard, none, picked, keeps }));""")
    assert "--battman-surface-popup:#050d12" in out["fromHa"] and "--battman-orange:#f90" in out["fromHa"]
    assert out["fromCard"] == out["fromHa"]                              # the same colours either way
    assert "--battman-surface-popup" not in out["none"]
    assert out["picked"] is True and out["keeps"] is True
