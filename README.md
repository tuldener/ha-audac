# ha-audac-mtx

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Custom Home Assistant Integration und Lovelace Dashboard Card zur Steuerung von **Audac MTX** Audio-Matrizen (MTX48 / MTX88). Das Design der Card orientiert sich an [Bubble Card](https://github.com/Clooos/Bubble-Card).

![Preview Dark](docs/preview-dark.png)

---

## Features

- **Zonensteuerung** – Lautstärke, Mute, Quellenauswahl pro Zone
- **Bass & Höhen** – Anzeige der aktuellen Klangregelung
- **Quellenauswahl** – Übersichtliches Grid mit allen verfügbaren Eingängen
- **Benutzerdefinierte Namen** – Zonen und Quellen individuell benennen
- **Dark / Light Mode** – Automatisch oder manuell wählbar
- **Bubble Card Design** – Abgerundete Ecken, sanfte Gradienten, flüssige Animationen
- **Mehrsprachig** – Deutsch und Englisch

---

## Voraussetzungen

- Home Assistant 2023.6.0 oder neuer
- [HACS](https://hacs.xyz/) (empfohlen für die Installation)
- Audac MTX48 oder MTX88 mit Netzwerkverbindung (TCP/IP, Port 5001)

---

## Installation

### Über HACS (empfohlen)

1. Öffne HACS in Home Assistant
2. Gehe zu **Benutzerdefinierte Repositories** (drei Punkte oben rechts)
3. Füge `https://github.com/tuldener/Audac-Mtx-Control` hinzu und wähle Kategorie **Integration**
4. Suche nach **Audac MTX** und installiere es
5. Starte Home Assistant neu

### Manuell

1. Kopiere den Ordner `custom_components/audac_mtx` in dein Home Assistant `config/custom_components/` Verzeichnis
2. Starte Home Assistant neu
3. Die Lovelace Card wird automatisch als Ressource registriert

> **Hinweis:** Falls die automatische Registrierung nicht funktioniert, füge die Ressource manuell hinzu:
> ```yaml
> resources:
>   - url: /audac_mtx/audac-mtx-card.js
>     type: module
> ```

---

## Einrichtung

### 1. Integration hinzufügen

**Einstellungen → Integrationen → + Integration hinzufügen → "Audac MTX"**

| Feld | Beschreibung | Standard |
|------|-------------|----------|
| Host / IP-Adresse | IP-Adresse des MTX-Geräts | – |
| Port | TCP-Port | `5001` |
| Anzahl der Zonen | Aktive Zonen (1–8) | `8` |
| Gerätename | Anzeigename in HA | `Audac MTX` |

### 2. Zonen & Quellen benennen

**Einstellungen → Integrationen → Audac MTX → Konfigurieren**

Hier können die Namen aller Zonen und Quellen/Eingänge individuell angepasst werden:

- **Zonennamen** – z.B. „Empfangsbereich", „Konferenzraum", „Restaurant"
- **Quellennamen** – z.B. „Spotify", „Raummikrofon", „Bluetooth"

### 3. Dashboard Card hinzufügen

Füge im Lovelace Dashboard eine neue Karte hinzu:

```yaml
type: custom:audac-mtx-card
title: Audac MTX
zones:
  - entity: media_player.audac_mtx_zone_1
    name: Empfangsbereich
  - entity: media_player.audac_mtx_zone_2
    name: Konferenzraum
  - entity: media_player.audac_mtx_zone_3
    name: Restaurant
  - entity: media_player.audac_mtx_zone_4
    name: Terrasse
show_bass_treble: true
show_source: true
theme: auto
```

#### Card-Optionen

| Option | Beschreibung | Standard |
|--------|-------------|----------|
| `title` | Titel der Karte | `Audac MTX` |
| `zones` | Liste der Zonen (Entity-ID + opt. Name) | `[]` (Auto-Erkennung) |
| `show_source` | Quellenauswahl anzeigen | `true` |
| `show_bass_treble` | Bass/Höhen anzeigen | `true` |
| `theme` | Design: `auto`, `dark`, `light` | `auto` |

> **Tipp:** Werden keine Zonen konfiguriert, erkennt die Card automatisch alle `media_player` Entities, die „audac" im Namen enthalten.

---

## Unterstützte Geräte

| Gerät | Zonen | Eingänge |
|-------|-------|----------|
| Audac MTX48 | 4 | 8 |
| Audac MTX88 | 8 | 8 |

### Eingänge (Werksbezeichnung)

| Nr. | Bezeichnung |
|-----|------------|
| 1 | Mic 1 |
| 2 | Mic 2 |
| 3 | Line 3 |
| 4 | Line 4 |
| 5 | Line 5 |
| 6 | Line 6 |
| 7 | WLI/MWX65 |
| 8 | WMI |

---

## Steuerungsfunktionen

| Funktion | Beschreibung |
|----------|-------------|
| Lautstärke | Slider 0–100% (intern 0 bis -70 dB) |
| Lautstärke +/- | Schrittweise ±3 dB |
| Mute | Stummschaltung pro Zone |
| Quellenauswahl | Eingang pro Zone wählen (0–8) |
| Bass | Anzeige -14 bis +14 dB (2 dB Schritte) |
| Höhen | Anzeige -14 bis +14 dB (2 dB Schritte) |

---

## Kommunikation

Die Integration kommuniziert mit dem MTX über **TCP/IP auf Port 5001**.

- Befehlsformat: `#|X001|web|BEFEHL|ARGUMENT|U|\r\n`
- Prüfsumme: `U` (universell akzeptiert)
- Polling-Intervall: 10 Sekunden
- Automatische Wiederverbindung bei Verbindungsverlust
- Maximal 1 gleichzeitige TCP-Verbindung zum MTX

---

## Fehlerbehebung

| Problem | Lösung |
|---------|--------|
| Verbindung fehlgeschlagen | IP-Adresse und Port prüfen. Ist das MTX-Gerät im Netzwerk erreichbar? |
| Keine Zonen sichtbar | Anzahl der Zonen in der Integrations-Konfiguration prüfen |
| Card zeigt keine Daten | Entity-IDs in der Card-Konfiguration prüfen |
| Lautstärke reagiert nicht | Prüfen ob ein anderer TCP-Client verbunden ist (MTX erlaubt nur 1 Verbindung) |

---

## Lizenz

MIT License – siehe [LICENSE](LICENSE)

---

## Mitwirken

Beiträge sind willkommen! Bitte erstelle einen Fork, einen Feature-Branch und einen Pull Request.

```bash
git clone https://github.com/tuldener/Audac-Mtx-Control.git
git checkout -b feature/mein-feature
# Änderungen vornehmen
git commit -m "Beschreibung der Änderung"
git push origin feature/mein-feature
```
