"""Select entities for Audac."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_MODEL,
    DOMAIN,
    FMP_TRIGGER_ACTION_OPTIONS,
    MODEL_XMP44,
    STATE_ZONES,
    ZONE_SOURCE,
)
from .entity import AudacCoordinatorEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime: dict[str, Any] = hass.data[DOMAIN][entry.entry_id]
    model = runtime["config"][CONF_MODEL]
    coordinator = runtime["coordinator"]
    if model == MODEL_XMP44:
        slot_count = runtime["slot_count"]
        async_add_entities(
            [
                AudacXmpFmpTriggerActionSelect(coordinator, entry.entry_id, model, slot)
                for slot in range(1, slot_count + 1)
            ]
        )
        return

    zone_count = runtime["zone_count"]
    zone_names: dict[int, str] = runtime["zone_names"]
    input_labels: dict[str, str] = runtime["input_labels"]

    async_add_entities(
        [
            AudacZoneSourceSelect(
                coordinator,
                entry.entry_id,
                model,
                zone,
                zone_names.get(zone, f"Zone {zone}"),
                input_labels,
            )
            for zone in range(1, zone_count + 1)
        ]
    )


class AudacZoneSourceSelect(AudacCoordinatorEntity, SelectEntity):
    """Zone source select entity."""

    _attr_translation_key = "source"

    def __init__(
        self,
        coordinator,
        entry_id: str,
        model: str,
        zone: int,
        zone_name: str,
        input_labels: dict[str, str],
    ) -> None:
        super().__init__(coordinator, entry_id, model)
        self._zone = zone
        self._attr_unique_id = f"{entry_id}_zone_{zone}_source"
        self._attr_name = f"{zone_name} Source"
        self._id_to_name = input_labels
        self._name_to_id = {v: k for k, v in self._id_to_name.items()}

    @property
    def options(self) -> list[str]:
        options = list(self._id_to_name.values())
        current = self.current_option
        if current and current not in options:
            options.append(current)
        return options

    @property
    def current_option(self) -> str | None:
        zones = (self.coordinator.data or {}).get(STATE_ZONES, {})
        zone = zones.get(self._zone, {})
        src = str(zone.get(ZONE_SOURCE, "0"))
        return self._id_to_name.get(src, f"Input {src}")

    async def async_select_option(self, option: str) -> None:
        source_id = self._name_to_id.get(option)
        if source_id is None:
            raise ValueError(f"Unsupported source option: {option}")
        await self.coordinator.client.async_set_zone_source(self._zone, source_id)
        await self.coordinator.async_request_refresh()


class AudacXmpFmpTriggerActionSelect(AudacCoordinatorEntity, SelectEntity):
    """FMP40 trigger action select (start/stop)."""

    def __init__(self, coordinator, entry_id: str, model: str, slot: int) -> None:
        super().__init__(coordinator, entry_id, model)
        self._slot = slot
        self._attr_unique_id = f"{entry_id}_slot_{slot}_fmp_trigger_action"
        self._attr_name = f"Slot {slot} Trigger Action"

    @property
    def available(self) -> bool:
        return self.coordinator.is_fmp_slot(self._slot)

    @property
    def options(self) -> list[str]:
        return list(FMP_TRIGGER_ACTION_OPTIONS)

    @property
    def current_option(self) -> str | None:
        return self.coordinator.get_fmp_trigger_action(self._slot)

    async def async_select_option(self, option: str) -> None:
        self.coordinator.set_fmp_trigger_action(self._slot, option)
