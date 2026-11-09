"""Theme studio: Import / Paste / Load from box must finish instead of throwing halfway.

The studio became a card in 845df57. Its import path kept calling applyChromeVars(), which only
ever existed on the old stand-alone page, so the browser threw "applyChromeVars is not defined"
after the colours and theme name had been replaced in memory: the font boxes, the redraw, the
dropdown entry, the "imported" message and the unsaved-changes reset were all skipped and nothing
confirmed the import. Every function a card calls has to exist in the card itself.
"""

import json
import subprocess
from pathlib import Path

WWW = Path(__file__).parents[1] / "custom_components/battman/www"
STUDIO = WWW / "battman-theme-studio.js"
CHECK = Path(__file__).parent / "js/theme_studio_import_check.js"


def test_theme_studio_is_valid_javascript() -> None:
    assert subprocess.run(["node", "--check", str(STUDIO)]).returncode == 0


def test_theme_studio_calls_only_functions_it_has() -> None:
    r = subprocess.run(["node", str(CHECK), str(STUDIO)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["missing"] == []


def test_importing_a_theme_applies_it_to_the_studio() -> None:
    js = STUDIO.read_text()
    body = js[js.index("function importYaml(text){"):]
    body = body[:body.index("function buildYaml()")]
    assert "applyPreviewVars()" in body           # the card's way of applying a palette
    assert "applyChromeVars" not in js            # the old page's helper, gone with the page
