// The browser half of shoot.py: draws the real cards in headless Chrome and saves the pictures.
//   node shoot.mjs <config.json>      (shoot.py makes the config and runs this)
import http from "http";
import fs from "fs";
import path from "path";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const CFG = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const CHROME = process.env.BATTMAN_CHROME || process.env.CHROME;
if (!CHROME) throw new Error("Set BATTMAN_CHROME to a Chromium or Chrome executable.");

const themeCss = ":root{" + Object.entries(CFG.theme).map(([k, v]) => `--${k}:${v};`).join("") + "}";
const PAGE = `<!doctype html><html><head><meta charset="utf-8"><style>${themeCss}
html,body{margin:0;background:var(--primary-background-color);font-family:Roboto,"Helvetica Neue",Arial,sans-serif;color:var(--primary-text-color)}
ha-card{display:block}
#host{width:__W__px}
#tbl{height:__H__px;overflow:hidden;background:var(--battman-surface-popup);text-align:center}  /* button-card centres its fields */</style></head><body><div id="host"></div></body></html>`;

// the files the cards load, served where Home Assistant serves them
const MIME = { ".js": "text/javascript", ".png": "image/png", ".webp": "image/webp", ".svg": "image/svg+xml", ".css": "text/css", ".json": "application/json" };
const server = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split("?")[0]);
  if (u.startsWith("/battmanfiles/")) {
    const f = path.join(CFG.www, u.slice("/battmanfiles/".length));
    if (f.startsWith(CFG.www) && fs.existsSync(f) && fs.statSync(f).isFile()) {
      res.writeHead(200, { "content-type": MIME[path.extname(f)] || "application/octet-stream" });
      return res.end(fs.readFileSync(f));
    }
  }
  const m = u.match(/^\/page-(\d+)-(\d+)$/);
  if (m) { res.writeHead(200, { "content-type": "text/html" }); return res.end(PAGE.replace("__W__", m[1]).replace("__H__", m[2])); }
  if (u === "/favicon.ico") { res.writeHead(204); return res.end(); }
  res.writeHead(404); res.end();
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const base = `http://127.0.0.1:${server.address().port}`;

const browser = await chromium.launch({ executablePath: CHROME });
const problems = [];
try {
  for (const [name, shot] of Object.entries(CFG.shots)) {
    const ctx = await browser.newContext({ viewport: { width: shot.width + 40, height: 900 }, deviceScaleFactor: 2,
      timezoneId: CFG.tz, locale: "en-AU" });
    const page = await ctx.newPage();
    page.on("pageerror", (e) => problems.push(`${name}: ${e.message}`));
    page.on("console", (m) => { if (m.type() === "error") problems.push(`${name}: ${m.text()} ${m.location().url || ""}`); });
    // the clock stands still at the time the sample data is for
    await page.addInitScript((now) => {
      const T = Date.parse(now), D = Date;
      globalThis.Date = class extends D { constructor(...a) { super(...(a.length ? a : [T])); } static now() { return T; } };
    }, CFG.now);
    await page.goto(`${base}/page-${shot.kind === "settings" ? shot.width + 34 : shot.width}-${shot.height || 0}`);

    if (shot.kind === "settings") {
      await page.evaluate(async ({ cfg, types }) => {
        const S = cfg.settings;
        const states = {
          [cfg.map.parameters]: { state: "ok", attributes: S.params },
          [cfg.map.sell_rules]: { state: S.sell_rules.state, attributes: S.sell_rules.attributes },
          [cfg.map.buy_rules]: { state: S.buy_rules.state, attributes: S.buy_rules.attributes },
          [cfg.map.buy_total]: { state: "0", attributes: {} },
          [cfg.map.power_provider_buy]: { state: "amber", attributes: {} },
          [cfg.map.power_provider_sell]: { state: "amber", attributes: {} },
        };
        const hass = { states, themes: {}, config: { time_zone: cfg.tz }, user: { name: "Battman", is_admin: true }, language: "en",
          callApi: async () => ({ entities: cfg.map }), callWS: async () => ({}), callService: async () => {},
          connection: { sendMessagePromise: async () => ({}), sendMessage() {} } };
        window.__hass = hass;
        // Home Assistant's own <ha-card> is a block box; without it the card's width-based layout never starts
        if (!customElements.get("ha-card")) customElements.define("ha-card", class extends HTMLElement { connectedCallback() { this.style.display = "block"; } });
        await import("/battmanfiles/battman-settings.js");
        await customElements.whenDefined("battman-settings");
        const card = document.createElement("battman-settings");
        card.setConfig({ type: "custom:battman-settings" });
        document.getElementById("host").appendChild(card);
        card.hass = hass;
      }, { cfg: CFG, types: null });
      const sec = page.locator(`.sec[data-sec="${shot.section}"]`);
      await sec.waitFor({ timeout: 10000 });
      await page.waitForTimeout(600);                                     // fonts and the logo
      await sec.screenshot({ path: path.join(CFG.out, name + ".png") });
      const box = await sec.boundingBox();
      console.log(`${name}.png  ${Math.round(box.width * 2)}x${Math.round(box.height * 2)}`);
    } else if (shot.kind === "table") {
      const html = await page.evaluate(({ js, states, tz }) => {
        const body = js.trim().replace(/^\[\[\[/, "").replace(/\]\]\]$/, "");
        const f = new Function("states", "entity", "hass", "user", "variables", body);
        return f(states, null, { states, config: { time_zone: tz } }, {}, {});
      }, { js: CFG.table.js, states: CFG.table.states, tz: CFG.tz });
      await page.evaluate((h) => { const d = document.createElement("div"); d.id = "tbl"; d.innerHTML = h; document.getElementById("host").appendChild(d); }, html);
      await page.waitForTimeout(300);
      await page.locator("#tbl").screenshot({ path: path.join(CFG.out, name + ".png") });
      console.log(`${name}.png  ${shot.width * 2}x${shot.height * 2}`);
    }
    await ctx.close();
  }
} finally {
  await browser.close();
  server.close();
}
if (problems.length) { console.error("Problems in the page:\n" + problems.join("\n")); process.exit(1); }
