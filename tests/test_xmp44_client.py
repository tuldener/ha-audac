"""Tests for the Audac XMP44 SourceCon TCP client (xmp44_client.py)."""
from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock

import pytest

from custom_components.audac_mtx import xmp44_client as xmp_module
from custom_components.audac_mtx.xmp44_client import (
    MODULE_BMP40,
    MODULE_DMP40,
    MODULE_EMPTY,
    MODULE_FMP40,
    MODULE_IMP40,
    MODULE_MMP40,
    MODULE_NMP40,
    MODULE_TMP40,
    MODULE_UNSUPPORTED,
    XMP44Client,
)

from tests.test_audac_client import FakeDevice, patch_connection


@pytest.fixture(autouse=True)
def fast_polling(monkeypatch):
    monkeypatch.setattr(xmp_module, "INTER_COMMAND_DELAY", 0)


@pytest.fixture
def device() -> FakeDevice:
    return FakeDevice("D001")


@pytest.fixture
async def client(device: FakeDevice):
    connections: list = []
    xmp = XMP44Client("192.0.2.20")
    with patch_connection(device, connections):
        await xmp.connect()
        xmp.test_connections = connections
        yield xmp
        await xmp.disconnect()


@pytest.fixture
def offline_client() -> XMP44Client:
    """Client whose command methods get mocked — never touches the network."""
    return XMP44Client("192.0.2.20")


# ── Module detection ────────────────────────────────────────────────


async def test_detect_modules_parses_gtps(client: XMP44Client, device: FakeDevice) -> None:
    device.replies["GTPS"] = "4^1^15^6^IMP40 V 1.0.4^DMP40 ^No Module ^FMP40 V1.4.29"
    types = await client.detect_modules()
    assert types == {1: MODULE_IMP40, 2: MODULE_DMP40, 3: MODULE_EMPTY, 4: MODULE_FMP40}
    assert client.module_types == types
    assert client.module_names == {1: "IMP40", 2: "DMP40", 3: None, 4: "FMP40"}
    assert client._module_versions == {
        1: "IMP40 V 1.0.4",
        2: "DMP40",
        3: "No Module",
        4: "FMP40 V1.4.29",
    }
    assert client.get_installed_slots() == [1, 2, 4]
    assert client._build_command("GTPS") == b"#|D001|web|GTPS|0|U|\r\n"


async def test_detect_modules_short_and_garbled(client: XMP44Client, device: FakeDevice) -> None:
    device.replies["GTPS"] = "8^junk"
    types = await client.detect_modules()
    assert types == {1: MODULE_BMP40, 2: MODULE_EMPTY, 3: MODULE_EMPTY, 4: MODULE_EMPTY}
    assert client.module_names[2] is None


async def test_detect_modules_no_data(client: XMP44Client, device: FakeDevice, caplog) -> None:
    caplog.set_level(logging.WARNING, logger="custom_components.audac_mtx.xmp44_client")
    device.replies["GTPS"] = ""
    assert await client.detect_modules() == {}
    assert "GTPS returned no data" in caplog.text


def test_set_module_config_and_capabilities(offline_client: XMP44Client) -> None:
    offline_client.set_module_config(
        {1: MODULE_BMP40, 2: MODULE_DMP40, 3: MODULE_TMP40, 4: MODULE_UNSUPPORTED}
    )
    assert offline_client.get_installed_slots() == [1, 2, 3]
    assert offline_client.slot_has_playback(1) is True
    assert offline_client.slot_has_playback(2) is False
    assert offline_client.slot_has_song_info(1) is True
    assert offline_client.slot_has_tuner(2) is True
    assert offline_client.slot_has_tuner(3) is True
    assert offline_client.slot_has_dab(2) is True
    assert offline_client.slot_has_dab(3) is False
    # Unknown slot defaults to empty
    assert offline_client.slot_has_playback(4) is False
    assert offline_client.module_names[1] == "BMP40"
    assert offline_client.module_names[4] is None


# ── Output gain encoding ────────────────────────────────────────────


@pytest.mark.parametrize(("gain_db", "arg"), [(8, "0"), (0, "8"), (-20, "28"), (12, "0")])
async def test_set_output_gain_encoding(
    client: XMP44Client, device: FakeDevice, gain_db: int, arg: str
) -> None:
    assert await client.set_output_gain(1, gain_db) is True
    assert device.commands == [("SOG1", arg)]


