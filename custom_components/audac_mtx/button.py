"""Button entities for Audac XMP44 modules (FMP40 triggers, IMP40 stations)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_MODEL, MODEL_MTX88, is_xmp_model
from .xmp44_coordinator import XMP44Coordinator
from .xmp44_client import MODULE_FMP40, MODULE_IMP40, MODULE_BMP40, MODULE_DMP40, MODULE_TMP40, MODULE_MMP40, MODULES_WITH_TUNER

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    model = entry.data.get(CONF_MODEL, MODEL_MTX88)
    if not is_xmp_model(model):
        return

    coordinator: XMP44Coordinator = hass.data[DOMAIN][entry.entry_id]
    slots_count = entry.data.get("slots", 4)

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

    for fav in favs:
        name = fav.get("name", "")
        pointer = fav.get("pointer", "")
        if name and pointer:
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
        self._attr_unique_id = f"{entry.entry_id}_imp40_slot{slot}_station_{safe_name}"
        self._attr_name = station_name
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry.entry_id}_slot_{slot}")},
        }

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

    async def async_press(self) -> None:
        await self.coordinator.client.select_preset(self._slot, self._preset)
        await self.coordinator.async_request_refresh()
