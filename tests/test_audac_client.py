"""Tests for the shared Audac TCP base client (audac_client.py).

Also provides the fake TCP device harness reused by the MTX and XMP44
client tests (imported as tests.test_audac_client).
"""
from __future__ import annotations

import asyncio
from collections import deque
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.audac_mtx import audac_client as ac_module
from custom_components.audac_mtx.audac_client import AudacClient


# ── Fake device harness ─────────────────────────────────────────────


class FakeDevice:
    """Scripted AUDAC device behind a fake StreamReader/StreamWriter pair.

    Responses follow the real protocol frame:
        #|<source>|<address>|CMD|data|U|\r\n
    GET replies strip the leading 'G' from the command (GZI01 -> ZI01),
    SET replies echo the command with '+' as data.
    """

    def __init__(self, address: str = "X001") -> None:
        self.address = address
        self.commands: list[tuple[str, str]] = []
        # cmd -> data string, list of data strings (consumed per call),
        # or None (no reply at all)
        self.replies: dict[str, Any] = {}
        self.queue: deque[bytes] = deque()
        self.eof = False
        self.ack_unknown_sets = True
        self.fail_drain = False
        # Raw frames queued verbatim before the scripted reply on next write
        self.raw_frames: list[bytes] = []

    def reply_frame(self, cmd: str, data: str) -> bytes:
        resp_cmd = cmd[1:] if cmd.startswith("G") else cmd
        return f"#|web|{self.address}|{resp_cmd}|{data}|U|\r\n".encode()

    def handle_write(self, raw: bytes) -> None:
        line = raw.decode().strip()
        parts = line.split("|")
        cmd, arg = parts[3], parts[4]
        self.commands.append((cmd, arg))
        for frame in self.raw_frames:
            self.queue.append(frame)
        self.raw_frames = []
        if cmd in self.replies:
            entry = self.replies[cmd]
            if isinstance(entry, list):
                entry = entry.pop(0) if entry else None
            if entry is None:
                return
            self.queue.append(self.reply_frame(cmd, entry))
        elif not cmd.startswith("G") and self.ack_unknown_sets:
            self.queue.append(self.reply_frame(cmd, "+"))


class FakeReader:
    def __init__(self, device: FakeDevice) -> None:
        self._device = device

    async def read(self, n: int) -> bytes:
        while not self._device.queue:
            if self._device.eof:
                return b""
            await asyncio.sleep(0.005)
        return self._device.queue.popleft()


class FakeWriter:
    def __init__(self, device: FakeDevice) -> None:
        self._device = device
        self.closed = False
        self.written: list[bytes] = []

    def write(self, data: bytes) -> None:
        self.written.append(data)
        self._device.handle_write(data)

    async def drain(self) -> None:
        if self._device.fail_drain:
            raise OSError("drain failed")

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        return None


def patch_connection(device: FakeDevice, connections: list | None = None):
    """Patch asyncio.open_connection to hand out fake reader/writer pairs."""

    async def _open(host, port):
        pair = (FakeReader(device), FakeWriter(device))
        if connections is not None:
            connections.append(pair)
        return pair

    return patch("asyncio.open_connection", side_effect=_open)


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def device() -> FakeDevice:
    return FakeDevice("X001")


@pytest.fixture
def fast_backoff(monkeypatch):
    monkeypatch.setattr(ac_module, "RECONNECT_DELAY", 0.001)
    monkeypatch.setattr(ac_module, "RECONNECT_MAX_DELAY", 0.005)


# ── Frame building / parsing helpers ────────────────────────────────


def test_build_command_frame() -> None:
    client = AudacClient("192.0.2.1")
    assert client._build_command("GZI01") == b"#|X001|web|GZI01|0|U|\r\n"
    assert client._build_command("SV2", "40") == b"#|X001|web|SV2|40|U|\r\n"


def test_build_command_uses_custom_source_and_address() -> None:
    class _D001Client(AudacClient):
        DEVICE_ADDRESS = "D001"

    client = _D001Client("192.0.2.1", port=5001, source="ha")
    assert client._build_command("GTPS") == b"#|D001|ha|GTPS|0|U|\r\n"


