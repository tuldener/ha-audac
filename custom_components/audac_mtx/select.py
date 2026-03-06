"""Select entities for Audac MTX zone source selection."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, INPUT_NAMES, CONF_MODEL, MODEL_MTX88, MODEL_ZONES, get_source_names
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
        entities.append(AudacMTXSourceSelect(coordinator, zone, entry))
    async_add_entities(entities)
    await _async_update_zone_visibility(hass, entry, zones_count, DOMAIN)


class AudacMTXSourceSelect(AudacMTXBaseEntity, SelectEntity):
    _attr_icon = "mdi:audio-input-rca"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: AudacMTXCoordinator, zone: int, entry: ConfigEntry) -> None:
        super().__init__(coordinator, zone, entry)
        zone_name = entry.options.get(f"zone_{zone}_name", f"Zone {zone}")
        self._attr_unique_id = f"{entry.entry_id}_zone_{zone}_source"
        self._attr_name = f"{zone_name} Source"
        self._source_names = get_source_names(entry.options)
        self._attr_options = list(self._source_names.values())

    @property
    def options(self) -> list[str]:
        opts = list(self._source_names.values())
        data = self._zone_data
        if data:
            routing = data.get("routing", 0)
            current = self._source_names.get(routing)
            if current is None:
                fallback = INPUT_NAMES.get(routing, f"Input {routing}")
                if fallback not in opts:
                    opts.append(fallback)
        return opts

    @property
    def current_option(self) -> str | None:
        data = self._zone_data
        if not data:
            return None
        routing = data.get("routing")
        if routing is None:
            return None
        if routing in self._source_names:
            return self._source_names[routing]
        return INPUT_NAMES.get(routing, f"Input {routing}")

    async def async_select_option(self, option: str) -> None:
        for input_id, name in self._source_names.items():
            if name == option:
                await self.coordinator.client.set_routing(self._zone, input_id)
                await self.coordinator.async_request_refresh()
                return
        for input_id, name in INPUT_NAMES.items():
            if name == option:
                await self.coordinator.client.set_routing(self._zone, input_id)
                await self.coordinator.async_request_refresh()
                return
