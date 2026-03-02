"""Media player entities for Audac MTX zones."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, INPUT_NAMES, BASS_TREBLE_MAP
from .coordinator import AudacMTXCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AudacMTXCoordinator = hass.data[DOMAIN][entry.entry_id]
    zones_count = entry.data.get("zones", 8)

    entities = [
        AudacMTXZone(coordinator, zone, entry)
        for zone in range(1, zones_count + 1)
    ]
    async_add_entities(entities)


class AudacMTXZone(CoordinatorEntity[AudacMTXCoordinator], MediaPlayerEntity):
    _attr_has_entity_name = True
    _attr_supported_features = (
        MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.SELECT_SOURCE
    )

    def __init__(
        self,
        coordinator: AudacMTXCoordinator,
        zone: int,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._zone = zone
        self._attr_unique_id = f"{entry.entry_id}_zone_{zone}"
        self._attr_name = f"Zone {zone}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.data.get("name", "Audac MTX"),
            "manufacturer": "Audac",
            "model": "MTX",
        }
        self._attr_source_list = list(INPUT_NAMES.values())

    @property
    def _zone_data(self) -> dict[str, Any]:
        if self.coordinator.data and self._zone in self.coordinator.data:
            return self.coordinator.data[self._zone]
        return {}

    @property
    def state(self) -> MediaPlayerState:
        data = self._zone_data
        if not data:
            return MediaPlayerState.OFF
        if data.get("mute"):
            return MediaPlayerState.IDLE
        return MediaPlayerState.ON

    @property
    def volume_level(self) -> float | None:
        data = self._zone_data
        if not data:
            return None
        volume_raw = data.get("volume", 70)
        return 1.0 - (volume_raw / 70.0)

    @property
    def is_volume_muted(self) -> bool | None:
        data = self._zone_data
        if not data:
            return None
        return data.get("mute", False)

    @property
    def source(self) -> str | None:
        data = self._zone_data
        if not data:
            return None
        return data.get("source_name")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self._zone_data
        if not data:
            return {}
        return {
            "bass": data.get("bass_db", 0),
            "treble": data.get("treble_db", 0),
            "bass_raw": data.get("bass", 7),
            "treble_raw": data.get("treble", 7),
            "volume_db": data.get("volume_db", -70),
            "routing": data.get("routing", 0),
        }

    async def async_set_volume_level(self, volume: float) -> None:
        volume_raw = int((1.0 - volume) * 70)
        await self.coordinator.client.set_volume(self._zone, volume_raw)
        await self.coordinator.async_request_refresh()

    async def async_volume_up(self) -> None:
        await self.coordinator.client.set_volume_up(self._zone)
        await self.coordinator.async_request_refresh()

    async def async_volume_down(self) -> None:
        await self.coordinator.client.set_volume_down(self._zone)
        await self.coordinator.async_request_refresh()

    async def async_mute_volume(self, mute: bool) -> None:
        await self.coordinator.client.set_mute(self._zone, mute)
        await self.coordinator.async_request_refresh()

    async def async_select_source(self, source: str) -> None:
        for input_id, name in INPUT_NAMES.items():
            if name == source:
                await self.coordinator.client.set_routing(self._zone, input_id)
                await self.coordinator.async_request_refresh()
                return
