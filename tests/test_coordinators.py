"""Tests for the MTX and XMP44 data coordinators."""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.audac_mtx import coordinator as mtx_coord_module
from custom_components.audac_mtx import xmp44_coordinator as xmp_coord_module
from custom_components.audac_mtx.const import CONF_MODEL, DOMAIN, MODEL_MTX88, MODEL_XMP44
from custom_components.audac_mtx.coordinator import (
    MAX_CONSECUTIVE_FAILURES,
    SCAN_INTERVAL,
    SCAN_INTERVAL_SLOW,
    SLOW_POLL_THRESHOLD,
    AudacMTXCoordinator,
)
from custom_components.audac_mtx.xmp44_client import MODULE_BMP40, MODULE_IMP40
from custom_components.audac_mtx.xmp44_coordinator import XMP44Coordinator


def _zone(volume=20, routing=3, mute=False, bass=7, treble=7) -> dict[str, Any]:
    return {"volume": volume, "routing": routing, "mute": mute, "bass": bass, "treble": treble}


def make_mtx_coordinator(
    hass: HomeAssistant, zones: int = 2, options: dict | None = None
) -> AudacMTXCoordinator:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "192.0.2.10", "port": 5001, CONF_MODEL: MODEL_MTX88, "zones": zones},
        options=options or {},
    )
    entry.add_to_hass(hass)
    coordinator = AudacMTXCoordinator(hass, entry)
    coordinator.client = AsyncMock()
    return coordinator


def make_xmp_coordinator(
    hass: HomeAssistant, options: dict | None = None, module_types: dict | None = None
) -> XMP44Coordinator:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "192.0.2.20", "port": 5001, CONF_MODEL: MODEL_XMP44, "slots": 4},
        options=options or {},
    )
    entry.add_to_hass(hass)
    coordinator = XMP44Coordinator(hass, entry)
    coordinator.client = AsyncMock()
    coordinator.client.module_types = module_types or {}
    return coordinator


# ── MTX coordinator ─────────────────────────────────────────────────


async def test_mtx_init_reads_entry(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "192.0.2.10", CONF_MODEL: MODEL_MTX88},
    )
    entry.add_to_hass(hass)
    coordinator = AudacMTXCoordinator(hass, entry)
    assert coordinator.client.host == "192.0.2.10"
    assert coordinator._zones_count == 8  # MTX88 default
    assert coordinator.update_interval == SCAN_INTERVAL


async def test_mtx_update_success(hass: HomeAssistant) -> None:
    coordinator = make_mtx_coordinator(hass)
    zones = {1: _zone(), 2: _zone(volume=30)}
    coordinator.client.get_all_zones.return_value = zones
    result = await coordinator._async_update_data()
    assert result == zones
    coordinator.client.get_all_zones.assert_awaited_once_with(2, previous=None)
    assert coordinator._consecutive_update_failures == 0
    assert coordinator.update_interval == SCAN_INTERVAL


async def test_mtx_success_restores_normal_interval(hass: HomeAssistant, caplog) -> None:
    coordinator = make_mtx_coordinator(hass)
    coordinator._consecutive_update_failures = 5
    coordinator.update_interval = SCAN_INTERVAL_SLOW
    coordinator.client.get_all_zones.return_value = {1: _zone(), 2: _zone()}
    await coordinator._async_update_data()
    assert coordinator._consecutive_update_failures == 0
    assert coordinator.update_interval == SCAN_INTERVAL
    assert "recovered after 5 failures" in caplog.text


async def test_mtx_empty_result_keeps_previous_within_grace(hass: HomeAssistant) -> None:
    coordinator = make_mtx_coordinator(hass)
    previous = {1: _zone(), 2: _zone()}
    coordinator.data = previous
    coordinator.client.get_all_zones.return_value = {}
    result = await coordinator._async_update_data()
    assert result == previous
    assert coordinator._consecutive_update_failures == 1
    assert coordinator.update_interval == SCAN_INTERVAL  # not slowed yet


async def test_mtx_empty_result_beyond_grace_raises_and_slows(hass: HomeAssistant) -> None:
    coordinator = make_mtx_coordinator(hass)
    coordinator.data = {1: _zone(), 2: _zone()}
    coordinator._consecutive_update_failures = SLOW_POLL_THRESHOLD
    coordinator.client.get_all_zones.return_value = {}
    with pytest.raises(UpdateFailed, match="No zone data"):
        await coordinator._async_update_data()
    assert coordinator._consecutive_update_failures == SLOW_POLL_THRESHOLD + 1
    assert coordinator.update_interval == SCAN_INTERVAL_SLOW


