# Battman's Repairs

When Battman finds a problem it can't fix by itself, it says so under **Settings → Repairs** in Home Assistant. This page explains each one: what it means, why it appears and how to fix it. The headings are the titles you'll see in Repairs.

<!-- guide:repairs -->

Most Repairs clear by themselves once the problem is fixed, usually after the restart or reload the fix asks for. They fall into four groups:

| Group | Repairs |
|---|---|
| Updating | [Restart to finish updating Battman](#restart-required) |
| Your Home Assistant setup | [Battman's package files aren't loaded](#packages-not-loaded), [Battman's engine automations didn't load](#engine-not-loaded), [Battman automations didn't load](#notifications-not-loaded), [Battman's themes aren't loaded](#themes-not-loaded), [Battman needs other dashboard cards](#missing-dependencies) |
| The integrations Battman reads | [Battman can't find entities it uses](#missing-entities), [An integration Battman uses needs updating](#integration-too-old), [Battman's NEM mix card needs OpenNEM](#opennem-missing), [Pick your OpenNEM region](#opennem-choose), [Battman no longer uses some of your Configure choices](#map-choice-ignored) |
| The dashboard and cards | [Battman could not create its dashboard](#dashboard-unavailable), [Battman is using your own card files](#local-cards) |

## Updating

<a id="restart-required"></a>
### Restart to finish updating Battman

**What it means:** a new version of Battman has been installed (usually by HACS), but Home Assistant is still running the old one. The new version only starts when Home Assistant restarts.

**Why it appears:** every 5 minutes Battman compares the version on disk with the one that's running. It appears for any difference, including going back to an older version.

**Fix:** select the Repair and press **Submit** to restart Home Assistant (it asks "Battman *new* is installed, but Home Assistant is still running Battman *old*. Restart now to finish the update?"). Or restart Home Assistant any other way. It clears when Home Assistant starts again.

## Your Home Assistant setup

Battman writes its engine, sensors and themes into your Home Assistant configuration folder. Home Assistant only reads them if `configuration.yaml` includes those folders and files. These Repairs mean one of them isn't being read.

<a id="packages-not-loaded"></a>
### Battman's package files aren't loaded

**What it means:** Battman's sensors and helpers don't exist, so its engine and most of its cards can't work. The Repair lists what's missing.

**Why it appears:** Battman writes them as package files into `packages/battman/`, and Home Assistant isn't reading that folder.

**Fix:** add this to `configuration.yaml` (or check that your existing `packages:` line uses `!include_dir_named packages`), then restart Home Assistant:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

<a id="engine-not-loaded"></a>
### Battman's engine automations didn't load

**What it means:** some of the automations and scripts that make up Battman's engine aren't running. The Repair names them.

**Why it appears:** Battman wrote them into `automations.yaml` and `scripts.yaml`, and Home Assistant didn't load them after reloading.

**Fix:**

1. Check that `configuration.yaml` has `automation: !include automations.yaml` and `script: !include scripts.yaml`. They're there by default.
2. Look in the Home Assistant log (**Settings → System → Logs**) for an error about `automations.yaml` or `scripts.yaml`. A YAML mistake anywhere in either file stops Home Assistant loading it.
3. Restart Home Assistant, or press **Create automations** on the [Battman device](../start/device-page.md#create-automations).

<a id="notifications-not-loaded"></a>
### Battman automations didn't load

**What it means:** Battman's notification automations (the price and off-grid alerts and the Live Activity) were written, but Home Assistant didn't load them. The Repair names them.

**Why it appears:** for the same reasons as [the engine's](#engine-not-loaded).

**Fix:** check `configuration.yaml` has `automation: !include automations.yaml` and `script: !include scripts.yaml`, then press **Create automations** on the [Battman device](../start/device-page.md#create-automations) again.

<a id="themes-not-loaded"></a>
### Battman's themes aren't loaded

**What it means:** Battman's themes are missing, so its views and cards can't find their colours and show "no theme".

**Why it appears:** Battman writes its themes into `themes/battman/`, and Home Assistant isn't reading that folder.

**Fix:** add this to `configuration.yaml` (or check that your existing `themes:` line uses `!include_dir_merge_named themes`), then restart Home Assistant:

```yaml
frontend:
  themes: !include_dir_merge_named themes
```

<a id="missing-dependencies"></a>
### Battman needs other dashboard cards

**What it means:** some of Battman's cards are built on other people's cards, and one or more of them isn't installed. The Repair lists which, with a link to each.

**Why it appears:** Battman needs **button-card**, **card-mod** and **modern-circular-gauge**. It checks for them when it starts.

**Fix:** install each one with HACS (they're under **Frontend**), restart Home Assistant, then refresh your browser. Because Battman only checks when it starts, the Repair stays until that restart.

## The integrations Battman reads

Battman reads Sigenergy, Amber and Solcast entities by their own names. These Repairs mean one of them can't be read as Battman expects.

<a id="missing-entities"></a>
### Battman can't find entities it uses

**What it means:** entities Battman reads by name don't exist, or are disabled. The Repair lists each one, what Battman uses it for, which integration should provide it, and whether it's "not found" or "disabled". Until it's fixed, whatever uses that entity shows a note or a blank, never a made-up value.

**Why it appears:** Battman needs entities from three integrations:

- **Sigenergy-Local-Modbus**, version 1.1.0 or newer. Some of the entities Battman needs are disabled when the integration is first set up.
- **Amber**, through **amber2mqtt** (MQTT).
- **Solcast PV Forecast**.

It checks when Home Assistant starts and whenever entities change.

**Fix:**

- **"disabled"**: enable the entity under **Settings → Entities**.
- **"not found"**: install or set up the integration named. If the entity exists under a different name, rename it to the name in the Repair.

This Repair doesn't report an entity that exists but is unavailable (for example, when its integration can't reach the device).

<a id="integration-too-old"></a>
### An integration Battman uses needs updating

**What it means:** your Sigenergy-Local-Modbus integration is older than 1.1.0. Battman uses entity names that only exist from 1.1.0 on.

**Fix:** update it in HACS, then restart Home Assistant. If its entities were made by an older version they may still have older names; [Battman can't find entities it uses](#missing-entities) then names any Battman can't find.

<a id="opennem-missing"></a>
### Battman's NEM mix card needs OpenNEM

**What it means:** the NEM mix card on the Power view shows where your region's electricity comes from and goes. Its figures come from the **OpenNEM** integration, which isn't installed, so the card is empty.

**Fix:** if you want the card, in HACS search for **OpenNEM**, download it and restart Home Assistant. Then go to **Settings → Devices & services → Add integration → OpenNEM** and pick your region. Battman finds it by itself.

**Don't want it?** OpenNEM is optional and nothing else in Battman uses it. Press **Ignore** on the Repair and remove the NEM mix card from your dashboard.

<a id="opennem-choose"></a>
### Pick your OpenNEM region

**What it means:** OpenNEM has more than one region, and Battman doesn't know which one its NEM sensors should read. Until you pick one, the NEM sensors are unavailable.

**Fix:** go to **Settings → Devices & services → Battman**, select the gear icon (**Configure**), and pick the region.

<a id="map-choice-ignored"></a>
### Battman no longer uses some of your Configure choices

**What it means:** Battman's **Configure** screen still holds choices it no longer uses. Battman reads the Sigenergy, Amber and Solcast entities by their own names, so those choices change nothing.

**Fix:** go to **Settings → Devices & services → Battman**, select the gear icon (**Configure**), and save. Entries that are no longer there are dropped. If one of your entities has a different name from the one Battman uses, rename it under **Settings → Entities**.

## The dashboard and cards

<a id="dashboard-unavailable"></a>
### Battman could not create its dashboard

**What it means:** Battman tried to make its dashboard at `/battman` and couldn't. The Repair shows the error.

**Why it appears:** Home Assistant has no official way for an integration to make a dashboard, so Battman uses the same steps Home Assistant uses for its own. If a Home Assistant update changes those steps, this can fail.

**Fix:** press **Create dashboard** on the [Battman device](../start/device-page.md#create-dashboard), or run the action `battman.create_dashboard`. If it still fails, report it on [Battman's issues page](https://github.com/AJErazzor/battman/issues) with the error. The Repair clears when the dashboard is made.

<a id="local-cards"></a>
### Battman is using your own card files

**What it means:** some Battman cards are drawn from your own files in `battman/cards/` (in your Home Assistant configuration folder) instead of the ones Battman ships. The Repair names them. Those cards don't change when Battman updates.

**Why it appears:** that folder is for trying out changes to a card. A file there with the same name as one of Battman's cards replaces it; a file with any other name adds a card of your own.

**Fix:** if you're finished trying something out, delete the file from `battman/cards/` to go back to Battman's version. The Repair clears when the folder has no card files.
