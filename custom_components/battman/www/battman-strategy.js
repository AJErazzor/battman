// Battman dashboard strategy.
//
// A dashboard whose whole config is
//     strategy:
//       type: custom:battman
// is "managed": its views come from Battman (custom_components/battman/views/*.yaml,
// with entity names filled from Battman's entity map), every time it opens, so new
// and changed views arrive with Battman updates. "Take control" in HA turns it into
// a normal dashboard you own, and Battman never touches it again.
// Add `theme: <name>` under `strategy:` to put every Battman view on one theme.
//
// No fallbacks: if Battman can't build the views, the dashboard says exactly why.

function errorView(lines) {
  return {
    title: "Battman",
    path: "battman-error",
    cards: [
      {
        type: "markdown",
        content:
          "## Battman dashboard problem\n\n" + lines.map((l) => "- " + l).join("\n"),
      },
    ],
  };
}

class BattmanDashboardStrategy {
  static async generate(config, hass) {
    let data;
    try {
      data = await hass.callApi("GET", "battman/dashboard");
    } catch (err) {
      return {
        title: "Battman",
        views: [errorView([
          "Could not load the dashboard from the Battman integration (" +
            ((err && (err.message || err.body || err.status_code)) || err) + ").",
          "Is Battman installed, set up, and has Home Assistant been restarted since updating?",
        ])],
      };
    }
    if (data.errors && data.errors.length) {
      return { title: "Battman", views: [errorView(data.errors)] };
    }
    // Optional dashboard-wide theme (set by the theme studio's Make Active, or by
    // hand):  strategy: {type: custom:battman, theme: Battman Neon Drift}
    if (config && config.theme) data.views.forEach((v) => { v.theme = config.theme; });
    return { title: "Battman", views: data.views };
  }
}

// Register a custom element so HA finds it. HA's frontend may swap window.customElements for
// its own registry (a compatibility layer) while it starts; anything registered just before the
// swap is lost to HA. So register now, and again in HA's registry if the swap comes after us.
function battmanDefine(tag, cls) {
  const reg = window.customElements;
  if (!reg.get(tag)) reg.define(tag, cls);
  const t0 = Date.now();
  (function watch() {
    const now = window.customElements;
    if (now !== reg) {
      if (!now.get(tag)) {
        try { now.define(tag, cls); } catch (e) { console.error(`Battman: couldn't register ${tag}: ${e.message}`); }
      }
      return;
    }
    // HA's registry was already in place when we registered (it leaves this marker): nothing to wait for
    if (window.CustomElementRegistryPolyfill) return;
    if (Date.now() - t0 < 30000) setTimeout(watch, 20);
  })();
}

battmanDefine("ll-strategy-dashboard-battman", BattmanDashboardStrategy);
