"""Test setup: load custom_components/battman from this repo."""

from pathlib import Path

import pytest

REPO_COMPONENTS = str(Path(__file__).resolve().parent.parent / "custom_components")


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
