"""Number entities for Audac MTX zone volume control."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_MODEL, MODEL_MTX88, MODEL_ZONES
from .coordinator import AudacMTXCoordinator
from .entity import AudacMTXBaseEntity

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
        entities.append(AudacMTXVolumeNumber(coordinator, zone, entry))
    async_add_entities(entities)
    await _async_update_zone_visibility(hass, entry, zones_count, DOMAIN)


class AudacMTXVolumeNumber(AudacMTXBaseEntity, NumberEntity):
    _attr_icon = "mdi:volume-high"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = "%"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: AudacMTXCoordinator, zone: int, entry: ConfigEntry) -> None:
        super().__init__(coordinator, zone, entry)
        zone_name = entry.options.get(f"zone_{zone}_name", f"Zone {zone}")
        self._attr_unique_id = f"{entry.entry_id}_zone_{zone}_volume"
        self._attr_name = f"{zone_name} Volume"

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
