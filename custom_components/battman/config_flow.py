"""Config flow for Battman, plus the Configure screen for the entity map."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DOMAIN, ENTITY_MAP_DEFAULTS, MAP_TEXT_ENTRIES


class BattmanConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Battman."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Single-instance setup."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="Battman", data={})
        return self.async_show_form(step_id="user")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return BattmanOptionsFlow()


class BattmanOptionsFlow(OptionsFlow):
    """Configure: which entity (or event / pattern) each Battman name points at."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        current = {**ENTITY_MAP_DEFAULTS, **{k: v for k, v in self.config_entry.options.items() if v}}
        if user_input is not None:
            errors: dict[str, str] = {}
            if "{n}" not in (user_input.get("pv_string") or ""):
                errors["pv_string"] = "pv_pattern"
            if errors:
                return self.async_show_form(step_id="init", data_schema=self._schema(user_input), errors=errors)
            # store only what differs from Battman's defaults; a default changing
            # in a future release then still reaches you
            return self.async_create_entry(
                data={k: v for k, v in user_input.items() if v and v != ENTITY_MAP_DEFAULTS.get(k)}
            )
        return self.async_show_form(step_id="init", data_schema=self._schema(current))

    @staticmethod
    def _schema(values: dict[str, Any]) -> vol.Schema:
        fields: dict[Any, Any] = {}
        for key in ENTITY_MAP_DEFAULTS:
            sel = (
                selector.TextSelector()
                if key in MAP_TEXT_ENTRIES
                else selector.EntitySelector(selector.EntitySelectorConfig())
            )
            fields[vol.Required(key, default=values.get(key, ENTITY_MAP_DEFAULTS[key]))] = sel
        return vol.Schema(fields)
