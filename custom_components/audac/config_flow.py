"""Config flow for Audac integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT

from .client import AudacApiError, AudacMtxClient, AudacXmpClient
from .const import (
    CONF_DEVICE_ADDRESS,
    CONF_LINE_NAME_PREFIX,
    CONF_MODEL,
    CONF_SCAN_INTERVAL,
    CONF_SLOT_MODULE_PREFIX,
    CONF_SOURCE_ID,
    CONF_ZONE_NAME_PREFIX,
    CONF_ZONE_COUNT,
    DEFAULT_DEVICE_ADDRESS,
    DEFAULT_INPUT_LABELS,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SOURCE_ID_MTX,
    DEFAULT_SOURCE_ID_XMP,
    DEFAULT_XMP_DEVICE_ADDRESS,
    DOMAIN,
    MODEL_MTX48,
    MODEL_MTX88,
    MODEL_TO_ZONES,
    MODEL_XMP44,
    MTX_LINE_IDS,
    XMP_MODULE_AUTO,
    XMP_MODULE_OPTIONS,
    XMP_SLOT_COUNT,
)


def _normalize_model(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if raw in (MODEL_MTX48, MODEL_MTX88, MODEL_XMP44):
        return raw
    return MODEL_MTX48


def _model_schema(default_model: str) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_MODEL, default=default_model): vol.In(
                {
                    MODEL_MTX48: "MTX48",
                    MODEL_MTX88: "MTX88",
                    MODEL_XMP44: "XMP44",
                }
            )
        }
    )


def _device_schema(model: str, user_input: Mapping[str, Any] | None = None) -> vol.Schema:
    user_input = user_input or {}
    default_source_id = DEFAULT_SOURCE_ID_XMP if model == MODEL_XMP44 else DEFAULT_SOURCE_ID_MTX

    schema: dict[Any, Any] = {
        vol.Required(CONF_NAME, default=user_input.get(CONF_NAME, "Audac")): str,
        vol.Required(CONF_HOST, default=user_input.get(CONF_HOST, "")): str,
        vol.Required(CONF_PORT, default=user_input.get(CONF_PORT, DEFAULT_PORT)): vol.All(
            int, vol.Range(min=1, max=65535)
        ),
        vol.Required(
            CONF_SOURCE_ID,
            default=user_input.get(CONF_SOURCE_ID, default_source_id),
        ): str,
        vol.Required(
            CONF_SCAN_INTERVAL,
            default=user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        ): vol.All(int, vol.Range(min=2, max=300)),
    }

    if model == MODEL_XMP44:
        for slot in range(1, XMP_SLOT_COUNT + 1):
            key = f"{CONF_SLOT_MODULE_PREFIX}{slot}"
            schema[vol.Optional(key, default=user_input.get(key, XMP_MODULE_AUTO))] = vol.In(
                XMP_MODULE_OPTIONS
            )
        return vol.Schema(schema)

    zone_count = MODEL_TO_ZONES.get(model, MODEL_TO_ZONES[MODEL_MTX48])

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


def _validate_custom_labels(data: Mapping[str, Any], model: str) -> str | None:
    if model == MODEL_XMP44:
        return None

    for key, value in data.items():
        if key.startswith(CONF_ZONE_NAME_PREFIX) or key.startswith(CONF_LINE_NAME_PREFIX):
            if not str(value).strip():
                return key
    return None


def _entry_merged_data(config_entry: config_entries.ConfigEntry) -> dict[str, Any]:
    data = config_entry.data if isinstance(config_entry.data, Mapping) else {}
    options = config_entry.options if isinstance(config_entry.options, Mapping) else {}
    return {**data, **options}


def _device_address_for_model(model: str, data: Mapping[str, Any]) -> str:
    """Resolve device address with model defaults for backward compatibility."""
    if CONF_DEVICE_ADDRESS in data:
        return str(data[CONF_DEVICE_ADDRESS])
    return DEFAULT_XMP_DEVICE_ADDRESS if model == MODEL_XMP44 else DEFAULT_DEVICE_ADDRESS


async def _can_connect(data: Mapping[str, Any]) -> bool:
    model = _normalize_model(data.get(CONF_MODEL))
    device_address = _device_address_for_model(model, data)
    if model == MODEL_XMP44:
        slot_modules = {
            slot: str(data.get(f"{CONF_SLOT_MODULE_PREFIX}{slot}", XMP_MODULE_AUTO)).strip().lower()
            for slot in range(1, XMP_SLOT_COUNT + 1)
        }
        client = AudacXmpClient(
            host=data[CONF_HOST],
            port=data[CONF_PORT],
            source_id=data[CONF_SOURCE_ID],
            device_address=device_address,
        )
        await client.async_get_state(XMP_SLOT_COUNT, slot_modules)
        return True

    client = AudacMtxClient(
        host=data[CONF_HOST],
        port=data[CONF_PORT],
        source_id=data[CONF_SOURCE_ID],
        device_address=device_address,
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

            invalid_label_key = _validate_custom_labels(complete_input, self._selected_model)
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
                    f"{self._selected_model}"
                )
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                complete_input[CONF_ZONE_COUNT] = MODEL_TO_ZONES.get(self._selected_model, 0)
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
        self._config_entry = config_entry
        self._last_error_detail = "-"
        merged = _entry_merged_data(self._config_entry)
        self._selected_model = _normalize_model(merged.get(CONF_MODEL))

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            errors: dict[str, str] = {}
            merged = _entry_merged_data(self._config_entry)
            model = _normalize_model((user_input or merged).get(CONF_MODEL))
            self._selected_model = model

            if user_input is not None:
                complete_input = {**merged, **user_input, CONF_MODEL: model}

                if not _validate_source_id(complete_input):
                    errors["base"] = "invalid_source_id"
                    return self.async_show_form(
                        step_id="init",
                        data_schema=vol.Schema(
                            {
                                **_model_schema(model).schema,
                                **_device_schema(model, complete_input).schema,
                            }
                        ),
                        errors=errors,
                        description_placeholders={"error_detail": self._last_error_detail},
                    )

                invalid_label_key = _validate_custom_labels(complete_input, model)
                if invalid_label_key:
                    self._last_error_detail = invalid_label_key
                    errors["base"] = "invalid_label"
                    return self.async_show_form(
                        step_id="init",
                        data_schema=vol.Schema(
                            {
                                **_model_schema(model).schema,
                                **_device_schema(model, complete_input).schema,
                            }
                        ),
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
                    result[CONF_MODEL] = model
                    result[CONF_ZONE_COUNT] = MODEL_TO_ZONES.get(model, 0)
                    return self.async_create_entry(title="", data=result)

            schema = vol.Schema(
                {
                    **_model_schema(model).schema,
                    **_device_schema(model, merged).schema,
                }
            )

            return self.async_show_form(
                step_id="init",
                data_schema=schema,
                errors=errors,
                description_placeholders={"error_detail": self._last_error_detail},
            )
        except Exception as err:  # noqa: BLE001
            self._last_error_detail = repr(err)
            return self.async_show_form(
                step_id="init",
                data_schema=_model_schema(self._selected_model),
                errors={"base": "unknown"},
                description_placeholders={"error_detail": self._last_error_detail},
            )
