"""The Battman House card (custom:battman-house, www/battman-house.js): loaded on every HA page,
its pictures ship with Battman, its map defaults are real map entries, and it's the first card
on the Power view. Also: Curvy copies the sensor's curves when it loads them (else its "Saved"
check compares your edit with itself)."""

import re
import subprocess
from pathlib import Path

import yaml

from custom_components.battman.const import ENTITY_MAP_DEFAULTS

ROOT = Path(__file__).parents[1] / "custom_components/battman"
JS = (ROOT / "www/battman-house.js").read_text()


def test_loaded_and_valid() -> None:
    assert 'add_extra_js_url(hass, f"{STATIC_URL}/battman-house.js' in (ROOT / "__init__.py").read_text()
    assert subprocess.run(["node", "--check", str(ROOT / "www/battman-house.js")]).returncode == 0
    assert 'battmanDefine("battman-house", BattmanHouseCard)' in JS
    assert 'battmanDefine("battman-house-editor", BattmanHouseEditor)' in JS


def test_pictures_ship_with_battman() -> None:
    pics = re.findall(r'image: "/battmanfiles/images/([\w-]+\.webp)"', JS)
    assert sorted(pics) == ["house-battery.webp", "house-gateway.webp", "house.webp"]
    for p in pics:
        assert (ROOT / "www/images" / p).stat().st_size > 1000
    assert not re.search(r'image: "/local/', JS)               # no one's own files as defaults


def test_map_defaults_exist() -> None:
    keys = set(re.findall(r'\w+: "map:(\w+)"', JS))
    assert keys and keys <= set(ENTITY_MAP_DEFAULTS), keys - set(ENTITY_MAP_DEFAULTS)


def test_every_item_can_be_turned_off_and_devices_have_text_and_suffix() -> None:
    items = re.findall(r'\{ key: "(\w+)", title: "[^"]+",([^\n]*)\}', JS)
    assert len(items) == 23
    devices = {k: rest for k, rest in items if k.startswith("pc")}
    assert set(devices) == {"pc1", "pc2", "pc3"}
    for rest in devices.values():
        assert "label:" in rest and "suffix:" in rest and "entity:" in rest
    assert 'const out = { show: true };' in JS                  # every item has a show toggle


def test_first_on_the_power_view() -> None:
    power = yaml.safe_load((ROOT / "views/05-power.yaml").read_text())
    assert power["sections"][0]["cards"][:2] == [{"type": "custom:battman-house"}, {"type": "custom:battman-batterymode"}]


def test_curvy_copies_the_curves_it_loads() -> None:
    page = (ROOT / "www/battman-curvy.js").read_text()
    assert "data[month] = { sell: [...c.sell], sell_high: [...c.sell_high], buy: [...c.buy], buy_high: [...c.buy_high] };" in page
    assert "data[month] = { sell: c.sell," not in page
