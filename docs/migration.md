# Moving from Smiggles to Battman

Battman can run the battery instead of Smiggles. Installing or updating Battman changes nothing
about who controls the battery: Battman's engine is installed switched off
(`binary_sensor.battman_in_charge` is off; its settings and curves sit at their defaults). One action moves control across, and one moves it back.

## What Migrate does

`battman.migrate_from_smiggles` with **confirm on**:

1. Checks Battman's engine entities and automations are loaded (creates any that are missing).
2. Turns **off every Smiggles automation** (by name: SolarSystem…, Smiggles…, SSC…) and stops the
   Smiggles script. It remembers which were on.
3. Copies Smiggles into Battman: settings and overrides, run data, buy/sell rules, power provider,
   SOC and price curves, the cost odometers (totals and every day/month/year figure), enable,
   no export, mode, high consumption, the override timer (with the time it had left), the engine
   log file, and the odometers' long-term statistics (so their graphs carry on).
4. Turns Smiggles' enable off, turns Battman in charge on, and runs the engine once.
   The cards switch to Battman's entities (refresh the browser).

With **confirm off** it's a dry run: it lists exactly what it would turn off and copy, and changes
nothing.

`battman.hand_back_to_smiggles` (confirm on) reverses it: Battman's engine stops, Battman's
settings, overrides, rules, curves, power provider, mode, no export, high consumption and timer are
copied back into Smiggles', the Smiggles automations that were on go back on, Smiggles' enable is
set as Battman's was, and the cards switch back. (Smiggles' odometers kept counting the whole time,
so they're current.)

## Run it (A.J.)

Before:

1. Update Battman (HACS), restart HA.
2. Settings → Repairs: nothing from Battman. (If "packages not loaded" or "engine automations didn't
   load" shows, stop and tell Claude.)
3. Check Battman is installed but idle: `binary_sensor.battman_in_charge` = off;
   Settings → Automations shows the eight "Battman engine – …" automations.
4. **Take a full backup** (Settings → System → Backups). Restoring it later rolls back everything
   since, including history recorded after it.

Migrate:

5. Developer tools → Actions → `Battman: Migrate from Smiggles`, confirm **off** → Perform action.
   Read the response: `can_migrate: true`, no problems; the `turn_off` list is all Smiggles
   automations and nothing else of yours.
6. Same action, confirm **on**. A notification says Battman is in charge.

Check (refresh the browser first):

7. `binary_sensor.battman_in_charge` on; Smiggles automations all off; Smiggles enable off.
8. Battman dashboard: mode, overrides, odometers and curves show what Smiggles had.
9. Engine log popup / Log card: Smiggles' history, then a new Battman run line.
10. Change something live: set an override (or a scene) and watch the mode change and the Sigen
    EMS mode follow; flip no export and watch the export limit go to 0 and back (18.2).
11. Leave it a few hours: each 5-minute price change runs the engine (Log card).

If anything's wrong: `Battman: Hand back to Smiggles`, confirm on (Smiggles is back as it was).
If that's not enough: restore the backup.

## Another Smiggles user

Install Battman, restart, check Repairs is empty, take a backup, run the dry run, then Migrate.
Their Amber entity names go on Battman's Configure screen first if they differ. Sigen and Solcast
are used by name: Battman's Repairs name any that's missing (rename yours to the name given).

## What doesn't move

- **State history** (the graph lines) of Smiggles' entities stays under their names; Battman's
  start at migration. The three odometers' long-term statistics are copied.
- **Smiggles' own dashboard** still shows Smiggles' entities: after migrating, use Battman's.
- **Live Activity** automations made by Battman follow the map; ones you've set your own entities on
  keep them.
- Smiggles stays installed (its sensors keep updating, its automations stay off) until you remove it.
  Remove it only after you're happy, and after that Hand back isn't possible.