async def test_mtx_empty_result_on_first_poll_fails(hass: HomeAssistant) -> None:
    coordinator = make_mtx_coordinator(hass)
    coordinator.client.get_all_zones.return_value = {}
    with pytest.raises(UpdateFailed, match="first poll"):
        await coordinator._async_update_data()


async def test_mtx_incomplete_result_keeps_previous(hass: HomeAssistant) -> None:
    coordinator = make_mtx_coordinator(hass)
    previous = {1: _zone(), 2: _zone()}
    coordinator.data = previous
    coordinator.client.get_all_zones.return_value = {1: _zone(volume=10)}
    result = await coordinator._async_update_data()
    assert result == previous
    assert coordinator._consecutive_update_failures == 1


async def test_mtx_incomplete_result_beyond_grace_raises(hass: HomeAssistant) -> None:
    coordinator = make_mtx_coordinator(hass)
    coordinator.data = {1: _zone(), 2: _zone()}
    coordinator._consecutive_update_failures = SLOW_POLL_THRESHOLD
    coordinator.client.get_all_zones.return_value = {1: _zone()}
    with pytest.raises(UpdateFailed, match="Incomplete"):
        await coordinator._async_update_data()


async def test_mtx_suspicious_all_zero_keeps_previous(hass: HomeAssistant) -> None:
    coordinator = make_mtx_coordinator(hass)
    previous = {1: _zone(routing=3), 2: _zone(routing=0)}
    coordinator.data = previous
    coordinator.client.get_all_zones.return_value = {
        1: _zone(routing=0),
        2: _zone(routing=0),
    }
    result = await coordinator._async_update_data()
    assert result == previous
    assert coordinator._consecutive_update_failures == 1


async def test_mtx_suspicious_all_zero_accepted_after_max_failures(
    hass: HomeAssistant,
) -> None:
    coordinator = make_mtx_coordinator(hass)
    coordinator.data = {1: _zone(routing=3), 2: _zone(routing=0)}
    coordinator._consecutive_update_failures = MAX_CONSECUTIVE_FAILURES - 1
    all_zero = {1: _zone(routing=0), 2: _zone(routing=0)}
    coordinator.client.get_all_zones.return_value = all_zero
    result = await coordinator._async_update_data()
    assert result == all_zero
    # Accepted as real: success path resets the counter
    assert coordinator._consecutive_update_failures == 0


def test_mtx_is_suspicious_response_edge_cases(hass: HomeAssistant) -> None:
    coordinator = make_mtx_coordinator(hass)
    all_zero = {1: _zone(routing=0), 2: _zone(routing=0)}
    # No previous data at all
    assert coordinator._is_suspicious_response(all_zero) is False
    # Previous data had nothing active: all-zero is plausible
    coordinator.data = {1: _zone(routing=0), 2: _zone(routing=0)}
    assert coordinator._is_suspicious_response(all_zero) is False
    # Previous active, new partially active: not suspicious
    coordinator.data = {1: _zone(routing=3), 2: _zone(routing=0)}
    assert coordinator._is_suspicious_response({1: _zone(routing=1), 2: _zone(routing=0)}) is False


async def test_mtx_connection_error_keeps_previous(hass: HomeAssistant) -> None:
    coordinator = make_mtx_coordinator(hass)
    previous = {1: _zone(), 2: _zone()}
    coordinator.data = previous
    coordinator.client.get_all_zones.side_effect = ConnectionError("gone")
    result = await coordinator._async_update_data()
    assert result == previous
    assert coordinator._consecutive_update_failures == 1


async def test_mtx_connection_error_without_previous_raises(hass: HomeAssistant) -> None:
    coordinator = make_mtx_coordinator(hass)
    coordinator.client.get_all_zones.side_effect = ConnectionError("gone")
    with pytest.raises(UpdateFailed, match="Connection error"):
        await coordinator._async_update_data()


async def test_mtx_generic_error_disconnects(hass: HomeAssistant) -> None:
    coordinator = make_mtx_coordinator(hass)
    coordinator.client.get_all_zones.side_effect = ValueError("boom")
    with pytest.raises(UpdateFailed, match="Error communicating"):
        await coordinator._async_update_data()
    coordinator.client.disconnect.assert_awaited_once()


async def test_mtx_generic_error_keeps_previous(hass: HomeAssistant) -> None:
    coordinator = make_mtx_coordinator(hass)
    previous = {1: _zone(), 2: _zone()}
    coordinator.data = previous
    coordinator.client.get_all_zones.side_effect = ValueError("boom")
    result = await coordinator._async_update_data()
    assert result == previous


