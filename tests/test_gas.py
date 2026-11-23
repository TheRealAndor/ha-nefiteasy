"""Tests of the daily gas usage of the nefiteasy integration."""

from datetime import date

from homeassistant.core import HomeAssistant

from custom_components.nefiteasy.gas import KWH_TO_M3, page_of_record, parse_page


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
