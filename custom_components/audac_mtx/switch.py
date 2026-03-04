"""Switch entities for Audac MTX zone mute control."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
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
            entities.append(AudacMTXMuteSwitch(coordinator, zone, entry))
    async_add_entities(entities)


class AudacMTXMuteSwitch(CoordinatorEntity[AudacMTXCoordinator], SwitchEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:volume-off"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: AudacMTXCoordinator, zone: int, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._zone = zone
        self._entry = entry
        zone_name = entry.options.get(f"zone_{zone}_name", f"Zone {zone}")
        self._attr_unique_id = f"{entry.entry_id}_zone_{zone}_mute"
        self._attr_name = f"{zone_name} Mute"
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
    def is_on(self) -> bool | None:
        data = self._zone_data
        if not data:
            return None
        return data.get("mute", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.client.set_mute(self._zone, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.set_mute(self._zone, False)
        await self.coordinator.async_request_refresh()
