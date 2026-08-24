"""Tests for the Audac MTX48/MTX88 TCP client (mtx_client.py)."""
from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock

import pytest

from custom_components.audac_mtx import mtx_client as mtx_module
from custom_components.audac_mtx.mtx_client import MTXClient

from tests.test_audac_client import FakeDevice, patch_connection


@pytest.fixture(autouse=True)
def fast_polling(monkeypatch):
    """Remove the inter-command pacing delay for fast tests."""
    monkeypatch.setattr(mtx_module, "INTER_COMMAND_DELAY", 0)


@pytest.fixture
def device() -> FakeDevice:
    return FakeDevice("X001")


@pytest.fixture
async def client(device: FakeDevice):
    connections: list = []
    mtx = MTXClient("192.0.2.10")
    with patch_connection(device, connections):
        await mtx.connect()
        mtx.test_connections = connections
        yield mtx
        await mtx.disconnect()


# ── SET command frames ──────────────────────────────────────────────


async def test_set_command_frames(client: MTXClient, device: FakeDevice) -> None:
    """Every SET helper sends the documented command and argument."""
    cases = [
        (client.set_volume(2, 40), ("SV2", "40")),
        (client.set_volume(1, 99), ("SV1", "70")),   # clamped to min level
        (client.set_volume(1, -5), ("SV1", "0")),    # clamped to max level
        (client.set_volume_up(1), ("SVU01", "0")),
        (client.set_volume_down(3), ("SVD03", "0")),
        (client.set_routing(1, 3), ("SR1", "3")),
        (client.set_routing_up(2), ("SRU02", "0")),
        (client.set_routing_down(2), ("SRD02", "0")),
        (client.set_bass(1, 8), ("SB01", "8")),
        (client.set_bass(1, 20), ("SB01", "14")),    # clamped high
        (client.set_bass(1, -3), ("SB01", "0")),     # clamped low
        (client.set_treble(4, 5), ("ST04", "5")),
        (client.set_treble(4, 15), ("ST04", "14")),
        (client.set_mute(1, True), ("SM01", "1")),
        (client.set_mute(1, False), ("SM01", "0")),
        (client.save(), ("SAVE", "0")),
        (client.factory_reset(), ("DEF", "0")),
    ]
    for coro, expected in cases:
        device.commands.clear()
        assert await coro is True
        assert device.commands == [expected]


async def test_set_volume_raw_bytes_on_wire(client: MTXClient, device: FakeDevice) -> None:
    assert await client.set_volume(2, 40) is True
    writer = client.test_connections[0][1]
    assert writer.written[-1] == b"#|X001|web|SV2|40|U|\r\n"


async def test_set_command_failure_returns_false(client: MTXClient, device: FakeDevice) -> None:
    device.replies["SM01"] = "0"  # device answers with data instead of '+'
    assert await client.set_mute(1, True) is False


# ── Zone info parsing ───────────────────────────────────────────────


async def test_get_zone_info_parses_full_response(client: MTXClient, device: FakeDevice) -> None:
    device.replies["GZI01"] = "20^3^0^07^07"
    info = await client.get_zone_info(1)
    assert info == {
        "volume": 20,
        "volume_db": -20,
        "routing": 3,
        "source_name": "Line 3",
        "mute": False,
        "bass": 7,
        "bass_db": 0,
        "treble": 7,
        "treble_db": 0,
    }


async def test_get_zone_info_muted_with_tone(client: MTXClient, device: FakeDevice) -> None:
    device.replies["GZI02"] = "40^1^1^08^05"
    info = await client.get_zone_info(2)
    assert info["mute"] is True
    assert info["volume_db"] == -40
    assert info["source_name"] == "Mic 1"
    assert info["bass_db"] == 2
    assert info["treble_db"] == -4


async def test_get_zone_info_unknown_routing_name(client: MTXClient, device: FakeDevice) -> None:
    device.replies["GZI01"] = "20^42^0^07^07"
    info = await client.get_zone_info(1)
    assert info["source_name"] == "Input 42"


async def test_get_zone_info_empty_data(client: MTXClient, device: FakeDevice) -> None:
    device.replies["GZI01"] = ""
    assert await client.get_zone_info(1) == {}
    device.replies["GZI01"] = "+"
    assert await client.get_zone_info(1) == {}


async def test_get_zone_info_too_few_fields(client: MTXClient, device: FakeDevice, caplog) -> None:
    caplog.set_level(logging.WARNING, logger="custom_components.audac_mtx.mtx_client")
    device.replies["GZI01"] = "20^3^0"
    assert await client.get_zone_info(1) == {}
    assert "expected >=5 fields" in caplog.text


async def test_get_zone_info_unparsable_values(client: MTXClient, device: FakeDevice, caplog) -> None:
    caplog.set_level(logging.WARNING, logger="custom_components.audac_mtx.mtx_client")
    device.replies["GZI01"] = "a^b^c^d^e"
    assert await client.get_zone_info(1) == {}
    assert "parse error" in caplog.text


