# How do I…?

Pick what you want to do. Each task gives the steps and the cards you'll use. In the Help view, **Show me** walks you through it on your own dashboard: it opens the view, rings each thing to press, and moves on when you press it, into popups too. It never presses anything for you. Tap somewhere else to pause it, and **Back to the walkthrough** to carry on; **Stop** or Esc ends it.

<!-- guide:howto -->

## Battery mode buttons

Each button on the **Power** view's **Battery mode** card puts the battery in a mode straight away. While **Active** is on, the engine picks the mode again each time it runs (when the price or a setting changes), so a mode you pick lasts until then. To make something last, use an [override](#sell-when-price-high) instead.

**House Party** and **HOOOOVER** are for negative buy prices, and Battman switches to them itself: you don't need to press them.

<a id="sell-now"></a>
### Sell to the grid right now
<!-- guide:task where="Power · Battery mode" uses="power-batterymode.png power-state.png" -->

Sell exports from the battery to the grid now, whatever the curves say.

1. On the **Power** view's **Battery mode** card, tap **Sell**.
   <!-- guide:show view="power" card="battman-batterymode" target="Sell" until="press" say="Tap Sell" -->
2. If feed-in is negative right now, selling would cost you money, so it asks "Sell?" first and says "Feed-in is -x.xc: you would pay to export. Sell anyway?". Press **Cancel** to leave it, or **Sell anyway** to sell regardless.
   <!-- guide:show view="power" popup="Sell?" target="Sell anyway" until="closed" say="Cancel, or Sell anyway" -->
3. Check it: **Sell** lights green. If the engine wouldn't have sold, the **State** card reads "Manual mode change · Sell".
   <!-- guide:show view="power" card="battman-batterymode" target="Sell" until="state:input_select.battman_mode=Discharge" say="Sell lights green" -->

