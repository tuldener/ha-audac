"""Button entities for Audac."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_MODEL, DOMAIN, MODEL_XMP44
from .entity import AudacCoordinatorEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime: dict[str, Any] = hass.data[DOMAIN][entry.entry_id]
    model = runtime["config"][CONF_MODEL]
    if model != MODEL_XMP44:
        return

    coordinator = runtime["coordinator"]
    slot_count = runtime["slot_count"]
    async_add_entities(
        [
            AudacXmpFmpTriggerButton(coordinator, entry.entry_id, model, slot)
            for slot in range(1, slot_count + 1)
        ]
    )


class AudacXmpFmpTriggerButton(AudacCoordinatorEntity, ButtonEntity):
    """Execute FMP40 trigger with selected action and contact."""

    def __init__(self, coordinator, entry_id: str, model: str, slot: int) -> None:
        super().__init__(coordinator, entry_id, model)
        self._slot = slot
        self._attr_unique_id = f"{entry_id}_slot_{slot}_fmp_trigger_execute"
        self._attr_name = f"Slot {slot} Trigger Execute"

    @property
    def available(self) -> bool:
        return self.coordinator.is_fmp_slot(self._slot)

    async def async_press(self) -> None:
        await self.coordinator.async_trigger_fmp(self._slot)
        await self.coordinator.async_request_refresh()
