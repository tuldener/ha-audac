"""TCP client for communicating with Audac MTX48/MTX88 audio matrices.

Inherits the shared TCP protocol from AudacClient and adds
MTX-specific zone commands (volume, routing, bass, treble, mute).

Protocol:
  Address: X001
  Zones:   4 (MTX48) or 8 (MTX88)
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from .audac_client import AudacClient, INTER_COMMAND_DELAY
from .const import DEFAULT_PORT, DEFAULT_SOURCE, INPUT_NAMES, BASS_TREBLE_MAP

_LOGGER = logging.getLogger(__name__)

# Hard timeout for the entire get_all_zones() call (seconds).
GET_ALL_ZONES_TIMEOUT = 45.0


class MTXClient(AudacClient):
    """Client for Audac MTX48/MTX88 audio matrices."""

    DEVICE_ADDRESS = "X001"

    def __init__(self, host: str, port: int = DEFAULT_PORT, source: str = DEFAULT_SOURCE) -> None:
        super().__init__(host, port, source)
        self._bulk_supported: bool | None = None

    async def connect(self) -> None:
        await super().connect()
        self._bulk_supported = None

    # ── Zone queries ────────────────────────────────────────────────

    async def get_zone_info(self, zone: int) -> dict[str, Any]:
        resp = await self._send_and_receive(f"GZI0{zone}")
        data = self._get_data_field(resp)
        if not data or data == "+":
            return {}
        values = data.split("^")
        if len(values) < 5:
            _LOGGER.warning("Zone %d: expected >=5 fields, got %d: %s", zone, len(values), data)
            return {}
        try:
            volume_raw = int(values[0])
            routing = int(values[1])
            mute_raw = int(values[2])
            bass_raw = int(values[3])
            treble_raw = int(values[4])
        except (ValueError, IndexError) as err:
            _LOGGER.warning("Zone %d parse error: %s", zone, err)
            return {}
        return {
            "volume": volume_raw,
            "volume_db": -volume_raw,
            "routing": routing,
            "source_name": INPUT_NAMES.get(routing, f"Input {routing}"),
            "mute": mute_raw != 0,
            "bass": bass_raw,
            "bass_db": BASS_TREBLE_MAP.get(bass_raw, 0),
            "treble": treble_raw,
            "treble_db": BASS_TREBLE_MAP.get(treble_raw, 0),
        }

    async def get_all_zones(self, zones_count: int = 8) -> dict[int, dict[str, Any]]:
        """Fetch all zone data with a hard overall timeout."""
        try:
            return await asyncio.wait_for(
                self._get_all_zones_inner(zones_count),
                timeout=GET_ALL_ZONES_TIMEOUT,
            )
        except asyncio.TimeoutError:
            _LOGGER.warning(
                "get_all_zones() exceeded %.0fs total timeout — forcing disconnect",
                GET_ALL_ZONES_TIMEOUT,
            )
            self._writer = None
            self._reader = None
            self._consecutive_failures += 1
            raise ConnectionError("get_all_zones timed out") from None

    async def _get_all_zones_inner(self, zones_count: int) -> dict[int, dict[str, Any]]:
        if self._bulk_supported is False:
            return await self._get_all_zones_individual(zones_count)

        zones: dict[int, dict[str, Any]] = {}
        volumes = await self._get_bulk("GVALL", zones_count)
        await asyncio.sleep(INTER_COMMAND_DELAY)
        routings = await self._get_bulk("GRALL", zones_count)
        await asyncio.sleep(INTER_COMMAND_DELAY)
        mutes = await self._get_bulk("GMALL", zones_count)
        await asyncio.sleep(INTER_COMMAND_DELAY)

        if not volumes and not routings and not mutes:
            if self._bulk_supported is None:
                _LOGGER.info("MTX bulk commands not supported, switching to per-zone queries")
            self._bulk_supported = False
            return await self._get_all_zones_individual(zones_count)

        self._bulk_supported = True
        for zone in range(1, zones_count + 1):
            zones[zone] = {
                "volume": volumes.get(zone, 70),
                "volume_db": -volumes.get(zone, 70),
                "routing": routings.get(zone, 0),
                "source_name": INPUT_NAMES.get(routings.get(zone, 0), "Off"),
                "mute": mutes.get(zone, 0) != 0,
                "bass": 7,
                "bass_db": 0,
                "treble": 7,
                "treble_db": 0,
            }

        for zone in range(1, zones_count + 1):
            try:
                bass = await self._get_single_value(f"GB0{zone}")
                if bass is not None:
                    zones[zone]["bass"] = bass
                    zones[zone]["bass_db"] = BASS_TREBLE_MAP.get(bass, 0)
                await asyncio.sleep(INTER_COMMAND_DELAY)
                treble = await self._get_single_value(f"GT0{zone}")
                if treble is not None:
                    zones[zone]["treble"] = treble
                    zones[zone]["treble_db"] = BASS_TREBLE_MAP.get(treble, 0)
                await asyncio.sleep(INTER_COMMAND_DELAY)
            except ConnectionError:
                raise
            except Exception as err:
                _LOGGER.warning("Bass/treble error zone %d: %s", zone, err)

        return zones

    async def _get_all_zones_individual(self, zones_count: int) -> dict[int, dict[str, Any]]:
        zones = {}
        for zone in range(1, zones_count + 1):
            try:
                info = await self.get_zone_info(zone)
                if info:
                    zones[zone] = info
            except ConnectionError:
                raise
            except Exception as err:
                _LOGGER.warning("Failed to get info for zone %d: %s", zone, err)
            await asyncio.sleep(INTER_COMMAND_DELAY)
        return zones

    async def _get_bulk(self, command: str, zones_count: int) -> dict[int, int]:
        resp = await self._send_and_receive(command, timeout=3.0)
        data = self._get_data_field(resp)
        if not data or data == "+":
            _LOGGER.debug("No data for bulk command %s, will fall back to per-zone", command)
            return {}
        values = data.split("^")
        result = {}
        for i, val in enumerate(values):
            zone = i + 1
            if zone > zones_count:
                break
            try:
                result[zone] = int(val)
            except ValueError:
                _LOGGER.warning("%s: invalid value '%s' for zone %d", command, val, zone)
        return result

    # ── Zone SET commands ───────────────────────────────────────────

    async def set_volume(self, zone: int, volume: int) -> bool:
        volume = max(0, min(70, volume))
        resp = await self._send_and_receive(f"SV{zone}", str(volume))
        return self._is_success(resp)

    async def set_volume_up(self, zone: int) -> bool:
        resp = await self._send_and_receive(f"SVU0{zone}", "0")
        return self._is_success(resp)

    async def set_volume_down(self, zone: int) -> bool:
        resp = await self._send_and_receive(f"SVD0{zone}", "0")
        return self._is_success(resp)

    async def set_routing(self, zone: int, input_id: int) -> bool:
        resp = await self._send_and_receive(f"SR{zone}", str(input_id))
        return self._is_success(resp)

    async def set_routing_up(self, zone: int) -> bool:
        resp = await self._send_and_receive(f"SRU0{zone}", "0")
        return self._is_success(resp)

    async def set_routing_down(self, zone: int) -> bool:
        resp = await self._send_and_receive(f"SRD0{zone}", "0")
        return self._is_success(resp)

    async def set_bass(self, zone: int, bass: int) -> bool:
        bass = max(0, min(14, bass))
        resp = await self._send_and_receive(f"SB0{zone}", str(bass))
        return self._is_success(resp)

    async def set_treble(self, zone: int, treble: int) -> bool:
        treble = max(0, min(14, treble))
        resp = await self._send_and_receive(f"ST0{zone}", str(treble))
        return self._is_success(resp)

    async def set_mute(self, zone: int, mute: bool) -> bool:
        resp = await self._send_and_receive(f"SM0{zone}", "1" if mute else "0")
        return self._is_success(resp)

    async def save(self) -> bool:
        resp = await self._send_and_receive("SAVE", "0")
        return self._is_success(resp)

    async def factory_reset(self) -> bool:
        resp = await self._send_and_receive("DEF", "0")
        return self._is_success(resp)

    async def get_version(self) -> str:
        resp = await self._send_and_receive("GSV", "0")
        data = self._get_data_field(resp)
        return data if data and data != "+" else "Unknown"

    async def get_zone_volume(self, zone: int) -> int | None:
        return await self._get_single_value(f"GV0{zone}")

    async def get_zone_routing(self, zone: int) -> int | None:
        return await self._get_single_value(f"GR0{zone}")

    async def get_zone_mute(self, zone: int) -> bool | None:
        val = await self._get_single_value(f"GM0{zone}")
        if val is None:
            return None
        return val != 0
