# Notifications

**Settings → Notifications** on the Battman dashboard. Every alert goes to one **notify target**
(one of HA's notify services; **Off** silences them all), and each is **off** until you switch it on.

| Alert | Setting(s) | Default |
|---|---|---|
| Notify target | `alertNotifyTarget` | Off |
| Cheap-price alert | `amberBuyAlert`; fires when the buy price is below `amberBuyAlertThreshold` (c/kWh) | off, 8 |
| Negative-price alert | `amberNegativeBuyAlert` | off |
| Live Activity | `liveActivityEnabled` is the master setting; `liveActivity` is whether it is showing (see [live-activity.md](live-activity.md)) | on, off |
| Spike alert | `liveActivitySpikeAlertOn`, above `liveActivitySpikeAlert` ($/kWh); a plain push, independent of the Live Activity and the car | off, 0.30 |
| Off-grid alert | `offGridAlert`, after `offGridAlertDelay` minutes (0–30) | off, 1 |
| Grid-restored alert | `offGridRestoredAlert` | off |

The Amber alerts carry **Charge** buttons (5 and 10 minutes; the negative-price one also 15): tapping one sets Charge mode and
starts the override timer for that long.

The **off-grid alert** is a time-sensitive push (it gets through iPhone Focus modes). It uses
`sensor.sigen_plant_grid_connection_status`: **Off Grid (Auto)** (`off_grid_auto` in Sigenergy-Local-Modbus 2.x)
is titled *Power outage*, **Off Grid (Manual)** (`off_grid_manual`) *Switched to off-grid*. The message says the battery level and roughly how
long it will last: rated capacity × SOC ÷ the house's current load.

## The automations

Battman writes them to `automations.yaml` from its blueprints, once, on the first start of a version
that has them (so a release's new ones arrive by themselves, and one you delete stays deleted):

`battman_amber_buy_alert`, `battman_amber_negative_alert`, `battman_amber_charge_action`,
`battman_offgrid_alert`, `battman_spike_alert`, and the three Live Activity ones with their script.

They're yours to edit (Battman never overwrites one that exists). **Create automations** (a button on
the Battman device, or the action `battman.create_automations`) makes any that are missing, engine
ones included. If HA can't load them, a Repair says so.

If you made your own copies of the Amber alerts before v0.34.0 (they read the same settings), delete
them: Battman's replace them, and both would send.
