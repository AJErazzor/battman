"""Finances as Battman cards (cost chart, cost compare, Billing, Solar System), the Correct
totals popup's SetTotal action on the totals sensors, and Battman's one list of mode colours."""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from . import engine_harness as H
from .dashboard_views import built

ROOT = Path(__file__).parents[1] / "custom_components/battman"
LIB = ROOT / "www/battman-lib.js"


def js(expr: str):
    script = ("globalThis.window = globalThis; globalThis.document = {querySelector: () => null};\n"
              + LIB.read_text() + f"\nprocess.stdout.write(JSON.stringify({expr}));")
    return json.loads(subprocess.run(["node", "-"], input=script, capture_output=True, text=True, check=True).stdout)


async def _totals(hass):
    b, s = hass.states.get("sensor.battman_buy_total"), hass.states.get("sensor.battman_sell_total")
    return b, s


async def _start_totals(hass):
    """Battman in charge, the totals running (they start on a price-interval change)."""
    from custom_components.battman.const import IN_CHARGE

    entry, _rec = await H.start(hass, smiggles=False)
    hass.config_entries.async_update_entry(entry, data={**entry.data, IN_CHARGE: True})
    await hass.async_block_till_done()
    H.set_world(hass, {"estimate": False})
    await hass.async_block_till_done()
    H.set_world(hass, {"estimate": True})        # estimated price off -> on: the totals' interval tick
    await hass.async_block_till_done()
    hass.bus.async_fire("battman_totals_update", {})   # and a plain totals update (what Billing's buttons send)
    await hass.async_block_till_done()
    return entry


async def test_set_total_corrects_each_period(hass: HomeAssistant) -> None:
    await _start_totals(hass)
    b, s = await _totals(hass)
    assert b.state not in ("unknown", "unavailable") and s.state not in ("unknown", "unavailable"), (b, s)
    before_b, before_s = dict(b.attributes), dict(s.attributes)

    for period, buy, sell in (("day", 1.5, 3.25), ("yesterday", 2, 4), ("month", 30.1234, 60.5), ("bill", 42.12345, 88)):
        hass.bus.async_fire("battman_totals_update", {"attribute": "SetTotal", "period": period, "buy": buy, "sell": sell})
        await hass.async_block_till_done()
        b, s = await _totals(hass)
        assert b.attributes[period] == round(buy, 4) and s.attributes[period] == round(sell, 4), (period, b, s)

    # only the named period changes; the odometer itself (state) and the markers stay
    hass.bus.async_fire("battman_totals_update", {"attribute": "SetTotal", "period": "day", "buy": 9, "sell": 9})
    await hass.async_block_till_done()
    b, s = await _totals(hass)
    assert (b.attributes["month"], s.attributes["bill"]) == (30.1234, 88)
    assert b.attributes["day_marker"] == before_b["day_marker"] and s.attributes["bill_marker"] == before_s["bill_marker"]

    # not a number: ignored, nothing changes
    hass.bus.async_fire("battman_totals_update", {"attribute": "SetTotal", "period": "month", "buy": "oops", "sell": 1})
    await hass.async_block_till_done()
    b, s = await _totals(hass)
    assert b.attributes["month"] == 30.1234 and s.attributes["month"] == 60.5

    # recorded by the sensors themselves (what HA saves and restores), not just shown
    comp = hass.data["entity_components"]["sensor"]
    ent = next(e for e in comp.entities if e.entity_id == "sensor.battman_buy_total")
    assert ent.extra_state_attributes["day"] == 9


async def test_set_total_ignored_when_not_in_charge(hass: HomeAssistant) -> None:
    from custom_components.battman.const import IN_CHARGE

    entry = await _start_totals(hass)
    b, _ = await _totals(hass)
    hass.config_entries.async_update_entry(entry, data={**entry.data, IN_CHARGE: False})
    await hass.async_block_till_done()
    hass.bus.async_fire("battman_totals_update", {"attribute": "SetTotal", "period": "day", "buy": 77, "sell": 77})
    await hass.async_block_till_done()
    assert (await _totals(hass))[0].attributes["day"] == b.attributes["day"]


@pytest.mark.skipif(not shutil.which("node"), reason="needs Node")
def test_correct_totals_popup_sends_set_total() -> None:
    assert js("window.BattmanLib.setTotalEvent('bill', '42.123456', ' 7 ')") == \
        {"attribute": "SetTotal", "period": "bill", "buy": 42.1235, "sell": 7}
    for bad in (("", "1"), ("1", "x"), ("abc", "2")):
        assert js(f"window.BattmanLib.setTotalEvent('day', {json.dumps(bad[0])}, {json.dumps(bad[1])})") is None
    assert js("window.BattmanLib.TOTAL_PERIODS.map(p => p[0])") == ["day", "yesterday", "month", "bill"]


