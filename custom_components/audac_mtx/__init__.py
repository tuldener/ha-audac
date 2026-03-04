"""Audac MTX integration for Home Assistant."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform

from .const import DOMAIN, CARD_URL_PATH, CARD_FILENAME, CONF_MODEL, MODEL_MTX48, MODEL_MTX88, MODEL_ZONES
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
    entry.async_on_unload(coordinator.async_shutdown)

    return True


async def _register_card(hass: HomeAssistant) -> None:
    www_dir = Path(__file__).parent / "www"
    if not www_dir.is_dir():
        _LOGGER.warning("Audac MTX www directory not found at %s", www_dir)
        return

    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                CARD_URL_PATH,
                str(www_dir / CARD_FILENAME),
                cache_headers=False,
            )
        ]
    )

    try:
        if hass.data.get("lovelace_resources"):
            from homeassistant.components.lovelace.resources import ResourceStorageCollection
            resources: ResourceStorageCollection = hass.data["lovelace_resources"]
            existing = [
                r for r in resources.async_items()
                if r.get("url", "").startswith(CARD_URL_PATH)
            ]
            if not existing:
                await resources.async_create_item(
                    {"res_type": "module", "url": CARD_URL_PATH}
                )
                _LOGGER.info("Registered Audac MTX card as Lovelace resource: %s", CARD_URL_PATH)
            else:
                _LOGGER.debug("Audac MTX card already registered as Lovelace resource")
        else:
            from homeassistant.components.frontend import add_extra_js_url
            add_extra_js_url(hass, CARD_URL_PATH)
            _LOGGER.info("Registered Audac MTX card via add_extra_js_url: %s", CARD_URL_PATH)
    except Exception as err:
        _LOGGER.warning(
            "Could not auto-register Audac MTX card. Add manually as Lovelace resource (type: module): %s — %s",
            CARD_URL_PATH, err,
        )


async def _async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
    return unload_ok
