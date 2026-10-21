"""Images for the Battman Image card (custom:battman-image).

custom_components/battman/www/images/   Battman's, updated by releases
<config>/battman/images/                yours: Battman never touches this folder. A file
                                        with the same name as one of Battman's is used
                                        instead of it (the card's list says so).

The card lists them through /api/battman/images and draws one from
/api/battman/image/<name>. Only plain image files directly in those two folders are
served (no sub-folders, no other paths).
"""

from __future__ import annotations

import re
from pathlib import Path

from homeassistant.core import HomeAssistant

SHIPPED = Path(__file__).parent / "www" / "images"
LOCAL_PARTS = ("battman", "images")
# a file name only: no folders, no leading dot. SVG is left out on purpose (it can carry script).
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._()-]{0,100}\.(png|jpe?g|webp|gif)$", re.IGNORECASE)
TYPES = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp", "gif": "image/gif"}

SOURCE_BATTMAN = "battman"
SOURCE_YOURS = "yours"
SOURCE_REPLACES = "yours, replaces Battman's"


def local_dir(hass: HomeAssistant) -> Path:
    return Path(hass.config.path(*LOCAL_PARTS))


def _files(local: Path) -> dict[str, tuple[Path, str]]:
    """name -> (file, source). Yours win over Battman's."""
    out: dict[str, tuple[Path, str]] = {}
    for f in sorted(SHIPPED.iterdir()):
        if f.is_file() and NAME_RE.match(f.name):
            out[f.name] = (f, SOURCE_BATTMAN)
    if local.is_dir():
        for f in sorted(local.iterdir()):
            if f.is_file() and NAME_RE.match(f.name):
                out[f.name] = (f, SOURCE_REPLACES if f.name in out else SOURCE_YOURS)
    return out


def list_images(local: Path) -> list[dict[str, str]]:
    return [
        {"name": name, "source": source, "url": f"/api/battman/image/{name}"}
        for name, (_path, source) in _files(local).items()
    ]


def find(local: Path, name: str) -> Path | None:
    """The file for an image name, or None (not a valid name, or no such image)."""
    if not NAME_RE.match(name or ""):
        return None
    hit = _files(local).get(name)
    return hit[0] if hit else None


def content_type(path: Path) -> str:
    return TYPES[path.suffix.lower().lstrip(".")]
