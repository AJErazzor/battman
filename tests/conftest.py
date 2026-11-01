"""Test setup: load custom_components/battman from this repo."""

import os
from pathlib import Path

import pytest

REPO_COMPONENTS = str(Path(__file__).resolve().parent.parent / "custom_components")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """With BATTMAN_NO_SKIPS=1 (set in CI), a skipped test fails: every test must run there, so
    a browser test that couldn't find Chromium, or a test that couldn't find node, can't pass
    quietly by skipping."""
    outcome = yield
    report = outcome.get_result()
    if os.environ.get("BATTMAN_NO_SKIPS") == "1" and report.skipped and not hasattr(report, "wasxfail"):
        reason = report.longrepr[2] if isinstance(report.longrepr, tuple) else str(report.longrepr)
        report.outcome = "failed"
        report.longrepr = f"Skipped, but BATTMAN_NO_SKIPS=1 says every test must run: {reason}"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let HA find custom_components/battman in every test."""
    import custom_components  # the test harness's own package

    if REPO_COMPONENTS not in custom_components.__path__:
        custom_components.__path__.append(REPO_COMPONENTS)
    yield


@pytest.fixture(autouse=True)
def own_config_dir(hass, tmp_path):
    """Each test gets its own config folder, so theme files don't leak between tests."""
    hass.config.config_dir = str(tmp_path)
    yield


SMIGGLES_PROBE = "sensor.solarsystemcontrolparameters"


@pytest.fixture
def smiggles_installed(hass):
    """Smiggles is installed and in charge (its parameters sensor exists), as on A.J.'s HA
    today: the entity map points the engine entries at Smiggles' entities."""
    if hass.states.get(SMIGGLES_PROBE) is None:
        hass.states.async_set(SMIGGLES_PROBE, "on")
    yield
