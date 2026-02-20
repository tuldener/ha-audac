"""Switch entities for Audac MTX."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_MODEL, DOMAIN, STATE_ZONES, ZONE_MUTE
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