async def test_mtx_update_timeout_keeps_previous(hass: HomeAssistant, monkeypatch) -> None:
    monkeypatch.setattr(mtx_coord_module, "UPDATE_TIMEOUT", 0.05)
    coordinator = make_mtx_coordinator(hass)
    previous = {1: _zone(), 2: _zone()}
    coordinator.data = previous

    async def hang(*args, **kwargs):
        await asyncio.sleep(5)

    coordinator.client.get_all_zones.side_effect = hang
    result = await coordinator._async_update_data()
    assert result == previous
    assert coordinator._consecutive_update_failures == 1
    coordinator.client.disconnect.assert_awaited_once()


async def test_mtx_update_timeout_without_previous_raises(
    hass: HomeAssistant, monkeypatch
) -> None:
    monkeypatch.setattr(mtx_coord_module, "UPDATE_TIMEOUT", 0.05)
    coordinator = make_mtx_coordinator(hass)

    async def hang(*args, **kwargs):
        await asyncio.sleep(5)

    coordinator.client.get_all_zones.side_effect = hang
    with pytest.raises(UpdateFailed, match="timed out"):
        await coordinator._async_update_data()


async def test_mtx_slow_poll_threshold(hass: HomeAssistant) -> None:
    """Interval only slows after more than SLOW_POLL_THRESHOLD failures."""
    coordinator = make_mtx_coordinator(hass)
    coordinator.client.get_all_zones.side_effect = ConnectionError("gone")
    for expected_failures in (1, 2):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()
        assert coordinator._consecutive_update_failures == expected_failures
        assert coordinator.update_interval == SCAN_INTERVAL
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
    assert coordinator._consecutive_update_failures == 3
    assert coordinator.update_interval == SCAN_INTERVAL_SLOW


async def test_mtx_sync_slave_zones_pushes_master_values(hass: HomeAssistant) -> None:
    coordinator = make_mtx_coordinator(hass, options={"zone_2_link": "1"})
    zones = {
        1: _zone(volume=20, routing=3, mute=False, bass=8, treble=7),
        2: _zone(volume=30, routing=1, mute=True, bass=7, treble=5),
    }
    await coordinator._sync_slave_zones(zones)
    coordinator.client.set_volume.assert_awaited_once_with(2, 20)
    coordinator.client.set_mute.assert_awaited_once_with(2, False)
    coordinator.client.set_routing.assert_awaited_once_with(2, 3)
    coordinator.client.set_bass.assert_awaited_once_with(2, 8)
    coordinator.client.set_treble.assert_awaited_once_with(2, 7)


async def test_mtx_sync_slave_zones_no_drift_no_commands(hass: HomeAssistant) -> None:
    coordinator = make_mtx_coordinator(hass, options={"zone_2_link": "1"})
    zones = {1: _zone(), 2: _zone()}
    await coordinator._sync_slave_zones(zones)
    coordinator.client.set_volume.assert_not_awaited()
    coordinator.client.set_mute.assert_not_awaited()
    coordinator.client.set_routing.assert_not_awaited()
    coordinator.client.set_bass.assert_not_awaited()
    coordinator.client.set_treble.assert_not_awaited()


async def test_mtx_sync_slave_zones_without_links_or_data(hass: HomeAssistant) -> None:
    # No links configured: early return
    coordinator = make_mtx_coordinator(hass)
    await coordinator._sync_slave_zones({1: _zone(), 2: _zone()})
    coordinator.client.set_volume.assert_not_awaited()
    # Link configured but master zone data missing: skipped
    coordinator = make_mtx_coordinator(hass, options={"zone_2_link": "1"})
    await coordinator._sync_slave_zones({2: _zone(volume=30)})
    coordinator.client.set_volume.assert_not_awaited()


async def test_mtx_update_runs_slave_sync(hass: HomeAssistant) -> None:
    coordinator = make_mtx_coordinator(hass, options={"zone_2_link": "1"})
    zones = {1: _zone(volume=20), 2: _zone(volume=40)}
    coordinator.client.get_all_zones.return_value = zones
    await coordinator._async_update_data()
    coordinator.client.set_volume.assert_awaited_once_with(2, 20)


async def test_mtx_shutdown_disconnects(hass: HomeAssistant) -> None:
    coordinator = make_mtx_coordinator(hass)
    await coordinator.async_shutdown()
    coordinator.client.disconnect.assert_awaited_once()


# ── XMP44 coordinator ───────────────────────────────────────────────


