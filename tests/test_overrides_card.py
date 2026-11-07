"""The Overrides card (custom:battman-overrides): a real element (www/battman-overrides.js), not button-cards full of
JavaScript strings. It was rebuilt from the old card, and these tests keep the proof that nothing changed:

- every strip and row it draws matches, byte for byte, what the old card drew on the same states (recorded from the
  old code in tests/snapshots/test_overrides_card.json), including preset names, locked rows, Plughole, a negative
  Buy price, a missing SOC and the Net Target states;
- what each tap, double-tap and hold does (quick edit, control centre, timer bar and sheet) is run on a stand-in page
  (tests/js/overrides_check.mjs) with frozen sample states, and every check there must pass;
- no globals, no inline handlers, and the old card's files and library code are gone.
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from .snapshots import assert_snapshot

ROOT = Path(__file__).parents[1] / "custom_components/battman"
WWW = ROOT / "www"
JS = Path(__file__).parent / "js"
FIXTURES = Path(__file__).parent / "fixtures"
needs_node = pytest.mark.skipif(not shutil.which("node"), reason="needs node to run the card's JavaScript")
# node's time zone and locale pinned, so the recorded outputs repeat on any machine
PINNED = {"TZ": "Australia/Adelaide", "LC_ALL": "C.UTF-8", "LANG": "C.UTF-8"}


def run_card_checks(tmp_path):
    out = tmp_path / "overrides_check.json"
    subprocess.run(["node", str(JS / "overrides_check.mjs"), str(out)], check=True, capture_output=True, text=True,
                   env={**os.environ, **PINNED})
    return json.loads(out.read_text())


@needs_node
def test_card_checks_all_pass(tmp_path) -> None:
    """Quick edit, control centre (Net Target, panels, scenes, save), timer bar and sheet, strip / row gestures."""
    r = run_card_checks(tmp_path)
    assert len(r["results"]) > 80
    failed = [f"{x['n']}: got {json.dumps(x['got'])[:200]}, expected {json.dumps(x['exp'])[:200]}" for x in r["results"] if not x["ok"]]
    assert failed == []


@needs_node
def test_strip_and_rows_match_the_old_card(tmp_path) -> None:
    r = run_card_checks(tmp_path)
    scenarios = json.loads((FIXTURES / "overrides_scenarios.json").read_text())
    expected = ({f"row:{s['name']}:{o}" for s in scenarios["rows"] for o in ("sell", "sellsolar", "buy", "any", "drain")}
                | {f"strip:{s['name']}" for s in scenarios["strips"]})
    assert set(r["snapshots"]) == expected
    recorded = json.loads((Path(__file__).parent / "snapshots/test_overrides_card.json").read_text())
    assert set(recorded) == expected, "stale or missing recordings"
    for key, html in r["snapshots"].items():
        assert_snapshot(__file__, key, html)


def test_a_missing_soc_is_never_shown_as_zero() -> None:
    """With the SOC unavailable the row shows dashes, not a made-up 0%."""
    snap = json.loads((Path(__file__).parent / "snapshots/test_overrides_card.json").read_text())
    row = snap["row:soc-unavailable:sell"]
    assert "—% → 50%" in row and "— kWh" in row


def test_the_card_is_one_element_with_no_globals() -> None:
    card = (WWW / "battman-overrides.js").read_text()
    core = (WWW / "battman-overrides-core.js").read_text()
    for name, text in (("battman-overrides.js", card), ("battman-overrides-core.js", core)):
        assert "window.bm" not in text, name
        assert not re.search(r"\bon(click|input|load|pointer\w*)=", text), name       # no inline handlers
        assert "browser_mod" not in text and "button-card" not in text, name
    assert 'battmanDefine("battman-overrides", BattmanOverrides)' in card
    assert 'battmanPicker("battman-overrides"' in card
    # the five overrides are defined once
    assert core.count('{ id: "sell",') == 1 and "attr_soc" not in core


def test_the_old_card_is_gone() -> None:
    assert not (ROOT / "cards/overrides.yaml").exists()
    lib = (WWW / "battman-lib.js").read_text()
    for gone in ("renderRow", "buildPopup", "bmq", "bmRoot", "POPUPS.html", "POPUPS.run"):
        assert gone not in lib, gone
    # one script starts the card, and the Power view places it by name
    loaded = re.search(r"const SCRIPTS = \[([^\]]*)\]", (WWW / "battman.js").read_text()).group(1)
    assert '"overrides"' in loaded
    assert "custom:battman-overrides" in (ROOT / "views/05-power.yaml").read_text()


def test_the_theme_studio_draws_the_real_rows() -> None:
    studio = (WWW / "battman-theme-studio.js").read_text()
    assert 'import { OVERRIDES, rowHtml } from "./battman-overrides-core.js";' in studio
    assert "rowHtml(o,MOCK_ATTR,states,env)" in studio
    assert "renderRow" not in studio and "loadBattmanLib" not in studio


def test_documented() -> None:
    docs = (Path(__file__).parents[1] / "docs/cards.md").read_text()
    row = next(line for line in docs.splitlines() if line.startswith("| `battman-overrides` |"))
    assert "Draws itself" in row and "button-card" not in row


def test_popups_fit_the_screen_and_the_close_button_has_room() -> None:
    """A tall popup is capped to the visible screen height (dvh, less the notch and home bar), scrolls inside, and the
    close button keeps its own place in the title bar. (On a phone the popups used to run off both ends and the close
    button ended up under the status bar or on top of the first row.)"""
    lib = (WWW / "battman-lib.js").read_text()
    assert "100dvh - env(safe-area-inset-top" in lib and "env(safe-area-inset-bottom" in lib
    assert ".bm .bm-scroll{" in lib and '<div class="bm-scroll">' in lib
    assert "82vh" not in lib and "90vh" not in lib                       # no popup scrolls itself or measures in vh
    card = (WWW / "battman-overrides.js").read_text()
    assert card.count("padding:0 52px") >= 4                             # the quick edit, help, dock help and control centre
    assert 'dlg.querySelector(".bm-scroll")' in card                       # the Save preset overlay is scrolled into view
