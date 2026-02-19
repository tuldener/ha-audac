"""Services for Audac MTX."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_ARGUMENT,
    ATTR_COMMAND,
    ATTR_ENTRY_ID,
    DOMAIN,
    SERVICE_SEND_RAW_COMMAND,
)

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTRY_ID): cv.string,
        vol.Required(ATTR_COMMAND): cv.string,
        vol.Optional(ATTR_ARGUMENT, default="0"): cv.string,
    }
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register Audac services."""

    if hass.services.has_service(DOMAIN, SERVICE_SEND_RAW_COMMAND):
        return

    async def handle_send_raw(call: ServiceCall) -> None:
        entry_id: str = call.data[ATTR_ENTRY_ID]
        runtime: dict[str, Any] = hass.data[DOMAIN].get(entry_id)
        if not runtime:
            raise ValueError(f"Unknown Audac entry_id: {entry_id}")

        coordinator = runtime["coordinator"]
        await coordinator.client.async_send_raw(
            call.data[ATTR_COMMAND],
            call.data[ATTR_ARGUMENT],
        )
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_RAW_COMMAND,
        handle_send_raw,
        schema=SERVICE_SCHEMA,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload Audac services when no config entries are left."""
    if hass.services.has_service(DOMAIN, SERVICE_SEND_RAW_COMMAND):
        hass.services.async_remove(DOMAIN, SERVICE_SEND_RAW_COMMAND)
