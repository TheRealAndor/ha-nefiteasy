"""Support for first generation Bosch smart home thermostats: Nefit Easy, Junkers CT100 etc."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
import re
from typing import Any

from aionefit import NefitCore
from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
import slixmpp

from .const import (
    CONF_ACCESSKEY,
    CONF_PASSWORD,
    CONF_SERIAL,
    DOMAIN,
    SIGNAL_CONNECTION_STATUS,
    STATE_CONNECTED,
    STATE_CONNECTION_VERIFIED,
    STATE_ERROR_AUTH,
    STATE_INIT,
    short,
)
from .models import NefitEntityDescription

_LOGGER = logging.getLogger(__name__)


class _SuppressLegacyXmppWarning(logging.Filter):
    """Hide slixmpp's 'Legacy XMPP 0.9 protocol detected.' warning.

    The Bosch/Nefit XMPP server does not send a version attribute in its
    stream header, so slixmpp logs this warning on every (re)connect. It is
    harmless: slixmpp falls back to legacy handling and the connection works.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        return "Legacy XMPP 0.9 protocol detected" not in record.getMessage()


logging.getLogger("slixmpp.basexmpp").addFilter(_SuppressLegacyXmppWarning())


DOMAINS = ["binary_sensor", "climate", "select", "sensor", "switch", "number"]

