"""Battman brings the descriptions of its own engine items up to date where an older version wrote them:
only exact matches, only the description, nothing else in the files, and the same result every time."""

import hashlib
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.util.yaml import load_yaml

from custom_components.battman import automation_files, engine

# what earlier versions wrote (they mention things that no longer exist)
OLD = [
    "Battman engine, made by Battman from its blueprint. Does nothing unless Battman is in charge "
    "(binary_sensor.battman_in_charge). Battman won't overwrite it; delete it and reinstall to get Battman's version back.",
    "Battman engine, made by Battman from its blueprint (ported like for like from Smiggles). Does nothing unless "
    "Battman is in charge (binary_sensor.battman_in_charge). Battman won't overwrite it; delete it and reinstall to get "
    "Battman's version back.",
    "Battman engine, made by Battman from its blueprint (ported like for like from Smiggles). Does nothing unless "
    "Battman is in charge (binary_sensor.battman_in_charge). Battman won't overwrite it; delete it and run Migrate "
    "(or reinstall) to get Battman's version back.",
]


def _files(tmp: Path) -> tuple[Path, Path]:
    autos, scripts = tmp / "automations.yaml", tmp / "scripts.yaml"
    autos.write_text(
        "- id: battman_engine_main_loop\n  alias: Battman engine – main loop\n  description: >-\n    " + OLD[2] + "\n"
        "  use_blueprint:\n    path: battman/battman_engine_main_loop.yaml\n    input: {}\n"
        "- id: battman_engine_watchdog\n  alias: Battman engine – watchdog\n  description: " + OLD[1] + "\n"
        "  use_blueprint:\n    path: battman/battman_engine_watchdog.yaml\n    input: {}\n"
        "- id: battman_engine_curtail\n  alias: mine\n  description: I changed this one myself\n"
        "  use_blueprint:\n    path: battman/battman_engine_curtail.yaml\n    input: {}\n"
        "- id: somebody_elses\n  alias: other\n  description: " + OLD[0] + "\n  triggers: []\n"
    )
    scripts.write_text(
        "battman_engine:\n  alias: Battman engine\n  description: " + OLD[0] + "\n  sequence: []\n"
        "battman_apply_scene:\n  alias: Battman apply scene\n  description: " + engine.NOTE + "\n  sequence: []\n"
    )
    return autos, scripts


def test_hashes_are_those_of_the_old_wordings() -> None:
    assert engine.OLD_NOTE_HASHES == {hashlib.sha256(o.encode()).hexdigest() for o in OLD}
    assert hashlib.sha256(engine.NOTE.encode()).hexdigest() not in engine.OLD_NOTE_HASHES


def test_only_exact_old_descriptions_change_and_nothing_else(tmp_path) -> None:
    autos, scripts = _files(tmp_path)
    ids = {a["id"] for a in engine.AUTOMATIONS}
    changed = automation_files.refresh_descriptions(autos, scripts, ids, set(engine.SCRIPTS), engine.NOTE, engine.OLD_NOTE_HASHES)
    assert sorted(changed) == ["battman_engine", "battman_engine_main_loop", "battman_engine_watchdog"], changed
    a = {x["id"]: x for x in load_yaml(str(autos))}
    s = load_yaml(str(scripts))
    assert a["battman_engine_main_loop"]["description"] == engine.NOTE
    assert a["battman_engine_watchdog"]["description"] == engine.NOTE
    assert s["battman_engine"]["description"] == engine.NOTE
    assert a["battman_engine_curtail"]["description"] == "I changed this one myself"       # yours: left alone
    assert a["somebody_elses"]["description"] == OLD[0]                                      # not Battman's id
    assert a["battman_engine_main_loop"]["alias"] == "Battman engine – main loop"             # nothing else touched
    assert a["battman_engine_main_loop"]["use_blueprint"]["path"] == "battman/battman_engine_main_loop.yaml"
    assert a["battman_engine_curtail"]["alias"] == "mine" and s["battman_engine"]["sequence"] == []


def test_second_run_changes_nothing(tmp_path) -> None:
    autos, scripts = _files(tmp_path)
    args = ({a["id"] for a in engine.AUTOMATIONS}, set(engine.SCRIPTS), engine.NOTE, engine.OLD_NOTE_HASHES)
    assert automation_files.refresh_descriptions(autos, scripts, *args)
    before = (autos.read_bytes(), scripts.read_bytes())
    assert automation_files.refresh_descriptions(autos, scripts, *args) == []
    assert (autos.read_bytes(), scripts.read_bytes()) == before


async def test_missing_or_broken_files_never_raise(hass: HomeAssistant) -> None:
    assert await engine.async_refresh_notes(hass) == []                      # no files at all
    Path(hass.config.path("automations.yaml")).write_text("- id: [unclosed\n")
    assert await engine.async_refresh_notes(hass) == []                      # unreadable: logged, skipped
