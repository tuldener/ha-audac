# Changelog

## 3.8.7
- Static previews for Volume, Source, Bass, Treble sub-cards in the HA card picker
- Removed `audac-mtx-more-info` from card picker (more-info panel, not a standalone card)
- Fixed `_config.title` crash in MoreInfo `_getZones()`
- Linked Audac to audac.eu in README

## 3.8.6
- Fix: `helpers.py` now checks all 3 link formats (`zone_z_link`, `zone_z_links`, `zone_z_linked_to`) for slave zone visibility — was only checking legacy format
- Fix: Removed duplicate `window.customCards` registration at end of `audac-mtx-card.js` causing double entries in HA card picker
- Fix: Removed redundant `client.disconnect()` in config flow (already handled by `finally`)

## 3.8.5
- README title and references renamed from "Audac MTX" to "Audac"
- Repository references updated from `tuldener/Audac-Mtx-Control` to `FX6W9WZK/ha-audac`

## 3.8.4
- README: Added XMP44 Lovelace Card manual setup instructions

## 3.8.3
- XMP44 card: Accordion behavior – only one slot expanded at a time

## 3.8.2
- Fix: XMP44 card flickering – state diff rendering like MTX card

## 3.8.1
- MTX: Save button + Volume Up/Down buttons per zone

## 3.8.0
- All module controls rendered as buttons with full card rendering

## 3.7.2
- Prepare repo rename from `Audac-Mtx-Control` to `ha-audac`

## 3.7.1
- FMP40 triggers rendered as rows – 50% Play / 50% Stop per line

## 3.7.0
- XMP44 Card: FMP40 trigger buttons, BMP40 Bluetooth controls

## 3.6.1
- Fix: XMP44 card editor – prevent Assist popup when typing

## 3.6.0
- XMP44 Lovelace Card (separate Bubble Card-inspired card)

## 3.5.0
- Complete DMP40, TMP40, MMP40 module support

## 3.4.0
- NMP40 Network Audio Player – sensors and IP polling

## 3.3.0
- BMP40 Bluetooth controls – pairing, disconnect, sensors

## 3.2.2
- Critical fix: Accept ALL broadcast responses from XMP44

## 3.2.1
- IMP40 station buttons from favourites

## 3.2.0
- IMP40 Internet Radio with source selection (favourites)

## 3.1.2
- Individual name field per FMP40 trigger

## 3.1.1
- FMP40 trigger config only shown for FMP40 slots, custom trigger names

## 3.1.0
- FMP40 voice file trigger buttons

## 3.0.6
- XMP44 modules as individual sub-devices (via_device)

## 3.0.5
- Renamed integration to "Audac", added XMP44 device info

## 3.0.4
- Fix: Duplicate card registration when multiple config entries

## 3.0.3
- Removed auto-detect, kept simple manual module dropdowns

## 3.0.2
- Auto-detect button for XMP44 modules

## 3.0.1
- Manual module selection for XMP44 via dropdown in options

## 3.0.0
- **XMP44 support** – Audac XMP44 modular audio system is now supported
- New client framework: `AudacClient` base class for shared TCP protocol
- `MTXClient` and `XMP44Client` inherit from `AudacClient`
- Automatic module detection via GTPS command (DMP40, TMP40, IMP40, MMP40, FMP40, BMP40, NMP40)
- Media player entity per installed XMP44 module with module-specific features
- Config flow: XMP44 selectable as third model
- No breaking changes for existing MTX users

## 2.5.0
- Zone coupling as dropdown instead of checkboxes (a slave zone can only have one master)
- Default: "No coupling"
- Full backward compatibility with old checkbox and legacy format

## 2.4.7
- Fix: Added `issue_tracker` to manifest.json (HACS required field)
- Fix: Added `http` to `after_dependencies` (Hassfest validation)
- Fix: Added `CONFIG_SCHEMA` (`config_entry_only_config_schema`)

## 2.4.6
- Brand assets (icon.png) for HACS Default Store
- GitHub Actions workflow for HACS and Hassfest validation
- Cleaned up hacs.json (removed invalid fields)
- HACS "My" button in README for easy installation

## 2.4.5
- Fix: Linked zones now show the configured name instead of "Zone X"
- New `zone_number` attribute on each media player entity
- `mtxLinkedNames()` now matches via `zone_number` instead of entity ID pattern

## 2.4.4
- Fix: SyntaxError in `_renderZone` (single quotes in template literal)
- Fix: Typos in DE translations

## 2.4.3
- Linked slave zone names shown next to the link icon (e.g. `Bar 🔗 Subwoofer`)
- New helper function `mtxLinkedNames()` resolves zone numbers to friendly names

## 2.4.2
- i18n fallback changed to English (instead of German)

## 2.4.1
- Automatic language detection (German / English) for the entire Lovelace card
- Language read from HA user settings (`hass.language`)
- All card UI strings translated: labels, tooltips, editor, error messages, card descriptions

## 2.4.0
- README: Real screenshot as card preview

## 2.3.9
- Card editor: Removed "Zones" section (manual add/remove), auto-discover is sufficient

## 2.3.8
- README: Card preview with generic zone names, absolute image path for HACS

## 2.3.7
- Fix: README image displayed correctly (absolute URL via raw.githubusercontent.com)
- Fix: Version badge switched to static

## 2.3.3
- Bass/treble visibility removed from integration settings (card editor toggle only)
- CARD_VERSION correctly bumped for browser cache busting

## 2.3.2
- Fix: Removed duplicate code in coordinator.py – second `_fetch_data` (without sync) was overwriting the first
- Fix: Cleaned up `async_shutdown` (removed dead code)

## 2.3.1
- Fix: Zone coupling was not working (sync + hiding in card)
- Coordinator now reads `zone_X_links` (list) instead of `zone_X_linked_to` (int)
- Card correctly hides slave zones

## 2.3.0
- Coupling as checkboxes (SelectSelector, multi-select) instead of dropdown
- Migration from old to new coupling format

## 2.2.1
- Slave zone sync on every coordinator poll (~60 s)
- Volume tolerance (±2 units), exact matching for mute, source, bass, treble

## 2.2.0
- Zone coupling (master/slave) in integration options
- Immediate mirroring when sending commands to the master zone

## 2.1.1
- Fix: Zone dropdown in single card editor

## 2.1.0
- Bass/treble visibility in card editor

## 2.0.1
- Fix: `_async_update_zone_visibility` was not defined
- Fix: Visibility covers all entity types
- New: Central `helpers.py` module

## 2.0.0
- Entities are always created, visibility via Entity Registry

## 1.9.2
- Coordinator SCAN_INTERVAL 60 s, timeout improvements

## 1.7.4
- Fix: Card not loading on first render (ll-rebuild)

## 1.7.3
- Fix: `window.customCards` moved to top of file

## 1.7.0
- Zone names auto-truncated, volume as background fill

## 1.6.0
- Flickering fixed: smart DOM patching, interactive bass/treble sliders

## 1.3.0
- Services `routing_up` / `routing_down`, protocol documentation

## 1.0.0
- Initial release
