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

# Normal polling interval.
SCAN_INTERVAL = timedelta(seconds=30)

# Slower polling when device is unreachable — retry every 3 minutes.
SCAN_INTERVAL_SLOW = timedelta(seconds=180)

# Hard timeout for a complete coordinator update cycle.
UPDATE_TIMEOUT = 55.0

# Number of failures before slowing down the poll interval.
SLOW_POLL_THRESHOLD = 2

# Number of consecutive failures for plausibility checks.
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

    def _on_failure(self) -> None:
        """Track failure and slow down polling after threshold."""
        self._consecutive_update_failures += 1
        if self._consecutive_update_failures > SLOW_POLL_THRESHOLD and self.update_interval != SCAN_INTERVAL_SLOW:
            self.update_interval = SCAN_INTERVAL_SLOW
            _LOGGER.warning(
                "XMP44 unreachable after %d attempts, slowing poll to %ds",
                self._consecutive_update_failures, int(SCAN_INTERVAL_SLOW.total_seconds()),
            )

    @property
    def _should_keep_state(self) -> bool:
        """True if we still have grace period (<=2 failures) and previous data."""
        return self.data is not None and self._consecutive_update_failures <= SLOW_POLL_THRESHOLD

    def _on_success(self) -> None:
        """Reset failure counter and restore normal polling."""
        if self._consecutive_update_failures > SLOW_POLL_THRESHOLD:
            _LOGGER.info("XMP44 device recovered after %d failures, restoring normal poll interval",
                         self._consecutive_update_failures)
        self._consecutive_update_failures = 0
        if self.update_interval != SCAN_INTERVAL:
            self.update_interval = SCAN_INTERVAL

    async def _async_update_data(self) -> dict[int, dict[str, Any]]:
        try:
            result = await asyncio.wait_for(
                self._fetch_data(),
                timeout=UPDATE_TIMEOUT,
            )
            return result
        except asyncio.TimeoutError:
            self._on_failure()
            _LOGGER.warning(
                "XMP44 coordinator timed out after %ss (failure %d), retrying in %ds",
                UPDATE_TIMEOUT, self._consecutive_update_failures,
                int(self.update_interval.total_seconds()),
            )
            await self.client.disconnect()
            if self._should_keep_state:
                return self.data
            raise UpdateFailed(f"Update timed out after {UPDATE_TIMEOUT}s") from None

    async def _fetch_data(self) -> dict[int, dict[str, Any]]:
        try:
            # Load favourites for IMP40 slots — retry on each poll until successful
            if not self._favourites_loaded:
                has_imp40 = any(t == MODULE_IMP40 for t in self.client.module_types.values())
                if has_imp40:
                    await self._load_favourites()
                    if self.favourites:
                        self._favourites_loaded = True
                        _LOGGER.info("XMP44: Favourites loaded for %d IMP40 slot(s)", len(self.favourites))
                    else:
                        _LOGGER.debug("XMP44: No favourites loaded yet, will retry next poll")
                else:
                    self._favourites_loaded = True  # No IMP40 modules, nothing to load

            slots = await self.client.get_all_slots()
            if not slots and self.data:
                self._on_failure()
                _LOGGER.debug("No slot data received (failure %d), keeping previous state",
                              self._consecutive_update_failures)
                if self._should_keep_state:
                    return self.data
                raise UpdateFailed("No slot data received from XMP44")
            if not slots:
                raise UpdateFailed("No slot data received from XMP44 (first poll)")

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
            self._on_success()
            return slots
        except ConnectionError as err:
            self._on_failure()
            _LOGGER.warning("Connection lost to XMP44 (failure %d), retrying in %ds: %s",
                            self._consecutive_update_failures,
                            int(self.update_interval.total_seconds()), err)
            if self._should_keep_state:
                return self.data
            raise UpdateFailed(f"Connection error: {err}") from err
        except UpdateFailed:
            raise
        except Exception as err:
            self._on_failure()
            await self.client.disconnect()
            _LOGGER.warning("XMP44 update error (failure %d), retrying in %ds: %s",
                            self._consecutive_update_failures,
                            int(self.update_interval.total_seconds()), err)
            if self._should_keep_state:
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
