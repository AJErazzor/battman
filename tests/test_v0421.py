"""v0.42.1: the forecast's first blocks use what the house and the solar are doing right now, then fade
into yesterday's load and the Solcast forecast. A block whose mode has the solar off shows what is available."""

from pathlib import Path

ROOT = Path(__file__).parents[1] / "custom_components/battman"
SCRIPTS = ROOT / "blueprints/script"


def test_inputs_reads_the_live_house_and_solar() -> None:
    text = (SCRIPTS / "battman_engine_inputs.yaml").read_text()
    assert "house_power_now: sensor.sigen_plant_consumed_power" in text
    assert "solar_power_now: sensor.sigen_plant_pv_power" in text
    assert "load_now_kw:" in text and "pv_now_kw:" in text


def test_forecast_holds_the_live_readings_then_fades() -> None:
    text = (SCRIPTS / "battman_engine_forecast.yaml").read_text()
    assert "live_hold_minutes: 30" in text and "live_fade_minutes: 60" in text
    assert "live_weight:" in text and "base.load_now_kw" in text and "base.pv_now_kw" in text
    # the live solar reading is only trusted while the mode lets the solar work
    assert "'Charge Solar Off', 'Float Solar Off'" in text and "live_pv_ok" in text
    # the decision still gets the profile hour or the 30-minute average, not the live reading
    assert "load_avg_kw: '{{ later_load if use_profile and not slot.live else base.load_avg_kw }}'" in text
    assert "solar_off: '{{ not solar_on }}'" in text


def test_page_says_when_the_solar_is_switched_off() -> None:
    page = (ROOT / "www/battman-forecast.html").read_text()
    assert "solar switched off" in page and "a.every(s => s.solar_off)" in page
