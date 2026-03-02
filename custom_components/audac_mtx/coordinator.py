"""Data coordinator for the Audac MTX integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .mtx_client import MTXClient

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=10)


class AudacMTXCoordinator(DataUpdateCoordinator[dict[int, dict[str, Any]]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.entry = entry
        self.client = MTXClient(
            host=entry.data["host"],
            port=entry.data.get("port", 5001),
        )
        self._zones_count = entry.data.get("zones", 8)

    async def _async_update_data(self) -> dict[int, dict[str, Any]]:
        try:
            zones = await self.client.get_all_zones(self._zones_count)
            if not zones:
                raise UpdateFailed("No zone data received from MTX")
            return zones
        except ConnectionError as err:
            raise UpdateFailed(f"Connection error: {err}") from err
        except UpdateFailed:
            raise
        except Exception as err:
            await self.client.disconnect()
            raise UpdateFailed(f"Error communicating with MTX: {err}") from err

    async def async_shutdown(self) -> None:
        await self.client.disconnect()