async def test_get_output_gain_decoding(client: XMP44Client, device: FakeDevice) -> None:
    device.replies["GOG2"] = "28"
    assert await client.get_output_gain(2) == -20
    device.replies["GOG2"] = "0"
    assert await client.get_output_gain(2) == 8
    device.replies["GOG2"] = "+"
    assert await client.get_output_gain(2) is None


# ── SET command frames ──────────────────────────────────────────────


async def test_set_command_frames(client: XMP44Client, device: FakeDevice) -> None:
    cases = [
        (client.play(1), ("SPPLAY1", "0")),
        (client.stop(2), ("SPSTOP2", "0")),
        (client.pause(1), ("SPPAUS1", "0")),
        (client.next_track(1), ("SPNEXT1", "0")),
        (client.previous_track(1), ("SPPREV1", "0")),
        (client.fast_forward(1), ("SPFFW1", "0")),
        (client.fast_rewind(1), ("SPFRW1", "0")),
        (client.go_to_start(1), ("SPGTST1", "0")),
        (client.set_repeat(1, 4), ("SPRP1", "4")),
        (client.set_random(1, True), ("SPRND1", "1")),
        (client.set_random(1, False), ("SPRND1", "0")),
        (client.set_frequency(2, 10410), ("SFREQ2", "10410")),
        (client.search_up(2), ("SFSUP2", "0")),
        (client.search_down(2), ("SFSDN2", "0")),
        (client.select_preset(2, 3), ("SELPR2", "3")),
        (client.set_stereo(2, True), ("SSTSE2", "1")),
        (client.set_stereo(2, False), ("SSTSE2", "0")),
        (client.switch_band(2), ("SSBND2", "0")),
        (client.select_station(3, 4711), ("DWSEST3", "4711")),
        (client.trigger_start(4, 1), ("SSTR4", "1^1")),
        (client.trigger_stop(4, 2), ("SSTR4", "2^0")),
        (client.set_pairing(1, True), ("SPAIR1", "1")),
        (client.set_pairing(1, False), ("SPAIR1", "0")),
        (client.disconnect_device(1), ("SDISC1", "0")),
        (client.forget_device(1, 5), ("SFORGET1", "5")),
        (client.set_player_name(3, "Kitchen"), ("SPNAME3", "Kitchen")),
        (client.set_recorder_mode(1, True), ("SRRM1", "1")),
        (client.set_recorder_mode(1, False), ("SRRM1", "0")),
        (client.start_recording(1), ("SRSTA1", "0")),
        (client.stop_recording(1), ("SRSTO1", "0")),
        (client.pause_recording(1), ("SRPAU1", "0")),
        (client.cancel_recording(1), ("SRCAN1", "0")),
    ]
    for coro, expected in cases:
        device.commands.clear()
        assert await coro is True
        assert device.commands == [expected]


async def test_play_raw_bytes_on_wire(client: XMP44Client) -> None:
    assert await client.play(1) is True
    writer = client.test_connections[0][1]
    assert writer.written[-1] == b"#|D001|web|SPPLAY1|0|U|\r\n"


# ── Simple getters ──────────────────────────────────────────────────


async def test_simple_getters(client: XMP44Client, device: FakeDevice) -> None:
    device.replies.update(
        {
            "GFREQ1": "10410",
            "GPRES1": "0^10410^Radio 1",
            "GPRGN1": "SRF 3",
            "GPRGT1": "Now playing",
            "GSIGS1": "85",
            "GCH1": "5",
            "GSON1": "Track A",
            "GSTN1": "Radio Swiss Pop",
            "GPAIRS1": "3",
            "GPAIRL1": "1^Phone^AA:BB",
            "GCONNL1": "1^Phone^AA:BB",
            "GPNAME1": "NMP40 player 1",
            "GPIP1": "10.2.3.99",
        }
    )
    assert await client.get_frequency(1) == 10410
    assert await client.get_presets(1) == "0^10410^Radio 1"
    assert await client.get_program_name(1) == "SRF 3"
    assert await client.get_program_text(1) == "Now playing"
    assert await client.get_signal_strength(1) == 85
    assert await client.get_dab_channel(1) == 5
    assert await client.get_song_name(1) == "Track A"
    assert await client.get_station_name(1) == "Radio Swiss Pop"
    assert await client.get_pairing_state(1) == 3
    assert await client.get_paired_devices(1) == "1^Phone^AA:BB"
    assert await client.get_connected_device(1) == "1^Phone^AA:BB"
    assert await client.get_player_name(1) == "NMP40 player 1"
    assert await client.get_player_ip(1) == "10.2.3.99"


