"""Tests for integration setup, unload, migration and card registration."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_registry import RegistryEntryHider
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.audac_mtx as audac_init
from custom_components.audac_mtx import (
    _read_card_version,
    _register_card,
    _register_lovelace_resource,
    async_migrate_entry,
)
from custom_components.audac_mtx.const import (
    BASS_TREBLE_MAP,
    CARD_URL_PATH,
    CONF_MODEL,
    DOMAIN,
    MODEL_MTX48,
    MODEL_MTX88,
    MODEL_XMP44,
)
from custom_components.audac_mtx.helpers import _async_update_zone_visibility

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
    """Skip Lovelace card registration during normal setup tests."""
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


async def setup_mtx(hass: HomeAssistant, client, options=None, data=None):
    entry = MockConfigEntry(
        domain=DOMAIN, data=data or MTX_DATA, options=options or {}, version=2
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.audac_mtx.coordinator.MTXClient", return_value=client
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


def make_xmp_client(slots_data, module_types, favourites=None):
    client = MagicMock()
    client.module_types = module_types
    client.set_module_config = MagicMock()
    client.get_all_slots = AsyncMock(return_value=slots_data)
    client.get_all_favourites = AsyncMock(return_value=favourites or [])
    client.disconnect = AsyncMock()
    return client


async def setup_xmp(hass: HomeAssistant, client, options=None):
    entry = MockConfigEntry(
        domain=DOMAIN, data=XMP_DATA, options=options or {}, version=2
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.audac_mtx.xmp44_coordinator.XMP44Client",
        return_value=client,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


# ── Migration ───────────────────────────────────────────────────────


async def test_migrate_v1_small_zone_count(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, data={"host": "h", "zones": 4}, version=1
    )
    entry.add_to_hass(hass)
    assert await async_migrate_entry(hass, entry)
    assert entry.version == 2
    assert entry.data[CONF_MODEL] == MODEL_MTX48


async def test_migrate_v1_large_zone_count(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, data={"host": "h", "zones": 8}, version=1
    )
    entry.add_to_hass(hass)
    assert await async_migrate_entry(hass, entry)
    assert entry.version == 2
    assert entry.data[CONF_MODEL] == MODEL_MTX88


async def test_migrate_v1_model_already_present(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "h", "zones": 8, CONF_MODEL: MODEL_MTX48},
        version=1,
    )
    entry.add_to_hass(hass)
    assert await async_migrate_entry(hass, entry)
    assert entry.version == 2
    assert entry.data[CONF_MODEL] == MODEL_MTX48


async def test_migrate_v2_noop(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data=MTX_DATA, version=2)
    entry.add_to_hass(hass)
    assert await async_migrate_entry(hass, entry)
    assert entry.version == 2


# ── MTX setup / unload ──────────────────────────────────────────────


async def test_setup_mtx_creates_entities(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client)

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.client is client

    ent_reg = er.async_get(hass)
    for zone in range(1, 9):
        for platform, suffix in (
            ("media_player", f"_zone_{zone}"),
            ("number", f"_zone_{zone}_volume"),
            ("switch", f"_zone_{zone}_mute"),
            ("select", f"_zone_{zone}_source"),
            ("sensor", f"_zone_{zone}_active_source"),
            ("button", f"_zone_{zone}_vol_up"),
            ("button", f"_zone_{zone}_vol_down"),
        ):
            assert ent_reg.async_get_entity_id(
                platform, DOMAIN, f"{entry.entry_id}{suffix}"
            ), f"missing {platform}{suffix}"
    assert ent_reg.async_get_entity_id(
        "button", DOMAIN, f"{entry.entry_id}_mtx_save"
    )

    # Hub device exists
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get_device_by_identifier(
        (DOMAIN, entry.entry_id), entry.entry_id
    )
    assert device is not None
    assert device.manufacturer == "Audac"
    assert device.model == "MTX88"


async def test_unload_mtx(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
    client.disconnect.assert_awaited()


async def test_setup_mtx48_default_zone_count(hass: HomeAssistant) -> None:
    data = {"host": "192.168.1.51", CONF_MODEL: MODEL_MTX48, "name": "MTX48"}
    client = make_mtx_client({z: make_zone_data() for z in range(1, 5)})
    entry = await setup_mtx(hass, client, data=data)
    ent_reg = er.async_get(hass)
    assert ent_reg.async_get_entity_id(
        "media_player", DOMAIN, f"{entry.entry_id}_zone_4"
    )
    assert not ent_reg.async_get_entity_id(
        "media_player", DOMAIN, f"{entry.entry_id}_zone_5"
    )


# ── Zone visibility ─────────────────────────────────────────────────


async def test_zone_visibility_hides_zones(hass: HomeAssistant) -> None:
    options = {"zone_2_visible": False, "zone_3_link": "1"}
    client = make_mtx_client()
    entry = await setup_mtx(hass, client, options=options)

    ent_reg = er.async_get(hass)

    def hidden(platform: str, suffix: str) -> bool:
        eid = ent_reg.async_get_entity_id(
            platform, DOMAIN, f"{entry.entry_id}{suffix}"
        )
        return ent_reg.async_get(eid).hidden_by == RegistryEntryHider.INTEGRATION

    # Zone 2 hidden via zone_2_visible, zone 3 hidden because it is a slave
    for zone in (2, 3):
        assert hidden("media_player", f"_zone_{zone}")
        assert hidden("number", f"_zone_{zone}_volume")
        assert hidden("switch", f"_zone_{zone}_mute")
        assert hidden("select", f"_zone_{zone}_source")
        assert hidden("sensor", f"_zone_{zone}_active_source")
    assert not hidden("media_player", "_zone_1")


async def test_zone_visibility_unhides_zones(hass: HomeAssistant) -> None:
    client = make_mtx_client()
    entry = await setup_mtx(hass, client, options={"zone_2_visible": False})

    ent_reg = er.async_get(hass)
    eid = ent_reg.async_get_entity_id(
        "media_player", DOMAIN, f"{entry.entry_id}_zone_2"
    )
    assert ent_reg.async_get(eid).hidden_by == RegistryEntryHider.INTEGRATION

    # Entity belonging to another config entry is ignored by the scan
    other_entry = MockConfigEntry(domain=DOMAIN, data=MTX_DATA, version=2)
    other_entry.add_to_hass(hass)
    other = ent_reg.async_get_or_create(
        "media_player",
        DOMAIN,
        f"{other_entry.entry_id}_zone_2",
        config_entry=other_entry,
    )

    hass.config_entries.async_update_entry(entry, options={"zone_2_visible": True})
    await _async_update_zone_visibility(hass, entry, 8)
    assert ent_reg.async_get(eid).hidden_by is None
    assert ent_reg.async_get(other.entity_id).hidden_by is None


# ── XMP44 setup ─────────────────────────────────────────────────────


async def test_setup_xmp44_hub_and_slot_devices(hass: HomeAssistant) -> None:
    slots = {
        1: {
            "module_type": 8,
            "module_name": "BMP40",
            "module_description": "Bluetooth Receiver",
            "module_version": "1.2",
            "status": "playing",
            "output_gain": 0,
        },
    }
    client = make_xmp_client(slots, {1: 8})
    entry = await setup_xmp(hass, client, options={"slot_1_module": "8"})

    assert entry.state is ConfigEntryState.LOADED

    dev_reg = dr.async_get(hass)
    hub = dev_reg.async_get_device_by_identifier(
        (DOMAIN, entry.entry_id), entry.entry_id
    )
    assert hub is not None
    assert hub.model == "XMP44"

    slot_dev = dev_reg.async_get_device_by_identifier(
        (DOMAIN, f"{entry.entry_id}_slot_1"), entry.entry_id
    )
    assert slot_dev is not None
    assert slot_dev.via_device_id == hub.id

    ent_reg = er.async_get(hass)
    assert ent_reg.async_get_entity_id(
        "media_player", DOMAIN, f"{entry.entry_id}_xmp44_slot_1"
    )

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
    client.disconnect.assert_awaited()


async def test_setup_registers_card_once(hass: HomeAssistant, monkeypatch) -> None:
    monkeypatch.setattr(audac_init, "_CARD_REGISTERED", False)
    mock_register = AsyncMock()
    hass.http = MagicMock(async_register_static_paths=mock_register)
    client = make_mtx_client()
    await setup_mtx(hass, client)
    mock_register.assert_awaited_once()
    assert audac_init._CARD_REGISTERED is True


# ── Card version reading ────────────────────────────────────────────


def test_read_card_version_ok(tmp_path) -> None:
    path = tmp_path / "card.js"
    path.write_text('const CARD_VERSION = "1.2.3";\nrest')
    assert _read_card_version(path) == "1.2.3"


def test_read_card_version_no_marker(tmp_path) -> None:
    path = tmp_path / "card.js"
    path.write_text("console.log('hi');")
    assert _read_card_version(path) == "0"


def test_read_card_version_missing_file(tmp_path) -> None:
    assert _read_card_version(tmp_path / "nope.js") == "0"


def test_read_card_version_malformed(tmp_path) -> None:
    path = tmp_path / "card.js"
    path.write_text("const CARD_VERSION = broken")
    assert _read_card_version(path) == "0"


# ── _register_card branches ─────────────────────────────────────────


async def test_register_card_missing_www_dir(hass: HomeAssistant) -> None:
    fake_www = MagicMock()
    fake_www.is_dir.return_value = False
    fake_path = MagicMock()
    fake_path.parent.__truediv__ = MagicMock(return_value=fake_www)
    with patch("custom_components.audac_mtx.Path", return_value=fake_path):
        await _register_card(hass)  # No exception, warning logged


async def test_register_card_already_registered_paths(hass: HomeAssistant) -> None:
    hass.http = MagicMock(
        async_register_static_paths=AsyncMock(
            side_effect=RuntimeError("Path already registered")
        )
    )
    await _register_card(hass)  # swallowed


async def test_register_card_other_runtime_error(hass: HomeAssistant) -> None:
    hass.http = MagicMock(
        async_register_static_paths=AsyncMock(side_effect=RuntimeError("boom"))
    )
    with pytest.raises(RuntimeError):
        await _register_card(hass)


# ── Lovelace resource registration ──────────────────────────────────


class FakeResources:
    def __init__(self, items=None, loaded=True):
        self.loaded = loaded
        self._items = items or []
        self.updated = []
        self.created = []

    def async_items(self):
        return self._items

    async def async_update_item(self, item_id, data):
        self.updated.append((item_id, data))

    async def async_create_item(self, data):
        self.created.append(data)


async def test_lovelace_resource_created(hass: HomeAssistant) -> None:
    resources = FakeResources()
    hass.data["lovelace"] = SimpleNamespace(resources=resources)
    await _register_lovelace_resource(hass, CARD_URL_PATH, f"{CARD_URL_PATH}?v=1", "MTX")
    assert resources.created == [
        {"res_type": "module", "url": f"{CARD_URL_PATH}?v=1"}
    ]


async def test_lovelace_resource_updated(hass: HomeAssistant) -> None:
    resources = FakeResources(
        items=[{"id": "abc", "url": f"{CARD_URL_PATH}?v=0"}]
    )
    hass.data["lovelace"] = SimpleNamespace(resources=resources)
    await _register_lovelace_resource(hass, CARD_URL_PATH, f"{CARD_URL_PATH}?v=1", "MTX")
    assert resources.updated == [("abc", {"url": f"{CARD_URL_PATH}?v=1"})]
    assert resources.created == []


async def test_lovelace_resource_up_to_date(hass: HomeAssistant) -> None:
    resources = FakeResources(
        items=[{"id": "abc", "url": f"{CARD_URL_PATH}?v=1"}]
    )
    hass.data["lovelace"] = SimpleNamespace(resources=resources)
    await _register_lovelace_resource(hass, CARD_URL_PATH, f"{CARD_URL_PATH}?v=1", "MTX")
    assert resources.updated == []
    assert resources.created == []


async def test_lovelace_resource_not_available_running(hass: HomeAssistant) -> None:
    hass.data.pop("lovelace", None)
    await _register_lovelace_resource(hass, CARD_URL_PATH, f"{CARD_URL_PATH}?v=1", "MTX")
    # Nothing registered, no exception (YAML mode branch)


async def test_lovelace_resource_deferred_until_started(hass: HomeAssistant) -> None:
    hass.data.pop("lovelace", None)
    hass.set_state(CoreState.not_running)
    await _register_lovelace_resource(hass, CARD_URL_PATH, f"{CARD_URL_PATH}?v=1", "MTX")

    # Lovelace becomes available before HA finishes starting
    resources = FakeResources()
    hass.data["lovelace"] = SimpleNamespace(resources=resources)
    hass.set_state(CoreState.running)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()
    assert resources.created


async def test_lovelace_resource_not_loaded_deferred(hass: HomeAssistant) -> None:
    resources = FakeResources(loaded=False)
    hass.data["lovelace"] = SimpleNamespace(resources=resources)
    await _register_lovelace_resource(hass, CARD_URL_PATH, f"{CARD_URL_PATH}?v=1", "MTX")
    assert resources.created == []

    resources.loaded = True
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()
    assert resources.created


async def test_lovelace_resource_error_swallowed(hass: HomeAssistant) -> None:
    resources = FakeResources()

    async def boom(data):
        raise ValueError("storage broken")

    resources.async_create_item = boom
    hass.data["lovelace"] = SimpleNamespace(resources=resources)
    # Must not raise
    await _register_lovelace_resource(hass, CARD_URL_PATH, f"{CARD_URL_PATH}?v=1", "MTX")
