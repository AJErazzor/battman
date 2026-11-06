"""The Log card's Forecast / Both views (issue #62).

The log lists predicted blocks in the Chill popup's own wording, using a copy of the popup's grouping code.
These tests make sure that copy never drifts from the popup, and that the card is a clean node module.
"""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1] / "custom_components/battman"
WWW = ROOT / "www"


def _lines(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def test_log_copy_of_the_popup_logic_matches_the_popup() -> None:
    popup = (WWW / "battman-forecast.html").read_text()
    pure = popup[popup.index("// <pure>") + len("// <pure>"):popup.index("// </pure>")]
    log = (WWW / "battman-log.js").read_text()
    start = log.index("const FP = (() => {") + len("const FP = (() => {")
    end = log.index("return { group, split, describe, money };", start)
    assert _lines(log[start:end]) == _lines(pure), "re-copy the <pure> block of battman-forecast.html into the Log card"


def test_log_card_forecast_views() -> None:
    js = (WWW / "battman-log.js").read_text()
    assert subprocess.run(["node", "--input-type=module", "--check"], input=js, text=True).returncode == 0
    assert "domain: 'script', service: 'battman_engine_forecast'" in js   # the same script the popup calls
    assert "'battman.logView'" in js and "battman.logFuture" not in js
    # a remembered Forecast / Both loads the forecast on entry
    assert re.search(r"started = true;\s+setFcStamp\(\);[^\n]*\n\s+if \(wantsFuture\(\) && !fc\) loadForecast\(\);", js)