async def test_get_stereo_state(client: XMP44Client, device: FakeDevice) -> None:
    device.replies["GSTST1"] = "1"
    assert await client.get_stereo_state(1) is True
    device.replies["GSTST1"] = "0"
    assert await client.get_stereo_state(1) is False
    device.replies["GSTST1"] = "+"
    assert await client.get_stereo_state(1) is None


async def test_get_band(client: XMP44Client, device: FakeDevice) -> None:
    device.replies["GBND1"] = "0"
    assert await client.get_band(1) == "DAB"
    device.replies["GBND1"] = "1"
    assert await client.get_band(1) == "FM"
    device.replies["GBND1"] = "+"
    assert await client.get_band(1) is None


async def test_get_recorder_mode(client: XMP44Client, device: FakeDevice) -> None:
    device.replies["GRRM1"] = "1"
    assert await client.get_recorder_mode(1) == "recorder"
    device.replies["GRRM1"] = "0"
    assert await client.get_recorder_mode(1) == "player"
    device.replies["GRRM1"] = "+"
    assert await client.get_recorder_mode(1) is None


# ── Song info / player status ───────────────────────────────────────


async def test_get_song_info_full(client: XMP44Client, device: FakeDevice) -> None:
    device.replies["GPSI1"] = "Song^Artist^Album^240^37"
    info = await client.get_song_info(1)
    assert info == {
        "title": "Song",
        "artist": "Artist",
        "album": "Album",
        "duration": 240,
        "position": 37,
    }


async def test_get_song_info_partial_and_bad_numbers(
    client: XMP44Client, device: FakeDevice
) -> None:
    device.replies["GPSI1"] = "Song^Artist"
    assert await client.get_song_info(1) == {"title": "Song", "artist": "Artist"}
    device.replies["GPSI1"] = "Song^Artist^Album^abc^xyz"
    info = await client.get_song_info(1)
    assert info["album"] == "Album"
    assert "duration" not in info
    assert "position" not in info
    device.replies["GPSI1"] = ""
    assert await client.get_song_info(1) is None
    device.replies["GPSI1"] = "+"
    assert await client.get_song_info(1) is None


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ("0^1^0", "playing"),
        ("1^0^0", "paused"),
        ("0^0^0", "stopped"),
        ("0^0^1", "recording"),
        ("x^y^z", "unknown"),
        ("1", "unknown"),
        ("", "unknown"),
        ("+", "unknown"),
    ],
)
async def test_get_player_status(
    client: XMP44Client, device: FakeDevice, data: str, expected: str
) -> None:
    device.replies["GPSTAT2"] = data
    assert await client.get_player_status(2) == expected


# ── Bluetooth info ──────────────────────────────────────────────────


async def test_get_bluetooth_info(client: XMP44Client, device: FakeDevice) -> None:
    device.replies["GBMPI2"] = "1.4^BMP40 Living^00:11:22:33:44:55"
    assert await client.get_bluetooth_info(2) == {
        "version": "1.4",
        "name": "BMP40 Living",
        "address": "00:11:22:33:44:55",
    }
    device.replies["GBMPI2"] = "1.4"
    assert await client.get_bluetooth_info(2) == {"version": "1.4"}
    device.replies["GBMPI2"] = ""
    assert await client.get_bluetooth_info(2) is None


# ── Favourites ──────────────────────────────────────────────────────


async def test_get_favourites_parsing(client: XMP44Client, device: FakeDevice) -> None:
    device.replies["GFAV1"] = "0^Radio A^101^1^Radio B^102"
    favs = await client.get_favourites(1)
    assert favs == [
        {"index": 0, "name": "Radio A", "pointer": "101"},
        {"index": 1, "name": "Radio B", "pointer": "102"},
    ]
    assert device.commands[-1] == ("GFAV1", "0")


async def test_get_favourites_skips_invalid_entries(
    client: XMP44Client, device: FakeDevice
) -> None:
    # Empty name, non-numeric index, then one valid entry
    device.replies["GFAV1"] = "0^^101^x^Radio B^102^2^Radio C^103"
    favs = await client.get_favourites(1)
    assert favs == [{"index": 2, "name": "Radio C", "pointer": "103"}]


