"""v0.38.0: the Auto curve switcher. Settings are autoCurve* on the parameters sensor; a blueprint
automation (made once per install) picks a SOC preset from today's projected solar and writes it into
the current month, and puts the month's own curve back (reset hour, switched off, month end)."""

from datetime import timedelta
from pathlib import Path

import yaml
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .test_v0100 import _la, _set, _settle, _setup

ROOT = Path(__file__).parents[1] / "custom_components/battman"
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
SW = "automation.battman_engine_auto_curve_switcher"


def _preset(n: int) -> dict:
    return {k: [n * 10 + i % 3 for i in range(24)] for k in ("sell", "sell_high", "buy", "buy_high")}


async def _settle_all(hass: HomeAssistant) -> None:
    for _ in range(6):
        await _settle(hass)


async def _scene(hass: HomeAssistant, kwh_per_period: float = 2.0, periods: int = 4) -> tuple[str, dict]:
    """Solcast says `periods` half hours of `kwh_per_period` kW still to come (no solar made yet); two presets saved."""
    start = (dt_util.now() + timedelta(minutes=30)).replace(minute=0, second=0, microsecond=0)
    start = start if start > dt_util.now() else start + timedelta(minutes=30)
    detail = [{"period_start": start + timedelta(minutes=30 * i), "pv_estimate": kwh_per_period * 2,
               "pv_estimate10": kwh_per_period, "pv_estimate90": kwh_per_period * 3} for i in range(periods)]
    hass.states.async_set("sensor.solcast_pv_forecast_forecast_today", "10", {"detailedForecast": detail})
    hass.states.async_set("sensor.sigen_inverter_daily_pv_energy", "0")
    hass.states.async_set("sensor.sigen_plant_daily_third_party_inverter_energy", "0")
    hass.bus.async_fire("battman_soc_curves_update", {"presets": {"1": _preset(1), "2": _preset(2)},
                                                      "preset_names": {"1": "Cloudy", "2": "Sunny"}})
    await _settle_all(hass)
    mon = MONTHS[dt_util.now().month - 1]
    return mon, hass.states.get("sensor.battman_soc_curves").attributes["curves"][mon]


async def _check(hass: HomeAssistant) -> None:
    hass.bus.async_fire("battman_auto_curve_check")
    await _settle_all(hass)


def _auto(hass: HomeAssistant) -> dict:
    return dict(hass.states.get("sensor.battman_auto_curve").attributes)


def _curve(hass: HomeAssistant, mon: str) -> dict:
    return hass.states.get("sensor.battman_soc_curves").attributes["curves"][mon]


async def test_settings_defaults_and_limits(hass: HomeAssistant) -> None:
    await _setup(hass)
    assert _la(hass, "autoCurve") is False                                   # off until you switch it on
    assert (_la(hass, "autoCurveCheckHour"), _la(hass, "autoCurveRepeat"), _la(hass, "autoCurveResetHour")) == (6, 0, 20)
    assert _la(hass, "autoCurveBasis") == "p10"
    assert _la(hass, "autoCurveBelow") == "" and _la(hass, "autoCurveAbove") == ""     # blank = rule skipped
    assert _la(hass, "autoCurveHolidayFrom") == "" and _la(hass, "autoCurveBelowPreset") == 0
    await _set(hass, autoCurveBelow=12, autoCurveBelowPreset=3, autoCurveHolidayFrom="2026-12-24", autoCurveCheckHour=7)
    assert _la(hass, "autoCurveBelow") == 12 and _la(hass, "autoCurveBelowPreset") == 3
    assert _la(hass, "autoCurveHolidayFrom") == "2026-12-24" and _la(hass, "autoCurveCheckHour") == 7
    await _set(hass, autoCurveBelow="")                                      # blank again
    assert _la(hass, "autoCurveBelow") == ""
    await _set(hass, autoCurveBelow=501, autoCurveCheckHour=24, autoCurveBelowPreset=11, autoCurveBasis="x",
               autoCurveHolidayTo="not a date", autoCurveResetHour=-2)       # out of range: ignored
    assert _la(hass, "autoCurveCheckHour") == 7 and _la(hass, "autoCurveBelowPreset") == 3
    assert _la(hass, "autoCurveBasis") == "p10" and _la(hass, "autoCurveHolidayTo") == ""
    assert _la(hass, "autoCurveResetHour") == 20
    await _set(hass, autoCurveResetHour=-1)                                  # -1 = no daily reset
    assert _la(hass, "autoCurveResetHour") == -1


