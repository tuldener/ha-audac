# Audac MTX Card

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Custom Lovelace Dashboard Card zur Steuerung von **Audac MTX** Audio-Matrizen (MTX48 / MTX88). Das Design orientiert sich an [Bubble Card](https://github.com/Clooos/Bubble-Card).

Arbeitet mit der [ha-audac](https://github.com/tuldener/ha-audac) Integration zusammen.

---

## Features

- **Zonensteuerung** – Lautstärke, Mute, Quellenauswahl pro Zone
- **Bass & Höhen** – Anzeige der aktuellen Klangregelung
- **Quellenauswahl** – Übersichtliches Grid mit allen verfügbaren Eingängen
- **Automatische Erkennung** – Findet Audac Entities automatisch
- **Benutzerdefinierte Namen** – Zonen individuell benennen
- **Dark / Light Mode** – Automatisch oder manuell wählbar
- **Bubble Card Design** – Abgerundete Ecken, sanfte Gradienten, flüssige Animationen

---

## Voraussetzungen

- Home Assistant 2023.6.0 oder neuer
- [HACS](https://hacs.xyz/) (empfohlen)
- [ha-audac](https://github.com/tuldener/ha-audac) Integration (erstellt die Audac Entities)

---

## Installation

### Über HACS (empfohlen)

1. Öffne HACS in Home Assistant
2. Gehe zu **Frontend** → drei Punkte → **Benutzerdefinierte Repositories**
3. Füge `https://github.com/tuldener/Audac-Mtx-Control` hinzu und wähle Kategorie **Dashboard**
4. Suche nach **Audac MTX Card** und installiere es
5. Starte Home Assistant neu

### Manuell

1. Lade `audac-mtx-card.js` aus dem `dist/` Ordner herunter
2. Kopiere die Datei nach `config/www/audac-mtx-card.js`
3. Füge die Lovelace-Ressource hinzu:
   ```yaml
   resources:
     - url: /local/audac-mtx-card.js
       type: module
   ```
4. Starte Home Assistant neu

---

## Konfiguration

### Einfach (Automatische Erkennung)

```yaml
type: custom:audac-mtx-card
title: Audac MTX
```

Die Card erkennt automatisch alle Audac Volume-Entities und verknüpft die zugehörigen Source- und Mute-Entities.

### Manuell (Zonen einzeln konfigurieren)

```yaml
type: custom:audac-mtx-card
title: Audac MTX
zones:
  - name: Empfangsbereich
    volume: number.audac_zone_1_volume
    source: select.audac_zone_1_source
    mute: switch.audac_zone_1_mute
  - name: Konferenzraum
    volume: number.audac_zone_2_volume
    source: select.audac_zone_2_source
    mute: switch.audac_zone_2_mute
  - name: Restaurant
    volume: number.audac_zone_3_volume
    source: select.audac_zone_3_source
    mute: switch.audac_zone_3_mute
show_bass_treble: true
show_source: true
theme: auto
```

### Card-Optionen

| Option | Beschreibung | Standard |
|--------|-------------|----------|
| `title` | Titel der Karte | `Audac MTX` |
| `zones` | Liste der Zonen | `[]` (Auto-Erkennung) |
| `show_source` | Quellenauswahl anzeigen | `true` |
| `show_bass_treble` | Bass/Höhen anzeigen | `true` |
| `theme` | Design: `auto`, `dark`, `light` | `auto` |

### Zone-Konfiguration

| Option | Entity-Typ | Beschreibung |
|--------|-----------|-------------|
| `name` | – | Anzeigename der Zone |
| `volume` | `number.*` | Volume Entity aus ha-audac |
| `source` | `select.*` | Source/Routing Entity |
| `mute` | `switch.*` | Mute Entity |
| `bass` | `number.*` | Bass Entity (optional) |
| `treble` | `number.*` | Treble Entity (optional) |

---

## Entity-Zuordnung (ha-audac)

Die Card arbeitet mit den Entities, die von der [ha-audac](https://github.com/tuldener/ha-audac) Integration erstellt werden:

| Funktion | Entity-Typ | Beispiel |
|----------|-----------|---------|
| Lautstärke | `number` | `number.audac_zone_1_volume` |
| Quellenauswahl | `select` | `select.audac_zone_1_source` |
| Stummschaltung | `switch` | `switch.audac_zone_1_mute` |

---

## Lizenz

MIT License – siehe [LICENSE](LICENSE)

---

## Mitwirken

Beiträge sind willkommen! Bitte erstelle einen Fork, einen Feature-Branch und einen Pull Request.

```bash
git clone https://github.com/tuldener/Audac-Mtx-Control.git
git checkout -b feature/mein-feature
git commit -m "Beschreibung der Änderung"
git push origin feature/mein-feature
```
