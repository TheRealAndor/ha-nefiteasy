"""Support for first generation Bosch smart home thermostats: Nefit Easy, Junkers CT100 etc."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .const import CONF_SERIAL, STATE_CONNECTION_VERIFIED, STATE_ERROR_AUTH
from .coordinator import NefitEasy, NefitEasyConfigEntry

__all__ = ["NefitEasy", "NefitEasyConfigEntry"]

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
]


async def async_setup_entry(hass: HomeAssistant, entry: NefitEasyConfigEntry) -> bool:
    """Set up a Nefit Easy thermostat from a config entry."""
    client = NefitEasy(hass, entry)

    await client.connect()
    if client.connected_state == STATE_ERROR_AUTH:
        raise ConfigEntryAuthFailed(
            f"The Bosch cloud rejected the credentials of {entry.data[CONF_SERIAL]}"
        )
    if client.connected_state != STATE_CONNECTION_VERIFIED:
        await client.shutdown("Setup failed")
        raise ConfigEntryNotReady(
            f"Unable to verify connection to {entry.data[CONF_SERIAL]}: "
            f"{client.last_connect_error or client.connected_state}"
        )

    entry.runtime_data = client

    # The connection was just verified; let the connection sensor start as
    # connected instead of waiting for the first poll.
    client.record_update_result(None)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # The options flow changes the poll interval, the timeout and the
    # temperature limits; reload so everything uses the new values.
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    # The entities register the endpoints to poll when they are added, so the
    # first full poll runs after the platforms are set up.
    await client.async_refresh()

    return True


async def _async_reload_entry(hass: HomeAssistant, entry: NefitEasyConfigEntry) -> None:
    """Reload the entry after its options changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: NefitEasyConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        await entry.runtime_data.shutdown("Unload entry")

    return unload_ok
