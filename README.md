<p align="center">
  <img src="custom_components/nefiteasy/brand/icon.png" alt="Nefit Bosch" width="128">
</p>

<h1 align="center">Nefit Easy (Bosch) for Home Assistant</h1>

<p align="center">
  Control your Nefit Easy thermostat from Home Assistant, with a connection to the Bosch cloud that recovers by itself.
</p>

<p align="center">
  <a href="https://github.com/TheRealAndor/ha-nefiteasy/releases"><img src="https://img.shields.io/github/v/release/TheRealAndor/ha-nefiteasy?label=release" alt="Release"></a>
  <a href="https://github.com/TheRealAndor/ha-nefiteasy/actions/workflows/push.yml"><img src="https://github.com/TheRealAndor/ha-nefiteasy/actions/workflows/push.yml/badge.svg" alt="Build"></a>
  <a href="https://hacs.xyz"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg" alt="HACS Custom"></a>
  <a href="https://github.com/TheRealAndor/ha-nefiteasy/issues"><img src="https://img.shields.io/github/issues/TheRealAndor/ha-nefiteasy" alt="Issues"></a>
  <br>
  <a href="https://ko-fi.com/therealandor"><img src="https://img.shields.io/badge/Ko--fi-Support%20me-FF5E5B?logo=ko-fi&logoColor=white" alt="Ko-fi"></a>
  <a href="https://paypal.me/andorklink"><img src="https://img.shields.io/badge/PayPal-Donate-00457C?logo=paypal&logoColor=white" alt="PayPal"></a>
</p>

