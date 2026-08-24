"""Tests for the button platform (MTX buttons and XMP44 module buttons)."""
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


def make_zone_data():
    return {
        "volume": 20,
        "volume_db": -20,
        "routing": 1,
        "source_name": "Mic 1",
        "mute": False,
        "bass": 7,
        "bass_db": 0,
        "treble": 7,
        "treble_db": 0,
    }


def make_mtx_client():
    client = MagicMock()
    client.get_all_zones = AsyncMock(
        return_value={z: make_zone_data() for z in range(1, 9)}
    )
    client.disconnect = AsyncMock()
    for method in ("set_volume", "set_volume_up", "set_volume_down", "save"):
        setattr(client, method, AsyncMock(return_value=True))
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
        "button", DOMAIN, f"{entry.entry_id}{suffix}"
    )


async def press(hass: HomeAssistant, entity_id: str) -> None:
    await hass.services.async_call(
        "button", "press", {"entity_id": entity_id}, blocking=True
    )


# ── MTX buttons ─────────────────────────────────────────────────────


async def test_mtx_save_button(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client)
    await press(hass, eid(hass, entry, "_mtx_save"))
    client.save.assert_awaited_once()


async def test_mtx_volume_buttons(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client)
    await press(hass, eid(hass, entry, "_zone_2_vol_up"))
    client.set_volume_up.assert_any_await(2)
    await press(hass, eid(hass, entry, "_zone_2_vol_down"))
    client.set_volume_down.assert_any_await(2)


async def test_mtx_button_connection_error(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client)
    client.save.side_effect = ConnectionError("gone")
    with pytest.raises(HomeAssistantError, match="Audac command failed"):
        await press(hass, eid(hass, entry, "_mtx_save"))


async def test_mtx_buttons_available_despite_poll_failure(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client)
    coordinator = entry.runtime_data
    coordinator.async_set_update_error(Exception("down"))
    await hass.async_block_till_done()
    # Buttons stay available even when the coordinator fails
    assert hass.states.get(eid(hass, entry, "_mtx_save")).state != "unavailable"


# ── XMP44 buttons ───────────────────────────────────────────────────


SLOTS = {
    1: {"module_type": 6, "module_name": "FMP40", "status": "stopped", "output_gain": 0},
    2: {"module_type": 4, "module_name": "IMP40", "status": "playing", "output_gain": 0},
    3: {"module_type": 1, "module_name": "DMP40", "status": "playing", "output_gain": 0},
    4: {"module_type": 3, "module_name": "MMP40", "status": "stopped", "output_gain": 0},
}

FAVOURITES = [
    {"name": "Radio 1", "pointer": "1"},
    {"name": "Swiss Pop", "pointer": "2"},
    {"name": "Duplikat", "pointer": "2"},  # duplicate pointer is skipped
    {"name": "", "pointer": "3"},  # empty name is skipped
]

XMP_OPTIONS = {
    "slot_1_module": "6",
    "slot_1_triggers": 2,
    "slot_1_trigger_1_name": "Durchsage",
    "slot_2_module": "4",
    "slot_3_module": "1",
    "slot_4_module": "3",
}


def make_xmp_client(favourites=None):
    client = MagicMock()
    client.module_types = {1: 6, 2: 4, 3: 1, 4: 3}
    client.set_module_config = MagicMock()
    client.get_all_slots = AsyncMock(
        return_value={k: dict(v) for k, v in SLOTS.items()}
    )
    client.get_all_favourites = AsyncMock(
        return_value=list(FAVOURITES) if favourites is None else favourites
    )
    client.disconnect = AsyncMock()
    for method in (
        "trigger_start",
        "trigger_stop",
        "select_station",
        "disconnect_device",
        "search_up",
        "search_down",
        "switch_band",
        "select_preset",
        "go_to_start",
        "fast_forward",
        "fast_rewind",
        "start_recording",
        "stop_recording",
        "pause_recording",
        "cancel_recording",
        "set_random",
        "set_repeat",
    ):
        setattr(client, method, AsyncMock(return_value=True))
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


async def test_fmp40_trigger_buttons(hass: HomeAssistant) -> None:
    client = make_xmp_client()
    entry = await setup_xmp(hass, client)

    await press(hass, eid(hass, entry, "_fmp40_slot1_trigger1_start"))
    client.trigger_start.assert_any_await(1, 1)

    await press(hass, eid(hass, entry, "_fmp40_slot1_trigger1_stop"))
    client.trigger_stop.assert_any_await(1, 1)

    await press(hass, eid(hass, entry, "_fmp40_slot1_trigger2_start"))
    client.trigger_start.assert_any_await(1, 2)

    assert eid(hass, entry, "_fmp40_slot1_trigger3_start") is None


async def test_fmp40_invalid_trigger_count(hass: HomeAssistant) -> None:
    client = make_xmp_client()
    options = {**XMP_OPTIONS, "slot_1_triggers": "kaputt"}
    entry = await setup_xmp(hass, client, options=options)
    assert eid(hass, entry, "_fmp40_slot1_trigger1_start") is None


async def test_imp40_station_buttons(hass: HomeAssistant) -> None:
    client = make_xmp_client()
    entry = await setup_xmp(hass, client)

    button1 = eid(hass, entry, "_imp40_slot2_station_1_radio_1")
    assert button1 is not None
    await press(hass, button1)
    client.select_station.assert_any_await(2, 1)

    assert eid(hass, entry, "_imp40_slot2_station_2_swiss_pop") is not None
    # Duplicate pointer and empty name skipped
    assert eid(hass, entry, "_imp40_slot2_station_2_duplikat") is None
    assert eid(hass, entry, "_imp40_slot2_station_3_") is None


