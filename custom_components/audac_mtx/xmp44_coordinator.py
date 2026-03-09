"""Data coordinator for the Audac XMP44 modular audio system."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_MODEL, MODEL_XMP44
from .xmp44_client import XMP44Client

_LOGGER = logging.getLogger(__name__)

# Poll every 30s — XMP44 has fewer commands than MTX per cycle
SCAN_INTERVAL = timedelta(seconds=30)

# Hard timeout for a complete coordinator update cycle.
UPDATE_TIMEOUT = 45.0


class XMP44Coordinator(DataUpdateCoordinator[dict[int, dict[str, Any]]]):
    """Coordinator that polls an XMP44 for slot data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_xmp44",
            update_interval=SCAN_INTERVAL,
        )
        self.entry = entry
        self.client = XMP44Client(
            host=entry.data["host"],
            port=entry.data.get("port", 5001),
        )
        self._apply_module_config()

    def _apply_module_config(self) -> None:
        """Read module configuration from entry options and apply to client."""
        slots_count = self.entry.data.get("slots", 4)
        module_config: dict[int, int] = {}
        for slot in range(1, slots_count + 1):
            module_str = self.entry.options.get(f"slot_{slot}_module", "0")
            try:
                module_type = int(module_str)
            except (ValueError, TypeError):
                module_type = 0
            if module_type and module_type not in (15, 255):
                module_config[slot] = module_type
        self.client.set_module_config(module_config)

    async def _async_update_data(self) -> dict[int, dict[str, Any]]:
        try:
            return await asyncio.wait_for(
                self._fetch_data(),
                timeout=UPDATE_TIMEOUT,
            )
        except asyncio.TimeoutError:
            _LOGGER.warning(
                "XMP44 coordinator update timed out after %ss — disconnecting client",
                UPDATE_TIMEOUT,
            )
            await self.client.disconnect()
            if self.data:
                return self.data
            raise UpdateFailed(f"Update timed out after {UPDATE_TIMEOUT}s") from None

    async def _fetch_data(self) -> dict[int, dict[str, Any]]:
        try:
            slots = await self.client.get_all_slots()
            if not slots and self.data:
                _LOGGER.debug("No slot data received, keeping previous state")
                return self.data
            if not slots:
                raise UpdateFailed("No slot data received from XMP44")
            for slot_id, slot_data in slots.items():
                _LOGGER.debug(
                    "XMP44 slot %d (%s): status=%s gain=%s",
                    slot_id,
                    slot_data.get("module_name"),
                    slot_data.get("status"),
                    slot_data.get("output_gain"),
                )
            return slots
        except ConnectionError as err:
            if self.data:
                _LOGGER.warning("Connection lost to XMP44, keeping previous state: %s", err)
                return self.data
            raise UpdateFailed(f"Connection error: {err}") from err
        except UpdateFailed:
            raise
        except Exception as err:
            await self.client.disconnect()
            if self.data:
                _LOGGER.warning("XMP44 update error, keeping previous state: %s", err)
                return self.data
            raise UpdateFailed(f"Error communicating with XMP44: {err}") from err

    async def async_shutdown(self) -> None:
        await self.client.disconnect()