async def test_get_favourites_empty(client: XMP44Client, device: FakeDevice) -> None:
    device.replies["GFAV1"] = ""
    assert await client.get_favourites(1) == []
    device.replies["GFAV1"] = "+"
    assert await client.get_favourites(1) == []


async def test_get_all_favourites_paginates(offline_client: XMP44Client) -> None:
    page1 = [{"index": i, "name": f"S{i}", "pointer": str(100 + i)} for i in range(10)]
    page2 = [{"index": 10, "name": "S10", "pointer": "110"}]
    offline_client.get_favourites = AsyncMock(side_effect=[page1, page2, []])
    favs = await offline_client.get_all_favourites(1)
    assert len(favs) == 11
    calls = offline_client.get_favourites.await_args_list
    assert [c.args for c in calls] == [(1, 0), (1, 10), (1, 20)]


async def test_get_all_favourites_stops_on_repeated_pointers(
    offline_client: XMP44Client,
) -> None:
    page = [{"index": 0, "name": "S0", "pointer": "100"}]
    offline_client.get_favourites = AsyncMock(side_effect=[page, page, page])
    favs = await offline_client.get_all_favourites(1)
    assert favs == page
    assert offline_client.get_favourites.await_count == 2


# ── get_all_slots ───────────────────────────────────────────────────


def _mock_common(client: XMP44Client) -> None:
    client.get_output_gain = AsyncMock(return_value=-2)
    client.get_player_status = AsyncMock(return_value="playing")
    client.get_song_info = AsyncMock(return_value={"title": "T"})


async def test_get_all_slots_without_config(offline_client: XMP44Client, caplog) -> None:
    caplog.set_level(logging.WARNING, logger="custom_components.audac_mtx.xmp44_client")
    assert await offline_client.get_all_slots() == {}
    assert "No module configuration" in caplog.text


async def test_get_all_slots_bmp40(offline_client: XMP44Client) -> None:
    offline_client.set_module_config({1: MODULE_BMP40})
    offline_client._module_versions = {1: "BMP40 V1.2"}
    _mock_common(offline_client)
    offline_client.get_bluetooth_info = AsyncMock(return_value={"name": "BT"})
    offline_client.get_connected_device = AsyncMock(return_value="1^Phone^AA")
    offline_client.get_pairing_state = AsyncMock(return_value=3)
    slots = await offline_client.get_all_slots()
    assert slots == {
        1: {
            "module_type": MODULE_BMP40,
            "module_name": "BMP40",
            "module_description": "Bluetooth Receiver",
            "module_version": "BMP40 V1.2",
            "status": "playing",
            "output_gain": -2,
            "song_info": {"title": "T"},
            "bluetooth_info": {"name": "BT"},
            "connected_device": "1^Phone^AA",
            "pairing_state": 3,
        }
    }


async def test_get_all_slots_mmp40(offline_client: XMP44Client) -> None:
    offline_client.set_module_config({2: MODULE_MMP40})
    _mock_common(offline_client)
    offline_client.get_recorder_mode = AsyncMock(return_value="recorder")
    slots = await offline_client.get_all_slots()
    assert slots[2]["recorder_mode"] == "recorder"
    assert slots[2]["status"] == "playing"
    assert slots[2]["song_info"] == {"title": "T"}


async def test_get_all_slots_dmp40_tuner_with_dab(offline_client: XMP44Client) -> None:
    offline_client.set_module_config({1: MODULE_DMP40})
    offline_client.get_output_gain = AsyncMock(return_value=0)
    offline_client.get_frequency = AsyncMock(return_value=10410)
    offline_client.get_program_name = AsyncMock(return_value="SRF 3")
    offline_client.get_signal_strength = AsyncMock(return_value=85)
    offline_client.get_stereo_state = AsyncMock(return_value=True)
    offline_client.get_band = AsyncMock(return_value="DAB")
    slots = await offline_client.get_all_slots()
    data = slots[1]
    assert data["frequency"] == 10410
    assert data["program_name"] == "SRF 3"
    assert data["signal_strength"] == 85
    assert data["stereo"] is True
    assert data["band"] == "DAB"
    assert data["status"] == "unknown"  # tuners have no playback status


