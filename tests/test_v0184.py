"""v0.18.4: Battman's elements survive HA's frontend swapping its element registry.

HA's frontend replaces window.customElements with its own registry (a compatibility layer) as
it starts. Battman's start-up scripts load at the same time; anything they registered just
before the swap was lost to HA ("Custom element doesn't exist"). Each script now registers again in the new registry."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

WWW = Path(__file__).parents[1] / "custom_components/battman/www"
CHROME = os.environ.get("BATTMAN_CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
NODE_PATH = os.environ.get("BATTMAN_NODE_PATH", "/tmp/pwtest/node_modules")


def test_every_registration_goes_through_the_helper() -> None:
    # one helper (battman-card-base.js), which knows how to register again after HA swaps its registry...
    base = (WWW / "battman-card-base.js").read_text()
    assert "export function battmanDefine(tag, cls)" in base and "window.CustomElementRegistryPolyfill" in base
    # ...and no other Battman script registers an element or carries its own copy of the helper
    for f in sorted(WWW.glob("battman*.js")):
        if f.name == "battman-card-base.js":
            continue
        js = f.read_text()
        assert "function battmanDefine(" not in js, f.name
        direct = [l for l in js.splitlines() if "customElements.define(" in l]
        assert direct == [], (f.name, direct)


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


@pytest.mark.skipif(not (Path(CHROME).exists() and Path(NODE_PATH, "playwright").exists() and shutil.which("node")),
                    reason="needs Playwright and Chromium")
def test_the_one_script_starts_the_rest_and_survives_a_broken_one(tmp_path) -> None:
    """battman.js starts every Battman script; one that won't load is reported and the others still work."""
    def run(www):
        r = subprocess.run(["node", str(Path(__file__).parent / "js/loader_check.js"), str(www)], capture_output=True, text=True,
                           timeout=120, check=True, env={**os.environ, "NODE_PATH": NODE_PATH, "CHROME": CHROME})
        return json.loads(r.stdout.strip().splitlines()[-1])

    everything = {"battman-countdown", "battman-house", "battman-log", "battman-settings", "battman-curvy", "battman-pricy",
                  "battman-forecast-view", "battman-pie-card", "battman-state"}
    ok = run(WWW)
    assert set(ok["defined"]) == everything and ok["lib"] and ok["enginelog"] and ok["errors"] == []
    broken = tmp_path / "www"
    shutil.copytree(WWW, broken, ignore=shutil.ignore_patterns("images", "previews", "vendor"))
    (broken / "battman-curvy.js").write_text("this is not javascript (\n")
    bad = run(broken)
    assert set(bad["defined"]) == everything - {"battman-curvy"} and bad["lib"]       # everything else carried on
    assert any("battman-curvy.js" in e and "didn't load" in e for e in bad["errors"]), bad["errors"]
