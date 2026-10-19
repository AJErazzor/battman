// Battman dashboard strategy.
//
// A dashboard whose whole config is
//     strategy:
//       type: custom:battman
// is "managed": Battman builds its views here, every time it opens, so new and
// changed views arrive with Battman updates. "Take control" in HA turns it into
// a normal dashboard you own, and Battman never touches it again.

const BATTMAN_THEME = "Battman Coffee";

// Full-bleed iframe styling for Battman pages (needs card-mod).
const IFRAME_CARD_MOD = {
  style:
    "ha-card { height: 100%; background: transparent; border: none; box-shadow: none; padding: 0; overflow: hidden; }\n" +
    ".wrapper { height: 100% !important; padding: 0 !important; }\n" +
    "iframe { height: 100% !important; width: 100% !important; border: 0 !important; }",
};

function pageView({ title, path, icon, url, rows }) {
  return {
    title,
    path,
    icon,
    theme: BATTMAN_THEME,
    type: "sections",
    max_columns: 4,
    sections: [
      {
        type: "grid",
        column_span: 4,
        cards: [
          {
            type: "iframe",
            url,
            grid_options: { columns: "full", rows },
            card_mod: IFRAME_CARD_MOD,
          },
        ],
      },
    ],
  };
}

class BattmanDashboardStrategy {
  static async generate(config, hass) {
    return {
      title: "Battman",
      views: [
        pageView({
          title: "Cost",
          path: "cost",
          icon: "mdi:cash-multiple",
          url: "/battman/cost-chart.html",
          rows: 9,
        }),
      ],
    };
  }
}

if (!customElements.get("ll-strategy-dashboard-battman")) {
  customElements.define("ll-strategy-dashboard-battman", BattmanDashboardStrategy);
}
