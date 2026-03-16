"""Button entities for Audac XMP44 modules (FMP40 triggers, IMP40 stations)."""
from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_MODEL, MODEL_MTX88, MODEL_ZONES, is_xmp_model
from .xmp44_coordinator import XMP44Coordinator
from .xmp44_client import MODULE_FMP40, MODULE_IMP40, MODULE_BMP40, MODULE_DMP40, MODULE_TMP40, MODULE_MMP40, MODULES_WITH_TUNER

_LOGGER = logging.getLogger(__name__)

# Regex for the NEW unique_id format: ..._imp40_slotN_station_{pointer}_{safe_name}
_IMP40_NEW_UID = re.compile(r"_imp40_slot\d+_station_\d+_")
# Regex for ANY IMP40 station unique_id
_IMP40_ANY_UID = re.compile(r"_imp40_slot\d+_station_")


async def _cleanup_legacy_imp40_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove IMP40 station entities that use the old unique_id format (without pointer).

    Old format: {entry_id}_imp40_slot{N}_station_{safe_name}
    New format: {entry_id}_imp40_slot{N}_station_{pointer}_{safe_name}
    """
    ent_reg = er.async_get(hass)
    removed = 0

    for ent_entry in list(ent_reg.entities.values()):
        if ent_entry.config_entry_id != entry.entry_id:
            continue
        uid = ent_entry.unique_id or ""
        # Must be an IMP40 station entity ...
        if not _IMP40_ANY_UID.search(uid):
            continue
        # ... but NOT in the new format (with pointer)
        if _IMP40_NEW_UID.search(uid):
            continue
        # This is an old-format entity — remove it
        _LOGGER.info("Removing legacy IMP40 station entity: %s (uid=%s)", ent_entry.entity_id, uid)
        ent_reg.async_remove(ent_entry.entity_id)
        removed += 1

    if removed:
        _LOGGER.info("Cleaned up %d legacy IMP40 station entities", removed)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    model = entry.data.get(CONF_MODEL, MODEL_MTX88)
    coordinator = hass.data[DOMAIN][entry.entry_id]

    if is_xmp_model(model):
        await _setup_xmp44_buttons(hass, entry, coordinator, async_add_entities)
    else:
        await _setup_mtx_buttons(hass, entry, coordinator, async_add_entities)


async def _setup_mtx_buttons(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create MTX-specific buttons: Save, Volume Up/Down per zone."""
    from .entity import AudacMTXBaseEntity
    zones_count = entry.data.get("zones", MODEL_ZONES.get(entry.data.get(CONF_MODEL, MODEL_MTX88), 8))

    entities: list[ButtonEntity] = []

    # Save button (one per device)
    entities.append(MTXSaveButton(coordinator, entry))

    # Volume Up/Down per zone
    for zone in range(1, zones_count + 1):
        entities.append(MTXVolumeUpButton(coordinator, zone, entry))
        entities.append(MTXVolumeDownButton(coordinator, zone, entry))

    if entities:
        async_add_entities(entities)