async def test_get_all_slots_tmp40_tuner_without_dab(offline_client: XMP44Client) -> None:
    offline_client.set_module_config({3: MODULE_TMP40})
    offline_client.get_output_gain = AsyncMock(return_value=None)
    offline_client.get_frequency = AsyncMock(return_value=None)
    offline_client.get_program_name = AsyncMock(return_value=None)
    offline_client.get_signal_strength = AsyncMock(return_value=None)
    offline_client.get_stereo_state = AsyncMock(return_value=None)
    offline_client.get_band = AsyncMock()
    slots = await offline_client.get_all_slots()
    data = slots[3]
    assert data["output_gain"] == 0  # default kept when gain query returns None
    assert "frequency" not in data
    assert "program_name" not in data
    assert "signal_strength" not in data
    assert "stereo" not in data
    offline_client.get_band.assert_not_awaited()


async def test_get_all_slots_imp40(offline_client: XMP44Client) -> None:
    offline_client.set_module_config({4: MODULE_IMP40})
    offline_client.get_output_gain = AsyncMock(return_value=3)
    offline_client.get_song_info = AsyncMock(return_value=None)
    offline_client.get_station_name = AsyncMock(return_value="Radio Swiss Pop")
    offline_client.get_song_name = AsyncMock(return_value="Track A")
    slots = await offline_client.get_all_slots()
    data = slots[4]
    assert data["station_name"] == "Radio Swiss Pop"
    assert data["song_name"] == "Track A"
    assert "song_info" not in data


async def test_get_all_slots_nmp40(offline_client: XMP44Client) -> None:
    offline_client.set_module_config({1: MODULE_NMP40})
    _mock_common(offline_client)
    offline_client.get_player_name = AsyncMock(return_value="NMP40 player 1")
    offline_client.get_player_ip = AsyncMock(return_value="10.2.3.99")
    slots = await offline_client.get_all_slots()
    assert slots[1]["player_name"] == "NMP40 player 1"
    assert slots[1]["player_ip"] == "10.2.3.99"


async def test_get_all_slots_fmp40_only_gain(offline_client: XMP44Client) -> None:
    offline_client.set_module_config({2: MODULE_FMP40})
    offline_client.get_output_gain = AsyncMock(return_value=-4)
    slots = await offline_client.get_all_slots()
    assert slots[2]["output_gain"] == -4
    assert slots[2]["status"] == "unknown"


async def test_get_all_slots_skips_empty_and_unsupported(
    offline_client: XMP44Client,
) -> None:
    offline_client._module_types = {1: MODULE_EMPTY, 2: MODULE_UNSUPPORTED, 3: MODULE_FMP40}
    offline_client.get_output_gain = AsyncMock(return_value=0)
    slots = await offline_client.get_all_slots()
    assert set(slots) == {3}


async def test_get_all_slots_slot_error_keeps_defaults(
    offline_client: XMP44Client, caplog
) -> None:
    caplog.set_level(logging.WARNING, logger="custom_components.audac_mtx.xmp44_client")
    offline_client.set_module_config({1: MODULE_FMP40})
    offline_client.get_output_gain = AsyncMock(side_effect=ValueError("garbled"))
    slots = await offline_client.get_all_slots()
    assert slots[1]["output_gain"] == 0
    assert "Error polling XMP44 slot 1" in caplog.text


async def test_get_all_slots_connection_error_propagates(
    offline_client: XMP44Client,
) -> None:
    offline_client.set_module_config({1: MODULE_FMP40})
    offline_client.get_output_gain = AsyncMock(side_effect=ConnectionError("gone"))
    with pytest.raises(ConnectionError, match="gone"):
        await offline_client.get_all_slots()


async def test_get_all_slots_timeout_forces_disconnect(
    client: XMP44Client, monkeypatch
) -> None:
    monkeypatch.setattr(xmp_module, "GET_ALL_SLOTS_TIMEOUT", 0.05)
    client.set_module_config({1: MODULE_FMP40})

    async def hang(slot):
        await asyncio.sleep(5)

    client.get_output_gain = hang
    writer = client.test_connections[0][1]
    with pytest.raises(ConnectionError, match="timed out"):
        await client.get_all_slots()
    assert client.connected is False
    assert writer.closed is True
    assert client._consecutive_failures == 1
