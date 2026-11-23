"""Support for Bosch home thermostats."""

from __future__ import annotations

import asyncio
import logging
from types import MappingProxyType
from typing import Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    CONF_TEMP_STEP,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DEFAULT_TEMP_STEP,
)
from .coordinator import NefitEasy, NefitEasyConfigEntry
from .entity import nefit_device_info

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = (
    ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
)

# supported operating modes (preset mode)
OPERATION_MANUAL = "Manual"
OPERATION_CLOCK = "Clock"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: NefitEasyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Climate setup for nefit easy."""
    entities = []

    client = config_entry.runtime_data

    entities.append(NefitThermostat(client, config_entry.data))

    async_add_entities(entities, update_before_add=True)


class NefitThermostat(CoordinatorEntity[NefitEasy], ClimateEntity):
    """Representation of a NefitThermostat device."""

    # The thermostat is the main feature of the device: it takes the device
    # name, for example "Nefit".
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, client: NefitEasy, data: MappingProxyType[str, Any]) -> None:
        """Initialize the thermostat."""
        super().__init__(client)

        self._config = data
        self._client = client

        self._unit_of_measurement = UnitOfTemperature.CELSIUS
        self._hvac_modes = [HVACMode.HEAT]

        self._attr_unique_id = "{}_{}".format(client.nefit.serial_number, "climate")
        self._attr_device_info = nefit_device_info(data)

    def _setting(self, key: str, default: Any) -> Any:
        """Return a setting of the options flow or the setup."""
        return NefitEasy.setting(self.coordinator.config_entry, key, default)

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def target_temperature_step(self) -> float:
        """Return target temperature step."""
        return float(self._setting(CONF_TEMP_STEP, DEFAULT_TEMP_STEP))

    @property
    def native_temperature_unit(self) -> str:
        """Return the unit of measurement."""
        return self._unit_of_measurement

    def _temperature(self, key: str) -> float | None:
        """Return a temperature, or None before the first status arrived.

        The platforms are set up before the first poll, because the entities
        register the endpoints to poll when they are added.
        """
        value = self.coordinator.data.get(key)
        return None if value is None else float(value)

    @property
    def native_current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._temperature("inhouse_temperature")

    @property
    def native_target_temperature(self) -> float | None:
        """Return target temperature."""
        return self._temperature("temp_setpoint")

    if not hasattr(ClimateEntity, "native_current_temperature"):
        # Home Assistant before 2026.11 only knows the non-native names.
        temperature_unit = native_temperature_unit
        current_temperature = native_current_temperature
        target_temperature = native_target_temperature

    @property
    def hvac_modes(self) -> list[str]:
        """List of available modes."""
        return self._hvac_modes

    @property
    def hvac_mode(self) -> str:
        """Return hvac mode."""
        return HVACMode.HEAT

    @property
    def hvac_action(self) -> str:
        """Return the current running hvac operation if supported."""
        if (
            self.coordinator.data.get("boiler_indicator") == "CH"
        ):  # HW (hot water) is not for climate
            return HVACAction.HEATING

        return HVACAction.IDLE

    @property
    def preset_modes(self) -> list[str]:
        """Return available preset modes."""
        return [OPERATION_MANUAL, OPERATION_CLOCK]

    @property
    def preset_mode(self) -> str:
        """Return the current preset mode."""
        if self.coordinator.data.get("user_mode") == "clock":
            return OPERATION_CLOCK

        return OPERATION_MANUAL

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the nefit specific state attributes."""
        return {
            "last_update": self.coordinator.data.get("last_update"),
            "boiler_indicator": self.coordinator.data.get("boiler_indicator"),
        }

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        return float(self._setting(CONF_MIN_TEMP, DEFAULT_MIN_TEMP))

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        return float(self._setting(CONF_MAX_TEMP, DEFAULT_MAX_TEMP))

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new target operation mode."""
        _LOGGER.debug("set_preset_mode called mode=%s", preset_mode)
        if preset_mode == OPERATION_CLOCK:
            new_mode = "clock"
        else:
            new_mode = "manual"

        self._client.nefit.set_usermode(new_mode)
        await asyncio.wait_for(
            self._client.nefit.xmppclient.message_event.wait(),
            timeout=self._client.request_timeout,
        )
        self._client.nefit.xmppclient.message_event.clear()

        self._client.nefit.get("/ecus/rrc/uiStatus")
        await self._client.update_ui_status_later(2)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        _LOGGER.debug("set_temperature called (temperature=%s)", temperature)
        self._client.nefit.set_temperature(temperature)
        await asyncio.wait_for(
            self._client.nefit.xmppclient.message_event.wait(),
            timeout=self._client.request_timeout,
        )
        self._client.nefit.xmppclient.message_event.clear()

        self._client.nefit.get("/ecus/rrc/uiStatus")
