"""Sensor entities for Audac MTX active source display."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_MODEL, MODEL_MTX88, MODEL_ZONES, MODEL_NAMES, get_source_names
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
            entities.append(AudacMTXSourceSensor(coordinator, zone, entry))
    async_add_entities(entities)


class AudacMTXSourceSensor(CoordinatorEntity[AudacMTXCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:audio-input-stereo-minijack"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: AudacMTXCoordinator, zone: int, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._zone = zone
        self._entry = entry
        zone_name = entry.options.get(f"zone_{zone}_name", f"Zone {zone}")
        self._attr_unique_id = f"{entry.entry_id}_zone_{zone}_active_source"
        self._attr_name = f"{zone_name} Active Source"
        self._source_names = get_source_names(entry.options, visible_only=False)
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
    def native_value(self) -> str | None:
        data = self._zone_data
        if not data:
            return None
        routing = data.get("routing")
        if routing is None:
            return None
        return self._source_names.get(routing, f"Input {routing}")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self._zone_data
        if not data:
            return {}
        return {
            "routing_id": data.get("routing", 0),
            "volume_raw": data.get("volume", 70),
            "volume_db": data.get("volume_db", -70),
            "mute": data.get("mute", False),
            "bass_db": data.get("bass_db", 0),
            "treble_db": data.get("treble_db", 0),
        }
