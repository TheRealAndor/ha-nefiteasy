# Backlog

Ideas and open work for upcoming versions. Tick an item when it ships and mention it in the release notes.

## Overview

**✨ Features**

- [ ] Repair issue during a long outage
- [ ] Options flow: poll interval and timeouts
- [ ] Dutch translation and translatable entity names
- [ ] Gas usage per day, split into hot water and heating
- [ ] Holiday mode that does not switch off after a minute
- [ ] Action to read or write any endpoint
- [ ] Icons for the Manual and Clock presets

**🧪 Quality**

- [ ] Verify the 20 s request timeout in a real installation
- [ ] Verify the hot water switch
- [ ] Automated tests for the reconnect logic
- [ ] Use the request timeout constant in the climate entity
- [ ] Remove unused imports

**🧹 Housekeeping**

- [ ] Submit to the HACS default repositories
- [ ] Keep up with upstream
- [ ] Offer the connection fixes upstream
- [ ] Mention in ksya#479 that this fork fixed it
- [ ] Delete the suppress-legacy-xmpp-warning branch

## ✨ Features

### Repair issue during a long outage

The `Bosch cloud connection` sensor shows an outage, but only people who look at it or build an automation notice it.

- Create a repair issue in **Settings → Repairs** when the connection has been down for a set time (for example 30 minutes), with the last error and the time it started
- Remove the issue automatically when the connection is back
- Keep it informational: most outages are on the Bosch side and the user cannot fix them

### Options flow: poll interval and timeouts

The poll interval is fixed at 60 seconds (`update_interval` in `__init__.py`). People with floor heating change the code to 15 seconds to follow the boiler status faster (ksya#213, ksya#192, ksya#47).

- Add the poll interval to the existing options step, with a sensible minimum (for example 15 s) so the Bosch cloud is not hammered
- Optionally the request timeout, now fixed at 20 s (`REQUEST_TIMEOUT`)
- Mention in the description that a short interval means more requests and that the status still depends on how fast the cloud answers

### Dutch translation and translatable entity names

Most users are Dutch, but there is only `translations/en.json`. Entity names are hard-coded in `const.py`, which also causes odd names (ksya#214, "Sensor name does not make sense").

- Switch entities to `has_entity_name` and `translation_key`, with the names in `strings.json`
- Add `translations/nl.json` for the config flow, options, entity names and status texts
- Check the effect on existing entity IDs: they must stay the same for current installations

### Gas usage per day, split into hot water and heating

The most requested feature (ksya#194). The thermostat keeps a gas usage history per day, split into hot water and central heating. The endpoint is described in the [Nefit Easy protocol notes by marcelrv](https://github.com/marcelrv/nefit_easy_protocol/blob/master/gasusage.md).

- Read the history pages and expose today's and yesterday's usage for hot water and heating as sensors usable in the Energy dashboard
- Optionally import the history as long-term statistics
- Useful for mindergas.nl (cooking and hot water versus heating)

### Holiday mode that does not switch off after a minute

Turning on `holiday_mode` from Home Assistant switches it off again after about a minute (ksya#173). The switch only sets the status; without an end date in the future the thermostat ends the holiday right away. Users work around it by setting a far-away end date in the app.

- When turning on, also write a start and end date, for example from now until a configurable number of days ahead, or until it is turned off
- Check the holiday mode endpoints and date format first (protocol notes or a capture of the app)

### Action to read or write any endpoint

An action such as `nefiteasy.get_endpoint` and `nefiteasy.set_endpoint` (ksya#46) for advanced users and to explore endpoints that have no entity yet.

- Return the answer as a response
- Keep writes behind a clear warning in the description

### Icons for the Manual and Clock presets

The thermostat card shows the presets without icons (ksya#341), because `Manual` and `Clock` are not Home Assistant's standard presets. Upstream wants to keep the names in line with the Nefit app.

- Keep the names and add icons through `icons.json` (climate `preset_mode` state attribute icons), for example `mdi:hand-back-right` for Manual and `mdi:clock-outline` for Clock
- Needs a `translation_key` on the climate entity (see *Dutch translation*)

## 🧪 Quality

### Verify the 20 s request timeout in a real installation

v0.4.10.5 raised the request timeout from 9 s to 20 s, based on measurements by wrburton in ksya#462.

- After a few days, check `reconnects` and `last_error` on the `Bosch cloud connection` sensor and compare with the number of outages before
- Check that updates during a slow Bosch cloud don't take so long that they overlap
- Write the result down in ksya#462

### Verify the hot water switch

ksya was not sure whether the `hot_water` switch ever worked (ksya#44). It writes to an endpoint that depends on clock or manual mode, but the state is read from `uiStatus`.

- Test it on a real thermostat in both modes and compare with the Nefit app
- Fix it or document what it actually does

### Automated tests for the reconnect logic

The tests cover entities, diagnostics and the connection sensor, but not the main changes of this fork.

- Retry once, then reconnect within the same update
- Stale transport closed and leftover keepalive removed before reconnecting
- A session that comes up after the connect timeout is reused
- A slow optional endpoint keeps its previous value
- `session_end` during our own reconnect is ignored

### Use the request timeout constant in the climate entity

`climate.py` still waits a fixed 9 s after setting the preset or temperature (`timeout=9`). Use `REQUEST_TIMEOUT` so a slow Bosch cloud does not cause an error there either.

### Remove unused imports

flake8 7 reports `EVENT_HOMEASSISTANT_STOP` in `__init__.py` and `ConfigType` in `config_flow.py` as unused (from upstream). CI passes because it uses an older flake8.

## 🧹 Housekeeping

### Submit to the HACS default repositories

The repository passes all HACS checks (v0.4.10.4 and later): brand icon, topics, releases, hassfest.

- Optionally let RobBie1221 know, since the domain is the same as ksya/ha-nefiteasy (which is not in HACS default)
- Fork `hacs/default`, add `TheRealAndor/ha-nefiteasy` alphabetically to the `integration` file on a new branch
- Open the PR from a personal account and fill in the template completely
- After merge: update the README installation section and the HACS badge

Review can take months.

### Keep up with upstream

Upstream `dev` is still active. Changes not in this fork yet:

- `c10a487` Fetch data before setting up the platforms (ksya#484, wrburton)
- Open: ksya#480 (split the connection and coordinator out of `__init__.py`), ksya#481 (recover from drops and outages), ksya#482 (presence lookup failure). These overlap with this fork's connection changes; compare and take over what is better

Check `git log dev..upstream/dev` now and then.

### Offer the connection fixes upstream

The comment in ksya#462 offers PRs against upstream `dev`. If RobBie1221 or wrburton are interested, split the changes into small PRs that fit alongside wrburton's work, so all users benefit.

### Mention in ksya#479 that this fork fixed it

ksya#479 reports the deprecated `CONN_CLASS_CLOUD_POLL` constant. This fork removed `CONNECTION_CLASS` in v0.4.10.3. A short comment can point users there.

### Delete the suppress-legacy-xmpp-warning branch

The branch is merged into `dev` (v0.4.10.3) and can be deleted on GitHub.
