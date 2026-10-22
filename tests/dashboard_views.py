"""The views Create dashboard writes into /battman (views/*.yaml, map filled in)."""


async def built(hass):
    from custom_components.battman.api import async_build_dashboard  # noqa: PLC0415

    return await async_build_dashboard(hass)
