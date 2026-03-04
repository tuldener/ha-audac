"""TCP client for communicating with the Audac MTX device.

Protocol reference (MTX48/MTX88):
  Command:  #|X001|source|CMD|arg|U|\\r\\n
  Answer:   #|source|X001|CMD|data|checksum|\\r\\n
  Update:   #|ALL|X001|CMD|data|checksum|\\r\\n  (broadcast after SET)

  GET responses strip the 'G' prefix: GZI01 → ZI01, GVALL → VALL
  SET responses echo the command with '+' as data.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from .const import DEFAULT_PORT, DEFAULT_SOURCE, INPUT_NAMES, BASS_TREBLE_MAP

_LOGGER = logging.getLogger(__name__)

MAX_RETRIES = 1
RECONNECT_DELAY = 1.0
INTER_COMMAND_DELAY = 0.1


class MTXClient:
    def __init__(self, host: str, port: int = DEFAULT_PORT, source: str = DEFAULT_SOURCE) -> None:
        self._host = host
        self._port = port
        self._source = source
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()
        self._consecutive_failures = 0

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
                timeout=3,
            )
            self._consecutive_failures = 0
            _LOGGER.debug("Connected to MTX at %s:%s", self._host, self._port)
            await asyncio.sleep(0.2)
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

    async def _ensure_connected(self) -> None:
        if self._writer is None:
            if self._consecutive_failures > 0:
                delay = min(RECONNECT_DELAY * self._consecutive_failures, 10.0)
                await asyncio.sleep(delay)
            await self.connect()

    def _build_command(self, command: str, argument: str = "0") -> bytes:
        return f"#|X001|{self._source}|{command}|{argument}|U|\r\n".encode()

    @staticmethod
    def _expected_response_cmds(command: str) -> set[str]:
        result = {command}
        if command.startswith("G"):
            result.add(command[1:])
        return result

    async def _read_response(self, expected_cmds: set[str], timeout: float = 2.0) -> str:
        buffer = b""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout

        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            try:
                chunk = await asyncio.wait_for(
                    self._reader.read(4096),
                    timeout=min(remaining, 0.5),
                )
                if not chunk:
                    break
                buffer += chunk
                _LOGGER.debug("MTX raw recv chunk: %s", chunk[:200])

                text = buffer.decode(errors="replace")
                for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
                    line = line.strip()
                    if not line or not line.startswith("#|"):
                        continue

                    parts = line.split("|")
                    if len(parts) < 5:
                        continue

                    if parts[1].strip() == "ALL":
                        continue

                    resp_cmd = parts[3].strip()
                    if resp_cmd in expected_cmds:
                        _LOGGER.debug("MTX matched %s: %s", expected_cmds, line[:120])
                        return line

                    _LOGGER.debug(
                        "Skipping mismatched response: got '%s', expected %s: %s",
                        resp_cmd, expected_cmds, line[:80],
                    )

            except asyncio.TimeoutError:
                continue

        if buffer:
            _LOGGER.debug(
                "MTX no match in buffer for %s: %s",
                expected_cmds, buffer.decode(errors="replace")[:200],
            )
        return ""

    async def _send_and_receive(self, command: str, argument: str = "0") -> str:
        expected_cmds = self._expected_response_cmds(command)

        async with self._lock:
            for attempt in range(MAX_RETRIES + 1):
                try:
                    await self._ensure_connected()
                except ConnectionError:
                    if attempt < MAX_RETRIES:
                        self._consecutive_failures += 1
                        continue
                    raise

                raw = self._build_command(command, argument)
                try:
                    self._writer.write(raw)
                    await self._writer.drain()

                    response = await self._read_response(expected_cmds, timeout=2.0)

                    if not response:
                        if attempt < MAX_RETRIES:
                            await self.disconnect()
                            continue
                        return ""

                    self._consecutive_failures = 0
                    return response

                except (asyncio.TimeoutError, OSError, ConnectionError) as err:
                    _LOGGER.warning("MTX error cmd=%s attempt=%d: %s", command, attempt, err)
                    await self.disconnect()
                    self._consecutive_failures += 1
                    if attempt < MAX_RETRIES:
                        continue
                    raise ConnectionError(f"Lost connection to MTX: {err}") from err

        return ""

    @staticmethod
    def _get_data_field(response: str) -> str:
        if not response:
            return ""
        parts = response.split("|")
        if len(parts) >= 5:
            return parts[4].strip()
        return ""

    @staticmethod
    def _is_success(response: str) -> bool:
        if not response:
            return False
        return MTXClient._get_data_field(response) == "+"

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
        zones: dict[int, dict[str, Any]] = {}

        volumes = await self._get_bulk("GVALL", zones_count)
        await asyncio.sleep(INTER_COMMAND_DELAY)
        routings = await self._get_bulk("GRALL", zones_count)
        await asyncio.sleep(INTER_COMMAND_DELAY)
        mutes = await self._get_bulk("GMALL", zones_count)
        await asyncio.sleep(INTER_COMMAND_DELAY)

        if not volumes and not routings and not mutes:
            _LOGGER.warning("No bulk data received, falling back to per-zone queries")
            return await self._get_all_zones_individual(zones_count)

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
        resp = await self._send_and_receive(command)
        data = self._get_data_field(resp)

        if not data or data == "+":
            _LOGGER.warning("No data for bulk command %s", command)
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

    async def _get_single_value(self, command: str) -> int | None:
        resp = await self._send_and_receive(command)
        data = self._get_data_field(resp)

        if not data or data == "+":
            return None

        try:
            return int(data)
        except ValueError:
            _LOGGER.debug("Could not parse %s response: %s", command, data)
            return None

    async def set_volume(self, zone: int, volume: int) -> bool:
        volume = max(0, min(70, volume))
        resp = await self._send_and_receive(f"SV{zone}", str(volume))
        return self._is_success(resp)

    async def set_volume_up(self, zone: int) -> bool:
        resp = await self._send_and_receive(f"SVU0{zone}")
        return self._is_success(resp)

    async def set_volume_down(self, zone: int) -> bool:
        resp = await self._send_and_receive(f"SVD0{zone}")
        return self._is_success(resp)

    async def set_routing(self, zone: int, input_id: int) -> bool:
        resp = await self._send_and_receive(f"SR{zone}", str(input_id))
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
        resp = await self._send_and_receive("SAVE")
        return self._is_success(resp)

    async def get_version(self) -> str:
        resp = await self._send_and_receive("GSV")
        data = self._get_data_field(resp)
        return data if data and data != "+" else "Unknown"
