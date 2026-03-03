# Audac MTX Card

HACS Dashboard Plugin (Lovelace Card) for Home Assistant to control Audac MTX audio matrices (MTX48/MTX88).
Works together with the [ha-audac](https://github.com/tuldener/ha-audac) backend integration.

## Architecture

This is a **pure HACS Plugin** (Dashboard type) — no custom_components. The backend is provided by ha-audac.

### Frontend (Lovelace Card)
- `dist/audac-mtx-card.js` — Custom Lovelace card (Web Component), Bubble Card-inspired design
- Works with ha-audac entities: `number.*_volume`, `select.*_source`, `switch.*_mute`
- Card features: volume sliders, mute toggle, source selection grid, bass/treble display, dark/light theme
- Auto-discovery of Audac entities, or manual zone configuration
- Card editor with German labels

### HACS Structure (GitHub only)
```
dist/audac-mtx-card.js    # The card JS file
hacs.json                  # HACS plugin manifest (filename: audac-mtx-card.js)
README.md                  # Documentation
LICENSE                    # MIT License
```

### Development (Replit only, gitignored)
- `server.js` — Node.js HTTP server for card preview (port 5000)
- `preview/index.html` — Preview page with mock HA states using number/select/switch entities
- `custom_components/` — Legacy, kept locally but excluded from GitHub
- `src/` — Source files for development

### Entity Types (from ha-audac)
- `number.audac_zone_X_volume` — Zone volume (0-70 dB attenuation)
- `select.audac_zone_X_source` — Zone source/routing selection
- `switch.audac_zone_X_mute` — Zone mute toggle

## Tech Stack
- Frontend: Vanilla JS Web Component (no build step needed)
- Preview: Node.js HTTP server (port 5000)
