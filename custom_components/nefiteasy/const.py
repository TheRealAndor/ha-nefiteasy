"""Constants for the nefiteasy component."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    PERCENTAGE,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfVolume,
)

from .models import (
    NefitBinarySensorEntityDescription,
    NefitEntityDescription,
    NefitNumberEntityDescription,
    NefitSelectEntityDescription,
    NefitSensorEntityDescription,
    NefitSwitchEntityDescription,
)

DOMAIN = "nefiteasy"

CONF_DEVICES = "devices"
CONF_SERIAL = "serial"
CONF_ACCESSKEY = "accesskey"
CONF_PASSWORD = "password"
CONF_NAME = "name"
CONF_MIN_TEMP = "min_temp"
CONF_MAX_TEMP = "max_temp"
CONF_TEMP_STEP = "temp_step"
CONF_SWITCHES = "switches"
CONF_SENSORS = "sensors"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_REQUEST_TIMEOUT = "request_timeout"

DEFAULT_MIN_TEMP = 10
DEFAULT_MAX_TEMP = 28
DEFAULT_TEMP_STEP = 0.5
# Seconds between two polls. Below 15 s the Bosch cloud gets more requests
# than it answers in time: one poll asks for 15 or more endpoints in a row.
DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 15
MAX_SCAN_INTERVAL = 3600
# Seconds to wait for the answer to a single request. The Bosch cloud is often
# slow without being down: measurements in ksya/ha-nefiteasy#462 showed replies
# of 9-20 s on sessions that kept working.
DEFAULT_REQUEST_TIMEOUT = 20
MIN_REQUEST_TIMEOUT = 5
MAX_REQUEST_TIMEOUT = 60

STATE_CONNECTED = "connected"
STATE_CONNECTION_VERIFIED = "connection_verified"
STATE_INIT = "initializing"
STATE_ERROR_AUTH = "authentication_failed"

# Dispatcher signal (formatted with the serial) sent when the connection
# health of a thermostat changes.
SIGNAL_CONNECTION_STATUS = "nefiteasy_connection_status_{}"

AUTH_ERROR_PASSWORD = "auth_error_password"
AUTH_ERROR_CREDENTIALS = "auth_error_credentials"

DHW_CIRCUIT = "/dhwCircuits/dhwA/"

# Burner activity (uiStatus BAI) mapped to the states of the sensor.
BURNER_ACTIVITY = {
    "CH": "central_heating",
    "HW": "hot_water",
    "No": "idle",
}

# "Snel warm water" in the Nefit Easy app. The thermostat keeps one value per
# user mode; in the clock mode the program sets it at every switchpoint.
HOT_WATER_MANUAL = NefitEntityDescription(
    key="hot_water_manual", url=DHW_CIRCUIT + "dhwOperationManualMode"
)
HOT_WATER_CLOCK = NefitEntityDescription(
    key="hot_water_clock", url=DHW_CIRCUIT + "dhwOperationClockMode"
)

# "Volgens programma" in the app: eco follows the program and the setting
# above, comfort keeps hot water on all the time.
HOT_WATER_MODE = NefitEntityDescription(
    key="hot_water_mode", url=DHW_CIRCUIT + "dhwOperationMode"
)

HOT_WATER_STATE = NefitBinarySensorEntityDescription(
    key="hot_water_state",
    name="Hot water state",
    short="DHW",
    icon="mdi:water-boiler",
)

HOT_WATER_PROGRAM = NefitBinarySensorEntityDescription(
    key="hot_water_program",
    name="Hot water program",
    url=DHW_CIRCUIT + "dhwCurrentSwitchpoint",
    icon="mdi:calendar-clock",
    entity_registry_enabled_default=False,
)

HOT_WATER_NEXT_SWITCHPOINT = NefitEntityDescription(
    key="hot_water_next_switchpoint", url=DHW_CIRCUIT + "dhwNextSwitchpoint"
)

name = "name"
url = "url"
unit = "unit"
device_class = "device_class"
short = "short"
icon = "icon"
options = "options"

SELECTS: tuple[NefitSelectEntityDescription, ...] = (
    NefitSelectEntityDescription(
        key="active_program",
        name="Active program",
        url="/ecus/rrc/userprogram/activeprogram",
        icon="mdi:calendar-today",
        options={
            0: "Clock 1",
            1: "Clock 2",
        },
        entity_registry_enabled_default=False,
    ),
)

SENSORS: tuple[NefitSensorEntityDescription, ...] = (
    NefitSensorEntityDescription(
        key="year_total",
        name="Year total",
        url="/ecus/rrc/recordings/yearTotal",
        unit=UnitOfVolume.CUBIC_METERS,
        device_class=SensorDeviceClass.GAS,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    NefitSensorEntityDescription(
        key="status", name="Status", url="/system/appliance/displaycode"
    ),
    # Gas usage of the newest day in the history of the thermostat, normally
    # yesterday. The full history goes to the long-term statistics, see gas.py.
    NefitSensorEntityDescription(
        key="gas_hot_water_yesterday",
        name="Gas hot water yesterday",
        icon="mdi:water-boiler",
        unit=UnitOfVolume.CUBIC_METERS,
        device_class=SensorDeviceClass.GAS,
        suggested_display_precision=2,
    ),
    NefitSensorEntityDescription(
        key="gas_heating_yesterday",
        name="Gas heating yesterday",
        icon="mdi:radiator",
        unit=UnitOfVolume.CUBIC_METERS,
        device_class=SensorDeviceClass.GAS,
        suggested_display_precision=2,
    ),
    NefitSensorEntityDescription(
        key="burner_activity",
        name="Burner activity",
        short="BAI",
        icon="mdi:fire-circle",
        device_class=SensorDeviceClass.ENUM,
        options=list(BURNER_ACTIVITY.values()),
    ),
    NefitSensorEntityDescription(
        key="supply_temperature",
        name="Supply temperature",
        url="/heatingCircuits/hc1/actualSupplyTemperature",
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NefitSensorEntityDescription(
        key="outdoor_temperature",
        name="Outdoor temperature",
        url="/system/sensors/temperatures/outdoor_t1",
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NefitSensorEntityDescription(
        key="system_pressure",
        name="System pressure",
        url="/system/appliance/systemPressure",
        unit=UnitOfPressure.BAR,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NefitSensorEntityDescription(
        key="actual_power",
        name="Power",
        url="/system/appliance/actualPower",
        unit=PERCENTAGE,
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    NefitSensorEntityDescription(
        key="hot_water_operation",
        name="Hot water operation",
        url="/dhwCircuits/dhwA/dhwOperationType",
        entity_registry_enabled_default=False,
    ),
    NefitSensorEntityDescription(
        key="inhouse_temperature",
        name="Inhouse temperature",
        short="IHT",
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    NefitSensorEntityDescription(
        key="target_temperature",
        name="Target temperature",
        short="TSP",
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    NefitSensorEntityDescription(
        key="firmware_version",
        name="Firmware version",
        url="/gateway/versionFirmware",
        icon="mdi:information-outline",
        entity_registry_enabled_default=False,
    ),
    NefitSensorEntityDescription(
        key="hardware_version",
        name="Hardware revision",
        url="/gateway/versionHardware",
        icon="mdi:chip",
        entity_registry_enabled_default=False,
    ),
    NefitSensorEntityDescription(
        key="refill_needed",
        name="Refill needed",
        url="/ecus/rrc/pm/refillneeded/status",
        icon="mdi:water-alert",
        entity_registry_enabled_default=False,
    ),
    NefitSensorEntityDescription(
        key="system_leaking",
        name="System leak detected",
        url="/ecus/rrc/pm/systemleaking/status",
        icon="mdi:pipe-leak",
        entity_registry_enabled_default=False,
    ),
    NefitSensorEntityDescription(
        key="ignition_status",
        name="Ignition status",
        url="/ecus/rrc/pm/ignition/status",
        icon="mdi:fire-alert",
        entity_registry_enabled_default=False,
    ),
    NefitSensorEntityDescription(
        key="closing_valve_status",
        name="Gas valve status",
        url="/ecus/rrc/pm/closingvalve/status",
        icon="mdi:valve-closed",
        entity_registry_enabled_default=False,
    ),
    NefitSensorEntityDescription(
        key="maintenance_request",
        name="Boiler maintenance required",
        url="/system/appliance/boilermaintenancerequest",
        icon="mdi:wrench-clock",
        entity_registry_enabled_default=False,
    ),
)

SWITCHES: tuple[NefitSwitchEntityDescription, ...] = (
    # "Snel warm water" of the current user mode, see HOT_WATER_MANUAL.
    NefitSwitchEntityDescription(
        key="hot_water",
        name="Hot water",
        icon="mdi:water-boiler",
        entity_registry_enabled_default=False,
    ),
    # "Volgens programma", see HOT_WATER_MODE.
    NefitSwitchEntityDescription(
        key="hot_water_follows_program",
        name="Hot water follows program",
        icon="mdi:water-boiler-auto",
        entity_registry_enabled_default=False,
    ),
    NefitSwitchEntityDescription(
        key="holiday_mode",
        name="Holiday mode",
        url="/heatingCircuits/hc1/holidayMode/status",
        short="HMD",
        icon="mdi:briefcase-outline",
        entity_registry_enabled_default=False,
    ),
    NefitSwitchEntityDescription(
        key="fireplace_mode",
        name="Fireplace mode",
        url="/ecus/rrc/userprogram/fireplacefunction",
        short="FPA",
        icon="mdi:fire",
        entity_registry_enabled_default=False,
    ),
    NefitSwitchEntityDescription(
        key="today_as_sunday",
        name="Today as Sunday",
        url="/ecus/rrc/dayassunday/day10/active",
        short="DAS",
        icon="mdi:calendar-star",
        entity_registry_enabled_default=False,
    ),
    NefitSwitchEntityDescription(
        key="tomorrow_as_sunday",
        name="Tomorrow as Sunday",
        url="/ecus/rrc/dayassunday/day11/active",
        short="TAS",
        icon="mdi:calendar-star",
        entity_registry_enabled_default=False,
    ),
    NefitSwitchEntityDescription(
        key="preheating",
        name="Preheating",
        url="/ecus/rrc/userprogram/preheating",
        icon="mdi:calendar-clock",
        entity_registry_enabled_default=False,
    ),
    NefitSwitchEntityDescription(
        key="home_entrance_detection",
        name="Presence {}",
        icon="mdi:account-check",
        entity_registry_enabled_default=False,
    ),
    NefitSwitchEntityDescription(
        key="weather_dependent",
        name="Weather dependent",
        url="/heatingCircuits/hc1/control",
        icon="mdi:weather-partly-snowy-rainy",
        entity_registry_enabled_default=False,
    ),
    NefitSwitchEntityDescription(
        key="lockui",
        name="Lock UI",
        url="/ecus/rrc/lockuserinterface",
        icon="mdi:lock",
        entity_registry_enabled_default=False,
    ),
    NefitSwitchEntityDescription(
        key="shower_timer",
        name="Shower timer",
        url="/dhwCircuits/dhwA/extraDhw/status",
        icon="mdi:timer-cog-outline",
        entity_registry_enabled_default=False,
    ),
)

NUMBERS: tuple[NefitNumberEntityDescription, ...] = (
    NefitNumberEntityDescription(
        key="shower_timer_duration",
        name="Shower timer duration",
        url="/dhwCircuits/dhwA/extraDhw/duration",
        icon="mdi:timer-outline",
        native_min_value=0,
        native_max_value=60,
        native_step=1,
        entity_registry_enabled_default=False,
    ),
    NefitNumberEntityDescription(
        key="temperature_adjustment",
        name="Temperature adjustment",
        url="/heatingCircuits/hc1/temperatureAdjustment",
        icon="mdi:adjust",
        native_min_value=-2,
        native_max_value=2,
        native_step=0.1,
        entity_registry_enabled_default=False,
    ),
)
