# Settings

The **Settings** view on the Battman dashboard holds every Battman setting, in sections you can fold away and drag into the order you like. Each change is saved as you make it: the card refuses a value Battman won't accept before sending it, then waits for the setting to change and tells you if it didn't, and only a Home Assistant administrator can save, because Home Assistant only lets administrators send the event Battman uses.

- **What you see next to a control:** "Saving…", then "✓ Saved", or "Not saved:" and the reason. If the setting hasn't changed after 5 seconds it says so ("Not saved: … didn't change."). Someone who isn't an administrator gets "Not saved: Unauthorized". The **Live Activity** switch and **Run engine now** work for anyone.
- **What it refuses:** "Enter a number", "Must be at least …", "Must be at most …". Settings that take whole numbers drop anything after the decimal point (2.7 becomes 2). "Not set yet" under a setting means Battman has no value for it yet.
- **When a change takes effect:** while Battman is Active, a change to most settings runs the engine straight away. Buy rules, Sell rules, Sell price protection and Power provider are kept elsewhere, so they apply at the engine's next run, normally within a few minutes when Amber's price next updates.
- **Run engine now**, at the top, runs the engine once, straight away, even while Active is off. It says "✓ Ran" once the engine has run, or "Didn't run: the engine's run sensor didn't change" after 15 seconds.
- **Collapse all** and **Show all** fold or open every section; a section's title folds just that one. Drag a section by its dotted grip to move it. This device remembers the order and what's folded; to begin with every section is open except **Reset defaults**.

SOC means the battery's state of charge, as a %. Prices are in c/kWh (cents per kWh) unless a setting says otherwise. Where this page says "points", it means points of SOC: 10 points below a 50% curve is 40%.

<a id="buy"></a>
## Buy

<!-- guide:summary id="settings.buy" -->
How readily the battery charges from the grid when the buy price is positive. Battman charges while the battery is below your buy SOC curve for the hour (set on Curvy) and the price is at or below its buy price. That price starts at the hour's preferred buy price (set on Pricy), and these two offsets say how far below the curve the battery must be before Battman will pay more, up to the hour's high buy price.
<!-- /guide:summary -->

The card's note: "How hard the battery charges when grid prices are positive. Higher offsets mean more cautious charging." At a positive price, Battman doesn't buy in the evening peak (5 pm to 9 pm) unless a Buy override on the Overrides card says so.

For example, with the buy curve at 50% this hour and the offsets at 1 and 10: above 49% Battman pays only the preferred price; from 49% down to 40% the price it will pay rises steadily towards the high price; at 40% or below it pays up to the high price.

