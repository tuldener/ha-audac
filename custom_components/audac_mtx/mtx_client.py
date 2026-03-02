"""TCP client for communicating with the Audac MTX device."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from .const import DEFAULT_PORT, DEFAULT_SOURCE, INPUT_NAMES, BASS_TREBLE_MAP

_LOGGER = logging.getLogger(__name__)


class MTXClient:
    def __init__(self, host: str, port: int = DEFAULT_PORT, source: str = DEFAULT_SOURCE) -> None:
        self._host = host
        self._port = port
        self._source = source
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()

    @property
    def host(self) -> str:
        return self._host

    @property
    def connected(self) -> bool:
        return self._writer is not None

    async def connect(self) -> None:
        if self._writer is not None:
            return
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=5,
            )
            _LOGGER.debug("Connected to MTX at %s:%s", self._host, self._port)
        except Exception as err:
            self._reader = None
            self._writer = None
            raise ConnectionError(f"Cannot connect to MTX at {self._host}:{self._port}: {err}") from err

    async def disconnect(self) -> None:
        if self._writer is not None:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None
            self._reader = None
            _LOGGER.debug("Disconnected from MTX")

    async def _ensure_connected(self) -> None:
        if self._writer is None:
            await self.connect()

    def _build_command(self, command: str, argument: str = "0") -> bytes:
        return f"#|X001|{self._source}|{command}|{argument}|U|\r\n".encode()

    async def _send_and_receive(self, command: str, argument: str = "0") -> str:
        async with self._lock:
            try:
                await self._ensure_connected()
            except ConnectionError:
                raise

            raw = self._build_command(command, argument)
            try:
                self._writer.write(raw)
                await self._writer.drain()

                response = await asyncio.wait_for(
                    self._reader.readline(),
                    timeout=3,
                )
                return response.decode().strip()
            except (asyncio.TimeoutError, OSError, ConnectionError) as err:
                _LOGGER.warning("Communication error with MTX for command %s: %s", command, err)
                await self.disconnect()
                raise ConnectionError(f"Lost connection to MTX: {err}") from err

    @staticmethod
    def _parse_response(response: str) -> str | None:
        if not response:
            return None
        parts = response.split("|")
        if len(parts) >= 5:
            return parts[4]
        return None

    async def get_zone_info(self, zone: int) -> dict[str, Any]:
        resp = await self._send_and_receive(f"GZI0{zone}")
        data = self._parse_response(resp)
        if data is None:
            return {}

        values = data.split("^")
        if len(values) != 5:
            return {}

        volume_raw = int(values[0])
        routing = int(values[1])
        mute = bool(int(values[2]))
        bass_raw = int(values[3])
        treble_raw = int(values[4])

        return {
            "volume": volume_raw,
            "volume_db": -volume_raw,
            "routing": routing,
            "source_name": INPUT_NAMES.get(routing, f"Input {routing}"),
            "mute": mute,
            "bass": bass_raw,
            "bass_db": BASS_TREBLE_MAP.get(bass_raw, 0),
            "treble": treble_raw,
            "treble_db": BASS_TREBLE_MAP.get(treble_raw, 0),
        }

    async def get_all_zones(self, zones_count: int = 8) -> dict[int, dict[str, Any]]:
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
        return zones

    async def set_volume(self, zone: int, volume: int) -> bool:
        volume = max(0, min(70, volume))
        resp = await self._send_and_receive(f"SV{zone}", str(volume))
        return "+" in (resp or "")

    async def set_volume_up(self, zone: int) -> bool:
        resp = await self._send_and_receive(f"SVU0{zone}")
        return "+" in (resp or "")

    async def set_volume_down(self, zone: int) -> bool:
        resp = await self._send_and_receive(f"SVD0{zone}")
        return "+" in (resp or "")

    async def set_routing(self, zone: int, input_id: int) -> bool:
        resp = await self._send_and_receive(f"SR{zone}", str(input_id))
        return "+" in (resp or "")

    async def set_bass(self, zone: int, bass: int) -> bool:
        bass = max(0, min(14, bass))
        resp = await self._send_and_receive(f"SB0{zone}", str(bass))
        return "+" in (resp or "")

    async def set_treble(self, zone: int, treble: int) -> bool:
        treble = max(0, min(14, treble))
        resp = await self._send_and_receive(f"ST0{zone}", str(treble))
        return "+" in (resp or "")

    async def set_mute(self, zone: int, mute: bool) -> bool:
        resp = await self._send_and_receive(f"SM0{zone}", "1" if mute else "0")
        return "+" in (resp or "")

    async def save(self) -> bool:
        resp = await self._send_and_receive("SAVE")
        return "+" in (resp or "")

    async def get_version(self) -> str:
        resp = await self._send_and_receive("GSV")
        data = self._parse_response(resp)
        return data or "Unknown"
