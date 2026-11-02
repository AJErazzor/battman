"""v0.12.0: the Profit / Loss card, and the Power view laid out like the Smiggles one."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from .snapshots import assert_snapshot


DOMAIN = "battman"
SELL, BUY, PAR = ("sensor.battman_sell_total", "sensor.battman_buy_total",
                  "sensor.battman_parameters")


async def _card(hass, hass_client):
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain=DOMAIN, title="Battman", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_client()
    cards = (await (await client.get("/api/battman/cards")).json())["cards"]
    assert {"id": "profitloss", "name": "Profit / Loss", "source": "battman",
            "description": "Today's sell and buy totals, gross, and net after the daily network charge."} in cards
    return await (await client.get("/api/battman/cards/profitloss")).json()


def _js(src: str, states: dict) -> str:
    """Run one button-card [[[ ]]] template the way button-card does, with these states."""
    body = src.strip()
    assert body.startswith("[[[") and body.endswith("]]]")
    prog = ("const states = " + json.dumps(states) + ";\n"
            "process.stdout.write(String((function(){" + body[3:-3] + "})()));")
    return subprocess.run(["node", "-e", prog], capture_output=True, text=True, check=True).stdout


def _st(day=None, **attrs):
    a = dict(attrs)
    if day is not None:
        a["day"] = day
    return {"state": "on", "attributes": a}


async def test_profitloss_card(hass: HomeAssistant, hass_client) -> None:
    card = await _card(hass, hass_client)
    assert card["missing_map"] == [] and card["needs"] == ["button-card"]
    text = yaml.safe_dump(card["config"])
    assert "[[map:" not in text
    for old in ("smiggles", "ssc-", "input_number.solarsystemcontrol"):
        assert old not in text.lower()
    for e in (SELL, BUY, PAR):
        assert e in text
    raw = (Path(__file__).parents[1] / "custom_components/battman/cards/profitloss.yaml").read_text().lower()
    assert "smiggles" not in raw and "solarsystemcontrol" not in raw and "ssc" not in raw


async def test_profitloss_layout(hass: HomeAssistant, hass_client) -> None:
    """The card's structure, styles and trigger sensors (snapshot)."""
    m = (await _card(hass, hass_client))["config"]

    def strip(x):   # drop the JS templates; keep structure/styles
        if isinstance(x, dict):
            return {k: strip(v) for k, v in x.items() if k not in ("triggers_update",)}
        if isinstance(x, list):
            return [strip(v) for v in x]
        if isinstance(x, str):
            return "JS" if x.strip().startswith("[[[") else x
        return x

    bm = m["cards"][0]["cards"][0]
    assert_snapshot(__file__, "profitloss-layout", strip(m))
    assert_snapshot(__file__, "profitloss-triggers_update", bm["triggers_update"])


@pytest.mark.skipif(not shutil.which("node"), reason="needs node to run the card's JavaScript")
async def test_profitloss_draws(hass: HomeAssistant, hass_client) -> None:
    """With real values it draws correctly; missing values show — or an error (snapshot)."""
    m = (await _card(hass, hass_client))["config"]["cards"][0]["cards"][0]
    js_m = m["custom_fields"]["card"]
    bord_m = m["styles"]["card"][-1]["border"]

    for sell, buy, fee in ((12.34, 3.21, 1.10), (0.5, 4.75, 1.10), (2.0, 1.0, 1.0)):
        states = {SELL: _st(sell), BUY: _st(buy), PAR: _st(dailyNetworkCharge=fee)}
        assert_snapshot(__file__, f"profitloss-draw-{sell}-{buy}-{fee}",
                        {"card": _js(js_m, states), "border": _js(bord_m, states)})

    # Unavailable (no 'day' yet): —, never $0.00; border goes neutral.
    states = {SELL: _st(), BUY: _st(2.0), PAR: _st(dailyNetworkCharge=1.1)}
    out = _js(js_m, states)
    assert "$0.00" not in out and out.count("—") == 3            # SELL, GROSS, NET
    assert "-$2.00" not in out and "$2.00" in out                 # BUY still shown
    assert "border-neutral-soft" in _js(bord_m, states)
    states = {SELL: _st(5.0), BUY: _st(2.0), PAR: _st()}          # no network charge
    out = _js(js_m, states)
    assert "$3.00" in out and out.count("—") == 1                  # GROSS shown, NET —

    # A sensor that doesn't exist: an error naming it.
    out = _js(js_m, {SELL: _st(1.0), PAR: _st(dailyNetworkCharge=1.0)})
    assert "missing " + BUY in out and "$" not in out