async def test_automation_is_made_and_loaded(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    assert hass.states.get(SW) is not None and hass.states.get(SW).state != "unavailable"
    assert "battman_engine_curve_switcher" in entry.data["automations_offered"]


async def test_an_existing_install_gets_it_once(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    path = Path(hass.config.path("automations.yaml"))
    autos = [a for a in yaml.safe_load(path.read_text()) if a["id"] != "battman_engine_curve_switcher"]
    path.write_text(yaml.safe_dump(autos, allow_unicode=True))
    assert await hass.config_entries.async_reload(entry.entry_id)               # offered already: stays deleted
    await hass.async_block_till_done()
    assert "battman_engine_curve_switcher" not in {a["id"] for a in yaml.safe_load(path.read_text())}
    hass.config_entries.async_update_entry(                                       # an install from before it existed
        entry, data={**entry.data, "automations_offered": [i for i in entry.data["automations_offered"] if i != "battman_engine_curve_switcher"]})
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert "battman_engine_curve_switcher" in {a["id"] for a in yaml.safe_load(path.read_text())}


async def test_below_rule_applies_a_preset_and_off_puts_the_curve_back(hass: HomeAssistant) -> None:
    await _setup(hass)
    mon, original = await _scene(hass)                                           # 4 x 2 kW x 0.5 h = 4 kWh to come
    await _set(hass, autoCurve=True, autoCurveBelow=12, autoCurveBelowPreset=1, autoCurveAbove=30, autoCurveAbovePreset=2)
    await _check(hass)
    a = _auto(hass)
    assert (a["status"], a["rule"], a["preset"]) == ("applied", "below", 1), a
    assert 3.9 < a["projected"] < 4.1 and a["generated"] == 0
    assert _curve(hass, mon)["sell"] == _preset(1)["sell"]                      # written into this month
    assert a["originalMonth"] == mon and a["original"]["sell"] == original["sell"]   # the month's own curve is kept
    assert hass.states.get("sensor.battman_soc_curves").attributes["preset_tracking"][f"month_{mon}"]["preset"] == "Cloudy"
    await _check(hass)                                                           # again: nothing to do, snapshot kept
    assert _auto(hass)["status"] == "unchanged" and _auto(hass)["original"]["sell"] == original["sell"]
    await _set(hass, autoCurve=False)                                            # switched off: back to the month's own
    await _settle_all(hass)
    assert _curve(hass, mon) == original
    assert _auto(hass)["status"] == "restored" and _auto(hass)["originalMonth"] == ""
    assert f"month_{mon}" not in hass.states.get("sensor.battman_soc_curves").attributes["preset_tracking"]


async def test_blank_rules_are_skipped_and_the_projection_adds_what_was_made(hass: HomeAssistant) -> None:
    await _setup(hass)
    mon, original = await _scene(hass)
    hass.states.async_set("sensor.sigen_inverter_daily_pv_energy", "5.5")
    hass.states.async_set("sensor.sigen_plant_daily_third_party_inverter_energy", "2.5")   # + the third-party inverter
    await _set(hass, autoCurve=True, autoCurveBelow="", autoCurveBelowPreset=1, autoCurveAbove=10, autoCurveAbovePreset=2)
    await _check(hass)
    a = _auto(hass)
    assert (a["status"], a["rule"], a["preset"]) == ("applied", "above", 2), a   # 8 made + 4 to come = 12 > 10
    assert 11.9 < a["projected"] < 12.1 and a["generated"] == 8
    await _set(hass, autoCurveAbove="")                                          # nothing matches: the curve goes back
    await _check(hass)
    await _settle_all(hass)
    assert _curve(hass, mon) == original and _auto(hass)["rule"] == ""


async def test_no_forecast_or_empty_preset_changes_nothing(hass: HomeAssistant) -> None:
    await _setup(hass)
    mon, original = await _scene(hass)
    await _set(hass, autoCurve=True, autoCurveBelow=12, autoCurveBelowPreset=7)   # preset 7 was never saved
    await _check(hass)
    assert _auto(hass)["status"] == "no_preset" and _curve(hass, mon) == original
    hass.states.async_set("sensor.solcast_pv_forecast_forecast_today", "unavailable", {})
    await _check(hass)
    assert _auto(hass)["status"] == "no_forecast" and _curve(hass, mon) == original


async def test_a_disabled_switcher_does_nothing(hass: HomeAssistant) -> None:
    await _setup(hass)
    mon, original = await _scene(hass)
    await _set(hass, autoCurveBelow=12, autoCurveBelowPreset=1)                  # autoCurve is still off
    await _check(hass)
    assert _curve(hass, mon) == original and _auto(hass)["status"] == "off"


def test_the_month_end_copy_runs_after_the_switchers_safety_restore() -> None:
    copy = yaml.safe_load((ROOT / "blueprints/automation/battman_engine_copy_curves.yaml").read_text())
    sw = (ROOT / "blueprints/automation/battman_engine_curve_switcher.yaml").read_text()
    assert copy["triggers"][0]["at"] == "23:55:00"
    assert "at: '23:50:00'" in sw                                                # restored before the copy