async def test_xmp_apply_module_config(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "192.0.2.20", CONF_MODEL: MODEL_XMP44, "slots": 4},
        options={
            "slot_1_module": "4",
            "slot_2_module": "15",   # empty — filtered out
            "slot_3_module": "abc",  # unparsable — filtered out
            "slot_4_module": "0",    # none — filtered out
        },
    )
    entry.add_to_hass(hass)
    coordinator = XMP44Coordinator(hass, entry)
    assert coordinator.client.module_types == {1: MODULE_IMP40}
    assert coordinator.update_interval == xmp_coord_module.SCAN_INTERVAL


async def test_xmp_update_success_without_imp40(hass: HomeAssistant) -> None:
    coordinator = make_xmp_coordinator(hass, module_types={1: MODULE_BMP40})
    slots = {1: {"module_name": "BMP40", "status": "playing", "output_gain": 0}}
    coordinator.client.get_all_slots.return_value = slots
    result = await coordinator._async_update_data()
    assert result == slots
    assert coordinator._favourites_loaded is True
    coordinator.client.get_all_favourites.assert_not_awaited()


async def test_xmp_favourites_loaded_and_injected(hass: HomeAssistant) -> None:
    coordinator = make_xmp_coordinator(hass, module_types={2: MODULE_IMP40})
    favs = [{"index": 0, "name": "Radio A", "pointer": "101"}]
    coordinator.client.get_all_favourites.return_value = favs
    coordinator.client.get_all_slots.return_value = {2: {"module_name": "IMP40"}}
    result = await coordinator._async_update_data()
    assert coordinator._favourites_loaded is True
    assert coordinator.favourites == {2: favs}
    assert result[2]["favourites"] == favs
    coordinator.client.get_all_favourites.assert_awaited_once_with(2)


async def test_xmp_favourites_retry_until_loaded(hass: HomeAssistant, caplog) -> None:
    coordinator = make_xmp_coordinator(hass, module_types={2: MODULE_IMP40})
    coordinator.client.get_all_slots.return_value = {2: {"module_name": "IMP40"}}
    # First poll: no favourites yet
    coordinator.client.get_all_favourites.return_value = []
    result = await coordinator._async_update_data()
    assert coordinator._favourites_loaded is False
    assert "favourites" not in result[2]
    # Second poll: favourites appear and are cached
    favs = [{"index": 0, "name": "Radio A", "pointer": "101"}]
    coordinator.client.get_all_favourites.return_value = favs
    result = await coordinator._async_update_data()
    assert coordinator._favourites_loaded is True
    assert result[2]["favourites"] == favs
    assert coordinator.client.get_all_favourites.await_count == 2
    # Third poll: no reload once cached
    await coordinator._async_update_data()
    assert coordinator.client.get_all_favourites.await_count == 2


async def test_xmp_load_favourites_error_is_swallowed(hass: HomeAssistant, caplog) -> None:
    coordinator = make_xmp_coordinator(hass, module_types={2: MODULE_IMP40})
    coordinator.client.get_all_favourites.side_effect = ValueError("boom")
    coordinator.client.get_all_slots.return_value = {2: {"module_name": "IMP40"}}
    result = await coordinator._async_update_data()
    assert result == {2: {"module_name": "IMP40"}}
    assert coordinator._favourites_loaded is False
    assert "Failed to load favourites for slot 2" in caplog.text


async def test_xmp_reload_favourites(hass: HomeAssistant, caplog) -> None:
    coordinator = make_xmp_coordinator(hass)
    favs = [{"index": 0, "name": "Radio A", "pointer": "101"}]
    coordinator.client.get_all_favourites.return_value = favs
    await coordinator.async_reload_favourites(2)
    assert coordinator.favourites == {2: favs}
    # Empty result leaves the cache untouched
    coordinator.client.get_all_favourites.return_value = []
    await coordinator.async_reload_favourites(3)
    assert 3 not in coordinator.favourites
    # Errors are logged, not raised
    coordinator.client.get_all_favourites.side_effect = ValueError("boom")
    await coordinator.async_reload_favourites(2)
    assert "Failed to reload favourites for slot 2" in caplog.text
    assert coordinator.favourites == {2: favs}


async def test_xmp_empty_result_keeps_previous_within_grace(hass: HomeAssistant) -> None:
    coordinator = make_xmp_coordinator(hass, module_types={1: MODULE_BMP40})
    previous = {1: {"module_name": "BMP40"}}
    coordinator.data = previous
    coordinator.client.get_all_slots.return_value = {}
    result = await coordinator._async_update_data()
    assert result == previous
    assert coordinator._consecutive_update_failures == 1


