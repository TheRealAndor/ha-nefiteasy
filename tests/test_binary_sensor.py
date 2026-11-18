"""Tests of the nefiteasy Bosch cloud connection sensor."""

from unittest.mock import patch

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import UpdateFailed


def _entity_id(hass: HomeAssistant) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(
        "binary_sensor", "nefiteasy", "123456789_cloud_connection"
    )
    assert entity_id
    return entity_id


async def test_connection_sensor_connected(hass: HomeAssistant, nefit_wrapper):
    """Test the connection sensor is on after a successful setup."""
    entity_id = _entity_id(hass)

    entry = er.async_get(hass).async_get(entity_id)
    assert entry.entity_category == "diagnostic"

    state = hass.states.get(entity_id)
    assert state
    assert state.state == STATE_ON
    assert state.attributes["device_class"] == "connectivity"
    assert state.attributes["last_error"] is None
    assert state.attributes["disconnected_since"] is None
    assert state.attributes["reconnects"] == 0


async def test_connection_sensor_outage(
    hass: HomeAssistant, nefit_config, nefit_wrapper
):
    """Test the sensor stays available and reports the reason of an outage."""
    entity_id = _entity_id(hass)
    coordinator = hass.data["nefiteasy"][nefit_config.entry_id]["client"]

    with patch.object(
        coordinator,
        "_async_update_data_inner",
        side_effect=UpdateFailed("first failure"),
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        state = hass.states.get(entity_id)
        assert state.state == STATE_OFF
        assert state.attributes["last_error"] == "first failure"
        since = state.attributes["disconnected_since"]
        assert since is not None

        # The other entities become unavailable, this one does not.
        assert hass.states.get("sensor.nefit_status").state == "unavailable"

    # A second failure in a row: the coordinator does not notify entities,
    # the sensor must still show the new reason.
    with patch.object(
        coordinator,
        "_async_update_data_inner",
        side_effect=UpdateFailed("second failure"),
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        state = hass.states.get(entity_id)
        assert state.state == STATE_OFF
        assert state.attributes["last_error"] == "second failure"
        assert state.attributes["disconnected_since"] == since

    await coordinator.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == STATE_ON
    assert state.attributes["disconnected_since"] is None
    # The reason of the last outage stays visible after recovering.
    assert state.attributes["last_error"] == "second failure"
