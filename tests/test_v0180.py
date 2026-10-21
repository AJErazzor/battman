"""v0.18.0: the Battman Image card (custom:battman-image): Battman's images and yours, listed
and served by Battman, drawn with fit / position / height options and dark / narrow overrides."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

ROOT = Path(__file__).parents[1]
WWW = ROOT / "custom_components/battman/www"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
NODE_PATH = "/tmp/pwtest/node_modules"


async def _client(hass: HomeAssistant, hass_client):
    await async_setup_component(hass, "http", {})
    entry = MockConfigEntry(domain="battman", title="Battman")
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, "battman", {})
    await hass.async_block_till_done()
    return await hass_client()


def test_main_image_shipped() -> None:
    f = WWW / "images/battman-main.webp"
    assert f.read_bytes()[8:12] == b"WEBP" and f.stat().st_size < 200_000


async def test_list_and_serve(hass: HomeAssistant, hass_client, hass_client_no_auth) -> None:
    client = await _client(hass, hass_client)
    res = await (await client.get("/api/battman/images")).json()
    names = {i["name"]: i for i in res["images"]}
    assert res["folder"] == "battman/images"
    assert names["battman-main.webp"] == {"name": "battman-main.webp", "source": "battman",
                                          "url": "/api/battman/image/battman-main.webp"}
    assert set(names) == {f.name for f in (WWW / "images").iterdir()}

    # yours: a new one, and one that replaces Battman's (same name); a non-image file is left out
    local = Path(hass.config.path("battman/images"))
    local.mkdir(parents=True)
    (local / "my-house.png").write_bytes(b"\x89PNG mine")
    (local / "battman-wrench.webp").write_bytes(b"RIFF mine")
    (local / "notes.txt").write_text("not an image")
    (local / "evil.svg").write_text("<svg onload='x'/>")
    res = await (await client.get("/api/battman/images")).json()
    names = {i["name"]: i["source"] for i in res["images"]}
    assert names["my-house.png"] == "yours" and names["battman-wrench.webp"] == "yours, replaces Battman's"
    assert "notes.txt" not in names and "evil.svg" not in names

    # served without a login (an <img> can't send one), yours first
    anon = await hass_client_no_auth()
    r = await anon.get("/api/battman/image/my-house.png")
    assert r.status == 200 and r.headers["Content-Type"] == "image/png" and await r.read() == b"\x89PNG mine"
    assert await (await anon.get("/api/battman/image/battman-wrench.webp")).read() == b"RIFF mine"
    r = await anon.get("/api/battman/image/battman-main.webp")
    assert r.status == 200 and r.headers["Content-Type"] == "image/webp"
    # the list itself needs a login
    assert (await anon.get("/api/battman/images")).status == 401
    # nothing outside the two folders, no other file types
    for bad in ("gone.webp", "evil.svg", "notes.txt", "..%2Fconfiguration.yaml", "..%2F..%2Fmanifest.json",
                ".hidden.png"):
        r = await anon.get(f"/api/battman/image/{bad}")
        assert r.status in (400, 404), bad          # 400: HA's own filter refuses ../ before Battman sees it
    (Path(hass.config.config_dir) / "secret.png").write_bytes(b"x")
    assert (await anon.get("/api/battman/image/..%2Fsecret.png")).status in (400, 404)


def test_card_registered_and_documented() -> None:
    js = (WWW / "battman-cards.js").read_text()
    assert 'customElements.define("battman-image", BattmanImageCard)' in js
    assert 'type: "battman-image", name: "Battman Image"' in js
    assert '"(max-width: 767px)"' in js                          # the same line as HA's Mobile visibility
    docs = (ROOT / "docs/cards.md").read_text()
    assert "## Battman Image" in docs and "config/battman/images/" in docs


@pytest.mark.skipif(not (Path(CHROME).exists() and Path(NODE_PATH, "playwright").exists() and shutil.which("node")),
                    reason="needs Playwright and Chromium")
def test_image_card_in_a_browser(tmp_path) -> None:
    r = subprocess.run(["node", str(Path(__file__).parent / "js/image_check.js"), str(WWW / "battman-cards.js"),
                        str(WWW / "images"), str(tmp_path)], capture_output=True, text=True, timeout=120,
                       env={**os.environ, "NODE_PATH": NODE_PATH, "CHROME": CHROME})
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert out["stub"] == {"image": "battman-main.webp"} and out["picker"] == 1
    a = out["auto"]                                                  # auto: the image's own shape
    assert a["loaded"] and a["w"] == 600 and abs(a["h"] - round(600 * 768 / 1407)) <= 1 and a["fit"] == "contain"
    assert out["grid"][0]["rows"] == "auto" and out["grid"][1]["rows"] == 4
    f = out["fill"]                                                  # fill: the space given, less padding
    assert f["loaded"] and (f["w"], f["h"]) == (580, 280) and f["fit"] == "cover" and f["pos"] == "50% 100%"
    assert "height: fill needs a sections view" in out["fillFlat"]["problem"]   # no silent fallback
    p = out["fixedPx"]
    assert p["h"] == 150 and p["flip"].startswith("matrix(-1") and p["shadow"] == "none" and p["alt"] == "Battman"
    assert p["bg"] == "rgba(0, 0, 0, 0)" and out["colour"]["bg"] == "rgb(255, 0, 0)"
    assert "needs background_color" in out["colourMissing"]["problem"]
    assert "no image called “gone.webp”" in out["missing"]["problem"]
    assert "Couldn't load the image “my-house.png” (yours)" in out["notLoading"]["problem"]
    assert out["bad"] == ["Battman Image: Unknown setting: fitt.",
                          "Battman Image: fit is “zoom”: use contain, cover, stretch, actual, shrink.",
                          "Battman Image: height is “tall”: use auto, fill, or a number of px (20 to 2000).",
                          "Battman Image: Unknown setting (in narrow): height."]
    assert out["noImage"] == "Battman Image: pick an image (image:)."
    # dark mode, then a narrow screen (narrow wins), then wide again (dark still applies)
    assert out["wideLight"] == "contain" and out["wideDark"] == ["cover", "50% 0%"]
    assert out["narrowDark"] == ["fill", "50% 0%"] and out["backWide"] == "cover"
    e = out["editor"]
    assert "my-house.png (yours)" in e["opts"] and "battman-main.webp" in e["opts"]
    assert e["changed"] == {"type": "custom:battman-image", "grid_options": {"rows": 5}, "image": "battman-main.webp",
                            "fit": "cover", "height": "fill", "narrow": {"fit": "contain", "flip": True}}
    assert e["fixed"]["height"] == 240 and e["fixed"]["frame"] is False and e["fixed"]["fit"] == "cover"
    assert e["preview"] == "/api/battman/image/battman-main.webp"
    assert out["editorMissing"] == ["There's no image called “gone.webp”. Pick another.", "gone.webp (not found)"]
