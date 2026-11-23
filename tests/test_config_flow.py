"""Tests of the config flow of the nefiteasy integration."""

import asyncio
from datetime import timedelta
from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nefiteasy.const import DOMAIN

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


@patch("custom_components.nefiteasy.config_flow.NefitCore")
async def test_setup(mock_class, hass: HomeAssistant):
    """Test we can setup the component."""
    client = ClientMock(mock_class)
    mock_class.return_value = client

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"serial": "123456789", "accesskey": "myAccessKey", "password": "mypassword"},
    )

    assert result["type"] == "form"
    assert result["step_id"] == "options"
    assert result["errors"] == {}

    with patch("custom_components.nefiteasy.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"min_temp": 12, "max_temp": 32, "temp_step": 0.2},
        )

    assert result["type"] == "create_entry"
    assert result["title"] == "123456789"
    assert result["data"] == {
        "serial": "123456789",
        "accesskey": "myAccessKey",
        "password": "mypassword",
        "min_temp": 12,
        "max_temp": 32,
        "temp_step": 0.2,
        "name": "Nefit",
    }


@patch("custom_components.nefiteasy.config_flow.NefitCore")
async def test_setup_invalid_credentials(mock_class, hass: HomeAssistant):
    """Test we can setup network."""
    client = ClientMock(mock_class)
    mock_class.return_value = client

    async def connect():
        loop = asyncio.get_event_loop()
        coroutine = client.failed_auth_handler("auth_error")
        loop.create_task(coroutine)

    client.connect = connect

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "serial": "123456789",
            "accesskey": "myAccessKey",
            "password": "mypassword",
        },
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "invalid_credentials"}


@patch("custom_components.nefiteasy.config_flow.NefitCore")
async def test_setup_invalid_password(mock_class, hass: HomeAssistant):
    """Test we can setup network."""
    client = ClientMock(mock_class)
    mock_class.return_value = client

    async def set_msg_event():
        client.xmppclient.message_event.set()

    def get(path):
        loop = asyncio.get_event_loop()
        coroutine = client.failed_auth_handler("auth_error_password")
        loop.create_task(coroutine)

        coroutine2 = set_msg_event()
        loop.create_task(coroutine2)

    client.get = get

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "serial": "123456789",
            "accesskey": "myAccessKey",
            "password": "mypassword",
        },
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "invalid_password"}


@patch("custom_components.nefiteasy.config_flow.NefitCore")
async def test_setup_connect_timeout(mock_class, hass: HomeAssistant):
    """Test we can setup network."""
    client = ClientMock(mock_class)
    mock_class.return_value = client

    async def wait():
        raise asyncio.TimeoutError

    client.xmppclient.connected_event.wait = wait

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "serial": "123456789",
            "accesskey": "myAccessKey",
            "password": "mypassword",
        },
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}


@patch("custom_components.nefiteasy.config_flow.NefitCore")
async def test_setup_message_timeout(mock_class, hass: HomeAssistant):
    """Test we can setup network."""
    client = ClientMock(mock_class)
    mock_class.return_value = client

    async def wait():
        raise asyncio.TimeoutError

    client.xmppclient.message_event.wait = wait

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "serial": "123456789",
            "accesskey": "myAccessKey",
            "password": "mypassword",
        },
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_communicate"}


@patch("custom_components.nefiteasy.config_flow.NefitCore")
async def test_setup_already_configured(mock_class, hass: HomeAssistant):
    """Test a thermostat that is already set up is not added twice."""
    MockConfigEntry(domain=DOMAIN, unique_id="123456789", data=ENTRY_DATA).add_to_hass(
        hass
    )
    mock_class.return_value = ClientMock(mock_class)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"serial": "123456789", "accesskey": "myAccessKey", "password": "mypassword"},
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@patch("custom_components.nefiteasy.config_flow.NefitCore")
async def test_setup_unknown_error_recovers(mock_class, hass: HomeAssistant):
    """Test an unexpected error shows a message and the user can try again."""
    client = ClientMock(mock_class)
    mock_class.side_effect = RuntimeError("boom")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"serial": "123456789", "accesskey": "myAccessKey", "password": "mypassword"},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "unknown"}

    mock_class.side_effect = None
    mock_class.return_value = client

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"serial": "123456789", "accesskey": "myAccessKey", "password": "mypassword"},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "options"

    with patch("custom_components.nefiteasy.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"min_temp": 10, "max_temp": 28, "temp_step": 0.5},
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == "123456789"


@patch("custom_components.nefiteasy.config_flow.NefitCore")
async def test_reauth(mock_class, hass: HomeAssistant):
    """Test new credentials can be entered after the cloud rejected them."""
    entry = MockConfigEntry(domain=DOMAIN, unique_id="123456789", data=ENTRY_DATA)
    entry.add_to_hass(hass)
    client = ClientMock(mock_class)
    mock_class.return_value = client

    result = await entry.start_reauth_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    # First attempt with a wrong password.
    async def set_msg_event():
        client.xmppclient.message_event.set()

    def get_wrong_password(path):
        loop = asyncio.get_event_loop()
        loop.create_task(client.failed_auth_handler("auth_error_password"))
        loop.create_task(set_msg_event())

    original_get = client.get
    client.get = get_wrong_password

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"accesskey": "newAccessKey", "password": "wrong"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_password"}

    client.get = original_get
    client.xmppclient.message_event.clear()

    with patch("custom_components.nefiteasy.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"accesskey": "newAccessKey", "password": "newPass"}
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data["accesskey"] == "newAccessKey"
    assert entry.data["password"] == "newPass"
    assert entry.data["serial"] == "123456789"
    assert entry.data["min_temp"] == 10


OPTIONS = {
    "min_temp": 12,
    "max_temp": 25,
    "temp_step": 0.5,
    "scan_interval": 30,
    "request_timeout": 25,
}


@patch("custom_components.nefiteasy.coordinator.NefitCore")
async def test_options_flow(mock_class, hass: HomeAssistant):
    """Test the options change the limits, poll interval and timeout."""
    client = ClientMock(mock_class)
    mock_class.return_value = client

    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)

    assert entry.runtime_data.update_interval == timedelta(seconds=60)
    assert entry.runtime_data.request_timeout == 20

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    # The form starts with the values of the setup.
    suggested = {
        str(key): key.description["suggested_value"]
        for key in result["data_schema"].schema
    }
    assert suggested == {
        "min_temp": 10,
        "max_temp": 28,
        "temp_step": 0.5,
        "scan_interval": 60,
        "request_timeout": 20,
    }

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], OPTIONS
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == OPTIONS
    await hass.async_block_till_done(wait_background_tasks=True)

    # The entry was reloaded with the new settings.
    assert entry.state is config_entries.ConfigEntryState.LOADED
    assert entry.runtime_data.update_interval == timedelta(seconds=30)
    assert entry.runtime_data.request_timeout == 25

    thermostat = hass.states.get("climate.nefit")
    assert thermostat.attributes["min_temp"] == 12
    assert thermostat.attributes["max_temp"] == 25


@patch("custom_components.nefiteasy.coordinator.NefitCore")
async def test_options_flow_max_below_min(mock_class, hass: HomeAssistant):
    """Test the maximum temperature must be above the minimum."""
    client = ClientMock(mock_class)
    mock_class.return_value = client

    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {**OPTIONS, "min_temp": 25, "max_temp": 20}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"max_temp": "max_below_min"}
    assert entry.options == {}