# ── get_all_zones ───────────────────────────────────────────────────


async def test_get_all_zones_success(client: MTXClient, device: FakeDevice) -> None:
    device.replies["GZI01"] = "20^3^0^07^07"
    device.replies["GZI02"] = "40^1^1^08^05"
    zones = await client.get_all_zones(zones_count=2)
    assert set(zones) == {1, 2}
    assert zones[1]["volume"] == 20
    assert zones[2]["mute"] is True


async def test_get_all_zones_failed_zone_keeps_previous(
    client: MTXClient, device: FakeDevice, caplog
) -> None:
    caplog.set_level(logging.DEBUG, logger="custom_components.audac_mtx.mtx_client")
    device.replies["GZI01"] = "20^3^0^07^07"
    device.replies["GZI02"] = ""  # zone 2 glitch
    device.replies["GZI03"] = "10^4^0^07^07"
    device.replies["GZI04"] = "15^5^0^07^07"
    previous = {2: {"volume": 33, "routing": 2, "mute": False}}
    zones = await client.get_all_zones(zones_count=4, previous=previous)
    assert zones[2] == previous[2]
    assert zones[1]["volume"] == 20
    # 1 of 4 failed (25% < 50%): stays at DEBUG, no warning escalation
    warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert not warning_records
    assert "kept previous state" in caplog.text


async def test_get_all_zones_failed_zone_without_previous_is_dropped(
    client: MTXClient, device: FakeDevice
) -> None:
    device.replies["GZI01"] = "20^3^0^07^07"
    device.replies["GZI02"] = ""
    zones = await client.get_all_zones(zones_count=2)
    assert set(zones) == {1}


async def test_get_all_zones_warning_at_half_failed(
    client: MTXClient, device: FakeDevice, caplog
) -> None:
    caplog.set_level(logging.DEBUG, logger="custom_components.audac_mtx.mtx_client")
    device.replies["GZI01"] = "20^3^0^07^07"
    device.replies["GZI02"] = ""
    previous = {2: {"volume": 33}}
    zones = await client.get_all_zones(zones_count=2, previous=previous)
    assert zones[2] == previous[2]
    warning_records = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and "kept previous state" in r.getMessage()
    ]
    assert warning_records  # 1 of 2 failed (50%) escalates to WARNING


async def test_get_all_zones_generic_error_keeps_previous(client: MTXClient) -> None:
    previous = {2: {"volume": 33}}
    client.get_zone_info = AsyncMock(
        side_effect=[{"volume": 20, "routing": 3}, ValueError("garbled")]
    )
    zones = await client.get_all_zones(zones_count=2, previous=previous)
    assert zones[1] == {"volume": 20, "routing": 3}
    assert zones[2] == previous[2]


async def test_get_all_zones_connection_error_propagates(client: MTXClient) -> None:
    client.get_zone_info = AsyncMock(side_effect=ConnectionError("gone"))
    with pytest.raises(ConnectionError):
        await client.get_all_zones(zones_count=2, previous={1: {}})


async def test_get_all_zones_timeout_forces_disconnect(
    client: MTXClient, monkeypatch
) -> None:
    monkeypatch.setattr(mtx_module, "GET_ALL_ZONES_TIMEOUT", 0.05)

    async def hang(zone):
        await asyncio.sleep(5)

    client.get_zone_info = hang
    failures_before = client._consecutive_failures
    writer = client.test_connections[0][1]
    with pytest.raises(ConnectionError, match="timed out"):
        await client.get_all_zones(zones_count=2)
    assert client.connected is False
    assert writer.closed is True
    assert client._consecutive_failures == failures_before + 1


# ── Simple getters ──────────────────────────────────────────────────


async def test_get_version(client: MTXClient, device: FakeDevice) -> None:
    device.replies["GSV"] = "V1.1"
    assert await client.get_version() == "V1.1"
    device.replies["GSV"] = ""
    assert await client.get_version() == "Unknown"
    device.replies["GSV"] = "+"
    assert await client.get_version() == "Unknown"


async def test_get_zone_volume(client: MTXClient, device: FakeDevice) -> None:
    device.replies["GV01"] = "20"
    assert await client.get_zone_volume(1) == 20


async def test_get_zone_routing(client: MTXClient, device: FakeDevice) -> None:
    device.replies["GR03"] = "3"
    assert await client.get_zone_routing(3) == 3


async def test_get_zone_mute(client: MTXClient, device: FakeDevice) -> None:
    device.replies["GM01"] = "1"
    assert await client.get_zone_mute(1) is True
    device.replies["GM01"] = "0"
    assert await client.get_zone_mute(1) is False
    device.replies["GM01"] = "x"
    assert await client.get_zone_mute(1) is None
