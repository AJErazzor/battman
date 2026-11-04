// Runs the real Solar card against dummy states (no browser): node solar_today_check.mjs <battman-solar-card.js>
// Prints each scenario's figures as JSON (run by tests/test_solar_card.py).
import { load, render } from "./solar_card_harness.mjs";

const K = await load(process.argv[2]);
const kwh = { unit_of_measurement: "kWh" }, kW = { unit_of_measurement: "kW" };
// Sigenergy sensors that exist in HA but that this card was never told about
const unrelated = { "sensor.sigen_plant_third_party_pv_power": [1.0, kW], "sensor.sigen_inverter_pv_power": [3.0, kW],
  "sensor.sigen_plant_daily_third_party_inverter_energy": [12.3, kwh], "sensor.sigen_inverter_daily_pv_energy": [9.9, kwh] };
const mine = { "sensor.my_inverter1_power": [4.0, kW], "sensor.my_inverter2_power": [2.0, kW],
  "sensor.my_solcast_today": [30, { estimate: 30, estimate10: 24, estimate_aaaa: 18, estimate_bbbb: 12 }] };
const base = { type: "custom:battman-solar-card", view: "now", forecast_today: "sensor.my_solcast_today" };
const inv = (power, today, site) => ({ power, ...(today ? { today } : {}), site });
const out = {};
// 1. two inverters, only each Power sensor + site: Today is blank, never another sensor's figure
out.powerOnly = render(K, { ...base, inverters: [inv("sensor.my_inverter1_power", "", "aaaa"), inv("sensor.my_inverter2_power", "", "bbbb")] },
  { ...mine, ...unrelated }).today;
// 2. with their own energy sensors, Today follows those
out.withEnergy = render(K, { ...base, inverters: [inv("sensor.my_inverter1_power", "sensor.my_inverter1_energy", "aaaa"),
  inv("sensor.my_inverter2_power", "sensor.my_inverter2_energy", "bbbb")] },
  { ...mine, ...unrelated, "sensor.my_inverter1_energy": [5.5, kwh], "sensor.my_inverter2_energy": [3.2, kwh] }).today;
// 3. only one inverter has an energy sensor: the total isn't a partial sum
out.oneEnergy = render(K, { ...base, inverters: [inv("sensor.my_inverter1_power", "sensor.my_inverter1_energy", "aaaa"),
  inv("sensor.my_inverter2_power", "", "bbbb")] }, { ...mine, ...unrelated, "sensor.my_inverter1_energy": [5.5, kwh] }).today;
// 4. nothing set up, though Sigenergy sensors exist: nothing is drawn or added
const none = render(K, { ...base, forecast_today: undefined }, unrelated);
out.nothing = { today: none.today, msg: none.text };
// 5. the older symo / sig entries still work when they name their own power sensor, and are ignored when they don't
out.legacy = render(K, { ...base, sig: { power: "sensor.my_inverter1_power", today: "sensor.my_inverter1_energy" }, symo: { show: true } },
  { ...mine, ...unrelated, "sensor.my_inverter1_energy": [5.5, kwh] }).today;
// 6. names: the one typed, else the power sensor's device, else the sensor's own name
const reg = { entities: { "sensor.my_inverter1_power": { device_id: "d1" } }, devices: { d1: { name: "Fronius Symo", name_by_user: null } } };
const names = render(K, { ...base, inverters: [inv("sensor.my_inverter1_power", "", ""), { power: "sensor.my_inverter2_power", label: "Roof west" }] }, mine, reg);
out.names = ["Fronius Symo", "Roof west"].map((n) => names.html.includes(n));
const plain = render(K, { ...base, inverters: [inv("sensor.my_inverter2_power", "", "")] }, { ...mine, "sensor.my_inverter2_power": [2.0, { unit_of_measurement: "kW", friendly_name: "Roof sensor" }] }, reg);
out.fallbackName = plain.html.includes("Roof sensor");
console.log(JSON.stringify(out));
