"""Sensor entities for Audac MTX active source and XMP44 BMP40 Bluetooth."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_MODEL, MODEL_MTX88, MODEL_ZONES, get_source_names, is_xmp_model
from .coordinator import AudacMTXCoordinator
from .entity import AudacMTXBaseEntity
from .helpers import _async_update_zone_visibility

_LOGGER = logging.getLogger(__name__)

PAIRING_STATE_MAP = {
    0: "Erfolgreich",
    1: "Timeout",
    2: "Fehlgeschlagen",
    3: "Aktiv",
    4: "Deaktiviert",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    model = entry.data.get(CONF_MODEL, MODEL_MTX88)

    if is_xmp_model(model):
        await _setup_xmp44_sensors(entry, coordinator, async_add_entities)
    else:
        await _setup_mtx_sensors(hass, entry, coordinator, async_add_entities)


async def _setup_mtx_sensors(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: AudacMTXCoordinator,
    async_add_entities: AddEntitiesCallback,
) -> None:
    model = entry.data.get(CONF_MODEL, MODEL_MTX88)
    zones_count = entry.data.get("zones", MODEL_ZONES.get(model, 8))
    entities = []
    for zone in range(1, zones_count + 1):
        entities.append(AudacMTXSourceSensor(coordinator, zone, entry))
    async_add_entities(entities)
    await _async_update_zone_visibility(hass, entry, zones_count, DOMAIN)


async def _setup_xmp44_sensors(
    entry: ConfigEntry,
    coordinator,
    async_add_entities: AddEntitiesCallback,
) -> None:
    from .xmp44_client import MODULE_BMP40
    slots_count = entry.data.get("slots", 4)
    entities = []

    for slot in range(1, slots_count + 1):
        module_str = entry.options.get(f"slot_{slot}_module", "0")
        try:
            module_type = int(module_str)
        except (ValueError, TypeError):
            module_type = 0

        if module_type == MODULE_BMP40:
            entities.append(BMP40ConnectedDeviceSensor(coordinator, entry, slot))
            entities.append(BMP40PairingStateSensor(coordinator, entry, slot))

    if entities:
        async_add_entities(entities)


class AudacMTXSourceSensor(AudacMTXBaseEntity, SensorEntity):
    _attr_icon = "mdi:audio-input-stereo-minijack"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: AudacMTXCoordinator, zone: int, entry: ConfigEntry) -> None:
        super().__init__(coordinator, zone, entry)
        zone_name = entry.options.get(f"zone_{zone}_name", f"Zone {zone}")
        self._attr_unique_id = f"{entry.entry_id}_zone_{zone}_active_source"
        self._attr_name = f"{zone_name} Active Source"
        self._source_names = get_source_names(entry.options, visible_only=False)

    @property
    def native_value(self) -> str | None:
        data = self._zone_data
        if not data:
            return None
        routing = data.get("routing")
        if routing is None:
            return None
        return self._source_names.get(routing, f"Input {routing}")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self._zone_data
        if not data:
            return {}
        return {
            "routing_id": data.get("routing", 0),
            "volume_raw": data.get("volume", 70),
            "volume_db": data.get("volume_db", -70),
            "mute": data.get("mute", False),
            "bass_db": data.get("bass_db", 0),
            "treble_db": data.get("treble_db", 0),
        }


# ═══════════════════════════════════════════════════════════════════════
# BMP40 Bluetooth Sensors
# ═══════════════════════════════════════════════════════════════════════

class BMP40ConnectedDeviceSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing the currently connected Bluetooth device."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:bluetooth-connect"

    def __init__(self, coordinator, entry: ConfigEntry, slot: int) -> None:
        super().__init__(coordinator)
        self._slot = slot
        self._attr_unique_id = f"{entry.entry_id}_bmp40_slot{slot}_connected_device"
        self._attr_name = "Verbundenes Gerät"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry.entry_id}_slot_{slot}")},
        }

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data
        if not data or self._slot not in data:
            return None
        slot_data = data[self._slot]
        connected = slot_data.get("connected_device")
        if not connected:
            return "Nicht verbunden"
        # Parse: "number^name^address"
        parts = connected.split("^")
        if len(parts) >= 2 and parts[1].strip():
            return parts[1].strip()
        return "Nicht verbunden"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        if not data or self._slot not in data:
            return {}
        slot_data = data[self._slot]
        attrs: dict[str, Any] = {}
        connected = slot_data.get("connected_device")
        if connected:
            parts = connected.split("^")
            if len(parts) >= 3:
                attrs["device_address"] = parts[2].strip()
        bt_info = slot_data.get("bluetooth_info")
        if bt_info:
            attrs["bt_name"] = bt_info.get("name", "")
            attrs["bt_address"] = bt_info.get("address", "")
            attrs["bt_version"] = bt_info.get("version", "")
        return attrs


class BMP40PairingStateSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing the BMP40 Bluetooth pairing state."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:bluetooth-settings"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry: ConfigEntry, slot: int) -> None:
        super().__init__(coordinator)
        self._slot = slot
        self._attr_unique_id = f"{entry.entry_id}_bmp40_slot{slot}_pairing_state"
        self._attr_name = "Pairing Status"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry.entry_id}_slot_{slot}")},
        }

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data
        if not data or self._slot not in data:
            return None
        slot_data = data[self._slot]
        state = slot_data.get("pairing_state")
        if state is None:
            return None
        return PAIRING_STATE_MAP.get(state, f"Unbekannt ({state})")
