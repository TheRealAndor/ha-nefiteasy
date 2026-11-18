"""Diagnostics support for Nefit Easy."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_ACCESSKEY, CONF_PASSWORD, CONF_SERIAL, DOMAIN

TO_REDACT = {CONF_SERIAL, CONF_ACCESSKEY, CONF_PASSWORD}
REDACTED = "**REDACTED**"


def _aionefit_version() -> str | None:
    """Return the installed aionefit version (reads package metadata)."""
    try:
        return version("aionefit-updated")
    except PackageNotFoundError:
        return None


def _redact_values(data: dict[str, Any]) -> dict[str, Any]:
    """Hide personal values: the names of the presence detection phones."""
    return {
        key: (
            REDACTED if key.startswith("presence") and key.endswith("_name") else value
        )
        for key, value in data.items()
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    client = hass.data[DOMAIN][entry.entry_id]["client"]

    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "aionefit_version": await hass.async_add_executor_job(_aionefit_version),
        "connection": client.connection_diagnostics(),
        "polled_endpoints": client.registered_urls,
        "status_keys": client.status_keys,
        "data": _redact_values(dict(client.data or {})),
    }
