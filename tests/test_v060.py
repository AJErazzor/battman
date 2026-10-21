import pytest
"""v0.6.0: Log and Theme views, Save to HA, custom themes, Configure screen, restart prompt."""

import json
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("smiggles_installed")

DOMAIN = "battman"

GOOD = """Battman Mine:
  battman-accent: "#ff8800"
  primary-color: "#ff8800"
"""


async def _setup(hass, options=None):
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain=DOMAIN, title="Battman", data={}, options=options or {})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_log_and_theme_views(hass: HomeAssistant, hass_client) -> None:
    await _setup(hass)
    data = await (await (await hass_client()).get("/api/battman/dashboard")).json()
    assert data["errors"] == []
    by_path = {v["path"]: v for v in data["views"]}
    log, theme = by_path["log"], by_path["theme"]
    assert log["cards"][0]["url"] == "/battman/log.html"
    assert theme["cards"][0]["url"].startswith("/battman/theme-studio.html")
    text = json.dumps(data["views"][1:])
    assert "/battman/log.html" in text and "/battman/theme-studio.html" in text
    assert "smiggles" not in text.lower() and "{{" not in text


async def test_save_theme(hass: HomeAssistant, hass_client, hass_admin_user) -> None:
    await _setup(hass)
    client = await hass_client()
    custom = Path(hass.config.path("themes", "battman", "custom"))

    r = await client.post("/api/battman/themes", json={"name": "Battman Mine", "yaml": GOOD})
    assert r.status == 200, await r.text()
    assert (custom / "Battman Mine.yaml").read_text() == GOOD

    r = await client.post("/api/battman/themes", json={"name": "Battman Mine", "yaml": GOOD})
    assert r.status == 409 and (await r.json())["exists"] is True
    r = await client.post("/api/battman/themes",
                          json={"name": "Battman Mine", "yaml": GOOD.replace("ff8800", "00ff00"), "overwrite": True})
    assert r.status == 200 and "00ff00" in (custom / "Battman Mine.yaml").read_text()

    r = await client.post("/api/battman/themes",
                          json={"name": "Battman Coffee", "yaml": GOOD.replace("Mine", "Coffee")})
    assert r.status == 409 and (await r.json())["exists"] is False      # shipped name
    for bad in ({"name": "Mine", "yaml": GOOD},                           # no Battman prefix
                {"name": "Battman Mine", "yaml": "Battman Mine: [oops"},   # not YAML
                {"name": "Battman Other", "yaml": GOOD},                   # name mismatch
                {"name": "Battman Mine", "yaml": "Battman Mine:\n  primary-color: red\n"}):  # no battman-*
        r = await client.post("/api/battman/themes", json=bad)
        assert r.status == 400, bad

    hass_admin_user.groups = []                                           # now not an admin
    r = await client.post("/api/battman/themes", json={"name": "Battman Two", "yaml": GOOD})
    assert r.status == 403


async def test_custom_themes_survive_update_and_removal(hass: HomeAssistant) -> None:
    root = Path(hass.config.path("themes", "battman"))
    (root / "custom").mkdir(parents=True)
    (root / "custom" / "Battman Mine.yaml").write_text(GOOD)
    (root / "Old Shipped.yaml").write_text("Old: {}\n")
    entry = await _setup(hass)
    assert not (root / "Old Shipped.yaml").exists()                      # stale shipped file cleaned
    assert len(list(root.glob("*.yaml"))) == 20                         # shipped themes in place
    assert (root / "custom" / "Battman Mine.yaml").exists()
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert not list(root.glob("*.yaml"))                                  # shipped themes gone
    assert (root / "custom" / "Battman Mine.yaml").read_text() == GOOD     # yours kept


