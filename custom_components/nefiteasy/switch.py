"""Support for Bosch home thermostats."""

from __future__ import annotations

import asyncio
import logging
from types import MappingProxyType
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import HOT_WATER_CLOCK, HOT_WATER_MANUAL, HOT_WATER_MODE, SWITCHES
from .coordinator import NefitEasy, NefitEasyConfigEntry
from .entity import NefitEntity
from .models import NefitEntityDescription, NefitSwitchEntityDescription

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
        elif description.key == "hot_water_follows_program":
            entities.append(NefitHotWaterFollowsProgram(description, client, data))
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


class NefitHotWaterSwitch(NefitSwitch):
    """Base for the hot water switches.

    They read the hot water endpoints by their own keys, and ask for the
    status again after a change so the hot water state follows quickly.
    """

    async def async_added_to_hass(self) -> None:
        """Poll the hot water endpoints."""
        for description in (HOT_WATER_MANUAL, HOT_WATER_CLOCK, HOT_WATER_MODE):
            await self._client.add_key(description)
        await super().async_added_to_hass()

    def _value(self) -> Any:
        """Return the value the switch shows."""
        raise NotImplementedError

    @property
    def is_on(self) -> bool:
        """Get whether the switch is in on state."""
        return self._value() == self._on_value

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on and refresh the hot water state."""
        await super().async_turn_on(**kwargs)
        await self._client.update_ui_status_later(3)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off and refresh the hot water state."""
        await super().async_turn_off(**kwargs)
        await self._client.update_ui_status_later(3)


class NefitHotWater(NefitHotWaterSwitch):
    """ "Snel warm water" in the Nefit Easy app.

    The thermostat keeps one value per user mode, so the switch writes and
    reads the one of the current mode. In the clock mode the program sets it
    at every switchpoint. When hot water does not follow the program
    (comfort), hot water is always on and the switch has no effect; the app
    hides it then, here it is unavailable.
    """

    def _description(self) -> NefitEntityDescription:
        """Return the endpoint of the current user mode."""
        if self.coordinator.data.get("user_mode") == "clock":
            return HOT_WATER_CLOCK
        return HOT_WATER_MANUAL

    def _value(self) -> Any:
        """Return the value of the current user mode."""
        return self.coordinator.data.get(self._description().key)

    def get_endpoint(self) -> str | None:
        """Get end point."""
        return self._description().url

    @property
    def available(self) -> bool:
        """Unavailable while hot water is always on (comfort)."""
        return (
            super().available
            and self.coordinator.data.get(HOT_WATER_MODE.key) != "comfort"
        )


class NefitHotWaterFollowsProgram(NefitHotWaterSwitch):
    """ "Volgens programma" in the Nefit Easy app.

    On (eco) follows the program and the hot water switch; off (comfort)
    keeps hot water on all the time.
    """

    def __init__(
        self,
        entity_description: NefitSwitchEntityDescription,
        client: NefitEasy,
        data: MappingProxyType[str, Any],
    ) -> None:
        """Init the switch with the values of the hot water mode."""
        super().__init__(entity_description, client, data, "eco", "comfort")

    def _value(self) -> Any:
        """Return the hot water mode."""
        return self.coordinator.data.get(HOT_WATER_MODE.key)

    def get_endpoint(self) -> str | None:
        """Get end point."""
        return HOT_WATER_MODE.url
