"""Audac MTX integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant

from .client import AudacMtxClient
from .const import (
    CONF_DEVICE_ADDRESS,
    CONF_LINE_NAME_PREFIX,
    CONF_MODEL,
    CONF_SCAN_INTERVAL,
    CONF_SOURCE_ID,
    CONF_ZONE_NAME_PREFIX,
    CONF_ZONE_COUNT,
    DEFAULT_INPUT_LABELS,
    DOMAIN,
    MTX_LINE_IDS,
    MODEL_TO_ZONES,
    PLATFORMS,
)
from .coordinator import AudacDataUpdateCoordinator
from .services import async_setup_services, async_unload_services


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Audac MTX from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    config = {**entry.data, **entry.options}
    zone_count = config.get(CONF_ZONE_COUNT, MODEL_TO_ZONES[config[CONF_MODEL]])
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

    client = AudacMtxClient(
        host=config[CONF_HOST],
        port=config[CONF_PORT],
        source_id=config[CONF_SOURCE_ID],
        device_address=config[CONF_DEVICE_ADDRESS],
    )

    coordinator = AudacDataUpdateCoordinator(
        hass=hass,
        client=client,
        name=entry.title,
        scan_interval=config[CONF_SCAN_INTERVAL],
        zone_count=zone_count,
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
        "config": config,
        "zone_count": zone_count,
        "zone_names": zone_names,
        "input_labels": input_labels,
    }

    await async_setup_services(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an Audac MTX config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    if not hass.data[DOMAIN]:
        await async_unload_services(hass)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload Audac MTX config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
