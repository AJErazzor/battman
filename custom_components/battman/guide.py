"""Battman's built-in guide: the Markdown pages in guide/, read by the Help view's card.

guide/index.yaml lists the pages, in order, grouped into tracks (Getting started, Troubleshooting and
so on). A page's id is "<track>/<slug>" and its file is guide/<track>/<slug>.md; the home page is
guide/README.md, which is also what GitHub shows for the folder. Only pages listed in the index are
served, so a request can never reach any other file.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

GUIDE_DIR = Path(__file__).parent / "guide"
HOME = "home"
_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class GuideError(Exception):
    """A page that isn't in the guide (404)."""


def load_index(base: Path = GUIDE_DIR) -> dict[str, Any]:
    """The guide's contents: {"home": {title, summary}, "tracks": [{id, title, summary, pages: [...]}]}."""
    raw = yaml.safe_load((base / "index.yaml").read_text(encoding="utf-8")) or {}
    tracks = []
    for t in raw.get("tracks") or []:
        pages = [
            {"id": f"{t['id']}/{p['slug']}", "title": p["title"], "summary": p.get("summary", "")}
            for p in t.get("pages") or []
        ]
        tracks.append({"id": t["id"], "title": t["title"], "summary": t.get("summary", ""), "pages": pages})
    home = raw.get("home") or {}
    return {"home": {"id": HOME, "title": home.get("title", ""), "summary": home.get("summary", "")}, "tracks": tracks}


def page_ids(index: dict[str, Any]) -> list[str]:
    """Every page id, home first, in contents order."""
    return [HOME] + [p["id"] for t in index["tracks"] for p in t["pages"]]


def page_file(page_id: str, base: Path = GUIDE_DIR) -> Path:
    """The Markdown file for a page id (not checked against the index)."""
    if page_id == HOME:
        return base / "README.md"
    track, slug = page_id.split("/", 1)
    return base / track / f"{slug}.md"


def read_page(page_id: str, base: Path = GUIDE_DIR) -> str:
    """A page's Markdown. Raises GuideError for anything that isn't a page in the index."""
    parts = page_id.split("/")
    if not (page_id == HOME or (len(parts) == 2 and all(_ID.match(p) for p in parts))):
        raise GuideError(f"There's no guide page called {page_id!r}.")
    if page_id not in page_ids(load_index(base)):
        raise GuideError(f"There's no guide page called {page_id!r}.")
    return page_file(page_id, base).read_text(encoding="utf-8")
