"""Data coordinator for Audac MTX."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import AudacApiError, AudacMtxClient
from .const import STATE_FIRMWARE, STATE_ZONES

LOGGER = logging.getLogger(__name__)


class AudacDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate Audac MTX polling."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: AudacMtxClient,
        name: str,
        scan_interval: int,
        zone_count: int,
    ) -> None:
        super().__init__(
            hass,
            logger=LOGGER,
            name=f"audac_{name}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self.zone_count = zone_count

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            state = await self.client.async_get_state(self.zone_count)
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
