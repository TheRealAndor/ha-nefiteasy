"""Connection status of the Bosch cloud for Nefit Easy thermostats."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_CONNECTION_STATUS
from .models import NefitBinarySensorEntityDescription
from .nefit_entity import NefitEntity

CLOUD_CONNECTION = NefitBinarySensorEntityDescription(
    key="cloud_connection",
    name="Bosch cloud connection",
    device_class=BinarySensorDeviceClass.CONNECTIVITY,
    entity_category=EntityCategory.DIAGNOSTIC,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Binary sensor platform setup for nefit easy."""
    client = hass.data[DOMAIN][config_entry.entry_id]["client"]
    async_add_entities(
        [NefitCloudConnection(CLOUD_CONNECTION, client, config_entry.data)]
    )


class NefitCloudConnection(NefitEntity, BinarySensorEntity):
    """Whether Home Assistant currently gets answers through the Bosch cloud.

    Unlike the other entities it stays available during an outage; showing
    the outage and its reason is its purpose.
    """

    entity_description: NefitBinarySensorEntityDescription

    async def async_added_to_hass(self) -> None:
        """Also listen for connection changes outside regular updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_CONNECTION_STATUS.format(self._client.serial),
                self.async_write_ha_state,
            )
        )

    @property
    def available(self) -> bool:
        """Always available, also when updates fail."""
        return True

    @property
    def is_on(self) -> bool:
        """Return true when the last update got answers from the thermostat."""
        return self._client.cloud_connected

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return details about the connection."""
        client = self._client
        return {
            "last_success": client.last_success_at,
            "disconnected_since": client.disconnected_since,
            "last_error": client.last_error,
            "last_error_at": client.last_error_at,
            "reconnects": client.reconnect_count,
        }
