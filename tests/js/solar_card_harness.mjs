// Runs a real battman-solar-card.js against dummy HA states: stub card base, fake DOM, no browser.
import fs from 'fs'; import path from 'path'; import os from 'os';
export async function load(cardPath) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'solar-'));
  fs.copyFileSync(cardPath, path.join(dir, 'card.mjs'));
  fs.writeFileSync(path.join(dir, 'battman-card-base.js'), `
export class BattmanCardBase { attachShadow(){ this.shadowRoot = globalThis.__root; return this.shadowRoot; }
  set hass(h){ this._hass = h; if (!this._run) this._run = this.run(this.shadowRoot) || {}; }
  get hass(){ return this._hass; } dispatchEvent(){} }
export const battmanDefine = (n, k) => { globalThis.__K = k; }; export const battmanPicker = () => {}; export const esc = (s) => String(s); export const inCardPicker = () => {};`);
  globalThis.HTMLElement = class {}; globalThis.CustomEvent = class {};
  globalThis.localStorage = { getItem() { return null; }, setItem() {} };
  globalThis.getComputedStyle = () => ({ getPropertyValue: () => '' });
  await import(path.join(dir, 'card.mjs'));
  return globalThis.__K;
}
export function render(Klass, config, states) {
  const els = {}; globalThis.__root = { getElementById: (id) => (els[id] ??= { innerHTML: '', textContent: '' }), addEventListener() {} };
  const c = new Klass(); c.attachShadow({ mode: 'open' }); c.setConfig(config);
  const st = Object.fromEntries(Object.entries(states).map(([id, v]) => [id, { state: String(v[0]), attributes: v[1] || {} }]));
  c.hass = { states: st, themes: {}, callWS: async () => [], callApi: async () => [], config: { time_zone: 'Australia/Adelaide' } };
  const html = els.b.innerHTML;
  return { today: [...html.matchAll(/Today <b>([^<]*)<\/b>/g)].map((m) => m[1]), text: html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 260) };
}
