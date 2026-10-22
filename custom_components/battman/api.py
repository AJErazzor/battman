"""HTTP endpoints for Battman pages, plus the views Create dashboard writes."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.http import KEY_HASS

from . import cards, images, themes
from .const import (
    CARDS_URL,
    DOMAIN,
    ENTITY_MAP_DEFAULTS,
    ENTITY_MAP_URL,
    IMAGE_URL,
    IMAGES_URL,
    MIGRATED,
    OTHER_MAP_DEFAULTS,
    SMIGGLES_NAMES,
    SMIGGLES_PROBE,
    THEMES_URL,
)

VIEWS_DIR = Path(__file__).parent / "views"
PLACEHOLDER = re.compile(r"\{\{\s*([a-z0-9_]+)\s*\}\}")


def smiggles_in_charge(hass: HomeAssistant) -> bool:
    """True until you migrate, if Smiggles is installed (its parameters sensor exists)."""
    entries = hass.config_entries.async_entries(DOMAIN)
    if entries and entries[0].data.get(MIGRATED):
        return False
    if hass.states.get(SMIGGLES_PROBE) is not None:
        return True
    # early in HA's start the sensor may not be loaded yet: its registry entry says it exists
    return er.async_get(hass).async_get(SMIGGLES_PROBE) is not None


def entity_map(hass: HomeAssistant) -> dict[str, str]:
    """The entity map: Battman's defaults, with your Configure-screen choices on top.

    Engine entries (ENGINE_MAP) point at whichever engine is in charge: Smiggles'
    entities until you migrate (if Smiggles is installed), Battman's after.
    """
    emap = dict(ENTITY_MAP_DEFAULTS)
    entries = hass.config_entries.async_entries(DOMAIN)
    if entries:
        emap.update({k: v for k, v in entries[0].options.items() if k in OTHER_MAP_DEFAULTS and v})
    if smiggles_in_charge(hass):
        emap.update(SMIGGLES_NAMES)
    return emap


def _load_views() -> list[tuple[str, Any]]:
    return [(f.name, yaml.safe_load(f.read_text(encoding="utf-8"))) for f in sorted(VIEWS_DIR.glob("*.yaml"))]


def _fill(obj: Any, emap: dict[str, str], missing: set[str]) -> Any:
    if isinstance(obj, dict):
        return {k: _fill(v, emap, missing) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_fill(v, emap, missing) for v in obj]
    if isinstance(obj, str):
        def sub(m: re.Match) -> str:
            name = m.group(1)
            if name not in emap:
                missing.add(name)
                return m.group(0)
            return emap[name]
        return PLACEHOLDER.sub(sub, obj)
    return obj


def _card_sizes(obj: Any, sizes: dict[str, Any]) -> Any:
    """A Battman card placed without grid_options gets its card file's (e.g. columns: full).
    HA reads grid_options only on the card as placed, never inside the card file."""
    if isinstance(obj, dict):
        out = {k: _card_sizes(v, sizes) for k, v in obj.items()}
        t = out.get("type")
        if isinstance(t, str) and t.startswith("custom:battman-") and "grid_options" not in out:
            if (size := sizes.get(t[len("custom:battman-"):])) is not None:
                out["grid_options"] = dict(size)
        return out
    if isinstance(obj, list):
        return [_card_sizes(v, sizes) for v in obj]
    return obj


async def async_build_dashboard(hass: HomeAssistant) -> dict[str, Any]:
    """{"views": [...], "errors": [...]}: the views Create dashboard writes into /battman."""
    emap = entity_map(hass)
    errors: list[str] = []
    views = []
    sizes = await hass.async_add_executor_job(cards.grid_options, cards.local_dir(hass))
    for name, view in await hass.async_add_executor_job(_load_views):
        missing: set[str] = set()
        filled = _card_sizes(_fill(view, emap, missing), sizes)
        if missing:
            errors.append(f"{name}: Battman entity map has no entry for: {', '.join(sorted(missing))}")
        views.append(filled)
    return {"views": views, "errors": errors}


class BattmanEntityMapView(HomeAssistantView):
    """GET /api/battman/entities -> {"version": "...", "entities": {name: entity_id}}."""

    url = ENTITY_MAP_URL
    name = "api:battman:entities"
    requires_auth = True

    def __init__(self, version: str) -> None:
        self._version = version

    async def get(self, request):
        hass: HomeAssistant = request.app[KEY_HASS]
        return self.json({"version": self._version, "entities": entity_map(hass)})


class BattmanThemeSaveView(HomeAssistantView):
    """POST /api/battman/themes {name, yaml, overwrite} -> saves one of your themes.

    Admin only. Writes <config>/themes/battman/custom/<name>.yaml and reloads themes.
    """

    url = THEMES_URL
    name = "api:battman:themes"
    requires_auth = True

    async def post(self, request):
        hass: HomeAssistant = request.app[KEY_HASS]
        user = request.get("hass_user")
        if user is None or not user.is_admin:
            return self.json({"message": "Only an administrator can save themes."}, status_code=403)
        try:
            body = await request.json()
        except ValueError:
            return self.json({"message": "Request isn't valid JSON."}, status_code=400)
        dst = themes.dst_dir(hass)
        try:
            path = await hass.async_add_executor_job(
                themes.save_custom, dst, body.get("name", ""), body.get("yaml", ""), bool(body.get("overwrite"))
            )
        except themes.ThemeSaveError as err:
            return self.json({"message": str(err), "exists": err.exists}, status_code=err.status)
        await themes.async_reload(hass)
        return self.json({"message": "saved", "file": str(path.relative_to(hass.config.config_dir))})


class BattmanCardsView(HomeAssistantView):
    """GET /api/battman/cards -> {"cards": [{id, name, description, source}]}."""

    url = CARDS_URL
    name = "api:battman:cards"
    requires_auth = True

    async def get(self, request):
        hass: HomeAssistant = request.app[KEY_HASS]
        local = cards.local_dir(hass)
        result = await hass.async_add_executor_job(cards.list_cards, local)
        cards.update_issue(hass, [c["id"] for c in result if c["source"] != "battman"])
        return self.json({"cards": result})


class BattmanCardView(HomeAssistantView):
    """GET /api/battman/cards/{card_id} -> the card's config with the map filled in."""

    url = CARDS_URL + "/{card_id}"
    name = "api:battman:card"
    requires_auth = True

    async def get(self, request, card_id: str):
        hass: HomeAssistant = request.app[KEY_HASS]
        local = cards.local_dir(hass)
        try:
            card = await hass.async_add_executor_job(cards.get_card, local, card_id, entity_map(hass))
        except cards.CardError as err:
            return self.json({"message": str(err)}, status_code=err.status)
        cards.update_issue(hass, await hass.async_add_executor_job(cards.local_ids, local))
        return self.json(card)


class BattmanImagesView(HomeAssistantView):
    """GET /api/battman/images -> {"images": [{name, source, url}], "folder": "battman/images"}."""

    url = IMAGES_URL
    name = "api:battman:images"
    requires_auth = True

    async def get(self, request):
        hass: HomeAssistant = request.app[KEY_HASS]
        result = await hass.async_add_executor_job(images.list_images, images.local_dir(hass))
        return self.json({"images": result, "folder": "/".join(images.LOCAL_PARTS)})


class BattmanImageView(HomeAssistantView):
    """GET /api/battman/image/{name} -> the image (yours if you have one by that name)."""

    url = IMAGE_URL + "/{name}"
    name = "api:battman:image"
    requires_auth = False   # an <img> can't send a login; same as /local/ and /battmanfiles/images/

    async def get(self, request, name: str):
        hass: HomeAssistant = request.app[KEY_HASS]
        path = await hass.async_add_executor_job(images.find, images.local_dir(hass), name)
        if path is None:
            return web.Response(status=404, text=f"There's no Battman image called {name!r}.")
        return web.FileResponse(
            path, headers={"Content-Type": images.content_type(path), "Cache-Control": "no-cache"}
        )
