"""Audac MTX integration for Home Assistant."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CARD_URL_PATH, CARD_URL_VERSIONED, CARD_VERSION, CARD_FILENAME, CONF_MODEL, MODEL_MTX48, MODEL_MTX88, MODEL_XMP44, MODEL_ZONES, is_xmp_model
from .coordinator import AudacMTXCoordinator
from .xmp44_coordinator import XMP44Coordinator

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS_MTX = [
    Platform.MEDIA_PLAYER,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.SWITCH,
    Platform.SENSOR,
]

PLATFORMS_XMP44 = [
    Platform.MEDIA_PLAYER,
]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {"loaded": False})
    return True


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    if config_entry.version < 2:
        _LOGGER.info("Migrating Audac MTX config entry from version %s to 2", config_entry.version)
        new_data = {**config_entry.data}
        if CONF_MODEL not in new_data:
            zones = new_data.get("zones", 8)
            new_data[CONF_MODEL] = MODEL_MTX48 if zones <= 4 else MODEL_MTX88
        hass.config_entries.async_update_entry(config_entry, data=new_data, version=2)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {"loaded": False})

    if not hass.data[DOMAIN].get("loaded"):
        await _register_card(hass)
        hass.data[DOMAIN]["loaded"] = True

    model = entry.data.get(CONF_MODEL, "mtx88")

    if is_xmp_model(model):
        coordinator = XMP44Coordinator(hass, entry)
        platforms = PLATFORMS_XMP44
    else:
        coordinator = AudacMTXCoordinator(hass, entry)
        platforms = PLATFORMS_MTX

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, platforms)

    entry.async_on_unload(
        entry.add_update_listener(_async_update_options)
    )
    entry.async_on_unload(coordinator.async_shutdown)

    return True


async def _register_card(hass: HomeAssistant) -> None:
    www_dir = Path(__file__).parent / "www"
    if not www_dir.is_dir():
        _LOGGER.warning("Audac MTX www directory not found at %s", www_dir)
        return

    # Register static path (unversioned, the file itself)
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                CARD_URL_PATH,
                str(www_dir / CARD_FILENAME),
                cache_headers=False,
            )
        ]
    )
    _LOGGER.debug("Registered Audac MTX static path: %s", CARD_URL_PATH)

    # Register as Lovelace storage resource (same mechanism as HACS)
    # This avoids the race condition caused by add_extra_js_url's async dynamic import()
    await _register_lovelace_resource(hass)


async def _register_lovelace_resource(hass: HomeAssistant) -> None:
    """Register the card as a Lovelace storage resource.

    This is the same mechanism HACS uses and avoids the race condition
    where HA renders Lovelace before add_extra_js_url's dynamic import() resolves.
    Uses multiple strategies to find the ResourceStorageCollection across HA versions.
    """
    # Strategy 1: Direct import of lovelace resources module (works in HA 2023-2026)
    resource_collection = None
    try:
        from homeassistant.components.lovelace.resources import ResourceStorageCollection
        # In HA 2024+, the collection is stored under hass.data["lovelace"]["resources"]
        # In HA 2023, it may be under hass.data["lovelace_resources"]
        lovelace_data = hass.data.get("lovelace")
        if isinstance(lovelace_data, dict):
            candidate = lovelace_data.get("resources")
            if isinstance(candidate, ResourceStorageCollection):
                resource_collection = candidate
                _LOGGER.debug("Found ResourceStorageCollection via hass.data['lovelace']['resources']")

        if resource_collection is None:
            # Try direct key (older HA versions)
            candidate = hass.data.get("lovelace_resources")
            if isinstance(candidate, ResourceStorageCollection):
                resource_collection = candidate
                _LOGGER.debug("Found ResourceStorageCollection via hass.data['lovelace_resources']")

        if resource_collection is None:
            # Scan all lovelace data values
            if isinstance(lovelace_data, dict):
                for key, val in lovelace_data.items():
                    if isinstance(val, ResourceStorageCollection):
                        resource_collection = val
                        _LOGGER.debug("Found ResourceStorageCollection via hass.data['lovelace']['%s']", key)
                        break

    except ImportError as err:
        _LOGGER.debug("Could not import ResourceStorageCollection: %s", err)

    # Strategy 2: Ensure lovelace is loaded and retry
    if resource_collection is None:
        try:
            await hass.async_add_executor_job(
                lambda: None  # just yield to event loop
            )
            # Try to load the lovelace component if not loaded yet
            if "lovelace" not in hass.data:
                _LOGGER.debug("Lovelace not yet loaded, scheduling resource registration after startup")
                hass.bus.async_listen_once(
                    "homeassistant_started",
                    lambda _: hass.async_create_task(_register_lovelace_resource(hass))
                )
                return
        except Exception as err:
            _LOGGER.debug("Strategy 2 failed: %s", err)

    if resource_collection is None:
        _LOGGER.warning(
            "Audac MTX: Could not find Lovelace resource collection. "
            "Please add the card manually via Settings -> Dashboards -> Resources: "
            "URL=%s, Type=JavaScript Module",
            CARD_URL_VERSIONED,
        )
        return

    try:
        existing = [
            r for r in resource_collection.async_items()
            if r.get("url", "").startswith(CARD_URL_PATH)
        ]

        if not existing:
            await resource_collection.async_create_item(
                {"res_type": "module", "url": CARD_URL_VERSIONED}
            )
            _LOGGER.info("Registered Audac MTX card as Lovelace resource: %s", CARD_URL_VERSIONED)
        else:
            # Update URL if version has changed
            for item in existing:
                if item.get("url") != CARD_URL_VERSIONED:
                    await resource_collection.async_update_item(
                        item["id"],
                        {"res_type": "module", "url": CARD_URL_VERSIONED},
                    )
                    _LOGGER.info(
                        "Updated Audac MTX card resource to %s", CARD_URL_VERSIONED
                    )
                else:
                    _LOGGER.debug(
                        "Audac MTX card resource already up-to-date: %s", CARD_URL_VERSIONED
                    )
    except Exception as err:
        _LOGGER.warning("Could not register/update Lovelace resource: %s", err)


async def _async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    model = entry.data.get(CONF_MODEL, "mtx88")
    platforms = PLATFORMS_XMP44 if is_xmp_model(model) else PLATFORMS_MTX
    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