> [!NOTE]
> **A maintained fork of [ksya/ha-nefiteasy](https://github.com/ksya/ha-nefiteasy).**
> I keep this repository for my own Home Assistant, and anyone is welcome to use it. I try to solve the issues reported here myself and keep the integration up to date for as long as I have a Nefit Easy myself. [Issues](https://github.com/TheRealAndor/ha-nefiteasy/issues) and pull requests are welcome.

## 🔎 What it does

The Nefit Easy is a smart thermostat from Bosch for Nefit gas boilers. It has no local API: the thermostat and the Nefit Easy app talk to each other through the Bosch cloud. This integration connects Home Assistant to that same cloud, with the serial number, access key and password of the thermostat, and polls it every 60 seconds by default. The poll interval and the request timeout are **configurable** in the options, from 15 seconds up to an hour.

You get a thermostat entity to read and set the room temperature and the program, plus sensors and switches for the boiler: status codes, supply and outdoor temperature, water pressure, gas usage, hot water, holiday and fireplace mode, presence detection and more. The integration is written for the first generation of Bosch cloud thermostats; the Nefit Easy is the one it is tested with.

The integration meets the [Bronze tier](https://developers.home-assistant.io/docs/core/integration-quality-scale/) of the Home Assistant integration quality scale, see [`quality_scale.yaml`](custom_components/nefiteasy/quality_scale.yaml). HACS and the Marketplace do not require this; following the quality scale is a way to raise the quality of the integration, using the same rules as the integrations built into Home Assistant.

## ✨ Highlights

| | |
| - | - |
| 🔁 **Self-healing connection** | A lost or silent Bosch cloud session is detected and rebuilt within the same update, so entities no longer stay `unavailable` for minutes. |
| 📶 **Connection sensor** | `Bosch cloud connection` shows whether Home Assistant gets answers, since when it doesn't, and why. It stays available during an outage. |
| 🩺 **Diagnostics download** | One click gives you a file with the connection state, errors and values, with all secrets removed. Ideal for issues. |
| ⏱️ **Configurable polling** | Set the poll interval (15 s to 1 hour) and the request timeout in the options, without editing the code. Follow the boiler status faster for floor heating, or poll less often. See [Options](#options). |
| 🔥 **Gas usage per day** | Hot water and heating apart, with about a year of history, straight into the Energy dashboard. |
| 🐢 **Patient with a slow cloud** | 20 s request timeout by default: slow but working replies no longer count as a dropped session. |
| 🧹 **Clean log** | No "Legacy XMPP" spam, no deprecation warnings on Home Assistant 2026.11 and no `Whitespace Keepalive` errors. |
| ⚡ **Fast startup** | Presence profiles are read in the background, so setup no longer takes over 10 seconds. |
| 🏠 **Drop-in replacement** | Same `nefiteasy` domain as the original: your configuration, entities and history stay. |

## 📦 Installation

### HACS (recommended)

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=TheRealAndor&repository=ha-nefiteasy&category=integration)

Or by hand:

1. In HACS (or the Marketplace), open the menu (⋮, top right) → **Custom repositories**.
2. Add `https://github.com/TheRealAndor/ha-nefiteasy` with type **Integration**.
3. Search for **Nefit Easy**, install it and restart Home Assistant.

> [!TIP]
> **Coming from ksya/ha-nefiteasy?** Follow [Migrating from ksya/ha-nefiteasy](#-migrating-from-ksyaha-nefiteasy) below, so your configuration and entities stay.

### Manual

Copy `custom_components/nefiteasy/` into the `custom_components` folder of your Home Assistant configuration and restart.

## 🔄 Migrating from ksya/ha-nefiteasy

Both integrations use the same `nefiteasy` folder and domain, so your configuration, entities and history stay. Only the source of the integration has to change. The steps depend on where you installed ksya/ha-nefiteasy from: the **Marketplace** built into recent Home Assistant versions, or **HACS**.

Make a backup first under *Settings → System → Backups*.

### Home Assistant Marketplace

> [!WARNING]
> **Never choose "Remove and uninstall"** (*Verwijderen en de-installeren*) on the ksya entry. That also deletes your Nefit configuration, including all entities and their history.

1. **Add this repository** as a custom repository (type **Integration**) and install **Nefit Easy (Bosch)**. If that works, restart Home Assistant and you are done.
2. If the install is refused with *"The nefiteasy directory belongs to ksya/ha-nefiteasy"*, the ksya entry still claims the folder. Release it as follows.

<details>
<summary><b>Release the folder from the ksya entry</b></summary>

**a. Stop Home Assistant Core** from the console of the Home Assistant machine or an SSH connection from your computer (with the SSH add-on, its port must be enabled):

```
ha core stop
```

> [!IMPORTANT]
> Don't use the web terminal inside Home Assistant (*Terminal & SSH* in the sidebar): it runs through Home Assistant Core and stops working as soon as Core is stopped, so you could not start it again from there.

Home Assistant must be stopped, otherwise it overwrites the change below.

**b. Mark the ksya entry as not installed.** The file is `.storage/marketplace.repositories` in your configuration folder (`/config` or `/homeassistant`, depending on the add-on). Make a copy first, then change only the entry with `"full_name": "ksya/ha-nefiteasy"`:

```diff
   "full_name": "ksya/ha-nefiteasy",
   ...
-  "installed_commit": "28880e4",
-  "installed": true,
+  "installed": false,
   ...
-  "version_installed": "v0.4.10",
```

Or in one go with `jq`:

```bash
cd /config/.storage
cp marketplace.repositories marketplace.repositories.bak
jq '(.data[] | select(.full_name == "ksya/ha-nefiteasy"))
    |= (.installed = false | del(.version_installed, .installed_commit))'   marketplace.repositories.bak > marketplace.repositories
```

**c. Start Home Assistant Core** again, from the console or SSH:

```
ha core start
```

**d. Install Nefit Easy (Bosch)** from this repository. The red message is gone now. Restart Home Assistant once more afterwards.

If something goes wrong, stop Core again, put `marketplace.repositories.bak` back and start Core.

</details>

After the switch, updates come from this repository. The ksya entry usually disappears from the list by itself. If it is still there and removing it again offers to delete your configuration, cancel and leave it.

### HACS

In HACS, removing a repository deletes the files in `custom_components/nefiteasy`, but not your configuration. The order matters: remove ksya first, then install this repository. The other way around, HACS deletes the files of this repository again.

1. In HACS, open **Nefit Easy** (ksya/ha-nefiteasy) and choose **Remove**. Don't restart Home Assistant yet.
2. Add `https://github.com/TheRealAndor/ha-nefiteasy` as a custom repository (type **Integration**) and download **Nefit Easy (Bosch)**.
3. Restart Home Assistant. Your Nefit configuration loads again with the new version.

If you restarted between step 1 and 2 by accident, the integration shows as *not loaded*. Your configuration is still there; it loads again after step 2 and 3.

## ⚙️ Configuration

[![Open your Home Assistant instance and start setting up Nefit Easy (Bosch).](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=nefiteasy)

1. Use the button above, or go to **Settings → Devices & services → Add integration** and search for **Nefit Easy (Bosch)**.
2. Enter the **serial number**, **access key** and **password** of your thermostat, *without spaces*. Serial number and access key are on the sticker of the thermostat; the password is the one you set in the Nefit Easy app.
3. Choose the minimum and maximum temperature and the temperature step for the thermostat.

Many entities are disabled by default. Enable the ones you need on the device page; disabled entities are not polled.

### Options

Change the settings later under **Settings → Devices & services → Nefit Easy (Bosch) → ⚙️ Configure**. Home Assistant reloads the integration after saving.

> [!TIP]
> **Polling is configurable.** The original integration polls every 60 seconds, and the only way to change that was to edit the code ([ksya#213](https://github.com/ksya/ha-nefiteasy/issues/213), [ksya#192](https://github.com/ksya/ha-nefiteasy/issues/192), [ksya#47](https://github.com/ksya/ha-nefiteasy/issues/47)). Here you set the **poll interval** and the **request timeout** in the options. The interval applies to the status and every enabled entity.

| Option | Default | Range | Description |
| - | :-: | :-: | - |
| Minimum temperature | 10 °C | 5–35 °C | Lowest target temperature you can set from Home Assistant |
| Maximum temperature | 28 °C | 5–35 °C | Highest target temperature you can set from Home Assistant |
| Temperature step | 0.5 °C | 0.1–1 °C | Step size of the target temperature |
| Poll interval | 60 s | 15–3600 s | How often the status and all enabled entities are read. Each poll is about 15 requests to the Bosch cloud, so a short interval means many more requests. The status is never faster than the Bosch cloud answers. |
| Request timeout | 20 s | 5–60 s | How long to wait for one answer before retrying or reconnecting. The Bosch cloud often needs 10–20 s; a shorter timeout causes more reconnects. |

## 🧩 Entities

The entity IDs below are those for the default device name **Nefit**. If you renamed the device, yours differ (for example `sensor.living_room_status`); check them on the device page.

### Thermostat

`climate.nefit`: room temperature, target temperature and the presets **Manual** and **Clock** (follow the program). `hvac_action` is `heating` while the boiler heats the house (not for hot water).

### Connection

| Entity | Description |
| - | - |
| `binary_sensor.nefit_bosch_cloud_connection` | `on` while Home Assistant gets answers from the thermostat. Stays available during an outage. |

| Attribute | Meaning |
| - | - |
| `last_success` | Last time the thermostat answered |
| `disconnected_since` | Start of the current outage (empty when connected) |
| `last_error` / `last_error_at` | Reason and time of the last failure, kept after recovering |
| `reconnects` | Number of reconnects since Home Assistant started |

<details>
<summary><b>Sensors</b></summary>

| Key | Name | Unit | Default | Description |
| - | - | :-: | :-: | - |
| `status` | Status | | ✅ | Boiler display code with explanation, see *Status codes* below |
| `burner_activity` | Burner activity | | ✅ | What the boiler heats now: `central_heating`, `hot_water` or `idle`. Attribute `code` has the raw value. |
| `supply_temperature` | Supply temperature | °C | ✅ | Temperature of the water to the radiators |
| `outdoor_temperature` | Outdoor temperature | °C | ✅ | Outdoor temperature |
| `system_pressure` | System pressure | bar | ✅ | Water pressure of the heating system |
| `actual_power` | Power | % | ✅ | Current burner power |
| `year_total` | Year total | m³ | ✅ | Gas used since 1 January, usable in the Energy dashboard. Converted from kWh for natural gas. |
| `gas_hot_water_yesterday` | Gas hot water yesterday | m³ | ✅ | Gas used for hot water on the newest day in the history of the thermostat, normally yesterday. Attributes `date`, `energy_kwh` and `average_outdoor_temperature`. |
| `gas_heating_yesterday` | Gas heating yesterday | m³ | ✅ | The same for central heating |
| `inhouse_temperature` | Inhouse temperature | °C | ❌ | Room temperature (also in the thermostat) |
| `target_temperature` | Target temperature | °C | ❌ | Target temperature (also in the thermostat) |
| `hot_water_operation` | Hot water operation | | ❌ | Hot water program, for example `follow-ch` (follow the heating program) |
| `refill_needed` | Refill needed | | ❌ | Water pressure too low, refill the system |
| `system_leaking` | System leak detected | | ❌ | Pressure keeps dropping |
| `ignition_status` | Ignition status | | ❌ | Burner ignition failure |
| `closing_valve_status` | Gas valve status | | ❌ | Gas valve fault |
| `maintenance_request` | Boiler maintenance required | | ❌ | Service of the boiler needed |
| `firmware_version` | Firmware version | | ❌ | Firmware of the thermostat |
| `hardware_version` | Hardware revision | | ❌ | Hardware revision of the thermostat |

</details>

<details>
<summary><b>Switches, select and numbers</b> (all disabled by default)</summary>

| Key | Type | Description |
| - | - | - |
| `active_program` | select | Clock program 1 or 2 |
| `hot_water` | switch | **Snel warm water** in the app, for the current user mode; see *Hot water* below |
| `hot_water_follows_program` | switch | **Volgens programma** in the app; see *Hot water* below |
| `hot_water_program` | binary sensor | Hot water period of the program; see *Hot water* below |
| `holiday_mode` | switch | Holiday mode; set the period in the Nefit Easy app |
| `fireplace_mode` | switch | Other rooms stay warm while a fire burns in the room with the thermostat |
| `today_as_sunday` / `tomorrow_as_sunday` | switch | Use the Sunday program today or tomorrow |
| `preheating` | switch | Preheating |
| `weather_dependent` | switch | Weather compensation based on the outdoor temperature. Ask your installer before using it. |
| `lockui` | switch | Lock the buttons of the thermostat |
| `shower_timer` | switch | Cold water from the hot tap after the shower time has passed |
| `shower_timer_duration` | number | Shower time in minutes |
| `temperature_adjustment` | number | Calibrate the measured room temperature (−2 to +2 °C) |
| `home_entrance_detection` | switch | One switch `Presence <phone>` per phone that is set up for presence detection in the app |

</details>

<details>
<summary><b>Hot water</b></summary>

The entities follow the hot water settings of the Nefit Easy app. Measured on a Nefit Easy with a combi boiler in November 2026.

| Entity | In the app | What it does |
| - | - | - |
| `binary_sensor.nefit_hot_water_state` | | `on` while hot water is on, as the thermostat reports it. Enabled by default. |
| `switch.nefit_hot_water` | Home → **Snel warm water** | Turns hot water on or off. The thermostat keeps one value for the manual and one for the clock user mode; the switch always shows and changes the one of the current mode. Unavailable while *follows program* is off, like the app hides it then. |
| `switch.nefit_hot_water_follows_program` | Programma → Warm water → **Volgens programma** | `on`: hot water follows the program and the switch above. `off`: hot water is always on. |
| `binary_sensor.nefit_hot_water_program` | | `on` during a hot water period of the program. Attributes `since`, `next_switchpoint` (for example `Sa 17:00`) and `next_state`. Disabled by default. |

**In the clock user mode the program turns `hot_water` on at the start of a hot water period** (measured at 17:00). At the end of a period nothing changed in two measurements at 23:00: the switch and the hot water state stayed `on`. To turn hot water off at night, turn the switch off yourself, for example with an automation on `binary_sensor.nefit_hot_water_program`. In the manual user mode the program does nothing and the switch keeps its value.

Changes show within a few seconds. What "off" means at the tap depends on the boiler; see its manual. `sensor.nefit_burner_activity` shows `hot_water` while the boiler heats water.

</details>

<details>
<summary><b>Status codes</b></summary>

| Code | Meaning |
| :-: | - |
| -H | Central heating active |
| =H | Hot water active |
| 0C, 0L, 0U | System starting |
| 0E | System waiting |
| 0H | System standby |
| 0A, 0Y | System waiting (boiler cannot transfer heat to central heating) |
| 2E, H07 | Boiler water pressure too low |
| 2F, 2L, 2P, 2U, 4F, 4L | Sensors measured an abnormal temperature |
| 6A, 6C | Burner doesn't ignite |
| rE | System restarting |

The sensor shows the code with its meaning, for example `-H: central heating active`.

</details>

## 💡 Examples

Adjust the entity IDs and the notification service (`notify.mobile_app_...`) to your own setup.

<details>
<summary><b>Notify me when the Bosch cloud connection is down for 15 minutes</b></summary>

```yaml
automation:
  - alias: "Nefit: connection lost"
    triggers:
      - trigger: state
        entity_id: binary_sensor.nefit_bosch_cloud_connection
        to: "off"
        for: "00:15:00"
    actions:
      - action: notify.mobile_app_my_phone
        data:
          title: "Nefit Easy offline"
          message: >
            No answer from the Bosch cloud since
            {{ state_attr('binary_sensor.nefit_bosch_cloud_connection', 'disconnected_since') }}.
            Reason: {{ state_attr('binary_sensor.nefit_bosch_cloud_connection', 'last_error') }}
```

Most outages are on the Bosch side and the integration reconnects by itself as soon as the cloud is back. Reloading the integration is not needed.

</details>

<details>
<summary><b>Warn when the water pressure is too low</b></summary>

```yaml
automation:
  - alias: "Nefit: low water pressure"
    triggers:
      - trigger: numeric_state
        entity_id: sensor.nefit_system_pressure
        below: 1.0
        for: "00:10:00"
    actions:
      - action: notify.mobile_app_my_phone
        data:
          message: "Heating pressure is {{ states('sensor.nefit_system_pressure') }} bar, top up the system."
```

</details>

<details>
<summary><b>Lower the temperature when everyone has left, follow the program when someone is home</b></summary>

```yaml
automation:
  - alias: "Nefit: away"
    triggers:
      - trigger: state
        entity_id: zone.home
        to: "0"
        for: "00:30:00"
    actions:
      - action: climate.set_temperature
        target:
          entity_id: climate.nefit
        data:
          temperature: 16

  - alias: "Nefit: home again"
    triggers:
      - trigger: numeric_state
        entity_id: zone.home
        above: 0
    actions:
      - action: climate.set_preset_mode
        target:
          entity_id: climate.nefit
        data:
          preset_mode: Clock
```

</details>

<details>
<summary><b>Start a floor heating pump while the boiler heats</b></summary>

```yaml
automation:
  - alias: "Nefit: floor heating pump"
    triggers:
      - trigger: state
        entity_id: sensor.nefit_status
    actions:
      - action: >
          {{ 'switch.turn_on' if trigger.to_state.state.startswith('-H')
             else 'switch.turn_off' }}
        target:
          entity_id: switch.floor_heating_pump
```

The status is polled every 60 seconds by default, so the pump follows the boiler with up to a minute of delay. A shorter **poll interval** in the options makes it follow faster.

</details>

<details>
<summary><b>Dashboard card</b></summary>

```yaml
type: vertical-stack
cards:
  - type: thermostat
    entity: climate.nefit
    features:
      - type: climate-preset-modes
        style: icons
        preset_modes: [Manual, Clock]
  - type: entities
    entities:
      - sensor.nefit_status
      - sensor.nefit_system_pressure
      - sensor.nefit_supply_temperature
      - sensor.nefit_outdoor_temperature
      - binary_sensor.nefit_bosch_cloud_connection
```

</details>

**Gas usage:** under *Settings → Dashboards → Energy → Gas consumption*, add either

- **Nefit gas hot water** and **Nefit gas heating** (recommended). These are statistics with the usage per day, split into hot water and heating, on the day it was used. The first time, the integration imports about a year of history from the thermostat; after that it adds each new day. The thermostat adds a day after it has ended, so today shows up tomorrow. In the Energy dashboard the values are on midnight of each day.
- or `sensor.nefit_year_total`, which updates during the day but is not split. It counts from 1 January and resets each year; the Energy dashboard handles that.

Use one of the two, not both, or the usage is counted twice.

<details>
<summary><b>Gas usage history</b></summary>

The thermostat keeps one record per day since it was installed, with the gas used for hot water and for central heating in kWh and the average outdoor temperature ([protocol notes by marcelrv](https://github.com/marcelrv/nefit_easy_protocol/blob/master/gasusage.md)). The integration checks once an hour for a new day; this is one small request. kWh is converted to m³ with the factor of the thermostat for natural gas (0.12307692, a calorific value of 29 MJ/m³), the same as `year_total`.

The statistics need the recorder, which is on in a standard installation. Without it only the two sensors are updated. The statistics are not linked to an entity: they stay when you remove the integration, and you can remove them under *Developer tools → Statistics*.

</details>

## 🛠️ Improvements compared to the original

Based on upstream 0.4.10. The changes mainly target the unstable connection to the Bosch cloud ([ksya/ha-nefiteasy#462](https://github.com/ksya/ha-nefiteasy/issues/462)).

<details>
<summary><b>Connection</b></summary>

- **Retry, then reconnect in the same update.** A missed status answer is retried once; if that fails too, the connection is rebuilt right away instead of after several poll cycles.
- **Request timeout of 20 s instead of 9 s.** Measurements in #462 showed replies of 9–20 s on sessions that kept working; with 9 s each of those caused a retry or reconnect.
- **Stale connections are closed first.** This fixes `ValueError: There is already a scheduled event of name: Whitespace Keepalive` and the old session's `session_end` killing the new one. A background connect attempt and a leftover keepalive are cleaned up too.
- **A session that comes up late is reused** instead of torn down, and only one connect procedure runs at a time.
- **A slow optional endpoint keeps its previous value** instead of failing the whole update.
- **Clear reasons in the log** when a reconnect fails, and the harmless "Legacy XMPP 0.9 protocol detected" warning is filtered out.

</details>

<details>
<summary><b>New features</b></summary>

- **Connection sensor** `Bosch cloud connection` with the time and reason of outages. It has its own update signal, because Home Assistant does not notify entities after a second failed update in a row.
- **Hot water that works** (0.5.0). The `hot_water` switch sprang back after every change ([ksya#44](https://github.com/ksya/ha-nefiteasy/issues/44)): it wrote the setting of the current user mode but showed the hot water state, which stays `on` while *follows program* is off in the app. Now the switch shows the setting it writes in both user modes, with new entities for *follows program*, the hot water state and the program. See *Hot water* under *Entities*.
- **Burner activity sensor** (0.5.0): central heating, hot water or idle.
- **Gas usage per day, split into hot water and heating** (0.5.0, [ksya#194](https://github.com/ksya/ha-nefiteasy/issues/194)): statistics for the Energy dashboard with about a year of history, and sensors for yesterday. See *Gas usage* under *Examples*.
- **Options** (0.5.0): change the temperature limits, the poll interval and the request timeout after setup, without editing the code ([ksya#213](https://github.com/ksya/ha-nefiteasy/issues/213), [ksya#47](https://github.com/ksya/ha-nefiteasy/issues/47)).
- **Diagnostics download** (*Settings → Devices & services → Nefit Easy (Bosch) → ⋮ → Download diagnostics*) with connection state, timeouts, polled endpoints and values. Serial number, access key, password and presence phone names are removed.

</details>

<details>
<summary><b>Startup and Home Assistant compatibility</b></summary>

- **Presence profiles are read in the background**, which fixes "Setup of switch platform nefiteasy is taking over 10 seconds". A slow profile no longer drops the others.
- **No deprecation warnings on Home Assistant 2026.11**: the thermostat uses the new `native_*` temperature properties, which the original will need before 2027.11. Older Home Assistant versions keep working.
- **Authentication errors show a notification again** (`hass.components` was removed from Home Assistant).
- Deprecated `CONNECTION_CLASS` removed ([ksya#479](https://github.com/ksya/ha-nefiteasy/issues/479)), and entities no longer read `None` before the first update.

</details>

<details>
<summary><b>Home Assistant quality scale (Bronze)</b></summary>

- **Reauthentication works.** When the Bosch cloud rejects the access key or password, Home Assistant asks for new ones under *Settings → Devices & services* instead of failing to start a flow that did not exist. A wrong password during startup is now recognised as such, not as a connection problem that keeps retrying.
- **Clearer setup form** with a description for each field, and an unexpected error shows a message instead of a broken form.
- **Entity names follow the device name** (`has_entity_name`). Entity IDs stay the same; friendly names now start with the device name, for example *Nefit Status*.
- Under the hood: the connection lives in `coordinator.py` and is stored in the config entry (`runtime_data`), the climate entity waits the same 20 s as other requests, and more tests cover the config flow.

</details>

See the [releases](https://github.com/TheRealAndor/ha-nefiteasy/releases) for what changed in each version.

## 🗑️ Removing

1. Go to **Settings → Devices & services → Nefit Easy (Bosch)**.
2. Open the menu (⋮) next to the thermostat and choose **Delete**. Home Assistant removes the device and its entities; the thermostat and the Nefit Easy app keep working as before.
3. To remove the integration files too, uninstall **Nefit Easy** in HACS (or the Marketplace), or delete `custom_components/nefiteasy/` for a manual installation, and restart Home Assistant.

## 🐞 Troubleshooting

1. Check the **Bosch cloud connection** sensor. If it is `off`, look at `last_error`. Most outages are on the Bosch side and pass by themselves; the Nefit Easy app usually has trouble at the same time.
2. **Download the diagnostics** and attach the file when you [open an issue](https://github.com/TheRealAndor/ha-nefiteasy/issues).
3. For more detail, enable debug logging:

```yaml
logger:
  default: info
  logs:
    custom_components.nefiteasy: debug
    aionefit: debug
```

<details>
<summary><b>Cannot connect on an older Debian-based installation</b></summary>

On self-installed Home Assistant on Debian 10 (Buster) or similar, the OpenSSL defaults could block the connection to the Bosch cloud (*"Timeout while connecting to Bosch cloud. Retrying in the background"*). Edit `/etc/ssl/openssl.cnf` and set:

```
MinProtocol = None
CipherString = DEFAULT
```

See the [Debian release notes](https://www.debian.org/releases/buster/amd64/release-notes/ch-information.en.html#openssl-defaults). Home Assistant OS is not affected.

</details>

## 🙏 Credits

- **[ksya](https://github.com/ksya)** created the original [ha-nefiteasy](https://github.com/ksya/ha-nefiteasy). ksya no longer has the thermostat since 2021 ([#74](https://github.com/ksya/ha-nefiteasy/issues/74#issuecomment-929656113): *"I cannot test since I don't have the thermostat anymore."*); since then the original has mainly been kept alive by **[RobBie1221](https://github.com/RobBie1221)** and other contributors.
- **[marconfus](https://github.com/marconfus)** for the [aionefit](https://github.com/marconfus/aionefit) library and [ha-nefit-ng](https://github.com/marconfus/ha-nefit-ng).
- **[wrburton](https://github.com/wrburton)** and **[GerbenJavado](https://github.com/GerbenJavado)** for the connection measurements in [#462](https://github.com/ksya/ha-nefiteasy/issues/462).

Nefit and Bosch are trademarks of their respective owners. This is an unofficial integration, not affiliated with or endorsed by Bosch.
