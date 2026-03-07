# Audac MTX

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=flat-square)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/Version-2.3.8-green.svg?style=flat-square)](https://github.com/tuldener/Audac-Mtx-Control/releases/latest)

Home Assistant Integration zur Steuerung von **Audac MTX** Audio-Matrizen (MTX48 / MTX88).

Kommuniziert direkt per TCP mit dem MTX-Geraet und liefert eine Bubble Card-inspirierte Lovelace Card mit.

![Audac MTX Card Preview](https://raw.githubusercontent.com/tuldener/Audac-Mtx-Control/main/docs/card-preview.png)

---

## Features

- **Direkte TCP-Verbindung** - Kommuniziert direkt mit dem Audac MTX (Port 5001)
- **Media Player Entities** - Jede Zone wird als eigener Media Player dargestellt
- **Zonensteuerung** - Lautstaerke, Mute, Quellenauswahl pro Zone
- **Zonenkopplung** - Zonen als Master/Slave koppeln (Checkboxen in den Optionen). Slave-Zonen werden automatisch synchronisiert und in der Kachel ausgeblendet
- **Bass & Hoehen** - Anzeige und Steuerung der Klangregelung (+-14 dB), ein-/ausblendbar im Card-Editor
- **Quellenauswahl** - Uebersichtliches Grid mit allen verfuegbaren Eingaengen
- **Automatische Erkennung** - Die Card findet alle MTX-Zonen automatisch
- **Benutzerdefinierte Namen** - Zonen und Quellen individuell benennen (ueber Optionen)
- **Zonen-Sichtbarkeit** - Einzelne Zonen ausblenden; Entitaeten bleiben fuer Services/Automationen erhalten
- **Quellen-Sichtbarkeit** - Einzelne Quellen ausblenden (z.B. nicht belegte Eingaenge)
- **Dark / Light Mode** - Automatisch oder manuell waehlbar
- **Akzentfarbe** - Frei waehlbare Akzentfarbe im Card-Editor
- **Akkordeon-Navigation** - Nur eine Zone gleichzeitig geoeffnet
- **Bubble Card Design** - Abgerundete Ecken, sanfte Gradienten, fluessige Animationen
- **Card Editor** - Visuelle Konfiguration direkt im Lovelace-Editor
- **Auto-Reconnect** - Exponentieller Backoff bei Verbindungsabbruch (max. 30 s)

---

## Voraussetzungen

- Home Assistant 2023.9.0 oder neuer
- [HACS](https://hacs.xyz/) (empfohlen)
- Audac MTX48 oder MTX88, erreichbar im Netzwerk (TCP Port 5001)

---

## Installation

### Ueber HACS (empfohlen)

1. Oeffne HACS in Home Assistant
2. Gehe zu **Integrationen** -> drei Punkte -> **Benutzerdefinierte Repositories**
3. Fuege `https://github.com/tuldener/Audac-Mtx-Control` hinzu, Kategorie **Integration**
4. Installiere **Audac MTX**
5. Starte Home Assistant neu

### Manuell

1. Lade den Inhalt des Ordners `custom_components/audac_mtx` in dein HA-Verzeichnis
2. Starte Home Assistant neu

---

## Konfiguration

1. **Einstellungen** -> **Geraete & Dienste** -> **Integration hinzufuegen**
2. Suche nach **Audac MTX**
3. Gib IP-Adresse, Port (Standard: 5001) und Modell (MTX48 / MTX88) ein

---

## Lovelace Card

```yaml
type: custom:audac-mtx-card
title: Audac MTX
zones: []
show_bass_treble: true
show_source: true
theme: auto
accent_color: ""
```

---

## Services

| Service | Parameter | Beschreibung |
|---|---|---|
| `media_player.volume_set` | `volume_level` (0.0-1.0) | Lautstaerke setzen |
| `media_player.volume_mute` | `is_volume_muted` | Mute setzen |
| `media_player.select_source` | `source` | Eingang waehlen |
| `audac_mtx.set_bass` | `bass` (0-14) | Bass setzen |
| `audac_mtx.set_treble` | `treble` (0-14) | Treble setzen |
| `audac_mtx.routing_up` | - | Naechsten Eingang waehlen |
| `audac_mtx.routing_down` | - | Vorherigen Eingang waehlen |

---

## Changelog

### 2.3.7
- Fix: README Bild wird jetzt korrekt angezeigt (absolute URL via raw.githubusercontent.com)
- Fix: Version-Badge auf statisch umgestellt (shields.io caching-Problem)

### 2.3.3
- Bass/Hoehen-Sichtbarkeit aus Integrations-Settings entfernt (war doppelt mit Card-Editor Toggle)
- Card: Bass/Hoehen werden nur noch ueber den Card-Editor gesteuert (`show_bass_treble`)
- Card: CARD_VERSION korrekt gebumpt fuer Browser-Cache-Busting

### 2.3.2
- Fix: Duplizierter Code in coordinator.py entfernt – die zweite `_fetch_data` Definition (ohne Sync) ueberschrieb die korrekte erste
- Fix: `async_shutdown` enthielt toten Code (versehentlich eingefuegter Duplikat-Block)
- Fix: `CARD_VERSION` wird jetzt korrekt hochgezaehlt fuer Browser-Cache-Busting

### 2.3.1
- Fix: Zonenkopplung funktionierte nicht (Sync + Ausblenden in der Kachel)
- Coordinator liest jetzt das neue `zone_X_links`-Format (Liste) statt nur das alte `zone_X_linked_to` (int)
- Kachel blendet Slave-Zonen (nicht-leeres `linked_to`) korrekt aus

### 2.3.0
- Kopplung als Checkboxen (`SelectSelector`, Multi-Select, Listenmodus) statt Dropdown
- Migration vom alten Format (`zone_X_linked_to`) auf neues Format (`zone_X_links`)

### 2.2.1
- Slave-Zonen werden bei jedem Coordinator-Poll (~60s) automatisch synchronisiert
- Toleranz bei Lautstaerke (+-2 Einheiten), exakter Abgleich fuer Mute, Quelle, Bass, Treble

### 2.2.0
- Zonenkopplung (Master/Slave) in den Integrationsoptionen
- Sofortige Spiegelung bei Befehlen an die Master-Zone

### 2.1.1
- Fix: Zonen-Dropdown im Single-Card-Editor

### 2.1.0
- Bass/Treble-Sichtbarkeit im Card-Editor (ersetzt seit 2.3.3 die Integrationsoption)

### 2.0.1
- Fix: `_async_update_zone_visibility` war nicht definiert
- Fix: Sichtbarkeit deckt jetzt alle Entitaets-Typen ab (media_player, number, switch, select, sensor)
- Neu: Zentrales `helpers.py`

### 2.0.0
- Entitaeten werden immer erstellt, Sichtbarkeit ueber Entity Registry
- `zone_visible` als State-Attribut

### 1.9.2
- Coordinator SCAN_INTERVAL 60s, Timeout-Verbesserungen

### 1.7.4
- Fix: Card laedt beim ersten Render nicht (ll-rebuild)

### 1.7.3
- Fix: `window.customCards` an Dateianfang verschoben

### 1.7.0
- Zonennamen automatisch gekuerzt
- Prozent-Badge entfernt, Lautstaerke als Hintergrundfuellung

### 1.6.0
- Flackern behoben: intelligentes DOM-Patching
- Bass/Hoehen-Slider interaktiv

### 1.3.0
- Services `routing_up` / `routing_down`
- Protokolldokumentation

### 1.0.0
- Erstveroeffentlichung

---

## Lizenz

MIT License
