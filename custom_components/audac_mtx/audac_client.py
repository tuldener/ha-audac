"""Base TCP client for communicating with Audac audio devices.

Protocol format (shared by MTX48/MTX88 and XMP44):
  Command: #|<address>|<source>|CMD|arg|U|\r\n
  Answer:  #|<source>|<address>|CMD|data|checksum|\r\n
  Update:  #|ALL|<address>|CMD|data|checksum|\r\n  (broadcast after SET)

Addresses:
  MTX48/MTX88: X001
  XMP44:       D001

GET responses strip the 'G' prefix: GZI01 → ZI01, GVALL → VALL
SET responses echo the command with '+' as data.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

MAX_RETRIES = 1
RECONNECT_DELAY = 1.0
RECONNECT_MAX_DELAY = 30.0
INTER_COMMAND_DELAY = 0.15

# Hard timeout for a single send-and-receive cycle (seconds).
# This covers: lock acquisition + connect + send + read + 1 retry.
# Must be larger than the longest inner read timeout (5s for GFAV)
# plus overhead for connect/lock. 8s gives 3s margin.
COMMAND_TIMEOUT = 8.0


class AudacClient:
    """Base TCP client for Audac devices."""

    # Subclasses MUST override this with the device address (e.g. "X001", "D001")
    DEVICE_ADDRESS: str = "X001"

    def __init__(self, host: str, port: int = 5001, source: str = "web") -> None:
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
            _LOGGER.debug(
                "Connected to Audac %s at %s:%s",
                self.DEVICE_ADDRESS, self._host, self._port,
            )
            await asyncio.sleep(0.3)
            await self._flush_buffer()
        except Exception as err:
            self._reader = None
            self._writer = None
            raise ConnectionError(
                f"Cannot connect to Audac device at {self._host}:{self._port}: {err}"
            ) from err

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
                delay = min(
                    RECONNECT_DELAY * (2 ** (self._consecutive_failures - 1)),
                    RECONNECT_MAX_DELAY,
                )
                await asyncio.sleep(delay)
            await self.connect()

    async def _flush_buffer(self) -> None:
        if self._reader is None:
            return
        flushed = b""
        while True:
            try:
                chunk = await asyncio.wait_for(self._reader.read(4096), timeout=0.05)
                if not chunk:
                    break
                flushed += chunk
            except asyncio.TimeoutError:
                break
        if flushed:
            _LOGGER.debug("Audac flushed %d bytes of stale data", len(flushed))

    def _build_command(self, command: str, argument: str = "0") -> bytes:
        return f"#|{self.DEVICE_ADDRESS}|{self._source}|{command}|{argument}|U|\r\n".encode()

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
                _LOGGER.debug("Audac raw recv chunk (%d bytes): %s", len(chunk), chunk[:200])
                text = buffer.decode(errors="replace")
                lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
                for line in lines[:-1]:
                    line = line.strip()
                    if not line or not line.startswith("#|"):
                        continue
                    parts = line.split("|")
                    if len(parts) < 5:
                        continue
                    # Determine response command field position:
                    # Directed: #|source|address|CMD|data|checksum  → parts[3]
                    # Broadcast: #|ALL|address|CMD|data|checksum    → parts[3]
                    if parts[1].strip() == "ALL":
                        # Broadcast response — accept if command matches
                        resp_cmd = parts[3].strip()
                        if resp_cmd in expected_cmds:
                            _LOGGER.debug("Audac matched (ALL) %s: %s", expected_cmds, line[:120])
                            return line
                        continue
                    resp_cmd = parts[3].strip()
                    if resp_cmd in expected_cmds:
                        _LOGGER.debug("Audac matched %s: %s", expected_cmds, line[:120])
                        return line
                    _LOGGER.debug(
                        "Skipping mismatched response: got '%s', expected %s: %s",
                        resp_cmd, expected_cmds, line[:80],
                    )
                last_line = lines[-1]
                if last_line and last_line.strip():
                    buffer = last_line.encode()
                else:
                    buffer = b""
            except asyncio.TimeoutError:
                continue
        if buffer:
            _LOGGER.debug(
                "Audac no match in buffer for %s: %s",
                expected_cmds, buffer.decode(errors="replace")[:200],
            )
        return ""

    async def _send_and_receive(self, command: str, argument: str = "0", timeout: float = 2.0) -> str:
        """Send a command and wait for a matching response.

        The entire operation (including lock acquisition) is wrapped in
        COMMAND_TIMEOUT to prevent the lock from being held indefinitely
        when the TCP connection silently hangs.
        """
        expected_cmds = self._expected_response_cmds(command)

        async def _do() -> str:
            async with self._lock:
                for attempt in range(MAX_RETRIES + 1):
                    try:
                        await self._ensure_connected()
                    except ConnectionError:
                        if attempt < MAX_RETRIES:
                            self._consecutive_failures += 1
                            continue
                        raise
                    await self._flush_buffer()
                    raw = self._build_command(command, argument)
                    try:
                        self._writer.write(raw)
                        await self._writer.drain()
                        response = await self._read_response(expected_cmds, timeout=timeout)
                        if not response:
                            if attempt < MAX_RETRIES:
                                await self.disconnect()
                                continue
                            return ""
                        self._consecutive_failures = 0
                        return response
                    except (asyncio.TimeoutError, OSError, ConnectionError) as err:
                        _LOGGER.warning(
                            "Audac error cmd=%s attempt=%d: %s", command, attempt, err
                        )
                        await self.disconnect()
                        self._consecutive_failures += 1
                        if attempt < MAX_RETRIES:
                            continue
                        raise ConnectionError(f"Lost connection to Audac device: {err}") from err
            return ""

        try:
            return await asyncio.wait_for(_do(), timeout=COMMAND_TIMEOUT)
        except asyncio.TimeoutError:
            if self._lock.locked():
                _LOGGER.warning(
                    "Audac command %s timed out with lock held — creating new Lock to recover",
                    command,
                )
                self._lock = asyncio.Lock()
            _LOGGER.warning(
                "Audac command %s timed out after %.0fs — forcing disconnect",
                command, COMMAND_TIMEOUT,
            )
            self._writer = None
            self._reader = None
            self._consecutive_failures += 1
            raise ConnectionError(f"Command {command} timed out") from None

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
        return AudacClient._get_data_field(response) == "+"

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

    async def _get_string_value(self, command: str) -> str | None:
        """Send a GET command and return the data field as string."""
        resp = await self._send_and_receive(command)
        data = self._get_data_field(resp)
        if not data or data == "+":
            return None
        return data
