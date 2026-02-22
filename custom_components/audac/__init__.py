"""Audac integration."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant

from .client import AudacMtxClient, AudacXmpClient
from .const import (
    CONF_DEVICE_ADDRESS,
    CONF_LINE_NAME_PREFIX,
    CONF_MODEL,
    CONF_SCAN_INTERVAL,
    CONF_SLOT_MODULE_PREFIX,
    CONF_SOURCE_ID,
    CONF_ZONE_NAME_PREFIX,
    DEFAULT_DEVICE_ADDRESS,
    DEFAULT_INPUT_LABELS,
    DEFAULT_XMP_DEVICE_ADDRESS,
    DOMAIN,
    MODEL_MTX48,
    MODEL_TO_ZONES,
    MODEL_XMP44,
    MTX_LINE_IDS,
    PLATFORMS,
    XMP_MODULE_AUTO,
    XMP_SLOT_COUNT,
    normalize_xmp_module,
)
from .coordinator import AudacDataUpdateCoordinator
from .services import async_setup_services, async_unload_services

LOGGER = logging.getLogger(__name__)
STATIC_URL_BASE = "/audac-local"
STATIC_DIR = Path(__file__).resolve().parent / "www"


async def _async_forward_platforms(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Forward platforms in background to avoid blocking startup."""
    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception:  # noqa: BLE001
        LOGGER.exception("Failed to forward Audac platforms for entry %s", entry.entry_id)


async def _async_register_static(hass: HomeAssistant) -> None:
    """Expose custom card assets via a stable local URL."""
    if hass.data[DOMAIN].get("_static_registered"):
        return
    if not hasattr(hass, "http") or hass.http is None:
        return
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL_BASE, str(STATIC_DIR), cache_headers=False)]
    )
    hass.data[DOMAIN]["_static_registered"] = True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Audac from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    await _async_register_static(hass)

    config = {**entry.data, **entry.options}
    model = str(config.get(CONF_MODEL, "")).strip().lower()
    if model not in MODEL_TO_ZONES and model != MODEL_XMP44:
        model = MODEL_MTX48
    config[CONF_MODEL] = model

    zone_count = MODEL_TO_ZONES.get(model, 0)
    slot_count = XMP_SLOT_COUNT if model == MODEL_XMP44 else 0

    zone_names = {
        zone: str(config.get(f"{CONF_ZONE_NAME_PREFIX}{zone}", f"Zone {zone}")).strip()
        or f"Zone {zone}"
        for zone in range(1, zone_count + 1)
    }

    input_labels = {
        "0": DEFAULT_INPUT_LABELS["0"],
        **{
            line_id: str(
                config.get(
                    f"{CONF_LINE_NAME_PREFIX}{line_id}",
                    DEFAULT_INPUT_LABELS.get(line_id, f"Line {line_id}"),
                )
            ).strip()
            or DEFAULT_INPUT_LABELS.get(line_id, f"Line {line_id}")
            for line_id in MTX_LINE_IDS
        },
    }

    slot_modules = {
        slot: normalize_xmp_module(
            str(config.get(f"{CONF_SLOT_MODULE_PREFIX}{slot}", XMP_MODULE_AUTO)).strip().lower()
        )
        for slot in range(1, slot_count + 1)
    }
    device_address = str(
        config.get(
            CONF_DEVICE_ADDRESS,
            DEFAULT_XMP_DEVICE_ADDRESS if model == MODEL_XMP44 else DEFAULT_DEVICE_ADDRESS,
        )
    )

    if model == MODEL_XMP44:
        client = AudacXmpClient(
            host=config[CONF_HOST],
            port=config[CONF_PORT],
            source_id=config[CONF_SOURCE_ID],
            device_address=device_address,
        )
    else:
        client = AudacMtxClient(
            host=config[CONF_HOST],
            port=config[CONF_PORT],
            source_id=config[CONF_SOURCE_ID],
            device_address=device_address,
        )

    coordinator = AudacDataUpdateCoordinator(
        hass=hass,
        client=client,
        name=entry.title,
        scan_interval=config[CONF_SCAN_INTERVAL],
        model=model,
        zone_count=zone_count,
        slot_count=slot_count,
        slot_modules=slot_modules,
    )
    # Keep HA startup responsive even if the device is slow or temporarily offline.
    hass.async_create_task(coordinator.async_refresh())

    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
        "config": config,
        "model": model,
        "zone_count": zone_count,
        "zone_names": zone_names,
        "input_labels": input_labels,
        "slot_count": slot_count,
        "slot_modules": slot_modules,
    }

    await async_setup_services(hass)
    hass.async_create_task(_async_forward_platforms(hass, entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an Audac config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    if not hass.data[DOMAIN]:
        await async_unload_services(hass)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload Audac config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
