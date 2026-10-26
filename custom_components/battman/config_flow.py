"""Config flow for Battman, plus its Configure screen (the OpenNEM region, when there are several)."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DOMAIN
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
    """Configure: the OpenNEM region when OpenNEM has several. Saving keeps only what's on the
    screen, so choices from older versions (the entity map) are dropped."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        current = {k: v for k, v in self.config_entry.options.items() if v}
        if user_input is not None:
            return self.async_create_entry(data={k: v for k, v in user_input.items() if v})
        return self.async_show_form(
            step_id="init", data_schema=self._schema(current, find_regions(self.hass)),
        )

    @staticmethod
    def _schema(values: dict[str, Any], regions: list[str]) -> vol.Schema:
        fields: dict[Any, Any] = {}
        # OpenNEM: Battman finds its region sensor itself; only with several regions is there a choice
        if len(regions) > 1:
            chosen = values.get(OPENNEM_OPTION)
            fields[vol.Required(OPENNEM_OPTION, default=chosen if chosen in regions else vol.UNDEFINED)] = (
                selector.SelectSelector(selector.SelectSelectorConfig(options=regions))
            )
        return vol.Schema(fields)
