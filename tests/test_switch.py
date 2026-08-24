"""Tests for the switch platform (MTX mute and XMP44 module switches)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.audac_mtx as audac_init
from custom_components.audac_mtx.const import (
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


def make_zone_data(mute=False):
    return {
        "volume": 20,
        "volume_db": -20,
        "routing": 1,
        "source_name": "Mic 1",
        "mute": mute,
        "bass": 7,
        "bass_db": 0,
        "treble": 7,
        "treble_db": 0,
    }


def make_mtx_client():
    client = MagicMock()
    zones = {z: make_zone_data() for z in range(1, 9)}
    zones[2]["mute"] = True
    client.get_all_zones = AsyncMock(return_value=zones)
    client.disconnect = AsyncMock()
    client.set_mute = AsyncMock(return_value=True)
    client.set_volume = AsyncMock(return_value=True)
    client.set_routing = AsyncMock(return_value=True)
    return client


async def setup_mtx(hass: HomeAssistant, client):
    entry = MockConfigEntry(domain=DOMAIN, data=MTX_DATA, version=2)
    entry.add_to_hass(hass)
    with patch(
        "custom_components.audac_mtx.coordinator.MTXClient", return_value=client
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


def eid(hass: HomeAssistant, entry, suffix: str) -> str:
    return er.async_get(hass).async_get_entity_id(
        "switch", DOMAIN, f"{entry.entry_id}{suffix}"
    )


# ── MTX mute switch ─────────────────────────────────────────────────


async def test_mute_switch_state(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client)
    assert hass.states.get(eid(hass, entry, "_zone_1_mute")).state == "off"
    assert hass.states.get(eid(hass, entry, "_zone_2_mute")).state == "on"


async def test_mute_switch_turn_on_off(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client)
    entity_id = eid(hass, entry, "_zone_1_mute")

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )
    client.set_mute.assert_any_await(1, True)

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": entity_id}, blocking=True
    )
    client.set_mute.assert_any_await(1, False)


async def test_mute_switch_connection_error(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client)
    client.set_mute.side_effect = ConnectionError("gone")
    with pytest.raises(HomeAssistantError, match="Audac command failed"):
        await hass.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": eid(hass, entry, "_zone_1_mute")},
            blocking=True,
        )


async def test_mute_switch_unknown_without_data(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client)
    coordinator = entry.runtime_data
    data = dict(coordinator.data)
    data.pop(1)
    coordinator.async_set_updated_data(data)
    await hass.async_block_till_done()
    assert hass.states.get(eid(hass, entry, "_zone_1_mute")).state == "unavailable"


# ── XMP44 switches ──────────────────────────────────────────────────


SLOTS = {
    1: {
        "module_type": 8,
        "module_name": "BMP40",
        "status": "playing",
        "output_gain": 0,
        "pairing_state": 3,
    },
    2: {
        "module_type": 1,
        "module_name": "DMP40",
        "status": "playing",
        "output_gain": 0,
        "stereo": True,
    },
    3: {
        "module_type": 3,
        "module_name": "MMP40",
        "status": "stopped",
        "output_gain": 0,
        "recorder_mode": "recorder",
    },
}

XMP_OPTIONS = {
    "slot_1_module": "8",
    "slot_2_module": "1",
    "slot_3_module": "3",
    "slot_4_module": "15",
}


def make_xmp_client():
    client = MagicMock()
    client.module_types = {1: 8, 2: 1, 3: 3}
    client.set_module_config = MagicMock()
    client.get_all_slots = AsyncMock(
        return_value={k: dict(v) for k, v in SLOTS.items()}
    )
    client.get_all_favourites = AsyncMock(return_value=[])
    client.disconnect = AsyncMock()
    for method in ("set_pairing", "set_stereo", "set_recorder_mode"):
        setattr(client, method, AsyncMock(return_value=True))
    return client


async def setup_xmp(hass: HomeAssistant, client):
    entry = MockConfigEntry(
        domain=DOMAIN, data=XMP_DATA, options=XMP_OPTIONS, version=2
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.audac_mtx.xmp44_coordinator.XMP44Client",
        return_value=client,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_bmp40_pairing_switch(hass: HomeAssistant) -> None:
    client = make_xmp_client()
    entry = await setup_xmp(hass, client)
    entity_id = eid(hass, entry, "_bmp40_slot1_pairing")

    assert hass.states.get(entity_id).state == "on"

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": entity_id}, blocking=True
    )
    client.set_pairing.assert_any_await(1, False)

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )
    client.set_pairing.assert_any_await(1, True)


async def test_stereo_switch(hass: HomeAssistant) -> None:
    client = make_xmp_client()
    entry = await setup_xmp(hass, client)
    entity_id = eid(hass, entry, "_tuner_slot2_stereo")

    assert hass.states.get(entity_id).state == "on"

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": entity_id}, blocking=True
    )
    client.set_stereo.assert_any_await(2, False)

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )
    client.set_stereo.assert_any_await(2, True)


async def test_recorder_mode_switch(hass: HomeAssistant) -> None:
    client = make_xmp_client()
    entry = await setup_xmp(hass, client)
    entity_id = eid(hass, entry, "_mmp40_slot3_recorder")

    assert hass.states.get(entity_id).state == "on"

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": entity_id}, blocking=True
    )
    client.set_recorder_mode.assert_any_await(3, False)

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )
    client.set_recorder_mode.assert_any_await(3, True)


async def test_xmp44_switch_states_without_data(hass: HomeAssistant) -> None:
    client = make_xmp_client()
    entry = await setup_xmp(hass, client)
    coordinator = entry.runtime_data

    coordinator.async_set_updated_data(
        {
            1: {**SLOTS[1], "pairing_state": None},
            2: {**SLOTS[2], "stereo": None},
            3: {**SLOTS[3], "recorder_mode": None},
        }
    )
    await hass.async_block_till_done()
    assert hass.states.get(eid(hass, entry, "_bmp40_slot1_pairing")).state == "unknown"
    assert hass.states.get(eid(hass, entry, "_tuner_slot2_stereo")).state == "unknown"
    assert hass.states.get(eid(hass, entry, "_mmp40_slot3_recorder")).state == "unknown"

    coordinator.async_set_updated_data({})
    await hass.async_block_till_done()
    assert hass.states.get(eid(hass, entry, "_bmp40_slot1_pairing")).state == "unknown"

    # No switches for the empty slot 4
    assert eid(hass, entry, "_tuner_slot4_stereo") is None


def test_mute_switch_is_on_without_data() -> None:
    from custom_components.audac_mtx.switch import AudacMTXMuteSwitch

    entry = MockConfigEntry(domain=DOMAIN, data=MTX_DATA, version=2)
    coordinator = MagicMock(data={})
    switch = AudacMTXMuteSwitch(coordinator, 1, entry)
    assert switch.is_on is None
