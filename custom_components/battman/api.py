"""HTTP endpoints for Battman pages and the managed dashboard."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.helpers.http import KEY_HASS

from . import themes
from .const import DASHBOARD_URL, DOMAIN, ENTITY_MAP_DEFAULTS, ENTITY_MAP_URL, THEMES_URL

VIEWS_DIR = Path(__file__).parent / "views"
PLACEHOLDER = re.compile(r"\{\{\s*([a-z0-9_]+)\s*\}\}")


def entity_map(hass: HomeAssistant) -> dict[str, str]:
    """The entity map: Battman's defaults, with your Configure-screen choices on top."""
    emap = dict(ENTITY_MAP_DEFAULTS)
    entries = hass.config_entries.async_entries(DOMAIN)
    if entries:
        emap.update({k: v for k, v in entries[0].options.items() if k in emap and v})
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


async def async_build_dashboard(hass: HomeAssistant) -> dict[str, Any]:
    """{"views": [...], "errors": [...]} for the managed dashboard."""
    emap = entity_map(hass)
    errors: list[str] = []
    views = []
    for name, view in await hass.async_add_executor_job(_load_views):
        missing: set[str] = set()
        filled = _fill(view, emap, missing)
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


class BattmanDashboardView(HomeAssistantView):
    """GET /api/battman/dashboard -> the managed dashboard's views."""

    url = DASHBOARD_URL
    name = "api:battman:dashboard"
    requires_auth = True

    async def get(self, request):
        hass: HomeAssistant = request.app[KEY_HASS]
        return self.json(await async_build_dashboard(hass))


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
