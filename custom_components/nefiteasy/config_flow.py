"""Config flow for Nefit Easy Bosch Thermostat integration."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
import logging
from typing import Any

from aionefit import NefitCore
from homeassistant import core, exceptions
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)
import voluptuous as vol

from .const import (
    AUTH_ERROR_CREDENTIALS,
    AUTH_ERROR_PASSWORD,
    CONF_ACCESSKEY,
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_REQUEST_TIMEOUT,
    CONF_SCAN_INTERVAL,
    CONF_SERIAL,
    CONF_TEMP_STEP,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TEMP_STEP,
    DOMAIN,
    MAX_REQUEST_TIMEOUT,
    MAX_SCAN_INTERVAL,
    MIN_REQUEST_TIMEOUT,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class NefitConnection:
    """Test the connection to NefitEasy and check read to verify description of messages."""

    def __init__(self, serial_number: str, access_key: str, password: str) -> None:
        """Initialize."""
        self.nefit = NefitCore(
            serial_number=serial_number,
            access_key=access_key,
            password=password,
        )

        self.nefit.failed_auth_handler = self.failed_auth_handler
        self.nefit.no_content_callback = self.no_content_callback
        self.nefit.session_end_callback = self.session_end_callback

        self.auth_failure = None

    async def failed_auth_handler(self, event: str) -> None:
        """Report failed auth."""
        if event == "auth_error_password":
            self.auth_failure = AUTH_ERROR_PASSWORD
            _LOGGER.debug("Invalid password for connecting to Bosch cloud.")
        else:
            self.auth_failure = AUTH_ERROR_CREDENTIALS
            _LOGGER.debug(
                "Invalid credentials (serial or accesskey) for connecting to Bosch cloud."
            )

        self.nefit.xmppclient.connected_event.set()

    async def session_end_callback(self) -> None:
        """Session end."""

    async def no_content_callback(self, data: Any) -> None:
        """No content."""

    async def validate_connect(self) -> None:
        """Test if we can connect and communicate with the device."""

        await self.nefit.connect()
        try:
            await asyncio.wait_for(
                self.nefit.xmppclient.connected_event.wait(), timeout=10.0
            )
        except asyncio.TimeoutError as ex:
            self.nefit.xmppclient.cancel_connection_attempt()
            raise CannotConnect from ex

        if self.auth_failure == AUTH_ERROR_CREDENTIALS:
            raise InvalidCredentials

        self.nefit.get("/gateway/brandID")
        try:
            await asyncio.wait_for(
                self.nefit.xmppclient.message_event.wait(), timeout=10.0
            )
        except asyncio.TimeoutError as ex:
            await self.nefit.disconnect()
            raise CannotCommunicate from ex

        self.nefit.xmppclient.message_event.clear()

        await self.nefit.disconnect()

        if self.auth_failure == AUTH_ERROR_PASSWORD:
            raise InvalidPassword


async def _validate_nefiteasy_connection(
    hass: core.HomeAssistant, data: dict[str, Any]
) -> None:
    """Validate the user input allows us to connect."""
    conn = NefitConnection(
        data.get(CONF_SERIAL), data[CONF_ACCESSKEY], data[CONF_PASSWORD]
    )

    await conn.validate_connect()


async def _async_validate_input(
    hass: core.HomeAssistant, data: dict[str, Any]
) -> dict[str, str]:
    """Test the credentials and return the errors for the form."""
    try:
        await _validate_nefiteasy_connection(hass, data)
    except CannotConnect:
        return {"base": "cannot_connect"}
    except CannotCommunicate:
        return {"base": "cannot_communicate"}
    except InvalidCredentials:
        return {"base": "invalid_credentials"}
    except InvalidPassword:
        return {"base": "invalid_password"}
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception("Unexpected error while testing the connection")
        return {"base": "unknown"}
    return {}


class NefitEasyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Nefit Easy Bosch Thermostat."""

    VERSION = 1

    def __init__(self) -> None:
        """Init nefit easy config flow."""
        self._serial: str | None = None
        self._accesskey: str | None = None
        self._password: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step when user initializes an integration."""
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_SERIAL])
            self._abort_if_unique_id_configured()

            errors = await _async_validate_input(self.hass, user_input)

            if not errors:
                self._serial = user_input[CONF_SERIAL]
                self._accesskey = user_input[CONF_ACCESSKEY]
                self._password = user_input[CONF_PASSWORD]

                return await self.async_step_options()

        schema = vol.Schema(
            {
                vol.Required(CONF_SERIAL): cv.string,
                vol.Required(CONF_ACCESSKEY): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step to set options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {
                CONF_SERIAL: self._serial,
                CONF_ACCESSKEY: self._accesskey,
                CONF_PASSWORD: self._password,
                CONF_MIN_TEMP: user_input[CONF_MIN_TEMP],
                CONF_MAX_TEMP: user_input[CONF_MAX_TEMP],
                CONF_TEMP_STEP: user_input[CONF_TEMP_STEP],
                CONF_NAME: "Nefit",
            }

            return self.async_create_entry(title=f"{self._serial}", data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_MIN_TEMP, default=DEFAULT_MIN_TEMP): cv.positive_int,
                vol.Required(CONF_MAX_TEMP, default=DEFAULT_MAX_TEMP): cv.positive_int,
                vol.Required(CONF_TEMP_STEP, default=DEFAULT_TEMP_STEP): cv.small_float,
            }
        )

        return self.async_show_form(
            step_id="options", data_schema=schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> NefitEasyOptionsFlow:
        """Return the options flow."""
        return NefitEasyOptionsFlow()

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauthentication when the Bosch cloud rejects the credentials."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a new access key and password."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            data = {
                CONF_SERIAL: reauth_entry.data[CONF_SERIAL],
                CONF_ACCESSKEY: user_input[CONF_ACCESSKEY],
                CONF_PASSWORD: user_input[CONF_PASSWORD],
            }
            errors = await _async_validate_input(self.hass, data)

            if not errors:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={
                        CONF_ACCESSKEY: user_input[CONF_ACCESSKEY],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ACCESSKEY, default=reauth_entry.data[CONF_ACCESSKEY]
                ): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
            }
        )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=schema,
            errors=errors,
            description_placeholders={"serial": reauth_entry.data[CONF_SERIAL]},
        )


def _seconds(minimum: int, maximum: int) -> NumberSelector:
    """Return a number field in seconds."""
    return NumberSelector(
        NumberSelectorConfig(
            min=minimum,
            max=maximum,
            step=1,
            mode=NumberSelectorMode.BOX,
            unit_of_measurement=UnitOfTime.SECONDS,
        )
    )


def _temperature(minimum: float, maximum: float, step: float) -> NumberSelector:
    """Return a number field in degrees Celsius."""
    return NumberSelector(
        NumberSelectorConfig(
            min=minimum,
            max=maximum,
            step=step,
            mode=NumberSelectorMode.BOX,
            unit_of_measurement=UnitOfTemperature.CELSIUS,
        )
    )


OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MIN_TEMP): _temperature(5, 35, 1),
        vol.Required(CONF_MAX_TEMP): _temperature(5, 35, 1),
        vol.Required(CONF_TEMP_STEP): _temperature(0.1, 1, 0.1),
        vol.Required(CONF_SCAN_INTERVAL): _seconds(
            MIN_SCAN_INTERVAL, MAX_SCAN_INTERVAL
        ),
        vol.Required(CONF_REQUEST_TIMEOUT): _seconds(
            MIN_REQUEST_TIMEOUT, MAX_REQUEST_TIMEOUT
        ),
    }
)


class NefitEasyOptionsFlow(OptionsFlow):
    """Change the settings of a thermostat after setup."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show and store the settings."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input[CONF_MIN_TEMP] >= user_input[CONF_MAX_TEMP]:
                errors[CONF_MAX_TEMP] = "max_below_min"
            else:
                return self.async_create_entry(
                    data={
                        CONF_MIN_TEMP: int(user_input[CONF_MIN_TEMP]),
                        CONF_MAX_TEMP: int(user_input[CONF_MAX_TEMP]),
                        CONF_TEMP_STEP: float(user_input[CONF_TEMP_STEP]),
                        CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
                        CONF_REQUEST_TIMEOUT: int(user_input[CONF_REQUEST_TIMEOUT]),
                    }
                )

        entry = self.config_entry
        current = {
            key: entry.options.get(key, entry.data.get(key, default))
            for key, default in (
                (CONF_MIN_TEMP, DEFAULT_MIN_TEMP),
                (CONF_MAX_TEMP, DEFAULT_MAX_TEMP),
                (CONF_TEMP_STEP, DEFAULT_TEMP_STEP),
                (CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                (CONF_REQUEST_TIMEOUT, DEFAULT_REQUEST_TIMEOUT),
            )
        }

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, user_input or current
            ),
            errors=errors,
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class CannotCommunicate(exceptions.HomeAssistantError):
    """Error to indicate we cannot communicate."""


class InvalidCredentials(exceptions.HomeAssistantError):
    """Error to indicate we cannot verify credentials."""


class InvalidPassword(exceptions.HomeAssistantError):
    """Error to indicate we cannot verify password."""
