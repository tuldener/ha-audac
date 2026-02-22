"""Switch entities for Audac."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_MODEL,
    DOMAIN,
    MODEL_XMP44,
    STATE_XMP_SLOTS,
    STATE_ZONES,
    XMP_SLOT_MODULE,
    XMP_SLOT_PAIRING,
    ZONE_MUTE,
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
        entities: list[SwitchEntity] = []
        for slot in range(1, slot_count + 1):
            entities.append(AudacXmpPairingSwitch(coordinator, entry.entry_id, model, slot))
        async_add_entities(entities)
        return

    zone_count = runtime["zone_count"]
    zone_names: dict[int, str] = runtime["zone_names"]

    entities: list[SwitchEntity] = []
    for zone in range(1, zone_count + 1):
        entities.append(
            AudacZoneMuteSwitch(
                coordinator,
                entry.entry_id,
                model,
                zone,
                zone_names.get(zone, f"Zone {zone}"),
            )
        )

    async_add_entities(entities)


class AudacZoneMuteSwitch(AudacCoordinatorEntity, SwitchEntity):
    """Zone mute switch entity."""

    _attr_translation_key = "mute"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self, coordinator, entry_id: str, model: str, zone: int, zone_name: str
    ) -> None:
        super().__init__(coordinator, entry_id, model)
        self._zone = zone
        self._attr_unique_id = f"{entry_id}_zone_{zone}_mute"
        self._attr_name = f"{zone_name} Mute"

    @property
    def is_on(self) -> bool:
        zones = (self.coordinator.data or {}).get(STATE_ZONES, {})
        zone = zones.get(self._zone, {})
        return bool(zone.get(ZONE_MUTE, False))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_set_zone_mute(self._zone, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_set_zone_mute(self._zone, False)
        await self.coordinator.async_request_refresh()


class AudacXmpPairingSwitch(AudacCoordinatorEntity, SwitchEntity):
    """BMP42 pairing enable switch."""

    _attr_translation_key = "mute"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, entry_id: str, model: str, slot: int) -> None:
        super().__init__(coordinator, entry_id, model)
        self._slot = slot
        self._attr_unique_id = f"{entry_id}_slot_{slot}_pairing"
        self._attr_name = f"Slot {slot} Bluetooth Pairing"

    @property
    def available(self) -> bool:
        slots = (self.coordinator.data or {}).get(STATE_XMP_SLOTS, {})
        slot = slots.get(self._slot, {})
        return slot.get(XMP_SLOT_MODULE) == "bmp42"

    @property
    def is_on(self) -> bool:
        slots = (self.coordinator.data or {}).get(STATE_XMP_SLOTS, {})
        slot = slots.get(self._slot, {})
        pairing = str(slot.get(XMP_SLOT_PAIRING, ""))
        return pairing == "3"

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_set_bmp_pairing(self._slot, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_set_bmp_pairing(self._slot, False)
        await self.coordinator.async_request_refresh()
