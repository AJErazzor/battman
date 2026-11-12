"""Theme studio: Import, Paste and Load from box finish (issue #100).

All three go through importYaml(). It called applyChromeVars(), which doesn't exist in the card, so the
browser stopped halfway: the colours were replaced, but the font boxes, the redraw, the dropdown entry and
the "imported" message never happened. renderAll() at the end of the import applies the colours.
"""

import re
from pathlib import Path

JS = (Path(__file__).parents[1] / "custom_components/battman/www/battman-theme-studio.js").read_text()

# browser and language names importYaml() may call without defining them
BUILT_IN = {"String", "Object", "if", "function"}


def _body(name: str) -> str:
    start = JS.index(f"function {name}(")
    depth, i = 0, JS.index("{", start)
    for j in range(i, len(JS)):
        depth += {"{": 1, "}": -1}.get(JS[j], 0)
        if depth == 0:
            return JS[i:j + 1]
    raise AssertionError(name)


def test_import_calls_only_functions_the_studio_has() -> None:
    body = _body("importYaml")
    called = set(re.findall(r"(?<![.\w$])([A-Za-z_$][\w$]*)\s*\(", body)) - BUILT_IN
    missing = sorted(n for n in called if not re.search(rf"\bfunction {re.escape(n)}\(|\b(var|let|const) {re.escape(n)}\s*=", JS))
    assert missing == [], missing
    assert "applyChromeVars" not in JS
    # the colours still reach the studio: renderAll() applies them, after the font boxes are set
    assert body.index("setFontFields(") < body.index("renderAll();")
    assert "applyPreviewVars()" in _body("renderAll")
