"""Select entities for Audac MTX."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_MODEL, DEFAULT_INPUT_LABELS, DOMAIN, STATE_ZONES, ZONE_SOURCE
from .entity import AudacCoordinatorEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime: dict[str, Any] = hass.data[DOMAIN][entry.entry_id]
    coordinator = runtime["coordinator"]
    zone_count = runtime["zone_count"]
    model = runtime["config"][CONF_MODEL]

    async_add_entities(
        [
            AudacZoneSourceSelect(coordinator, entry.entry_id, model, zone)
            for zone in range(1, zone_count + 1)
        ]
    )


class AudacZoneSourceSelect(AudacCoordinatorEntity, SelectEntity):
    """Zone source select entity."""

    _attr_translation_key = "source"

    def __init__(self, coordinator, entry_id: str, model: str, zone: int) -> None:
        super().__init__(coordinator, entry_id, model)
        self._zone = zone
        self._attr_unique_id = f"{entry_id}_zone_{zone}_source"
        self._attr_name = f"Zone {zone} Source"
        self._id_to_name = DEFAULT_INPUT_LABELS
        self._name_to_id = {v: k for k, v in self._id_to_name.items()}

    @property
    def options(self) -> list[str]:
        options = list(self._id_to_name.values())
        current = self.current_option
        if current and current not in options:
            options.append(current)
        return options

    @property
    def current_option(self) -> str | None:
        zones = (self.coordinator.data or {}).get(STATE_ZONES, {})
        zone = zones.get(self._zone, {})
        src = str(zone.get(ZONE_SOURCE, "0"))
        return self._id_to_name.get(src, f"Input {src}")

    async def async_select_option(self, option: str) -> None:
        source_id = self._name_to_id.get(option)
        if source_id is None:
            raise ValueError(f"Unsupported source option: {option}")
        await self.coordinator.client.async_set_zone_source(self._zone, source_id)
        await self.coordinator.async_request_refresh()