async def test_configure_screen(hass: HomeAssistant, hass_client) -> None:
    entry = await _setup(hass)
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    assert flow["type"] is FlowResultType.FORM
    defaults = {k.schema: k.default() for k in flow["data_schema"].schema}
    assert defaults["buy_price"] == "sensor.amber_5min_current_general_price"
    assert "buy_total" not in defaults          # engine entries follow the engine in charge, not Configure

    bad = await hass.config_entries.options.async_configure(
        flow["flow_id"], {**defaults, "pv_string": "sensor.pv_power"})
    assert bad["errors"] == {"pv_string": "pv_pattern"}
    done = await hass.config_entries.options.async_configure(
        bad["flow_id"], {**defaults, "buy_price": "sensor.my_buy", "pv_string": "sensor.inv_pv{n}"})
    assert done["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {"buy_price": "sensor.my_buy", "pv_string": "sensor.inv_pv{n}"}  # only changes
    await hass.async_block_till_done()

    client = await hass_client()
    emap = (await (await client.get("/api/battman/entities")).json())["entities"]
    assert emap["buy_price"] == "sensor.my_buy" and emap["sell_total"] == "sensor.solarsystemcontrolselltotal"
    dash = json.dumps(await (await client.get("/api/battman/dashboard")).json())
    assert "sensor.my_buy" in dash and "sensor.amber_5min_current_general_price" not in dash


async def test_restart_prompt(hass: HomeAssistant) -> None:
    await _setup(hass)
    from custom_components.battman import update_check

    issues = ir.async_get(hass)
    disk = update_check._disk_version()
    assert not await update_check.async_check_once(hass, disk)            # same version: quiet
    assert issues.async_get_issue(DOMAIN, "restart_required") is None
    assert await update_check.async_check_once(hass, "0.0.1")              # files newer than running code
    issue = issues.async_get_issue(DOMAIN, "restart_required")
    assert issue.is_fixable and issue.translation_placeholders == {"running": "0.0.1", "new": disk}


async def test_restart_fix_flow(hass: HomeAssistant, hass_client) -> None:
    await _setup(hass)
    assert await async_setup_component(hass, "repairs", {})
    from custom_components.battman import update_check

    await update_check.async_check_once(hass, "0.0.1")
    client = await hass_client()
    r = await client.post("/api/repairs/issues/fix", json={"handler": DOMAIN, "issue_id": "restart_required"})
    flow = await r.json()
    assert flow["step_id"] == "confirm"
    assert flow["description_placeholders"]["running"] == "0.0.1"     # dialog shows real versions

    calls = []
    hass.services.async_register("homeassistant", "restart", lambda call: calls.append(call))
    r = await client.post(f"/api/repairs/issues/fix/{flow['flow_id']}", json={})
    assert (await r.json())["type"] == "create_entry"
    await hass.async_block_till_done()
    assert len(calls) == 1                                             # HA restart requested


async def test_correct_totals_subview(hass: HomeAssistant, hass_client) -> None:
    await _setup(hass)
    data = await (await (await hass_client()).get("/api/battman/dashboard")).json()
    by_path = {v["path"]: v for v in data["views"]}
    fin, sub = by_path["finances"], by_path["correct-totals"]
    assert sub["path"] == "correct-totals" and sub["subview"] is True       # hidden: no tab
    assert sub["cards"][0]["url"] == "/battman/correct-energy.html"
    billing = fin["sections"][0]["cards"][2]
    assert "/correct-totals" in billing["custom_fields"]["row9"] and "Correct Totals" in billing["custom_fields"]["row9"]
    assert "row9" in billing["styles"]["grid"][0]["grid-template-areas"]


async def test_curvy_and_pricy(hass: HomeAssistant, hass_client) -> None:
    await _setup(hass)
    client = await hass_client()
    by_path = {v["path"]: v for v in (await (await client.get("/api/battman/dashboard")).json())["views"]}
    assert by_path["curvy"]["cards"][0]["url"] == "/battman/curvy.html" and by_path["curvy"]["theme"] == "Battman Nord"
    assert by_path["pricy"]["cards"][0]["url"] == "/battman/pricy.html" and by_path["pricy"]["title"] == "Pricy"
    emap = (await (await client.get("/api/battman/entities")).json())["entities"]
    assert emap["sigen_pv_power"] == "sensor.sigen_plant_sigen_pv_power"      # Sigen-only, separate from pv_power
    assert emap["pv_power"] == "sensor.sigen_plant_pv_power"
    assert emap["soc_curves_update_event"] == "solar_system_control_soc_curves_update"
