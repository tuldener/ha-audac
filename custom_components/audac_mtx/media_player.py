"""Media player entities for Audac MTX zones."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_MODEL, MODEL_MTX88, MODEL_ZONES, get_source_names
from .coordinator import AudacMTXCoordinator
from .entity import AudacMTXBaseEntity
from .helpers import _async_update_zone_visibility

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
        entities.append(AudacMTXZone(coordinator, zone, entry))
    async_add_entities(entities)
    await _async_update_zone_visibility(hass, entry, zones_count, DOMAIN)

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        "set_bass",
        {vol.Required("bass"): vol.All(int, vol.Range(min=0, max=14))},
        "async_set_bass",
    )
    platform.async_register_entity_service(
        "set_treble",
        {vol.Required("treble"): vol.All(int, vol.Range(min=0, max=14))},
        "async_set_treble",
    )
    platform.async_register_entity_service(
        "routing_up",
        {},
        "async_routing_up",
    )
    platform.async_register_entity_service(
        "routing_down",
        {},
        "async_routing_down",
    )


class AudacMTXZone(AudacMTXBaseEntity, MediaPlayerEntity):
    _attr_supported_features = (
        MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.SELECT_SOURCE
    )

    def __init__(self, coordinator: AudacMTXCoordinator, zone: int, entry: ConfigEntry) -> None:
        super().__init__(coordinator, zone, entry)
        self._attr_unique_id = f"{entry.entry_id}_zone_{zone}"
        self._attr_name = entry.options.get(f"zone_{zone}_name", f"Zone {zone}")
        self._source_names = get_source_names(entry.options)
        self._attr_source_list = list(self._source_names.values())

    def _get_slave_zones(self) -> list[int]:
        """Return zone numbers that are linked/slaved to this master zone.

        Supports three formats for backward compatibility:
        - zone_z_link: str   (current: dropdown, "0" = no link)
        - zone_z_links: List[str]  (old: checkbox multi-select)
        - zone_z_linked_to: int    (legacy)
        """
        from .const import MODEL_MTX88, MODEL_ZONES, CONF_MODEL
        model = self._entry.data.get(CONF_MODEL, MODEL_MTX88)
        zones_count = self._entry.data.get("zones", MODEL_ZONES.get(model, 8))
        result = []
        for z in range(1, zones_count + 1):
            if z == self._zone:
                continue
            # Current format: single string from dropdown
            link = self._entry.options.get(f"zone_{z}_link")
            if link is not None:
                try:
                    if int(link) == self._zone:
                        result.append(z)
                except (ValueError, TypeError):
                    pass
                continue
            # Old format: list of zone-number strings
            links = self._entry.options.get(f"zone_{z}_links")
            if links is not None:
                if str(self._zone) in links:
                    result.append(z)
                continue
            # Legacy format: integer
            if self._entry.options.get(f"zone_{z}_linked_to", 0) == self._zone:
                result.append(z)
        return result

    async def _mirror_to_slaves(self, coro_factory) -> None:
        """Send the same command to all slave zones linked to this master."""
        for slave_zone in self._get_slave_zones():
            await coro_factory(slave_zone)

    def _get_linked_to(self) -> int:
        """Return the master zone number this zone is linked to, or 0."""
        # Current format: single string from dropdown
        link = self._entry.options.get(f"zone_{self._zone}_link")
        if link is not None:
            try:
                return int(link)
            except (ValueError, TypeError):
                return 0
        # Old format: list of zone-number strings
        links = self._entry.options.get(f"zone_{self._zone}_links")
        if links and isinstance(links, list) and len(links) > 0:
            try:
                return int(links[0])
            except (ValueError, TypeError):
                return 0
        # Legacy format: integer
        return self._entry.options.get(f"zone_{self._zone}_linked_to", 0)

    @property
    def state(self) -> MediaPlayerState:
        data = self._zone_data
        if not data:
            return MediaPlayerState.OFF
        if data.get("routing", 0) == 0:
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
        routing = data.get("routing", 0)
        return self._source_names.get(routing, f"Input {routing}")

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
            "zone_number": self._zone,
            "zone_visible": self._entry.options.get(f"zone_{self._zone}_visible", True),
            "linked_to": self._get_linked_to(),
            "linked_zones": self._get_slave_zones(),
        }

    async def async_set_volume_level(self, volume: float) -> None:
        volume_raw = int((1.0 - volume) * 70)
        await self.coordinator.client.set_volume(self._zone, volume_raw)
        await self._mirror_to_slaves(lambda z: self.coordinator.client.set_volume(z, volume_raw))
        await self.coordinator.async_request_refresh()

    async def async_volume_up(self) -> None:
        await self.coordinator.client.set_volume_up(self._zone)
        await self._mirror_to_slaves(lambda z: self.coordinator.client.set_volume_up(z))
        await self.coordinator.async_request_refresh()

    async def async_volume_down(self) -> None:
        await self.coordinator.client.set_volume_down(self._zone)
        await self._mirror_to_slaves(lambda z: self.coordinator.client.set_volume_down(z))
        await self.coordinator.async_request_refresh()

    async def async_mute_volume(self, mute: bool) -> None:
        await self.coordinator.client.set_mute(self._zone, mute)
        await self._mirror_to_slaves(lambda z: self.coordinator.client.set_mute(z, mute))
        await self.coordinator.async_request_refresh()

    async def async_select_source(self, source: str) -> None:
        for input_id, name in self._source_names.items():
            if name == source:
                await self.coordinator.client.set_routing(self._zone, input_id)
                await self._mirror_to_slaves(lambda z: self.coordinator.client.set_routing(z, input_id))
                await self.coordinator.async_request_refresh()
                return

    async def async_set_bass(self, bass: int) -> None:
        await self.coordinator.client.set_bass(self._zone, bass)
        await self._mirror_to_slaves(lambda z: self.coordinator.client.set_bass(z, bass))
        await self.coordinator.async_request_refresh()

    async def async_set_treble(self, treble: int) -> None:
        await self.coordinator.client.set_treble(self._zone, treble)
        await self._mirror_to_slaves(lambda z: self.coordinator.client.set_treble(z, treble))
        await self.coordinator.async_request_refresh()

    async def async_routing_up(self) -> None:
        """Cycle to next available input source (skips disabled inputs on device)."""
        await self.coordinator.client.set_routing_up(self._zone)
        await self._mirror_to_slaves(lambda z: self.coordinator.client.set_routing_up(z))
        await self.coordinator.async_request_refresh()

    async def async_routing_down(self) -> None:
        """Cycle to previous available input source (skips disabled inputs on device)."""
        await self.coordinator.client.set_routing_down(self._zone)
        await self.coordinator.async_request_refresh()
