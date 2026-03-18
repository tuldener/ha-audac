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
from .xmp44_client import XMP44Client, MODULE_IMP40

_LOGGER = logging.getLogger(__name__)

# Poll every 30s — XMP44 has fewer commands than MTX per cycle
SCAN_INTERVAL = timedelta(seconds=30)

# Hard timeout for a complete coordinator update cycle.
UPDATE_TIMEOUT = 55.0

# Number of consecutive failures before marking entities as unavailable.
MAX_CONSECUTIVE_FAILURES = 3


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
        # Cached favourites per IMP40 slot: {slot: [{name, pointer}, ...]}
        self.favourites: dict[int, list[dict[str, Any]]] = {}
        self._favourites_loaded = False
        self._consecutive_update_failures = 0

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
            result = await asyncio.wait_for(
                self._fetch_data(),
                timeout=UPDATE_TIMEOUT,
            )
            return result
        except asyncio.TimeoutError:
            self._consecutive_update_failures += 1
            _LOGGER.warning(
                "XMP44 coordinator update timed out after %ss (failure %d/%d)",
                UPDATE_TIMEOUT, self._consecutive_update_failures, MAX_CONSECUTIVE_FAILURES,
            )
            await self.client.disconnect()
            if self.data and self._consecutive_update_failures < MAX_CONSECUTIVE_FAILURES:
                return self.data
            raise UpdateFailed(f"Update timed out after {UPDATE_TIMEOUT}s") from None

    async def _fetch_data(self) -> dict[int, dict[str, Any]]:
        try:
            # Load favourites once for IMP40 slots
            if not self._favourites_loaded:
                await self._load_favourites()
                self._favourites_loaded = True

            slots = await self.client.get_all_slots()
            if not slots and self.data:
                self._consecutive_update_failures += 1
                _LOGGER.debug("No slot data received (failure %d/%d), keeping previous state",
                              self._consecutive_update_failures, MAX_CONSECUTIVE_FAILURES)
                if self._consecutive_update_failures < MAX_CONSECUTIVE_FAILURES:
                    return self.data
                raise UpdateFailed("No slot data received from XMP44 after %d attempts" % MAX_CONSECUTIVE_FAILURES)
            if not slots:
                raise UpdateFailed("No slot data received from XMP44")

            # Inject cached favourites into slot data
            for slot_id, slot_data in slots.items():
                if slot_id in self.favourites:
                    slot_data["favourites"] = self.favourites[slot_id]
                _LOGGER.debug(
                    "XMP44 slot %d (%s): status=%s gain=%s",
                    slot_id,
                    slot_data.get("module_name"),
                    slot_data.get("status"),
                    slot_data.get("output_gain"),
                )
            self._consecutive_update_failures = 0
            return slots
        except ConnectionError as err:
            self._consecutive_update_failures += 1
            if self.data and self._consecutive_update_failures < MAX_CONSECUTIVE_FAILURES:
                _LOGGER.warning("Connection lost to XMP44 (failure %d/%d), keeping previous state: %s",
                                self._consecutive_update_failures, MAX_CONSECUTIVE_FAILURES, err)
                return self.data
            raise UpdateFailed(f"Connection error: {err}") from err
        except UpdateFailed:
            raise
        except Exception as err:
            self._consecutive_update_failures += 1
            await self.client.disconnect()
            if self.data and self._consecutive_update_failures < MAX_CONSECUTIVE_FAILURES:
                _LOGGER.warning("XMP44 update error (failure %d/%d), keeping previous state: %s",
                                self._consecutive_update_failures, MAX_CONSECUTIVE_FAILURES, err)
                return self.data
            raise UpdateFailed(f"Error communicating with XMP44: {err}") from err

    async def _load_favourites(self) -> None:
        """Load favourites for all IMP40 slots (once)."""
        for slot, type_id in self.client.module_types.items():
            if type_id == MODULE_IMP40:
                try:
                    favs = await self.client.get_all_favourites(slot)
                    if favs:
                        self.favourites[slot] = favs
                        _LOGGER.debug(
                            "XMP44 IMP40 slot %d: loaded %d favourites",
                            slot, len(favs),
                        )
                except Exception as err:
                    _LOGGER.warning("Failed to load favourites for slot %d: %s", slot, err)

    async def async_reload_favourites(self, slot: int) -> None:
        """Reload favourites for a specific IMP40 slot."""
        try:
            favs = await self.client.get_all_favourites(slot)
            if favs:
                self.favourites[slot] = favs
        except Exception as err:
            _LOGGER.warning("Failed to reload favourites for slot %d: %s", slot, err)

    async def async_shutdown(self) -> None:
        await self.client.disconnect()