> [!TIP]
> While **Curtail** is on, the grid export limit is 0 and nothing reaches the grid. To sell only down to a level, or only above a price, use a [Sell Override](#sell-when-price-high).

More: [The mode buttons](../intermediate/power.md#batterymode) · [Confirmations](../intermediate/settings.md#dashboard-confirmations)

<a id="buy-now"></a>
### Charge the battery from the grid right now
<!-- guide:task where="Power · Battery mode" uses="power-batterymode.png" -->

Buy charges the battery from the grid now.

1. On the **Power** view's **Battery mode** card, tap **Buy**.
   <!-- guide:show view="power" card="battman-batterymode" target="Buy" until="press" say="Tap Buy" -->
2. If the buy price is above your **Warn on Buy above** limit, it asks "Buy?" first and says "Buy is x.xc, above your x.xc limit. Buy anyway?". Press **Cancel** to leave it, or **Buy anyway** to buy at that price.
   <!-- guide:show view="power" popup="Buy?" target="Buy anyway" until="closed" say="Cancel, or Buy anyway" -->
3. Check it: **Buy** lights yellow.
   <!-- guide:show view="power" card="battman-batterymode" target="Buy" until="state:input_select.battman_mode=Charge" say="Buy lights yellow" -->

> [!TIP]
> To charge to a level at a price you choose, use a [Buy Override](#buy-when-cheap) instead. When the buy price goes negative, Battman switches to **HOOOOVER** or **House Party** itself.

More: [The mode buttons](../intermediate/power.md#batterymode) · [Confirmations](../intermediate/settings.md#dashboard-confirmations)

<a id="sell-solar-now"></a>
### Send the solar to the grid and hold the battery
<!-- guide:task where="Power · Battery mode" uses="power-batterymode.png power-limits.png" -->

Sell Solar holds the battery where it is and sends the solar to the grid: Battman cuts **Max Charge Limit** to 0.1 kW.

1. On the **Power** view's **Battery mode** card, tap **Sell Solar**.
   <!-- guide:show view="power" card="battman-batterymode" target="Sell Solar" until="press" say="Tap Sell Solar" -->
2. If feed-in is negative right now, exporting would cost you money, so it asks "Sell Solar?" first and says "Feed-in is -x.xc: you would pay to export. Sell Solar anyway?". Press **Cancel**, or **Sell Solar anyway**.
   <!-- guide:show view="power" popup="Sell Solar?" target="Sell Solar anyway" until="closed" say="Cancel, or Sell Solar anyway" -->
3. Check it: **Sell Solar** lights orange, and the **Limits** card's **Max Charge Limit** drops to 0.1.
   <!-- guide:show view="power" card="battman-batterymode" target="Sell Solar" until="state:input_select.battman_mode=Float" say="Sell Solar lights orange" -->

More: [The mode buttons](../intermediate/power.md#batterymode) · [Limits](../intermediate/power.md#limits)

<a id="drain-now"></a>
### Run the house off the battery right now
<!-- guide:task where="Power · Battery mode" uses="power-batterymode.png power-limits.png" -->

Drain runs the house off the battery with the solar off: Battman sets **PV Max Limit** to 0. It doesn't ask first and doesn't stop by itself.

1. On the **Power** view's **Battery mode** card, tap **Drain**.
   <!-- guide:show view="power" card="battman-batterymode" target="Drain" until="press" say="Tap Drain" -->
2. Check it: **Drain** lights red, and the **Limits** card's **PV Max Limit** drops to 0.
   <!-- guide:show view="power" card="battman-batterymode" target="Drain" until="state:input_select.battman_mode=Drain" say="Drain lights red" -->

> [!TIP]
> To drain down to a level and then stop, use the [Drain Battery override](#drain-to-level).

More: [The mode buttons](../intermediate/power.md#batterymode) · [Limits](../intermediate/power.md#limits)

<a id="self-consume-now"></a>
### Go back to using the battery for the house
<!-- guide:task where="Power · Battery mode" uses="power-batterymode.png" -->

Self Consume is the everyday mode: solar and the battery run the house, and the battery doesn't sell to or buy from the grid.

1. On the **Power** view's **Battery mode** card, tap **Self Consume**. It doesn't ask first.
   <!-- guide:show view="power" card="battman-batterymode" target="Self Consume" until="press" say="Tap Self Consume" -->
2. Check it: **Self Consume** lights blue.
   <!-- guide:show view="power" card="battman-batterymode" target="Self Consume" until="state:input_select.battman_mode=Self Consume" say="Self Consume lights blue" -->

More: [The mode buttons](../intermediate/power.md#batterymode)

## Overrides

An override takes the place of the curves for a while: a battery level (**SOC %**) and a price you choose. You set them in the control centre, which opens from the **OVERRIDES** strip on the **Power** view. Overrides act only while **Active** is on.

<a id="sell-when-price-high"></a>
### Sell only when the price is high enough
<!-- guide:task where="Power · Overrides" uses="power-overrides.png power-state.png" -->

A **Sell Override** sells while the feed-in price is at or above its price and the battery is above its level, in place of the Sell curve.

1. On the **Power** view's **Overrides** card, tap the **OVERRIDES** strip to open the control centre.
   <!-- guide:show view="power" card="battman-overrides" target="OVERRIDES" until="popup" say="Tap the OVERRIDES strip" -->
2. Tap **Sell Override** to open its panel.
   <!-- guide:show view="power" popup="Overrides" target="Sell Override" until="press" say="Open Sell Override" -->
3. In **SOC %**, type the level to sell down to. 100 means no selling.
   <!-- guide:show view="power" popup="Overrides" target="SOC %" until="next" say="Type the level to sell down to" -->
4. In **PRICE ¢**, type the lowest feed-in price to sell at. Leave one of the two empty and the curve's value is used for it.
   <!-- guide:show view="power" popup="Overrides" target="PRICE ¢" until="next" say="Type the lowest price" -->
5. To limit how long it lasts, tap a time under **Start for** or **Run until**, or type **Timer h** or **Until**. Leave them and it lasts until it reaches its level or the daily reset.
   <!-- guide:show view="power" popup="Overrides" target="id:tb0" until="next" say="Choose how long, or leave it" -->
6. If it should stay past its level and the daily reset, tap the box under **No Reset** so it reads ON. Otherwise leave it.
   <!-- guide:show view="power" popup="Overrides" target="id:r0" until="next" say="No Reset, if it should stay" -->
7. Press **Set**.
   <!-- guide:show view="power" popup="Overrides" target="Set" until="closed" say="Press Set" -->
8. Check it: the **Sell Override** row shows **SOC**, **PRICE**, an **EARN** estimate and the move, such as "80% → 40%", and the **State** card's SELL tile shows **Override**. To clear it, double-tap the row, or open its panel and press **Clear**.
   <!-- guide:show view="power" card="battman-overrides" target="Sell Override" until="next" say="Check the row" -->

More: [Overrides](../intermediate/power.md#overrides) · [State](../intermediate/power.md#state)

<a id="sell-solar-when-price-high"></a>
### Sell solar only when the price is high enough
<!-- guide:task where="Power · Overrides" uses="power-overrides.png power-state.png" -->

A **Sell Solar** override sends the solar to the grid while the feed-in price is at or above its price and the battery is above its level, in place of the curve.

1. On the **Power** view's **Overrides** card, tap the **OVERRIDES** strip.
   <!-- guide:show view="power" card="battman-overrides" target="OVERRIDES" until="popup" say="Tap the OVERRIDES strip" -->
2. Tap **Sell Solar** to open its panel.
   <!-- guide:show view="power" popup="Overrides" target="Sell Solar" until="press" say="Open Sell Solar" -->
3. In **SOC %**, type the level above which solar is sold.
   <!-- guide:show view="power" popup="Overrides" target="SOC %" until="next" say="Type the battery level" -->
4. In **PRICE ¢**, type the lowest feed-in price to sell solar at.
   <!-- guide:show view="power" popup="Overrides" target="PRICE ¢" until="next" say="Type the lowest price" -->
5. To limit how long it lasts, tap a time under **Start for** or **Run until**. Or leave it.
   <!-- guide:show view="power" popup="Overrides" target="id:tb1" until="next" say="Choose how long, or leave it" -->
6. If it should stay past the daily reset, tap the box under **No Reset** so it reads ON. Otherwise leave it.
   <!-- guide:show view="power" popup="Overrides" target="id:r1" until="next" say="No Reset, if it should stay" -->
7. Press **Set**.
   <!-- guide:show view="power" popup="Overrides" target="Set" until="closed" say="Press Set" -->
8. Check it: the **Sell Solar** row shows its **SOC** and **PRICE**, and the **State** card's SELL tile shows **Solar**. To clear it, double-tap the row.
   <!-- guide:show view="power" card="battman-overrides" target="Sell Solar" until="next" say="Check the row" -->

More: [Overrides](../intermediate/power.md#overrides)

<a id="buy-when-cheap"></a>
### Buy when power is cheap
<!-- guide:task where="Power · Overrides" uses="power-overrides.png power-state.png" -->

A **Buy Override** charges while the buy price is at or below its price and the battery is below its level, in place of the Buy curve, even in the 5–9pm peak.

1. On the **Power** view's **Overrides** card, tap the **OVERRIDES** strip.
   <!-- guide:show view="power" card="battman-overrides" target="OVERRIDES" until="popup" say="Tap the OVERRIDES strip" -->
2. Tap **Buy Override** to open its panel.
   <!-- guide:show view="power" popup="Overrides" target="Buy Override" until="press" say="Open Buy Override" -->
3. In **SOC %**, type the level to charge up to.
   <!-- guide:show view="power" popup="Overrides" target="SOC %" until="next" say="Type the level to charge to" -->
4. In **PRICE ¢**, type the highest buy price to pay. It can be negative: then it charges whenever the price is at or below it, whatever the battery level.
   <!-- guide:show view="power" popup="Overrides" target="PRICE ¢" until="next" say="Type the highest price" -->
5. To limit how long it lasts, tap a time under **Start for** or **Run until**. Or leave it.
   <!-- guide:show view="power" popup="Overrides" target="id:tb2" until="next" say="Choose how long, or leave it" -->
6. If it should stay past its level and the daily reset, tap the box under **No Reset** so it reads ON. Otherwise leave it.
   <!-- guide:show view="power" popup="Overrides" target="id:r2" until="next" say="No Reset, if it should stay" -->
7. Press **Set**.
   <!-- guide:show view="power" popup="Overrides" target="Set" until="closed" say="Press Set" -->
8. Check it: the **Buy Override** row shows a **COST** estimate and the move, such as "42% → 80%", and the **State** card's BUY tile shows **Override**. To clear it, double-tap the row.
   <!-- guide:show view="power" card="battman-overrides" target="Buy Override" until="next" say="Check the row" -->

More: [Overrides](../intermediate/power.md#overrides) · [State](../intermediate/power.md#state)

<a id="buy-anytime"></a>
### Charge to a level at the cheapest price by a time
<!-- guide:task where="Power · Overrides" uses="power-overrides.png" -->

**Buy Anytime** adds to the curves: it charges to its level while the buy price is at or below its price, at any time except the 5–9pm peak or while a Buy Override is set. It needs both a level and a price.

1. On the **Power** view's **Overrides** card, tap the **OVERRIDES** strip.
   <!-- guide:show view="power" card="battman-overrides" target="OVERRIDES" until="popup" say="Tap the OVERRIDES strip" -->
2. Tap **Buy Anytime** to open its panel.
   <!-- guide:show view="power" popup="Overrides" target="Buy Anytime" until="press" say="Open Buy Anytime" -->
3. In **SOC %**, type the level to charge up to. Under it, the panel shows what that would cost.
   <!-- guide:show view="power" popup="Overrides" target="SOC %" until="next" say="Type the level to charge to" -->
4. Pick when it must be done by: a time under **Start for** or **Run until**, or **Timer h** or **Until**.
   <!-- guide:show view="power" popup="Overrides" target="id:tb3" until="next" say="Choose when it's done by" -->
5. Press **Calculate cheapest price**. It fills **PRICE ¢** with the lowest price that still reaches the level by then. Or type your own price.
   <!-- guide:show view="power" popup="Overrides" target="Calculate cheapest price" until="next" say="Calculate cheapest price" -->
6. If it should stay past the daily reset, tap the box under **No Reset** so it reads ON. Otherwise leave it.
   <!-- guide:show view="power" popup="Overrides" target="id:r3" until="next" say="No Reset, if it should stay" -->
7. Press **Set**.
   <!-- guide:show view="power" popup="Overrides" target="Set" until="closed" say="Press Set" -->
8. Check it: the **Buy Anytime** row shows its move, and the **State** card's BUY tile shows **Anytime** while it's driving. To clear it, double-tap the row.
   <!-- guide:show view="power" card="battman-overrides" target="Buy Anytime" until="next" say="Check the row" -->

More: [Overrides](../intermediate/power.md#overrides)

<a id="drain-to-level"></a>
### Drain the battery down to a level
<!-- guide:task where="Power · Overrides" uses="power-overrides.png power-batterymode.png" -->

The **Drain Battery** override runs the house off the battery with the solar off, while the buy price is below its price and the battery is above its level. At the level it clears, unless the timer is running or **No Reset** is on.

1. On the **Power** view's **Overrides** card, tap the **OVERRIDES** strip.
   <!-- guide:show view="power" card="battman-overrides" target="OVERRIDES" until="popup" say="Tap the OVERRIDES strip" -->
2. Tap **Drain Battery** to open its panel.
   <!-- guide:show view="power" popup="Overrides" target="Drain Battery" until="press" say="Open Drain Battery" -->
3. In **SOC %**, type the level to drain down to. 100 means no draining.
   <!-- guide:show view="power" popup="Overrides" target="SOC %" until="next" say="Type the level to drain to" -->
4. In **PRICE ¢**, type the buy price to drain below. Drain Battery needs a price.
   <!-- guide:show view="power" popup="Overrides" target="PRICE ¢" until="next" say="Type the price to drain below" -->
5. **Drain instead of House Party** (**Plughole**): tap it to keep draining when the buy price goes negative, instead of Battman switching to House Party. Otherwise leave it.
   <!-- guide:show view="power" popup="Overrides" target="id:ph4" until="next" say="Plughole, if you want it" -->
6. To limit how long it lasts, tap a time under **Start for** or **Run until**. Or leave it.
   <!-- guide:show view="power" popup="Overrides" target="id:tb4" until="next" say="Choose how long, or leave it" -->
7. Press **Set**.
   <!-- guide:show view="power" popup="Overrides" target="Set" until="closed" say="Press Set" -->
8. Check it: the **Drain Battery** row shows the move, such as "60% → 30%". While it drains, **Drain** is lit on the **Battery mode** card and **PV Max Limit** is 0. To clear it, double-tap the row.
   <!-- guide:show view="power" card="battman-overrides" target="Drain Battery" until="next" say="Check the row" -->

More: [Overrides](../intermediate/power.md#overrides) · [Limits](../intermediate/power.md#limits)

<a id="net-target"></a>
### Make a set amount today, or break even
<!-- guide:task where="Power · Overrides" uses="power-overrides.png" -->

The **Net Target** is a goal for today's money: what you've sold, less what you've bought, less the daily network charge. **Sell** sets an amount to make, **Buy** a budget to spend, and **Break even** means sold covers bought. When it's reached, Battman clears that side's overrides.

1. On the **Power** view's **Overrides** card, tap the **OVERRIDES** strip.
   <!-- guide:show view="power" card="battman-overrides" target="OVERRIDES" until="popup" say="Tap the OVERRIDES strip" -->
2. Tap **Net Target** to open its panel.
   <!-- guide:show view="power" popup="Overrides" target="Net Target" until="press" say="Open Net Target" -->
3. Tap **Sell** for an amount to make, or **Buy** for a budget.
   <!-- guide:show view="power" popup="Overrides" target="Sell" until="next" say="Pick Sell or Buy" -->
4. Set the amount with **−** and **+** (5¢ a tap; hold to go faster), or tap **Break even**. Under it, "Net today" shows where today stands and what's left "to make" or "to spend".
   <!-- guide:show view="power" popup="Overrides" target="id:ntv" until="next" say="Set the amount" -->
5. To limit how long it lasts, tap a time under **Start for** or **Run until**. Or leave it: it ends at midnight.
   <!-- guide:show view="power" popup="Overrides" target="id:tb99" until="next" say="Choose how long, or leave it" -->
6. Press **Set**. Setting one side clears the other.
   <!-- guide:show view="power" popup="Overrides" target="Set" until="closed" say="Press Set" -->
7. Check it: the strip shows **SELL TARGET** or **BUY BUDGET**, or **BREAK EVEN**, counting down what's left. When it's reached it reads **TARGET MET** or **BUDGET REACHED**.
   <!-- guide:show view="power" card="battman-overrides" target="OVERRIDES" until="next" say="Check the strip" -->

More: [Net Target](../intermediate/power.md#net-target)

<a id="presets-and-scenes"></a>
### Save overrides as a preset or scene, and use it again
<!-- guide:task where="Power · Overrides" uses="power-overrides.png" -->

A **preset** is one override saved under a name; a **scene** is two or more overrides, or overrides and a Net Target, saved together. Set the overrides you want first.

1. On the **Power** view's **Overrides** card, tap the **OVERRIDES** strip.
   <!-- guide:show view="power" card="battman-overrides" target="OVERRIDES" until="popup" say="Tap the OVERRIDES strip" -->
2. Press **＋ Save current**. It lists what it will save under **Will save**, and says whether that makes a chip (one override) or a Scene.
   <!-- guide:show view="power" popup="Overrides" target="＋ Save current" until="press" say="Press Save current" -->
3. Type a **Name**, such as "Evening dump". A **Timer h** or **Until** here is saved with it.
   <!-- guide:show view="power" popup="Overrides" target="Name" until="next" say="Type a name" -->
4. Press **Save preset**.
   <!-- guide:show view="power" popup="Overrides" target="Save preset" until="press" say="Press Save preset" -->
5. To use it again: a preset is a chip at the top of its override's panel, and a scene is a chip under **Scenes**. Tap the chip and it's set straight away; a scene replaces every override and the Net Target.
   <!-- guide:show view="power" popup="Overrides" until="next" say="Tap a chip to use it" -->
6. A scene with a Net Target has a moon (**00:01**). Tap it to arm the scene: it's applied at 00:01 tonight. **Manage** puts a **×** on each chip to delete it.

More: [Presets and scenes](../intermediate/power.md#presets-and-scenes)

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
<!-- guide:task where="Pricy · Preferred and second prices" uses="pricy-edit.png pricy-preferred.png pricy-second.png" -->

Each hour, Battman checks two things on the curve in use: the battery level, set on **Curvy**, and the price, set on **Pricy**. It **sells** while the battery is above that hour's **Sell** curve *and* the feed-in price is at or above **Preferred Sell**. It **buys** from the grid while the battery is below that hour's **Buy** curve *and* the buy price is at or below **Preferred Buy**. Curvy is how much charge to keep; Pricy is what price makes it worth it.

Every curve has a normal and a **High Consumption** version, on both views. Battman uses the High Consumption ones while the house's average use over the last 30 minutes is above **House power above**, or, between 10 am and 4 pm, when the cautious solar forecast won't fill the battery (**PV to full battery gap**). The engine log says "(On High Curve!)" while it does.

1. Open the **Pricy** view. It opens on this month and on the curve for now: **Sell** from 5 pm to 10 pm, **Buy** otherwise. **Currently Editing** says which. The editor opens on High Consumption by the **Battman high consumption** helper, not by the engine's setting, so the engine log is the place to check which one the engine is using.
   <!-- guide:show view="pricy" card="battman-pricy" target="id:edit-info" until="next" say="See which curve this is" -->
2. Tap the curve to change: **Sell** or **Buy**, or a **High Consumption** one.
   <!-- guide:show view="pricy" card="battman-pricy" target="Sell" until="press" say="Tap Sell or Buy" -->
3. In the left box, **Preferred Sell** or **Preferred Buy**, change an hour's price, in ¢/kWh. The chart above shows the change, with today's Amber prices over it.
   <!-- guide:show view="pricy" card="battman-pricy" target="5pm" until="next" say="Change an hour's price" -->
4. To give every hour one price instead, type it in that box's "value in ¢" box and press **Set All**.
   <!-- guide:show view="pricy" card="battman-pricy" target="Set All" until="press" say="Or press Set All" -->
5. The right box is the second price: **Low Sell**, the least Battman takes when the battery is well above the Sell curve and today's sales haven't yet covered today's costs, or **High Buy**, the most it pays when the battery is well below the Buy curve. While **Linked to Preferred Sell** (or **Buy**) is ticked, it follows the preferred price wherever the two were the same.
6. Press **Save**. It says "💾 Saved!".
   <!-- guide:show view="pricy" card="battman-pricy" target="Save" until="press" say="Press Save" -->

> [!TIP]
> Prices are whole cents and can be negative. A change goes to the month shown; [copy it to other months](#copy-curves-to-other-months) the same way as Curvy's.

More: [Preferred Sell or Preferred Buy](../intermediate/pricy.md#preferred) · [Low Sell or High Buy](../intermediate/pricy.md#second) · [Needy curve triggers](../intermediate/settings.md#needy)

<a id="cheapest-hours"></a>
### Find the cheapest or dearest times today
<!-- guide:task where="Power · Amber price cards" uses="power-amber5minpricegrid.png power-amber24hourforecasttable.png" -->

1. On the **Power** view, the **Amber 5-minute price grid** shows the SELL price now above the BUY price now, each with a countdown to the next price and the next eight periods under it. Purple is best for you: a buy price below 0c, or a sell price of 25c and above. Dark red is worst.
   <!-- guide:show view="power" card="battman-amber5minpricegrid" until="next" say="Read the prices now" -->
2. The **Amber 24-hour forecast table** has every interval ahead: **Time**, **Sell**, **Buy**, and Amber Advanced's predicted price for each (**SS**). Scroll it to find the best times; the colours are the same.
   <!-- guide:show view="power" card="battman-amber24hourforecasttable" until="next" say="Scroll the forecast" -->

> [!TIP]
> To act on a cheap stretch, use a [Buy Override](#buy-when-cheap) or [Buy Anytime](#buy-anytime); for a dear one, a [Sell Override](#sell-when-price-high).

More: [Amber 5-minute price grid](../intermediate/power.md#amber5minpricegrid) · [Amber 24-hour forecast table](../intermediate/power.md#amber24hourforecasttable)

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

<a id="holiday-curve"></a>
### Use a different curve while I'm away
<!-- guide:task where="Curvy · Presets, Settings · Auto curve switcher" uses="curvy-buttons.png settings-auto-curve.png" -->

Save the curves for while you're away as a preset, then give the **Auto curve switcher** your holiday dates: it uses the preset on those days, and the month's own curve again after.

1. On the **Curvy** view, shape the curves for while you're away: say, a lower **Buy** curve, since the house uses less. Don't press **Save**: that would change the month's own curve. If **Auto-save** is ticked, untick it first.
   <!-- guide:show view="curvy" card="battman-curvy" target="5pm" until="next" say="Shape the holiday curves" -->
2. Press **Save Preset ▼**.
   <!-- guide:show view="curvy" card="battman-curvy" target="Save Preset ▼" until="press" say="Press Save Preset" -->
3. Pick a preset in the list. It asks "Save current curves for … to …?". Press **OK**. It says "Saved to" and the preset's name.
4. On the **Settings** view, under **Auto curve switcher**, turn **Auto curve switcher** on.
   <!-- guide:show view="settings" card="battman-settings" target="Master switch. Off puts the month's own curve back" until="press" say="Turn the switcher on" -->
5. In the **Holiday** row, set the first and last day (both count) and pick the preset you saved.
   <!-- guide:show view="settings" card="battman-settings" target="Between these dates. Leave blank to skip" until="next" say="Set the dates and preset" -->

> [!TIP]
> It checks on the hour, so the preset takes over at the next check on the first day. While the switcher is on, the **State** card shows an **Auto** pill. Its other rules pick presets by the day's solar forecast; leave them blank if you only want the holiday.

More: [Auto curve switcher](../intermediate/settings.md#auto-curve) · [Presets](../intermediate/curvy.md#presets)

## Money

<a id="this-bill"></a>
### See what I've made or spent this bill
<!-- guide:task where="Finances · Cost chart, Cost compare" uses="finances-costchart.png finances-costchart-totals.png" -->

1. On the **Finances** view's **Cost chart**, tap **This cycle**. Each bar is a day's cost and sales, with its net above it.
   <!-- guide:show view="finances" card="battman-cost-chart" target="This cycle" until="press" say="Tap This cycle" -->
2. The strip above the bars: **This Bill** is this bill cycle's net so far, **Last Bill** the whole of the last one, and **Lifetime** everything. **Today Sell** and **Today Buy** are today's kWh at their average price.
   <!-- guide:show view="finances" card="battman-cost-chart" target="This Bill" until="next" say="Read This Bill" -->
3. The **Cost compare** card puts this cycle's running net against the last cycle's, day by day.
   <!-- guide:show view="finances" card="battman-cost-compare" until="next" say="Compare with last cycle" -->

> [!TIP]
> A net figure is sales less buying less the daily network charge: green at $0 or more, red below. The bill cycle starts on **Bill day of month** in Settings.

More: [Cost chart](../intermediate/finances.md#costchart) · [Cost compare](../intermediate/finances.md#costcompare)

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
   <!-- guide:show view="theme" card="battman-theme-studio" target="id:themeSel" until="next" say="Pick a theme to start from" -->
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

## Check on Battman

<a id="next-hours"></a>
### See what Battman will do over the next few hours
<!-- guide:task where="Power · State" uses="power-state.png" -->

1. On the **Power** view, tap the **State** card. **Next hours** opens.
   <!-- guide:show view="power" card="battman-state" until="popup" say="Tap the State card" -->
2. Each stretch says what the engine would do, from now on: "Sell … kWh", "Buy … kWh", "Drain … kWh", "Hold the battery at …%" or "Do nothing". Each gives its times ("Now" for the one under way), the battery level, what it earns (green, "+$") or costs (yellow, "−$"), why, and the house and solar power.
   <!-- guide:show view="power" popup="*" until="next" say="Read the next hours" -->
3. To try other conditions, open **What-if**.
   <!-- guide:show view="power" popup="*" target="What-if" until="open" say="Open What-if" -->
4. Change **Battery level**, **Solar**, **House load**, **Buy price shift** or **Sell price shift**, and the stretches change with them. None of it is sent to the battery; **Reset to live** puts them back.
   <!-- guide:show view="power" popup="*" target="Reset to live" until="next" say="Try a what-if" -->
5. Press **✕** to close it.
   <!-- guide:show view="power" popup="*" target="✕" until="closed" say="Press ✕" -->

More: [The next hours](../intermediate/power.md#the-next-hours) · [Forecast entries](../intermediate/log.md#forecast-entries)

<a id="what-battman-did"></a>
### Find out what Battman did and why
<!-- guide:task where="Power · State, Log" uses="power-state.png log-log.png" -->

1. On the **Power** view, the pill at the bottom of the **State** card names the side that's acting ("Selling" or "Buying") and why, such as "Sell Override 25c >40%". A mode set by hand shows as "Manual mode change · " and the button's name.
   <!-- guide:show view="power" card="battman-state" until="next" say="Read the reason on the State card" -->
2. On the **Battery mode** card, tap the information button.
   <!-- guide:show view="power" card="battman-batterymode" target="icon:mdi:information-outline" until="popup" say="Tap the information button" -->
3. The **Engine log** is the engine's account of its last run. Press **✕** to close it.
   <!-- guide:show view="power" popup="*" target="✕" until="closed" say="Read it, then press ✕" -->
4. For earlier runs, open the **Log** view. Under **Filter Log**, pick how far back to look, such as **24h**.
   <!-- guide:show view="log" card="battman-log" target="24h" until="press" say="Pick how far back" -->
5. Tap **Log** to open the list of runs.
   <!-- guide:show view="log" card="battman-log" target="Log" until="open" say="Tap Log to open it" -->
6. Tick **Changes Only** to see just the runs where the mode changed. Each entry's **Mode** shows the change, such as "Self Consume → Charge", with the prices and battery level that led to it. Untick a mode to hide its runs.
   <!-- guide:show view="log" card="battman-log" target="Changes Only" until="press" say="Tick Changes Only" -->

More: [State](../intermediate/power.md#state) · [Filter Log](../intermediate/log.md#controls) · [Log](../intermediate/log.md#log)

## Something's not right

<a id="what-repair-means"></a>
### Find out what a Repair means
<!-- guide:task where="Help · Repairs" -->

1. In Home Assistant, go to **Settings → Repairs** to see Battman's Repairs by title.
2. On the **Help** view, the **Repairs** item on the status line says how many are open. Tap "what they mean".
3. The [Battman's Repairs](../help/repairs.md) page opens with the Repairs open right now listed at the top. Tap one to go to its section.
4. Follow its **Fix**. Most Repairs clear by themselves once the problem is fixed.

More: [Battman's Repairs](../help/repairs.md), [The status line](../README.md#the-status-line)

