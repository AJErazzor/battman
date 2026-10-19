"""Repair flows: the restart button on the 'Battman updated' notice."""

from __future__ import annotations

from typing import Any

from homeassistant.components.repairs import RepairsFlow
import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import issue_registry as ir


class RestartFlow(RepairsFlow):
    """Confirm, then restart Home Assistant."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            await self.hass.services.async_call("homeassistant", "restart", blocking=False)
            return self.async_create_entry(data={})
        issue = ir.async_get(self.hass).async_get_issue(self.handler, self.issue_id)
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders=issue.translation_placeholders if issue else None,
        )


async def async_create_fix_flow(
    hass: HomeAssistant, issue_id: str, data: dict[str, str | int | float | None] | None
) -> RepairsFlow:
    return RestartFlow()