async def test_imp40_no_favourites(hass: HomeAssistant) -> None:
    client = make_xmp_client(favourites=[])
    entry = await setup_xmp(hass, client)
    assert eid(hass, entry, "_imp40_slot2_station_1_radio_1") is None


async def test_imp40_legacy_entity_cleanup(hass: HomeAssistant) -> None:
    client = make_xmp_client()
    entry = MockConfigEntry(
        domain=DOMAIN, data=XMP_DATA, options=XMP_OPTIONS, version=2
    )
    entry.add_to_hass(hass)

    # Pre-create an entity with the OLD unique_id format (no pointer)
    ent_reg = er.async_get(hass)
    legacy = ent_reg.async_get_or_create(
        "button",
        DOMAIN,
        f"{entry.entry_id}_imp40_slot2_station_radio_1",
        config_entry=entry,
    )
    assert ent_reg.async_get(legacy.entity_id) is not None

    # New-format entity must survive the cleanup
    ent_reg.async_get_or_create(
        "button",
        DOMAIN,
        f"{entry.entry_id}_imp40_slot2_station_2_swiss_pop",
        config_entry=entry,
    )

    # Entity of a different config entry must be ignored (a foreign domain,
    # otherwise HA would set it up together with the first audac_mtx entry
    # and its own cleanup would legitimately remove the entity)
    other_entry = MockConfigEntry(domain="test", data={}, version=1)
    other_entry.add_to_hass(hass)
    foreign = ent_reg.async_get_or_create(
        "button",
        DOMAIN,
        f"{other_entry.entry_id}_imp40_slot2_station_radio_1",
        config_entry=other_entry,
    )

    with patch(
        "custom_components.audac_mtx.xmp44_coordinator.XMP44Client",
        return_value=client,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # Legacy entity removed, new-format entity present
    assert (
        ent_reg.async_get_entity_id(
            "button", DOMAIN, f"{entry.entry_id}_imp40_slot2_station_radio_1"
        )
        is None
    )
    assert eid(hass, entry, "_imp40_slot2_station_1_radio_1") is not None
    assert eid(hass, entry, "_imp40_slot2_station_2_swiss_pop") is not None
    assert ent_reg.async_get(foreign.entity_id) is not None


async def test_tuner_buttons(hass: HomeAssistant) -> None:
    client = make_xmp_client()
    entry = await setup_xmp(hass, client)

    await press(hass, eid(hass, entry, "_tuner_slot3_search_up"))
    client.search_up.assert_any_await(3)

    await press(hass, eid(hass, entry, "_tuner_slot3_search_down"))
    client.search_down.assert_any_await(3)

    await press(hass, eid(hass, entry, "_tuner_slot3_band_switch"))
    client.switch_band.assert_any_await(3)

    await press(hass, eid(hass, entry, "_tuner_slot3_preset_5"))
    client.select_preset.assert_any_await(3, 5)

    assert eid(hass, entry, "_tuner_slot3_preset_10") is not None
    assert eid(hass, entry, "_tuner_slot3_preset_11") is None


async def test_mmp40_buttons(hass: HomeAssistant) -> None:
    client = make_xmp_client()
    entry = await setup_xmp(hass, client)

    simple = {
        "_mmp40_slot4_go_to_start": (client.go_to_start, (4,)),
        "_mmp40_slot4_fast_forward": (client.fast_forward, (4,)),
        "_mmp40_slot4_fast_rewind": (client.fast_rewind, (4,)),
        "_mmp40_slot4_rec_start": (client.start_recording, (4,)),
        "_mmp40_slot4_rec_stop": (client.stop_recording, (4,)),
        "_mmp40_slot4_rec_pause": (client.pause_recording, (4,)),
        "_mmp40_slot4_rec_cancel": (client.cancel_recording, (4,)),
        "_mmp40_slot4_random_on": (client.set_random, (4, True)),
        "_mmp40_slot4_random_off": (client.set_random, (4, False)),
        "_mmp40_slot4_repeat_one": (client.set_repeat, (4, 0)),
        "_mmp40_slot4_repeat_all": (client.set_repeat, (4, 4)),
        "_mmp40_slot4_repeat_folder": (client.set_repeat, (4, 1)),
        "_mmp40_slot4_repeat_off": (client.set_repeat, (4, 3)),
    }
    for suffix, (method, args) in simple.items():
        entity_id = eid(hass, entry, suffix)
        assert entity_id is not None, suffix
        await press(hass, entity_id)
        method.assert_any_await(*args)


async def test_bmp40_disconnect_button(hass: HomeAssistant) -> None:
    client = make_xmp_client()
    client.module_types = {1: 8}
    client.get_all_slots = AsyncMock(
        return_value={
            1: {"module_type": 8, "module_name": "BMP40", "status": "playing", "output_gain": 0}
        }
    )
    entry = await setup_xmp(hass, client, options={"slot_1_module": "8"})
    await press(hass, eid(hass, entry, "_bmp40_slot1_disconnect"))
    client.disconnect_device.assert_any_await(1)


async def test_xmp_button_connection_error(hass: HomeAssistant) -> None:
    client = make_xmp_client()
    entry = await setup_xmp(hass, client)
    client.search_up.side_effect = ConnectionError("gone")
    with pytest.raises(HomeAssistantError, match="Audac command failed"):
        await press(hass, eid(hass, entry, "_tuner_slot3_search_up"))
