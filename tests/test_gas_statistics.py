"""Tests of the gas usage statistics of the nefiteasy integration."""

from datetime import date
from unittest.mock import patch

from homeassistant.components.recorder import Recorder, get_instance
from homeassistant.components.recorder.statistics import get_last_statistics
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nefiteasy.gas import KWH_TO_M3, parse_page

from .conftest import ClientMock


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    recorder_mock: Recorder, enable_custom_integrations
):
    """Start the recorder before hass, then allow custom integrations."""
    yield


ENTRY_DATA = {
    "serial": "123456789",
    "accesskey": "myAccessKey",
    "password": "myPass",
    "min_temp": 10,
    "max_temp": 28,
    "temp_step": 0.5,
    "name": "Nefit",
}
PAGE_2 = "/ecus/rrc/recordings/gasusage?page=2"
POINTER = "/ecus/rrc/recordings/gasusagePointer"


def _expected_sum(client: ClientMock, field: str) -> float:
    """Add up the fixture the way the integration does."""
    total = 0.0
    for page in (1, 2):
        for record in parse_page(
            client.data[f"/ecus/rrc/recordings/gasusage?page={page}"]["value"]
        ):
            kwh = record.hot_water if field == "hw" else record.heating
            total = round(total + round(kwh * KWH_TO_M3, 3), 3)
    return total


async def _last_statistic(hass: HomeAssistant, statistic_id: str) -> dict:
    """Return the newest row of a statistic."""
    await get_instance(hass).async_block_till_done()
    stats = await get_instance(hass).async_add_executor_job(
        get_last_statistics, hass, 1, statistic_id, True, {"sum", "state"}
    )
    return stats[statistic_id][0]


@patch("custom_components.nefiteasy.coordinator.NefitCore")
async def test_gas_statistics(mock_class, hass: HomeAssistant):
    """Test the history goes into the statistics once, then day by day."""
    client = ClientMock(mock_class)
    mock_class.return_value = client

    entry = MockConfigEntry(domain="nefiteasy", data=ENTRY_DATA)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)

    hot_water = "nefiteasy:123456789_gas_hot_water"
    heating = "nefiteasy:123456789_gas_heating"

    last = await _last_statistic(hass, hot_water)
    assert dt_util.as_local(dt_util.utc_from_timestamp(last["start"])).date() == (
        date(2026, 11, 5)
    )
    assert last["state"] == round(7.5 * KWH_TO_M3, 3)
    assert last["sum"] == _expected_sum(client, "hw")

    last = await _last_statistic(hass, heating)
    assert last["sum"] == _expected_sum(client, "ch")

    # A new day appears in the history.
    client.data[PAGE_2]["value"][4] = {"d": "06-11-2026", "hw": 3.0, "ch": 20.0}
    client.data[POINTER]["value"] = 38
    requested: list[str] = []
    original_get = client.get

    def get(path):
        requested.append(path)
        original_get(path)

    client.get = get

    gas = entry.runtime_data.gas
    gas._next_check = None
    gas.async_schedule()
    await hass.async_block_till_done(wait_background_tasks=True)

    # Only the newest page is read: the statistics already have the rest.
    assert "/ecus/rrc/recordings/gasusage?page=1" not in requested
    assert PAGE_2 in requested

    last = await _last_statistic(hass, hot_water)
    assert dt_util.as_local(dt_util.utc_from_timestamp(last["start"])).date() == (
        date(2026, 11, 6)
    )
    # The new day is added to the sum of the earlier days, not counted twice.
    assert last["sum"] == _expected_sum(client, "hw")

    state = hass.states.get("sensor.nefit_gas_heating_yesterday")
    assert float(state.state) == round(20.0 * KWH_TO_M3, 3)
    assert state.attributes["average_outdoor_temperature"] is None
