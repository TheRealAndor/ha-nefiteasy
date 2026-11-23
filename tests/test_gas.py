"""Tests of the daily gas usage of the nefiteasy integration."""

from datetime import date
from unittest.mock import patch

from homeassistant.components.recorder import Recorder, get_instance
from homeassistant.components.recorder.statistics import get_last_statistics
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nefiteasy.gas import KWH_TO_M3, page_of_record, parse_page

from .conftest import ClientMock

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


def test_parse_page():
    """Test empty records are skipped and the temperature is scaled."""
    records = parse_page(
        [
            {"d": "22-11-2026", "hw": 5.1, "ch": 0.0, "T": 23},
            {"d": "21-11-2026", "hw": 5.3, "ch": 59.8, "T": -12},
            {"d": "255-256-65535", "hw": 6553.5, "ch": 6553.5, "T": -1},
        ]
    )
    assert [record.day for record in records] == [
        date(2026, 11, 21),
        date(2026, 11, 22),
    ]
    assert records[0].outdoor_temperature == -1.2
    assert records[0].m3("heating") == round(59.8 * KWH_TO_M3, 3)
    assert parse_page(None) == []


def test_page_of_record():
    """Test the page that holds a record."""
    assert page_of_record(1) == 1
    assert page_of_record(32) == 1
    assert page_of_record(33) == 2
    assert page_of_record(4437) == 139


async def test_gas_sensors(hass: HomeAssistant, nefit_wrapper):
    """Test the sensors show the newest day of the history."""
    await hass.async_block_till_done(wait_background_tasks=True)

    state = hass.states.get("sensor.nefit_gas_hot_water_yesterday")
    assert state
    assert float(state.state) == round(7.5 * KWH_TO_M3, 3)
    assert state.attributes["unit_of_measurement"] == "m³"
    assert state.attributes["date"] == "2026-11-05"
    assert state.attributes["energy_kwh"] == 7.5
    assert state.attributes["average_outdoor_temperature"] == 6.5
    assert state.attributes["statistic_id"] == "nefiteasy:123456789_gas_hot_water"

    state = hass.states.get("sensor.nefit_gas_heating_yesterday")
    assert state
    assert float(state.state) == round(35.0 * KWH_TO_M3, 3)


@patch("custom_components.nefiteasy.coordinator.NefitCore")
async def test_gas_statistics(mock_class, recorder_mock: Recorder, hass: HomeAssistant):
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