**↻ Reset** puts both offsets back to the values under [Reset defaults](#defaults).

> [!WARNING]
> **Reset here also clears Buy Anytime.** The Buy section's **↻ Reset** sends a Buy Anytime price of 0 along with the two offsets, so a Buy Anytime override that's set on the Overrides card is switched off too.

### Prorate price SOC offset

"SOC target offset when prorating by price". When the battery is at least this many points below the buy curve, Battman starts paying more than the preferred buy price, rising in a straight line to the high buy price at the **High price SOC offset**.

1% to start with. Whole numbers from 0 to 100. If it's the same as the high offset or more, there's no gradual band: the price jumps from preferred to high at the high offset.

### High price SOC offset

"SOC offset at high buy prices". When the battery is this many points or more below the buy curve, Battman will pay up to the hour's high buy price.

10% to start with. Whole numbers from 0 to 100. At 0 Battman never pays more than the preferred price.

<a id="buy-rules"></a>
## Buy rules

<!-- guide:summary id="settings.buyRules" -->
Hour-by-hour rules that look at Amber's price forecast before Battman charges. With an hour's rule on, Battman finds the cheapest average price in the hours ahead and waits for it, instead of charging now at a dearer price. Nothing here applies until **Buy rules enabled** is on and that hour's rule is **Active**.
<!-- /guide:summary -->

The card's note: "Fine-grained control over the buy price target each hour. Pick an hour and set its rule, or apply a cascade." Before any rule has been saved the card says "sensor.battman_buy_rules has no rules yet (Battman sets them up the first time it saves a rule)." and shows only the master switch.

When the hour's rule is on, Battman averages the forecast in blocks (**Grouping**) up to the end of the look-ahead, takes the cheapest block, adds **Offset by** and rounds it. That's the rule's target:

- **Lower than the price Battman would otherwise pay** (see [Buy](#buy)): Battman uses the target, so it holds off for the cheaper time.
- **Higher:** Battman uses it only while the battery is between the two levels set under Buy (or below a Buy override's SOC), so it can top up now.
- **0 or less, or at or above the hour's high buy price:** ignored.

The engine's log gives "Rule Active" as the reason when a rule made it buy.

### Buy rules enabled

"Master switch for all buy rule processing". Off to begin with. While it's off, no buy rule is used, whatever each hour says.

### Hour

"Hour to configure". The arrows step through the hours; the card starts on the hour it is now. The rows below it belong to that hour: the 2pm rule is used from 2:00 to 2:59 pm. Under the hour are two tabs: **Single hour** (the rows from **Active** to **Offset by**) and **⚡ Cascade** (**Start hour** and **Max look-ahead**).

### Active

"Use this rule at" the chosen hour. Off for every hour to begin with.

### Look ahead

"Hours of future prices to consider", in hours. 3 to start with, whole numbers. The window ends on the hour: at 2:20 pm a look-ahead of 3 runs to 5 pm. At 0 the rule does nothing.

### Grouping

"Interval for grouping dispatch windows", in minutes. 60 to start with. The forecast is averaged in blocks this long and the rule takes the cheapest one: short blocks let Battman wait for a brief dip, long ones for a cheaper stretch. Anything under 5 minutes counts as 5.

### Round to

"Decimal places for the price target". 2 to start with. The target is in $/kWh at this point, so 2 places rounds to a whole cent and 3 to a tenth of a cent. At 0 the target isn't rounded.

### Round type

"Direction to round the price target": **None**, **Down (floor)** or **Up (ceil)**. **Down (floor)** to start with. **None** still rounds, to the nearest; to stop rounding, set **Round to** to 0. Rounding a buy target down makes Battman a little choosier.

### Offset by

"Fixed adjustment added to the price target", in c/kWh. 0 to start with. Whole cents (decimals are dropped), and it can be negative. A positive offset lets Battman pay a little more than the cheapest block; a negative one makes it wait for less.

### Start hour

On the **⚡ Cascade** tab: "From the start hour, each hour is switched on with a look-ahead counting down to 1. Its other settings stay as they are." So every hour in the run looks ahead to the same end. Starting at 2pm with 4 hours sets 2pm to 4 hours, 3pm to 3, 4pm to 2 and 5pm to 1, all looking to 6 pm. The start hour begins at the hour shown above.

### Max look-ahead

"1 to 12 hours", in hours: how many hours the cascade covers, and the first hour's look-ahead. 4 to start with. The chips under it show each hour and its look-ahead. **Apply cascade** saves them one hour at a time and says "✓ Cascade applied to" and the number of hours. If an hour doesn't save, it stops there and says which.

<a id="needy"></a>
## Needy curve triggers

<!-- guide:summary id="settings.needy" -->
Battman keeps two versions of each SOC and price curve: the normal ones and the "high" ones for needy times (both set on Curvy and Pricy). It uses the high curves while the house is using a lot of power, or, between 10 am and 4 pm, when the cautious solar forecast won't fill the battery today. These two settings say what "a lot" and "won't fill" mean.
<!-- /guide:summary -->

The card's note: "Switches to a more aggressive charging curve when the house uses a lot, or solar won't fill the battery before sunset." The engine's log says "(On High Curve!)" while it's using them. **↻ Reset** puts both back to the values under [Reset defaults](#defaults).

### PV to full battery gap

"Remaining solar needed to fill the battery", in kWh. Battman takes the room left in the battery and subtracts Solcast's cautious (10%) estimate of the solar still to come today. If more than this gap is left over, between 10 am and 4 pm, it uses the high curves.

3 kWh to start with. From −40 to 40. A bigger gap makes the high curves rarer; a negative one uses them even when the forecast should fill the battery with that much to spare. If Solcast has no cautious estimate, the check is skipped and the log says so.

### House power above

"Use that triggers the needy curve", in kW. When the house's average power use over the last 30 minutes is above this, Battman uses the high curves, at any time of day.

3.5 kW to start with. From 0 to 20. If the 30-minute average has no value (`sensor.battman_load_30m_avg`, from Sigenergy's consumed power), the check is skipped and the log says so.

> [!NOTE]
> Curvy and Pricy open on their high curve by a separate helper, **Battman high consumption**, not by this setting, so the curve they open on can differ from the one the engine is using.

<a id="auto-curve"></a>
## Auto curve switcher

<!-- guide:summary id="settings.autoCurve" -->
Picks one of your SOC curve presets (saved on Curvy) for the day, from how much solar today is likely to bring: what's been made so far plus the Solcast forecast still to come. It writes the preset into this month's SOC curve, and puts the month's own curve back at the reset hour. It's off until you switch it on, and it never changes the price curves.
<!-- /guide:summary -->

The card's note: "Picks a curve preset from today's projected solar: made so far plus the forecast still to come. At the reset hour the month's own curve goes back." If the card says "Not available yet: Battman is still loading its new settings. Reload the template entities, then come back.", do as it says.

Good to know:

- It checks on the hour. Changing a setting here doesn't start a check; the next one comes at the next hour that's due.
- Each change goes in the logbook as "Battman auto curve": the preset's name "applied to" the month and why, or the month's "curve put back."
- While it's on, the State card shows an **Auto** pill: its icon shows which rule won, and it turns orange when there was no forecast or the preset was empty.
- On the last day of the month it puts the month's own curve back at 11:50 pm, before Battman copies this month's curves into the next.
- A new curve is used from the engine's next run.

### Auto curve switcher

"Master switch. Off puts the month's own curve back". Off to begin with. Turning it off puts the month's own curve back if the switcher had changed it.

### Check at

"Hour the forecast is first read each day". 6am to start with.

### Also check every

"On top of the daily check": **Off**, **1 hr**, **2 hrs**, **3 hrs**, **4 hrs** or **6 hrs**. **Off** to start with. Repeat checks run from **Check at** until **Reset at**, or to the end of the day when **Reset at** is **Off** or isn't later than **Check at**.

### Reset at

"Hour the month's own curve goes back. Repeat checks stop then". 8pm to start with, or **Off**. With **Off**, a preset stays until a later check picks another or finds no rule, the month ends, or you switch the switcher off.

> [!WARNING]
> **Don't set Reset at to the same hour as Check at.** Then the two take turns: one day the check applies a preset, the next day at that hour the curve is put back and no check runs, and so on.

### Forecast used

"Solar still to come today, added to what is made so far": **10% (cautious)**, **Expected** or **90% (optimistic)**, Solcast's three estimates. **10% (cautious)** to start with. What's made so far is the day's solar from the Sigenergy inverter plus a third-party inverter. If one of those has no value it counts as 0, so the day's total comes out low and **Day total below** can win.

If Solcast has no forecast for today, the curve stays as it is.

<a id="auto-curve-rules-first-match-wins"></a>
### Rules, first match wins

<!-- guide:summary id="settings.autoCurve.rules-first-match-wins" -->
Up to four rules, checked from the top; the first one that applies picks the preset. A rule is skipped while its preset is **Not used** or its dates or kWh are left blank. If none applies, the month's own curve stays, or goes back if the switcher had changed it.
<!-- /guide:summary -->

The preset lists show the presets that have curves saved on Curvy. One marked "(empty)" has none: if its rule wins, the curve stays as it is.

#### Holiday

"Between these dates. Leave blank to skip". A first and last date (both days count) and a preset. Both dates and a preset are needed.

#### Day total below

"Projected solar for the day is under. Leave blank to skip". A total in kWh (0 to 500) and a preset, used when the day's projected solar is under it.

#### Day total above

"Projected solar for the day is over. Leave blank to skip". A total in kWh (0 to 500) and a preset, used when the day's projected solar is over it.

#### Otherwise

"Between the two. Leave alone keeps the month's curve". The preset to use when none of the rules above applies. **Leave alone** to start with.

<a id="watchdog"></a>
## Watchdog

<!-- guide:summary id="settings.watchdog" -->
A safety net that runs every minute while Battman is Active. If the engine hasn't run for longer than the limit, it sets the battery to Self Consume and stops exports until the engine runs again. It also clears overrides once a day, at the time you set. While Active is off, the watchdog does nothing at all.
<!-- /guide:summary -->

The card's note: "Keeps an eye on the engine. If its script stops running or stays disabled, Battman alerts and recovers it." **↻ Reset** puts both limits back to the values under [Reset defaults](#defaults).

### Script not run limit

"Alert if the script hasn't run within this time", in minutes. If the engine hasn't run for longer than this, the watchdog sets the battery to Self Consume, turns Curtail on so nothing is exported, writes "[WATCHDOG] Script not run for > configured minutes — forcing Self Consume" to the logbook and posts the notification "Battman watchdog": "Script not run for configured minutes". It does this every minute until the engine runs again.

10 minutes to start with. Whole numbers from 0 to 60. Don't set 0: the engine only runs when prices or settings change, so the watchdog would trip almost every minute.

> [!WARNING]
> **Turning Active back on can trip it.** Turning Active on doesn't run the engine. If Active was off for longer than this limit, within a minute the watchdog sets Self Consume and stops exports, until the next price update runs the engine. See [issue #104](https://github.com/AJErazzor/battman/issues/104).

### Script disabled limit

"Turn it back on if disabled longer than this", in minutes. 60 to start with; whole numbers from 0 to 360.

> [!WARNING]
> **This setting does nothing.** The watchdog never turns Active back on: it only runs while Active is on. See [issue #111](https://github.com/AJErazzor/battman/issues/111). Its value under Reset defaults is 10, so **↻ Reset** sets 10, not 60.

### Reset overrides at

"Daily time to clear manual overrides". 8:00 am to start with. At that minute each day, unless the override timer is running, the watchdog clears the Sell, Sell Solar, Drain, Buy and Buy Anytime overrides that are allowed to reset, and any Net Target. A "No Sell" override (sell at 0 with SOC 100) is never cleared this way. It only happens while Active is on.

<a id="billing"></a>
## Billing

<!-- guide:summary id="settings.billing" -->
Two figures from your electricity bill that Battman uses in its money totals: the daily supply charge and the day your billing period starts. The daily charge also counts in today's profit, which decides how readily the engine sells below its preferred price.
<!-- /guide:summary -->

The card's note: "For your net electricity costs. Set these to match your retailer's bill." **↻ Reset** puts both back to the values under [Reset defaults](#defaults).

### Daily network charge

"Your retailer's fixed daily supply charge", in $. $1.09 to start with. From 0 to 5.

Battman adds it to its network fee total once a day and takes it off today's net (today's sales less today's buying less this charge). The engine uses that net (see [Sell](#sell)), and so do Net Targets, the Live Activity, and the Profit / Loss, Billing and Solar System cards. The **Network Fee** box on the Billing card is the same setting.

### Bill day of month

"Day your billing period starts each month". The 2nd to start with. From 1 to 31 ("Must be more than 0"). Battman's billing-period totals start again on this day.

In a month that hasn't got that day (the 31st in April, say), the new period doesn't start until the 1st of the next month. A day from 1 to 28 avoids that.

<a id="system"></a>
## System & financials

<!-- guide:summary id="settings.system" -->
Facts about your solar and battery purchase, for the Solar System card on the Finances view: what it cost, when it was switched on, any rebates, and what your bills were before solar. The card uses them to show how far the system is towards paying for itself and how long is left.
<!-- /guide:summary -->

The card's note: "Install details, income, expenses and pre-solar bills, for payback and lifetime savings (the Solar System card)." The Solar System card shows the system cost, bill savings, rebates and income, what's still to pay (**Remaining**), and the years installed and to go.

### Install cost

"Total cost of solar + battery", in $. 0 to start with. From 0 to 100,000.

### Install date

"When the system was switched on". Until you set it, it's the day Battman was first set up. The card counts the years installed and the bill savings from this date.

### Other income

"Rebates, credits, incentives: lifetime total", in $. 0 to start with. From 0 to 50,000. The card takes it off what's still to pay.

### Other expenses

"Maintenance, repairs, parts: lifetime total", in $. 0 to start with. From 0 to 50,000.

> [!WARNING]
> **Nothing uses this yet.** Battman saves it, but the Solar System card leaves it out of its sums.

<a id="system-pre-solar-quarterly-bills"></a>
### Pre-solar quarterly bills

<!-- guide:summary id="settings.system.pre-solar-quarterly-bills" -->
What you paid for electricity in each quarter of a year before you had solar. Added up, they make a year's bill; the Solar System card counts that, day by day since the install date and grown by **Bill inflation**, as your bill savings. Each box shows its bill as a daily amount underneath.
<!-- /guide:summary -->

Each is in $, 0 to start with, from 0 to 5,000. The quarters run from July, as Australia's financial year does.

#### Q1 · Jul – Sep

July to September's bill (92 days).

#### Q2 · Oct – Dec

October to December's bill (92 days).

#### Q3 · Jan – Mar

January to March's bill (90 days).

#### Q4 · Apr – Jun

April to June's bill (91 days).

### Bill inflation

"Yearly rise in electricity prices", in %. 0 to start with. Whole numbers from 0 to 100. The card grows the pre-solar bills by this much each year, both in the bill savings ("Bill Savings (inflation …%)") and in how long is left to pay.

<a id="sell"></a>
## Sell

<!-- guide:summary id="settings.sell" -->
How readily the battery sells to the grid below its preferred price. Battman sells while the battery is above your sell SOC curve for the hour (set on Curvy) and the feed-in price is at or above its sell price, which starts at the hour's preferred sell price (set on Pricy). While today's earnings haven't yet covered today's costs, these offsets let it accept less when the battery is well above the curve, down to the hour's low sell price.
<!-- /guide:summary -->

The card's note: "When and how much the battery exports. SOC offsets stop it running too low." Battman never sells while the feed-in price is negative, and its normal selling never goes below the [Sell price protection](#protection) floor. **↻ Reset** puts both offsets back to the values under [Reset defaults](#defaults).

"Today's costs" are today's buying plus the [daily network charge](#billing). Once today's sales cover them, Battman sticks to the preferred price.

For example, with the sell curve at 20% this hour and the offsets at 30 and 50: below 50% Battman wants the preferred price; from 50% to 70% the price it accepts slides down towards the low price; at 70% or above it accepts the low price.

### Prorate price SOC offset

"SOC offset when prorating the sell price". When the battery is at least this many points above the sell curve, Battman starts accepting less than the preferred sell price, sliding in a straight line to the low sell price at the **Low price SOC offset**.

30% to start with. Whole numbers from 0 to 100. If it's the same as the low offset or more, there's no gradual band: the price drops from preferred to low at the low offset.

### Low price SOC offset

"SOC offset at low sell prices". When the battery is this many points or more above the sell curve, Battman accepts the hour's low sell price.

50% to start with. Whole numbers from 0 to 100. At 0 Battman never accepts less than the preferred price. A level that works out above 100% is never reached.

<a id="sell-rules"></a>
## Sell rules

<!-- guide:summary id="settings.sellRules" -->
Hour-by-hour rules that look at Amber's feed-in forecast before Battman sells. With an hour's rule on, Battman finds the best average feed-in price in the hours ahead and holds out for it, rather than selling now for less. Nothing here applies until **Sell rules enabled** is on and that hour's rule is **Active**.
<!-- /guide:summary -->

The card's note: "Fine-grained control over the sell price target each hour. Pick an hour and set its rule, or apply a cascade." Before any rule has been saved the card says "sensor.battman_sell_rules has no rules yet (Battman sets them up the first time it saves a rule)." and shows only the master switch.

Sell rules work like [Buy rules](#buy-rules), but take the best (highest) block instead of the cheapest. The rule's target:

- **At or above Battman's own sell price** (see [Sell](#sell)): Battman holds out for it, selling only when the feed-in price gets there.
- **Lower:** nothing changes, unless **Allow last chance to sell low** is on.
- **0 or less, or at or below the hour's low sell price:** ignored.

The [Sell price protection](#protection) floor still applies.

### Sell rules enabled

"Master switch for all sell rule processing". Off to begin with. While it's off, no sell rule is used, whatever each hour says.

### Hour

"Hour to configure". The arrows step through the hours; the card starts on the hour it is now. The rows below belong to that hour, under the tabs **Single hour** and **⚡ Cascade**.

### Active

"Use this rule at" the chosen hour. Off for every hour to begin with.

### Allow last chance to sell low

"Override the minimum price in the final window". Off to begin with. When it's on and today's earnings haven't yet covered today's costs, a target below Battman's own sell price is used too, so Battman sells now at the best price still to come rather than waiting for its usual price. It never goes below the hour's low sell price or the protection floor. With **Look ahead** at 0 it does nothing.

### Look ahead

"Hours of future prices to consider", in hours. 3 to start with, whole numbers. The window ends on the hour. At 0 the rule does nothing.

### Grouping

"Interval for grouping dispatch windows", in minutes. 60 to start with. The forecast is averaged in blocks this long and the rule takes the best one. Anything under 5 minutes counts as 5.

### Round to

"Decimal places for the price target". 2 to start with: a whole cent, as the target is in $/kWh here. At 0 it isn't rounded.

### Round type

"Direction to round the price target": **None**, **Down (floor)** or **Up (ceil)**. **Down (floor)** to start with, which makes Battman a little readier to sell. **None** rounds to the nearest; to stop rounding, set **Round to** to 0.

### Offset by

"Fixed adjustment added to the price target", in c/kWh. 0 to start with. Whole cents, and it can be negative. A positive offset holds out for more than the best block; a negative one settles for a little less.

### Start hour

On the **⚡ Cascade** tab: "From the start hour, each hour is switched on with a look-ahead counting down to 1. Its other settings stay as they are." Every hour in the run looks ahead to the same end, as for [Buy rules](#buy-rules).

### Max look-ahead

"1 to 12 hours", in hours. 4 to start with. The chips show each hour and its look-ahead; **Apply cascade** saves them and says "✓ Cascade applied to" and the number of hours.

<a id="spike"></a>
## Spike selling

<!-- guide:summary id="settings.spike" -->
When the feed-in price jumps, Battman can sell the battery further down than your sell curve allows. Each tier is a price and a battery level: while the feed-in price is above the tier's price, Battman sells as long as the battery is above that level. Spike selling doesn't wait for today's totals or the sell price protection.
<!-- /guide:summary -->

The card's note: "When prices spike the battery can export at a profit. Two tiers let it sell harder at higher prices." Battman checks its normal selling first, then Tier 1, then Tier 2, so give Tier 1 the higher price. **↻ Reset** puts all four back to the values under [Reset defaults](#defaults).

### Spike sell price (Tier 1)

In c/kWh. 500 (that's $5/kWh) to start with. From 0 to 10,000. At 0, any feed-in price above 0 counts as a spike.

### Sell above SOC (Tier 1)

In %. 10% to start with. Whole numbers from 0 to 100. During a Tier 1 spike, Battman sells while the battery is above this.

### Spike sell price (Tier 2)

In c/kWh. 100 (that's $1/kWh) to start with. From 0 to 10,000.

### Sell above SOC (Tier 2)

In %. 15% to start with. Whole numbers from 0 to 100. During a Tier 2 spike, Battman sells while the battery is above this.

<a id="protection"></a>
## Sell price protection

<!-- guide:summary id="settings.protection" -->
Stops Battman selling for less than you've been paying for grid power. Once your grid import since the reset hour and its average price are both above the thresholds here, Battman won't sell below that average plus your margin. It's off until **And average buy above** is more than 0.
<!-- /guide:summary -->

The card's note: "Stops selling below a margin over what you've been paying, once today's grid import and average buy price are both above these thresholds."

Protection also needs what you've spent on imports since the reset hour to be more than you've earned from exports since then. It sets a floor under normal selling (from the curves and the sell rules), not under spike selling or a Sell override. The engine's log shows "Min Sell:" and the floor while it applies.

These settings are kept with Battman's buy total (`sensor.battman_buy_total`), not with the other settings, and **↻ Reset** doesn't cover them. The card takes any number from 0 up. "Not set yet" shows until that sensor's first update.

### When import above

"Daily grid import that turns protection on", in kWh. 0 to start with.

### And average buy above

"Average buy price that turns protection on", in c/kWh. 0 to start with, which leaves protection off.

### Minimum sell is average buy plus

"Margin above the average buy price", in c/kWh. 0 to start with. The floor is the average buy price since the reset hour plus this.

### Allow last chance to sell lower

"Let last-chance discharge intervals ignore protection". Off to begin with.

> [!WARNING]
> **This setting does nothing.** The engine applies the protection floor again after every other step, so a sell rule's last chance never goes below it, whether this is on or off.

### Reset hour

"Hour of day the import tracking starts again (0 to 23)". 0 (midnight) to start with. Whole numbers from 0 to 23. The export tracking starts again at the same hour.

<a id="provider"></a>
## Power provider

<!-- guide:summary id="settings.provider" -->
Meant for choosing where Battman's buy and sell prices come from: Amber's live prices, or a retailer's fixed hourly tariff entered here. At present the choice changes nothing: the engine and Battman's money totals always use Amber's prices.
<!-- /guide:summary -->

The card's note: "Your electricity retailer and its hourly rates. Retail uses these rates instead of live Amber prices."

> [!WARNING]
> **Retail changes nothing yet.** The engine and the totals always use Amber's prices, whichever provider is chosen. The tariff only shows on `sensor.battman_power_provider_buy` and `sensor.battman_power_provider_sell`. See [issue #111](https://github.com/AJErazzor/battman/issues/111).

### Provider

"Where buy and sell prices come from": **Amber (live)** or **Retail (fixed)**. Amber to begin with ("Not set" until the provider sensors' first update). With Retail chosen, the rows below appear.

### Hour

"Hour to configure". The arrows step through the hours; under it, the **Buy tariff** and **Sell tariff** tabs choose which tariff the rows below change. "… has no tariff yet." means that tariff hasn't been saved yet.

### Normal price

"Standard buy rate for this hour" (Buy tariff) or "Standard sell (feed-in) rate for this hour" (Sell tariff), in c/kWh.

### Bonus price

"Cheaper rate while usage is under the limit" (Buy tariff) or "Better feed-in while export is under the limit" (Sell tariff), in c/kWh.

### Bonus limit

"Usage (kWh) that gets the bonus price" (Buy tariff) or "Export (kWh) that gets the bonus price" (Sell tariff), in kWh. At 0 the hour has no bonus price.

<a id="notifications"></a>
## Notifications

<!-- guide:summary id="settings.notifications" -->
Alerts sent to one phone through the Home Assistant Companion app: cheap and negative buy prices, the battery Live Activity on an iPhone's lock screen, feed-in spikes and power cuts. Choose the phone under **Notify target** first; every alert is off until you switch it on.
<!-- /guide:summary -->

The card's note: "Every alert goes to one phone, and each is off until you switch it on." The alerts are automations Battman writes for you; if one is missing, **Create automations** puts it back (see [Create automations](../start/device-page.md#create-automations)). If the card says "Battman setting not found:" and "Is Battman set up (and its packages loaded)?", see [Battman's package files aren't loaded](../help/repairs.md#packages-not-loaded).

### Notify target

"Which phone gets the alerts (Off silences all)". The list has every notify action in Home Assistant: phones by their device name, Alexa ones marked "(Alexa)". **— Off —** sends nothing, the Live Activity included. "Not set" means none has been chosen yet; "(not found)" means the one saved no longer exists.

<a id="notifications-cheap-price"></a>
### Cheap price

<!-- guide:summary id="settings.notifications.cheap-price" -->
A push when Amber's buy price drops below your limit, with buttons to charge the battery for 5 or 10 minutes. It's sent once each time the price drops below the limit, and not while the battery mode is already Charge (Buy).
<!-- /guide:summary -->

The push is "⚡ Cheap Power": "Buy …c · SOC …% · Charge battery?", with the buttons "5 min" and "10 min". A button sets the battery mode to Charge and starts the override timer for that long. The engine decides again at its next run, so the charge can end sooner.

#### Cheap-price alert

"Push when the buy price drops below the limit". Off to begin with.

#### Below

The limit, in c/kWh. 8 to start with. From 0 to 99.

<a id="notifications-negative-price"></a>
### Negative price

<!-- guide:summary id="settings.notifications.negative-price" -->
A push when Amber's buy price goes below zero, so you're paid to import, with buttons to charge the battery for 5, 10 or 15 minutes. It's sent once each time the price goes negative.
<!-- /guide:summary -->

The push is "💸 Negative Buy Price": "Buy …c — you're paid to import. Charge battery?", with the buttons "5 min", "10 min", "15 min" and "No". The charge buttons work as for the cheap-price alert.

#### Negative-price alert

"Push when you're paid to import". Off to begin with.

<a id="notifications-live-activity"></a>
### Live Activity

<!-- guide:summary id="settings.notifications.live-activity" -->
The battery on an iPhone's lock screen as a Live Activity: the feed-in price, the buy price, today's net and the battery level, in the battery mode's colour. Switch it on here, or let it follow something, such as the car, so it shows only when you want it.
<!-- /guide:summary -->

While it's on, the Live Activity updates when the battery level, the prices or the mode change, at most every 2 minutes, and restarts itself every 7 hours (iOS ends one after about 8). A value that's missing shows as "—". Its bar takes the mode's colour from the [Dashboard theme](#dashboard); with none chosen it's grey.

#### Live Activity

"Your battery on the phone's lock screen". This is `switch.battman_live_activity`. Off to begin with; turning it off clears the Live Activity.

#### Follow entity

The thing the Live Activity follows. Its description says "Blank: not following anything", or "Now:" with the entity's name and state. **Choose…** opens Home Assistant's picker: people, device trackers, binary sensors, switches, input booleans, text sensors, locks and covers, not Battman's own entities. "⚠ … not found" means the saved entity no longer exists. When you choose one, Battman starts the two states below on its usual pair, such as on and off, or home and not_home.

#### Show when it becomes

The state that turns the Live Activity on, when the entity changes to it. When the entity doesn't list its states, the card offers ones it has seen ("It doesn't declare its states, so these are ones it has reported lately."), with **Other…** to type one. The state has to match exactly. Coming back from unavailable doesn't count as a change.

#### Hide when it becomes

"And stays that way for the time below": the state that turns the Live Activity off.

#### Hide after

How long the entity must stay in that state before the Live Activity goes, in minutes. 2 to start with. Whole numbers from 0 to 60. A quick stop doesn't end it.

<a id="notifications-feed-in-spike"></a>
### Feed-in spike

<!-- guide:summary id="settings.notifications.feed-in-spike" -->
While the Live Activity is showing, an update with a sound when Amber's feed-in price goes above your level. Note that this level is in dollars, not cents.
<!-- /guide:summary -->

#### Spike alert

"Sound on the Live Activity when feed-in spikes". Off to begin with. It sounds once each time the price goes above the level, and only while the Live Activity is on.

#### Above

The level, in $/kWh. 0.3 ($0.30, that's 30c) to start with. From 0 to 20.

<a id="notifications-off-grid"></a>
### Off-grid

<!-- guide:summary id="settings.notifications.off-grid" -->
A time-sensitive push when your Sigenergy system loses the grid or is switched off-grid, with roughly how long the battery will last at the house's present use. Optionally a second push when the grid is back.
<!-- /guide:summary -->

The push is "🔌 Power outage" (or "🔌 Switched to off-grid" when it was done by hand), with "Battery …% · about … h at … kW" (minutes under an hour).

#### Off-grid alert

"Time-sensitive push, with how long the battery will last". Off to begin with.

#### Wait before alerting

"Ignores brief blips", in minutes: how long the system must be off-grid before the push. 1 to start with. Whole numbers from 0 to 30.

#### Grid-restored alert

"Also tell me when it is back". Off to begin with. It needs **Off-grid alert** on too. The push is "✅ Grid is back": "Battery …%". It's sent whenever the grid comes back, even after a blip too short for the outage push.

<a id="dashboard"></a>
## Dashboard options

<!-- guide:summary id="settings.dashboard" -->
How the Battman dashboard looks and behaves: a simpler set of mode buttons, the override timer, the colour theme and the Help view. Under **Confirmations**, when the mode buttons ask before they act.
<!-- /guide:summary -->

The card's note: "How the dashboard shows battery controls, and its theme."

### Simple battery mode

"Simple buy / sell / self-consume buttons instead of the full mode controls". Off to begin with. The Battery mode card shows just **Buy**, **Sell** and **Self Consume** while the mode is one of those; in any other mode it shows the full set.

### Always show override timer

"Keep the override timer visible even when no timer is running". Off to begin with. Otherwise the Overrides card shows the timer only while it's running and an override is on or pinned.

### Dashboard theme

The colour theme. The list has the Battman themes installed in Home Assistant, without "Battman" in front. Choosing one saves it and puts it on every view of the dashboard you're on, then redraws the dashboard: "✓ Theme applied". If the dashboard can't be changed: "Theme name saved, but the dashboard could not be changed:" and the reason. "Not set" means none has been chosen; "(not installed)" means the saved one has gone.

It's the same as **Make Active** on the Theme view. The Live Activity takes its colours from it. **↻ Reset** never changes it.

### Show help

"The Help view on the Battman dashboard". On to begin with. See [Showing or hiding the guide](../README.md#showing-or-hiding-the-guide).

<a id="dashboard-confirmations"></a>
### Confirmations

<!-- guide:summary id="settings.dashboard.confirmations" -->
When the mode buttons on the Battery mode card ask before acting. The question names the price and has **Cancel** and an "… anyway" button. **Active** and **Curtail** always ask; these two settings cover the mode buttons.
<!-- /guide:summary -->

#### Warn when a mode goes against the price

"Sell at a negative feed-in, HOOOOVER or House Party at a non-negative buy". On to begin with. **Sell** and **Sell Solar** ask "Feed-in is …c: you would pay to export. Sell anyway?" (or "Sell Solar anyway?") while the feed-in price is negative; **HOOOOVER** and **House Party** ask "Buy is …c: HOOOOVER is for negative prices. HOOOOVER anyway?" (or House Party) while the buy price is 0 or more.

#### Warn on Buy above

"Blank or 0: never", in c/kWh. 0 to start with. From 0 to 99. Above this buy price, **Buy** asks "Buy is …c, above your …c limit. Buy anyway?".

> [!WARNING]
> **Blank isn't accepted.** Clearing the box gets "Enter a number". To never ask, enter 0.

<a id="defaults"></a>
## Reset defaults

<!-- guide:summary id="settings.defaults" -->
The values each section's **↻ Reset** button puts back, for Buy, Sell, Spike selling, Needy curve triggers, Watchdog and Billing. Change them and press **Save defaults** to make your own values the ones Reset restores. Nothing here changes a setting until you press a Reset button.
<!-- /guide:summary -->

The card's note: "The values each ↻ Reset button puts back." This section starts folded. **Save defaults** checks every box first (a value it won't take gets its message at that row), then saves them all. A section's **↻ Reset** says "No defaults saved for this section (see Reset defaults)" if it has none.

They match a fresh install's values, except **Watchdog: disabled limit**. The Buy section's Reset also clears Buy Anytime (see [Buy](#buy)).

### Buy: prorate price SOC offset

Buy's **Prorate price SOC offset**, in %. 1 to start with.

### Buy: high price SOC offset

Buy's **High price SOC offset**, in %. 10 to start with.

### Sell: prorate price SOC offset

Sell's **Prorate price SOC offset**, in %. 30 to start with.

### Sell: low price SOC offset

Sell's **Low price SOC offset**, in %. 50 to start with.

### Spike tier 1 price

Spike selling's Tier 1 **Spike sell price**, in c/kWh. 500 to start with.

### Spike tier 1 above SOC

Spike selling's Tier 1 **Sell above SOC**, in %. 10 to start with.

### Spike tier 2 price

Spike selling's Tier 2 **Spike sell price**, in c/kWh. 100 to start with.

### Spike tier 2 above SOC

Spike selling's Tier 2 **Sell above SOC**, in %. 15 to start with.

### Needy: PV to full battery gap

Needy curve triggers' **PV to full battery gap**, in kWh. 3 to start with.

### Needy: house power above

Needy curve triggers' **House power above**, in kW. 3.5 to start with.

### Watchdog: not run limit

Watchdog's **Script not run limit**, in minutes. 10 to start with.

### Watchdog: disabled limit

Watchdog's **Script disabled limit**, in minutes. 10 to start with, though a fresh install has 60. The setting does nothing either way (see [Watchdog](#watchdog)).

### Billing: daily network charge

Billing's **Daily network charge**, in $. 1.09 to start with.

### Billing: bill day of month

Billing's **Bill day of month**. 2 to start with.
