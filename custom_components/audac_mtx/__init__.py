"""Audac MTX integration for Home Assistant."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CARD_URL_PATH, CARD_FILENAME, XMP44_CARD_FILENAME, XMP44_CARD_URL_PATH, CONF_MODEL, MODEL_MTX48, MODEL_MTX88, MODEL_XMP44, MODEL_ZONES, is_xmp_model
from .coordinator import AudacMTXCoordinator
from .xmp44_coordinator import XMP44Coordinator

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


def _read_card_version(js_path: Path) -> str:
    """Read CARD_VERSION from the first line of a JS file.

    Expected format: const CARD_VERSION = "x.y.z";
    Falls back to "0" if unreadable.
    """
    try:
        first_line = js_path.read_text(encoding="utf-8").split("\n", 1)[0]
        if "CARD_VERSION" in first_line:
            return first_line.split('"')[1]
    except (IndexError, OSError):
        pass
    return "0"

PLATFORMS_MTX = [
    Platform.MEDIA_PLAYER,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.SWITCH,
    Platform.SENSOR,
    Platform.BUTTON,
]

PLATFORMS_XMP44 = [
    Platform.MEDIA_PLAYER,
    Platform.BUTTON,
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
        hass.data[DOMAIN]["loaded"] = True  # Set early to prevent race condition
        await _register_card(hass)

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
        _LOGGER.warning("Audac www directory not found at %s", www_dir)
        return

    # Read versions from JS files (single source of truth)
    # Use executor to avoid blocking the event loop
    mtx_version = await hass.async_add_executor_job(_read_card_version, www_dir / CARD_FILENAME)
    xmp44_version = await hass.async_add_executor_job(_read_card_version, www_dir / XMP44_CARD_FILENAME)

    mtx_url_versioned = f"{CARD_URL_PATH}?v={mtx_version}"
    xmp44_url_versioned = f"{XMP44_CARD_URL_PATH}?v={xmp44_version}"

    # Register static paths for both cards
    paths = [
        StaticPathConfig(
            CARD_URL_PATH,
            str(www_dir / CARD_FILENAME),
            cache_headers=False,
        ),
    ]
    if (www_dir / XMP44_CARD_FILENAME).exists():
        paths.append(
            StaticPathConfig(
                XMP44_CARD_URL_PATH,
                str(www_dir / XMP44_CARD_FILENAME),
                cache_headers=False,
            )
        )
    try:
        await hass.http.async_register_static_paths(paths)
    except RuntimeError as err:
        if "already registered" in str(err):
            _LOGGER.debug("Audac static paths already registered: %s", err)
        else:
            raise
    _LOGGER.debug("Registered Audac static paths: %s (v%s), %s (v%s)", CARD_URL_PATH, mtx_version, XMP44_CARD_URL_PATH, xmp44_version)

    # Register as Lovelace storage resources
    await _register_lovelace_resource(hass, CARD_URL_PATH, mtx_url_versioned, "MTX")
    if (www_dir / XMP44_CARD_FILENAME).exists():
        await _register_lovelace_resource(hass, XMP44_CARD_URL_PATH, xmp44_url_versioned, "XMP44")


async def _register_lovelace_resource(hass: HomeAssistant, url_path: str, url_versioned: str, label: str = "") -> None:
    """Register a card as a Lovelace storage resource."""
    try:
        from homeassistant.components.lovelace import DOMAIN as LL_DOMAIN
        from homeassistant.components.lovelace.resources import ResourceStorageCollection

        ll_data = hass.data.get(LL_DOMAIN)
        if not ll_data or not hasattr(ll_data, "resources"):
            if not hass.is_running:
                async def _deferred(_event) -> None:
                    await _register_lovelace_resource(hass, url_path, url_versioned, label)
                hass.bus.async_listen_once("homeassistant_started", _deferred)
                _LOGGER.debug("Audac %s: Lovelace not ready, deferring to homeassistant_started", label)
            else:
                _LOGGER.debug("Audac %s: Lovelace resources not available (YAML mode?). Add manually: %s", label, url_versioned)
            return

        resources: ResourceStorageCollection = ll_data.resources
        if not resources.loaded:
            _LOGGER.debug("Audac %s: Lovelace resources not yet loaded, deferring", label)
            async def _deferred(_event) -> None:
                await _register_lovelace_resource(hass, url_path, url_versioned, label)
            hass.bus.async_listen_once("homeassistant_started", _deferred)
            return

        # Find existing resource by URL path
        existing = None
        for item in resources.async_items():
            if url_path in item.get("url", ""):
                existing = item
                break

        if existing:
            if existing["url"] != url_versioned:
                await resources.async_update_item(existing["id"], {"url": url_versioned})
                _LOGGER.info("Updated Audac %s card resource to %s", label, url_versioned)
            else:
                _LOGGER.debug("Audac %s card resource up-to-date: %s", label, url_versioned)
        else:
            await resources.async_create_item({"res_type": "module", "url": url_versioned})
            _LOGGER.info("Registered Audac %s card as Lovelace resource: %s", label, url_versioned)

    except Exception as err:
        _LOGGER.warning("Could not register Audac %s Lovelace resource: %s", label, err)


async def _async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    model = entry.data.get(CONF_MODEL, "mtx88")
    platforms = PLATFORMS_XMP44 if is_xmp_model(model) else PLATFORMS_MTX
    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
