"""Config flow for Audac MTX integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, DEFAULT_PORT
from .mtx_client import MTXClient

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional("zones", default=8): vol.All(int, vol.Range(min=1, max=8)),
        vol.Optional("name", default="Audac MTX"): str,
    }
)


class AudacMTXConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            client = MTXClient(
                host=user_input[CONF_HOST],
                port=user_input.get(CONF_PORT, DEFAULT_PORT),
            )
            try:
                await client.connect()
                version = await client.get_version()
                await client.disconnect()

                await self.async_set_unique_id(f"audac_mtx_{user_input[CONF_HOST]}")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input.get("name", "Audac MTX"),
                    data=user_input,
                )
            except Exception:
                errors["base"] = "cannot_connect"
            finally:
                await client.disconnect()

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )
