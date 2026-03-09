"""Button entities for Audac XMP44 FMP40 voice file triggers."""
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
from .xmp44_client import MODULE_FMP40

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    model = entry.data.get(CONF_MODEL, MODEL_MTX88)
    if not is_xmp_model(model):
        return  # Buttons only for XMP44

    coordinator: XMP44Coordinator = hass.data[DOMAIN][entry.entry_id]
    slots_count = entry.data.get("slots", 4)

    entities: list[ButtonEntity] = []

    for slot in range(1, slots_count + 1):
        # Check if this slot is configured as FMP40
        module_str = entry.options.get(f"slot_{slot}_module", "0")
        try:
            module_type = int(module_str)
        except (ValueError, TypeError):
            module_type = 0

        if module_type != MODULE_FMP40:
            continue

        # Get number of triggers for this slot
        trigger_count = entry.options.get(f"slot_{slot}_triggers", 0)
        try:
            trigger_count = int(trigger_count)
        except (ValueError, TypeError):
            trigger_count = 0

        if trigger_count <= 0:
            continue

        for trigger in range(1, trigger_count + 1):
            trigger_name = entry.options.get(f"slot_{slot}_trigger_{trigger}_name", f"Trigger {trigger}")

            entities.append(
                FMP40TriggerStartButton(coordinator, entry, slot, trigger, trigger_name)
            )
            entities.append(
                FMP40TriggerStopButton(coordinator, entry, slot, trigger, trigger_name)
            )

    if entities:
        async_add_entities(entities)
        _LOGGER.debug("Created %d FMP40 trigger buttons", len(entities))


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
