"""Tests for helpers.py and const.py helper functions."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.audac_mtx.const import (
    INPUT_NAMES,
    MODEL_MTX48,
    MODEL_MTX88,
    MODEL_XMP44,
    get_source_names,
    is_mtx_model,
    is_xmp_model,
)
from custom_components.audac_mtx.helpers import (
    execute_device_command,
    get_slave_zones,
    get_zone_links,
    get_zone_master,
)


# ── get_zone_master ─────────────────────────────────────────────────


def test_zone_master_current_format() -> None:
    assert get_zone_master({"zone_2_link": "1"}, 2) == 1
    assert get_zone_master({"zone_2_link": "0"}, 2) == 0


def test_zone_master_current_format_invalid() -> None:
    assert get_zone_master({"zone_2_link": "abc"}, 2) == 0
    assert get_zone_master({"zone_2_link": ["1"]}, 2) == 0


def test_zone_master_old_list_format() -> None:
    assert get_zone_master({"zone_3_links": ["4", "5"]}, 3) == 4


def test_zone_master_old_list_format_invalid() -> None:
    assert get_zone_master({"zone_3_links": ["x"]}, 3) == 0


def test_zone_master_old_list_format_empty() -> None:
    # Empty list falls through to legacy format
    assert get_zone_master({"zone_3_links": []}, 3) == 0


def test_zone_master_legacy_format() -> None:
    assert get_zone_master({"zone_4_linked_to": 2}, 4) == 2


def test_zone_master_no_options() -> None:
    assert get_zone_master({}, 1) == 0


# ── get_slave_zones ─────────────────────────────────────────────────


def test_slave_zones_current_format() -> None:
    options = {"zone_2_link": "1", "zone_3_link": "1", "zone_4_link": "0"}
    assert get_slave_zones(options, 1, 4) == [2, 3]


def test_slave_zones_current_format_invalid_value() -> None:
    options = {"zone_2_link": "junk"}
    assert get_slave_zones(options, 1, 4) == []


def test_slave_zones_skips_master_itself() -> None:
    options = {"zone_1_link": "1", "zone_2_link": "1"}
    assert get_slave_zones(options, 1, 2) == [2]


def test_slave_zones_old_list_format() -> None:
    # Membership anywhere in the list counts
    options = {"zone_2_links": ["3", "1"], "zone_3_links": ["4"]}
    assert get_slave_zones(options, 1, 4) == [2]


def test_slave_zones_legacy_format() -> None:
    options = {"zone_2_linked_to": 1, "zone_3_linked_to": 2}
    assert get_slave_zones(options, 1, 4) == [2]


def test_slave_zones_mixed_formats() -> None:
    options = {
        "zone_2_link": "1",
        "zone_3_links": ["1"],
        "zone_4_linked_to": 1,
    }
    assert get_slave_zones(options, 1, 4) == [2, 3, 4]


# ── get_zone_links ──────────────────────────────────────────────────


def test_zone_links_maps_slave_to_master() -> None:
    options = {"zone_2_link": "1", "zone_4_link": "3"}
    assert get_zone_links(options, 4) == {2: 1, 4: 3}


def test_zone_links_ignores_self_link_and_zero() -> None:
    options = {"zone_1_link": "1", "zone_2_link": "0"}
    assert get_zone_links(options, 2) == {}


# ── execute_device_command ──────────────────────────────────────────


async def test_execute_device_command_success() -> None:
    coro = AsyncMock(return_value=True)()
    assert await execute_device_command(coro, "set_volume") is True


@pytest.mark.parametrize("exc", [ConnectionError("boom"), TimeoutError(), OSError("io")])
async def test_execute_device_command_transport_errors(exc: Exception) -> None:
    coro = AsyncMock(side_effect=exc)()
    with pytest.raises(HomeAssistantError, match="Audac command failed"):
        await execute_device_command(coro, "set_volume")


# ── const helpers ───────────────────────────────────────────────────


def test_model_helpers() -> None:
    assert is_mtx_model(MODEL_MTX48)
    assert is_mtx_model(MODEL_MTX88)
    assert not is_mtx_model(MODEL_XMP44)
    assert is_xmp_model(MODEL_XMP44)
    assert not is_xmp_model(MODEL_MTX88)


def test_get_source_names_defaults() -> None:
    names = get_source_names({})
    # Source 0 (Off) hidden by default, all others visible
    assert 0 not in names
    assert names[1] == "Mic 1"
    assert len(names) == len(INPUT_NAMES) - 1


def test_get_source_names_custom_and_hidden() -> None:
    options = {
        "source_0_visible": True,
        "source_2_visible": False,
        "source_1_name": "Bühne",
    }
    names = get_source_names(options)
    assert names[0] == "Off"
    assert 2 not in names
    assert names[1] == "Bühne"


def test_get_source_names_all_visible() -> None:
    names = get_source_names({"source_2_visible": False}, visible_only=False)
    assert 0 in names and 2 in names
    assert len(names) == len(INPUT_NAMES)
