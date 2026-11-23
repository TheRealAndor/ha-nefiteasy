"""Daily gas usage of a Nefit Easy, split into hot water and central heating.

The thermostat keeps one record per day in pages of 32 days:
/ecus/rrc/recordings/gasusage?page=N. Each record has the date ("d",
dd-mm-yyyy), the gas used for hot water ("hw") and central heating ("ch") in
kWh, and the average outdoor temperature ("T", tenths of a degree). A day is
added after it has ended, so the newest record is yesterday.
/ecus/rrc/recordings/gasusagePointer is the number of the next, empty record.
Empty records have the date "255-256-65535" and the value 6553.5.

See https://github.com/marcelrv/nefit_easy_protocol/blob/master/gasusage.md
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    get_last_statistics,
)
from homeassistant.const import UnitOfVolume
from homeassistant.core import callback
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import VolumeConverter

from .const import CONF_NAME, DOMAIN

if TYPE_CHECKING:
    from .coordinator import NefitEasy

_LOGGER = logging.getLogger(__name__)

GAS_POINTER_URL = "/ecus/rrc/recordings/gasusagePointer"
GAS_USAGE_URL = "/ecus/rrc/recordings/gasusage"
RECORDS_PER_PAGE = 32
# The thermostat converts kWh to m³ with this factor for natural gas
# (a calorific value of 29 MJ/m³), the same as the year total sensor.
KWH_TO_M3 = 0.12307692
# Values of 6553.5 kWh (0xFFFF tenths) or more mark an empty record.
EMPTY_VALUE = 6553.5
# Pages to import into the statistics the first time: about one year.
FIRST_IMPORT_PAGES = 12
# How often to check for a new day. The pointer is one small request.
CHECK_INTERVAL = timedelta(hours=1)
# Wait before trying again after an error.
RETRY_INTERVAL = timedelta(minutes=10)

HOT_WATER = "hot_water"
HEATING = "heating"


@dataclass(frozen=True)
class GasDay:
    """Gas usage of one day, in kWh."""

    day: date
    hot_water: float
    heating: float
    outdoor_temperature: float | None

    def m3(self, kind: str) -> float:
        """Return the usage of hot water or heating in m³."""
        kwh = self.hot_water if kind == HOT_WATER else self.heating
        return round(kwh * KWH_TO_M3, 3)


def parse_page(value: Any) -> list[GasDay]:
    """Return the filled records of a gas usage page, oldest first."""
    days: list[GasDay] = []
    if not isinstance(value, list):
        return days

    for record in value:
        try:
            day = datetime.strptime(record["d"], "%d-%m-%Y").date()
            hot_water = float(record["hw"])
            heating = float(record["ch"])
        except (KeyError, TypeError, ValueError):
            # Empty records have the date 255-256-65535.
            continue
        if hot_water >= EMPTY_VALUE or heating >= EMPTY_VALUE:
            continue

        temperature = record.get("T")
        days.append(
            GasDay(
                day=day,
                hot_water=hot_water,
                heating=heating,
                outdoor_temperature=(
                    round(temperature / 10, 1)
                    if isinstance(temperature, (int, float))
                    else None
                ),
            )
        )

    return sorted(days, key=lambda gas_day: gas_day.day)


def page_of_record(record: int) -> int:
    """Return the page (from 1) that holds a record (from 1)."""
    return (record - 1) // RECORDS_PER_PAGE + 1


class NefitGasUsage:
    """Read the daily gas usage and add it to the long-term statistics."""

    def __init__(self, coordinator: NefitEasy) -> None:
        """Initialize."""
        self._coordinator = coordinator
        self._pointer: int | None = None
        self._next_check: datetime | None = None
        self._task: asyncio.Task | None = None
        # The newest day in the history: normally yesterday.
        self.latest: GasDay | None = None

    def statistic_id(self, kind: str) -> str:
        """Return the id of the statistic for hot water or heating."""
        return f"{DOMAIN}:{self._coordinator.serial}_gas_{kind}".lower()

    @callback
    def async_schedule(self) -> None:
        """Start a check in the background when one is due."""
        now = dt_util.utcnow()
        if self._next_check is not None and now < self._next_check:
            return
        if self._task is not None and not self._task.done():
            return

        self._next_check = now + CHECK_INTERVAL
        self._task = self._coordinator.config_entry.async_create_background_task(
            self._coordinator.hass,
            self._async_check(),
            f"{DOMAIN} gas usage {self._coordinator.serial}",
        )

    async def _async_check(self) -> None:
        """Read the history when a day was added."""
        try:
            await self._async_update()
        except asyncio.TimeoutError:
            _LOGGER.debug("No answer in time while reading the gas usage.")
            self._next_check = dt_util.utcnow() + RETRY_INTERVAL
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected error while reading the gas usage")
            self._next_check = dt_util.utcnow() + RETRY_INTERVAL

    async def _async_update(self) -> None:
        """Read the new days and update the sensors and statistics."""
        pointer = await self._coordinator.async_request(GAS_POINTER_URL)
        try:
            pointer = int(pointer)
        except (TypeError, ValueError):
            _LOGGER.debug("Unexpected gas usage pointer %r.", pointer)
            return
        if pointer == self._pointer or pointer < 2:
            return

        hass = self._coordinator.hass
        import_statistics = "recorder" in hass.config.components
        last = await self._async_last_statistics() if import_statistics else {}
        # Read back to the oldest day that is not in the statistics yet.
        known = [stat[0] for stat in last.values()]
        oldest_needed = min(known) + timedelta(days=1) if len(known) == 2 else None

        days: dict[date, GasDay] = {}
        newest_page = page_of_record(pointer - 1)
        for page in range(newest_page, max(newest_page - FIRST_IMPORT_PAGES, 0), -1):
            records = parse_page(
                await self._coordinator.async_request(f"{GAS_USAGE_URL}?page={page}")
            )
            days.update((record.day, record) for record in records)
            if not import_statistics or not records:
                break
            if oldest_needed is not None and records[0].day <= oldest_needed:
                break

        if not days:
            return

        if import_statistics:
            self._import(days, last)

        self.latest = days[max(days)]
        self._pointer = pointer
        self._coordinator.async_update_listeners()

    async def _async_last_statistics(self) -> dict[str, tuple[date, float]]:
        """Return the last imported day and sum of each statistic."""
        hass = self._coordinator.hass
        result: dict[str, tuple[date, float]] = {}
        for kind in (HOT_WATER, HEATING):
            statistic_id = self.statistic_id(kind)
            stats = await get_instance(hass).async_add_executor_job(
                get_last_statistics, hass, 1, statistic_id, True, {"sum"}
            )
            if stats.get(statistic_id):
                last = stats[statistic_id][0]
                start = dt_util.as_local(dt_util.utc_from_timestamp(last["start"]))
                result[kind] = (start.date(), float(last["sum"] or 0))
        return result

    def _import(
        self, days: dict[date, GasDay], last: dict[str, tuple[date, float]]
    ) -> None:
        """Add the days after the last imported day to the statistics."""
        device_name = self._coordinator.config_entry.data.get(CONF_NAME, "Nefit")
        names = {HOT_WATER: "gas hot water", HEATING: "gas heating"}

        for kind in (HOT_WATER, HEATING):
            last_day, total = last.get(kind, (None, 0.0))
            statistics: list[StatisticData] = []
            for day in sorted(days):
                if last_day is not None and day <= last_day:
                    continue
                usage = days[day].m3(kind)
                total = round(total + usage, 3)
                statistics.append(
                    StatisticData(
                        start=dt_util.start_of_local_day(day),
                        state=usage,
                        sum=total,
                    )
                )
            if not statistics:
                continue

            _LOGGER.debug(
                "Adding %d days of %s to the statistics.", len(statistics), kind
            )
            async_add_external_statistics(
                self._coordinator.hass,
                StatisticMetaData(
                    mean_type=StatisticMeanType.NONE,
                    has_sum=True,
                    name=f"{device_name} {names[kind]}",
                    source=DOMAIN,
                    statistic_id=self.statistic_id(kind),
                    unit_class=VolumeConverter.UNIT_CLASS,
                    unit_of_measurement=UnitOfVolume.CUBIC_METERS,
                ),
                statistics,
            )
