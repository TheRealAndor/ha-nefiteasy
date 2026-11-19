"""Base entity for Nefit Easy thermostats."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_NAME, CONF_SERIAL, DOMAIN
from .coordinator import NefitEasy
from .models import NefitEntityDescription


def nefit_device_info(data: MappingProxyType[str, Any]) -> DeviceInfo:
    """Return the device info of the thermostat."""
    return DeviceInfo(
        identifiers={(DOMAIN, data[CONF_SERIAL])},
        name=data[CONF_NAME],
        manufacturer="Bosch",
    )


class NefitEntity(CoordinatorEntity[NefitEasy]):
    """Representation of a Nefit entity."""

    _attr_has_entity_name = True

    entity_description: NefitEntityDescription

    def __init__(
        self,
        entity_description: NefitEntityDescription,
        client: NefitEasy,
        data: MappingProxyType[str, Any],
    ) -> None:
        """Initialize the entity."""
        super().__init__(client)

        self.entity_description = entity_description

        self._client = client
        self._config = data
        self._attr_unique_id = (
            f"{client.nefit.serial_number}_{self.entity_description.key}"
        )
        self._attr_device_info = nefit_device_info(data)

    async def async_added_to_hass(self) -> None:
        """Add required data to coordinator."""
        await self._client.add_key(self.entity_description)
        await super().async_added_to_hass()

    def get_endpoint(self) -> Any:
        """Get end point."""
        return self.entity_description.url
