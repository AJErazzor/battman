"""v0.21.0: Cost compare, Cost chart, Settings and Theme studio are real cards, like the Log.

- Each draws itself (www/battman-<id>.js, loaded on every HA page): no page in a frame, no login
  token taken from the page around it, no card-mod. The old pages and card files are gone.
- What they share is in two modules: battman-card-base.js (the card element, entity map, theme
  and entity checks, Chart.js loader) and battman-cost-data.js (the two cost cards' day figures).
- The datalabels plugin is gone from vendor/ (no card used it).
- Theme studio's State card demo gets the State card from Battman (it never found it before), and
  runs on its mocked values, so the card's live missing-sensor check is left out there.
"""

import json
import re
import subprocess
from pathlib import Path

import yaml
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .dashboard_views import built

ROOT = Path(__file__).parents[1] / "custom_components/battman"
WWW = ROOT / "www"
CARDS = {"cost-compare": "BattmanCostCompareCard", "cost-chart": "BattmanCostChartCard",
         "settings": "BattmanSettingsCard", "theme-studio": "BattmanThemeStudioCard"}
OLD_PAGES = ("cost-compare", "cost-chart", "settings", "theme-studio")


def test_each_card_is_a_real_card() -> None:
    init = (ROOT / "__init__.py").read_text()
    loaded = re.search(r'for name in \(([^)]*)\):\n\s+frontend\.add_extra_js_url', init).group(1)
    wrapper = (WWW / "battman-cards.js").read_text()
    own = wrapper[wrapper.index("const OWN_SCRIPT_CARDS = {"):]
    own = own[:own.index("};")]
    for cid, cls in CARDS.items():
        f = WWW / f"battman-{cid}.js"
        assert subprocess.run(["node", "--check", str(f)]).returncode == 0, cid
        js = f.read_text()
        assert f'battmanDefine("battman-{cid}", {cls})' in js and f"class {cls} extends BattmanCardBase" in js, cid
        assert f'static preview = "{cid}.webp";' in js and (WWW / f"previews/{cid}.webp").stat().st_size > 1000, cid
        assert f'battmanPicker("battman-{cid}",' in js, cid
        assert f'"{cid}"' in loaded, cid
        assert f'"{cid}": "battman-{cid}.js"' in own or f'{cid}: "battman-{cid}.js"' in own, cid
        # HA's connection, not a token taken from the page around it, and no frame
        for gone in ("access_token", "parent.document", "frameElement", "window.parent", "fetch(", "iframe",
                     "cdnjs.cloudflare.com", "cdn.jsdelivr.net", "card_mod:", "\"card_mod\""):
            assert gone not in js, (cid, gone)
    for page in OLD_PAGES:
        assert not (WWW / f"{page}.html").exists() and not (ROOT / f"cards/{page}.yaml").exists(), page
    assert not (WWW / "vendor/chartjs-plugin-datalabels.min.js").exists()


def test_shared_modules() -> None:
    base = (WWW / "battman-card-base.js").read_text()
    for name in ("battmanDefine", "battmanPicker", "loadChartJs", "battmanMap", "missingEntities", "missingThemeVars",
                 "problemHtml", "BattmanCardBase"):
        assert re.search(rf"^export (async )?(function |class )?{name.replace('class ', '')}\b", base, re.M), name
    for cid in ("cost-compare", "cost-chart"):
        js = (WWW / f"battman-{cid}.js").read_text()
        assert 'from "./battman-cost-data.js"' in js and "costData(() => card.hass," in js, cid
    for cid in (*CARDS, "log"):
        assert 'from "./battman-card-base.js"' in (WWW / f"battman-{cid}.js").read_text(), cid


def _node_module(code: str):
    r = subprocess.run(["node", "--input-type=module", "-e", code], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def test_cost_data_bill_cycle_and_today() -> None:
    url = (WWW / "battman-cost-data.js").as_uri()
    out = _node_module(f"""
import {{ costData, toDateStr }} from "{url}";
const states = {{
  "sensor.p": {{ attributes: {{ billDayOfMonth: 2, dailyNetworkCharge: 1.25 }} }},
  "sensor.b": {{ attributes: {{ day: 3.5 }} }}, "sensor.s": {{ attributes: {{ day: 1 }} }},
}};
const d = costData(() => ({{ states }}), {{ buy: "sensor.b", sell: "sensor.s", fee: "sensor.f", param: "sensor.p" }});
const today = new Date(); today.setHours(0, 0, 0, 0);
const old = new Date(2026, 0, 10);
const maps = {{ buyM: {{ "2026-01-10": 2 }}, sellM: {{ "2026-01-10": 4 }}, feeM: {{}}, present: {{}} }};
process.stdout.write(JSON.stringify({{
  billDay: d.billDay(),
  thisCycle: toDateStr(d.cycleStart(new Date(2026, 9, 23), 0)),
  lastCycle: toDateStr(d.cycleStart(new Date(2026, 9, 23), 1)),
  beforeBillDay: toDateStr(d.cycleStart(new Date(2026, 9, 1), 0)),
  oldDay: d.day(maps, old),
  today: d.day(maps, today),
}}));
""")
    assert out["billDay"] == 2
    assert (out["thisCycle"], out["lastCycle"], out["beforeBillDay"]) == ("2026-10-02", "2026-09-02", "2026-09-02")
    assert out["oldDay"] == {"buy": 2, "sell": 4, "fee": 1.25}          # no odometer that day: the flat fee
    assert out["today"] == {"buy": 3.5, "sell": 1, "fee": 1.25}         # today: the totals' live day figures


def test_studio_state_card_demo() -> None:
    studio = (WWW / "battman-theme-studio.js").read_text()
    assert 'hass.callApi("GET","battman/cards/state")' in studio
    assert "lovelace/config" not in studio[studio.index("function loadChillCard(){"):]
    # the line the studio leaves out is the State card's missing-sensor check, and only that
    content = yaml.safe_load((ROOT / "cards/state.yaml").read_text())["custom_fields"]["content"]
    pattern = r"^const _gone = .*\n^if \(_gone\.length\) return .*\n"
    assert '.replace(/^const _gone = .*\\n^if \\(_gone\\.length\\) return .*\\n/m,"")' in studio
    removed = re.findall(pattern, content, re.M)
    assert len(removed) == 1 and "State: missing" in removed[0]
    assert "const SC = null;" in content


def test_base_card_refuses_options() -> None:
    base = (WWW / "battman-card-base.js").read_text()
    assert '["type", "grid_options", "view_layout", "visibility"]' in base and "has no options (found:" in base


async def test_cards_on_their_views(hass: HomeAssistant, hass_client_no_auth) -> None:
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain="battman", title="Battman", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_client_no_auth()
    for f in ("battman-card-base.js", "battman-cost-data.js", *(f"battman-{c}.js" for c in CARDS)):
        assert (await client.get(f"/battmanfiles/{f}")).status == 200, f
    for page in OLD_PAGES:
        assert (await client.get(f"/battmanfiles/{page}.html")).status == 404, page
    views = {v["path"]: v for v in (await built(hass))["views"]}
    fin = [c["type"] for c in views["finances"]["sections"][0]["cards"]]
    assert fin[:2] == ["custom:battman-cost-chart", "custom:battman-cost-compare"]
    assert views["settings"]["cards"] == [{"type": "custom:battman-settings"}]
    assert [c["type"] for c in views["theme"]["cards"]] == ["custom:battman-theme-studio"]
