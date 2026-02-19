"""Number entities for Audac MTX."""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_MODEL, DOMAIN, STATE_ZONES, ZONE_VOLUME
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
            AudacZoneVolumeNumber(coordinator, entry.entry_id, model, zone)
            for zone in range(1, zone_count + 1)
        ]
    )


class AudacZoneVolumeNumber(AudacCoordinatorEntity, NumberEntity):
    """Zone volume control entity."""

    _attr_translation_key = "volume"
    _attr_native_min_value = 0
    _attr_native_max_value = 70
    _attr_native_step = 1
    _attr_mode = "slider"

    def __init__(self, coordinator, entry_id: str, model: str, zone: int) -> None:
        super().__init__(coordinator, entry_id, model)
        self._zone = zone
        self._attr_unique_id = f"{entry_id}_zone_{zone}_volume"
        self._attr_name = f"Zone {zone} Volume (dB attenuation)"

    @property
    def native_value(self) -> float | None:
        zones = (self.coordinator.data or {}).get(STATE_ZONES, {})
        zone = zones.get(self._zone, {})
        raw = zone.get(ZONE_VOLUME)
        if raw is None:
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.client.async_set_zone_volume(self._zone, int(round(value)))
        await self.coordinator.async_request_refresh()
