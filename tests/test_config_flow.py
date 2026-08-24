"""Tests for the Audac MTX config and options flows."""
from __future__ import annotations

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.audac_mtx.const import (
    CONF_MODEL,
    DOMAIN,
    MODEL_MTX48,
    MODEL_MTX88,
    MODEL_XMP44,
)

MTX_USER_INPUT = {
    CONF_HOST: "192.168.1.50",
    CONF_PORT: 5001,
    CONF_MODEL: MODEL_MTX88,
    "name": "Wohnzimmer MTX",
}


async def test_user_flow_mtx_success(
    hass: HomeAssistant, mock_mtx_client, mock_setup_entry
) -> None:
    """A successful MTX88 setup creates an entry with the zone count."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], MTX_USER_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Wohnzimmer MTX"
    assert result["data"][CONF_HOST] == "192.168.1.50"
    assert result["data"][CONF_MODEL] == MODEL_MTX88
    assert result["data"]["zones"] == 8
    assert result["result"].unique_id == "audac_mtx_192.168.1.50"
    mock_mtx_client.assert_awaited_once()
    mock_setup_entry.assert_awaited_once()


async def test_user_flow_mtx48_zone_count(
    hass: HomeAssistant, mock_mtx_client, mock_setup_entry
) -> None:
    """An MTX48 entry stores four zones."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {**MTX_USER_INPUT, CONF_MODEL: MODEL_MTX48},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["zones"] == 4


async def test_user_flow_xmp44_success(
    hass: HomeAssistant, mock_xmp_client, mock_setup_entry
) -> None:
    """A successful XMP44 setup creates an entry with the slot count."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {**MTX_USER_INPUT, CONF_MODEL: MODEL_XMP44},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["slots"] == 4
    mock_xmp_client.assert_awaited_once()


async def test_user_flow_cannot_connect_then_recover(
    hass: HomeAssistant, mock_mtx_client, mock_setup_entry
) -> None:
    """A failed connection shows an error; the flow can then succeed."""
    mock_mtx_client.side_effect = ConnectionError("no route")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], MTX_USER_INPUT
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    mock_mtx_client.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], MTX_USER_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_duplicate_host_aborts(
    hass: HomeAssistant, mock_mtx_client, mock_setup_entry
) -> None:
    """The same host cannot be configured twice."""
    MockConfigEntry(
        domain=DOMAIN,
        unique_id="audac_mtx_192.168.1.50",
        data=MTX_USER_INPUT,
    ).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], MTX_USER_INPUT
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    mock_mtx_client.assert_not_awaited()


async def _setup_entry(hass: HomeAssistant, data: dict, options: dict | None = None):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=f"audac_mtx_{data[CONF_HOST]}",
        data=data,
        options=options or {},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_options_flow_mtx(
    hass: HomeAssistant, mock_setup_entry
) -> None:
    """MTX options accept zone names and store stripped values."""
    entry = await _setup_entry(hass, {**MTX_USER_INPUT, "zones": 8})

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"zone_1_name": "  Küche  ", "zone_2_visible": False},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["zone_1_name"] == "Küche"
    assert entry.options["zone_2_visible"] is False


async def test_options_flow_empty_name_then_recover(
    hass: HomeAssistant, mock_setup_entry
) -> None:
    """A blank name is rejected with empty_name, then accepted once fixed."""
    entry = await _setup_entry(hass, {**MTX_USER_INPUT, "zones": 8})

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"zone_1_name": "   "}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "empty_name"}

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"zone_1_name": "Bad"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["zone_1_name"] == "Bad"


async def test_options_flow_mtx_link_migration_defaults(
    hass: HomeAssistant, mock_setup_entry
) -> None:
    """Legacy zone_x_links / zone_x_linked_to options prefill the dropdown."""
    entry = await _setup_entry(
        hass,
        {**MTX_USER_INPUT, "zones": 8},
        options={
            "zone_1_links": [2],
            "zone_2_linked_to": 3,
            "zone_3_link": 4,
        },
    )

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    schema = result["data_schema"].schema
    defaults = {
        str(key): key.default() for key in schema if key.default is not None
    }
    assert defaults["zone_1_link"] == "2"
    assert defaults["zone_2_link"] == "3"
    assert defaults["zone_3_link"] == "4"


async def test_options_flow_xmp44_with_fmp40_triggers(
    hass: HomeAssistant, mock_setup_entry
) -> None:
    """XMP44 options render trigger name fields for a configured FMP40."""
    entry = await _setup_entry(
        hass,
        {**MTX_USER_INPUT, CONF_MODEL: MODEL_XMP44, "slots": 4},
        options={
            "slot_1_module": 6,
            "slot_1_triggers": 2,
            "slot_2_module": "8",
        },
    )

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    field_names = [str(key) for key in result["data_schema"].schema]
    assert "slot_1_trigger_1_name" in field_names
    assert "slot_1_trigger_2_name" in field_names
    assert "slot_2_trigger_1_name" not in field_names

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"slot_1_trigger_1_name": "Gong", "slot_1_name": "Durchsagen"},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["slot_1_trigger_1_name"] == "Gong"
    assert entry.options["slot_1_name"] == "Durchsagen"


async def test_options_flow_xmp44_invalid_trigger_count(
    hass: HomeAssistant, mock_setup_entry
) -> None:
    """A corrupt trigger count falls back to no trigger name fields."""
    entry = await _setup_entry(
        hass,
        {**MTX_USER_INPUT, CONF_MODEL: MODEL_XMP44, "slots": 4},
        options={"slot_1_module": "6", "slot_1_triggers": "kaputt"},
    )

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    field_names = [str(key) for key in result["data_schema"].schema]
    assert "slot_1_trigger_1_name" not in field_names
