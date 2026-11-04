"""battman-pie-card: the NEM mix card draws its pies itself (no power-pie-card from HACS).

It's power-pie-card v0.3.2 renamed, with megawatt support. Stock power-pie-card reads `mw` as
milliwatts and only shows W or kW, which made the NEM mix card show 2.3 W instead of 2,285.9 MW.
"""

from pathlib import Path

ROOT = Path(__file__).parents[1]
JS = (ROOT / "custom_components/battman/www/battman-pie-card.js").read_text()
INIT = (ROOT / "custom_components/battman/__init__.py").read_text()


def test_pie_card_is_shipped_and_loaded() -> None:
    assert '"pie-card"' in INIT
    assert 'battmanDefine("battman-pie-card", ' in JS
    assert 'customElements.define("power-pie-card"' not in JS      # never claim the stock card's name


def test_megawatts() -> None:
    assert 'u === "mw") return value * 1000000' in JS               # MW is megawatts, not milliwatts
    assert '["kW", "MW"].includes(c.display_unit)' in JS
    assert "min_pct_label" in JS and "hide_legend_value" in JS


def test_nemmix_uses_it_and_needs_nothing_from_hacs() -> None:
    text = (ROOT / "custom_components/battman/cards/nemmix.yaml").read_text()
    assert "custom:battman-pie-card" in text and "custom:power-pie-card" not in text
    assert "power-pie-card" not in (ROOT / "custom_components/battman/dependencies.py").read_text()


def test_gas_group_solar_names_and_show_option() -> None:
    """#59: the four gas kinds are one "Gas" slice (the pie card sums them), the solar slices are
    Solar (S) / Solar (L), and the card's `show:` picks one pie."""
    text = (ROOT / "custom_components/battman/cards/nemmix.yaml").read_text()
    assert "name: Gas\n" in text and "name: Solar (S)" in text and "name: Solar (L)" in text
    assert "Gas (CCGT)" not in text and "Rooftop Solar" not in text
    assert "sensor.battman_nem_gas_recip" in text                # the warning line still names a missing member
    assert "Array.isArray(e.entities)" in JS and "parts.some((p) => !isFinite(p))" in JS   # a group needs every member
    cards = (ROOT / "custom_components/battman/www/battman-cards.js").read_text()
    for v in ('"both"', '"generation"', '"demand"'):
        assert v in cards
    assert "cardConfig(id, data, this._config)" in cards          # the dashboard card and Convert both apply it
