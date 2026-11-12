# The Battman device page

Battman has a device page in Home Assistant with two buttons. To open it, go to **Settings → Devices & services → Battman** and select **Battman** in the list (Home Assistant lists it under **Services**, as Battman isn't a physical device). The buttons are under **Controls**.

| Button | What it does | What it never does |
|---|---|---|
| [Create dashboard](#create-dashboard) | Makes the Battman dashboard at `/battman`, if there's nothing there | Change or replace a dashboard that's already there |
| [Create automations](#create-automations) | Adds any of Battman's automations and scripts that are missing | Change ones that already exist |

Each button tells you what it did in a notification (the bell in the sidebar). Each one is also an action, so you can use it in a script or automation.

**Only an administrator can press them.** Anyone else gets "Only a Home Assistant administrator can press this button", and the actions refuse them too. An automation can still use the actions.

## Create dashboard

**Create dashboard** makes the Battman dashboard at `/battman`, with Battman's views: Power, Curvy, Pricy, Finances, Settings, Log, Theme and Help. It shows up in the sidebar as **Battman**. The Help view is left out while **Show help** is off ([Showing or hiding the guide](../README.md#showing-or-hiding-the-guide)).

- **It only creates.** If something is already at `/battman`, nothing changes and the notification says: "There's already a dashboard at /battman, so nothing was created. For a fresh Battman dashboard, delete that one first."
- **When it works**, the notification says: "Created the Battman dashboard at /battman. It's yours: edit it like any dashboard."
- **Battman makes the dashboard once by itself**, when you first add Battman. After that only this button (or the action) makes one.

### What updates with Battman, and what doesn't

The dashboard is yours: edit it like any other. When Battman updates:

- **The Battman cards on it update.** Every Battman card is drawn from Battman's own files, so it changes with each release.
- **The layout doesn't.** Which views there are, and which cards are on them, stay as they were made (or as you've arranged them). Battman never changes your dashboard by itself.

### Getting a fresh copy

To get Battman's current layout, for example after a release adds a card:

1. Go to **Settings → Dashboards**, select **Battman** and delete it. Anything you changed on it is lost.
2. Press **Create dashboard**.

### If it fails

The notification says "Could not create the Battman dashboard:" followed by the reason, and a Repair appears: see [Battman could not create its dashboard](../help/repairs.md#dashboard-unavailable).

### As an action

```yaml
action: battman.create_dashboard
```

Add `response_variable: result` and the action returns what happened (`created`, `url_path` and `message`) instead of posting a notification.

## Create automations

Battman's engine and its notifications are automations and scripts that Battman writes into your `automations.yaml` and `scripts.yaml`. **Create automations** adds any of them that are missing, and reloads automations and scripts so Home Assistant starts them.

It covers:

- **The engine**: the scripts "Battman engine", "Battman engine – inputs", "Battman engine – decide", "Battman engine – forecast" and "Battman apply scene", and the automations "Battman engine – main loop", "– watchdog", "– Sigen mode", "– curtail", "– SAPN override", "– override timer start", "– copy curves to next month", "– auto curve switcher" and "– armed scene (00:01)".
- **Notifications**: "Battman Live Activity – push" (a script), "Battman Live Activity – on/off", "– updates" and "– follow", "Battman Amber – cheap price alert", "Battman Amber – negative price alert", "Battman Amber – charge from the alert", "Battman Off-grid alert" and "Battman Spike alert".

Good to know:

- **It never changes one that exists.** Each automation and script is matched by its id, and only missing ones are written.
- **To put one back to Battman's version**, delete it (Settings → Automations & scenes), then press **Create automations**.
- **It brings back ones you deleted on purpose.** If you don't want an alert, switch it off under **Settings → Notifications** on the Battman dashboard, or turn the automation off, rather than deleting it.
- **It reloads all your automations and scripts**, not just Battman's, when it adds any, or when one of the engine's is in the file but Home Assistant hasn't loaded it. Otherwise it changes and reloads nothing.
- **Battman writes them once by itself**, when you first add it, and again for any that a new release adds. After that only this button (or the action) writes them.

What the notification says:

- "Created:" followed by the ids it added, when it added any.
- "All Battman automations and scripts already exist; nothing changed."
- "Could not create the Battman automations:" followed by the reason, when it couldn't write to `automations.yaml` or `scripts.yaml`, or Home Assistant didn't load the engine's.

If Home Assistant didn't load what Battman wrote, a Repair also says which: see [Battman's engine automations didn't load](../help/repairs.md#engine-not-loaded) and [Battman automations didn't load](../help/repairs.md#notifications-not-loaded). For the notification automations that Repair is the only sign: the message still says "Created:".

### As an action

```yaml
action: battman.create_automations
```

With `response_variable`, it returns `created` (the ids it added) and `message`.