async def _setup(hass):
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain="battman", title="Battman", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_finances_is_battman_cards(hass: HomeAssistant, hass_client) -> None:
    await _setup(hass)
    client = await hass_client()
    data = await built(hass)
    assert data["errors"] == []
    assert [v["path"] for v in data["views"]] == ["power", "curvy", "pricy", "finances", "settings", "log", "theme"]
    fin = next(v for v in data["views"] if v["path"] == "finances")
    assert [c["type"] for c in fin["sections"][0]["cards"]] == [
        "custom:battman-cost-chart", "custom:battman-cost-compare", "custom:battman-billing", "custom:battman-solar-system"]
    assert fin["header"]["card"] == {"type": "custom:battman-image", "image": "finances-header.webp",
                                     "background": "none", "frame": False, "height": 48}
    for cid in ("billing", "solar-system"):
        card = await (await client.get(f"/api/battman/cards/{cid}")).json()
        assert card["missing_map"] == [] and card["needs"] == ["button-card"], cid
        assert "{{" not in json.dumps(card["config"]), cid
    # the cost cards draw themselves (battman-cost-*.js), no page in a frame and no card-mod
    for cid in ("cost-chart", "cost-compare"):
        assert (await client.get(f"/api/battman/cards/{cid}")).status == 404, cid
        assert (await client.get(f"/battmanfiles/battman-{cid}.js")).status == 200, cid
        assert (await client.get(f"/battmanfiles/{cid}.html")).status == 404, cid
        assert (await client.get(f"/battmanfiles/previews/{cid}.webp")).status == 200, cid
    for img in ("finances-header.webp",):
        assert (await client.get(f"/battmanfiles/images/{img}")).status == 200
    billing = await (await client.get("/api/battman/cards/billing")).json()
    row9 = billing["config"]["custom_fields"]["row9"]
    assert "window.BattmanLib.correctTotals(this,{buy:'sensor." in row9 and "correct-totals" not in row9
    # gone: the hidden view, its page, html-card
    assert (await client.get("/battmanfiles/correct-energy.html")).status == 404
    assert not list((ROOT / "views").glob("*history*")) and not list((ROOT / "views").glob("*correct*"))
    text = "".join(f.read_text() for f in ROOT.rglob("*") if f.is_file() and f.suffix in (".yaml", ".py", ".js", ".html"))
    assert "html-card" not in text and "correct-energy" not in text and "correct-totals" not in text


def test_one_list_of_mode_colours() -> None:
    hue = js("window.BattmanLib.MODE_HUE")
    assert hue == {"Self Consume": "blue", "Charge": "yellow", "Discharge": "green", "Float": "orange", "Drain": "red",
                   "Charge Solar Off": "purple", "Float Solar Off": "teal", "Solar Soak": "amber"}
    # the Power view's Battery mode buttons: the five everyday modes are the source
    card = (ROOT / "cards/batterymode.yaml").read_text()
    for mode in ("Self Consume", "Charge", "Discharge", "Float", "Drain"):
        block = card[card.index(f"option: {mode}\n"):]
        colour = re.search(r"battman-([a-z]+)-border-strong", block).group(1)
        assert colour == hue[mode], (mode, colour)
    # the Live Activity's default is the same list
    bp = yaml.load((ROOT / "blueprints/script/battman_live_activity_push.yaml").read_text(), Loader=_BlueprintLoader)
    assert bp["blueprint"]["input"]["look"]["input"]["mode_hues"]["default"] == hue
    # the colours sensor covers every colour the list uses, and every shipped theme has them
    from custom_components.battman.sensor import MODE_HUES

    assert set(hue.values()) <= set(MODE_HUES)
    for f in (ROOT / "themes").glob("*.yaml"):
        theme = next(iter(yaml.safe_load(f.read_text()).values()))
        for h in MODE_HUES:
            assert f"battman-{h}" in theme, (f.name, h)
    # the Log card takes its colours from the list (no colours of its own)
    log = (ROOT / "www/battman-log.js").read_text()
    assert "BattmanLib.MODE_HUE" in log and "'Self Consume':    '--battman-blue'" not in log


class _BlueprintLoader(yaml.SafeLoader):
    pass


_BlueprintLoader.add_constructor("!input", lambda loader, node: loader.construct_scalar(node))
