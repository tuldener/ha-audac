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
    MODEL_XMP44,
    MODEL_ZONES,
    MODEL_SLOTS,
    INPUT_NAMES,
    is_mtx_model,
    is_xmp_model,
)

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_MODEL, default=MODEL_MTX88): vol.In(
            {
                MODEL_MTX48: "MTX48 (4 Zonen)",
                MODEL_MTX88: "MTX88 (8 Zonen)",
                MODEL_XMP44: "XMP44 (4 Slots)",
            }
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
            model = user_input.get(CONF_MODEL, MODEL_MTX88)

            if is_xmp_model(model):
                from .xmp44_client import XMP44Client
                user_input["slots"] = MODEL_SLOTS[model]
                client = XMP44Client(
                    host=user_input[CONF_HOST],
                    port=user_input.get(CONF_PORT, DEFAULT_PORT),
                )
            else:
                from .mtx_client import MTXClient
                user_input["zones"] = MODEL_ZONES[model]
                client = MTXClient(
                    host=user_input[CONF_HOST],
                    port=user_input.get(CONF_PORT, DEFAULT_PORT),
                )

            try:
                await client.connect()
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

        return await self._show_options_form(errors)

    async def _show_options_form(
        self,
        errors: dict[str, str] | None = None,
    ) -> FlowResult:
        model = self._config_entry.data.get(CONF_MODEL, MODEL_MTX88)
        current_options = self._config_entry.options

        schema_dict = {}

        if is_xmp_model(model):
            # XMP44: Module selection, slot names and visibility
            slots_count = self._config_entry.data.get("slots", MODEL_SLOTS.get(model, 4))

            module_options = [
                selector.SelectOptionDict(value="0", label="Kein Modul"),
                selector.SelectOptionDict(value="1", label="DMP40 (DAB/DAB+ & FM Tuner)"),
                selector.SelectOptionDict(value="2", label="TMP40 (FM Tuner)"),
                selector.SelectOptionDict(value="3", label="MMP40 (Media Player/Recorder)"),
                selector.SelectOptionDict(value="4", label="IMP40 (Internet Radio)"),
                selector.SelectOptionDict(value="6", label="FMP40 (Voice File)"),
                selector.SelectOptionDict(value="8", label="BMP40 (Bluetooth)"),
                selector.SelectOptionDict(value="9", label="NMP40 (Network Player)"),
            ]

            for i in range(1, slots_count + 1):
                default_module = current_options.get(f"slot_{i}_module", "0")
                if isinstance(default_module, int):
                    default_module = str(default_module)
                schema_dict[vol.Optional(f"slot_{i}_module", default=default_module)] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=module_options,
                        multiple=False,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
                default_name = current_options.get(f"slot_{i}_name", f"Slot {i}")
                schema_dict[vol.Optional(f"slot_{i}_name", default=default_name)] = str
                default_visible = current_options.get(f"slot_{i}_visible", True)
                schema_dict[vol.Optional(f"slot_{i}_visible", default=default_visible)] = bool

                # FMP40-specific: trigger count and names (only if slot is FMP40)
                if default_module == "6":
                    default_triggers = current_options.get(f"slot_{i}_triggers", 0)
                    schema_dict[vol.Optional(f"slot_{i}_triggers", default=default_triggers)] = selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=50, step=1, mode=selector.NumberSelectorMode.BOX,
                        )
                    )
                    default_trigger_names = current_options.get(f"slot_{i}_trigger_names", "")
                    schema_dict[vol.Optional(f"slot_{i}_trigger_names", default=default_trigger_names)] = str
        else:
            # MTX: Zone names, visibility, coupling, and source configuration
            zones_count = MODEL_ZONES.get(model, 8)

            for i in range(1, zones_count + 1):
                default_name = current_options.get(f"zone_{i}_name", f"Zone {i}")
                schema_dict[vol.Optional(f"zone_{i}_name", default=default_name)] = str
                default_visible = current_options.get(f"zone_{i}_visible", True)
                schema_dict[vol.Optional(f"zone_{i}_visible", default=default_visible)] = bool

                # Kopplung als Dropdown (eine Slave-Zone kann nur einen Master haben)
                old_links = current_options.get(f"zone_{i}_links")
                if isinstance(old_links, list) and len(old_links) > 0:
                    migration_default = str(old_links[0])
                else:
                    old_linked = current_options.get(f"zone_{i}_linked_to", 0)
                    migration_default = str(old_linked) if old_linked and old_linked != 0 else "0"
                default_link = current_options.get(f"zone_{i}_link", migration_default)
                if isinstance(default_link, int):
                    default_link = str(default_link)

                coupling_options = [
                    selector.SelectOptionDict(value="0", label="Keine Kopplung"),
                ] + [
                    selector.SelectOptionDict(
                        value=str(j),
                        label=current_options.get(f"zone_{j}_name", f"Zone {j}"),
                    )
                    for j in range(1, zones_count + 1) if j != i
                ]
                schema_dict[vol.Optional(f"zone_{i}_link", default=default_link)] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=coupling_options,
                        multiple=False,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )

            for input_id, default_label in INPUT_NAMES.items():
                current_label = current_options.get(f"source_{input_id}_name", default_label)
                schema_dict[vol.Optional(f"source_{input_id}_name", default=current_label)] = str
                default_visible = input_id != 0
                default_visible = current_options.get(f"source_{input_id}_visible", default_visible)
                schema_dict[vol.Optional(f"source_{input_id}_visible", default=default_visible)] = bool

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
            errors=errors or {},
        )
