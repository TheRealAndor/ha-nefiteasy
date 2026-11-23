"""Tests of the nefiteasy sensor integration."""

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import async_fire_time_changed


async def test_disabled_switch_default(hass: HomeAssistant, nefit_wrapper):
    """Test disabled state of entity."""
    entity_registry = er.async_get(hass)

    entry = entity_registry.async_get("switch.nefit_hot_water")
    assert entry
    assert entry.disabled is True

    entry = entity_registry.async_get("switch.nefit_hot_water_follows_program")
    assert entry
    assert entry.disabled is True

    entry = entity_registry.async_get("switch.nefit_holiday_mode")
    assert entry
    assert entry.disabled is True

    entry = entity_registry.async_get("switch.nefit_fireplace_mode")
    assert entry
    assert entry.disabled is True

    entry = entity_registry.async_get("switch.nefit_today_as_sunday")
    assert entry
    assert entry.disabled is True

    entry = entity_registry.async_get("switch.nefit_tomorrow_as_sunday")
    assert entry
    assert entry.disabled is True

    entry = entity_registry.async_get("switch.nefit_preheating")
    assert entry
    assert entry.disabled is True

    entry = entity_registry.async_get("switch.nefit_weather_dependent")
    assert entry
    assert entry.disabled is True

    entry = entity_registry.async_get("switch.nefit_lock_ui")
    assert entry
    assert entry.disabled is True

    entry = entity_registry.async_get("switch.nefit_shower_timer")
    assert entry
    assert entry.disabled is True


async def test_switch_states(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    nefit_switch_wrapper,
    nefit_wrapper,
):
    """Test states of switches."""
    freezer.tick(timedelta(seconds=65))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)

    state = hass.states.get("switch.nefiteasy_123456789_hot_water")
    assert state
    assert state.state == "on"

    state = hass.states.get("switch.nefiteasy_123456789_hot_water_follows_program")
    assert state
    assert state.state == "on"

    state = hass.states.get("switch.nefiteasy_123456789_holiday_mode")
    assert state
    assert state.state == "off"

    state = hass.states.get("switch.nefiteasy_123456789_fireplace_mode")
    assert state
    assert state.state == "off"

    state = hass.states.get("switch.nefiteasy_123456789_today_as_sunday")
    assert state
    assert state.state == "off"

    state = hass.states.get("switch.nefiteasy_123456789_tomorrow_as_sunday")
    assert state
    assert state.state == "off"

    state = hass.states.get("switch.nefiteasy_123456789_preheating")
    assert state
    assert state.state == "on"

    state = hass.states.get("switch.nefiteasy_123456789_weather_dependent")
    assert state
    assert state.state == "off"

    state = hass.states.get("switch.nefiteasy_123456789_lockui")
    assert state
    assert state.state == "off"

    state = hass.states.get("switch.nefiteasy_123456789_shower_timer")
    assert state
    assert state.state == "off"


async def test_switch_turn_on_off(
    hass: HomeAssistant, nefit_switch_wrapper, nefit_wrapper
):
    """Test states of switches."""
    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "switch.nefiteasy_123456789_holiday_mode"},
        blocking=True,
    )
    await hass.async_block_till_done()

    state = hass.states.get("switch.nefiteasy_123456789_holiday_mode")
    assert state
    assert state.state == "on"

    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "switch.nefiteasy_123456789_preheating"},
        blocking=True,
    )
    await hass.async_block_till_done()

    state = hass.states.get("switch.nefiteasy_123456789_preheating")
    assert state
    assert state.state == "off"


async def test_hot_water_switch_follows_user_mode(
    hass: HomeAssistant, nefit_config, nefit_switch_wrapper, nefit_wrapper
):
    """Test the hot water switch uses the setting of the current user mode.

    It used to read uiStatus DHW while writing the setting of the user mode
    and sprang back (ksya#44).
    """
    client = nefit_wrapper
    coordinator = nefit_config.runtime_data
    manual = "/dhwCircuits/dhwA/dhwOperationManualMode"
    clock = "/dhwCircuits/dhwA/dhwOperationClockMode"
    entity_id = "switch.nefiteasy_123456789_hot_water"

    await coordinator.async_refresh()
    await hass.async_block_till_done()

    # Clock mode: the clock setting is on, the manual one off.
    assert hass.states.get(entity_id).state == "on"

    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    await hass.async_block_till_done()

    assert client.data[clock]["value"] == "off"
    assert client.data[manual]["value"] == "off"
    assert hass.states.get(entity_id).state == "off"

    # Manual mode: the switch shows and writes the manual setting.
    client.set_usermode("manual")
    client.data[clock]["value"] = "on"
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "off"

    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    await hass.async_block_till_done()

    assert client.data[manual]["value"] == "on"
    assert client.data[clock]["value"] == "on"
    assert hass.states.get(entity_id).state == "on"


async def test_hot_water_follows_program(
    hass: HomeAssistant, nefit_config, nefit_switch_wrapper, nefit_wrapper
):
    """Test "follows program" writes eco or comfort.

    With comfort hot water is always on and the hot water switch is
    unavailable, like the Nefit Easy app hides it.
    """
    client = nefit_wrapper
    coordinator = nefit_config.runtime_data
    mode = "/dhwCircuits/dhwA/dhwOperationMode"
    entity_id = "switch.nefiteasy_123456789_hot_water_follows_program"

    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "on"

    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    await hass.async_block_till_done()

    assert client.data[mode]["value"] == "comfort"
    assert hass.states.get(entity_id).state == "off"
    state = hass.states.get("switch.nefiteasy_123456789_hot_water")
    assert state.state == "unavailable"

    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    await hass.async_block_till_done()

    assert client.data[mode]["value"] == "eco"
    state = hass.states.get("switch.nefiteasy_123456789_hot_water")
    assert state.state == "on"


async def test_presence_detection(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    nefit_config,
    nefit_wrapper_precense,
):
    """Test presence detection."""
    client = nefit_wrapper_precense

    entity_registry = er.async_get(hass)

    entry = entity_registry.async_get("switch.nefit_presence_my_device")
    assert entry

    freezer.tick(timedelta(seconds=65))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)

    state = hass.states.get("switch.nefit_presence_my_device")
    assert state
    assert state.state == "on"

    client.data["/ecus/rrc/homeentrancedetection/userprofile1/detected"][
        "value"
    ] = "off"

    freezer.tick(timedelta(seconds=65))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)

    state = hass.states.get("switch.nefit_presence_my_device")
    assert state
    assert state.state == "off"
