"""Tests of the nefiteasy Bosch cloud connection sensor."""

from unittest.mock import patch

from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNKNOWN
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
    coordinator = nefit_config.runtime_data

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


async def test_hot_water_state(hass: HomeAssistant, nefit_config, nefit_wrapper):
    """Test the hot water state follows uiStatus DHW."""
    entity_id = "binary_sensor.nefit_hot_water_state"
    state = hass.states.get(entity_id)
    assert state

    await nefit_config.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_ON

    nefit_wrapper.data["/ecus/rrc/uiStatus"]["value"]["DHW"] = "off"
    await nefit_config.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_OFF


async def test_hot_water_program_disabled(hass: HomeAssistant, nefit_wrapper):
    """Test the hot water program sensor is disabled by default."""
    entry = er.async_get(hass).async_get("binary_sensor.nefit_hot_water_program")
    assert entry
    assert entry.disabled is True


async def test_hot_water_program(
    hass: HomeAssistant, nefit_config, nefit_binary_sensor_wrapper, nefit_wrapper
):
    """Test the hot water program sensor follows the current switchpoint."""
    entity_id = er.async_get(hass).async_get_entity_id(
        "binary_sensor", "nefiteasy", "123456789_hot_water_program"
    )
    assert entity_id

    # The sensor registers its endpoints when it is added; poll them.
    await nefit_config.runtime_data.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state
    assert state.state == STATE_OFF
    assert state.attributes["since"] == "Th 23:00"
    assert state.attributes["next_switchpoint"] == "Fr 07:00"
    assert state.attributes["next_state"] == "on"

    # Without a program (hot water always comfort) there are no switchpoints.
    nefit_wrapper.data["/dhwCircuits/dhwA/dhwCurrentSwitchpoint"]["value"] = []
    await nefit_config.runtime_data.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == STATE_UNKNOWN
