"""Sensor entities for Audac."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_MODEL,
    DOMAIN,
    MODEL_XMP44,
    STATE_FIRMWARE,
    STATE_XMP_SLOTS,
    XMP_SLOT_INFO,
    XMP_SLOT_MODULE,
    XMP_SLOT_PLAYER_STATUS,
    XMP_SLOT_PROGRAM,
    XMP_SLOT_SONG,
    XMP_SLOT_STATION,
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
        entities: list[SensorEntity] = []
        for slot in range(1, slot_count + 1):
            entities.extend(
                [
                    AudacXmpSlotModuleSensor(coordinator, entry.entry_id, model, slot),
                    AudacXmpSlotSongSensor(coordinator, entry.entry_id, model, slot),
                    AudacXmpSlotStationSensor(coordinator, entry.entry_id, model, slot),
                    AudacXmpSlotProgramSensor(coordinator, entry.entry_id, model, slot),
                    AudacXmpSlotStatusSensor(coordinator, entry.entry_id, model, slot),
                    AudacXmpSlotInfoSensor(coordinator, entry.entry_id, model, slot),
                ]
            )
        async_add_entities(entities)
        return

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


class _AudacXmpSlotSensor(AudacCoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id: str, model: str, slot: int) -> None:
        super().__init__(coordinator, entry_id, model)
        self._slot = slot

    def _slot_data(self) -> dict[str, Any]:
        slots = (self.coordinator.data or {}).get(STATE_XMP_SLOTS, {})
        return slots.get(self._slot, {})


class AudacXmpSlotModuleSensor(_AudacXmpSlotSensor):
    def __init__(self, coordinator, entry_id: str, model: str, slot: int) -> None:
        super().__init__(coordinator, entry_id, model, slot)
        self._attr_unique_id = f"{entry_id}_slot_{slot}_module"
        self._attr_name = f"Slot {slot} Module"

    @property
    def native_value(self) -> str | None:
        return self._slot_data().get(XMP_SLOT_MODULE)


class AudacXmpSlotSongSensor(_AudacXmpSlotSensor):
    def __init__(self, coordinator, entry_id: str, model: str, slot: int) -> None:
        super().__init__(coordinator, entry_id, model, slot)
        self._attr_unique_id = f"{entry_id}_slot_{slot}_song"
        self._attr_name = f"Slot {slot} Song"

    @property
    def native_value(self) -> str | None:
        return self._slot_data().get(XMP_SLOT_SONG)


class AudacXmpSlotStationSensor(_AudacXmpSlotSensor):
    def __init__(self, coordinator, entry_id: str, model: str, slot: int) -> None:
        super().__init__(coordinator, entry_id, model, slot)
        self._attr_unique_id = f"{entry_id}_slot_{slot}_station"
        self._attr_name = f"Slot {slot} Station"

    @property
    def native_value(self) -> str | None:
        return self._slot_data().get(XMP_SLOT_STATION)


class AudacXmpSlotProgramSensor(_AudacXmpSlotSensor):
    def __init__(self, coordinator, entry_id: str, model: str, slot: int) -> None:
        super().__init__(coordinator, entry_id, model, slot)
        self._attr_unique_id = f"{entry_id}_slot_{slot}_program"
        self._attr_name = f"Slot {slot} Program"

    @property
    def native_value(self) -> str | None:
        return self._slot_data().get(XMP_SLOT_PROGRAM)


class AudacXmpSlotStatusSensor(_AudacXmpSlotSensor):
    def __init__(self, coordinator, entry_id: str, model: str, slot: int) -> None:
        super().__init__(coordinator, entry_id, model, slot)
        self._attr_unique_id = f"{entry_id}_slot_{slot}_status"
        self._attr_name = f"Slot {slot} Player Status"

    @property
    def native_value(self) -> str | None:
        return self._slot_data().get(XMP_SLOT_PLAYER_STATUS)


class AudacXmpSlotInfoSensor(_AudacXmpSlotSensor):
    def __init__(self, coordinator, entry_id: str, model: str, slot: int) -> None:
        super().__init__(coordinator, entry_id, model, slot)
        self._attr_unique_id = f"{entry_id}_slot_{slot}_info"
        self._attr_name = f"Slot {slot} Module Info"
        self._attr_entity_registry_enabled_default = False

    @property
    def native_value(self) -> str | None:
        return self._slot_data().get(XMP_SLOT_INFO)
