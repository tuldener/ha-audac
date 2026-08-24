"""Tests for the media_player platform (MTX zones and XMP44 slots)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.audac_mtx as audac_init
from custom_components.audac_mtx.const import (
    BASS_TREBLE_MAP,
    CONF_MODEL,
    DOMAIN,
    MODEL_MTX88,
    MODEL_XMP44,
)

MTX_DATA = {
    "host": "192.168.1.50",
    "port": 5001,
    CONF_MODEL: MODEL_MTX88,
    "zones": 8,
    "name": "Audac MTX",
}

XMP_DATA = {
    "host": "192.168.1.60",
    "port": 5001,
    CONF_MODEL: MODEL_XMP44,
    "slots": 4,
    "name": "Audac XMP44",
}


@pytest.fixture(autouse=True)
def skip_card_registration(monkeypatch):
    monkeypatch.setattr(audac_init, "_CARD_REGISTERED", True)


def make_zone_data(volume=20, routing=1, mute=False, bass=7, treble=7):
    return {
        "volume": volume,
        "volume_db": -volume,
        "routing": routing,
        "source_name": f"Input {routing}",
        "mute": mute,
        "bass": bass,
        "bass_db": BASS_TREBLE_MAP.get(bass, 0),
        "treble": treble,
        "treble_db": BASS_TREBLE_MAP.get(treble, 0),
    }


DEFAULT_ZONES = {
    1: make_zone_data(volume=14, routing=1),
    2: make_zone_data(volume=14, routing=2, mute=True),
    3: make_zone_data(routing=0),
    **{z: make_zone_data() for z in range(4, 9)},
}


def make_mtx_client(zones_data=None):
    client = MagicMock()
    client.get_all_zones = AsyncMock(
        return_value=zones_data or {k: dict(v) for k, v in DEFAULT_ZONES.items()}
    )
    client.disconnect = AsyncMock()
    for method in (
        "set_volume",
        "set_volume_up",
        "set_volume_down",
        "set_routing",
        "set_routing_up",
        "set_routing_down",
        "set_bass",
        "set_treble",
        "set_mute",
        "save",
    ):
        setattr(client, method, AsyncMock(return_value=True))
    return client


async def setup_mtx(hass: HomeAssistant, client, options=None):
    entry = MockConfigEntry(
        domain=DOMAIN, data=MTX_DATA, options=options or {}, version=2
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.audac_mtx.coordinator.MTXClient", return_value=client
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


def zone_eid(hass: HomeAssistant, entry, zone: int) -> str:
    return er.async_get(hass).async_get_entity_id(
        "media_player", DOMAIN, f"{entry.entry_id}_zone_{zone}"
    )


# ── MTX zone state & attributes ─────────────────────────────────────


async def test_zone_states(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client)

    state1 = hass.states.get(zone_eid(hass, entry, 1))
    assert state1.state == "on"
    assert state1.attributes["source"] == "Mic 1"
    assert state1.attributes["volume_level"] == pytest.approx(1 - 14 / 70)
    assert state1.attributes["is_volume_muted"] is False

    state2 = hass.states.get(zone_eid(hass, entry, 2))
    assert state2.state == "idle"
    assert state2.attributes["is_volume_muted"] is True

    state3 = hass.states.get(zone_eid(hass, entry, 3))
    assert state3.state == "off"


async def test_zone_extra_attributes(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client, options={"zone_2_link": "1"})

    attrs = hass.states.get(zone_eid(hass, entry, 1)).attributes
    assert attrs["zone_number"] == 1
    assert attrs["routing"] == 1
    assert attrs["volume_db"] == -14
    assert attrs["bass"] == 0
    assert attrs["treble"] == 0
    assert attrs["bass_raw"] == 7
    assert attrs["treble_raw"] == 7
    assert attrs["zone_visible"] is True
    assert attrs["linked_to"] == 0
    assert attrs["linked_zones"] == [2]

    attrs2 = hass.states.get(zone_eid(hass, entry, 2)).attributes
    assert attrs2["linked_to"] == 1
    assert attrs2["linked_zones"] == []


async def test_zone_custom_name_and_sources(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(
        hass,
        client,
        options={"zone_1_name": "Wohnzimmer", "source_1_name": "Bühne"},
    )
    state = hass.states.get(zone_eid(hass, entry, 1))
    assert state.attributes["friendly_name"].endswith("Wohnzimmer")
    assert "Bühne" in state.attributes["source_list"]
    assert state.attributes["source"] == "Bühne"


async def test_zone_unknown_routing_source(hass: HomeAssistant) -> None:
    zones = {z: make_zone_data() for z in range(1, 9)}
    zones[1]["routing"] = 42
    client = make_mtx_client(zones)
    entry = await setup_mtx(hass, client)
    state = hass.states.get(zone_eid(hass, entry, 1))
    assert state.attributes["source"] == "Input 42"


async def test_zone_unavailable_on_update_failure(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client)
    coordinator = entry.runtime_data

    coordinator.async_set_update_error(Exception("device down"))
    await hass.async_block_till_done()
    assert hass.states.get(zone_eid(hass, entry, 1)).state == "unavailable"


async def test_zone_unavailable_without_zone_data(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client)
    coordinator = entry.runtime_data

    data = dict(coordinator.data)
    data.pop(1)
    coordinator.async_set_updated_data(data)
    await hass.async_block_till_done()
    assert hass.states.get(zone_eid(hass, entry, 1)).state == "unavailable"


# ── MTX services ────────────────────────────────────────────────────


async def test_volume_set(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client)
    await hass.services.async_call(
        "media_player",
        "volume_set",
        {"entity_id": zone_eid(hass, entry, 1), "volume_level": 0.5},
        blocking=True,
    )
    client.set_volume.assert_any_await(1, 35)


async def test_volume_up_down(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client)
    eid = zone_eid(hass, entry, 1)
    await hass.services.async_call(
        "media_player", "volume_up", {"entity_id": eid}, blocking=True
    )
    client.set_volume_up.assert_any_await(1)
    await hass.services.async_call(
        "media_player", "volume_down", {"entity_id": eid}, blocking=True
    )
    client.set_volume_down.assert_any_await(1)


async def test_mute(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client)
    await hass.services.async_call(
        "media_player",
        "volume_mute",
        {"entity_id": zone_eid(hass, entry, 1), "is_volume_muted": True},
        blocking=True,
    )
    client.set_mute.assert_any_await(1, True)


async def test_select_source(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client)
    await hass.services.async_call(
        "media_player",
        "select_source",
        {"entity_id": zone_eid(hass, entry, 1), "source": "Mic 2"},
        blocking=True,
    )
    client.set_routing.assert_any_await(1, 2)


async def test_custom_services(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client)
    eid = zone_eid(hass, entry, 1)

    await hass.services.async_call(
        DOMAIN, "set_bass", {"entity_id": eid, "bass": 10}, blocking=True
    )
    client.set_bass.assert_any_await(1, 10)

    await hass.services.async_call(
        DOMAIN, "set_treble", {"entity_id": eid, "treble": 3}, blocking=True
    )
    client.set_treble.assert_any_await(1, 3)

    await hass.services.async_call(
        DOMAIN, "routing_up", {"entity_id": eid}, blocking=True
    )
    client.set_routing_up.assert_any_await(1)

    await hass.services.async_call(
        DOMAIN, "routing_down", {"entity_id": eid}, blocking=True
    )
    client.set_routing_down.assert_any_await(1)


async def test_service_connection_error(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client)
    client.set_volume.side_effect = ConnectionError("gone")
    with pytest.raises(HomeAssistantError, match="Audac command failed"):
        await hass.services.async_call(
            "media_player",
            "volume_set",
            {"entity_id": zone_eid(hass, entry, 1), "volume_level": 0.5},
            blocking=True,
        )


# ── Zone linking / mirroring ────────────────────────────────────────


async def test_mirror_to_slaves(hass: HomeAssistant) -> None:
    zones = {z: make_zone_data(volume=35) for z in range(1, 9)}
    client = make_mtx_client(zones)
    entry = await setup_mtx(
        hass, client, options={"zone_2_link": "1", "zone_3_link": "1"}
    )

    await hass.services.async_call(
        "media_player",
        "volume_set",
        {"entity_id": zone_eid(hass, entry, 1), "volume_level": 0.5},
        blocking=True,
    )
    client.set_volume.assert_any_await(1, 35)
    client.set_volume.assert_any_await(2, 35)
    client.set_volume.assert_any_await(3, 35)


async def test_mirror_mute_and_source(hass: HomeAssistant) -> None:
    zones = {z: make_zone_data() for z in range(1, 9)}
    client = make_mtx_client(zones)
    entry = await setup_mtx(hass, client, options={"zone_2_link": "1"})
    eid = zone_eid(hass, entry, 1)

    await hass.services.async_call(
        "media_player",
        "volume_mute",
        {"entity_id": eid, "is_volume_muted": True},
        blocking=True,
    )
    client.set_mute.assert_any_await(2, True)

    await hass.services.async_call(
        "media_player",
        "select_source",
        {"entity_id": eid, "source": "Line 3"},
        blocking=True,
    )
    client.set_routing.assert_any_await(1, 3)
    client.set_routing.assert_any_await(2, 3)

    await hass.services.async_call(
        DOMAIN, "set_bass", {"entity_id": eid, "bass": 9}, blocking=True
    )
    client.set_bass.assert_any_await(2, 9)

    await hass.services.async_call(
        DOMAIN, "set_treble", {"entity_id": eid, "treble": 5}, blocking=True
    )
    client.set_treble.assert_any_await(2, 5)

    await hass.services.async_call(
        DOMAIN, "routing_up", {"entity_id": eid}, blocking=True
    )
    client.set_routing_up.assert_any_await(2)

    await hass.services.async_call(
        "media_player", "volume_up", {"entity_id": eid}, blocking=True
    )
    client.set_volume_up.assert_any_await(2)

    await hass.services.async_call(
        "media_player", "volume_down", {"entity_id": eid}, blocking=True
    )
    client.set_volume_down.assert_any_await(2)


# ── XMP44 slots ─────────────────────────────────────────────────────


IMP40_SLOT = {
    "module_type": 4,
    "module_name": "IMP40",
    "module_description": "Internet Radio",
    "module_version": "1.0",
    "status": "playing",
    "output_gain": 0,
    "station_name": "Radio 1",
    "song_name": "Song A",
}

BMP40_SLOT = {
    "module_type": 8,
    "module_name": "BMP40",
    "module_description": "Bluetooth Receiver",
    "module_version": "1.1",
    "status": "paused",
    "output_gain": -2,
    "song_info": {
        "title": "Track",
        "artist": "Artist",
        "album": "Album",
        "duration": 200,
        "position": 42,
    },
    "bluetooth_info": {"name": "BMP", "address": "AA:BB", "version": "5.0"},
    "connected_device": "1^Handy^AA:BB:CC",
}

MMP40_SLOT = {
    "module_type": 3,
    "module_name": "MMP40",
    "module_description": "Media Player/Recorder",
    "module_version": "1.2",
    "status": "stopped",
    "output_gain": 0,
    "frequency": 10410,
    "band": "FM",
    "signal_strength": 80,
    "program_name": "SRF 3",
    "player_name": "Player",
}

DMP40_SLOT = {
    "module_type": 1,
    "module_name": "DMP40",
    "module_description": "DAB/DAB+ & FM Tuner",
    "module_version": "1.3",
    "status": "unknown",
    "output_gain": 0,
    "frequency": 0,
    "program_name": "DRS",
}

FAVOURITES = [
    {"name": "Radio 1", "pointer": "1"},
    {"name": "Swiss Pop", "pointer": "2"},
]


def make_xmp_client():
    client = MagicMock()
    client.module_types = {1: 4, 2: 8, 3: 3, 4: 1}
    client.set_module_config = MagicMock()
    client.get_all_slots = AsyncMock(
        return_value={
            1: dict(IMP40_SLOT),
            2: dict(BMP40_SLOT),
            3: dict(MMP40_SLOT),
            4: dict(DMP40_SLOT),
        }
    )
    client.get_all_favourites = AsyncMock(return_value=list(FAVOURITES))
    client.disconnect = AsyncMock()
    for method in (
        "play",
        "stop",
        "pause",
        "next_track",
        "previous_track",
        "select_station",
    ):
        setattr(client, method, AsyncMock(return_value=True))
    return client


XMP_OPTIONS = {
    "slot_1_module": "4",
    "slot_2_module": "8",
    "slot_3_module": "3",
    "slot_4_module": "1",
    "slot_2_name": "Blau Zahn",
}


async def setup_xmp(hass: HomeAssistant, client, options=None):
    entry = MockConfigEntry(
        domain=DOMAIN, data=XMP_DATA, options=options or XMP_OPTIONS, version=2
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.audac_mtx.xmp44_coordinator.XMP44Client",
        return_value=client,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


def slot_eid(hass: HomeAssistant, entry, slot: int) -> str:
    return er.async_get(hass).async_get_entity_id(
        "media_player", DOMAIN, f"{entry.entry_id}_xmp44_slot_{slot}"
    )


async def test_xmp44_slot_states(hass: HomeAssistant) -> None:
    client = make_xmp_client()
    entry = await setup_xmp(hass, client)

    assert hass.states.get(slot_eid(hass, entry, 1)).state == "playing"
    assert hass.states.get(slot_eid(hass, entry, 2)).state == "paused"
    assert hass.states.get(slot_eid(hass, entry, 3)).state == "idle"
    # Unknown status maps to ON
    assert hass.states.get(slot_eid(hass, entry, 4)).state == "on"


async def test_xmp44_media_info(hass: HomeAssistant) -> None:
    client = make_xmp_client()
    entry = await setup_xmp(hass, client)

    # IMP40: media_title = song name, source = station name
    imp = hass.states.get(slot_eid(hass, entry, 1))
    assert imp.attributes["media_title"] == "Song A"
    assert imp.attributes["source"] == "Radio 1"
    assert imp.attributes["source_list"] == ["Radio 1", "Swiss Pop"]

    # BMP40: song_info fields
    bmp = hass.states.get(slot_eid(hass, entry, 2))
    assert bmp.attributes["media_title"] == "Track"
    assert bmp.attributes["media_artist"] == "Artist"
    assert bmp.attributes["media_album_name"] == "Album"
    assert bmp.attributes["media_duration"] == 200
    assert bmp.attributes["media_position"] == 42

    # MMP40 without song_info: falls back to program/station name
    mmp = hass.states.get(slot_eid(hass, entry, 3))
    assert mmp.attributes["media_title"] == "SRF 3"


async def test_xmp44_extra_attributes(hass: HomeAssistant) -> None:
    client = make_xmp_client()
    entry = await setup_xmp(hass, client)

    imp = hass.states.get(slot_eid(hass, entry, 1)).attributes
    assert imp["slot_number"] == 1
    assert imp["module_type"] == 4
    assert imp["station_name"] == "Radio 1"

    bmp = hass.states.get(slot_eid(hass, entry, 2)).attributes
    assert bmp["bluetooth_info"] == BMP40_SLOT["bluetooth_info"]
    assert bmp["connected_device"] == "1^Handy^AA:BB:CC"

    mmp = hass.states.get(slot_eid(hass, entry, 3)).attributes
    assert mmp["frequency"] == 10410
    assert mmp["frequency_mhz"] == 104.10
    assert mmp["band"] == "FM"
    assert mmp["signal_strength"] == 80
    assert mmp["program_name"] == "SRF 3"
    assert mmp["player_name"] == "Player"

    dmp = hass.states.get(slot_eid(hass, entry, 4)).attributes
    assert dmp["frequency"] == 0
    assert dmp["frequency_mhz"] is None


async def test_xmp44_playback_services(hass: HomeAssistant) -> None:
    client = make_xmp_client()
    entry = await setup_xmp(hass, client)
    eid = slot_eid(hass, entry, 2)

    for service, method in (
        ("media_play", client.play),
        ("media_stop", client.stop),
        ("media_pause", client.pause),
        ("media_next_track", client.next_track),
        ("media_previous_track", client.previous_track),
    ):
        await hass.services.async_call(
            "media_player", service, {"entity_id": eid}, blocking=True
        )
        method.assert_any_await(2)


async def test_xmp44_select_station(hass: HomeAssistant) -> None:
    client = make_xmp_client()
    entry = await setup_xmp(hass, client)
    eid = slot_eid(hass, entry, 1)

    await hass.services.async_call(
        "media_player",
        "select_source",
        {"entity_id": eid, "source": "Swiss Pop"},
        blocking=True,
    )
    client.select_station.assert_any_await(1, 2)


async def test_xmp44_select_station_error(hass: HomeAssistant) -> None:
    client = make_xmp_client()
    entry = await setup_xmp(hass, client)
    client.select_station.side_effect = ConnectionError("gone")
    with pytest.raises(HomeAssistantError, match="Audac command failed"):
        await hass.services.async_call(
            "media_player",
            "select_source",
            {"entity_id": slot_eid(hass, entry, 1), "source": "Radio 1"},
            blocking=True,
        )


async def test_xmp44_source_map_updates_on_refresh(hass: HomeAssistant) -> None:
    client = make_xmp_client()
    entry = await setup_xmp(hass, client)
    coordinator = entry.runtime_data

    new_data = {
        1: {**IMP40_SLOT, "favourites": [{"name": "Neu", "pointer": "5"}]},
        2: dict(BMP40_SLOT),
        3: dict(MMP40_SLOT),
        4: dict(DMP40_SLOT),
    }
    coordinator.async_set_updated_data(new_data)
    await hass.async_block_till_done()

    state = hass.states.get(slot_eid(hass, entry, 1))
    assert state.attributes["source_list"] == ["Neu"]

    await hass.services.async_call(
        "media_player",
        "select_source",
        {"entity_id": slot_eid(hass, entry, 1), "source": "Neu"},
        blocking=True,
    )
    client.select_station.assert_any_await(1, 5)


async def test_xmp44_slot_missing_data(hass: HomeAssistant) -> None:
    client = make_xmp_client()
    entry = await setup_xmp(hass, client)
    coordinator = entry.runtime_data

    data = dict(coordinator.data)
    data.pop(1)
    coordinator.async_set_updated_data(data)
    await hass.async_block_till_done()

    # No data for slot 1: state falls back to ON, no media info
    state = hass.states.get(slot_eid(hass, entry, 1))
    assert state.state == "on"
    assert "media_title" not in state.attributes


# ── Direct property coverage for empty zone/slot data ───────────────


def test_zone_properties_without_data() -> None:
    from custom_components.audac_mtx.media_player import AudacMTXZone

    entry = MockConfigEntry(domain=DOMAIN, data=MTX_DATA, version=2)
    coordinator = MagicMock(data={})
    zone = AudacMTXZone(coordinator, 1, entry)
    assert zone.volume_level is None
    assert zone.is_volume_muted is None
    assert zone.source is None
    assert zone.extra_state_attributes == {}


async def test_xmp44_setup_without_slot_data(hass: HomeAssistant) -> None:
    from custom_components.audac_mtx.media_player import _setup_xmp44

    entry = MockConfigEntry(domain=DOMAIN, data=XMP_DATA, version=2)
    entry.add_to_hass(hass)
    coordinator = MagicMock(data=None)
    added = MagicMock()
    await _setup_xmp44(hass, entry, coordinator, added)
    added.assert_not_called()


async def test_imp40_unknown_source_warning(caplog) -> None:
    from custom_components.audac_mtx.media_player import AudacXMP44Slot

    entry = MockConfigEntry(domain=DOMAIN, data=XMP_DATA, version=2)
    coordinator = MagicMock(data={1: dict(IMP40_SLOT)})
    slot = AudacXMP44Slot(coordinator, 1, entry, dict(IMP40_SLOT), "hub-id")
    await slot.async_select_source("Gibt es nicht")
    coordinator.client.select_station.assert_not_called()
    assert "unknown source" in caplog.text
