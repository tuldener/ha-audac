"""Config flow for Audac MTX integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT

from .client import AudacApiError, AudacMtxClient
from .const import (
    CONF_DEVICE_ADDRESS,
    CONF_MODEL,
    CONF_SCAN_INTERVAL,
    CONF_SOURCE_ID,
    CONF_ZONE_COUNT,
    DEFAULT_DEVICE_ADDRESS,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SOURCE_ID,
    DOMAIN,
    MODEL_MTX48,
    MODEL_MTX88,
    MODEL_TO_ZONES,
)


def _device_schema(user_input: Mapping[str, Any] | None = None) -> vol.Schema:
    user_input = user_input or {}

    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=user_input.get(CONF_NAME, "Audac MTX")): str,
            vol.Required(CONF_HOST, default=user_input.get(CONF_HOST, "")): str,
            vol.Required(CONF_PORT, default=user_input.get(CONF_PORT, DEFAULT_PORT)): vol.All(
                int, vol.Range(min=1, max=65535)
            ),
            vol.Required(
                CONF_MODEL,
                default=user_input.get(CONF_MODEL, MODEL_MTX48),
            ): vol.In({MODEL_MTX48: "MTX48", MODEL_MTX88: "MTX88"}),
            vol.Required(
                CONF_SOURCE_ID,
                default=user_input.get(CONF_SOURCE_ID, DEFAULT_SOURCE_ID),
            ): str,
            vol.Required(
                CONF_DEVICE_ADDRESS,
                default=user_input.get(CONF_DEVICE_ADDRESS, DEFAULT_DEVICE_ADDRESS),
            ): str,
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(int, vol.Range(min=2, max=300)),
        }
    )


async def _can_connect(data: Mapping[str, Any]) -> bool:
    client = AudacMtxClient(
        host=data[CONF_HOST],
        port=data[CONF_PORT],
        source_id=data[CONF_SOURCE_ID],
        device_address=data[CONF_DEVICE_ADDRESS],
    )
    await client.async_get_state(MODEL_TO_ZONES[data[CONF_MODEL]])
    return True


class AudacConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle Audac config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._last_error_detail = "-"

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        errors: dict[str, str] = {}

        if user_input is not None:
            source_id = str(user_input.get(CONF_SOURCE_ID, "")).strip()
            if not source_id or len(source_id) > 4 or "#" in source_id or "|" in source_id:
                errors["base"] = "invalid_source_id"
                return self.async_show_form(
                    step_id="user",
                    data_schema=_device_schema(user_input),
                    errors=errors,
                )
            try:
                await _can_connect(user_input)
            except AudacApiError as err:
                self._last_error_detail = str(err)
                errors["base"] = "cannot_connect"
            except Exception as err:  # noqa: BLE001
                self._last_error_detail = repr(err)
                errors["base"] = "unknown"
            else:
                self._last_error_detail = "-"
                unique_id = (
                    f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}:"
                    f"{user_input[CONF_DEVICE_ADDRESS]}"
                )
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                user_input[CONF_ZONE_COUNT] = MODEL_TO_ZONES[user_input[CONF_MODEL]]
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_device_schema(user_input),
            errors=errors,
            description_placeholders={"error_detail": self._last_error_detail},
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "AudacOptionsFlow":
        return AudacOptionsFlow(config_entry)


class AudacOptionsFlow(config_entries.OptionsFlow):
    """Handle Audac options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry
        self._last_error_detail = "-"

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        errors: dict[str, str] = {}

        merged = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            new_data = {**merged, **user_input}
            source_id = str(new_data.get(CONF_SOURCE_ID, "")).strip()
            if not source_id or len(source_id) > 4 or "#" in source_id or "|" in source_id:
                errors["base"] = "invalid_source_id"
                return self.async_show_form(
                    step_id="init",
                    data_schema=_device_schema(new_data),
                    errors=errors,
                )
            try:
                await _can_connect(new_data)
            except AudacApiError as err:
                self._last_error_detail = str(err)
                errors["base"] = "cannot_connect"
            except Exception as err:  # noqa: BLE001
                self._last_error_detail = repr(err)
                errors["base"] = "unknown"
            else:
                self._last_error_detail = "-"
                user_input[CONF_ZONE_COUNT] = MODEL_TO_ZONES[new_data[CONF_MODEL]]
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_device_schema(merged),
            errors=errors,
            description_placeholders={"error_detail": self._last_error_detail},
        )
