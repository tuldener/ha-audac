"""Number entities for Audac."""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_MODEL,
    DOMAIN,
    MODEL_XMP44,
    STATE_XMP_SLOTS,
    STATE_ZONES,
    XMP_SLOT_GAIN,
    ZONE_VOLUME,
)
from .entity import AudacCoordinatorEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime: dict[str, Any] = hass.data[DOMAIN][entry.entry_id]
    coordinator = runtime["coordinator"]
    model = runtime["config"][CONF_MODEL]

    if model == MODEL_XMP44:
        slot_count = runtime["slot_count"]
        async_add_entities(
            [
                AudacXmpSlotGainNumber(coordinator, entry.entry_id, model, slot)
                for slot in range(1, slot_count + 1)
            ]
        )
        return

    zone_count = runtime["zone_count"]
    zone_names: dict[int, str] = runtime["zone_names"]

    async_add_entities(
        [
            AudacZoneVolumeNumber(
                coordinator,
                entry.entry_id,
                model,
                zone,
                zone_names.get(zone, f"Zone {zone}"),
            )
            for zone in range(1, zone_count + 1)
        ]
    )


class AudacZoneVolumeNumber(AudacCoordinatorEntity, NumberEntity):
    """MTX zone volume control entity."""

    _attr_translation_key = "volume"
    _attr_native_min_value = 0
    _attr_native_max_value = 70
    _attr_native_step = 1
    _attr_mode = "slider"

    def __init__(
        self, coordinator, entry_id: str, model: str, zone: int, zone_name: str
    ) -> None:
        super().__init__(coordinator, entry_id, model)
        self._zone = zone
        self._attr_unique_id = f"{entry_id}_zone_{zone}_volume"
        self._attr_name = f"{zone_name} Volume (dB attenuation)"

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


class AudacXmpSlotGainNumber(AudacCoordinatorEntity, NumberEntity):
    """XMP slot output gain argument entity."""

    _attr_translation_key = "volume"
    _attr_native_min_value = 0
    _attr_native_max_value = 80
    _attr_native_step = 1
    _attr_mode = "slider"

    def __init__(self, coordinator, entry_id: str, model: str, slot: int) -> None:
        super().__init__(coordinator, entry_id, model)
        self._slot = slot
        self._attr_unique_id = f"{entry_id}_slot_{slot}_gain"
        self._attr_name = f"Slot {slot} Output Gain (arg)"

    @property
    def native_value(self) -> float | None:
        slots = (self.coordinator.data or {}).get(STATE_XMP_SLOTS, {})
        slot = slots.get(self._slot, {})
        raw = slot.get(XMP_SLOT_GAIN)
        if raw is None:
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.client.async_set_slot_gain(self._slot, int(round(value)))
        await self.coordinator.async_request_refresh()