def test_expected_response_cmds() -> None:
    assert AudacClient._expected_response_cmds("GZI01") == {"GZI01", "ZI01"}
    assert AudacClient._expected_response_cmds("SV2") == {"SV2"}


def test_get_data_field() -> None:
    assert AudacClient._get_data_field("#|web|X001|ZI01|20^3^0^07^07|U|") == "20^3^0^07^07"
    assert AudacClient._get_data_field("") == ""
    assert AudacClient._get_data_field("#|web|X001|ZI01") == ""


def test_is_success() -> None:
    assert AudacClient._is_success("#|web|X001|SV2|+|U|") is True
    assert AudacClient._is_success("#|web|X001|SV2|20|U|") is False
    assert AudacClient._is_success("") is False


# ── Connect / disconnect ────────────────────────────────────────────


async def test_connect_and_disconnect(device: FakeDevice) -> None:
    connections: list = []
    client = AudacClient("192.0.2.1")
    assert client.connected is False
    with patch_connection(device, connections):
        await client.connect()
        assert client.connected is True
        assert client.host == "192.0.2.1"
        # Second connect is a no-op while connected
        await client.connect()
        assert len(connections) == 1
        writer = connections[0][1]
        await client.disconnect()
        assert client.connected is False
        assert writer.closed is True
        # Disconnect while not connected is a no-op
        await client.disconnect()


async def test_connect_resets_failure_counter(device: FakeDevice) -> None:
    client = AudacClient("192.0.2.1")
    client._consecutive_failures = 4
    with patch_connection(device):
        await client.connect()
    assert client._consecutive_failures == 0


async def test_connect_failure_raises_connection_error() -> None:
    client = AudacClient("192.0.2.1")
    with patch("asyncio.open_connection", side_effect=OSError("refused")):
        with pytest.raises(ConnectionError, match="Cannot connect"):
            await client.connect()
    assert client.connected is False
    assert client._reader is None


async def test_connect_flushes_stale_data(device: FakeDevice) -> None:
    device.queue.append(b"#|ALL|X001|V01|27|U|\r\n")
    device.queue.append(b"#|ALL|X001|M01|1|U|\r\n")
    client = AudacClient("192.0.2.1")
    with patch_connection(device):
        await client.connect()
        assert not device.queue
        await client.disconnect()


async def test_disconnect_swallows_wait_closed_errors(device: FakeDevice) -> None:
    client = AudacClient("192.0.2.1")
    with patch_connection(device):
        await client.connect()
        client._writer.wait_closed = AsyncMock(side_effect=OSError("boom"))
        await client.disconnect()
    assert client.connected is False


async def test_connect_closes_writer_when_flush_fails(device: FakeDevice) -> None:
    """A failure after the socket opened still closes the writer."""
    connections: list = []
    client = AudacClient("192.0.2.1")
    with (
        patch_connection(device, connections),
        patch.object(client, "_flush_buffer", side_effect=OSError("reset")),
    ):
        with pytest.raises(ConnectionError, match="Cannot connect"):
            await client.connect()
    assert connections[0][1].closed is True
    assert client.connected is False


async def test_flush_buffer_without_reader_and_on_eof(device: FakeDevice) -> None:
    client = AudacClient("192.0.2.1")
    # No reader: early return
    await client._flush_buffer()
    # EOF while flushing: read returns b"" and the loop breaks
    client._reader = FakeReader(device)
    device.eof = True
    await client._flush_buffer()


# ── Backoff behaviour ───────────────────────────────────────────────


@pytest.mark.parametrize(
    ("failures", "expected_delay"),
    [(1, 1.0), (2, 2.0), (3, 4.0), (4, 5.0), (10, 5.0)],
)
async def test_ensure_connected_backoff_delays(failures: int, expected_delay: float) -> None:
    client = AudacClient("192.0.2.1")
    client._consecutive_failures = failures
    with (
        patch("asyncio.sleep", new=AsyncMock()) as sleep_mock,
        patch.object(client, "connect", new=AsyncMock()),
    ):
        await client._ensure_connected()
    sleep_mock.assert_awaited_once_with(expected_delay)
    assert client._in_backoff_sleep is False


