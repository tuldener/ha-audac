# Audac MTX

HACS Integration for Home Assistant to control Audac MTX audio matrices (MTX48/MTX88).
Standalone integration with direct TCP communication to the MTX device, including a Bubble Card-inspired Lovelace card.

## Architecture

### Backend (Custom Component)
- `custom_components/audac_mtx/` — HA integration
- `mtx_client.py` — Async TCP client with auto-reconnect (port 5001), chunk-based reading
- `coordinator.py` — DataUpdateCoordinator, 10s polling interval
- `media_player.py` — MediaPlayer entities per zone (core: volume, mute, source, bass, treble)
- `select.py` — Select entities for source selection (entity_category: CONFIG)
- `number.py` — Number entities for volume control 0-100% (entity_category: CONFIG)
- `switch.py` — Switch entities for mute toggle (entity_category: CONFIG)
- `sensor.py` — Sensor entities showing active source (entity_category: DIAGNOSTIC)
- `config_flow.py` — Setup flow with connection test + Options flow with validation
- `const.py` — Shared constants, INPUT_NAMES, BASS_TREBLE_MAP, get_source_names()
- `services.yaml` — Custom services (set_bass, set_treble) under media_player domain
- `strings.json` / `translations/` — EN and DE translations

### Entity Structure per Zone
| Entity | Domain | Category | Role |
|--------|--------|----------|------|
| media_player | `media_player` | — | Core zone entity (volume, mute, source, bass/treble) |
| select | `select` | CONFIG | Source selection (for custom card) |
| number | `number` | CONFIG | Volume 0-100% slider (for custom card) |
| switch | `switch` | CONFIG | Mute on/off (for custom card) |
| sensor | `sensor` | DIAGNOSTIC | Active source (read-only display) |

### Frontend (Lovelace Card)
- `custom_components/audac_mtx/www/audac-mtx-card.js` — Web Component card
- 5 card types: `audac-mtx-card`, `audac-mtx-volume-card`, `audac-mtx-source-card`, `audac-mtx-bass-card`, `audac-mtx-treble-card`
- Card registered via ResourceStorageCollection (preferred) with add_extra_js_url fallback

### HACS Structure (GitHub)
```
custom_components/audac_mtx/
  __init__.py, config_flow.py, const.py, coordinator.py,
  manifest.json, media_player.py, select.py, number.py,
  switch.py, sensor.py, mtx_client.py, services.yaml,
  strings.json, translations/{de,en}.json,
  www/audac-mtx-card.js
hacs.json
README.md
LICENSE
```

### Development (Replit only, gitignored)
- `server.js` — Node.js preview server (port 5000)
- `preview/index.html` — Mock HA states for card testing

### MTX Protocol
- TCP port 5001, format: `#|X001|web|CMD|ARG|U|\r\n`
- GET responses strip 'G' prefix (GVALL → VALL), but client accepts both
- Chunk-based TCP reading handles \r, \n, and \r\n line endings
- Response command validation prevents cross-assignment of bulk data
- Volume: attenuation 0-70 (0=max, 70=min), card converts to 0-100%
- Routing: 0=Off, 1-8=Inputs
- Bass/Treble: 0-14 mapped to -14dB to +14dB
- Bulk commands: GVALL, GRALL, GMALL with fallback to per-zone GZI0x

### Config Flow
- VERSION = 2 with async_migrate_entry for v1→v2 migration
- Model dropdown (MTX48=4 zones, MTX88=8 zones)
- Options: zone names, zone visibility, source names, source visibility
- Options flow validates non-empty names

## Tech Stack
- Backend: Python (HA custom component)
- Frontend: Vanilla JS Web Component
- Preview: Node.js HTTP server (port 5000)
