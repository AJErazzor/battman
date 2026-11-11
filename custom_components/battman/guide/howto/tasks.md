# How do I…?

Pick what you want to do. Each task gives the steps and the cards you'll use. In the Help view, **Show me** walks you through it on your own dashboard: it opens the view, points at what to press, and says what happens.

<!-- guide:howto -->

## Sell and buy

<a id="sell-now"></a>
### Sell to the grid right now
<!-- guide:task where="Power · Battery mode" icon="💰" uses="power-batterymode.png power-state.png" -->

For when you want the battery exporting now, whatever the curves say.

1. Open the **Power** view.
   <!-- guide:show view="power" card="battman-batterymode" say="The Battery mode card" -->
2. On the **Battery mode** card, tap **Sell**.
   <!-- guide:show view="power" card="battman-batterymode" text="Sell" say="Tap Sell" -->
3. If feed-in is negative, it asks "Sell?" and says "Feed-in is -x.xc: you would pay to export. Sell anyway?" Press **Sell anyway** to go ahead.
4. Check it: **Sell** lights green. While the engine wouldn't sell, the **State** card reads "Manual mode change · Sell".
   <!-- guide:show view="power" card="battman-state" say="Manual mode change · Sell" -->

> [!TIP]
> While **Active** is on, the engine sets the mode again each time it runs, so this lasts until its next run. To keep selling, see [Take over the battery for a while](#take-over-battery). While **Curtail** is on, the grid export limit is 0 and nothing reaches the grid.

More: [The mode buttons](../intermediate/power.md#batterymode) · [Confirmations](../intermediate/settings.md#dashboard-confirmations)

<a id="buy-now"></a>
### Charge the battery from the grid right now
<!-- guide:task where="Power · Battery mode" icon="🔌" uses="power-batterymode.png" -->

1. Open the **Power** view.
   <!-- guide:show view="power" card="battman-batterymode" say="The Battery mode card" -->
2. On the **Battery mode** card, tap **Buy**.
   <!-- guide:show view="power" card="battman-batterymode" text="Buy" say="Tap Buy" -->
3. If the buy price is above your **Warn on Buy above** limit, it asks "Buy?" and says "Buy is x.xc, above your x.xc limit. Buy anyway?" Press **Buy anyway** to go ahead.
4. Check it: **Buy** lights yellow.

> [!TIP]
> While **Active** is on, the engine sets the mode again at its next run. To charge to a level at a price you choose, use a [Buy Override](#buy-when-cheap) instead.

More: [The mode buttons](../intermediate/power.md#batterymode) · [Confirmations](../intermediate/settings.md#dashboard-confirmations)

<a id="stop-exports-negative-feed-in"></a>
### Stop exporting while feed-in is negative
<!-- guide:task where="Power · Battery mode" icon="🚫" uses="power-batterymode.png power-limits.png" -->

While **Active** is on, Battman does this itself: each engine run turns **Curtail** on while feed-in is negative and off when it isn't. To stop exports straight away:

1. Open the **Power** view.
   <!-- guide:show view="power" card="battman-batterymode" say="The Battery mode card" -->
2. On the **Battery mode** card, tap **Curtail**.
   <!-- guide:show view="power" card="battman-batterymode" text="Curtail" say="Tap Curtail" -->
3. It asks "Turn Curtail?" and says "This will stop any exports." Press **Turn on**.
4. Check it: the **Limits** card's **Grid Export Limit** drops to 0. If something raises it while Curtail is on, Battman puts it back to 0.
   <!-- guide:show view="power" card="battman-limits" text="Grid Export Limit" say="Grid Export Limit goes to 0" -->

> [!TIP]
> To export again, tap **Curtail** and press **Turn off**: **Grid Export Limit** goes back to 18.2. While feed-in is negative, it first warns "Feed-in is -x.xc. Turning off means you pay to export." While Active is on, the engine's next run sets Curtail to match the price again.

More: [Active, Curtail and the engine log](../intermediate/power.md#batterymode) · [Limits](../intermediate/power.md#limits)

<a id="sell-when-price-high"></a>
### Sell only when the price is high enough
<!-- guide:task where="Power · Overrides" icon="📈" uses="power-overrides.png power-state.png" -->

A Sell Override sells while the feed-in price is at or above your price and the battery is above your level, in place of the curves.

1. Open the **Power** view.
   <!-- guide:show view="power" card="battman-overrides" say="The Overrides card" -->
2. On the **Overrides** card, tap the **OVERRIDES** strip to open the control centre.
   <!-- guide:show view="power" card="battman-overrides" text="OVERRIDES" say="Tap the OVERRIDES strip" -->
3. Tap **Sell Override**. Set **SOC %** to the level to sell down to and **PRICE ¢** to the lowest feed-in price to sell at.
4. To limit how long it lasts, pick a time under **Start for** or **Run until**. Turn on **No Reset** to keep it past its level and the daily reset. Press **Set**.
5. Check it: the **Sell Override** row shows **SOC**, **PRICE**, an **EARN** estimate and the move, such as "80% → 40%" with the kWh to sell, or "target met". The **State** card's SELL tile shows **Override**.
   <!-- guide:show view="power" card="battman-state" say="SELL shows Override" -->

> [!TIP]
> Fill in only **SOC %** and the curve's price still applies; only **PRICE ¢** and the curve's level still applies. **SOC %** at 100 stops selling: the row reads "NO SELLING" and the strip "OVERRIDES · NO SELL". Overrides act only while **Active** is on. To clear one, double-tap its row.

More: [Overrides](../intermediate/power.md#overrides)

<a id="buy-when-cheap"></a>
### Buy when power is cheap
<!-- guide:task where="Power · Overrides" icon="🛒" uses="power-overrides.png" -->

**Buy Override** takes the place of the curves: it charges while the buy price is at or below its price and the battery is at or below its level, even in the 5–9pm peak. **Buy Anytime** adds to the curves: it charges to its level while the buy price is at or below its price, but not in the 5–9pm peak or while a Buy Override is set, and it needs both a level and a price.

1. Open the **Power** view.
   <!-- guide:show view="power" card="battman-overrides" say="The Overrides card" -->
2. On the **Overrides** card, tap the **OVERRIDES** strip to open the control centre.
   <!-- guide:show view="power" card="battman-overrides" text="OVERRIDES" say="Tap the OVERRIDES strip" -->
3. Tap **Buy Override** or **Buy Anytime**. Set **SOC %** to the level to charge up to and **PRICE ¢** to the highest buy price to pay.
4. For Buy Anytime, pick a finish time under **Start for** or **Run until**, then press **Calculate cheapest price**: it fills **PRICE ¢** with the lowest price that still reaches the level by then. Press **Set**.
5. Check it: the row shows a **COST** estimate and the move, such as "42% → 80%" with the kWh to buy. The **State** card's BUY tile shows **Override** or **Anytime**.
   <!-- guide:show view="power" card="battman-state" say="BUY shows Override or Anytime" -->

> [!TIP]
> A Buy Override with a negative **PRICE ¢** charges whenever the buy price is at or below it, whatever the battery level.

More: [Overrides](../intermediate/power.md#overrides) · [State](../intermediate/power.md#state)

<a id="drain-to-level"></a>
### Drain the battery down to a level
<!-- guide:task where="Power · Overrides" icon="🔻" uses="power-overrides.png power-batterymode.png" -->

The **Drain Battery** override runs the house off the battery with solar off, while the buy price is below its price and the battery is above its level. At the level it clears, unless the override timer is running or **No Reset** is on. The **Drain** button on the Battery mode card does the same straight away, with no level: it doesn't stop by itself.

1. Open the **Power** view.
   <!-- guide:show view="power" card="battman-overrides" say="The Overrides card" -->
2. On the **Overrides** card, tap the **OVERRIDES** strip to open the control centre.
   <!-- guide:show view="power" card="battman-overrides" text="OVERRIDES" say="Tap the OVERRIDES strip" -->
3. Tap **Drain Battery**. Set **SOC %** to the level to drain down to and **PRICE ¢** to the buy price it may drain below. It needs a price. Press **Set**.
4. Check it: the **Drain Battery** row shows the move, such as "60% → 30%" with the kWh. While it drains, **Drain** is lit on the **Battery mode** card and the **Limits** card's **PV Max Limit** is 0.
   <!-- guide:show view="power" card="battman-limits" text="PV Max Limit" say="PV Max Limit goes to 0" -->

> [!TIP]
> To drain now with no level, tap **Drain** on the **Battery mode** card. It doesn't ask first. While **Active** is on, the engine sets the mode again at its next run.

More: [Overrides](../intermediate/power.md#overrides) · [Limits](../intermediate/power.md#limits)

<a id="take-over-battery"></a>
### Take over the battery for a while
<!-- guide:task where="Power · Battery mode" icon="✋" uses="power-batterymode.png settings-watchdog.png" -->

While **Active** is on, the engine sets the mode and **Curtail** each time it runs, so a mode you pick by hand lasts only until then. Turn Active off to keep it.

1. Open the **Power** view.
   <!-- guide:show view="power" card="battman-batterymode" say="The Battery mode card" -->
2. On the **Battery mode** card, tap **Active**. It asks "Turn Active?" and says "Battman will stop controlling the battery." Press **Turn off**.
   <!-- guide:show view="power" card="battman-batterymode" text="Active" say="Tap Active" -->
3. Tap the mode you want, such as **Sell**, **Buy** or **Self Consume**, and use **Curtail** as you need. They stay as you set them: the engine and the watchdog don't run, and overrides don't clear.
4. When you want Battman to run the battery again, tap **Active**. It says "Battman will control the battery again." Press **Turn on**.
5. On the **Settings** view, press **Run engine now** so the engine picks the mode straight away. Otherwise it runs when the price or a setting next changes.
   <!-- guide:show view="settings" card="battman-settings" text="Run engine now" say="Press Run engine now" -->

> [!NOTE]
> If the engine last ran longer ago than the **Script not run limit**, the watchdog sets Self Consume and turns Curtail on within a minute of Active going on, until the engine runs. **Run engine now** also runs the engine while Active is off, and sets the mode.

More: [Active, Curtail and the engine log](../intermediate/power.md#batterymode) · [Watchdog](../intermediate/settings.md#watchdog)

## Plan the day

<a id="keep-charge-for-evening"></a>
### Keep more charge for the evening
<!-- guide:task where="Curvy · Sell curve" icon="🌙" uses="curvy-edit.png curvy-hours.png" -->

Battman sells only while the battery is above the **Sell** curve, so a higher curve in the afternoon and evening keeps more in the battery.

1. Open the **Curvy** view. It opens on this month.
   <!-- guide:show view="curvy" card="battman-curvy" say="The SOC Curve Editor" -->
2. Tap **Sell**.
   <!-- guide:show view="curvy" card="battman-curvy" text="Sell" say="The Sell curve" -->
3. Raise the hour boxes from the afternoon through the evening, such as **3pm** to **9pm**. Each value is the SOC % Battman keeps before it sells.
   <!-- guide:show view="curvy" card="battman-curvy" text="5pm" say="The evening hours" -->
4. Do the same on **Sell High Consumption**. Battman uses it instead of **Sell** at needy times.
   <!-- guide:show view="curvy" card="battman-curvy" text="Sell High Consumption" say="The high consumption curve" -->
5. Press **Save**. It says "Saved!".
   <!-- guide:show view="curvy" card="battman-curvy" text="Save" say="Send the curves to Battman" -->

> [!TIP]
> A change goes to the month shown. To give other months the same curves, see [Copy a month's curves to other months](tasks.md#copy-curves-to-other-months).

More: [Curvy: the four curves](../intermediate/curvy.md#the-four-curves), [Needy curve triggers](../intermediate/settings.md#needy)

<a id="change-sell-or-buy-price"></a>
### Change the price Battman sells or buys at
<!-- guide:task where="Pricy · Preferred and second prices" icon="💲" uses="pricy-preferred.png pricy-second.png" -->

Battman sells while the feed-in price is at or above **Preferred Sell**, and charges from the grid while the buy price is at or below **Preferred Buy**.

1. Open the **Pricy** view. It opens on this month.
   <!-- guide:show view="pricy" card="battman-pricy" say="The Price Curve Editor" -->
2. Tap **Sell** or **Buy**.
   <!-- guide:show view="pricy" card="battman-pricy" text="Sell" say="Pick the curve" -->
3. In the **Preferred Sell** or **Preferred Buy** box, change an hour's price, in ¢/kWh. Or type a price in the "value in ¢" box and press **Set All** to give it to every hour.
   <!-- guide:show view="pricy" card="battman-pricy" text="Set All" say="Set All for every hour" -->
4. Set **Low Sell** or **High Buy**, in the box beside it, the same way. While **Linked to Preferred Sell** (or **Linked to Preferred Buy**) is ticked, it follows the preferred price in every hour where the two were the same.
5. Press **Save**. It says "💾 Saved!".
   <!-- guide:show view="pricy" card="battman-pricy" text="Save" say="Send the prices to Battman" -->

> [!TIP]
> Prices are whole cents and can be negative. The **Sell High Consumption** and **Buy High Consumption** tabs hold the prices Battman uses at needy times.

More: [Preferred Sell or Preferred Buy](../intermediate/pricy.md#preferred), [Low Sell or High Buy](../intermediate/pricy.md#second)

<a id="copy-curves-to-other-months"></a>
### Copy a month's curves to other months
<!-- guide:task where="Curvy · Buttons" icon="📋" uses="curvy-buttons.png curvy-edit.png" -->

Use **Copy Period** and **Paste Period** to copy one month to the months you choose.

1. On the **Curvy** view, tap the tab of the month to copy from.
   <!-- guide:show view="curvy" card="battman-curvy" say="Pick the month to copy" -->
2. Press **Copy Period**. It says "📋 Copied:" and the month.
   <!-- guide:show view="curvy" card="battman-curvy" text="Copy Period" say="Copy the month's curves" -->
3. Tap the month to copy to and press **Paste Period**. It asks "Paste all curves from … to …?" and says "This will copy all 4 curve types." Confirm it.
   <!-- guide:show view="curvy" card="battman-curvy" text="Paste Period" say="Paste into this month" -->
4. Paste into each month you want, then press **Save**. It says "Saved!".
   <!-- guide:show view="curvy" card="battman-curvy" text="Save" say="Send the curves to Battman" -->

> [!TIP]
> When the months of each season should always share curves, press **Season** instead. It asks first ("Switching to Season mode will group months together."), then gives each season's three months the curves of its first month, and every change after that goes to all three. Press **Save** to send them to Battman.

More: [Month or season](../intermediate/curvy.md#month-or-season), [Curvy buttons](../intermediate/curvy.md#buttons)

<a id="save-and-reuse-a-curve"></a>
### Save curves and reuse them later
<!-- guide:task where="Curvy · Presets" icon="💾" uses="curvy-buttons.png curvy-editing.png" -->

A preset holds all four curves of one period. Curvy has ten.

1. On the **Curvy** view, tap the month whose curves you want to keep.
   <!-- guide:show view="curvy" card="battman-curvy" say="Pick the month" -->
2. To name a preset first, press **Manage Presets**, type the names and press **Save Names**. It says "Preset names saved!".
   <!-- guide:show view="curvy" card="battman-curvy" text="Manage Presets" say="Name the presets" -->
3. Press **Save Preset ▼** and pick a preset. It asks "Save current curves for … to …?". Confirm it, and it says "Saved to" and the preset's name. Battman has it straight away.
   <!-- guide:show view="curvy" card="battman-curvy" text="Save Preset ▼" say="Save the curves as a preset" -->
4. To use it later, tap a month, press **Load Preset ▼** and pick a preset marked "✓ Saved". It asks "Load … to …?". Confirm it.
   <!-- guide:show view="curvy" card="battman-curvy" text="Load Preset ▼" say="Load a preset" -->
5. Press **Save** so Battman gets the loaded curves. It says "Saved!".
   <!-- guide:show view="curvy" card="battman-curvy" text="Save" say="Send the curves to Battman" -->

> [!TIP]
> **Currently Editing** shows the preset a month came from under **Based on**. Pricy has the same buttons, with five presets for price curves.

More: [Presets](../intermediate/curvy.md#presets), [Auto curve switcher](../intermediate/settings.md#auto-curve)

## Money

<a id="bank-income"></a>
### Bank my income when a new bill starts
<!-- guide:task where="Finances · Billing" icon="🏦" uses="finances-billing.png finances-billing-buttons.png" -->

Do this when a bill closes, so the running totals start again for the next one.

1. Open the **Finances** view.
   <!-- guide:show view="finances" card="battman-billing" say="The Billing card" -->
2. On the **Billing** card, check **New Income**: **Sell** less **Buy** less **Days** times **Network Fee**.
   <!-- guide:show view="finances" card="battman-billing" text="New Income" say="What you've earned since the reset" -->
3. Press **Bank New Income**. It adds **New Income** to **Banked Income** and says "✓ New income banked".
   <!-- guide:show view="finances" card="battman-billing" text="Bank New Income" say="Bank it first" -->
4. Then press **Reset New Income**. It sets **Buy**, **Sell** and **Days** back to 0 and says "✓ New income reset".
   <!-- guide:show view="finances" card="battman-billing" text="Reset New Income" say="Then reset" -->
5. Check it: **New Income** is $0.00 and **Banked Income** has grown by what **New Income** was.

> [!TIP]
> Bank first: **Bank New Income** works from the **Buy** and **Sell** totals as they are. Resetting first leaves that income out of **Banked Income** and **Lifetime**, and banking twice before you reset adds it twice. Neither button asks first.

More: [Billing buttons](../intermediate/finances.md#billing-buttons)

<a id="fix-totals"></a>
### Fix totals that look wrong
<!-- guide:task where="Finances · Billing" icon="🧮" uses="finances-billing-buttons.png" -->

1. Open the **Finances** view.
   <!-- guide:show view="finances" card="battman-billing" say="The Billing card" -->
2. On the **Billing** card, press **Correct Totals**. The **Correct totals** popup opens.
   <!-- guide:show view="finances" card="battman-billing" text="Correct Totals" say="Open Correct totals" -->
3. In the box for the period, **Today**, **Yesterday**, **This Month** or **Billing Period**, type the right amounts in **Sell $** and **Buy $**.
4. Press **Apply**. It asks "Set Today:" (or the period's name) with each total's old and new amount, and says "This overwrites the running totals." Confirm it.
5. It says "✓ Today updated" (or the period's name).

> [!TIP]
> **Reset** in a box puts back the totals as they are now, and changes nothing. Correct Totals sets these four periods only: the **Buy** and **Sell** rows on the Billing card, counted since the last **Reset New Income**, stay as they are.

More: [Correct totals](../intermediate/finances.md#correct-totals)

<a id="set-network-charge-and-bill-day"></a>
### Set my network charge and bill day
<!-- guide:task where="Settings · Billing" icon="🧾" uses="settings-billing.png finances-billing.png" -->

Set these to match your retailer's bill.

1. Open the **Settings** view.
   <!-- guide:show view="settings" card="battman-settings" say="The Settings card" -->
2. Open the **Billing** section if it's folded.
   <!-- guide:show view="settings" card="battman-settings" text="Billing" say="The Billing section" -->
3. Type your retailer's daily supply charge in **Daily network charge**, in $ from 0 to 5, then press Enter or leave the box. It says "✓ Saved".
   <!-- guide:show view="settings" card="battman-settings" text="Daily network charge" say="Your daily supply charge" -->
4. Type the day your billing period starts in **Bill day of month**, from 1 to 31.
   <!-- guide:show view="settings" card="battman-settings" text="Bill day of month" say="The day your bill starts" -->

> [!TIP]
> The **Network Fee** box on the Finances view's **Billing** card is the same setting as **Daily network charge**; changing it there says "✓ Network fee saved". A bill day from 1 to 28 starts a period on that day every month. Only a Home Assistant administrator can save a setting.

More: [Billing settings](../intermediate/settings.md#billing), [Bill day of month](../intermediate/settings.md#bill-day-of-month)

<a id="see-payback"></a>
### See whether the system has paid for itself
<!-- guide:task where="Finances · Solar System" icon="☀️" uses="finances-solar.png settings-system.png" -->

1. Open the **Finances** view.
   <!-- guide:show view="finances" card="battman-solar-system" say="The Solar System card" -->
2. Under **Financials**, read **Remaining**: the system cost less bill savings, rebates and energy income. At $0 or below, the system has paid for itself.
   <!-- guide:show view="finances" card="battman-solar-system" text="Financials" say="What's left to pay" -->
3. Under **ROI Timeline**, **Remaining** is the years still to go, and **Total ROI** is those plus the years installed.
   <!-- guide:show view="finances" card="battman-solar-system" text="ROI Timeline" say="Years to pay off" -->
4. To set the figures it works from, open the **Settings** view and the **System & financials** section.
   <!-- guide:show view="settings" card="battman-settings" text="System & financials" say="The System & financials section" -->
5. Fill in **Install cost**, **Install date**, **Other income**, the four **Pre-solar quarterly bills** and **Bill inflation**.
   <!-- guide:show view="settings" card="battman-settings" text="Install cost" say="What the system cost" -->

> [!TIP]
> **Banked Energy Income** and **Current Energy Income** are **Banked Income** and **New Income** on the **Billing** card.

More: [Solar System](../intermediate/finances.md#solar), [System & financials](../intermediate/settings.md#system)

## Look and feel

<a id="change-dashboard-theme"></a>
### Change the dashboard's theme
<!-- guide:task where="Settings · Dashboard options" icon="🎨" uses="settings-dashboard.png theme-themes.png" -->

Put one of the installed Battman themes on every view of the dashboard.

1. Open the **Settings** view. Open **Dashboard options** if it's folded.
   <!-- guide:show view="settings" card="battman-settings" text="Dashboard options" say="Dashboard options" -->
2. Pick a theme in the **Dashboard theme** list.
   <!-- guide:show view="settings" card="battman-settings" text="Dashboard theme" say="Pick a theme here" -->
3. It says "✓ Theme applied" and redraws the dashboard in that theme.

> [!TIP]
> **Make Active** on the **Theme** view does the same for the theme picked in Theme Studio, and sets **Dashboard theme** to match. Either way, only the dashboard you're on changes.

More: [Dashboard theme](../intermediate/settings.md#dashboard-theme), [Themes](../intermediate/theme.md#themes)

<a id="make-own-theme"></a>
### Make my own theme
<!-- guide:task where="Theme · Theme Studio" icon="🖌️" uses="theme-palette.png theme-harmonic.png" -->

1. Open the **Theme** view and pick the theme to start from in the picker at the top.
   <!-- guide:show view="theme" card="battman-theme-studio" say="Theme Studio" -->
2. Under **Palette**, tap a slot's swatch or type a colour in its hex box. Its shades are made again from it.
   <!-- guide:show view="theme" card="battman-theme-studio" text="red" say="A Palette slot" -->
3. Or, under **Harmonic palette generator**, pick a **Seed colour** and a scheme, then press **Apply to 12 hues**.
   <!-- guide:show view="theme" card="battman-theme-studio" text="Apply to 12 hues" say="Apply to 12 hues" -->
4. Press **Save to HA** and type a name, without "Battman". It says "saved “…” — themes reloaded".
   <!-- guide:show view="theme" card="battman-theme-studio" text="Save to HA" say="Save to HA" -->
5. Press **Make Active** to put it on every view of this dashboard.
   <!-- guide:show view="theme" card="battman-theme-studio" text="Make Active" say="Make Active" -->

> [!TIP]
> Battman's own themes can't be saved over: "“…” is a theme Battman ships. Pick another name for your own theme." Save under a new name.

More: [Themes](../intermediate/theme.md#themes), [Palette](../intermediate/theme.md#palette), [Harmonic palette generator](../intermediate/theme.md#harmonic)

<a id="turn-help-off-on"></a>
### Turn the help off or back on
<!-- guide:task where="Settings · Dashboard options" icon="❔" uses="settings-dashboard.png" -->

1. Open the **Settings** view. Open **Dashboard options** if it's folded.
   <!-- guide:show view="settings" card="battman-settings" text="Dashboard options" say="Dashboard options" -->
2. Turn **Show help** off or on.
   <!-- guide:show view="settings" card="battman-settings" text="Show help" say="Show help" -->
3. Off takes the **Help** view off the dashboard and hides the **Help** buttons. On adds the **Help** view back as the last tab and shows the buttons again.
4. When Home Assistant asks "Your dashboard was updated. Refresh to see changes?", press **Refresh**.

> [!TIP]
> No Help tab while **Show help** is on? Turn it off and on again.

More: [Showing or hiding the guide](../README.md#showing-or-hiding-the-guide)

## Something's not right

<a id="why-this-mode"></a>
### See why Battman picked a mode
<!-- guide:task where="Power · State" icon="🔍" uses="power-state.png log-log.png" -->

1. Open the **Power** view. The pill at the bottom of the **State** card names the side that's acting ("Selling" or "Buying") and why, such as "Sell Override 25c >40%". A mode set by hand shows as "Manual mode change · " and the button's name.
   <!-- guide:show view="power" card="battman-state" say="The reason is on the State card" -->
2. On the **Battery mode** card, tap the information button. The **Engine log** shows the engine's account of its last run.
   <!-- guide:show view="power" card="battman-batterymode" say="The info button opens the log" -->
3. For earlier runs, open the **Log** view and tap **Log** to open the list.
   <!-- guide:show view="log" card="battman-log" text="Log" say="Tap Log to open it" -->
4. Tick **Changes Only** to see just the runs where the mode changed. Each entry's **Mode** shows the change, such as "Self Consume → Charge".
   <!-- guide:show view="log" card="battman-log" text="Changes Only" say="Changes Only" -->

More: [State](../intermediate/power.md#state), [Battery mode](../intermediate/power.md#batterymode), [Log](../intermediate/log.md#log)

<a id="what-repair-means"></a>
### Find out what a Repair means
<!-- guide:task where="Help · Repairs" icon="🛠️" -->

1. In Home Assistant, go to **Settings → Repairs** to see Battman's Repairs by title.
2. On the **Help** view, the **Repairs** item on the status line says how many are open. Tap "what they mean".
3. The [Battman's Repairs](../help/repairs.md) page opens with the Repairs open right now listed at the top. Tap one to go to its section.
4. Follow its **Fix**. Most Repairs clear by themselves once the problem is fixed.

More: [Battman's Repairs](../help/repairs.md), [The status line](../README.md#the-status-line)

