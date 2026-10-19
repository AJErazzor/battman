"""HTTP endpoints for Battman pages."""

from __future__ import annotations

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.helpers.http import KEY_HASS

from .const import ENTITY_MAP_DEFAULTS, ENTITY_MAP_URL


def entity_map(hass: HomeAssistant) -> dict[str, str]:
    """The current entity map (defaults for now; Configure screen overrides later)."""
    return dict(ENTITY_MAP_DEFAULTS)


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