async def _setup_xmp44_buttons(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: XMP44Coordinator,
    async_add_entities: AddEntitiesCallback,
) -> None:
    slots_count = entry.data.get("slots", 4)

    # Clean up old IMP40 station entities that used the legacy unique_id format
    # (without pointer). Old: ..._station_{safe_name}, New: ..._station_{pointer}_{safe_name}
    await _cleanup_legacy_imp40_entities(hass, entry)

    entities: list[ButtonEntity] = []

    for slot in range(1, slots_count + 1):
        module_str = entry.options.get(f"slot_{slot}_module", "0")
        try:
            module_type = int(module_str)
        except (ValueError, TypeError):
            module_type = 0

        # FMP40: Trigger buttons
        if module_type == MODULE_FMP40:
            _setup_fmp40_buttons(entities, coordinator, entry, slot)

        # IMP40: Station buttons from cached favourites
        if module_type == MODULE_IMP40:
            _setup_imp40_buttons(entities, coordinator, entry, slot)

        # BMP40: Disconnect button
        if module_type == MODULE_BMP40:
            entities.append(BMP40DisconnectButton(coordinator, entry, slot))

        # DMP40/TMP40: Search up/down, band switch (DMP40 only), preset buttons
        if module_type in MODULES_WITH_TUNER:
            entities.append(TunerSearchUpButton(coordinator, entry, slot))
            entities.append(TunerSearchDownButton(coordinator, entry, slot))
            for preset in range(1, 11):
                entities.append(TunerPresetButton(coordinator, entry, slot, preset))
            if module_type == MODULE_DMP40:
                entities.append(TunerBandSwitchButton(coordinator, entry, slot))

        # MMP40: Transport + Recording + Repeat/Random buttons
        if module_type == MODULE_MMP40:
            entities.append(MMP40GoToStartButton(coordinator, entry, slot))
            entities.append(MMP40FastForwardButton(coordinator, entry, slot))
            entities.append(MMP40FastRewindButton(coordinator, entry, slot))
            entities.append(MMP40StartRecordingButton(coordinator, entry, slot))
            entities.append(MMP40StopRecordingButton(coordinator, entry, slot))
            entities.append(MMP40PauseRecordingButton(coordinator, entry, slot))
            entities.append(MMP40CancelRecordingButton(coordinator, entry, slot))
            entities.append(MMP40RandomOnButton(coordinator, entry, slot))
            entities.append(MMP40RandomOffButton(coordinator, entry, slot))
            entities.append(MMP40RepeatOneButton(coordinator, entry, slot))
            entities.append(MMP40RepeatAllButton(coordinator, entry, slot))
            entities.append(MMP40RepeatFolderButton(coordinator, entry, slot))
            entities.append(MMP40RepeatOffButton(coordinator, entry, slot))

    if entities:
        async_add_entities(entities)
        _LOGGER.debug("Created %d XMP44 buttons", len(entities))


def _setup_fmp40_buttons(
    entities: list[ButtonEntity],
    coordinator: XMP44Coordinator,
    entry: ConfigEntry,
    slot: int,
) -> None:
    trigger_count = entry.options.get(f"slot_{slot}_triggers", 0)
    try:
        trigger_count = int(trigger_count)
    except (ValueError, TypeError):
        trigger_count = 0

    if trigger_count <= 0:
        return

    for trigger in range(1, trigger_count + 1):
        trigger_name = entry.options.get(f"slot_{slot}_trigger_{trigger}_name", f"Trigger {trigger}")
        entities.append(FMP40TriggerStartButton(coordinator, entry, slot, trigger, trigger_name))
        entities.append(FMP40TriggerStopButton(coordinator, entry, slot, trigger, trigger_name))


def _setup_imp40_buttons(
    entities: list[ButtonEntity],
    coordinator: XMP44Coordinator,
    entry: ConfigEntry,
    slot: int,
) -> None:
    favs = coordinator.favourites.get(slot, [])
    if not favs:
        _LOGGER.debug("IMP40 slot %d: no favourites loaded yet, skipping buttons", slot)
        return

    seen_pointers: set[str] = set()
    for fav in favs:
        name = fav.get("name", "")
        pointer = fav.get("pointer", "")
        if name and pointer and pointer not in seen_pointers:
            seen_pointers.add(pointer)
            entities.append(IMP40StationButton(coordinator, entry, slot, name, pointer))


class FMP40TriggerStartButton(CoordinatorEntity, ButtonEntity):
    """Button to start an FMP40 voice file trigger."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:play-circle"

    def __init__(
        self,
        coordinator: XMP44Coordinator,
        entry: ConfigEntry,
        slot: int,
        trigger: int,
        trigger_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._slot = slot
        self._trigger = trigger
        self._entry = entry

        self._attr_unique_id = f"{entry.entry_id}_fmp40_slot{slot}_trigger{trigger}_start"
        self._attr_name = trigger_name
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry.entry_id}_slot_{slot}")},
        }
        self._attr_extra_state_attributes = {"slot_number": slot, "trigger_number": trigger}

    async def async_press(self) -> None:
        """Start the trigger."""
        await self.coordinator.client.trigger_start(self._slot, self._trigger)


class FMP40TriggerStopButton(CoordinatorEntity, ButtonEntity):
    """Button to stop an FMP40 voice file trigger."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:stop-circle"

    def __init__(
        self,
        coordinator: XMP44Coordinator,
        entry: ConfigEntry,
        slot: int,
        trigger: int,
        trigger_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._slot = slot
        self._trigger = trigger
        self._entry = entry

        self._attr_unique_id = f"{entry.entry_id}_fmp40_slot{slot}_trigger{trigger}_stop"
        self._attr_name = f"{trigger_name} Stop"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry.entry_id}_slot_{slot}")},
        }
        self._attr_extra_state_attributes = {"slot_number": slot, "trigger_number": trigger}

    async def async_press(self) -> None:
        """Stop the trigger."""
        await self.coordinator.client.trigger_stop(self._slot, self._trigger)