async def test_ensure_connected_no_backoff_without_failures() -> None:
    client = AudacClient("192.0.2.1")
    with (
        patch("asyncio.sleep", new=AsyncMock()) as sleep_mock,
        patch.object(client, "connect", new=AsyncMock()) as connect_mock,
    ):
        await client._ensure_connected()
    sleep_mock.assert_not_awaited()
    connect_mock.assert_awaited_once()


async def test_ensure_connected_skips_when_connected(device: FakeDevice) -> None:
    client = AudacClient("192.0.2.1")
    connections: list = []
    with patch_connection(device, connections):
        await client.connect()
        await client._ensure_connected()
        assert len(connections) == 1
        await client.disconnect()


# ── _read_response parsing ──────────────────────────────────────────


async def test_read_response_directed(device: FakeDevice) -> None:
    client = AudacClient("192.0.2.1")
    client._reader = FakeReader(device)
    device.queue.append(b"#|web|X001|ZI01|20^3^0^07^07|U|\r\n")
    resp = await client._read_response({"GZI01", "ZI01"}, timeout=1.0)
    assert resp == "#|web|X001|ZI01|20^3^0^07^07|U|"


async def test_read_response_broadcast(device: FakeDevice) -> None:
    client = AudacClient("192.0.2.1")
    client._reader = FakeReader(device)
    device.queue.append(b"#|ALL|X001|V01|27|U|\r\n")
    resp = await client._read_response({"V01"}, timeout=1.0)
    assert resp == "#|ALL|X001|V01|27|U|"


async def test_read_response_skips_mismatched_and_garbage(device: FakeDevice) -> None:
    client = AudacClient("192.0.2.1")
    client._reader = FakeReader(device)
    device.queue.append(b"garbage line\r\n")
    device.queue.append(b"#|short\r\n")
    device.queue.append(b"#|ALL|X001|M01|1|U|\r\n")  # broadcast, wrong cmd
    device.queue.append(b"#|web|X001|R01|3|U|\r\n")  # directed, wrong cmd
    device.queue.append(b"#|web|X001|V01|20|U|\r\n")
    resp = await client._read_response({"V01"}, timeout=1.0)
    assert resp == "#|web|X001|V01|20|U|"


async def test_read_response_reassembles_partial_frames(device: FakeDevice) -> None:
    client = AudacClient("192.0.2.1")
    client._reader = FakeReader(device)
    device.queue.append(b"#|web|X001|ZI0")
    device.queue.append(b"1|20^3^0^07^07|U|\r\n")
    resp = await client._read_response({"ZI01"}, timeout=1.0)
    assert resp == "#|web|X001|ZI01|20^3^0^07^07|U|"


async def test_read_response_timeout_returns_empty(device: FakeDevice) -> None:
    client = AudacClient("192.0.2.1")
    client._reader = FakeReader(device)
    # Leave an unterminated partial frame in the buffer to hit the debug branch
    device.queue.append(b"#|web|X001|ZI01|20")
    resp = await client._read_response({"V01"}, timeout=0.2)
    assert resp == ""


async def test_read_response_eof_returns_empty(device: FakeDevice) -> None:
    client = AudacClient("192.0.2.1")
    client._reader = FakeReader(device)
    device.eof = True
    resp = await client._read_response({"V01"}, timeout=1.0)
    assert resp == ""


# ── _send_and_receive ───────────────────────────────────────────────


async def test_send_and_receive_success_resets_failures(device: FakeDevice, fast_backoff) -> None:
    device.replies["GSV"] = "V1.1"
    client = AudacClient("192.0.2.1")
    client._consecutive_failures = 1
    with patch_connection(device):
        resp = await client._send_and_receive("GSV")
        assert AudacClient._get_data_field(resp) == "V1.1"
        assert client._consecutive_failures == 0
        assert device.commands == [("GSV", "0")]
        await client.disconnect()


async def test_send_and_receive_sends_exact_bytes(device: FakeDevice) -> None:
    device.replies["SV2"] = "+"
    connections: list = []
    client = AudacClient("192.0.2.1")
    with patch_connection(device, connections):
        resp = await client._send_and_receive("SV2", "40")
        assert AudacClient._is_success(resp)
        writer = connections[0][1]
        assert b"#|X001|web|SV2|40|U|\r\n" in writer.written
        await client.disconnect()


