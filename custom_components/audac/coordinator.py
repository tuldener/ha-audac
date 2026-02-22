"""Data coordinator for Audac."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import AudacApiError, AudacMtxClient, AudacXmpClient
from .const import (
    FMP_TRIGGER_ACTION_OPTIONS,
    FMP_TRIGGER_ACTION_START,
    FMP_TRIGGER_MAX,
    FMP_TRIGGER_MIN,
    MODEL_XMP44,
    STATE_FIRMWARE,
    STATE_XMP_SLOTS,
    STATE_ZONES,
    XMP_MODULE_FMP40,
    XMP_SLOT_GAIN,
    XMP_SLOT_INFO,
    XMP_SLOT_MODULE,
    XMP_SLOT_MODULE_LABEL,
    XMP_SLOT_PAIRING,
    XMP_SLOT_PLAYER_STATUS,
    XMP_SLOT_PROGRAM,
    XMP_SLOT_SONG,
    XMP_SLOT_STATION,
)

LOGGER = logging.getLogger(__name__)


class AudacDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate Audac polling."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: AudacMtxClient | AudacXmpClient,
        name: str,
        scan_interval: int,
        model: str,
        zone_count: int,
        slot_count: int,
        slot_modules: dict[int, str],
    ) -> None:
        super().__init__(
            hass,
            logger=LOGGER,
            name=f"audac_{name}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self.model = model
        self.zone_count = zone_count
        self.slot_count = slot_count
        self.slot_modules = slot_modules
        self._fmp_trigger_state: dict[int, dict[str, Any]] = {
            slot: {
                "action": FMP_TRIGGER_ACTION_START,
                "contact": FMP_TRIGGER_MIN,
                "description": None,
            }
            for slot in range(1, slot_count + 1)
        }

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            if self.model == MODEL_XMP44:
                state = await self.client.async_get_state(self.slot_count, self.slot_modules)  # type: ignore[arg-type]
                return {
                    STATE_FIRMWARE: None,
                    STATE_XMP_SLOTS: {
                        slot: {
                            XMP_SLOT_MODULE: slot_state.module,
                            XMP_SLOT_MODULE_LABEL: slot_state.module_label,
                            XMP_SLOT_GAIN: slot_state.gain,
                            XMP_SLOT_PLAYER_STATUS: slot_state.player_status,
                            XMP_SLOT_SONG: slot_state.song,
                            XMP_SLOT_STATION: slot_state.station,
                            XMP_SLOT_PROGRAM: slot_state.program,
                            XMP_SLOT_INFO: slot_state.info,
                            XMP_SLOT_PAIRING: slot_state.pairing,
                        }
                        for slot, slot_state in state.slots.items()
                    },
                }

            previous_zones = self._get_previous_zones()
            state = await self.client.async_get_state(  # type: ignore[arg-type]
                self.zone_count, previous_zones
            )
        except AudacApiError as err:
            raise UpdateFailed(str(err)) from err

        return {
            STATE_FIRMWARE: state.firmware,
            STATE_ZONES: {
                zone: {
                    "volume": zone_state.volume_db,
                    "source": zone_state.source,
                    "mute": zone_state.mute,
                }
                for zone, zone_state in state.zones.items()
            },
        }

    def is_fmp_slot(self, slot: int) -> bool:
        """Return True if a slot is currently detected/configured as FMP40."""
        slots = (self.data or {}).get(STATE_XMP_SLOTS, {})
        slot_state = slots.get(slot, {})
        detected = str(slot_state.get(XMP_SLOT_MODULE, "")).strip().lower()
        configured = str(self.slot_modules.get(slot, "")).strip().lower()
        return detected == XMP_MODULE_FMP40 or configured == XMP_MODULE_FMP40

    def get_fmp_trigger_action(self, slot: int) -> str:
        return str(
            self._fmp_trigger_state.get(slot, {}).get("action", FMP_TRIGGER_ACTION_START)
        )

    def set_fmp_trigger_action(self, slot: int, action: str) -> None:
        normalized = str(action).strip().lower()
        if normalized not in FMP_TRIGGER_ACTION_OPTIONS:
            raise ValueError(f"Unsupported trigger action: {action}")
        self._fmp_trigger_state.setdefault(slot, {})["action"] = normalized
        self.async_update_listeners()

    def get_fmp_trigger_contact(self, slot: int) -> int:
        raw = self._fmp_trigger_state.get(slot, {}).get("contact", FMP_TRIGGER_MIN)
        try:
            value = int(raw)
        except (TypeError, ValueError):
            value = FMP_TRIGGER_MIN
        return max(FMP_TRIGGER_MIN, min(FMP_TRIGGER_MAX, value))

    def set_fmp_trigger_contact(self, slot: int, contact: int) -> None:
        value = max(FMP_TRIGGER_MIN, min(FMP_TRIGGER_MAX, int(contact)))
        self._fmp_trigger_state.setdefault(slot, {})["contact"] = value
        self.async_update_listeners()

    def get_fmp_trigger_description(self, slot: int) -> str | None:
        raw = self._fmp_trigger_state.get(slot, {}).get("description")
        if raw is None:
            return None
        value = str(raw).strip()
        return value or None

    async def async_trigger_fmp(self, slot: int) -> None:
        """Execute SSTR trigger command for a FMP40 slot."""
        action = self.get_fmp_trigger_action(slot)
        contact = self.get_fmp_trigger_contact(slot)
        start = action == FMP_TRIGGER_ACTION_START
        response = await self.client.async_set_slot_trigger(slot, contact, start)  # type: ignore[attr-defined]

        description = str(response).strip() or None
        if description == "+":
            description = f"Trigger {contact} {action}"
        self._fmp_trigger_state.setdefault(slot, {})["description"] = description
        self.async_update_listeners()

    def _get_previous_zones(self) -> dict[int, dict[str, Any]] | None:
        """Return last known MTX zone state for graceful polling fallbacks."""
        if not self.data:
            return None
        zones = self.data.get(STATE_ZONES)
        if not isinstance(zones, dict):
            return None

        previous: dict[int, dict[str, Any]] = {}
        for zone, zone_state in zones.items():
            if not isinstance(zone_state, dict):
                continue
            try:
                zone_idx = int(zone)
            except (TypeError, ValueError):
                continue
            previous[zone_idx] = {
                "volume": zone_state.get("volume", 0),
                "source": zone_state.get("source", "0"),
                "mute": zone_state.get("mute", False),
            }
        return previous or None
