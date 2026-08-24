"""Shared helper utilities for Audac MTX integration."""
from __future__ import annotations

from typing import Any, Mapping

from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_registry import RegistryEntryHider


def get_zone_master(options: Mapping[str, Any], zone: int) -> int:
    """Return the master zone number this zone is linked to, or 0.

    Supports three option formats for backward compatibility:
    - zone_z_link: str   (current: dropdown, "0" = no link)
    - zone_z_links: List[str]  (old: checkbox multi-select, first entry wins)
    - zone_z_linked_to: int    (legacy)
    """
    # Current format: single string from dropdown
    link = options.get(f"zone_{zone}_link")
    if link is not None:
        try:
            return int(link)
        except (ValueError, TypeError):
            return 0
    # Old format: list of zone-number strings
    links = options.get(f"zone_{zone}_links")
    if links and isinstance(links, list) and len(links) > 0:
        try:
            return int(links[0])
        except (ValueError, TypeError):
            return 0
    # Legacy format: integer
    return options.get(f"zone_{zone}_linked_to", 0)


def get_slave_zones(
    options: Mapping[str, Any], master_zone: int, zones_count: int
) -> list[int]:
    """Return zone numbers that are linked/slaved to the given master zone.

    Supports the same three option formats as get_zone_master. Note that for
    the old list format, membership of the master zone anywhere in the list
    counts (not just the first entry) — this preserves the historical
    behavior of the media_player platform.
    """
    result = []
    for z in range(1, zones_count + 1):
        if z == master_zone:
            continue
        # Current format: single string from dropdown
        link = options.get(f"zone_{z}_link")
        if link is not None:
            try:
                if int(link) == master_zone:
                    result.append(z)
            except (ValueError, TypeError):
                pass
            continue
        # Old format: list of zone-number strings
        links = options.get(f"zone_{z}_links")
        if links is not None:
            if str(master_zone) in links:
                result.append(z)
            continue
        # Legacy format: integer
        if options.get(f"zone_{z}_linked_to", 0) == master_zone:
            result.append(z)
    return result


def get_zone_links(options: Mapping[str, Any], zones_count: int) -> dict[int, int]:
    """Return {slave_zone: master_zone} mapping from current options."""
    links: dict[int, int] = {}
    for z in range(1, zones_count + 1):
        master = get_zone_master(options, z)
        if master and master != z:
            links[z] = master
    return links


async def _async_update_zone_visibility(
    hass: HomeAssistant, entry: ConfigEntry, zones_count: int
) -> None:
    """Hide/unhide all zone entities based on zone_X_visible config options.

    All sub-entities per zone are covered:
      Unique ID suffix          Platform
      ─────────────────────────────────────
      _zone_{n}                 media_player
      _zone_{n}_volume          number
      _zone_{n}_mute            switch
      _zone_{n}_source          select
      _zone_{n}_active_source   sensor

    Entities are always created so services and automations can use them.
    Visibility is controlled via entity registry (same as native HA entities).
    """
    ent_reg = er.async_get(hass)

    for zone in range(1, zones_count + 1):
        zone_visible = entry.options.get(f"zone_{zone}_visible", True)
        # Slave zones (linked to a master) are always hidden.
        master = get_zone_master(entry.options, zone)
        is_slave = master != 0 and master != zone
        should_be_visible = zone_visible and not is_slave

        suffixes = (
            f"_zone_{zone}",
            f"_zone_{zone}_volume",
            f"_zone_{zone}_mute",
            f"_zone_{zone}_source",
            f"_zone_{zone}_active_source",
        )

        for ent_entry in list(ent_reg.entities.values()):
            if ent_entry.config_entry_id != entry.entry_id:
                continue
            uid = ent_entry.unique_id or ""
            if not any(uid.endswith(s) for s in suffixes):
                continue

            currently_hidden = ent_entry.hidden_by == RegistryEntryHider.INTEGRATION
            if not should_be_visible and not currently_hidden:
                ent_reg.async_update_entity(
                    ent_entry.entity_id,
                    hidden_by=RegistryEntryHider.INTEGRATION,
                )
            elif should_be_visible and currently_hidden:
                ent_reg.async_update_entity(ent_entry.entity_id, hidden_by=None)


async def execute_device_command(coro, action: str):
    """Await a client command and translate transport errors for the UI.

    Raises HomeAssistantError so failed service actions surface as proper
    errors in Home Assistant instead of unhandled ConnectionErrors.
    """
    try:
        return await coro
    except (ConnectionError, TimeoutError, OSError) as err:
        raise HomeAssistantError(f"Audac command failed ({action}): {err}") from err
