"""Data coordinator for Audac."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import AudacApiError, AudacMtxClient, AudacXmpClient
from .const import (
    MODEL_XMP44,
    STATE_FIRMWARE,
    STATE_XMP_SLOTS,
    STATE_ZONES,
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
