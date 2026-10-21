"""v0.17.0: Migrate copies the cost odometers' long-term statistics into Battman's sensors."""

from datetime import timedelta

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.battman import migrate


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_mock, enable_custom_integrations):
    """As conftest's, but with the recorder started first."""
    from .conftest import REPO_COMPONENTS
    import custom_components

    if REPO_COMPONENTS not in custom_components.__path__:
        custom_components.__path__.append(REPO_COMPONENTS)
    yield


@pytest.fixture(autouse=True)
def own_config_dir(recorder_mock, hass, tmp_path):
    """The recorder has to start before hass here (overrides conftest's)."""
    hass.config.config_dir = str(tmp_path)
    yield


async def test_odometer_statistics_copied(recorder_mock, hass: HomeAssistant) -> None:
    from homeassistant.components.recorder.models import StatisticMeanType
    from homeassistant.components.recorder.statistics import async_import_statistics, statistics_during_period
    from pytest_homeassistant_custom_component.components.recorder.common import async_wait_recording_done

    src, dst = "sensor.solarsystemcontrolbuytotal", "sensor.battman_buy_total"
    hour = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)
    meta = {"mean_type": StatisticMeanType.NONE, "has_sum": True, "name": None, "source": "recorder",
            "statistic_id": src, "unit_class": None, "unit_of_measurement": "$"}
    rows = [{"start": hour - timedelta(hours=h), "state": 100 + 10 * (5 - h), "sum": 1000 + 10 * (5 - h)}
            for h in range(5, 0, -1)]
    async_import_statistics(hass, meta, rows)
    await async_wait_recording_done(hass)
    msg = await migrate._copy_statistics(hass, src, dst)
    await async_wait_recording_done(hass)
    assert msg.endswith("5 hours"), msg
    got = await recorder_mock.async_add_executor_job(
        statistics_during_period, hass, hour - timedelta(hours=6), None, {dst}, "hour", None, {"state", "sum"})
    got = got[dst]
    assert [r["state"] for r in got] == [100, 110, 120, 130, 140]
    assert [r["sum"] for r in got] == [-40, -30, -20, -10, 0]      # same changes, ending at 0
    # never twice
    assert "already has statistics" in await migrate._copy_statistics(hass, src, dst)
