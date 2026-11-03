// Runs the real Solar card against dummy states (no browser): node solar_today_check.mjs <battman-solar-card.js>
// Prints each scenario's "Today" figures as JSON (run by tests/test_solar_card.py).
import { load, render } from "./solar_card_harness.mjs";

const K = await load(process.argv[2]);
const kwh = { unit_of_measurement: "kWh" }, kW = { unit_of_measurement: "kW" };
// the Sigenergy sensors the card's own defaults point at (a Sigenergy install has them)
const defaults = { "sensor.sigen_plant_daily_third_party_inverter_energy": [12.3, kwh], "sensor.sigen_inverter_daily_pv_energy": [9.9, kwh] };
const mine = { "sensor.my_inverter1_power": [4.0, kW], "sensor.my_inverter2_power": [2.0, kW],
  "sensor.my_solcast_today": [30, { estimate: 30, estimate10: 24, estimate_aaaa: 18, estimate_bbbb: 12 }] };
const base = { type: "custom:battman-solar-card", view: "now", forecast_today: "sensor.my_solcast_today" };
const out = {};
// 1. the issue: two inverters, only each Power sensor + site (and the forecast sensor) filled in
out.powerOnly = render(K, { ...base, symo: { power: "sensor.my_inverter1_power", site: "aaaa" }, sig: { power: "sensor.my_inverter2_power", site: "bbbb" } },
  { ...mine, ...defaults }).today;
// 2. with their own energy sensors, Today follows those
out.withEnergy = render(K, { ...base, symo: { power: "sensor.my_inverter1_power", today: "sensor.my_inverter1_energy", site: "aaaa" },
  sig: { power: "sensor.my_inverter2_power", today: "sensor.my_inverter2_energy", site: "bbbb" } },
  { ...mine, ...defaults, "sensor.my_inverter1_energy": [5.5, kwh], "sensor.my_inverter2_energy": [3.2, kwh] }).today;
// 3. only one inverter has an energy sensor: the total isn't a partial sum
out.oneEnergy = render(K, { ...base, symo: { power: "sensor.my_inverter1_power", today: "sensor.my_inverter1_energy", site: "aaaa" },
  sig: { power: "sensor.my_inverter2_power", site: "bbbb" } }, { ...mine, ...defaults, "sensor.my_inverter1_energy": [5.5, kwh] }).today;
// 4. the card's own defaults together (a Sigenergy install, nothing configured): unchanged
out.defaults = render(K, { ...base, forecast_today: undefined }, { "sensor.sigen_plant_third_party_pv_power": [1.0, kW], "sensor.sigen_inverter_pv_power": [3.0, kW], ...defaults }).today;
console.log(JSON.stringify(out));
