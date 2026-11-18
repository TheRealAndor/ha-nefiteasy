# ha-nefiteasy (maintained fork)
Nefit Easy connection for Home Assistant

[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support%20me-FF5E5B?logo=ko-fi&logoColor=white)](https://ko-fi.com/therealandor) [![PayPal](https://img.shields.io/badge/PayPal-Donate-00457C?logo=paypal&logoColor=white)](https://paypal.me/andorklink)

> **This is a personal, maintained fork of [ksya/ha-nefiteasy](https://github.com/ksya/ha-nefiteasy).**
> I keep this repository for my own Home Assistant installation, but anyone is welcome to use it.
> I try to solve issues reported here myself and keep the integration actively up to date for as long as I still have a Nefit Easy thermostat myself.
> Issues and pull requests are welcome in [this repository's issue tracker](https://github.com/TheRealAndor/ha-nefiteasy/issues).

## Credits

All credit for the original integration goes to **[ksya](https://github.com/ksya)**, who created [ha-nefiteasy](https://github.com/ksya/ha-nefiteasy).
ksya mentioned in September 2021 that they no longer have the thermostat themselves ([comment in #74](https://github.com/ksya/ha-nefiteasy/issues/74#issuecomment-929656113): *"I cannot test since I don't have the thermostat anymore. It broke last summer."*). Since then the upstream repository has mainly been kept alive by [RobBie1221](https://github.com/RobBie1221) and other contributors – thanks to all of them!

Big thanks as well to marconfus for the aionefit library and his work on the ha-nefit-ng component:
* https://github.com/marconfus/aionefit
* https://github.com/marconfus/ha-nefit-ng

## Improvements compared to the original

Based on upstream version 0.4.10. The changes focus on the connection to the Bosch cloud, which regularly drops ([ksya/ha-nefiteasy#462](https://github.com/ksya/ha-nefiteasy/issues/462)) and left all entities `unavailable` for minutes.

### Connection stability
* **Self-healing poll:** when the Bosch cloud silently stops answering (TCP connection open, no replies), a missed status answer is retried once right away. If that fails too, the connection is rebuilt *within the same update*. Entities only become unavailable when that reconnect itself fails, instead of after several poll cycles.
* **Stale connections are closed before reconnecting.** Previously `connect()` was called on a client that still had an open transport, which started a second session on the same stream. This caused `ValueError: There is already a scheduled event of name: Whitespace Keepalive` and, when the orphaned transport closed later, a `session_end` that also killed the new, working session.
* **Background connection attempts are cancelled** before a new attempt starts, so a timed-out earlier attempt can no longer bring up a parallel session.
* **Leftover keepalive is removed** as a safety net, so the next session can always schedule it again.
* **Late sessions are reused:** if the XMPP session comes up just after the connect timeout, the next poll verifies and uses it instead of tearing it down. With a slow Bosch cloud the old behaviour could kill every session just before it became usable.
* **One connection procedure at a time:** an `asyncio.Lock` replaces the `is_connecting` flag. A second caller (poll or `session_end`) waits for the running attempt and uses its result instead of starting another one.
* **`session_end` during our own reconnect is ignored**, since that is the stale transport we closed ourselves.
* **A slow optional endpoint no longer fails the whole update:** if `uiStatus` answered but another endpoint times out, its previous value is kept instead of making every entity unavailable.
* **No more log spam on every reconnect:** the Bosch/Nefit XMPP server sends no version attribute in its stream header, so slixmpp logs *"Legacy XMPP 0.9 protocol detected"* on each (re)connect. This harmless warning is now filtered out; only this specific message from `slixmpp.basexmpp` is hidden.
* **Clearer error messages:** the reason a reconnect failed (no XMPP session within 29 s, thermostat did not answer, connection closed) is logged and shown in `UpdateFailed`. Timeouts are named constants.

### Startup
* **Faster platform setup:** probing the 10 presence (home entrance detection) profiles takes up to 20 sequential cloud requests. This now runs as a background task, which fixes *"Setup of switch platform nefiteasy is taking over 10 seconds"*. The presence switches are added as soon as they are known.
* **One slow presence profile no longer drops the others:** a timeout skips only that profile; a lost connection stops probing cleanly.
* Entities no longer trigger their own refresh on creation; values come from the coordinator refresh right after setup.
* `coordinator.data` is initialised to an empty dict, so entities added before the first refresh don't read `None`.

### Home Assistant compatibility
* **Authentication failure notifications work again:** `hass.components.persistent_notification` was removed from Home Assistant and raised `AttributeError`; replaced by `persistent_notification.async_create`.
* **No deprecation warnings on Home Assistant 2026.11:** the climate entity uses `native_temperature_unit`, `native_current_temperature` and `native_target_temperature`. The original logs *"…NefitThermostat provides the deprecated temperature_unit, this will stop working in Home Assistant 2027.11…"* (and the same for `current_temperature` and `target_temperature`), and its thermostat will stop working in 2027.11. Older Home Assistant versions keep working through the old property names.
* Removed the deprecated `CONNECTION_CLASS` from the config flow.
* Presence lookups use `.get()` so a missing key no longer raises `KeyError`.

## Installation

### HACS (recommended)
1. Open HACS and go to **Custom repositories** (three-dot menu, top right).
2. Add `https://github.com/TheRealAndor/ha-nefiteasy` with category **Integration**.
3. Search for **Nefit Easy** and install it.
4. Restart Home Assistant.

> If you already use the original ksya/ha-nefiteasy through HACS, remove that repository first. Both use the domain `nefiteasy`, so your existing configuration and entities are kept.

### Manual
1. Copy the folder ```custom_components/nefiteasy/``` to your homeassistant config directory.
2. Restart Home Assistant.

## Configuration
All configuration can be done from within Home Assistant:
1. Go to Settings
2. Go to Integrations
3. At the bottom right, click Add Integration
4. Search for "Nefit" -> Nefit Easy (Bosch) – Stable
5. Fill in your serial number, access key and password
6. Save

> Make sure to enter serial number and access key without spaces!

### Limit sensors and switches
Some entities are disabled by default, if needed they can be enabled. Entities that are disabled will not be updated.

## Controls/Switches & Sensors

### Controls/Switches

> None enabled by default.

| Key | Name | Description |
| - | - | -  |
| active_program | Active program | Clock [program] 1 or 2 |
| fireplace_mode | Fireplace mode | Other rooms stay warm as the fire burns |
| holiday_mode | Holiday mode | Define settings in the app. Activate/Deactivate them in Home Assistant |
| hot_water | Hot water | Hot water preheat |
| home_entrance_detection | Presence | "The Nefit Easy detects the presence of the smart device in the home and adjusts the room temperature accordingly.<br><br>To let this function, operate mobile Internet and Wi-Fi must be enabled continuously. Location services must be enabled in the settings; optionally you can use the location modus -> battery saving if your device supports it." |
| lockui | Lock UI | "Manual operation of the thermostat can be locked to prevent unintended adjustments." |
| preheating | Preheating | |
| shower_timer | Shower timer | "Shortening the duration of showering helps save energy.<br><br>3 minutes prior to the allotted time set cold water will come out of the hot water tap temporarily. When the allotted tome has fully passed, cold water will come out of the hot water tap until the tap is closed." |
| shower_timer_duration | Shower timer duration | Set time for the 'Shower timer' in minutes. |
| today_as_sunday | Today as Sunday | |
| tomorrow_as_sunday | Tomorrow as Sunday
| weather_dependent | Weather dependent | "Weather compensation control based on the local outdoor temperature.<br><br> Weather compensation control is best used with thermostatic radiator valves or thermostatically controlled radiant heating.<br><br>Please note:<br>The control is not based on the measured room temperature. Weather compensation control is comfort enhancing, but may result in increased heating costs. This control requires knowledge of weather compensation control. Ask your installer for support." |
| temperature_adjustment | Temperature Adjustment | Calibrate the measured temperature between +2 and -2 °C. |

### Sensors

| Key | Name | UoM | Description | Enabled by default |
| - | - | :-: | - | :-: |
| actual_power | Power | | | &#x2714; |
| hot_water_operation | Hot water operation |  | "When 'Follow program' is off, preheat function will be active or your indirect storage tank will remain heated.<br><br>Follow heating program: Hot water will be heated inline with heating 'Wakeup' & 'Home' activities, but extended one hour before and after these periods.<br><br>Custom program: Use this to set an independent hot water clock program.<br><br>For combi boilers: To disable preheat permanently, please refer to the boiler user manual." | &#x274C; |
| inhouse_temperature | Inhouse temperature | °C | Current room temperature | &#x274C; |
| outdoor_temperature | Outdoor temperature | °C | Outdoor temperature | &#x2714; |
| status | status | | Status of the boiler | &#x2714; |
| supply_temperature | Supply temperature | °C | Temperature of (hot) water ready to supply | &#x2714; |
| system_pressure | System pressure | Bar | System water pressure | &#x2714; |
| target_temperature | Target temperature | °C | Target temperature | &#x274C; |
| year_total | Year total | m<sup>3</sup> | Volume of gas consumed since Jan 1<sup>st</sup> | &#x2714; |
| firmware_version | Firmware version | | Firmware version installed on thermostat | &#x274C; |
| hardware_version | Hardware revision | | Hardware revision of thermostat unit | &#x274C; |
| refill_needed | Refill needed | | Alert when boiler water pressure drops low and needs refilling | &#x274C; |
| system_leaking | System leak detected | | Leak detection alert for heating system pressure drops | &#x274C; |
| ignition_status | Ignition status | | Burner ignition failure warning indicator | &#x274C; |
| closing_valve_status | Gas valve status | | Gas valve / closing valve fault warning indicator | &#x274C; |
| maintenance_request | Boiler maintenance required | | Boiler maintenance or service required indicator | &#x274C; |

#### Sensor values

##### Status

| Code | Description |
| :-: | - |
| -H | central heating active |
| =H | hot water active |
| 0C<br>0L<br>0U | system starting |
| 0E | system waiting |
| 0H | system standby |
| 0A<br>0Y | system waiting (boiler cannot transfer heat to central heating) |
| 2E<br>H07 | boiler water pressure too low |
| 2F<br>2L<br>2P<br>2U<br>4F<br>4L | sensors measured abnormal temperature |
| 6A<br>6C | burner doesn't ignite |
| rE | system restarting |


##### Hot water operation
```
- follow-ch
```

## Debugging problems
Turn on debug for both aionefit as custom_components.nefiteasy:
```
logger:
  default: info
  logs:
    custom_components.nefiteasy: debug
    aionefit: debug
```

## FAQ
#### HA cannot connect to Bosch cloud 

If you experience errors during the boot of HA regarding the connection to the Bosch cloud ie ```Timeout while connecting to Bosch cloud. Retrying in the background```, you may want to change the OpenSSL configuration.
The OpenSSL defaults for Buster are causing the problem, probably because Nefit/Bosch is using either an outdated TLS version or an outdated cipher.

Edit ```/etc/ssl/openssl.cnf``` and change the system wide defaults back to their previous values(pre-Buster):
```
MinProtocol = None
CipherString = DEFAULT
```

https://www.debian.org/releases/stable/amd64/release-notes/ch-information.en.html#openssl-defaults
