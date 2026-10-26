"""Config flow for Battman, plus the Configure screen for the entity map."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DOMAIN, OTHER_MAP_DEFAULTS
from .nem import OPTION as OPENNEM_OPTION, find_regions


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
    """Configure: which entity each Battman name points at."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        current = {**OTHER_MAP_DEFAULTS, **{k: v for k, v in self.config_entry.options.items() if v}}
        if user_input is not None:
            # store only what differs from Battman's defaults; a default changing
            # in a future release then still reaches you
            return self.async_create_entry(
                data={k: v for k, v in user_input.items() if v and v != OTHER_MAP_DEFAULTS.get(k)}
            )
        return self.async_show_form(
            step_id="init", data_schema=self._schema(current, find_regions(self.hass)),
        )

    @staticmethod
    def _schema(values: dict[str, Any], regions: list[str]) -> vol.Schema:
        fields: dict[Any, Any] = {}
        for key in OTHER_MAP_DEFAULTS:
            fields[vol.Required(key, default=values.get(key, OTHER_MAP_DEFAULTS[key]))] = (
                selector.EntitySelector(selector.EntitySelectorConfig())
            )
        # OpenNEM: Battman finds its region sensor itself; only with several regions is there a choice
        if len(regions) > 1:
            chosen = values.get(OPENNEM_OPTION)
            fields[vol.Required(OPENNEM_OPTION, default=chosen if chosen in regions else vol.UNDEFINED)] = (
                selector.SelectSelector(selector.SelectSelectorConfig(options=regions))
            )
        return vol.Schema(fields)
