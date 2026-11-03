"""Nothing Battman ships (the component, the docs, the README) names the engine it replaced: no entity,
helper, script, file or comment. Tests may name it, to assert it's absent."""

import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
LEGACY = re.compile(r"smiggles|solarsystem", re.I)
SHIPPED = [ROOT / "custom_components", ROOT / "docs", ROOT / "README.md", ROOT / "DEPENDENCIES.md"]


def test_nothing_shipped_names_the_old_engine() -> None:
    hits = []
    for base in SHIPPED:
        files = [base] if base.is_file() else [p for p in base.rglob("*") if p.is_file()]
        for p in files:
            if p.suffix in {".png", ".jpg", ".svg", ".webp", ".ico", ".gif", ".woff", ".woff2", ".pyc"}:
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for n, line in enumerate(text.splitlines(), 1):
                if LEGACY.search(line):
                    hits.append(f"{p.relative_to(ROOT)}:{n}: {line.strip()[:100]}")
    assert not hits, "\n".join(hits)


def test_solar_card_defaults_to_battmans_no_export_toggle() -> None:
    js = (ROOT / "custom_components/battman/www/battman-solar-card.js").read_text()
    assert 'no_export_entity: "input_boolean.battman_no_export"' in js
