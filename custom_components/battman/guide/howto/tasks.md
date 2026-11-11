# How do I…?

Pick what you want to do. Each task gives the steps and the cards you'll use. In the Help view, **Show me** walks you through it on your own dashboard: it opens the view, rings each thing to press, and moves on when you press it, into popups too. It never presses anything for you. Tap somewhere else to pause it, and **Back to the walkthrough** to carry on; **Stop** or Esc ends it.

<!-- guide:howto -->

## Sell and buy

<a id="sell-now"></a>
### Sell to the grid right now
<!-- guide:task where="Power · Battery mode" uses="power-batterymode.png power-state.png" -->

For when you want the battery exporting now, whatever the curves say.

1. On the **Power** view's **Battery mode** card, tap **Sell**.
   <!-- guide:show view="power" card="battman-batterymode" target="Sell" until="press" say="Tap Sell" -->
2. If feed-in is negative, it asks "Sell?" and says "Feed-in is -x.xc: you would pay to export. Sell anyway?" Press **Sell anyway** to go ahead.
   <!-- guide:show view="power" popup="Sell?" target="Sell anyway" until="closed" say="Press Sell anyway" -->
3. Check it: **Sell** lights green. While the engine wouldn't sell, the **State** card reads "Manual mode change · Sell".
   <!-- guide:show view="power" card="battman-batterymode" target="Sell" until="state:input_select.battman_mode=Discharge" say="Sell lights green" -->

