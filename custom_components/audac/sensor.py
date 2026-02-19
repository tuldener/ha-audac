"""Sensor entities for Audac MTX."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_MODEL, DOMAIN, STATE_FIRMWARE
from .entity import AudacCoordinatorEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime: dict[str, Any] = hass.data[DOMAIN][entry.entry_id]
    coordinator = runtime["coordinator"]
    model = runtime["config"][CONF_MODEL]

    async_add_entities([AudacFirmwareSensor(coordinator, entry.entry_id, model)])


class AudacFirmwareSensor(AudacCoordinatorEntity, SensorEntity):
    """Firmware info sensor."""

    _attr_translation_key = "firmware"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, entry_id: str, model: str) -> None:
        super().__init__(coordinator, entry_id, model)
        self._attr_unique_id = f"{entry_id}_firmware"
        self._attr_name = "Firmware"

    @property
    def native_value(self) -> str | None:
        value = (self.coordinator.data or {}).get(STATE_FIRMWARE)
        return None if value is None else str(value)
