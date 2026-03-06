"""Switch entities for Audac MTX zone mute control."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
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
        entities.append(AudacMTXMuteSwitch(coordinator, zone, entry))
    async_add_entities(entities)
    await _async_update_zone_visibility(hass, entry, zones_count, DOMAIN)


class AudacMTXMuteSwitch(AudacMTXBaseEntity, SwitchEntity):
    _attr_icon = "mdi:volume-off"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: AudacMTXCoordinator, zone: int, entry: ConfigEntry) -> None:
        super().__init__(coordinator, zone, entry)
        zone_name = entry.options.get(f"zone_{zone}_name", f"Zone {zone}")
        self._attr_unique_id = f"{entry.entry_id}_zone_{zone}_mute"
        self._attr_name = f"{zone_name} Mute"

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