# ═══════════════════════════════════════════════════════════════════════
# IMP40 Internet Radio Station Buttons
# ═══════════════════════════════════════════════════════════════════════

class IMP40StationButton(CoordinatorEntity, ButtonEntity):
    """Button to select an IMP40 internet radio station."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:radio"

    def __init__(
        self,
        coordinator: XMP44Coordinator,
        entry: ConfigEntry,
        slot: int,
        station_name: str,
        pointer: str,
    ) -> None:
        super().__init__(coordinator)
        self._slot = slot
        self._pointer = int(pointer)
        self._entry = entry

        # Sanitize station name for unique_id (keep alphanumeric + underscore)
        safe_name = "".join(c if c.isalnum() else "_" for c in station_name.lower()).strip("_")
        self._attr_unique_id = f"{entry.entry_id}_imp40_slot{slot}_station_{pointer}_{safe_name}"
        self._attr_name = station_name
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry.entry_id}_slot_{slot}")},
        }
        self._attr_extra_state_attributes = {"slot_number": slot, "station_pointer": self._pointer}

    async def async_press(self) -> None:
        """Select this station."""
        await self.coordinator.client.select_station(self._slot, self._pointer)
        await self.coordinator.async_request_refresh()


# ═══════════════════════════════════════════════════════════════════════
# BMP40 Bluetooth Disconnect Button
# ═══════════════════════════════════════════════════════════════════════

class BMP40DisconnectButton(CoordinatorEntity, ButtonEntity):
    """Button to disconnect the currently connected Bluetooth device."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:bluetooth-off"

    def __init__(
        self,
        coordinator: XMP44Coordinator,
        entry: ConfigEntry,
        slot: int,
    ) -> None:
        super().__init__(coordinator)
        self._slot = slot
        self._entry = entry

        self._attr_unique_id = f"{entry.entry_id}_bmp40_slot{slot}_disconnect"
        self._attr_name = "Disconnect"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry.entry_id}_slot_{slot}")},
        }
        self._attr_extra_state_attributes = {"slot_number": slot}

    async def async_press(self) -> None:
        """Disconnect the currently connected device."""
        await self.coordinator.client.disconnect_device(self._slot)
        await self.coordinator.async_request_refresh()


# ═══════════════════════════════════════════════════════════════════════
# DMP40/TMP40 Tuner Buttons
# ═══════════════════════════════════════════════════════════════════════

