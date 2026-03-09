"""Media player entities for Audac MTX zones and XMP44 slots."""
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
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_MODEL, MODEL_MTX88, MODEL_ZONES, get_source_names, is_xmp_model
from .coordinator import AudacMTXCoordinator
from .xmp44_coordinator import XMP44Coordinator
from .xmp44_client import (
    MODULES_WITH_PLAYBACK, MODULES_WITH_SONG_INFO, MODULES_WITH_TUNER,
    MODULE_NAMES, MODULE_DESCRIPTIONS, MODULE_EMPTY, MODULE_UNSUPPORTED, MODULE_BMP40,
)
from .entity import AudacMTXBaseEntity
from .helpers import _async_update_zone_visibility

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    model = entry.data.get(CONF_MODEL, MODEL_MTX88)

    if is_xmp_model(model):
        await _setup_xmp44(hass, entry, coordinator, async_add_entities)
    else:
        await _setup_mtx(hass, entry, coordinator, async_add_entities)


async def _setup_mtx(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: AudacMTXCoordinator,
    async_add_entities: AddEntitiesCallback,
) -> None:
    zones_count = entry.data.get("zones", MODEL_ZONES.get(entry.data.get(CONF_MODEL, MODEL_MTX88), 8))

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


# ═══════════════════════════════════════════════════════════════════════
# XMP44 Slot Entities
# ═══════════════════════════════════════════════════════════════════════

async def _setup_xmp44(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: XMP44Coordinator,
    async_add_entities: AddEntitiesCallback,
) -> None:
    # Wait for first data to know which slots are populated
    if coordinator.data:
        entities = []
        for slot, slot_data in coordinator.data.items():
            entities.append(AudacXMP44Slot(coordinator, slot, entry, slot_data))
        async_add_entities(entities)
    else:
        _LOGGER.warning("XMP44: no slot data available after first refresh")


class AudacXMP44Slot(CoordinatorEntity, MediaPlayerEntity):
    """Media player entity for a single XMP44 module slot."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: XMP44Coordinator,
        slot: int,
        entry: ConfigEntry,
        initial_data: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._slot = slot
        self._entry = entry
        self._module_type = initial_data.get("module_type", MODULE_EMPTY)
        self._module_name = initial_data.get("module_name", f"Slot {slot}")

        self._attr_unique_id = f"{entry.entry_id}_xmp44_slot_{slot}"
        custom_name = entry.options.get(f"slot_{slot}_name")
        self._attr_name = custom_name or f"{self._module_name} (Slot {slot})"

        # Build supported features based on module type
        features = MediaPlayerEntityFeature(0)
        if self._module_type in MODULES_WITH_PLAYBACK:
            features |= (
                MediaPlayerEntityFeature.PLAY
                | MediaPlayerEntityFeature.STOP
                | MediaPlayerEntityFeature.PAUSE
                | MediaPlayerEntityFeature.NEXT_TRACK
                | MediaPlayerEntityFeature.PREVIOUS_TRACK
            )
        self._attr_supported_features = features

    @property
    def _slot_data(self) -> dict[str, Any]:
        if self.coordinator.data and self._slot in self.coordinator.data:
            return self.coordinator.data[self._slot]
        return {}

    @property
    def state(self) -> MediaPlayerState:
        data = self._slot_data
        status = data.get("status", "unknown")
        if status == "playing":
            return MediaPlayerState.PLAYING
        if status == "paused":
            return MediaPlayerState.PAUSED
        if status == "stopped":
            return MediaPlayerState.IDLE
        return MediaPlayerState.ON

    @property
    def media_title(self) -> str | None:
        data = self._slot_data
        song_info = data.get("song_info")
        if song_info:
            return song_info.get("title")
        # For tuners, show program/station name
        return data.get("program_name") or data.get("station_name")

    @property
    def media_artist(self) -> str | None:
        data = self._slot_data
        song_info = data.get("song_info")
        if song_info:
            return song_info.get("artist")
        return None

    @property
    def media_album_name(self) -> str | None:
        data = self._slot_data
        song_info = data.get("song_info")
        if song_info:
            return song_info.get("album")
        return None

    @property
    def media_duration(self) -> int | None:
        data = self._slot_data
        song_info = data.get("song_info")
        if song_info:
            return song_info.get("duration")
        return None

    @property
    def media_position(self) -> int | None:
        data = self._slot_data
        song_info = data.get("song_info")
        if song_info:
            return song_info.get("position")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self._slot_data
        attrs: dict[str, Any] = {
            "slot_number": self._slot,
            "module_type": self._module_type,
            "module_name": self._module_name,
            "module_description": data.get("module_description", ""),
            "output_gain": data.get("output_gain", 0),
        }
        # Tuner attributes
        if "frequency" in data:
            freq = data["frequency"]
            attrs["frequency"] = freq
            attrs["frequency_mhz"] = freq / 100 if freq else None
        if "band" in data:
            attrs["band"] = data["band"]
        if "signal_strength" in data:
            attrs["signal_strength"] = data["signal_strength"]
        if "program_name" in data:
            attrs["program_name"] = data["program_name"]
        # Bluetooth attributes
        if "bluetooth_info" in data:
            attrs["bluetooth_info"] = data["bluetooth_info"]
        if "connected_device" in data:
            attrs["connected_device"] = data["connected_device"]
        # Network player attributes
        if "player_name" in data:
            attrs["player_name"] = data["player_name"]
        # Station name (internet radio)
        if "station_name" in data:
            attrs["station_name"] = data["station_name"]
        return attrs

    # ── Playback controls ───────────────────────────────────────────

    async def async_media_play(self) -> None:
        await self.coordinator.client.play(self._slot)
        await self.coordinator.async_request_refresh()

    async def async_media_stop(self) -> None:
        await self.coordinator.client.stop(self._slot)
        await self.coordinator.async_request_refresh()

    async def async_media_pause(self) -> None:
        await self.coordinator.client.pause(self._slot)
        await self.coordinator.async_request_refresh()

    async def async_media_next_track(self) -> None:
        await self.coordinator.client.next_track(self._slot)
        await self.coordinator.async_request_refresh()

    async def async_media_previous_track(self) -> None:
        await self.coordinator.client.previous_track(self._slot)
        await self.coordinator.async_request_refresh()
