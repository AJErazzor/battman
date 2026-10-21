// Real-browser check of the Battman Image card (run by tests/test_v0180.py).
// usage: NODE_PATH=<node_modules with playwright> CHROME=<chromium> node image_check.js <battman-cards.js> <images dir> <scratch dir>
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
(async () => {
  const [src, imagesDir, dir] = process.argv.slice(2);
  fs.writeFileSync(path.join(dir, "battman-cards.js"), fs.readFileSync(src, "utf8"));
  fs.writeFileSync(path.join(dir, "index.html"), `<!doctype html><html><body style="margin:0">
<script>
window.loadCardHelpers = async () => ({ createCardElement: () => document.createElement("div") });
// a stand-in for HA's ha-form: keeps what the editor gives it, and can send a change back
customElements.define("ha-form", class extends HTMLElement {
  send(value) { this.dispatchEvent(new CustomEvent("value-changed", { detail: { value } })); }
});
customElements.define("ha-card", class extends HTMLElement { connectedCallback() { this.style.display = "block"; } });
</script>
<script type="module" src="battman-cards.js"></script>
<div id="fixed" style="width:600px;height:300px"></div>
<div id="flat" style="width:600px"></div>
</body></html>`);
  const http = require("http");
  const server = http.createServer((req, res) => {
    const url = req.url.split("?")[0];
    let f = path.join(dir, url);
    if (url.startsWith("/api/battman/image/")) f = path.join(imagesDir, decodeURIComponent(url.slice(19)));
    if (!fs.existsSync(f)) { res.statusCode = 404; return res.end(); }
    res.setHeader("content-type", f.endsWith(".js") ? "text/javascript" : f.endsWith(".webp") ? "image/webp" : "text/html");
    res.end(fs.readFileSync(f));
  }).listen(0);
  const port = server.address().port;
  const browser = await chromium.launch({ executablePath: process.env.CHROME });
  const page = await browser.newPage({ viewport: { width: 1000, height: 800 } });
  await page.goto(`http://127.0.0.1:${port}/index.html`);
  await page.waitForFunction(() => customElements.get("battman-image"));
  const names = fs.readdirSync(imagesDir);
  const out = {};

  await page.evaluate((names) => {
    window.hass = {
      themes: { darkMode: false, themes: {} }, states: {},
      callApi: async () => ({
        folder: "battman/images",
        images: [...names.map((n) => ({ name: n, source: "battman", url: `/api/battman/image/${n}` })),
          { name: "my-house.png", source: "yours", url: "/api/battman/image/my-house.png" }],
      }),
    };
    window.make = async (config, where = "flat") => {
      const el = document.createElement("battman-image");
      el.setConfig(config);
      el.hass = window.hass;
      document.getElementById(where).replaceChildren(el);
      await new Promise((r) => setTimeout(r, 300));
      return el;
    };
    window.look = (el) => {
      const img = el.shadowRoot.querySelector("img");
      const problem = el.shadowRoot.querySelector("b") ? el.shadowRoot.textContent.trim() : "";
      if (!img) return { problem };
      const cs = getComputedStyle(img);
      const card = el.shadowRoot.querySelector("ha-card");
      return { problem, src: img.getAttribute("src"), fit: cs.objectFit, pos: cs.objectPosition, h: Math.round(img.getBoundingClientRect().height),
        w: Math.round(img.getBoundingClientRect().width), loaded: img.complete && img.naturalWidth > 0, flip: cs.transform,
        bg: getComputedStyle(card).backgroundColor, shadow: card.style.boxShadow, alt: img.alt };
    };
  }, names);

  out.stub = await page.evaluate(() => customElements.get("battman-image").getStubConfig());
  out.picker = await page.evaluate(() => window.customCards.filter((c) => c.type === "battman-image").length);
  out.auto = await page.evaluate(async () => look(await make({ type: "custom:battman-image", image: "battman-main.webp" })));
  out.grid = await page.evaluate(async () => [(await make({ type: "x", image: "battman-main.webp" })).getGridOptions(),
    (await make({ type: "x", image: "battman-main.webp", height: "fill" }, "fixed")).getGridOptions()]);
  out.fill = await page.evaluate(async () => look(await make({ type: "x", image: "battman-main.webp", height: "fill", fit: "cover", position: "bottom", padding: 10 }, "fixed")));
  out.fillFlat = await page.evaluate(async () => look(await make({ type: "x", image: "battman-main.webp", height: "fill" }, "flat")));
  out.fixedPx = await page.evaluate(async () => look(await make({ type: "x", image: "battman-main.webp", height: 150, fit: "contain", background: "none", frame: false, flip: true, alt: "Battman" })));
  out.colour = await page.evaluate(async () => look(await make({ type: "x", image: "battman-main.webp", background: "colour", background_color: "#ff0000" })));
  out.colourMissing = await page.evaluate(async () => look(await make({ type: "x", image: "battman-main.webp", background: "colour" })));
  out.missing = await page.evaluate(async () => look(await make({ type: "x", image: "gone.webp" })));
  out.notLoading = await page.evaluate(async () => look(await make({ type: "x", image: "my-house.png" })));
  out.bad = await page.evaluate(() => ["fitt", "fit", "height", "narrow"].map((k) => {
    const c = { type: "x", image: "battman-main.webp" };
    if (k === "fitt") c.fitt = "cover"; if (k === "fit") c.fit = "zoom"; if (k === "height") c.height = "tall";
    if (k === "narrow") c.narrow = { height: 100 };
    try { document.createElement("battman-image").setConfig(c); return "accepted"; } catch (e) { return e.message; }
  }));
  out.noImage = await page.evaluate(() => { try { document.createElement("battman-image").setConfig({ type: "x" }); return "accepted"; } catch (e) { return e.message; } });

  // overrides: narrow (screen width), dark (HA's dark mode); narrow wins
  const cfg = { type: "x", image: "battman-main.webp", fit: "contain", dark: { fit: "cover", position: "top" }, narrow: { fit: "stretch" } };
  await page.evaluate(async (cfg) => { window.ov = await make(cfg); }, cfg);
  out.wideLight = await page.evaluate(() => look(ov).fit);
  await page.evaluate(async () => { hass = { ...hass, themes: { ...hass.themes, darkMode: true } }; ov.hass = hass; await new Promise((r) => setTimeout(r, 200)); });
  out.wideDark = await page.evaluate(() => [look(ov).fit, look(ov).pos]);
  await page.setViewportSize({ width: 500, height: 800 });
  await page.waitForTimeout(300);
  out.narrowDark = await page.evaluate(() => [look(ov).fit, look(ov).pos]);
  await page.setViewportSize({ width: 1000, height: 800 });
  await page.waitForTimeout(300);
  out.backWide = await page.evaluate(() => look(ov).fit);

  // the editor: image list (yours marked), form data, and the YAML it writes back
  out.editor = await page.evaluate(async () => {
    const ed = document.createElement("battman-image-editor");
    document.body.append(ed);
    ed.setConfig({ type: "custom:battman-image", image: "battman-main.webp", grid_options: { rows: 5 } });
    ed.hass = window.hass;
    await new Promise((r) => setTimeout(r, 200));
    const form = ed.querySelector("ha-form");
    const opts = form.schema[0].selector.select.options;
    let got = null;
    ed.addEventListener("config-changed", (e) => { got = e.detail.config; });
    form.send({ ...form.data, fit: "cover", height_mode: "fill", narrow: { fit: "contain", flip: "on", padding: undefined }, dark: { image: "" } });
    const changed = got;
    form.send({ ...form.data, height_mode: "fixed", height_px: 240, frame: false });
    return { opts: opts.map((o) => o.label), data: form.data, changed, fixed: got,
      preview: ed.querySelector(".preview img") && ed.querySelector(".preview img").getAttribute("src"),
      labels: form.computeLabel({ name: "narrow" }) };
  });
  out.editorMissing = await page.evaluate(async () => {
    const ed = document.createElement("battman-image-editor");
    document.body.append(ed);
    ed.setConfig({ type: "custom:battman-image", image: "gone.webp" });
    ed.hass = window.hass;
    await new Promise((r) => setTimeout(r, 200));
    return [ed.querySelector(".msg").textContent, ed.querySelector("ha-form").schema[0].selector.select.options[0].label];
  });
  await page.screenshot({ path: path.join(dir, "shot.png"), fullPage: true });
  console.log(JSON.stringify(out));
  await browser.close();
  server.close();
})().catch((e) => { console.error(e); process.exit(1); });
