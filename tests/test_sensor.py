"""Tests for the sensor platform (MTX source sensors and XMP44 module sensors)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
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


def make_mtx_client(zones_data=None):
    client = MagicMock()
    client.get_all_zones = AsyncMock(
        return_value=zones_data or {z: make_zone_data() for z in range(1, 9)}
    )
    client.disconnect = AsyncMock()
    for method in ("set_volume", "set_routing", "set_bass", "set_treble", "set_mute"):
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


def eid(hass: HomeAssistant, entry, unique_suffix: str) -> str:
    return er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}{unique_suffix}"
    )


# ── MTX source sensor ───────────────────────────────────────────────


async def test_mtx_source_sensor(hass: HomeAssistant) -> None:
    zones = {z: make_zone_data() for z in range(1, 9)}
    zones[1]["routing"] = 2
    zones[2]["routing"] = 0
    client = make_mtx_client(zones)
    entry = await setup_mtx(hass, client)

    state = hass.states.get(eid(hass, entry, "_zone_1_active_source"))
    assert state.state == "Mic 2"
    assert state.attributes["routing_id"] == 2
    assert state.attributes["volume_raw"] == 20
    assert state.attributes["volume_db"] == -20
    assert state.attributes["mute"] is False
    assert state.attributes["bass_db"] == 0
    assert state.attributes["treble_db"] == 0

    # Source 0 is included even though it is hidden in selects
    state2 = hass.states.get(eid(hass, entry, "_zone_2_active_source"))
    assert state2.state == "Off"


async def test_mtx_source_sensor_unknown_routing(hass: HomeAssistant) -> None:
    zones = {z: make_zone_data() for z in range(1, 9)}
    zones[1]["routing"] = 99
    client = make_mtx_client(zones)
    entry = await setup_mtx(hass, client)
    assert hass.states.get(eid(hass, entry, "_zone_1_active_source")).state == "Input 99"


async def test_mtx_source_sensor_no_data(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client)
    coordinator = entry.runtime_data
    data = dict(coordinator.data)
    data[1] = {}
    data.pop(2)
    coordinator.async_set_updated_data(data)
    await hass.async_block_till_done()
    assert hass.states.get(eid(hass, entry, "_zone_1_active_source")).state == "unavailable"
    assert hass.states.get(eid(hass, entry, "_zone_2_active_source")).state == "unavailable"


async def test_mtx_source_sensor_routing_none(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client)
    coordinator = entry.runtime_data
    data = dict(coordinator.data)
    data[1] = {"volume": 20}  # no routing key
    coordinator.async_set_updated_data(data)
    await hass.async_block_till_done()
    assert hass.states.get(eid(hass, entry, "_zone_1_active_source")).state == "unknown"


# ── XMP44 sensors ───────────────────────────────────────────────────


BMP40_SLOT = {
    "module_type": 8,
    "module_name": "BMP40",
    "status": "playing",
    "output_gain": 0,
    "connected_device": "1^Handy^AA:BB:CC",
    "pairing_state": 3,
    "bluetooth_info": {"name": "BMP", "address": "AA:BB", "version": "5.0"},
}

NMP40_SLOT = {
    "module_type": 9,
    "module_name": "NMP40",
    "status": "stopped",
    "output_gain": 0,
    "player_name": "Streamer",
    "player_ip": "192.168.1.99",
}

DMP40_SLOT = {
    "module_type": 1,
    "module_name": "DMP40",
    "status": "playing",
    "output_gain": 0,
    "frequency": 10410,
    "band": "DAB",
    "signal_strength": 75,
    "program_name": "SRF 1",
}

TMP40_SLOT = {
    "module_type": 2,
    "module_name": "TMP40",
    "status": "playing",
    "output_gain": 0,
    "frequency": 8880,
    "signal_strength": 50,
    "program_name": "SRF 2",
}

XMP_OPTIONS = {
    "slot_1_module": "8",
    "slot_2_module": "9",
    "slot_3_module": "1",
    "slot_4_module": "2",
}


def make_xmp_client():
    client = MagicMock()
    client.module_types = {1: 8, 2: 9, 3: 1, 4: 2}
    client.set_module_config = MagicMock()
    client.get_all_slots = AsyncMock(
        return_value={
            1: dict(BMP40_SLOT),
            2: dict(NMP40_SLOT),
            3: dict(DMP40_SLOT),
            4: dict(TMP40_SLOT),
        }
    )
    client.get_all_favourites = AsyncMock(return_value=[])
    client.disconnect = AsyncMock()
    return client


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


async def test_bmp40_sensors(hass: HomeAssistant) -> None:
    client = make_xmp_client()
    entry = await setup_xmp(hass, client)

    connected = hass.states.get(eid(hass, entry, "_bmp40_slot1_connected_device"))
    assert connected.state == "Handy"
    assert connected.attributes["device_address"] == "AA:BB:CC"
    assert connected.attributes["bt_name"] == "BMP"
    assert connected.attributes["bt_address"] == "AA:BB"
    assert connected.attributes["bt_version"] == "5.0"
    assert connected.attributes["slot_number"] == 1

    pairing = hass.states.get(eid(hass, entry, "_bmp40_slot1_pairing_state"))
    assert pairing.state == "Aktiv"


async def test_bmp40_sensor_edge_cases(hass: HomeAssistant) -> None:
    client = make_xmp_client()
    entry = await setup_xmp(hass, client)
    coordinator = entry.runtime_data

    # Not connected + unknown pairing state
    data = dict(coordinator.data)
    data[1] = {**BMP40_SLOT, "connected_device": None, "pairing_state": 9, "bluetooth_info": None}
    coordinator.async_set_updated_data(data)
    await hass.async_block_till_done()
    assert hass.states.get(eid(hass, entry, "_bmp40_slot1_connected_device")).state == "Nicht verbunden"
    assert hass.states.get(eid(hass, entry, "_bmp40_slot1_pairing_state")).state == "Unbekannt (9)"

    # Connected string with empty name part
    data = dict(data)
    data[1] = {**BMP40_SLOT, "connected_device": "1^ ^", "pairing_state": None}
    coordinator.async_set_updated_data(data)
    await hass.async_block_till_done()
    assert hass.states.get(eid(hass, entry, "_bmp40_slot1_connected_device")).state == "Nicht verbunden"
    assert hass.states.get(eid(hass, entry, "_bmp40_slot1_pairing_state")).state == "unknown"

    # Slot missing entirely
    data = dict(data)
    data.pop(1)
    coordinator.async_set_updated_data(data)
    await hass.async_block_till_done()
    assert hass.states.get(eid(hass, entry, "_bmp40_slot1_connected_device")).state == "unknown"
    attrs = hass.states.get(eid(hass, entry, "_bmp40_slot1_connected_device")).attributes
    assert attrs["slot_number"] == 1
    assert hass.states.get(eid(hass, entry, "_bmp40_slot1_pairing_state")).state == "unknown"


async def test_nmp40_sensors(hass: HomeAssistant) -> None:
    client = make_xmp_client()
    entry = await setup_xmp(hass, client)

    assert hass.states.get(eid(hass, entry, "_nmp40_slot2_player_name")).state == "Streamer"
    assert hass.states.get(eid(hass, entry, "_nmp40_slot2_ip")).state == "192.168.1.99"

    coordinator = entry.runtime_data
    data = dict(coordinator.data)
    data.pop(2)
    coordinator.async_set_updated_data(data)
    await hass.async_block_till_done()
    assert hass.states.get(eid(hass, entry, "_nmp40_slot2_player_name")).state == "unknown"
    assert hass.states.get(eid(hass, entry, "_nmp40_slot2_ip")).state == "unknown"


async def test_tuner_sensors(hass: HomeAssistant) -> None:
    client = make_xmp_client()
    entry = await setup_xmp(hass, client)

    # DMP40 in slot 3 (has band sensor)
    assert hass.states.get(eid(hass, entry, "_tuner_slot3_frequency")).state == "104.1"
    assert hass.states.get(eid(hass, entry, "_tuner_slot3_program")).state == "SRF 1"
    assert hass.states.get(eid(hass, entry, "_tuner_slot3_signal")).state == "75"
    assert hass.states.get(eid(hass, entry, "_tuner_slot3_band")).state == "DAB"

    # TMP40 in slot 4 has no band sensor
    assert hass.states.get(eid(hass, entry, "_tuner_slot4_frequency")).state == "88.8"
    assert eid(hass, entry, "_tuner_slot4_band") is None


async def test_tuner_sensors_missing_data(hass: HomeAssistant) -> None:
    client = make_xmp_client()
    entry = await setup_xmp(hass, client)
    coordinator = entry.runtime_data

    data = dict(coordinator.data)
    data[3] = {**DMP40_SLOT, "frequency": None, "program_name": None, "signal_strength": None, "band": None}
    data.pop(4)
    coordinator.async_set_updated_data(data)
    await hass.async_block_till_done()

    for suffix in ("_tuner_slot3_frequency", "_tuner_slot3_program", "_tuner_slot3_signal", "_tuner_slot3_band"):
        assert hass.states.get(eid(hass, entry, suffix)).state == "unknown"
    for suffix in ("_tuner_slot4_frequency", "_tuner_slot4_program", "_tuner_slot4_signal"):
        assert hass.states.get(eid(hass, entry, suffix)).state == "unknown"


async def test_invalid_module_option_creates_no_sensors(hass: HomeAssistant) -> None:
    client = make_xmp_client()
    client.module_types = {}
    client.get_all_slots = AsyncMock(
        return_value={1: {"module_type": 15, "module_name": None, "status": "unknown", "output_gain": 0}}
    )
    entry = await setup_xmp(hass, client, options={"slot_1_module": "kaputt"})
    assert eid(hass, entry, "_bmp40_slot1_connected_device") is None


def test_source_sensor_properties_without_data() -> None:
    from custom_components.audac_mtx.sensor import AudacMTXSourceSensor

    entry = MockConfigEntry(domain=DOMAIN, data=MTX_DATA, version=2)
    coordinator = MagicMock(data={})
    sensor = AudacMTXSourceSensor(coordinator, 1, entry)
    assert sensor.native_value is None
    assert sensor.extra_state_attributes == {}
