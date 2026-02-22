"""Shared entity classes for Audac MTX."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MODEL_MTX48, MODEL_MTX88, MODEL_XMP44
from .coordinator import AudacDataUpdateCoordinator


class AudacCoordinatorEntity(CoordinatorEntity[AudacDataUpdateCoordinator]):
    """Base class for Audac entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AudacDataUpdateCoordinator,
        entry_id: str,
        model: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._model = model

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for HA device registry."""
        data = self.coordinator.data or {}
        firmware = data.get("firmware")

        if self._model == MODEL_MTX48:
            model_name = "MTX48"
        elif self._model == MODEL_MTX88:
            model_name = "MTX88"
        elif self._model == MODEL_XMP44:
            model_name = "XMP44"
        else:
            model_name = "Audac"
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            manufacturer="Audac",
            model=model_name,
            sw_version=firmware,
            name=self.coordinator.name.removeprefix("audac_"),
        )
