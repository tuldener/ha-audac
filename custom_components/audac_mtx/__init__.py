"""Audac MTX integration for Home Assistant."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform

from .const import DOMAIN, CARD_URL_PATH, CARD_URL_VERSIONED, CARD_VERSION, CARD_FILENAME, CONF_MODEL, MODEL_MTX48, MODEL_MTX88, MODEL_ZONES
from .coordinator import AudacMTXCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.MEDIA_PLAYER,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.SWITCH,
    Platform.SENSOR,
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

    coordinator = AudacMTXCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(
        entry.add_update_listener(_async_update_options)
    )
    entry.async_on_unload(coordinator.async_shutdown)  # called automatically on unload

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
    """
    # Try to find the ResourceStorageCollection in hass.data
    # The key changed across HA versions - try all known variants
    resource_collection = None
    for key in ("lovelace_resources", "lovelace", "frontend_extra_module_url"):
        candidate = hass.data.get(key)
        if candidate is None:
            continue
        # lovelace_resources key holds the collection directly
        if hasattr(candidate, "async_items") and hasattr(candidate, "async_create_item"):
            resource_collection = candidate
            _LOGGER.debug("Found Lovelace resource collection under key: %s", key)
            break
        # lovelace key may hold a dict with a resources sub-key
        if isinstance(candidate, dict) and hasattr(candidate.get("resources"), "async_items"):
            resource_collection = candidate["resources"]
            _LOGGER.debug("Found Lovelace resource collection under key: %s/resources", key)
            break

    if resource_collection is None:
        # Fallback: look through all lovelace data values
        try:
            lovelace_data = hass.data.get("lovelace")
            if isinstance(lovelace_data, dict):
                for v in lovelace_data.values():
                    if hasattr(v, "async_items") and hasattr(v, "async_create_item"):
                        resource_collection = v
                        break
        except Exception as err:
            _LOGGER.debug("Could not find lovelace resource collection via fallback: %s", err)

    if resource_collection is None:
        _LOGGER.warning(
            "Audac MTX: Could not find Lovelace resource collection. "
            "Please add the card manually: %s (type: module)",
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
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        # coordinator.async_shutdown() is already registered via async_on_unload
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
