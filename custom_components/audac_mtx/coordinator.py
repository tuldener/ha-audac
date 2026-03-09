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

# Poll every 60 s — gives the MTX device enough time to respond to all
# zone queries (~20-45 s) before the next cycle starts.
SCAN_INTERVAL = timedelta(seconds=60)

# Hard timeout for a complete coordinator update cycle.
# Must be longer than GET_ALL_ZONES_TIMEOUT (45 s) in mtx_client.py.
UPDATE_TIMEOUT = 55.0

# Tolerance for volume drift before a re-sync command is sent (0–70 raw units).
# 2 = roughly 3% volume — avoids constant re-syncing due to rounding.
SYNC_VOLUME_TOLERANCE = 1


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

    def _get_zone_links(self) -> dict[int, int]:
        """Return {slave_zone: master_zone} mapping from current options.

        Supports three formats for backward compatibility:
        - zone_z_link: str   (current: dropdown, "0" = no link)
        - zone_z_links: List[str]  (old: checkbox multi-select)
        - zone_z_linked_to: int    (legacy)
        """
        links = {}
        for z in range(1, self._zones_count + 1):
            # Current format: single string from dropdown
            zone_link = self.entry.options.get(f"zone_{z}_link")
            if zone_link is not None:
                try:
                    master = int(zone_link)
                    if master and master != z:
                        links[z] = master
                except (ValueError, TypeError):
                    pass
                continue
            # Old format: list of zone-number strings
            zone_links = self.entry.options.get(f"zone_{z}_links")
            if zone_links and isinstance(zone_links, list) and len(zone_links) > 0:
                try:
                    master = int(zone_links[0])
                    if master != z:
                        links[z] = master
                except (ValueError, TypeError):
                    pass
                continue
            # Legacy format: single integer
            master = self.entry.options.get(f"zone_{z}_linked_to", 0)
            if master and master != z:
                links[z] = master
        return links

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

    async def _async_update_data(self) -> dict[int, dict[str, Any]]:
        """Fetch data from the MTX device.

        The UPDATE_TIMEOUT wraps the entire fetch to ensure we never block
        the HA event loop if the MTX device stops responding.
        """
        try:
            return await asyncio.wait_for(
                self._fetch_data(),
                timeout=UPDATE_TIMEOUT,
            )
        except asyncio.TimeoutError:
            _LOGGER.warning(
                "MTX coordinator update timed out after %ss — disconnecting client",
                UPDATE_TIMEOUT,
            )
            # Force-reset the TCP connection so the next cycle reconnects cleanly.
            await self.client.disconnect()
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
            # Sync slave zones to master after every successful poll
            await self._sync_slave_zones(zones)
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