async def test_xmp_empty_result_beyond_grace_raises_and_slows(hass: HomeAssistant) -> None:
    coordinator = make_xmp_coordinator(hass, module_types={1: MODULE_BMP40})
    coordinator.data = {1: {"module_name": "BMP40"}}
    coordinator._consecutive_update_failures = xmp_coord_module.SLOW_POLL_THRESHOLD
    coordinator.client.get_all_slots.return_value = {}
    with pytest.raises(UpdateFailed, match="No slot data"):
        await coordinator._async_update_data()
    assert coordinator.update_interval == xmp_coord_module.SCAN_INTERVAL_SLOW


async def test_xmp_empty_result_on_first_poll_fails(hass: HomeAssistant) -> None:
    coordinator = make_xmp_coordinator(hass, module_types={1: MODULE_BMP40})
    coordinator.client.get_all_slots.return_value = {}
    with pytest.raises(UpdateFailed, match="first poll"):
        await coordinator._async_update_data()


async def test_xmp_connection_error_keeps_previous(hass: HomeAssistant) -> None:
    coordinator = make_xmp_coordinator(hass, module_types={1: MODULE_BMP40})
    previous = {1: {"module_name": "BMP40"}}
    coordinator.data = previous
    coordinator.client.get_all_slots.side_effect = ConnectionError("gone")
    result = await coordinator._async_update_data()
    assert result == previous


async def test_xmp_connection_error_without_previous_raises(hass: HomeAssistant) -> None:
    coordinator = make_xmp_coordinator(hass, module_types={1: MODULE_BMP40})
    coordinator.client.get_all_slots.side_effect = ConnectionError("gone")
    with pytest.raises(UpdateFailed, match="Connection error"):
        await coordinator._async_update_data()


async def test_xmp_generic_error_disconnects(hass: HomeAssistant) -> None:
    coordinator = make_xmp_coordinator(hass, module_types={1: MODULE_BMP40})
    coordinator.client.get_all_slots.side_effect = ValueError("boom")
    with pytest.raises(UpdateFailed, match="Error communicating"):
        await coordinator._async_update_data()
    coordinator.client.disconnect.assert_awaited_once()


async def test_xmp_generic_error_keeps_previous(hass: HomeAssistant) -> None:
    coordinator = make_xmp_coordinator(hass, module_types={1: MODULE_BMP40})
    previous = {1: {"module_name": "BMP40"}}
    coordinator.data = previous
    coordinator.client.get_all_slots.side_effect = ValueError("boom")
    result = await coordinator._async_update_data()
    assert result == previous


async def test_xmp_update_timeout_keeps_previous(hass: HomeAssistant, monkeypatch) -> None:
    monkeypatch.setattr(xmp_coord_module, "UPDATE_TIMEOUT", 0.05)
    coordinator = make_xmp_coordinator(hass, module_types={1: MODULE_BMP40})
    previous = {1: {"module_name": "BMP40"}}
    coordinator.data = previous

    async def hang(*args, **kwargs):
        await asyncio.sleep(5)

    coordinator.client.get_all_slots.side_effect = hang
    result = await coordinator._async_update_data()
    assert result == previous
    coordinator.client.disconnect.assert_awaited_once()


async def test_xmp_update_timeout_without_previous_raises(
    hass: HomeAssistant, monkeypatch
) -> None:
    monkeypatch.setattr(xmp_coord_module, "UPDATE_TIMEOUT", 0.05)
    coordinator = make_xmp_coordinator(hass, module_types={1: MODULE_BMP40})

    async def hang(*args, **kwargs):
        await asyncio.sleep(5)

    coordinator.client.get_all_slots.side_effect = hang
    with pytest.raises(UpdateFailed, match="timed out"):
        await coordinator._async_update_data()


async def test_xmp_success_restores_normal_interval(hass: HomeAssistant, caplog) -> None:
    coordinator = make_xmp_coordinator(hass, module_types={1: MODULE_BMP40})
    coordinator._consecutive_update_failures = 4
    coordinator.update_interval = xmp_coord_module.SCAN_INTERVAL_SLOW
    coordinator.client.get_all_slots.return_value = {1: {"module_name": "BMP40"}}
    await coordinator._async_update_data()
    assert coordinator._consecutive_update_failures == 0
    assert coordinator.update_interval == xmp_coord_module.SCAN_INTERVAL
    assert "recovered after 4 failures" in caplog.text


async def test_xmp_shutdown_disconnects(hass: HomeAssistant) -> None:
    coordinator = make_xmp_coordinator(hass)
    await coordinator.async_shutdown()
    coordinator.client.disconnect.assert_awaited_once()
