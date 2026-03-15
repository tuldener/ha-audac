# Audac for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=flat-square)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/Version-3.9.0-green.svg?style=flat-square)](https://github.com/FX6W9WZK/ha-audac/releases/latest)
[![Built with Claude AI](https://img.shields.io/badge/Built%20with-Claude%20AI-c4956b.svg?style=flat-square&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNTYgMjU2Ij48cGF0aCBkPSJNMTcyLjEgNjUuOEwxMDQuMiAxOTAuMiA4My44IDE4My4xbDY3LjktMTI0LjQgMjAuNCAxMi4xek0xNTYuNSAxNzIuMWwtNTEuOC0yMi42IDguNS0xOS41IDUxLjggMjIuNi04LjUgMTkuNXoiIGZpbGw9IiNjNDk1NmIiLz48L3N2Zz4=)](https://www.anthropic.com/claude)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=FX6W9WZK&repository=ha-audac&category=integration)

Home Assistant integration for controlling **[Audac](https://audac.eu)** audio devices:
- **MTX48 / MTX88** – Audio matrix (zone control)
- **XMP44** – Modular audio system (SourceCon modules)

Communicates directly via TCP with the devices and ships with Bubble Card-inspired Lovelace cards.

![Audac MTX Card Preview](https://raw.githubusercontent.com/FX6W9WZK/ha-audac/main/docs/card-preview.png)

---

## Features

- **Direct TCP connection** – Communicates directly with Audac devices (port 5001)
- **Media player entities** – Each zone is exposed as its own media player
- **Zone control** – Volume, mute, and source selection per zone
- **Zone coupling** – Link zones as master/slave (dropdown in options). Slave zones are automatically synchronized and hidden from the card. Linked zone names are shown next to the link icon
- **Bass & treble** – Display and control tone settings (±14 dB), toggleable in the card editor
- **Source selection** – Clean grid layout of all available inputs
- **Auto-discovery** – The card automatically finds all MTX zones
- **Custom names** – Rename zones and sources individually (via options)
- **Zone visibility** – Hide individual zones; entities remain available for services and automations
- **Source visibility** – Hide individual sources (e.g. unused inputs)
- **Multi-language** – Automatic language detection (German / English) based on HA user settings, fallback: English
- **Dark / light mode** – Automatic or manual selection
- **Accent color** – Freely configurable accent color in the card editor
- **Accordion navigation** – Only one zone expanded at a time
- **Bubble Card design** – Rounded corners, smooth gradients, fluid animations
- **Card editor** – Visual configuration directly in the Lovelace editor
- **Auto-reconnect** – Exponential backoff on connection loss (max 30 s)

### XMP44 Features

- **Automatic module detection** – Installed SourceCon modules are detected via GTPS command
- **Media player per slot** – Each installed module is exposed as its own media player
- **Supported modules** – DMP40 (DAB/FM), TMP40 (FM), IMP40 (Internet Radio), MMP40 (Media Player), FMP40 (Voice File), BMP40 (Bluetooth), NMP40 (Network Player)
- **Playback control** – Play, stop, pause, next, previous for BMP40, MMP40, NMP40
- **Song info** – Title, artist, album, duration, position for compatible modules
- **Tuner info** – Frequency, station name, signal strength, DAB/FM switching
- **Bluetooth** – Pairing status, connected devices

---

## Requirements

- Home Assistant 2023.9.0 or newer
- [HACS](https://hacs.xyz/) (recommended)
- Audac MTX48, MTX88, or XMP44 reachable on the network (TCP port 5001)

---

## Installation

### Via HACS (recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations** → three dots → **Custom repositories**
3. Add `https://github.com/FX6W9WZK/ha-audac`, category **Integration**
4. Install **Audac**
5. Restart Home Assistant

### Manual

1. Copy the contents of `custom_components/audac_mtx` into your HA config directory
2. Restart Home Assistant

---

## Configuration

1. **Settings** → **Devices & Services** → **Add Integration**
2. Search for **Audac**
3. Enter IP address, port (default: 5001), and model (MTX48 / MTX88 / XMP44)

---

## Lovelace Cards

The cards are automatically registered as Lovelace resources. If needed, they can be added manually:

**Settings** → **Dashboards** → **Resources**

| Card | URL | Type |
|---|---|---|
| MTX | `/audac_mtx/audac-mtx-card.js` | JavaScript Module |
| XMP44 | `/audac_mtx/audac-xmp44-card.js` | JavaScript Module |

### MTX Card

```yaml
type: custom:audac-mtx-card
title: Audac MTX
show_bass_treble: true
show_source: true
theme: auto
accent_color: ""
```

### XMP44 Card

```yaml
type: custom:audac-xmp44-card
title: Audac XMP44
theme: auto
accent_color: ""
```

The XMP44 card automatically detects all configured modules and shows per slot:
- Playback controls (BMP40, MMP40, NMP40)
- Station selection (IMP40 favourites)
- Trigger buttons (FMP40)
- Station search and presets (DMP40, TMP40)
- Bluetooth pairing and disconnect (BMP40)
- Song info, frequency, signal strength, output gain

---

## Services

| Service | Parameter | Description |
|---|---|---|
| `media_player.volume_set` | `volume_level` (0.0–1.0) | Set volume |
| `media_player.volume_mute` | `is_volume_muted` | Set mute |
| `media_player.select_source` | `source` | Select input |
| `audac_mtx.set_bass` | `bass` (0–14) | Set bass |
| `audac_mtx.set_treble` | `treble` (0–14) | Set treble |
| `audac_mtx.routing_up` | – | Select next input |
| `audac_mtx.routing_down` | – | Select previous input |

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full release history.

---

## License

MIT License
