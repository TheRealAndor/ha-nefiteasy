"""Tests of the nefiteasy diagnostics."""

from homeassistant.core import HomeAssistant

from custom_components.nefiteasy.diagnostics import (
    REDACTED,
    async_get_config_entry_diagnostics,
)


async def test_diagnostics(hass: HomeAssistant, nefit_config, nefit_wrapper):
    """Test diagnostics contain the connection state and hide secrets."""
    diagnostics = await async_get_config_entry_diagnostics(hass, nefit_config)

    entry = diagnostics["entry"]
    assert entry["serial"] == REDACTED
    assert entry["accesskey"] == REDACTED
    assert entry["password"] == REDACTED
    assert entry["name"] == "Nefit"

    connection = diagnostics["connection"]
    assert connection["connected_state"] == "connection_verified"
    assert connection["cloud_connected"] is True
    assert connection["request_timeout_seconds"] == 20.0

    assert "/system/appliance/displaycode" in diagnostics["polled_endpoints"]
    assert diagnostics["data"]["temp_setpoint"] is not None

    # Secrets must not appear anywhere in the output.
    text = str(diagnostics)
    for secret in ("123456789", "myAccessKey", "myPass"):
        assert secret not in text


async def test_diagnostics_redacts_presence_names(
    hass: HomeAssistant, nefit_config, nefit_wrapper_precense
):
    """Test the names of presence detection phones are hidden."""
    diagnostics = await async_get_config_entry_diagnostics(hass, nefit_config)

    names = {k: v for k, v in diagnostics["data"].items() if k.endswith("_name")}
    assert names
    assert set(names.values()) == {REDACTED}
