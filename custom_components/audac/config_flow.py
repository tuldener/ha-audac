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
    CONF_LINE_NAME_PREFIX,
    CONF_MODEL,
    CONF_SCAN_INTERVAL,
    CONF_SOURCE_ID,
    CONF_ZONE_NAME_PREFIX,
    CONF_ZONE_COUNT,
    DEFAULT_DEVICE_ADDRESS,
    DEFAULT_INPUT_LABELS,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SOURCE_ID,
    DOMAIN,
    MODEL_MTX48,
    MODEL_MTX88,
    MTX_LINE_IDS,
    MODEL_TO_ZONES,
)


def _normalize_model(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if raw in MODEL_TO_ZONES:
        return raw
    return MODEL_MTX48


def _model_schema(default_model: str) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_MODEL, default=default_model): vol.In(
                {MODEL_MTX48: "MTX48", MODEL_MTX88: "MTX88"}
            )
        }
    )


def _device_schema(model: str, user_input: Mapping[str, Any] | None = None) -> vol.Schema:
    user_input = user_input or {}
    zone_count = MODEL_TO_ZONES.get(model, MODEL_TO_ZONES[MODEL_MTX48])

    schema: dict[Any, Any] = {
        vol.Required(CONF_NAME, default=user_input.get(CONF_NAME, "Audac")): str,
        vol.Required(CONF_HOST, default=user_input.get(CONF_HOST, "")): str,
        vol.Required(CONF_PORT, default=user_input.get(CONF_PORT, DEFAULT_PORT)): vol.All(
            int, vol.Range(min=1, max=65535)
        ),
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

    for zone in range(1, zone_count + 1):
        key = f"{CONF_ZONE_NAME_PREFIX}{zone}"
        schema[vol.Optional(key, default=user_input.get(key, f"Zone {zone}"))] = str

    for line_id in MTX_LINE_IDS:
        key = f"{CONF_LINE_NAME_PREFIX}{line_id}"
        default_label = DEFAULT_INPUT_LABELS.get(line_id, f"Line {line_id}")
        schema[vol.Optional(key, default=user_input.get(key, default_label))] = str

    return vol.Schema(schema)


def _validate_source_id(data: Mapping[str, Any]) -> bool:
    source_id = str(data.get(CONF_SOURCE_ID, "")).strip()
    return bool(source_id) and len(source_id) <= 4 and "#" not in source_id and "|" not in source_id


def _validate_custom_labels(data: Mapping[str, Any]) -> str | None:
    for key, value in data.items():
        if key.startswith(CONF_ZONE_NAME_PREFIX) or key.startswith(CONF_LINE_NAME_PREFIX):
            if not str(value).strip():
                return key
    return None


async def _can_connect(data: Mapping[str, Any]) -> bool:
    model = _normalize_model(data.get(CONF_MODEL))
    client = AudacMtxClient(
        host=data[CONF_HOST],
        port=data[CONF_PORT],
        source_id=data[CONF_SOURCE_ID],
        device_address=data[CONF_DEVICE_ADDRESS],
    )
    await client.async_get_state(MODEL_TO_ZONES[model])
    return True


class AudacConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle Audac config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._last_error_detail = "-"
        self._selected_model = MODEL_MTX48

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> dict[str, Any]:
        if user_input is not None:
            self._selected_model = _normalize_model(user_input.get(CONF_MODEL))
            return await self.async_step_device()

        return self.async_show_form(
            step_id="user",
            data_schema=_model_schema(self._selected_model),
            description_placeholders={"error_detail": self._last_error_detail},
        )

    async def async_step_device(self, user_input: dict[str, Any] | None = None) -> dict[str, Any]:
        errors: dict[str, str] = {}

        if user_input is not None:
            complete_input = {**user_input, CONF_MODEL: self._selected_model}

            if not _validate_source_id(complete_input):
                errors["base"] = "invalid_source_id"
                return self.async_show_form(
                    step_id="device",
                    data_schema=_device_schema(self._selected_model, user_input),
                    errors=errors,
                    description_placeholders={"error_detail": self._last_error_detail},
                )

            invalid_label_key = _validate_custom_labels(complete_input)
            if invalid_label_key:
                self._last_error_detail = invalid_label_key
                errors["base"] = "invalid_label"
                return self.async_show_form(
                    step_id="device",
                    data_schema=_device_schema(self._selected_model, user_input),
                    errors=errors,
                    description_placeholders={"error_detail": self._last_error_detail},
                )

            try:
                await _can_connect(complete_input)
            except AudacApiError as err:
                self._last_error_detail = str(err)
                errors["base"] = "cannot_connect"
            except Exception as err:  # noqa: BLE001
                self._last_error_detail = repr(err)
                errors["base"] = "unknown"
            else:
                self._last_error_detail = "-"
                unique_id = (
                    f"{complete_input[CONF_HOST]}:{complete_input[CONF_PORT]}:"
                    f"{complete_input[CONF_DEVICE_ADDRESS]}"
                )
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                complete_input[CONF_ZONE_COUNT] = MODEL_TO_ZONES[self._selected_model]
                return self.async_create_entry(
                    title=complete_input[CONF_NAME],
                    data=complete_input,
                )

        return self.async_show_form(
            step_id="device",
            data_schema=_device_schema(self._selected_model, user_input),
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
        merged = {**self.config_entry.data, **self.config_entry.options}
        self._selected_model = _normalize_model(merged.get(CONF_MODEL))

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> dict[str, Any]:
        merged = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            self._selected_model = _normalize_model(user_input.get(CONF_MODEL))
            return await self.async_step_device()

        return self.async_show_form(
            step_id="init",
            data_schema=_model_schema(_normalize_model(merged.get(CONF_MODEL))),
            description_placeholders={"error_detail": self._last_error_detail},
        )

    async def async_step_device(self, user_input: dict[str, Any] | None = None) -> dict[str, Any]:
        errors: dict[str, str] = {}
        merged = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            complete_input = {**merged, **user_input, CONF_MODEL: self._selected_model}

            if not _validate_source_id(complete_input):
                errors["base"] = "invalid_source_id"
                return self.async_show_form(
                    step_id="device",
                    data_schema=_device_schema(self._selected_model, complete_input),
                    errors=errors,
                    description_placeholders={"error_detail": self._last_error_detail},
                )

            invalid_label_key = _validate_custom_labels(complete_input)
            if invalid_label_key:
                self._last_error_detail = invalid_label_key
                errors["base"] = "invalid_label"
                return self.async_show_form(
                    step_id="device",
                    data_schema=_device_schema(self._selected_model, complete_input),
                    errors=errors,
                    description_placeholders={"error_detail": self._last_error_detail},
                )

            try:
                await _can_connect(complete_input)
            except AudacApiError as err:
                self._last_error_detail = str(err)
                errors["base"] = "cannot_connect"
            except Exception as err:  # noqa: BLE001
                self._last_error_detail = repr(err)
                errors["base"] = "unknown"
            else:
                self._last_error_detail = "-"
                result = dict(user_input)
                result[CONF_MODEL] = self._selected_model
                result[CONF_ZONE_COUNT] = MODEL_TO_ZONES[self._selected_model]
                return self.async_create_entry(title="", data=result)

        return self.async_show_form(
            step_id="device",
            data_schema=_device_schema(self._selected_model, merged),
            errors=errors,
            description_placeholders={"error_detail": self._last_error_detail},
        )
