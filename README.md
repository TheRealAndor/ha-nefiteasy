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

The Nefit Easy is a smart thermostat from Bosch for Nefit gas boilers. It has no local API: the thermostat and the Nefit Easy app talk to each other through the Bosch cloud. This integration connects Home Assistant to that same cloud, with the serial number, access key and password of the thermostat, and polls it every 60 seconds.

You get a thermostat entity to read and set the room temperature and the program, plus sensors and switches for the boiler: status codes, supply and outdoor temperature, water pressure, gas usage, hot water, holiday and fireplace mode, presence detection and more. The integration is written for the first generation of Bosch cloud thermostats; the Nefit Easy is the one it is tested with.

The integration meets the [Bronze tier](https://developers.home-assistant.io/docs/core/integration-quality-scale/) of the Home Assistant integration quality scale, see [`quality_scale.yaml`](custom_components/nefiteasy/quality_scale.yaml). HACS and the Marketplace do not require this; following the quality scale is a way to raise the quality of the integration, using the same rules as the integrations built into Home Assistant.

## ✨ Highlights

| | |
| - | - |
| 🔁 **Self-healing connection** | A lost or silent Bosch cloud session is detected and rebuilt within the same update, so entities no longer stay `unavailable` for minutes. |
| 📶 **Connection sensor** | `Bosch cloud connection` shows whether Home Assistant gets answers, since when it doesn't, and why. It stays available during an outage. |
| 🩺 **Diagnostics download** | One click gives you a file with the connection state, errors and values, with all secrets removed. Ideal for issues. |
| 🐢 **Patient with a slow cloud** | 20 s request timeout: slow but working replies no longer count as a dropped session. |
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
| `supply_temperature` | Supply temperature | °C | ✅ | Temperature of the water to the radiators |
| `outdoor_temperature` | Outdoor temperature | °C | ✅ | Outdoor temperature |
| `system_pressure` | System pressure | bar | ✅ | Water pressure of the heating system |
| `actual_power` | Power | % | ✅ | Current burner power |
| `year_total` | Year total | m³ | ✅ | Gas used since 1 January, usable in the Energy dashboard. Converted from kWh for natural gas. |
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
| `hot_water` | switch | Hot water preheating |
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

The status is polled every 60 seconds, so the pump follows the boiler with up to a minute of delay.

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

**Gas usage:** add `sensor.nefit_year_total` under *Settings → Dashboards → Energy → Gas consumption*. It counts from 1 January and resets each year; the Energy dashboard handles that.

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
