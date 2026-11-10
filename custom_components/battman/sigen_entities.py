"""Find Sigenergy-Local-Modbus's entities whose ID differs between its 1.x and 2.x.

Sigenergy-Local-Modbus 2.0 renamed a few entities in English, and a fresh 2.x install builds its entity
IDs from the names (an install that was upgraded keeps its IDs). Its unique ID doesn't change:
`<config entry>_sigen_plant_<register key>`. So each is found in the entity registry by that key, and
Battman's blueprints, cards and Overrides card get the ID this HA has.

Nothing found (the integration isn't set up, or the entity is gone) gives the 1.x ID, so the
missing-entities Repair names it.
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import SIGEN_MAP

SIGEN_PLATFORM = "sigen"


def resolve(hass: HomeAssistant) -> dict[str, str]:
    """Map name -> the entity ID in this HA (the 1.x ID when the integration has no such entity)."""
    entries = [e for e in er.async_get(hass).entities.values() if e.platform == SIGEN_PLATFORM]
    out: dict[str, str] = {}
    for name, (domain, key, default) in SIGEN_MAP.items():
        found = sorted(e.entity_id for e in entries
                       if e.domain == domain and (e.unique_id or "").endswith(f"_sigen_plant_{key}"))
        # more than one plant: keep the one with the 1.x ID if there is one, else the first
        out[name] = default if default in found or not found else found[0]
    return out