async def test_send_empty_response_retries_then_returns_empty(device: FakeDevice) -> None:
    connections: list = []
    client = AudacClient("192.0.2.1")
    with patch_connection(device, connections):
        resp = await client._send_and_receive("GV01", timeout=0.1)
        assert resp == ""
        # Two attempts, reconnect between them
        assert device.commands == [("GV01", "0"), ("GV01", "0")]
        assert len(connections) == 2
        # An empty response is not a transport failure
        assert client._consecutive_failures == 0
        await client.disconnect()


async def test_send_empty_then_success_on_retry(device: FakeDevice) -> None:
    device.replies["GV01"] = [None, "20"]
    connections: list = []
    client = AudacClient("192.0.2.1")
    with patch_connection(device, connections):
        resp = await client._send_and_receive("GV01", timeout=0.15)
        assert AudacClient._get_data_field(resp) == "20"
        assert len(connections) == 2
        await client.disconnect()


async def test_send_transport_error_raises_after_retries(device: FakeDevice, fast_backoff) -> None:
    device.fail_drain = True
    client = AudacClient("192.0.2.1")
    with patch_connection(device):
        with pytest.raises(ConnectionError, match="Lost connection"):
            await client._send_and_receive("GV01", timeout=0.1)
    # attempt 0 fails (+1), the successful reconnect resets the counter,
    # then attempt 1 fails again (+1)
    assert client._consecutive_failures == 1
    assert client.connected is False


async def test_send_connect_error_retries_then_raises(fast_backoff) -> None:
    client = AudacClient("192.0.2.1")
    with patch("asyncio.open_connection", side_effect=OSError("refused")) as open_mock:
        with pytest.raises(ConnectionError, match="Cannot connect"):
            await client._send_and_receive("GV01", timeout=0.1)
    assert open_mock.call_count == 2
    assert client._consecutive_failures == 1


async def test_command_timeout_forces_disconnect(device: FakeDevice, monkeypatch) -> None:
    monkeypatch.setattr(ac_module, "COMMAND_TIMEOUT", 0.3)
    client = AudacClient("192.0.2.1")
    connections: list = []
    with patch_connection(device, connections):
        # No reply and an inner timeout longer than COMMAND_TIMEOUT
        with pytest.raises(ConnectionError, match="timed out"):
            await client._send_and_receive("GV01", timeout=5.0)
    assert client.connected is False
    assert connections[0][1].closed is True
    assert client._consecutive_failures == 1


async def test_command_timeout_in_backoff_does_not_ratchet(monkeypatch) -> None:
    monkeypatch.setattr(ac_module, "COMMAND_TIMEOUT", 0.2)
    monkeypatch.setattr(ac_module, "RECONNECT_DELAY", 30.0)
    monkeypatch.setattr(ac_module, "RECONNECT_MAX_DELAY", 30.0)
    client = AudacClient("192.0.2.1")
    client._consecutive_failures = 3
    with patch("asyncio.open_connection", side_effect=AssertionError("must not connect")):
        with pytest.raises(ConnectionError, match="timed out"):
            await client._send_and_receive("GV01")
    # Timed out inside the backoff sleep: counter untouched, flag reset
    assert client._consecutive_failures == 3
    assert client._in_backoff_sleep is False


# ── Value helpers ───────────────────────────────────────────────────


async def test_get_single_value(device: FakeDevice) -> None:
    client = AudacClient("192.0.2.1")
    with patch_connection(device):
        device.replies["GV01"] = "20"
        assert await client._get_single_value("GV01") == 20
        device.replies["GV01"] = "+"
        assert await client._get_single_value("GV01") is None
        device.replies["GV01"] = "abc"
        assert await client._get_single_value("GV01") is None
        device.replies["GV01"] = ""
        assert await client._get_single_value("GV01") is None
        await client.disconnect()


async def test_get_string_value(device: FakeDevice) -> None:
    client = AudacClient("192.0.2.1")
    with patch_connection(device):
        device.replies["GPRGN1"] = "Radio Swiss Jazz"
        assert await client._get_string_value("GPRGN1") == "Radio Swiss Jazz"
        device.replies["GPRGN1"] = "+"
        assert await client._get_string_value("GPRGN1") is None
        device.replies["GPRGN1"] = ""
        assert await client._get_string_value("GPRGN1") is None
        await client.disconnect()
