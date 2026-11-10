<!-- This folder is Battman's built-in guide. In Home Assistant it's the Help view on the Battman dashboard; on GitHub you're reading the same pages. -->

# Battman help

Battman runs a home battery from Home Assistant. It works with a Sigenergy system, Amber Electric prices and a Solcast solar forecast. As prices change through the day it decides whether to charge the battery, sell from it or just run the house, and its dashboard lets you see what it's doing and steer it.

This guide is written from Battman's own code, so it describes what your installed version does.

> [!NOTE]
> The guide is new, and more pages arrive with each release: installing Battman, the Power view, every card, the settings, how the engine decides, and a guide for developers.

## In this guide

**Getting started**

- [The Battman device page](start/device-page.md): the three buttons on the Battman device (**Create dashboard**, **Create help view** and **Create automations**), what each one does, and what it never does.

**Troubleshooting**

- [Battman's Repairs](help/repairs.md): every problem Battman can report under **Settings → Repairs**, what causes it and how to fix it.

## Finding the guide

- **On the Battman dashboard** it's the **Help** tab, the last one.
- **No Help tab?** Dashboards made before the guide existed don't have one, because Battman never changes your dashboard by itself. Open the [Battman device](start/device-page.md#create-help-view) and press **Create help view**.
- **On GitHub** these pages are in the `custom_components/battman/guide` folder of the Battman repository.

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
