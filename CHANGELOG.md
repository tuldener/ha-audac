# Changelog

## 3.14.3
- **Fix: persistent unavailable state** — Single command timeout reduced from 25s to 5s
- A hung TCP command now frees the lock in 5s instead of 25s, preventing cascading timeouts
- Overall timeouts restored: GET_ALL_ZONES 45s, UPDATE 55s (were aggressively reduced to 25s/35s in v3.12.0)
- Both MTX and XMP44 coordinators benefit from faster failure recovery

## 3.14.2
- Compact zone/slot rows further to match HA standard container padding
- Row padding: 10px 12px → 8px 12px (row height ~52px, down from ~58px)
- Content gap: 12px → 10px
- Container gap between rows: 8px → 6px
- Name line-height: default → 1.3

## 3.14.1
- Compact zone/slot row sizing to match HA standard row height (~56px)
- Zone/slot name: 14px → 13px (matches Bubble Card)
- Info column gap: 2px → 1px
- Detail text line-height: 1.2 (tighter)

## 3.14.0
- **HA theme integration**: Cards now use `--ha-card-background`, `--ha-card-border-radius`, `--ha-card-border-color`, and `--ha-card-box-shadow` CSS variables
- Removed hardcoded opaque backgrounds and `backdrop-filter: blur()` from card containers
- Zone/slot rows use subtle `rgba()` overlays instead of opaque card backgrounds
- Cards blend seamlessly with Bubble Card, transparent themes, and glassmorphism themes
- Both MTX and XMP44 cards (including slot card) updated

## 3.13.1
- **Fix: Lovelace resource registration for HA 2026.3+** — used `hasattr(ll_data, "resources")` attribute access instead of dict-style lookup (HA changed from dict to object)
- **Fix: blocking `read_text` call** — version reading now uses `async_add_executor_job` to avoid event loop warning
- Simplified and more robust `_register_lovelace_resource` implementation

## 3.13.0
- **Auto-versioning**: Card version is now single-source-of-truth in the JS files — `__init__.py` reads it dynamically, no more manual syncing of `CARD_VERSION` in `const.py`
- **Bubble Card sizing** for both MTX and XMP44 cards:
  - Karten-Radius: 25px durchgehend (statt 24px/18px gemischt)
  - Karten-Padding: 16px (statt 20px)
  - Header-Icon: 38px, rund (statt 42px, eckig)
  - Titel: 14px (statt 16px)
  - Zone/Slot-Icons: 36px, rund (statt 40px, eckig)
  - Zone/Slot-Zeilen: ~56px (statt ~68px)
  - Action-Buttons: Pillenform 20px Radius (statt eckig 12px)
  - Play-Buttons: rund (statt eckig)

## 3.12.0
- **Rewrite: GZI0x per-zone polling** replaces bulk GVALL/GRALL/GMALL strategy
- Each zone queried individually via `GZI0x` (volume^routing^mute^bass^treble in one response)
- **Per-zone failure resilience**: if one zone fails, previous data for that zone is kept while other zones update normally
- **Always fresh bass/treble**: no more cache, every poll returns all 5 values per zone
- 8 TCP commands per poll (~5-6s) — simple, predictable, resilient
- Removed bass/treble cache (no longer needed)
- Reduced timeouts (GET_ALL_ZONES: 45→25s, UPDATE: 55→35s)

## 3.11.0
- **Faster MTX polling**: Bass/treble values are now cached and only refreshed every 5th poll
- Normal polls: 3 TCP commands (~2-3s) instead of 19 (~15-20s)
- Eliminates HA warning "Update is taking over 10 seconds" for 80% of polls
- Bass/treble cache is updated immediately when set via HA (no wait for next refresh)

## 3.10.3
- **Plausibility check**: MTX coordinator detects suspicious all-zero responses (routing=0 on all zones) and keeps previous state instead of showing "0/6"
- **Incomplete data detection**: Keeps previous state when fewer zones than expected are returned
- Fixed failure counter not being properly maintained when plausibility check triggers

## 3.10.2
- Fix: `coroutine '_register_lovelace_resource' was never awaited` warning on Python 3.14
- Replaced sync lambda with async callback for `homeassistant_started` event listener

## 3.10.1
- Fix: XMP44 slot card editor no longer destroyed by state refreshes
- Editor renders only once (not on every `set hass()` call)
- Card only re-renders on actual config or state changes (config snapshot diff)

## 3.10.0
- **New: `audac-xmp44-slot-card`** — individual Lovelace card per XMP44 module
- Supports all module types (BMP40, IMP40, FMP40, DMP40, TMP40, MMP40, NMP40)
- Entity picker in card editor with auto-discover
- Always-expanded controls (no accordion click needed)
- Same Bubble Card-inspired design as the main XMP44 card
- Static preview in card picker

## 3.9.3
- Auto-cleanup of legacy IMP40 station entities (old unique_id format without pointer)
- No more duplicate "Nicht verfügbar" buttons after upgrading from v3.8.7 or earlier

## 3.9.2
- Icon now uses dark rounded background with white logo — works on both light and dark HA themes
- HA frontend only requests `icon.png` (not `dark_icon.png`), so the icon must work universally

## 3.9.1
- Rebuilt all brand assets from official AUDAC vector source (`.ai`)
- Light and dark variants with proper luminance-based alpha transparency
- Smaller file sizes and crisp edges from high-res vector rendering

## 3.9.0
- **Resilient state handling**: Entities keep their last known state for up to 3 consecutive poll failures before becoming unavailable. Previously, a single failed response could mark entities as unavailable.
- Applies to both MTX and XMP44 coordinators
- Failure counter resets on every successful poll
- Log messages now show failure count (e.g. `failure 2/3`)

## 3.8.9
- Fix: Lovelace resource warning at startup — defer registration to `homeassistant_started` when collection not ready yet (instead of logging a false warning)
- Downgraded fallback message from WARNING to DEBUG

## 3.8.8
- Fix: IMP40 station buttons duplicate unique_id — now includes pointer for guaranteed uniqueness
- Added deduplication for IMP40 favourites list

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
