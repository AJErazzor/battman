<!-- This folder is Battman's built-in guide. In Home Assistant it's the Help view on the Battman dashboard; on GitHub you're reading the same pages. -->

# Battman help

Battman runs a home battery from Home Assistant. It works with a Sigenergy system, Amber Electric prices and a Solcast solar forecast. As prices change through the day it decides whether to charge the battery, sell from it or just run the house, and its dashboard lets you see what it's doing and steer it.

This guide is written from Battman's own code, so it describes what your installed version does.

> [!NOTE]
> The guide doesn't cover all of Battman yet. These are its pages so far.

## In this guide

**Getting started**

- [The Battman device page](start/device-page.md): the two buttons on the Battman device (**Create dashboard** and **Create automations**), what each one does, and what it never does.

**Using Battman**

- [Settings](intermediate/settings.md): every section of the Settings view and what each setting does.

**Troubleshooting**

- [Battman's Repairs](help/repairs.md): every problem Battman can report under **Settings → Repairs**, what causes it and how to fix it.

## Finding the guide

- **On the Battman dashboard** it's the **Help** tab, the last one.
- **No Help tab?** Turn on **Show help**. If it's already on, turn it off and on again. See [Showing or hiding the guide](#showing-or-hiding-the-guide).
- **On GitHub** these pages are in the `custom_components/battman/guide` folder of the Battman repository.

## Showing or hiding the guide

The **Show help** switch is on the Battman dashboard's **Settings** view, under **Dashboard options**. It's on unless you turn it off.

- **Turning it off** takes the Help view off the Battman dashboard at `/battman`. Nothing else on the dashboard changes.
- **Turning it on** adds the Help view back as the last tab, if the dashboard hasn't got one. Nothing else on the dashboard changes.
- **While it's off**, **Create dashboard** makes the dashboard without the Help view.

When Battman changes the dashboard, Home Assistant shows "Your dashboard was updated. Refresh to see changes?" in any browser that has it open: press **Refresh** to see the Help tab come or go.

Battman only changes the dashboard when you turn the switch on or off. If you delete or move the Help view yourself, it stays as you left it. If there's no Help tab while the switch is on, turn it off and on again.

Battman's Help view is the view at `/battman/help` that holds the guide card. When you turn the switch on, any view at `/battman/help` counts as one, so Battman adds nothing beside a view of your own there. When you turn it off, Battman only takes away a view at that address with the guide card on it.

If Battman can't make the change, a notification says why:

| What it found | Message |
|---|---|
| No dashboard at `/battman` (turning it on) | "Show help is on, but there's no Battman dashboard at /battman to add the Help view to. Press Create dashboard on the Battman device: a new Battman dashboard includes it." |
| Something at `/battman` Battman can't change (turning it on) | "Show help is on, but Battman can't change what's at /battman (a dashboard written in YAML, one with no saved views yet, or something that isn't a dashboard), so nothing changed. To add the Help view yourself, add a view with the card type: custom:battman-guide." |
| A dashboard written in YAML at `/battman` (turning it off) | "Show help is off, but the dashboard at /battman is written in YAML, so Battman can't change it. Remove the Help view yourself if you don't want it." |
| Something went wrong (building the view or saving the dashboard) | "Could not add the Help view:" or "Could not remove the Help view:" followed by the reason. |

### Adding the guide yourself

The guide is one card, **Battman Help** (`custom:battman-guide`). It reads best on a view of its own in panel layout, on any dashboard:

```yaml
type: panel
path: help
title: Help
icon: mdi:help-circle-outline
cards:
  - type: custom:battman-guide
```

## The status line

In Home Assistant, the line at the top of the guide shows Battman as it is right now:

| Item | What it shows |
|---|---|
| **Active** | Whether Battman's engine is switched on: the Active switch on the Battery mode card. While it's off, the engine doesn't run by itself. |
| **Mode** | The battery mode now, set by the engine or by you. |
| **Last engine run** | How long ago the engine last decided. |
| **Curtail** | Whether Curtail is on. While it's on, nothing is exported to the grid. |
| **Repairs** | How many of Battman's Repairs are open, with a link to [what they mean](help/repairs.md). |

A value Battman can't read shows as "—" or "not found". The guide never fills a gap with a made-up value.

## Linking to a page

Every page and section has its own address, so you can link to it from a button or a note on any dashboard. Point the link at your Help view with the page added. For example, `/battman/help?page=help/repairs#packages-not-loaded` opens the Repairs page at "Battman's package files aren't loaded". The **#** button next to each heading copies the address of that section.
