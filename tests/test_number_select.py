"""Tests for the number (zone volume) and select (zone source) platforms."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.audac_mtx as audac_init
from custom_components.audac_mtx.const import CONF_MODEL, DOMAIN, MODEL_MTX88

MTX_DATA = {
    "host": "192.168.1.50",
    "port": 5001,
    CONF_MODEL: MODEL_MTX88,
    "zones": 8,
    "name": "Audac MTX",
}


@pytest.fixture(autouse=True)
def skip_card_registration(monkeypatch):
    monkeypatch.setattr(audac_init, "_CARD_REGISTERED", True)


def make_zone_data(volume=35, routing=1):
    return {
        "volume": volume,
        "volume_db": -volume,
        "routing": routing,
        "source_name": f"Input {routing}",
        "mute": False,
        "bass": 7,
        "bass_db": 0,
        "treble": 7,
        "treble_db": 0,
    }


def make_mtx_client(zones_data=None):
    client = MagicMock()
    client.get_all_zones = AsyncMock(
        return_value=zones_data or {z: make_zone_data() for z in range(1, 9)}
    )
    client.disconnect = AsyncMock()
    for method in ("set_volume", "set_routing", "set_mute", "set_bass", "set_treble"):
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


def eid(hass: HomeAssistant, entry, platform: str, suffix: str) -> str:
    return er.async_get(hass).async_get_entity_id(
        platform, DOMAIN, f"{entry.entry_id}{suffix}"
    )


# ── Number (volume) ─────────────────────────────────────────────────


async def test_number_value(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client)
    state = hass.states.get(eid(hass, entry, "number", "_zone_1_volume"))
    assert state.state == "50"  # raw 35 -> 50%


async def test_number_value_none(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client)
    coordinator = entry.runtime_data
    data = dict(coordinator.data)
    data[1] = {"routing": 1}  # no volume key
    coordinator.async_set_updated_data(data)
    await hass.async_block_till_done()
    assert hass.states.get(eid(hass, entry, "number", "_zone_1_volume")).state == "unknown"


async def test_number_set_value(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client)
    entity_id = eid(hass, entry, "number", "_zone_1_volume")

    await hass.services.async_call(
        "number", "set_value", {"entity_id": entity_id, "value": 50}, blocking=True
    )
    client.set_volume.assert_any_await(1, 35)

    await hass.services.async_call(
        "number", "set_value", {"entity_id": entity_id, "value": 100}, blocking=True
    )
    client.set_volume.assert_any_await(1, 0)

    await hass.services.async_call(
        "number", "set_value", {"entity_id": entity_id, "value": 0}, blocking=True
    )
    client.set_volume.assert_any_await(1, 70)


async def test_number_connection_error(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client)
    client.set_volume.side_effect = ConnectionError("gone")
    with pytest.raises(HomeAssistantError, match="Audac command failed"):
        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": eid(hass, entry, "number", "_zone_1_volume"), "value": 20},
            blocking=True,
        )


# ── Select (source) ─────────────────────────────────────────────────


async def test_select_current_option(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client)
    state = hass.states.get(eid(hass, entry, "select", "_zone_1_source"))
    assert state.state == "Mic 1"
    assert "Off" not in state.attributes["options"]
    assert "Mic 2" in state.attributes["options"]


async def test_select_hidden_routing_fallback(hass: HomeAssistant) -> None:
    # Zone routed to source 0 (Off), which is hidden by default:
    # the fallback name must be appended to the options list.
    zones = {z: make_zone_data() for z in range(1, 9)}
    zones[1]["routing"] = 0
    client = make_mtx_client(zones)
    entry = await setup_mtx(hass, client)
    state = hass.states.get(eid(hass, entry, "select", "_zone_1_source"))
    assert state.state == "Off"
    assert "Off" in state.attributes["options"]


async def test_select_unknown_routing_fallback(hass: HomeAssistant) -> None:
    zones = {z: make_zone_data() for z in range(1, 9)}
    zones[1]["routing"] = 42
    client = make_mtx_client(zones)
    entry = await setup_mtx(hass, client)
    state = hass.states.get(eid(hass, entry, "select", "_zone_1_source"))
    assert state.state == "Input 42"
    assert "Input 42" in state.attributes["options"]


async def test_select_no_data(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client)
    coordinator = entry.runtime_data
    data = dict(coordinator.data)
    data.pop(1)
    data[2] = {"volume": 20}  # no routing key
    coordinator.async_set_updated_data(data)
    await hass.async_block_till_done()
    assert hass.states.get(eid(hass, entry, "select", "_zone_1_source")).state == "unavailable"
    assert hass.states.get(eid(hass, entry, "select", "_zone_2_source")).state == "unknown"


async def test_select_option(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client)
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": eid(hass, entry, "select", "_zone_1_source"), "option": "Line 4"},
        blocking=True,
    )
    client.set_routing.assert_any_await(1, 4)


async def test_select_hidden_option_via_input_names(hass: HomeAssistant) -> None:
    # Source 3 is hidden; zone currently routed there so "Line 3" stays in
    # the options list. Selecting it must resolve via INPUT_NAMES fallback.
    zones = {z: make_zone_data() for z in range(1, 9)}
    zones[1]["routing"] = 3
    client = make_mtx_client(zones)
    entry = await setup_mtx(hass, client, options={"source_3_visible": False})
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": eid(hass, entry, "select", "_zone_1_source"), "option": "Line 3"},
        blocking=True,
    )
    client.set_routing.assert_any_await(1, 3)


async def test_select_connection_error(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client)
    client.set_routing.side_effect = ConnectionError("gone")
    with pytest.raises(HomeAssistantError, match="Audac command failed"):
        await hass.services.async_call(
            "select",
            "select_option",
            {
                "entity_id": eid(hass, entry, "select", "_zone_1_source"),
                "option": "Mic 2",
            },
            blocking=True,
        )


def test_number_native_value_without_data() -> None:
    from custom_components.audac_mtx.number import AudacMTXVolumeNumber

    entry = MockConfigEntry(domain=DOMAIN, data=MTX_DATA, version=2)
    coordinator = MagicMock(data={})
    number = AudacMTXVolumeNumber(coordinator, 1, entry)
    assert number.native_value is None


def test_select_properties_without_data() -> None:
    from custom_components.audac_mtx.select import AudacMTXSourceSelect

    entry = MockConfigEntry(domain=DOMAIN, data=MTX_DATA, version=2)
    coordinator = MagicMock(data={})
    select = AudacMTXSourceSelect(coordinator, 1, entry)
    assert select.current_option is None
    assert "Mic 1" in select.options
