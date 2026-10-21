"""v0.18.4: Battman's elements survive HA's frontend swapping its element registry.

HA's frontend replaces window.customElements with its own registry (a compatibility layer) as
it starts. Battman's start-up scripts load at the same time; anything they registered just
before the swap was lost to HA ("Timeout waiting for strategy element", "Custom element doesn't
exist"). Each script now registers again in the new registry."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

WWW = Path(__file__).parents[1] / "custom_components/battman/www"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
NODE_PATH = "/tmp/pwtest/node_modules"


def test_every_registration_goes_through_the_helper() -> None:
    for name in ("battman-strategy.js", "battman-countdown.js", "battman-cards.js"):
        js = (WWW / name).read_text()
        assert "function battmanDefine(tag, cls)" in js and "window.CustomElementRegistryPolyfill" in js, name
        direct = [l for l in js.splitlines() if "customElements.define(" in l]
        assert direct == [], (name, direct)


@pytest.mark.skipif(not (Path(CHROME).exists() and Path(NODE_PATH, "playwright").exists() and shutil.which("node")),
                    reason="needs Playwright and Chromium")
def test_registered_again_after_the_swap(tmp_path) -> None:
    r = subprocess.run(["node", str(Path(__file__).parent / "js/registry_check.js"), str(WWW), str(tmp_path)],
                       capture_output=True, text=True, timeout=120,
                       env={**os.environ, "NODE_PATH": NODE_PATH, "CHROME": CHROME})
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert out["missing"] == []
    assert out["sameClass"] == "BattmanImageCard"
