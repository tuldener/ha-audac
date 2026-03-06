"""Shared helper utilities for Audac MTX integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_registry import RegistryEntryHider


async def _async_update_zone_visibility(
    hass: HomeAssistant, entry: ConfigEntry, zones_count: int, domain: str
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
        # Slave zones (linked to a master) are always hidden
        linked_to = entry.options.get(f"zone_{zone}_linked_to", 0)
        is_slave = linked_to != 0
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
