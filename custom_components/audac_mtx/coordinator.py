"""Data coordinator for the Audac MTX integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_MODEL, MODEL_MTX88, MODEL_ZONES
from .mtx_client import MTXClient

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=15)

# Hard timeout for a complete coordinator update cycle.
# Must be longer than GET_ALL_ZONES_TIMEOUT (45s) in mtx_client.py.
UPDATE_TIMEOUT = 55.0


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
        model = entry.data.get(CONF_MODEL, MODEL_MTX88)
        self._zones_count = entry.data.get("zones", MODEL_ZONES.get(model, 8))

    async def _async_update_data(self) -> dict[int, dict[str, Any]]:
        """Fetch data from the MTX device with a hard overall timeout.

        Wrapping in wait_for() ensures that even if MTXClient's internal
        timeouts fail to fire (e.g. a double-lock scenario), the coordinator
        will never block the HA event loop indefinitely.
        """
        try:
            return await asyncio.wait_for(
                self._fetch_data(),
                timeout=UPDATE_TIMEOUT,
            )
        except asyncio.TimeoutError:
            _LOGGER.error(
                "Audac MTX coordinator update exceeded %.0fs — "
                "forcing client disconnect to unfreeze",
                UPDATE_TIMEOUT,
            )
            # Forcibly reset the client so the next cycle gets a fresh connection
            self.client._writer = None
            self.client._reader = None
            self.client._consecutive_failures += 1
            if self.data:
                return self.data
            raise UpdateFailed(f"Update timed out after {UPDATE_TIMEOUT}s") from None

    async def _fetch_data(self) -> dict[int, dict[str, Any]]:
        try:
            zones = await self.client.get_all_zones(self._zones_count)
            if not zones and self.data:
                _LOGGER.debug("No zone data received, keeping previous state")
                return self.data
            if not zones:
                raise UpdateFailed("No zone data received from MTX")
            for zone_id, zone_data in zones.items():
                _LOGGER.debug(
                    "Zone %d: volume=%s routing=%s mute=%s bass=%s treble=%s",
                    zone_id,
                    zone_data.get("volume"),
                    zone_data.get("routing"),
                    zone_data.get("mute"),
                    zone_data.get("bass"),
                    zone_data.get("treble"),
                )
            return zones
        except ConnectionError as err:
            if self.data:
                _LOGGER.warning("Connection lost to MTX, keeping previous state: %s", err)
                return self.data
            raise UpdateFailed(f"Connection error: {err}") from err
        except UpdateFailed:
            raise
        except Exception as err:
            await self.client.disconnect()
            if self.data:
                _LOGGER.warning("MTX update error, keeping previous state: %s", err)
                return self.data
            raise UpdateFailed(f"Error communicating with MTX: {err}") from err

    async def async_shutdown(self) -> None:
        await self.client.disconnect()
