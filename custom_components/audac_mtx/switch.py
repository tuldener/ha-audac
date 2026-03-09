"""Switch entities for Audac MTX zone mute and XMP44 BMP40 pairing."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_MODEL, MODEL_MTX88, MODEL_ZONES, is_xmp_model
from .coordinator import AudacMTXCoordinator
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
        await _setup_xmp44_switches(hass, entry, coordinator, async_add_entities)
    else:
        await _setup_mtx_switches(hass, entry, coordinator, async_add_entities)


async def _setup_mtx_switches(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: AudacMTXCoordinator,
    async_add_entities: AddEntitiesCallback,
) -> None:
    model = entry.data.get(CONF_MODEL, MODEL_MTX88)
    zones_count = entry.data.get("zones", MODEL_ZONES.get(model, 8))
    entities = []
    for zone in range(1, zones_count + 1):
        entities.append(AudacMTXMuteSwitch(coordinator, zone, entry))
    async_add_entities(entities)
    await _async_update_zone_visibility(hass, entry, zones_count, DOMAIN)


async def _setup_xmp44_switches(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator,
    async_add_entities: AddEntitiesCallback,
) -> None:
    from .xmp44_client import MODULE_BMP40, MODULE_DMP40, MODULE_TMP40, MODULE_MMP40, MODULES_WITH_TUNER
    slots_count = entry.data.get("slots", 4)
    entities = []

    for slot in range(1, slots_count + 1):
        module_str = entry.options.get(f"slot_{slot}_module", "0")
        try:
            module_type = int(module_str)
        except (ValueError, TypeError):
            module_type = 0

        if module_type == MODULE_BMP40:
            entities.append(BMP40PairingSwitch(coordinator, entry, slot))

        if module_type in MODULES_WITH_TUNER:
            entities.append(TunerStereoSwitch(coordinator, entry, slot))

        if module_type == MODULE_MMP40:
            entities.append(MMP40RecorderModeSwitch(coordinator, entry, slot))

    if entities:
        async_add_entities(entities)


class AudacMTXMuteSwitch(AudacMTXBaseEntity, SwitchEntity):
    _attr_icon = "mdi:volume-off"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: AudacMTXCoordinator, zone: int, entry: ConfigEntry) -> None:
        super().__init__(coordinator, zone, entry)
        zone_name = entry.options.get(f"zone_{zone}_name", f"Zone {zone}")
        self._attr_unique_id = f"{entry.entry_id}_zone_{zone}_mute"
        self._attr_name = f"{zone_name} Mute"

    @property
    def is_on(self) -> bool | None:
        data = self._zone_data
        if not data:
            return None
        return data.get("mute", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.client.set_mute(self._zone, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.set_mute(self._zone, False)
        await self.coordinator.async_request_refresh()


# ═══════════════════════════════════════════════════════════════════════
# BMP40 Bluetooth Pairing Switch
# ═══════════════════════════════════════════════════════════════════════

class BMP40PairingSwitch(CoordinatorEntity, SwitchEntity):
    """Switch to enable/disable BMP40 Bluetooth pairing mode."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:bluetooth-settings"

    def __init__(self, coordinator, entry: ConfigEntry, slot: int) -> None:
        super().__init__(coordinator)
        self._slot = slot
        self._entry = entry

        self._attr_unique_id = f"{entry.entry_id}_bmp40_slot{slot}_pairing"
        self._attr_name = "Pairing"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry.entry_id}_slot_{slot}")},
        }

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        if not data or self._slot not in data:
            return None
        slot_data = data[self._slot]
        # Pairing state: 3=enabled, 4=disabled, 0=success
        pairing = slot_data.get("pairing_state")
        if pairing is None:
            return None
        return pairing == 3  # enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.client.set_pairing(self._slot, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.set_pairing(self._slot, False)
        await self.coordinator.async_request_refresh()


# ═══════════════════════════════════════════════════════════════════════
# DMP40/TMP40 Stereo Switch
# ═══════════════════════════════════════════════════════════════════════

class TunerStereoSwitch(CoordinatorEntity, SwitchEntity):
    """Switch to toggle stereo/mono output for DMP40/TMP40 tuners."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:surround-sound"

    def __init__(self, coordinator, entry: ConfigEntry, slot: int) -> None:
        super().__init__(coordinator)
        self._slot = slot
        self._attr_unique_id = f"{entry.entry_id}_tuner_slot{slot}_stereo"
        self._attr_name = "Stereo"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry.entry_id}_slot_{slot}")},
        }

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        if not data or self._slot not in data:
            return None
        return data[self._slot].get("stereo")

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.client.set_stereo(self._slot, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.set_stereo(self._slot, False)
        await self.coordinator.async_request_refresh()


# ═══════════════════════════════════════════════════════════════════════
# MMP40 Recorder Mode Switch
# ═══════════════════════════════════════════════════════════════════════

class MMP40RecorderModeSwitch(CoordinatorEntity, SwitchEntity):
    """Switch to toggle between player and recorder mode on MMP40."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:microphone"

    def __init__(self, coordinator, entry: ConfigEntry, slot: int) -> None:
        super().__init__(coordinator)
        self._slot = slot
        self._attr_unique_id = f"{entry.entry_id}_mmp40_slot{slot}_recorder"
        self._attr_name = "Aufnahme-Modus"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry.entry_id}_slot_{slot}")},
        }

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        if not data or self._slot not in data:
            return None
        mode = data[self._slot].get("recorder_mode")
        if mode is None:
            return None
        return mode == "recorder"

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.client.set_recorder_mode(self._slot, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.set_recorder_mode(self._slot, False)
        await self.coordinator.async_request_refresh()
