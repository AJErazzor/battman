"""Battman cards: plain YAML card files, served to the custom:battman-<id> cards.

custom_components/battman/cards/<id>.yaml   shipped with Battman, updated by releases
<config>/battman/cards/<id>.yaml            yours: wins over the shipped one on this HA
                                            (or a new card of your own). A Repair lists
                                            these while any exist, so it's never silent.

A card file is ordinary dashboard-card YAML. Two header comments name it:
    # name: Limits
    # description: Grid export, PV max and max charge limits.
[[map:name]] anywhere in it is replaced by that entry of Battman's entity map.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN

SHIPPED = Path(__file__).parent / "cards"
LOCAL_PARTS = ("battman", "cards")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,40}$")
MAP_MARK = re.compile(r"\[\[map:([a-z0-9_]+)\]\]")
ISSUE_LOCAL = "local_cards"


class CardError(Exception):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


def local_dir(hass: HomeAssistant) -> Path:
    return Path(hass.config.path(*LOCAL_PARTS))


def _header(text: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    for line in text.splitlines():
        if not line.startswith("#"):
            break
        if m := re.match(r"#\s*(name|description)\s*:\s*(.+)$", line):
            meta[m.group(1)] = m.group(2).strip()
    return meta


def _files(local: Path) -> dict[str, tuple[Path, str]]:
    """id -> (file, source). Local files win over shipped ones."""
    out: dict[str, tuple[Path, str]] = {}
    for f in sorted(SHIPPED.glob("*.yaml")):
        out[f.stem] = (f, "battman")
    if local.is_dir():
        for f in sorted(local.glob("*.yaml")):
            if ID_RE.match(f.stem):
                out[f.stem] = (f, "local" if f.stem not in out else "local override")
    return out


def list_cards(local: Path) -> list[dict[str, str]]:
    cards = []
    for card_id, (path, source) in _files(local).items():
        meta = _header(path.read_text(encoding="utf-8"))
        cards.append({
            "id": card_id,
            "name": meta.get("name", card_id),
            "description": meta.get("description", ""),
            "source": source,
        })
    return cards


def local_ids(local: Path) -> list[str]:
    return [i for i, (_p, src) in _files(local).items() if src != "battman"]


def _fill(obj: Any, emap: dict[str, str], missing: set[str]) -> Any:
    if isinstance(obj, dict):
        return {k: _fill(v, emap, missing) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_fill(v, emap, missing) for v in obj]
    if isinstance(obj, str):
        def sub(m: re.Match) -> str:
            if m.group(1) not in emap:
                missing.add(m.group(1))
                return m.group(0)
            return emap[m.group(1)]
        return MAP_MARK.sub(sub, obj)
    return obj


def _custom_types(obj: Any, found: set[str]) -> set[str]:
    if isinstance(obj, dict):
        t = obj.get("type")
        if isinstance(t, str) and t.startswith("custom:"):
            found.add(t[7:])
        for v in obj.values():
            _custom_types(v, found)
    elif isinstance(obj, list):
        for v in obj:
            _custom_types(v, found)
    return found


def get_card(local: Path, card_id: str, emap: dict[str, str]) -> dict[str, Any]:
    """The card ready to draw. Raises CardError (unknown card, bad YAML)."""
    if not ID_RE.match(card_id or ""):
        raise CardError(f"“{card_id}” isn't a Battman card name.", 404)
    files = _files(local)
    if card_id not in files:
        raise CardError(f"There's no Battman card called “{card_id}”.", 404)
    path, source = files[card_id]
    text = path.read_text(encoding="utf-8")
    try:
        config = yaml.safe_load(text)
    except yaml.YAMLError as err:
        raise CardError(f"{path.name} ({source}) isn't valid YAML: {err}") from err
    if not isinstance(config, dict) or "type" not in config:
        raise CardError(f"{path.name} ({source}) isn't a card (it needs a `type:`).")
    missing: set[str] = set()
    filled = _fill(config, emap, missing)
    meta = _header(text)
    return {
        "id": card_id,
        "name": meta.get("name", card_id),
        "source": source,
        "config": filled,
        "missing_map": sorted(missing),
        "needs": sorted(_custom_types(filled, set())),
    }


def update_issue(hass: HomeAssistant, ids: list[str]) -> None:
    """Repair while any local card files are in use, so a local copy is never forgotten."""
    if ids:
        ir.async_create_issue(
            hass,
            DOMAIN,
            ISSUE_LOCAL,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_LOCAL,
            translation_placeholders={"cards": ", ".join(ids), "folder": "/".join(LOCAL_PARTS)},
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_LOCAL)
