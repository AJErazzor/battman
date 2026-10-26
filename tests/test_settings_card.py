"""Settings as one Battman card (custom:battman-settings, www/battman-settings.js): every
setting the old Settings view had is still there, and the page's limits are the ones the
parameters sensor accepts."""

import re
import subprocess
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from .dashboard_views import built

ROOT = Path(__file__).parents[1] / "custom_components/battman"
JS = (ROOT / "www/battman-settings.js").read_text()

# every setting the old Settings view (button-card sections) changed, and how it was sent
PARAMS = ["buyProrateSOCOffset", "buyHighSOCOffset", "sellProrateSOCOffset", "sellLowSOCOffset", "sellSpikePrice1",
          "sellSpikeSOC1", "sellSpikePrice2", "sellSpikeSOC2", "needyTriggerPVGap", "needyTriggerConsumption",
          "watchdogScriptNotRunLimit", "watchdogScriptDisabledLimit", "watchdogResetOverridesAt", "dailyNetworkCharge",
          "billDayOfMonth", "systemCost", "systemInstallDate", "systemIncome", "systemExpenses", "preSystemBillQ1",
          "preSystemBillQ2", "preSystemBillQ3", "preSystemBillQ4", "billInflation", "amberBuyAlertThreshold",
          "alertNotifyTarget", "amberNegativeBuyAlert", "simpleBatteryMode", "alwaysShowOverrideTimer", "dashboardTheme"]
RULE_ITEMS = ["isActive", "allowLastChance", "hours_ahead", "grouping_minutes", "roundTo", "roundtype", "offset"]
TRACKING = ["buy_trackingA_CutOffKwh", "buy_trackingA_CutOffcKwh", "buy_trackingA_Offset",
            "buy_trackingA_AllowLastChance", "buy_trackingA_ResetHour"]
# the Live Activity: its switch and its settings (parameters attributes since v0.26.0)
LIVE_ACTIVITY = ["switch.battman_live_activity", "sensor.battman_parameters", "liveActivityPhone", "liveActivityFollow",
                 "liveActivityFollowOn", "liveActivityFollowOff", "liveActivityFollowDelay", "liveActivitySpikeAlert"]


def test_every_old_setting_is_on_the_page() -> None:
    for k in PARAMS:
        assert re.search(rf"['\"]{k}['\"]", JS), k
    for item in RULE_ITEMS:
        assert f"'{item}'" in JS or f'"{item}"' in JS or f'data-item="{item}"' in JS, item
    for ev in TRACKING:
        assert ev in JS, ev
    for ent in LIVE_ACTIVITY:
        assert ent in JS, ent
    for marker in ("attribute: 'rules'", "attribute: 'state'", "action: 'SetValue', provider", "'tariffBuy' : 'tariffSell'",
                   "action: 'SetDefaults'", "create_live_activity", "data-cascade", "lovelace/config/save"):
        assert marker in JS, marker
    for sec in ("buy", "buyRules", "needy", "watchdog", "billing", "system", "sell", "sellRules", "spike", "protection",
                "provider", "alert", "liveActivity", "dashboard", "defaults"):
        assert re.search(rf"\b{sec}:\s+\{{ title:", JS), sec
    assert "{{" not in JS and "[[map:" not in JS                             # entity names come from the map at run time
    assert "?? " not in JS                                                    # no made-up values for missing settings


def test_limits_match_what_the_parameters_sensor_accepts() -> None:
    yaml_text = (ROOT / "packages/battman_parameters.yaml").read_text()
    table = JS[JS.index("const RANGE"):JS.index("const DEFAULT_KEYS")]
    page = {m[0]: m[1:] for m in re.findall(r"(\w+): \[(\d), (-?[\d.]+), (-?[\d.]+)", table)}
    assert len(page) == 23
    for key, (is_int, lo, hi) in page.items():
        block = yaml_text[yaml_text.index(f"\n          {key}: >"):]
        block = block[:block.index("{% else %}")]
        t = "int" if is_int == "1" else "float"
        assert re.search(rf"data\.{key} \| {t} >=? {re.escape(lo)}(\.0)?\b", block), (key, "min", lo)
        assert re.search(rf"data\.{key} \| {t} <= {re.escape(hi)}(\.0)?\b", block), (key, "max", hi)


def test_card_script_parses() -> None:
    subprocess.run(["node", "--check", str(ROOT / "www/battman-settings.js")], check=True, capture_output=True)


async def test_settings_card_and_view(hass: HomeAssistant, hass_client) -> None:
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain="battman", title="Battman", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_client()
    # a real card now (battman-settings.js, loaded on every HA page), not a page in a frame
    assert (await client.get("/api/battman/cards/settings")).status == 404
    assert (await client.get("/battmanfiles/battman-settings.js")).status == 200
    assert (await client.get("/battmanfiles/settings.html")).status == 404
    views = {v["path"]: v for v in (await built(hass))["views"]}
    assert views["settings"]["type"] == "panel" and views["settings"]["cards"] == [{"type": "custom:battman-settings"}]