# Seconds to wait for the XMPP session and for the first test message.
CONNECT_TIMEOUT = 29.0
# Seconds to wait for the answer to a single GET request. The Bosch cloud is
# often slow without being down: measurements in ksya/ha-nefiteasy#462 showed
# replies of 9-20 s on sessions that kept working. With a shorter timeout each
# of those counts as a lost session and triggers a retry or a reconnect.
REQUEST_TIMEOUT = 20.0
# Seconds to wait for a stale transport to close before reconnecting.
TEARDOWN_TIMEOUT = 5.0
# Name slixmpp uses for its repeating whitespace keepalive. Scheduling it a
# second time raises "There is already a scheduled event of name: ...".
KEEPALIVE_EVENT = "Whitespace Keepalive"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the nefiteasy component."""
    hass.data.setdefault(DOMAIN, {})

    hass.data[DOMAIN][entry.entry_id] = {}

    credentials = dict(entry.data)
    client = NefitEasy(hass, credentials)

    await client.connect()
    if client.connected_state == STATE_CONNECTION_VERIFIED:
        hass.data[DOMAIN][entry.entry_id]["client"] = client
    else:
        raise ConfigEntryNotReady(
            f"Unable to verify connection to {credentials[CONF_SERIAL]}, "
            f"state: {client.connected_state}"
        )

    # The connection was just verified; let the connection sensor start as
    # connected instead of waiting for the first poll.
    client.record_update_result(None)

    await hass.config_entries.async_forward_entry_setups(entry, DOMAINS)

    await client.async_refresh()

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload nefit easy component."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, DOMAINS)

    if unload_ok:
        client = hass.data[DOMAIN][entry.entry_id]["client"]

        await client.shutdown("Unload entry")

        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class NefitEasy(DataUpdateCoordinator):
    """Supporting class for nefit easy."""

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        """Initialize nefit easy component."""
        _LOGGER.debug("Initialize Nefit class")

        self._data: dict[str, Any] = {}  # stores device states and values
        self._event = asyncio.Event()
        self._lock = asyncio.Lock()
        self._connect_lock = asyncio.Lock()
        self.last_connect_error: str | None = None
        # Connection health, shown by the connection binary sensor and in the
        # diagnostics download.
        self.cloud_connected = False
        self.last_error: str | None = None
        self.last_error_at: datetime | None = None
        self.last_success_at: datetime | None = None
        self.disconnected_since: datetime | None = None
        self.reconnect_count = 0
        self._ever_verified = False
        self.hass = hass
        self.connected_state = STATE_INIT
        self.expected_end = False
        self.is_connecting = False
        self.serial = config[CONF_SERIAL]
        self._config = config
        self._request: str = ""

        self.nefit = NefitCore(
            serial_number=config[CONF_SERIAL],
            access_key=config[CONF_ACCESSKEY],
            password=config[CONF_PASSWORD],
            message_callback=self.parse_message,
        )

        self.nefit.failed_auth_handler = self.failed_auth_handler
        self.nefit.no_content_callback = self.no_content_callback
        self.nefit.session_end_callback = self.session_end_callback

        self._urls: dict[str, Any] = {}
        self._status_keys: dict[str, Any] = {}

        update_interval = timedelta(seconds=60)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

        # Entities may be added before the first refresh has finished; give
        # them an (empty) dict to read from instead of None.
        self.data = self._data

    async def add_key(self, entity_description: NefitEntityDescription) -> None:
        """Add key to list of endpoints."""
        async with self._lock:
            if entity_description.url is not None:
                self._urls[entity_description.url] = {
                    "key": entity_description.key,
                    short: entity_description.short,
                }
            elif entity_description.short is not None:
                self._status_keys[entity_description.short] = entity_description.key

    async def _async_teardown_transport(self) -> None:
        """Close a lingering XMPP connection before opening a new one.

        Calling connect() on a client that still has an open transport
        starts a second session on the same stream object. Its
        session_start then tries to schedule the whitespace keepalive while
        the old one is still registered (ValueError in slixmpp), and when
        the orphaned transport closes later it fires session_end on the
        stream and drops the new, working session too.
        """
        client = self.nefit.xmppclient

        # A connection attempt from an earlier, timed-out connect() may still
        # be retrying in the background. Stop it so it cannot start a session
        # alongside the one we are about to open.
        client.cancel_connection_attempt()

        if client.is_connected():
            _LOGGER.debug("Closing stale XMPP connection before reconnecting.")
            disconnected = getattr(client, "disconnected", None)
            client.abort()
            if isinstance(disconnected, asyncio.Future):
                try:
                    await asyncio.wait_for(
                        asyncio.shield(disconnected), timeout=TEARDOWN_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    _LOGGER.debug("Stale connection did not report closing in time.")
            else:
                # Let the loop run connection_lost() for the aborted transport
                # (scheduled with call_soon, so a few loop iterations suffice).
                for _ in range(3):
                    await asyncio.sleep(0)

        # Safety net: slixmpp removes the keepalive on 'disconnected'. If that
        # did not happen for any reason, drop it here so the next
        # session_start can schedule it again. A no-op when absent.
        if KEEPALIVE_EVENT in getattr(client, "scheduled_events", {}):
            _LOGGER.debug("Removing leftover keepalive from previous session.")
            client.cancel_schedule(KEEPALIVE_EVENT)

    async def connect(self) -> None:
        """Connect to nefit easy."""
        _LOGGER.debug("Start connecting.")
        if self._connect_lock.locked():
            # Another caller (poll or session_end) is already connecting.
            # Wait for it instead of starting a parallel attempt, and use
            # its result rather than trying again straight away.
            _LOGGER.debug("Connection procedure is already running, waiting.")
            async with self._connect_lock:
                return

        async with self._connect_lock:
            _LOGGER.debug("Set is connecting to true")
            self.is_connecting = True
            self.connected_state = STATE_INIT
            self.last_connect_error = None
            try:
                await self._async_teardown_transport()

                # Events from a previous session may still be set; without
                # clearing them the waits below would return instantly and
                # verify against a dead transport. Clear BEFORE connecting
                # so a genuine handshake can set them again afterwards.
                self.nefit.xmppclient.connected_event.clear()
                self.nefit.xmppclient.message_event.clear()
                await self.nefit.connect()
                _LOGGER.debug("Waiting for connected event.")
                try:
                    await asyncio.wait_for(
                        self.nefit.xmppclient.connected_event.wait(),
                        timeout=CONNECT_TIMEOUT,
                    )
                except asyncio.TimeoutError:
                    # slixmpp keeps trying in the background; if the session
                    # comes up later, the next poll picks it up (see
                    # _async_try_late_session) instead of starting over.
                    self.last_connect_error = (
                        f"no XMPP session with the Bosch cloud within "
                        f"{CONNECT_TIMEOUT:.0f}s"
                    )
                    return

                _LOGGER.debug("Connected successfully.")
                self.connected_state = STATE_CONNECTED
                await self._async_verify_session(CONNECT_TIMEOUT)
            finally:
                _LOGGER.debug("Set is connecting to false")
                self.is_connecting = False

    async def _async_verify_session(self, timeout: float) -> None:
        """Check that the thermostat answers on the current XMPP session."""
        self.nefit.xmppclient.message_event.clear()
        try:
            self.nefit.get("/gateway/brandID")
        except slixmpp.xmlstream.xmlstream.NotConnectedError:
            self.connected_state = STATE_INIT
            self.last_connect_error = "connection closed before the test request"
            return

        try:
            _LOGGER.debug("Wait for message event")
            await asyncio.wait_for(
                self.nefit.xmppclient.message_event.wait(), timeout=timeout
            )
        except asyncio.TimeoutError:
            self.last_connect_error = (
                f"XMPP session is up, but the thermostat did not answer "
                f"within {timeout:.0f}s"
            )
            return

        _LOGGER.debug("Message event received")
        self.nefit.xmppclient.message_event.clear()

        # No exception and no auth error
        if self.connected_state == STATE_CONNECTED:
            self.connected_state = STATE_CONNECTION_VERIFIED
            self.last_connect_error = None
            if self._ever_verified:
                self.reconnect_count += 1
            self._ever_verified = True
            _LOGGER.debug("Successfully verified connection.")

    async def _async_try_late_session(self) -> bool:
        """Use a session that came up after connect() had already timed out.

        Tearing such a session down and starting over would, with a slow
        Bosch cloud, keep killing every session just before it is usable.
        """
        client = self.nefit.xmppclient
        if (
            self._connect_lock.locked()
            or not client.is_connected()
            or not client.connected_event.is_set()
        ):
            return False

        _LOGGER.debug("XMPP session is up from an earlier attempt; verifying it.")
        async with self._connect_lock:
            self.connected_state = STATE_CONNECTED
            await self._async_verify_session(REQUEST_TIMEOUT)
            if self.connected_state != STATE_CONNECTION_VERIFIED:
                self.connected_state = STATE_INIT
                return False
        return True

    async def shutdown(self, event: str) -> None:
        """Shutdown."""
        _LOGGER.debug("Shutdown connection to Bosch cloud")
        self.expected_end = True
        await self.nefit.disconnect()

    async def no_content_callback(self, data: Any) -> None:
        """Log no content."""
        _LOGGER.debug("no_content_callback: %s", data)

    async def failed_auth_handler(self, event: str) -> None:
        """Handle failed auth."""
        self.connected_state = STATE_ERROR_AUTH
        self.nefit.xmppclient.connected_event.set()

        # disconnect, since nothing will work from now.
        await self.shutdown("auth_failed")

        # hass.components was removed from Home Assistant; use the module
        # function so an auth failure shows a notification instead of
        # raising AttributeError.
        if event == "auth_error_password":
            persistent_notification.async_create(
                self.hass,
                f"Invalid password for connecting {self.serial} to Bosch cloud.",
                title="Nefit password error",
                notification_id="nefit_password_error",
            )
        else:
            persistent_notification.async_create(
                self.hass,
                f"Invalid credentials (serial or accesskey) for connecting {self.serial} to Bosch cloud.",
                title="Nefit authentication error",
                notification_id="nefit_logon_error",
            )

        if self.config_entry:
            self.config_entry.async_start_reauth(self.hass)

    async def session_end_callback(self) -> None:
        """If connection is closed unexpectedly, try to reconnect."""
        if self.is_connecting:
            # Session end of the stale transport we closed ourselves in
            # connect(); the running connect() takes care of the rest.
            _LOGGER.debug("Ignoring session end during connect procedure.")
            return

        if not self.expected_end and self.connected_state != STATE_INIT:
            _LOGGER.debug(
                "Unexpected disconnect of %s with Bosch server. Try to reconnect..",
                self.serial,
            )

            # Reset values
            self.connected_state = STATE_INIT

            # Schedule an immediate reconnect rather than waiting up to 60s
            # for the next scheduled poll cycle.
            self.hass.async_create_task(self.async_refresh())

    async def parse_message(self, data: dict[str, Any]) -> None:
        """Message received callback function for the XMPP client."""
        if (
            data["id"] == "/ecus/rrc/uiStatus"
            and self.connected_state == STATE_CONNECTION_VERIFIED
        ):
            self._data["temp_setpoint"] = float(data["value"]["TSP"])  # for climate
            self._data["inhouse_temperature"] = float(
                data["value"]["IHT"]
            )  # for climate
            self._data["user_mode"] = data["value"]["UMD"]  # for climate
            self._data["boiler_indicator"] = data["value"]["BAI"]  # for climate
            self._data["last_update"] = data["value"]["CTD"]

            for val, key in self._status_keys.items():
                self._data[key] = data["value"].get(val)
        elif (
            data["id"].startswith("/ecus/rrc/homeentrancedetection/userprofile")
            and self.connected_state == STATE_CONNECTION_VERIFIED
        ):
            m = re.search(r"(?<=userprofile)\w+", data["id"])
            if m is not None:
                id = m.group(0)

                val = data["id"].rsplit("/", 1)[-1]

                self._data[f"presence{id}_{val}"] = data["value"]
        elif (
            data["id"] in self._urls
            and self.connected_state == STATE_CONNECTION_VERIFIED
        ):
            self._data[self._urls[data["id"]]["key"]] = data["value"]
        else:
            return

        if self._request == data["id"]:
            self._event.set()
        else:
            self.async_set_updated_data(self._data)

    @property
    def registered_urls(self) -> list[str]:
        """Return the endpoints polled on every update."""
        return sorted(self._urls)

    @property
    def status_keys(self) -> dict[str, Any]:
        """Return the uiStatus fields mapped to entity keys."""
        return dict(self._status_keys)

    def record_update_result(self, error: str | None) -> None:
        """Track connection health and tell the connection sensor.

        The coordinator does not notify entities after a second failed update
        in a row, so the connection sensor gets its own signal; otherwise its
        error attributes would stop updating during an outage.
        """
        now = dt_util.utcnow()
        if error is None:
            self.cloud_connected = True
            self.last_success_at = now
            self.disconnected_since = None
        else:
            if self.cloud_connected or self.disconnected_since is None:
                self.disconnected_since = now
            self.cloud_connected = False
            self.last_error = error
            self.last_error_at = now

        async_dispatcher_send(self.hass, SIGNAL_CONNECTION_STATUS.format(self.serial))

    def connection_diagnostics(self) -> dict[str, Any]:
        """Return the connection state for the diagnostics download."""
        client = self.nefit.xmppclient
        return {
            "connected_state": self.connected_state,
            "cloud_connected": self.cloud_connected,
            "xmpp_transport_connected": bool(client.is_connected()),
            "is_connecting": self.is_connecting,
            "last_success_at": self.last_success_at,
            "disconnected_since": self.disconnected_since,
            "last_error": self.last_error,
            "last_error_at": self.last_error_at,
            "last_connect_error": self.last_connect_error,
            "reconnect_count": self.reconnect_count,
            "last_update_success": self.last_update_success,
            "update_interval_seconds": (
                self.update_interval.total_seconds() if self.update_interval else None
            ),
            "connect_timeout_seconds": CONNECT_TIMEOUT,
            "request_timeout_seconds": REQUEST_TIMEOUT,
        }

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data and record the outcome for the connection sensor."""
        try:
            data = await self._async_update_data_inner()
        except Exception as ex:
            self.record_update_result(str(ex) or repr(ex))
            raise
        self.record_update_result(None)
        return data

    async def _async_update_data_inner(self) -> dict[str, Any]:
        """Update data via library.

        The Bosch cloud regularly lets a session die silently: the TCP
        connection stays open but no answers come back. Waiting several poll
        cycles before acting on that leaves every entity unavailable for
        minutes. Instead, a missed status answer is retried once straight
        away, and if that fails too the connection is rebuilt within the same
        update. Entities only become unavailable when that reconnect fails.
        """
        if self.connected_state != STATE_CONNECTION_VERIFIED:
            if not await self._async_try_late_session():
                _LOGGER.debug("Starting reconnect procedure.")
                await self._async_connect_or_fail()
            return await self._async_poll_or_fail()

        # Python clears an "except ... as" name after its block, so keep the
        # error in a variable of our own for the log message below.
        error: Exception | None = None
        try:
            return await self._async_poll()
        except Exception as ex:
            error = ex

        if not self.nefit.xmppclient.is_connected():
            reason = "connection is closed"
        else:
            _LOGGER.debug("No answer from Nefit Easy (%r), retrying once.", error)
            try:
                return await self._async_poll()
            except Exception as ex:
                error = ex
            reason = "no answer twice in a row"

        _LOGGER.info(
            "Nefit Easy session with Bosch cloud lost (%s: %r); reconnecting.",
            reason,
            error,
        )
        # connect() closes the old transport before opening a new one.
        self.connected_state = STATE_INIT
        await self._async_connect_or_fail()
        return await self._async_poll_or_fail()

    async def _async_connect_or_fail(self) -> None:
        """Connect, raising UpdateFailed when the connection is not verified."""
        await self.connect()
        if self.connected_state != STATE_CONNECTION_VERIFIED:
            reason = self.last_connect_error or f"state {self.connected_state}"
            _LOGGER.info("Reconnect to the Bosch cloud failed: %s.", reason)
            raise UpdateFailed(f"Unable to reconnect to the Bosch cloud: {reason}.")

    async def _async_poll_or_fail(self) -> dict[str, Any]:
        """Poll on a fresh connection; a failure here is a real outage."""
        try:
            return await self._async_poll()
        except Exception as ex:
            self.connected_state = STATE_INIT
            raise UpdateFailed(f"Error communicating with Nefit Easy: {ex!r}") from ex

    async def _async_poll(self) -> dict[str, Any]:
        """Request the status and all registered endpoints."""
        async with self._lock:
            await self._async_get_url("/ecus/rrc/uiStatus")

            for _url in self._urls:
                try:
                    await self._async_get_url(_url)
                except asyncio.TimeoutError:
                    # The status answered, so the connection works. Keep the
                    # previous value for this endpoint instead of failing the
                    # whole update (and making every entity unavailable).
                    _LOGGER.debug(
                        "No answer in time for %s, keeping previous value.", _url
                    )

        return self._data

    async def async_init_presence(self, endpoint: str, index: int) -> Any:
        """Init presence detection."""
        async with self._lock:
            url = f"{endpoint}/userprofile{index}/active"
            await self._async_get_url(url)

            if self._data.get(f"presence{index}_active") == "on":
                url = f"{endpoint}/userprofile{index}/name"
                await self._async_get_url(url)

                return self._data.get(f"presence{index}_name")

            return None

    async def update_ui_status_later(self, delay: float) -> None:
        """Force update of uiStatus after delay."""
        self.hass.loop.call_later(delay, self.nefit.get, "/ecus/rrc/uiStatus")

    async def _async_get_url(self, url: str) -> None:
        self._event.clear()
        self._request = url
        self.nefit.get(url)
        try:
            await asyncio.wait_for(self._event.wait(), timeout=REQUEST_TIMEOUT)
        except asyncio.TimeoutError:
            raise
        finally:
            self._request = ""