> [!TIP]
> While **Active** is on, the engine sets the mode again each time it runs, so this lasts until its next run. To keep selling, see [Take over the battery for a while](#take-over-battery). While **Curtail** is on, the grid export limit is 0 and nothing reaches the grid.

More: [The mode buttons](../intermediate/power.md#batterymode) · [Confirmations](../intermediate/settings.md#dashboard-confirmations)

<a id="buy-now"></a>
### Charge the battery from the grid right now
<!-- guide:task where="Power · Battery mode" uses="power-batterymode.png" -->

1. On the **Power** view's **Battery mode** card, tap **Buy**.
   <!-- guide:show view="power" card="battman-batterymode" target="Buy" until="press" say="Tap Buy" -->
2. If the buy price is above your **Warn on Buy above** limit, it asks "Buy?" and says "Buy is x.xc, above your x.xc limit. Buy anyway?" Press **Buy anyway** to go ahead.
   <!-- guide:show view="power" popup="Buy?" target="Buy anyway" until="closed" say="Press Buy anyway" -->
3. Check it: **Buy** lights yellow.
   <!-- guide:show view="power" card="battman-batterymode" target="Buy" until="state:input_select.battman_mode=Charge" say="Buy lights yellow" -->

> [!TIP]
> While **Active** is on, the engine sets the mode again at its next run. To charge to a level at a price you choose, use a [Buy Override](#buy-when-cheap) instead.

More: [The mode buttons](../intermediate/power.md#batterymode) · [Confirmations](../intermediate/settings.md#dashboard-confirmations)

<a id="stop-exports-negative-feed-in"></a>
### Stop exporting while feed-in is negative
<!-- guide:task where="Power · Battery mode" uses="power-batterymode.png power-limits.png" -->

While **Active** is on, Battman does this itself: each engine run turns **Curtail** on while feed-in is negative and off when it isn't. To stop exports straight away:

1. On the **Power** view's **Battery mode** card, tap **Curtail**.
   <!-- guide:show view="power" card="battman-batterymode" target="Curtail" until="popup" skipif="state:input_boolean.battman_no_export=on" say="Tap Curtail" -->
2. It asks "Turn Curtail?" and says "This will stop any exports." Press **Turn on**.
   <!-- guide:show view="power" popup="Turn Curtail?" target="Turn on" until="state:input_boolean.battman_no_export=on" skipif="state:input_boolean.battman_no_export=on" say="Press Turn on" -->
3. Check it: the **Limits** card's **Grid Export Limit** drops to 0. If something raises it while Curtail is on, Battman puts it back to 0.
   <!-- guide:show view="power" card="battman-limits" target="Grid Export Limit" until="next" say="Grid Export Limit goes to 0" -->

> [!TIP]
> To export again, tap **Curtail** and press **Turn off**: **Grid Export Limit** goes back to 18.2. While feed-in is negative, it first warns "Feed-in is -x.xc. Turning off means you pay to export." While Active is on, the engine's next run sets Curtail to match the price again.

More: [Active, Curtail and the engine log](../intermediate/power.md#batterymode) · [Limits](../intermediate/power.md#limits)

<a id="sell-when-price-high"></a>
### Sell only when the price is high enough
<!-- guide:task where="Power · Overrides" uses="power-overrides.png power-state.png" -->

A Sell Override sells while the feed-in price is at or above your price and the battery is above your level, in place of the curves.

1. On the **Power** view's **Overrides** card, tap the **OVERRIDES** strip to open the control centre.
   <!-- guide:show view="power" card="battman-overrides" target="OVERRIDES" until="popup" say="Tap the OVERRIDES strip" -->
2. Tap **Sell Override** to open its panel.
   <!-- guide:show view="power" popup="Overrides" target="Sell Override" until="press" say="Open Sell Override" -->
3. Set **SOC %** to the level to sell down to and **PRICE ¢** to the lowest feed-in price to sell at.
   <!-- guide:show view="power" popup="Overrides" target="SOC %" until="next" say="Set SOC % and PRICE ¢" -->
4. To limit how long it lasts, tap a time under **Start for** or **Run until**. To keep it past its level and the daily reset, tap the box under **No Reset** so it reads ON.
5. Press **Set**.
   <!-- guide:show view="power" popup="Overrides" target="Set" until="closed" say="Press Set" -->
6. Check it: the **Sell Override** row shows **SOC**, **PRICE**, an **EARN** estimate and the move, such as "80% → 40%" with the kWh to sell, or "target met". The **State** card's SELL tile shows **Override**.
   <!-- guide:show view="power" card="battman-state" until="next" say="SELL shows Override" -->

> [!TIP]
> Fill in only **SOC %** and the curve's price still applies; only **PRICE ¢** and the curve's level still applies. **SOC %** at 100 stops selling: the row reads "NO SELLING" and the strip "OVERRIDES · NO SELL". Overrides act only while **Active** is on. To clear one, double-tap its row.

More: [Overrides](../intermediate/power.md#overrides)

<a id="buy-when-cheap"></a>
### Buy when power is cheap
<!-- guide:task where="Power · Overrides" uses="power-overrides.png" -->

**Buy Override** takes the place of the curves: it charges while the buy price is at or below its price and the battery is at or below its level, even in the 5–9pm peak. **Buy Anytime** adds to the curves: it charges to its level while the buy price is at or below its price, but not in the 5–9pm peak or while a Buy Override is set, and it needs both a level and a price.

1. On the **Power** view's **Overrides** card, tap the **OVERRIDES** strip to open the control centre.
   <!-- guide:show view="power" card="battman-overrides" target="OVERRIDES" until="popup" say="Tap the OVERRIDES strip" -->
2. Tap **Buy Override** to open its panel. For Buy Anytime, tap **Buy Anytime** instead.
   <!-- guide:show view="power" popup="Overrides" target="Buy Override" until="press" say="Open Buy Override" -->
3. Set **SOC %** to the level to charge up to and **PRICE ¢** to the highest buy price to pay.
   <!-- guide:show view="power" popup="Overrides" target="SOC %" until="next" say="Set SOC % and PRICE ¢" -->
4. For Buy Anytime, tap a finish time under **Start for** or **Run until**, then press **Calculate cheapest price**: it fills **PRICE ¢** with the lowest price that still reaches the level by then.
5. Press **Set**.
   <!-- guide:show view="power" popup="Overrides" target="Set" until="closed" say="Press Set" -->
6. Check it: the row shows a **COST** estimate and the move, such as "42% → 80%" with the kWh to buy. The **State** card's BUY tile shows **Override** or **Anytime**.
   <!-- guide:show view="power" card="battman-state" until="next" say="BUY shows Override or Anytime" -->

> [!TIP]
> A Buy Override with a negative **PRICE ¢** charges whenever the buy price is at or below it, whatever the battery level.

More: [Overrides](../intermediate/power.md#overrides) · [State](../intermediate/power.md#state)

<a id="drain-to-level"></a>
### Drain the battery down to a level
<!-- guide:task where="Power · Overrides" uses="power-overrides.png power-batterymode.png" -->

The **Drain Battery** override runs the house off the battery with solar off, while the buy price is below its price and the battery is above its level. At the level it clears, unless the override timer is running or **No Reset** is on. The **Drain** button on the Battery mode card does the same straight away, with no level: it doesn't stop by itself.

1. On the **Power** view's **Overrides** card, tap the **OVERRIDES** strip to open the control centre.
   <!-- guide:show view="power" card="battman-overrides" target="OVERRIDES" until="popup" say="Tap the OVERRIDES strip" -->
2. Tap **Drain Battery** to open its panel.
   <!-- guide:show view="power" popup="Overrides" target="Drain Battery" until="press" say="Open Drain Battery" -->
3. Set **SOC %** to the level to drain down to and **PRICE ¢** to the buy price it may drain below. It needs a price.
   <!-- guide:show view="power" popup="Overrides" target="SOC %" until="next" say="Set SOC % and PRICE ¢" -->
4. Press **Set**.
   <!-- guide:show view="power" popup="Overrides" target="Set" until="closed" say="Press Set" -->
5. Check it: the **Drain Battery** row shows the move, such as "60% → 30%" with the kWh. While it drains, **Drain** is lit on the **Battery mode** card and the **Limits** card's **PV Max Limit** is 0.
   <!-- guide:show view="power" card="battman-limits" target="PV Max Limit" until="next" say="PV Max Limit goes to 0" -->

> [!TIP]
> To drain now with no level, tap **Drain** on the **Battery mode** card. It doesn't ask first. While **Active** is on, the engine sets the mode again at its next run.

More: [Overrides](../intermediate/power.md#overrides) · [Limits](../intermediate/power.md#limits)

<a id="take-over-battery"></a>
### Take over the battery for a while
<!-- guide:task where="Power · Battery mode" uses="power-batterymode.png settings-watchdog.png" -->

While **Active** is on, the engine sets the mode and **Curtail** each time it runs, so a mode you pick by hand lasts only until then. Turn Active off to keep it.

1. On the **Power** view's **Battery mode** card, tap **Active**.
   <!-- guide:show view="power" card="battman-batterymode" target="Active" until="popup" skipif="state:input_boolean.battman_enable=off" say="Tap Active" -->
2. It asks "Turn Active?" and says "Battman will stop controlling the battery." Press **Turn off**.
   <!-- guide:show view="power" popup="Turn Active?" target="Turn off" until="state:input_boolean.battman_enable=off" skipif="state:input_boolean.battman_enable=off" say="Press Turn off" -->
3. Tap the mode you want, such as **Sell**, **Buy** or **Self Consume**, and use **Curtail** as you need. They stay as you set them: the engine and the watchdog don't run, and overrides don't clear.
   <!-- guide:show view="power" card="battman-batterymode" until="next" say="Pick a mode" -->
4. When you want Battman to run the battery again, tap **Active**.
   <!-- guide:show view="power" card="battman-batterymode" target="Active" until="popup" skipif="state:input_boolean.battman_enable=on" say="Tap Active" -->
5. It says "Battman will control the battery again." Press **Turn on**.
   <!-- guide:show view="power" popup="Turn Active?" target="Turn on" until="state:input_boolean.battman_enable=on" skipif="state:input_boolean.battman_enable=on" say="Press Turn on" -->
6. On the **Settings** view, press **Run engine** so the engine picks the mode straight away. Otherwise it runs when the price or a setting next changes.
   <!-- guide:show view="settings" card="battman-settings" target="Run engine" until="press" say="Press Run engine" -->

> [!NOTE]
> If the engine last ran longer ago than the **Script not run limit**, the watchdog sets Self Consume and turns Curtail on within a minute of Active going on, until the engine runs. **Run engine** also runs the engine while Active is off, and sets the mode.

More: [Active, Curtail and the engine log](../intermediate/power.md#batterymode) · [Watchdog](../intermediate/settings.md#watchdog)

## Plan the day

<a id="keep-charge-for-evening"></a>
### Keep more charge for the evening
<!-- guide:task where="Curvy · Sell curve" uses="curvy-edit.png curvy-hours.png" -->

Battman sells only while the battery is above the **Sell** curve, so a higher curve in the afternoon and evening keeps more in the battery.

1. Open the **Curvy** view. It opens on this month. Tap **Sell**.
   <!-- guide:show view="curvy" card="battman-curvy" target="Sell" until="press" say="Tap Sell" -->
2. Raise the hour boxes from the afternoon through the evening, such as **3pm** to **9pm**. Each value is the SOC % Battman keeps before it sells.
   <!-- guide:show view="curvy" card="battman-curvy" target="5pm" until="next" say="Raise the evening hours" -->
3. Tap **Sell High Consumption**. Battman uses it instead of **Sell** at needy times.
   <!-- guide:show view="curvy" card="battman-curvy" target="Sell High Consumption" until="press" say="Tap Sell High Consumption" -->
4. Raise the same hours on this curve.
   <!-- guide:show view="curvy" card="battman-curvy" target="5pm" until="next" say="Raise the same hours" -->
5. Press **Save**. It says "Saved!".
   <!-- guide:show view="curvy" card="battman-curvy" target="Save" until="press" say="Press Save" -->

> [!TIP]
> A change goes to the month shown. To give other months the same curves, see [Copy a month's curves to other months](tasks.md#copy-curves-to-other-months).

More: [Curvy: the four curves](../intermediate/curvy.md#the-four-curves), [Needy curve triggers](../intermediate/settings.md#needy)

<a id="change-sell-or-buy-price"></a>
### Change the price Battman sells or buys at
<!-- guide:task where="Pricy · Preferred and second prices" uses="pricy-preferred.png pricy-second.png" -->

Battman sells while the feed-in price is at or above **Preferred Sell**, and charges from the grid while the buy price is at or below **Preferred Buy**.

1. Open the **Pricy** view. It opens on this month. Tap **Sell**, or **Buy** for buy prices.
   <!-- guide:show view="pricy" card="battman-pricy" target="Sell" until="press" say="Tap Sell or Buy" -->
2. In the left box, **Preferred Sell** or **Preferred Buy**, change an hour's price, in ¢/kWh.
   <!-- guide:show view="pricy" card="battman-pricy" target="5pm" until="next" say="Change an hour's price" -->
3. To give every hour one price instead, type it in that box's "value in ¢" box and press **Set All**.
   <!-- guide:show view="pricy" card="battman-pricy" target="Set All" until="press" say="Or press Set All" -->
4. Set **Low Sell** or **High Buy**, in the right box, the same way. While **Linked to Preferred Sell** (or **Linked to Preferred Buy**) is ticked, it follows the preferred price in every hour where the two were the same.
5. Press **Save**. It says "💾 Saved!".
   <!-- guide:show view="pricy" card="battman-pricy" target="Save" until="press" say="Press Save" -->

> [!TIP]
> Prices are whole cents and can be negative. The **Sell High Consumption** and **Buy High Consumption** tabs hold the prices Battman uses at needy times.

More: [Preferred Sell or Preferred Buy](../intermediate/pricy.md#preferred), [Low Sell or High Buy](../intermediate/pricy.md#second)

<a id="copy-curves-to-other-months"></a>
### Copy a month's curves to other months
<!-- guide:task where="Curvy · Buttons" uses="curvy-buttons.png curvy-edit.png" -->

Use **Copy Period** and **Paste Period** to copy one month to the months you choose.

1. On the **Curvy** view, tap the tab of the month to copy from.
2. Press **Copy Period**. It says "📋 Copied:" and the month.
   <!-- guide:show view="curvy" card="battman-curvy" target="Copy Period" until="press" say="Press Copy Period" -->
3. Tap the tab of a month to copy to, then press **Paste Period**.
   <!-- guide:show view="curvy" card="battman-curvy" target="Paste Period" until="press" say="Press Paste Period" -->
4. It asks "Paste all curves from … to …?" and says "This will copy all 4 curve types." Press **OK**. It says "✅ Pasted all curves from" and the month.
5. Paste into each month you want the same way, then press **Save**. It says "Saved!".
   <!-- guide:show view="curvy" card="battman-curvy" target="Save" until="press" say="Press Save" -->

> [!TIP]
> When the months of each season should always share curves, press **Season** instead. It asks first ("Switching to Season mode will group months together."), then gives each season's three months the curves of its first month, and every change after that goes to all three. Press **Save** to send them to Battman.

More: [Month or season](../intermediate/curvy.md#month-or-season), [Curvy buttons](../intermediate/curvy.md#buttons)

<a id="save-and-reuse-a-curve"></a>
### Save curves and reuse them later
<!-- guide:task where="Curvy · Presets" uses="curvy-buttons.png curvy-editing.png" -->

A preset holds all four curves of one period. Curvy has ten.

1. On the **Curvy** view, tap the tab of the month whose curves you want to keep.
2. To name the presets first, press **Manage Presets**.
   <!-- guide:show view="curvy" card="battman-curvy" target="Manage Presets" until="popup" say="Press Manage Presets" -->
3. Type a name in the **Preset 1:** to **Preset 10:** boxes.
   <!-- guide:show view="curvy" popup="Manage Presets" target="Preset 1:" until="next" say="Name the presets" -->
4. Press **Save Names**. It says "Preset names saved!" and the popup closes.
   <!-- guide:show view="curvy" popup="Manage Presets" target="Save Names" until="closed" say="Press Save Names" -->
5. Press **Save Preset ▼**.
   <!-- guide:show view="curvy" card="battman-curvy" target="Save Preset ▼" until="press" say="Press Save Preset" -->
6. Pick a preset in the list. It asks "Save current curves for … to …?". Press **OK**. It says "Saved to" and the preset's name, and Battman has it straight away.
7. To use it later, tap a month's tab and press **Load Preset ▼**.
   <!-- guide:show view="curvy" card="battman-curvy" target="Load Preset ▼" until="press" say="Press Load Preset" -->
8. Pick a preset marked "✓ Saved". It asks "Load … to …?". Press **OK**. It says "Loaded" and the preset's name.
9. Press **Save** so Battman gets the loaded curves. It says "Saved!".
   <!-- guide:show view="curvy" card="battman-curvy" target="Save" until="press" say="Press Save" -->

> [!TIP]
> **Currently Editing** shows the preset a month came from under **Based on**. Pricy has the same buttons, with five presets for price curves.

More: [Presets](../intermediate/curvy.md#presets), [Auto curve switcher](../intermediate/settings.md#auto-curve)

## Money

<a id="bank-income"></a>
### Bank my income when a new bill starts
<!-- guide:task where="Finances · Billing" uses="finances-billing.png finances-billing-buttons.png" -->

Do this when a bill closes, so the running totals start again for the next one.

1. Open the **Finances** view. On the **Billing** card, check **New Income**: **Sell** less **Buy** less **Days** times **Network Fee**.
   <!-- guide:show view="finances" card="battman-billing" target="New Income" until="next" say="Check New Income" -->
2. Press **Bank New Income**. It adds **New Income** to **Banked Income** and says "✓ New income banked".
   <!-- guide:show view="finances" card="battman-billing" target="Bank New Income" until="press" say="Press Bank New Income" -->
3. Then press **Reset New Income**. It sets **Buy**, **Sell** and **Days** back to 0 and says "✓ New income reset". **New Income** is now $0.00, and **Banked Income** has grown by what it was.
   <!-- guide:show view="finances" card="battman-billing" target="Reset New Income" until="press" say="Press Reset New Income" -->

> [!TIP]
> Bank first: **Bank New Income** works from the **Buy** and **Sell** totals as they are. Resetting first leaves that income out of **Banked Income** and **Lifetime**, and banking twice before you reset adds it twice. Neither button asks first.

More: [Billing buttons](../intermediate/finances.md#billing-buttons)

<a id="fix-totals"></a>
### Fix totals that look wrong
<!-- guide:task where="Finances · Billing" uses="finances-billing-buttons.png" -->

1. Open the **Finances** view. On the **Billing** card, press **Correct Totals**. The **Correct totals** popup opens.
   <!-- guide:show view="finances" card="battman-billing" target="Correct Totals" until="popup" say="Press Correct Totals" -->
2. In the box for the period, **Today**, **Yesterday**, **This Month** or **Billing Period**, type the right amounts in **Sell $** and **Buy $**.
   <!-- guide:show view="finances" popup="Correct totals" target="Sell $" until="next" say="Type the right totals" -->
3. Press **Apply** in that box.
   <!-- guide:show view="finances" popup="Correct totals" target="Apply" until="press" say="Press Apply" -->
4. It asks "Set Today:" (or the period's name) with each total's old and new amount, and says "This overwrites the running totals." Press **OK**.
5. It says "✓ Today updated" (or the period's name) under the box. Press **✕** to close the popup.
   <!-- guide:show view="finances" popup="Correct totals" target="✕" until="closed" say="Close the popup" -->

> [!TIP]
> **Reset** in a box puts back the totals as they are now, and changes nothing. Correct Totals sets these four periods only: the **Buy** and **Sell** rows on the Billing card, counted since the last **Reset New Income**, stay as they are.

More: [Correct totals](../intermediate/finances.md#correct-totals)

<a id="set-network-charge-and-bill-day"></a>
### Set my network charge and bill day
<!-- guide:task where="Settings · Billing" uses="settings-billing.png finances-billing.png" -->

Set these to match your retailer's bill.

1. Open the **Settings** view, and the **Billing** section if it's folded.
2. Type your retailer's daily supply charge in **Daily network charge**, in $ from 0 to 5, then press Enter or leave the box. It says "✓ Saved".
   <!-- guide:show view="settings" card="battman-settings" target="Daily network charge" until="next" say="Set your daily supply charge" -->
3. Type the day your billing period starts in **Bill day of month**, from 1 to 31, then press Enter or leave the box. It says "✓ Saved".
   <!-- guide:show view="settings" card="battman-settings" target="Bill day of month" until="next" say="Set the day your bill starts" -->

> [!TIP]
> The **Network Fee** box on the Finances view's **Billing** card is the same setting as **Daily network charge**; changing it there says "✓ Network fee saved". A bill day from 1 to 28 starts a period on that day every month. Only a Home Assistant administrator can save a setting.

More: [Billing settings](../intermediate/settings.md#billing), [Bill day of month](../intermediate/settings.md#bill-day-of-month)

<a id="see-payback"></a>
### See whether the system has paid for itself
<!-- guide:task where="Finances · Solar System" uses="finances-solar.png settings-system.png" -->

1. Open the **Finances** view. On the **Solar System** card, under **Financials**, read **🧾 Remaining**: the system cost less bill savings, rebates and energy income. At $0 or below, the system has paid for itself.
   <!-- guide:show view="finances" card="battman-solar-system" target="🧾 Remaining" until="next" say="Read what's left to pay" -->
2. Under **ROI Timeline**, **⏳ Remaining** is the years still to go, and **🏁 Total ROI** is those plus the years installed.
   <!-- guide:show view="finances" card="battman-solar-system" target="⏳ Remaining" until="next" say="Read the years to go" -->
3. To set the figures it works from, open the **Settings** view and the **System & financials** section. Fill in **Install cost** and **Install date**.
   <!-- guide:show view="settings" card="battman-settings" target="Install cost" until="next" say="Set the install cost and date" -->
4. Fill in **Other income**: rebates, credits and incentives.
   <!-- guide:show view="settings" card="battman-settings" target="Other income" until="next" say="Set your other income" -->
5. Fill in the four **Pre-solar quarterly bills**, from **Q1 · Jul – Sep** to **Q4 · Apr – Jun**.
   <!-- guide:show view="settings" card="battman-settings" target="Q1 · Jul – Sep" until="next" say="Set the pre-solar bills" -->
6. Fill in **Bill inflation**, the yearly rise in electricity prices.
   <!-- guide:show view="settings" card="battman-settings" target="Bill inflation" until="next" say="Set the bill inflation" -->

> [!TIP]
> **Banked Energy Income** and **Current Energy Income** are **Banked Income** and **New Income** on the **Billing** card.

More: [Solar System](../intermediate/finances.md#solar), [System & financials](../intermediate/settings.md#system)

## Look and feel

<a id="change-dashboard-theme"></a>
### Change the dashboard's theme
<!-- guide:task where="Settings · Dashboard options" uses="settings-dashboard.png theme-themes.png" -->

Put one of the installed Battman themes on every view of the dashboard.

1. Open the **Settings** view.
2. Under **Dashboard options**, pick a theme in the **Dashboard theme** list.
   <!-- guide:show view="settings" card="battman-settings" target="Dashboard theme" until="press" say="Pick a theme" -->
3. It says "✓ Theme applied" and redraws the dashboard in that theme.

> [!TIP]
> **Make Active** on the **Theme** view does the same for the theme picked in Theme Studio, and sets **Dashboard theme** to match. Either way, only the dashboard you're on changes.

More: [Dashboard theme](../intermediate/settings.md#dashboard-theme), [Themes](../intermediate/theme.md#themes)

<a id="make-own-theme"></a>
### Make my own theme
<!-- guide:task where="Theme · Theme Studio" uses="theme-palette.png theme-harmonic.png" -->

1. Open the **Theme** view and pick the theme to start from in the picker at the top.
   <!-- guide:show view="theme" card="battman-theme-studio" until="next" say="Pick a theme to start from" -->
2. Under **Palette**, tap a slot's swatch or type a colour in its hex box. Its shades are made again from it.
   <!-- guide:show view="theme" card="battman-theme-studio" target="red" until="press" say="Change a Palette colour" -->
3. Or, under **Harmonic palette generator**, pick a **Seed colour**.
   <!-- guide:show view="theme" card="battman-theme-studio" target="Seed colour" until="press" say="Pick a Seed colour" -->
4. Tap a scheme, such as **Triadic**.
   <!-- guide:show view="theme" card="battman-theme-studio" target="Triadic" until="press" say="Tap a scheme" -->
5. Press **Apply to 12 hues**.
   <!-- guide:show view="theme" card="battman-theme-studio" target="Apply to 12 hues" until="press" say="Press Apply to 12 hues" -->
6. Press **Save to HA**.
   <!-- guide:show view="theme" card="battman-theme-studio" target="Save to HA" until="press" say="Press Save to HA" -->
7. Type a name, without "Battman", and press **OK**. If you already have a theme by that name, it asks "Replace it with this version?": press **OK**. It says "saved “…” — themes reloaded".
8. Press **Make Active** to put it on every view of this dashboard.
   <!-- guide:show view="theme" card="battman-theme-studio" target="Make Active" until="press" say="Press Make Active" -->

> [!TIP]
> Battman's own themes can't be saved over: "“…” is a theme Battman ships. Pick another name for your own theme." Save under a new name.

More: [Themes](../intermediate/theme.md#themes), [Palette](../intermediate/theme.md#palette), [Harmonic palette generator](../intermediate/theme.md#harmonic)

<a id="turn-help-off-on"></a>
### Turn the help off or back on
<!-- guide:task where="Settings · Dashboard options" uses="settings-dashboard.png" -->

1. Open the **Settings** view.
2. Under **Dashboard options**, turn **Show help** off or on.
   <!-- guide:show view="settings" card="battman-settings" target="Show help" until="press" say="Turn Show help off or on" -->
3. Off takes the **Help** view off the dashboard and hides the **Help** buttons. On adds the **Help** view back as the last tab and shows the buttons again.
4. When Home Assistant asks "Your dashboard was updated. Refresh to see changes?", press **Refresh**.

> [!TIP]
> No Help tab while **Show help** is on? Turn it off and on again.

More: [Showing or hiding the guide](../README.md#showing-or-hiding-the-guide)

## Something's not right

<a id="why-this-mode"></a>
### See why Battman picked a mode
<!-- guide:task where="Power · State" uses="power-state.png log-log.png" -->

1. Open the **Power** view. The pill at the bottom of the **State** card names the side that's acting ("Selling" or "Buying") and why, such as "Sell Override 25c >40%". A mode set by hand shows as "Manual mode change · " and the button's name.
   <!-- guide:show view="power" card="battman-state" until="next" say="Read the reason on the State card" -->
2. On the **Battery mode** card, tap the information button.
   <!-- guide:show view="power" card="battman-batterymode" target="icon:mdi:information-outline" until="popup" say="Tap the information button" -->
3. The **Engine log** shows the engine's account of its last run. Press **✕** to close it.
   <!-- guide:show view="power" popup="*" target="✕" until="closed" say="Read it, then press ✕" -->
4. For earlier runs, open the **Log** view and tap **Log** to open the list.
   <!-- guide:show view="log" card="battman-log" target="Log" until="open" say="Tap Log to open it" -->
5. Tick **Changes Only** to see just the runs where the mode changed. Each entry's **Mode** shows the change, such as "Self Consume → Charge".
   <!-- guide:show view="log" card="battman-log" target="Changes Only" until="press" say="Tick Changes Only" -->

More: [State](../intermediate/power.md#state), [Battery mode](../intermediate/power.md#batterymode), [Log](../intermediate/log.md#log)

<a id="what-repair-means"></a>
### Find out what a Repair means
<!-- guide:task where="Help · Repairs" -->

1. In Home Assistant, go to **Settings → Repairs** to see Battman's Repairs by title.
2. On the **Help** view, the **Repairs** item on the status line says how many are open. Tap "what they mean".
3. The [Battman's Repairs](../help/repairs.md) page opens with the Repairs open right now listed at the top. Tap one to go to its section.
4. Follow its **Fix**. Most Repairs clear by themselves once the problem is fixed.

More: [Battman's Repairs](../help/repairs.md), [The status line](../README.md#the-status-line)

