"""Number entities for Audac MTX zone volume control."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_MODEL, MODEL_MTX88, MODEL_ZONES, MODEL_NAMES
from .coordinator import AudacMTXCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AudacMTXCoordinator = hass.data[DOMAIN][entry.entry_id]
    model = entry.data.get(CONF_MODEL, MODEL_MTX88)
    zones_count = entry.data.get("zones", MODEL_ZONES.get(model, 8))

    entities = []
    for zone in range(1, zones_count + 1):
        if entry.options.get(f"zone_{zone}_visible", True):
            entities.append(AudacMTXVolumeNumber(coordinator, zone, entry))
    async_add_entities(entities)


class AudacMTXVolumeNumber(CoordinatorEntity[AudacMTXCoordinator], NumberEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:volume-high"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = "%"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: AudacMTXCoordinator, zone: int, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._zone = zone
        self._entry = entry
        zone_name = entry.options.get(f"zone_{zone}_name", f"Zone {zone}")
        self._attr_unique_id = f"{entry.entry_id}_zone_{zone}_volume"
        self._attr_name = f"{zone_name} Volume"
        model = entry.data.get(CONF_MODEL, MODEL_MTX88)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.data.get("name", "Audac MTX"),
            "manufacturer": "Audac",
            "model": MODEL_NAMES.get(model, "MTX"),
        }

    @property
    def _zone_data(self) -> dict[str, Any]:
        if self.coordinator.data and self._zone in self.coordinator.data:
            return self.coordinator.data[self._zone]
        return {}

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and bool(self._zone_data)

    @property
    def native_value(self) -> float | None:
        data = self._zone_data
        if not data:
            return None
        volume_raw = data.get("volume")
        if volume_raw is None:
            return None
        return round((1.0 - (volume_raw / 70.0)) * 100)

    async def async_set_native_value(self, value: float) -> None:
        volume_raw = int((1.0 - (value / 100.0)) * 70)
        volume_raw = max(0, min(70, volume_raw))
        await self.coordinator.client.set_volume(self._zone, volume_raw)
        await self.coordinator.async_request_refresh()
