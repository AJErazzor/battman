"""v0.43.2: the "[[map:...]] markers are filled" header sentence is only on files that have markers."""

import re
from pathlib import Path

ROOT = Path(__file__).parents[1] / "custom_components/battman"
SENTENCE = "[[map:...]] markers are filled from Battman's entity map."


def _has_markers(text: str) -> bool:
    return any("[[map:" in line for line in text.splitlines() if not line.lstrip().startswith("#"))


def test_header_sentence_matches_the_markers() -> None:
    files = list((ROOT / "blueprints").glob("*/*.yaml")) + list((ROOT / "packages").glob("*.yaml"))
    assert files
    for f in files:
        text = f.read_text()
        if _has_markers(text):
            assert SENTENCE in text, f"{f.name} uses markers but doesn't say so"
        else:
            assert SENTENCE not in text, f"{f.name} says it has markers but has none"
