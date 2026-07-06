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
from .helpers import get_zone_links
from .mtx_client import MTXClient

_LOGGER = logging.getLogger(__name__)

# Normal polling interval.
SCAN_INTERVAL = timedelta(seconds=60)

# Slower polling when device is unreachable — retry every 3 minutes.
SCAN_INTERVAL_SLOW = timedelta(seconds=180)

# Hard timeout for a complete coordinator update cycle.
UPDATE_TIMEOUT = 55.0

# Tolerance for volume drift before a re-sync command is sent (0–70 raw units).
SYNC_VOLUME_TOLERANCE = 1

# Number of consecutive failures before accepting suspicious all-zero data as real.
MAX_CONSECUTIVE_FAILURES = 3

# Number of failures before slowing down the poll interval.
SLOW_POLL_THRESHOLD = 2


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
        self._consecutive_update_failures = 0

    def _get_zone_links(self) -> dict[int, int]:
        """Return {slave_zone: master_zone} mapping from current options."""
        return get_zone_links(self.entry.options, self._zones_count)

    def _is_suspicious_response(self, new_zones: dict[int, dict[str, Any]]) -> bool:
        """Detect suspicious all-zero responses that likely indicate a communication glitch.

        Returns True if:
        - Previous data had at least one zone with routing > 0 (active source)
        - New data has ALL zones with routing == 0
        This pattern is extremely unlikely to be a real user action (turning off
        every zone simultaneously) and almost always indicates the device returned
        garbled/zeroed data.
        """
        if not self.data:
            return False

        prev_has_active = any(
            z.get("routing", 0) > 0 for z in self.data.values()
        )
        if not prev_has_active:
            return False  # nothing was active before, so all-zero is plausible

        new_all_zero = all(
            z.get("routing", 0) == 0 for z in new_zones.values()
        )
        return new_all_zero

    async def _sync_slave_zones(self, zones: dict[int, dict[str, Any]]) -> None:
        """After a poll, push master values to any slave zone that has drifted.

        Checks volume, mute, routing (source), bass, and treble.
        Only sends a command when the slave value differs from the master
        (with a small tolerance for volume to avoid constant re-syncing).
        """
        links = self._get_zone_links()
        if not links:
            return

        for slave_zone, master_zone in links.items():
            master = zones.get(master_zone)
            slave = zones.get(slave_zone)
            if not master or not slave:
                continue

            # Volume (raw 0–70, lower = louder)
            m_vol = master.get("volume", 70)
            s_vol = slave.get("volume", 70)
            if abs(m_vol - s_vol) >= SYNC_VOLUME_TOLERANCE:
                _LOGGER.debug("Sync: zone %d volume %d -> %d (master zone %d)", slave_zone, s_vol, m_vol, master_zone)
                await self.client.set_volume(slave_zone, m_vol)

            # Mute
            m_mute = master.get("mute", False)
            s_mute = slave.get("mute", False)
            if m_mute != s_mute:
                _LOGGER.debug("Sync: zone %d mute %s -> %s (master zone %d)", slave_zone, s_mute, m_mute, master_zone)
                await self.client.set_mute(slave_zone, m_mute)

            # Routing / source
            m_routing = master.get("routing", 0)
            s_routing = slave.get("routing", 0)
            if m_routing != s_routing:
                _LOGGER.debug("Sync: zone %d routing %d -> %d (master zone %d)", slave_zone, s_routing, m_routing, master_zone)
                await self.client.set_routing(slave_zone, m_routing)

            # Bass
            m_bass = master.get("bass", 7)
            s_bass = slave.get("bass", 7)
            if m_bass != s_bass:
                _LOGGER.debug("Sync: zone %d bass %d -> %d (master zone %d)", slave_zone, s_bass, m_bass, master_zone)
                await self.client.set_bass(slave_zone, m_bass)

            # Treble
            m_treble = master.get("treble", 7)
            s_treble = slave.get("treble", 7)
            if m_treble != s_treble:
                _LOGGER.debug("Sync: zone %d treble %d -> %d (master zone %d)", slave_zone, s_treble, m_treble, master_zone)
                await self.client.set_treble(slave_zone, m_treble)

    def _on_failure(self) -> None:
        """Track failure and slow down polling after threshold."""
        self._consecutive_update_failures += 1
        if self._consecutive_update_failures > SLOW_POLL_THRESHOLD and self.update_interval != SCAN_INTERVAL_SLOW:
            self.update_interval = SCAN_INTERVAL_SLOW
            _LOGGER.warning(
                "MTX unreachable after %d attempts, slowing poll to %ds",
                self._consecutive_update_failures, int(SCAN_INTERVAL_SLOW.total_seconds()),
            )

    @property
    def _should_keep_state(self) -> bool:
        """True if we still have grace period (<=2 failures) and previous data."""
        return self.data is not None and self._consecutive_update_failures <= SLOW_POLL_THRESHOLD

    def _on_success(self) -> None:
        """Reset failure counter and restore normal polling."""
        if self._consecutive_update_failures > SLOW_POLL_THRESHOLD:
            _LOGGER.info("MTX device recovered after %d failures, restoring normal poll interval",
                         self._consecutive_update_failures)
        self._consecutive_update_failures = 0
        if self.update_interval != SCAN_INTERVAL:
            self.update_interval = SCAN_INTERVAL

    async def _async_update_data(self) -> dict[int, dict[str, Any]]:
        """Fetch data from the MTX device.

        Never raises UpdateFailed if previous data exists — entities always
        keep their last known state. After SLOW_POLL_THRESHOLD failures,
        the polling interval is increased to SCAN_INTERVAL_SLOW. On success,
        it is restored to SCAN_INTERVAL.
        """
        try:
            result = await asyncio.wait_for(
                self._fetch_data(),
                timeout=UPDATE_TIMEOUT,
            )
            return result
        except asyncio.TimeoutError:
            self._on_failure()
            _LOGGER.warning(
                "MTX coordinator timed out after %ss (failure %d), retrying in %ds",
                UPDATE_TIMEOUT, self._consecutive_update_failures,
                int(self.update_interval.total_seconds()),
            )
            await self.client.disconnect()
            if self._should_keep_state:
                return self.data
            raise UpdateFailed(f"Update timed out after {UPDATE_TIMEOUT}s") from None

    async def _fetch_data(self) -> dict[int, dict[str, Any]]:
        try:
            zones = await self.client.get_all_zones(self._zones_count, previous=self.data)
            if not zones and self.data:
                self._on_failure()
                _LOGGER.debug("No zone data received (failure %d), keeping previous state",
                              self._consecutive_update_failures)
                if self._should_keep_state:
                    return self.data
                raise UpdateFailed("No zone data received from MTX")
            if not zones:
                raise UpdateFailed("No zone data received from MTX (first poll)")

            # Check for incomplete response (fewer zones than expected)
            if self.data and len(zones) < self._zones_count and len(self.data) == self._zones_count:
                self._on_failure()
                _LOGGER.warning(
                    "MTX returned incomplete data: %d/%d zones (failure %d), keeping previous state",
                    len(zones), self._zones_count, self._consecutive_update_failures,
                )
                if self._should_keep_state:
                    return self.data
                raise UpdateFailed("Incomplete zone data from MTX")

            # Plausibility check: all zones suddenly routing=0
            if self.data and self._is_suspicious_response(zones):
                self._on_failure()
                _LOGGER.warning(
                    "MTX returned suspicious all-zero data (failure %d), keeping previous state",
                    self._consecutive_update_failures,
                )
                if self._consecutive_update_failures < MAX_CONSECUTIVE_FAILURES:
                    return self.data
                _LOGGER.info("MTX all-zero data persisted for %d polls, accepting as real state", MAX_CONSECUTIVE_FAILURES)

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
            # Sync slave zones to master after every successful poll
            await self._sync_slave_zones(zones)
            self._on_success()
            return zones
        except ConnectionError as err:
            self._on_failure()
            _LOGGER.warning("Connection lost to MTX (failure %d), retrying in %ds: %s",
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
            _LOGGER.warning("MTX update error (failure %d), retrying in %ds: %s",
                            self._consecutive_update_failures,
                            int(self.update_interval.total_seconds()), err)
            if self._should_keep_state:
                return self.data
            raise UpdateFailed(f"Error communicating with MTX: {err}") from err

    async def async_shutdown(self) -> None:
        await self.client.disconnect()
