"""Connection status of the Bosch cloud for Nefit Easy thermostats."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    HOT_WATER_NEXT_SWITCHPOINT,
    HOT_WATER_PROGRAM,
    HOT_WATER_STATE,
    SIGNAL_CONNECTION_STATUS,
)
from .coordinator import NefitEasyConfigEntry
from .entity import NefitEntity
from .models import NefitBinarySensorEntityDescription

CLOUD_CONNECTION = NefitBinarySensorEntityDescription(
    key="cloud_connection",
    name="Bosch cloud connection",
    device_class=BinarySensorDeviceClass.CONNECTIVITY,
    entity_category=EntityCategory.DIAGNOSTIC,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: NefitEasyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Binary sensor platform setup for nefit easy."""
    client = config_entry.runtime_data
    async_add_entities(
        [
            NefitCloudConnection(CLOUD_CONNECTION, client, config_entry.data),
            NefitHotWaterProgram(HOT_WATER_PROGRAM, client, config_entry.data),
            NefitHotWaterState(HOT_WATER_STATE, client, config_entry.data),
        ]
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


class NefitHotWaterState(NefitEntity, BinarySensorEntity):
    """Whether hot water is on, as the thermostat reports it (uiStatus DHW)."""

    entity_description: NefitBinarySensorEntityDescription

    @property
    def is_on(self) -> bool | None:
        """Return true when hot water is on."""
        value = self.coordinator.data.get(self.entity_description.key)
        if value is None:
            return None
        return value == "on"


def _switchpoint(value: Any) -> dict[str, Any] | None:
    """Return the first switchpoint of a dhw(Current|Next)Switchpoint answer."""
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0]
    return None


def _switchpoint_time(point: dict[str, Any]) -> str | None:
    """Return day and time of a switchpoint, for example "Fr 07:00"."""
    minutes = point.get("t")
    if not isinstance(minutes, int):
        return None
    return f"{point.get('d')} {minutes // 60:02d}:{minutes % 60:02d}"


class NefitHotWaterProgram(NefitEntity, BinarySensorEntity):
    """Whether the hot water program asks for hot water now.

    Only meaningful when hot water follows the program; otherwise the
    thermostat reports no switchpoints and the state is unknown.
    """

    entity_description: NefitBinarySensorEntityDescription

    async def async_added_to_hass(self) -> None:
        """Also poll the next switchpoint."""
        await self._client.add_key(HOT_WATER_NEXT_SWITCHPOINT)
        await super().async_added_to_hass()

    @property
    def is_on(self) -> bool | None:
        """Return true when the current switchpoint turns hot water on."""
        point = _switchpoint(self.coordinator.data.get(self.entity_description.key))
        if point is None:
            return None
        return point.get("dhw") == "on"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return when the current period started and what comes next."""
        current = _switchpoint(self.coordinator.data.get(self.entity_description.key))
        upcoming = _switchpoint(
            self.coordinator.data.get(HOT_WATER_NEXT_SWITCHPOINT.key)
        )
        return {
            "since": _switchpoint_time(current) if current else None,
            "next_switchpoint": _switchpoint_time(upcoming) if upcoming else None,
            "next_state": upcoming.get("dhw") if upcoming else None,
        }
