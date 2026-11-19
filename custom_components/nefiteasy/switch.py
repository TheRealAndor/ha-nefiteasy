"""Support for Bosch home thermostats."""

from __future__ import annotations

import asyncio
import logging
from types import MappingProxyType
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import SWITCHES
from .coordinator import NefitEasy, NefitEasyConfigEntry
from .entity import NefitEntity
from .models import NefitSwitchEntityDescription

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: NefitEasyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Switch setup for nefit easy."""
    entities: list[NefitEntity] = []

    client = config_entry.runtime_data
    data = config_entry.data

    presence_description = None

    for description in SWITCHES:
        if description.key == "hot_water":
            entities.append(NefitHotWater(description, client, data))
        elif description.key == "lockui":
            entities.append(NefitSwitch(description, client, data, "true", "false"))
        elif description.key == "weather_dependent":
            entities.append(NefitSwitch(description, client, data, "weather", "room"))
        elif description.key == "home_entrance_detection":
            presence_description = description
        else:
            entities.append(NefitSwitch(description, client, data))

    # Values arrive with the coordinator refresh that runs right after all
    # platforms are set up; refreshing here would make platform setup wait
    # for a complete poll of the Bosch cloud.
    async_add_entities(entities)

    if presence_description is not None:
        # Probing the presence profiles takes up to 20 sequential cloud
        # requests. Do it in the background so platform setup is not held
        # up ("Setup of switch platform nefiteasy is taking over 10 seconds")
        # and add the switches once they are known.
        config_entry.async_create_background_task(
            hass,
            setup_home_entrance_detection(
                async_add_entities,
                client,
                data,
                presence_description.key,
                presence_description.name,
                presence_description.icon,
            ),
            name=f"nefiteasy presence detection {config_entry.entry_id}",
        )


async def setup_home_entrance_detection(
    async_add_entities: AddEntitiesCallback,
    client: NefitEasy,
    data: MappingProxyType[str, Any],
    basekey: str,
    basename: str,
    baseicon: str,
) -> None:
    """Home entrance detection setup."""
    entities: list[NefitEntity] = []
    endpoint = "/ecus/rrc/homeentrancedetection"

    for i in range(0, 10):
        try:
            name = await client.async_init_presence(endpoint, i)
        except asyncio.TimeoutError:
            # One slow answer should not drop the other profiles.
            _LOGGER.debug("No answer for presence profile %s, skipping.", i)
            continue
        except Exception as ex:  # connection lost during probing
            _LOGGER.debug("Stopped probing presence profiles at %s: %r", i, ex)
            break

        if name is not None:
            description = NefitSwitchEntityDescription(
                key=f"presence{i}_detected",
                name=basename.format(name),
                url=f"{endpoint}/userprofile{i}/detected",
                icon=baseicon,
            )
            entities.append(NefitSwitch(description, client, data))

    if entities:
        async_add_entities(entities)
        # Fetch the values of the new switches now instead of at the next poll.
        await client.async_request_refresh()


class NefitSwitch(NefitEntity, SwitchEntity):
    """Representation of a NefitSwitch entity."""

    entity_description: NefitSwitchEntityDescription

    def __init__(
        self,
        entity_description: NefitSwitchEntityDescription,
        client: NefitEasy,
        data: MappingProxyType[str, Any],
        on_value: str = "on",
        off_value: str = "off",
    ) -> None:
        """Init Nefit Switch."""
        super().__init__(entity_description, client, data)

        self._on_value = on_value
        self._off_value = off_value

    @property
    def is_on(self) -> bool:
        """Get whether the switch is in on state."""
        return bool(
            self.coordinator.data.get(self.entity_description.key) == self._on_value
        )

    @property
    def assumed_state(self) -> bool:
        """Return true if we do optimistic updates."""
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        self._client.nefit.put_value(self.get_endpoint(), self._on_value)

        self._client.nefit.get(self.get_endpoint())

        _LOGGER.debug(
            "Switch Nefit %s to %s, endpoint=%s.",
            self.entity_description.key,
            self._on_value,
            self.get_endpoint(),
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        self._client.nefit.put_value(self.get_endpoint(), self._off_value)

        self._client.nefit.get(self.get_endpoint())

        _LOGGER.debug(
            "Switch Nefit %s to %s, endpoint=%s.",
            self.entity_description.key,
            self._off_value,
            self.get_endpoint(),
        )


class NefitHotWater(NefitSwitch):
    """Class for nefit hot water entity."""

    def get_endpoint(self) -> str:
        """Get end point."""
        endpoint = (
            "dhwOperationClockMode"
            if self.coordinator.data.get("user_mode") == "clock"
            else "dhwOperationManualMode"
        )
        return "/dhwCircuits/dhwA/" + endpoint