class TunerSearchUpButton(CoordinatorEntity, ButtonEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:magnify-plus-outline"

    def __init__(self, coordinator, entry: ConfigEntry, slot: int) -> None:
        super().__init__(coordinator)
        self._slot = slot
        self._attr_unique_id = f"{entry.entry_id}_tuner_slot{slot}_search_up"
        self._attr_name = "Sendersuche +"
        self._attr_device_info = {"identifiers": {(DOMAIN, f"{entry.entry_id}_slot_{slot}")}}
        self._attr_extra_state_attributes = {"slot_number": slot}

    async def async_press(self) -> None:
        await self.coordinator.client.search_up(self._slot)
        await self.coordinator.async_request_refresh()


class TunerSearchDownButton(CoordinatorEntity, ButtonEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:magnify-minus-outline"

    def __init__(self, coordinator, entry: ConfigEntry, slot: int) -> None:
        super().__init__(coordinator)
        self._slot = slot
        self._attr_unique_id = f"{entry.entry_id}_tuner_slot{slot}_search_down"
        self._attr_name = "Sendersuche -"
        self._attr_device_info = {"identifiers": {(DOMAIN, f"{entry.entry_id}_slot_{slot}")}}
        self._attr_extra_state_attributes = {"slot_number": slot}

    async def async_press(self) -> None:
        await self.coordinator.client.search_down(self._slot)
        await self.coordinator.async_request_refresh()


class TunerBandSwitchButton(CoordinatorEntity, ButtonEntity):
    """Toggle between FM and DAB (DMP40 only)."""
    _attr_has_entity_name = True
    _attr_icon = "mdi:swap-horizontal"

    def __init__(self, coordinator, entry: ConfigEntry, slot: int) -> None:
        super().__init__(coordinator)
        self._slot = slot
        self._attr_unique_id = f"{entry.entry_id}_tuner_slot{slot}_band_switch"
        self._attr_name = "DAB/FM Umschalten"
        self._attr_device_info = {"identifiers": {(DOMAIN, f"{entry.entry_id}_slot_{slot}")}}
        self._attr_extra_state_attributes = {"slot_number": slot}

    async def async_press(self) -> None:
        await self.coordinator.client.switch_band(self._slot)
        await self.coordinator.async_request_refresh()


class TunerPresetButton(CoordinatorEntity, ButtonEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:radio"

    def __init__(self, coordinator, entry: ConfigEntry, slot: int, preset: int) -> None:
        super().__init__(coordinator)
        self._slot = slot
        self._preset = preset
        self._attr_unique_id = f"{entry.entry_id}_tuner_slot{slot}_preset_{preset}"
        self._attr_name = f"Preset {preset}"
        self._attr_device_info = {"identifiers": {(DOMAIN, f"{entry.entry_id}_slot_{slot}")}}
        self._attr_extra_state_attributes = {"slot_number": slot, "preset_number": preset}

    async def async_press(self) -> None:
        await self.coordinator.client.select_preset(self._slot, self._preset)
        await self.coordinator.async_request_refresh()


# ═══════════════════════════════════════════════════════════════════════
# MMP40 Media Player/Recorder Buttons
# ═══════════════════════════════════════════════════════════════════════

def _mmp40_button(icon, name_str, uid_suffix, method_name):
    """Factory for simple MMP40 buttons."""
    class Btn(CoordinatorEntity, ButtonEntity):
        _attr_has_entity_name = True
        _attr_icon = icon

        def __init__(self, coordinator, entry, slot):
            super().__init__(coordinator)
            self._slot = slot
            self._attr_unique_id = f"{entry.entry_id}_mmp40_slot{slot}_{uid_suffix}"
            self._attr_name = name_str
            self._attr_device_info = {"identifiers": {(DOMAIN, f"{entry.entry_id}_slot_{slot}")}}
            self._attr_extra_state_attributes = {"slot_number": slot}

        async def async_press(self):
            await getattr(self.coordinator.client, method_name)(self._slot)
            await self.coordinator.async_request_refresh()

    Btn.__name__ = f"MMP40{uid_suffix.title().replace('_','')}Button"
    return Btn


MMP40GoToStartButton = _mmp40_button("mdi:skip-backward", "Zum Anfang", "go_to_start", "go_to_start")
MMP40FastForwardButton = _mmp40_button("mdi:fast-forward", "Vorspulen", "fast_forward", "fast_forward")
MMP40FastRewindButton = _mmp40_button("mdi:rewind", "Zurückspulen", "fast_rewind", "fast_rewind")
MMP40StartRecordingButton = _mmp40_button("mdi:record-circle", "Aufnahme starten", "rec_start", "start_recording")
MMP40StopRecordingButton = _mmp40_button("mdi:stop", "Aufnahme stoppen", "rec_stop", "stop_recording")
MMP40PauseRecordingButton = _mmp40_button("mdi:pause", "Aufnahme pausieren", "rec_pause", "pause_recording")
MMP40CancelRecordingButton = _mmp40_button("mdi:close-circle", "Aufnahme abbrechen", "rec_cancel", "cancel_recording")


def _mmp40_arg_button(icon, name_str, uid_suffix, method_name, arg):
    """Factory for MMP40 buttons that pass an argument."""
    class Btn(CoordinatorEntity, ButtonEntity):
        _attr_has_entity_name = True
        _attr_icon = icon

        def __init__(self, coordinator, entry, slot):
            super().__init__(coordinator)
            self._slot = slot
            self._attr_unique_id = f"{entry.entry_id}_mmp40_slot{slot}_{uid_suffix}"
            self._attr_name = name_str
            self._attr_device_info = {"identifiers": {(DOMAIN, f"{entry.entry_id}_slot_{slot}")}}
            self._attr_extra_state_attributes = {"slot_number": slot}

        async def async_press(self):
            await getattr(self.coordinator.client, method_name)(self._slot, arg)
            await self.coordinator.async_request_refresh()

    return Btn


MMP40RandomOnButton = _mmp40_arg_button("mdi:shuffle", "Zufällig An", "random_on", "set_random", True)
MMP40RandomOffButton = _mmp40_arg_button("mdi:shuffle-disabled", "Zufällig Aus", "random_off", "set_random", False)
MMP40RepeatOneButton = _mmp40_arg_button("mdi:repeat-once", "Wiederholen: Titel", "repeat_one", "set_repeat", 0)
MMP40RepeatAllButton = _mmp40_arg_button("mdi:repeat", "Wiederholen: Alle", "repeat_all", "set_repeat", 4)
MMP40RepeatFolderButton = _mmp40_arg_button("mdi:folder-sync", "Wiederholen: Ordner", "repeat_folder", "set_repeat", 1)
MMP40RepeatOffButton = _mmp40_arg_button("mdi:repeat-off", "Wiederholen: Aus", "repeat_off", "set_repeat", 3)


# ═══════════════════════════════════════════════════════════════════════
# MTX Buttons (Save, Volume Up/Down)
# ═══════════════════════════════════════════════════════════════════════

class MTXSaveButton(CoordinatorEntity, ButtonEntity):
    """Button to save MTX settings (survives power cycle)."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:content-save"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_mtx_save"
        self._attr_name = "Einstellungen speichern"
        from .const import MODEL_NAMES, CONF_MODEL, MODEL_MTX88
        model = entry.data.get(CONF_MODEL, MODEL_MTX88)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.data.get("name", "Audac MTX"),
            "manufacturer": "Audac",
            "model": MODEL_NAMES.get(model, "MTX"),
        }

    async def async_press(self) -> None:
        await self.coordinator.client.save()


class MTXVolumeUpButton(CoordinatorEntity, ButtonEntity):
    """Button to increase zone volume by 3dB."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:volume-plus"

    def __init__(self, coordinator, zone: int, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._zone = zone
        zone_name = entry.options.get(f"zone_{zone}_name", f"Zone {zone}")
        self._attr_unique_id = f"{entry.entry_id}_zone_{zone}_vol_up"
        self._attr_name = f"{zone_name} Lauter"
        from .const import MODEL_NAMES, CONF_MODEL, MODEL_MTX88
        model = entry.data.get(CONF_MODEL, MODEL_MTX88)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.data.get("name", "Audac MTX"),
            "manufacturer": "Audac",
            "model": MODEL_NAMES.get(model, "MTX"),
        }

    async def async_press(self) -> None:
        await self.coordinator.client.set_volume_up(self._zone)
        await self.coordinator.async_request_refresh()


class MTXVolumeDownButton(CoordinatorEntity, ButtonEntity):
    """Button to decrease zone volume by 3dB."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:volume-minus"

    def __init__(self, coordinator, zone: int, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._zone = zone
        zone_name = entry.options.get(f"zone_{zone}_name", f"Zone {zone}")
        self._attr_unique_id = f"{entry.entry_id}_zone_{zone}_vol_down"
        self._attr_name = f"{zone_name} Leiser"
        from .const import MODEL_NAMES, CONF_MODEL, MODEL_MTX88
        model = entry.data.get(CONF_MODEL, MODEL_MTX88)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.data.get("name", "Audac MTX"),
            "manufacturer": "Audac",
            "model": MODEL_NAMES.get(model, "MTX"),
        }

    async def async_press(self) -> None:
        await self.coordinator.client.set_volume_down(self._zone)
        await self.coordinator.async_request_refresh()
