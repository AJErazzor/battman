"""The guide's card pictures are taken from the real cards (tools/guide-screenshots/shoot.py), so
they can't drift from what the cards draw.

Drawing them again must give pictures of the size the guide holds. A card that gains a row, a column or
a line changes its picture's size, so this fails until the pictures are retaken and committed
(see CLAUDE.md). The pixels aren't compared: fonts and Chrome versions differ between machines."""

import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
IMAGES = ROOT / "custom_components/battman/www/guide-images"
TOOL = ROOT / "tools/guide-screenshots/shoot.py"
CHROME = os.environ.get("BATTMAN_CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
NODE_PATH = os.environ.get("BATTMAN_NODE_PATH", "/tmp/pwtest/node_modules")


def size(path: Path) -> tuple[int, int]:
    return struct.unpack(">II", path.read_bytes()[16:24])


def shots() -> list[str]:
    return re.findall(r'^    "([a-z0-9-]+)":\s+\{"kind"', TOOL.read_text(), re.M)


def test_every_picture_the_tool_makes_is_in_the_guide() -> None:
    names = shots()
    assert names, "no pictures found in shoot.py"
    pages = "".join(p.read_text(encoding="utf-8") for p in (ROOT / "custom_components/battman/guide").rglob("*.md"))
    for n in names:
        assert (IMAGES / f"{n}.png").exists(), n
        assert f"guide-images/{n}.png" in pages, n


@pytest.mark.skipif(not (Path(CHROME).exists() and Path(NODE_PATH, "playwright").exists() and shutil.which("node")),
                    reason="needs Chrome, Playwright and Node")
def test_pictures_are_the_size_the_cards_draw_now(tmp_path) -> None:
    r = subprocess.run([sys.executable, str(TOOL)], capture_output=True, text=True, timeout=240,
                       env={**os.environ, "BATTMAN_CHROME": CHROME, "BATTMAN_NODE_PATH": NODE_PATH, "BATTMAN_SHOTS_OUT": str(tmp_path)})
    assert r.returncode == 0, r.stdout + r.stderr
    for n in shots():
        assert size(tmp_path / f"{n}.png") == size(IMAGES / f"{n}.png"), (
            f"{n}.png no longer matches what its card draws: retake it with tools/guide-screenshots/shoot.py and commit it")
