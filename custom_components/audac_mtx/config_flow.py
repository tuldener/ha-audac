"""Config flow for Audac MTX integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    DEFAULT_PORT,
    CONF_MODEL,
    MODEL_MTX48,
    MODEL_MTX88,
    MODEL_ZONES,
    INPUT_NAMES,
)

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_MODEL, default=MODEL_MTX88): vol.In(
            {MODEL_MTX48: "MTX48 (4 Zonen)", MODEL_MTX88: "MTX88 (8 Zonen)"}
        ),
        vol.Optional("name", default="Audac MTX"): str,
    }
)


class AudacMTXConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            from .mtx_client import MTXClient

            model = user_input.get(CONF_MODEL, MODEL_MTX88)
            user_input["zones"] = MODEL_ZONES[model]

            client = MTXClient(
                host=user_input[CONF_HOST],
                port=user_input.get(CONF_PORT, DEFAULT_PORT),
            )
            try:
                await client.connect()
                await client.get_version()
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

    @staticmethod
    def async_get_options_flow(config_entry):
        return AudacMTXOptionsFlow(config_entry)


class AudacMTXOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            validated = {}
            for key, value in user_input.items():
                if isinstance(value, str):
                    value = value.strip()
                    if key.endswith("_name") and not value:
                        errors["base"] = "empty_name"
                        break
                validated[key] = value

            if not errors:
                return self.async_create_entry(title="", data=validated)

        model = self._config_entry.data.get(CONF_MODEL, MODEL_MTX88)
        zones_count = MODEL_ZONES.get(model, 8)
        current_options = self._config_entry.options

        schema_dict = {}

        for i in range(1, zones_count + 1):
            default_name = current_options.get(f"zone_{i}_name", f"Zone {i}")
            schema_dict[vol.Optional(f"zone_{i}_name", default=default_name)] = str
            default_visible = current_options.get(f"zone_{i}_visible", True)
            schema_dict[vol.Optional(f"zone_{i}_visible", default=default_visible)] = bool

            # Kopplung als Checkboxen (SelectSelector multi, mode=list)
            # Migration: altes Format zone_i_linked_to (int) → neues Format zone_i_links (List[str])
            old_linked = current_options.get(f"zone_{i}_linked_to", 0)
            if old_linked and old_linked != 0:
                migration_default = [str(old_linked)]
            else:
                migration_default = []
            default_links = current_options.get(f"zone_{i}_links", migration_default)
            if isinstance(default_links, int):
                default_links = [str(default_links)] if default_links != 0 else []

            coupling_options = [
                selector.SelectOptionDict(
                    value=str(j),
                    label=current_options.get(f"zone_{j}_name", f"Zone {j}"),
                )
                for j in range(1, zones_count + 1) if j != i
            ]
            schema_dict[vol.Optional(f"zone_{i}_links", default=default_links)] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=coupling_options,
                    multiple=True,
                    mode=selector.SelectSelectorMode.LIST,
                )
            )

        for input_id, default_label in INPUT_NAMES.items():
            current_label = current_options.get(f"source_{input_id}_name", default_label)
            schema_dict[vol.Optional(f"source_{input_id}_name", default=current_label)] = str
            # source_0 (Off) hidden by default; all others visible by default
            default_visible = input_id != 0
            default_visible = current_options.get(f"source_{input_id}_visible", default_visible)
            schema_dict[vol.Optional(f"source_{input_id}_visible", default=default_visible)] = bool

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )
