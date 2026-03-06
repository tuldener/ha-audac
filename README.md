# Audac MTX

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=flat-square)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/Version-1.2.0-green.svg?style=flat-square)](https://github.com/tuldener/Audac-Mtx-Control)

Home Assistant Integration zur Steuerung von **Audac MTX** Audio-Matrizen (MTX48 / MTX88).

Kommuniziert direkt per TCP mit dem MTX-GerÃÂ¤t und liefert eine Bubble Card-inspirierte Lovelace Card mit.

---

## Features

- **Direkte TCP-Verbindung** Ã¢ÂÂ Kommuniziert direkt mit dem Audac MTX (Port 5001)
- **Media Player Entities** Ã¢ÂÂ Jede Zone wird als eigener Media Player dargestellt
- **Zonensteuerung** Ã¢ÂÂ LautstÃÂ¤rke, Mute, Quellenauswahl pro Zone
- **Bass & HÃÂ¶hen** Ã¢ÂÂ Anzeige und Steuerung der Klangregelung (ÃÂ±14 dB)
- **Quellenauswahl** Ã¢ÂÂ ÃÂbersichtliches Grid mit allen verfÃÂ¼gbaren EingÃÂ¤ngen
- **Automatische Erkennung** Ã¢ÂÂ Die Card findet alle MTX-Zonen automatisch
- **Benutzerdefinierte Namen** Ã¢ÂÂ Zonen und Quellen individuell benennen (ÃÂ¼ber Optionen)
- **Quellen-Sichtbarkeit** Ã¢ÂÂ Einzelne Quellen ausblenden (z.B. nicht belegte EingÃÂ¤nge)
- **Dark / Light Mode** Ã¢ÂÂ Automatisch oder manuell wÃÂ¤hlbar
- **Bubble Card Design** Ã¢ÂÂ Abgerundete Ecken, sanfte Gradienten, flÃÂ¼ssige Animationen
- **Card Editor** Ã¢ÂÂ Visuelle Konfiguration direkt im Lovelace-Editor
- **Auto-Reconnect** Ã¢ÂÂ Exponentieller Backoff bei Verbindungsabbruch (max. 30 s)

---

## Voraussetzungen

- Home Assistant 2023.9.0 oder neuer
- [HACS](https://hacs.xyz/) (empfohlen)
- Audac MTX48 oder MTX88, erreichbar im Netzwerk (TCP Port 5001)

---

## Installation

### ÃÂber HACS (empfohlen)

1. ÃÂffne HACS in Home Assistant
2. Gehe zu **Integrationen** Ã¢ÂÂ drei Punkte Ã¢ÂÂ **Benutzerdefinierte Repositories**
3. FÃÂ¼ge `https://github.com/tuldener/Audac-Mtx-Control` hinzu, Kategorie **Integration**
4. Suche nach **Audac MTX** und installiere es
5. Starte Home Assistant neu
6. Gehe zu **Einstellungen** Ã¢ÂÂ **GerÃÂ¤te & Dienste** Ã¢ÂÂ **Integration hinzufÃÂ¼gen** Ã¢ÂÂ **Audac MTX**

### Manuell

1. Kopiere den Ordner `custom_components/audac_mtx/` nach `config/custom_components/audac_mtx/`
2. Starte Home Assistant neu
3. Gehe zu **Einstellungen** Ã¢ÂÂ **GerÃÂ¤te & Dienste** Ã¢ÂÂ **Integration hinzufÃÂ¼gen** Ã¢ÂÂ **Audac MTX**

---

## Einrichtung

### Integration konfigurieren

Beim HinzufÃÂ¼gen der Integration werden folgende Daten abgefragt:

| Feld | Beschreibung | Standard |
|------|-------------|----------|
| Host / IP-Adresse | IP des MTX-GerÃÂ¤ts | Ã¢ÂÂ |
| Port | TCP-Port | `5001` |
| Modell | MTX48 (4 Zonen) oder MTX88 (8 Zonen) | `MTX88` |
| GerÃÂ¤tename | Anzeigename in Home Assistant | `Audac MTX` |

### Zonen- und Quellennamen anpassen

ÃÂber **Einstellungen** Ã¢ÂÂ **GerÃÂ¤te & Dienste** Ã¢ÂÂ **Audac MTX** Ã¢ÂÂ **Konfigurieren** kÃÂ¶nnen individuelle Namen und Sichtbarkeit vergeben werden:

- **Zonennamen** (z.B. "Empfangsbereich", "Konferenzraum", "Terrasse")
- **ZonenvisibilitÃÂ¤t** Ã¢ÂÂ einzelne Zonen ausblenden
- **Quellennamen** (z.B. "Spotify", "Radio", "Mikrofon BÃÂ¼hne")
- **QuellenvisibilitÃÂ¤t** Ã¢ÂÂ nicht belegte EingÃÂ¤nge ausblenden

> **Hinweis:** Die Quelle Ã¢ÂÂOff" (Routing = 0) ist standardmÃÂ¤ÃÂig ausgeblendet. Sie kann in den Optionen sichtbar geschaltet werden, um eine Zone ÃÂ¼ber die Quellenauswahl abschalten zu kÃÂ¶nnen.

---

## Lovelace Card

Die Card wird automatisch als Lovelace-Ressource registriert. Falls nicht, manuell hinzufÃÂ¼gen:

```yaml
resources:
  - url: /audac_mtx/audac-mtx-card.js
    type: module
```

### Einfach (Automatische Erkennung)

```yaml
type: custom:audac-mtx-card
title: Audac MTX
```

### Manuell (Zonen einzeln konfigurieren)

```yaml
type: custom:audac-mtx-card
title: Audio Steuerung
zones:
  - entity: media_player.audac_mtx_zone_1
    name: Empfangsbereich
  - entity: media_player.audac_mtx_zone_2
    name: Konferenzraum
  - entity: media_player.audac_mtx_zone_3
    name: Restaurant
show_bass_treble: true
show_source: true
theme: auto
```

### Card-Optionen

| Option | Beschreibung | Standard |
|--------|-------------|----------|
| `title` | Titel der Karte | `Audac MTX` |
| `zones` | Liste der Zonen (leer = Auto-Erkennung) | `[]` |
| `show_source` | Quellenauswahl anzeigen | `true` |
| `show_bass_treble` | Bass/HÃÂ¶hen anzeigen | `true` |
| `theme` | Design: `auto`, `dark`, `light` | `auto` |

### Zone-Konfiguration

| Option | Beschreibung |
|--------|-------------|
| `entity` | Entity-ID des Media Players (z.B. `media_player.audac_mtx_zone_1`) |
| `name` | Anzeigename (optional, sonst wird `friendly_name` verwendet) |

### Weitere Card-Typen

Neben der Haupt-Card gibt es spezialisierte Einzel-Cards:

| Card-Typ | Beschreibung |
|----------|-------------|
| `custom:audac-mtx-volume-card` | LautstÃÂ¤rke-Regler fÃÂ¼r eine einzelne Zone |
| `custom:audac-mtx-source-card` | Quellenauswahl fÃÂ¼r eine einzelne Zone |
| `custom:audac-mtx-bass-card` | Bass-Regler fÃÂ¼r eine einzelne Zone |
| `custom:audac-mtx-treble-card` | HÃÂ¶hen-Regler fÃÂ¼r eine einzelne Zone |

---

## Entities

Pro Zone werden folgende Entities erstellt:

| Entity-Typ | Kategorie | Beschreibung |
|------------|-----------|-------------|
| `media_player` | Ã¢ÂÂ | Haupt-Entity mit LautstÃÂ¤rke, Mute, Quelle |
| `select` | CONFIG | Quellenauswahl |
| `number` | CONFIG | LautstÃÂ¤rke 0Ã¢ÂÂ100 % |
| `switch` | CONFIG | Mute Ein/Aus |
| `sensor` | DIAGNOSTIC | Aktive Quelle (Lesezugriff) |

### EingÃÂ¤nge (Input-Nummern)

| ID | Bezeichnung | Typ |
|----|-------------|-----|
| 0 | Off | Ã¢ÂÂ |
| 1 | Mic 1 | Balanced XLR (Phantomspeisung 15 V, PrioritÃÂ¤t) |
| 2 | Mic 2 | Balanced XLR (Phantomspeisung 15 V, PrioritÃÂ¤t) |
| 3 | Line 3 | Unbalanced Stereo RCA |
| 4 | Line 4 | Unbalanced Stereo RCA |
| 5 | Line 5 | Unbalanced Stereo RCA |
| 6 | Line 6 | Unbalanced Stereo RCA |
| 7 | Wall Panel (WLI/MWX65) | RJ45 Wandeingang |
| 8 | Wall Panel (WMI) | RJ45 Wandeingang |

> **MTX48:** Nutzt EingÃÂ¤nge 1Ã¢ÂÂ6 + WandeingÃÂ¤nge 7/8. EingÃÂ¤nge 5 und 6 sind physisch nicht vorhanden (4 Line-EingÃÂ¤nge), kÃÂ¶nnen aber in den Optionen ausgeblendet werden.

### Media Player Attribute

| Attribut | Beschreibung |
|----------|-------------|
| `volume_level` | LautstÃÂ¤rke (0.0 Ã¢ÂÂ 1.0) |
| `is_volume_muted` | Stummschaltung |
| `source` | Aktive Quelle |
| `source_list` | VerfÃÂ¼gbare Quellen |
| `bass` | Bass-Einstellung (dB, -14 bis +14) |
| `treble` | HÃÂ¶hen-Einstellung (dB, -14 bis +14) |
| `volume_db` | LautstÃÂ¤rke in dB (0 bis -70) |
| `routing` | Aktive Routing-ID (0=Off, 1-8=EingÃÂ¤nge) |

---

## Custom Services

| Service | Parameter | Beschreibung |
|---------|-----------|-------------|
| `media_player.set_bass` | `bass` (0Ã¢ÂÂ14) | Bass setzen (7 = 0 dB / neutral) |
| `media_player.set_treble` | `treble` (0Ã¢ÂÂ14) | HÃÂ¶hen setzen (7 = 0 dB / neutral) |
| `media_player.routing_up` | Ã¢ÂÂ | Zum nÃÂ¤chsten Eingang wechseln (`SRU0x`) |
| `media_player.routing_down` | Ã¢ÂÂ | Zum vorherigen Eingang wechseln (`SRD0x`) |

Beispiele in einer Automation:

```yaml
# Bass auf +4 dB setzen
service: media_player.set_bass
target:
  entity_id: media_player.audac_mtx_zone_1
data:
  bass: 9

# NÃÂ¤chste Quelle wÃÂ¤hlen
service: media_player.routing_up
target:
  entity_id: media_player.audac_mtx_zone_2
```

---

## MTX-Protokoll

### Verbindung

| Port | Protokoll | Parameter |
|------|-----------|-----------|
| 5001 | TCP/IP | max. **1 gleichzeitige Verbindung** |
| RS232 | Seriell | 19200 Baud, 8N1 (8 Datenbits, kein Parity, 1 Stopbit) |
| RS485 | Seriell | gleiche Parameter wie RS232 |

> Ã¢ÂÂ Ã¯Â¸Â **Wichtig:** Das MTX unterstÃÂ¼tzt nur **eine** gleichzeitige TCP/IP-Verbindung. Verbindungen der Audac TouchÃ¢ÂÂ¢ App oder des Webinterfaces werden getrennt, sobald Home Assistant verbindet.

### Protokollformat

```
Befehl:  #|X001|web|CMD|ARG|U|\r\n
Antwort: #|web|X001|CMD|DATA|CRC|\r\n
Update:  #|ALL|X001|CMD|DATA|CRC|\r\n   (Broadcast nach SET)
```

- Zieladresse des MTX ist immer `X001`
- PrÃÂ¼fsumme: CRC-16 (kann durch `U` ersetzt werden)
- GET-Antworten entfernen den `G`-Prefix: `GVALL` Ã¢ÂÂ `VALL`, `GZI01` Ã¢ÂÂ `ZI01`

### BefehlsÃÂ¼bersicht (vollstÃÂ¤ndig)

| Befehl | Argument | Funktion |
|--------|----------|---------|
| `GZI0x` | Ã¢ÂÂ | Zone-Info: Volume, Routing, Mute, Bass, Treble (1 Abfrage) |
| `GVALL` | Ã¢ÂÂ | LautstÃÂ¤rke aller Zonen (Bulk) |
| `GRALL` | Ã¢ÂÂ | Routing aller Zonen (Bulk) |
| `GMALL` | Ã¢ÂÂ | Mute-Status aller Zonen (Bulk) |
| `GV0x` | Ã¢ÂÂ | LautstÃÂ¤rke einer Zone |
| `GR0x` | Ã¢ÂÂ | Routing einer Zone |
| `GM0x` | Ã¢ÂÂ | Mute-Status einer Zone |
| `GB0x` | Ã¢ÂÂ | Bass einer Zone |
| `GT0x` | Ã¢ÂÂ | HÃÂ¶hen einer Zone |
| `SVx` | 0Ã¢ÂÂ70 | LautstÃÂ¤rke setzen (0=max, 70=min = -70 dB) |
| `SVU0x` | 0 | LautstÃÂ¤rke +3 dB |
| `SVD0x` | 0 | LautstÃÂ¤rke -3 dB |
| `SRx` | 0Ã¢ÂÂ8 | Routing/Quelle setzen (0=Off, 1Ã¢ÂÂ8=EingÃÂ¤nge) |
| `SRU0x` | 0 | Zum nÃÂ¤chsten Eingang wechseln (deaktivierte ÃÂ¼berspringen) |
| `SRD0x` | 0 | Zum vorherigen Eingang wechseln (deaktivierte ÃÂ¼berspringen) |
| `SM0x` | 0/1 | Mute setzen (0=aus, 1=ein) |
| `SB0x` | 0Ã¢ÂÂ14 | Bass setzen (7 = 0 dB neutral) |
| `ST0x` | 0Ã¢ÂÂ14 | Treble setzen (7 = 0 dB neutral) |
| `GSV` | Ã¢ÂÂ | Firmware-Version abrufen |
| `SAVE` | Ã¢ÂÂ | Zoneneinstellungen speichern (gehen sonst beim Ausschalten verloren!) |
| `DEF` | Ã¢ÂÂ | Ã¢ÂÂ Ã¯Â¸Â Werksreset Ã¢ÂÂ alle Zonen- und GerÃÂ¤teeinstellungen zurÃÂ¼cksetzen |

Bulk-Befehle werden bevorzugt verwendet; bei Nicht-UnterstÃÂ¼tzung wird automatisch auf `GZI0x` pro Zone zurÃÂ¼ckgefallen.

---

## Troubleshooting

**Integration kann keine Verbindung herstellen**
- PrÃÂ¼fe, ob das MTX-GerÃÂ¤t per Ping erreichbar ist
- PrÃÂ¼fe, ob Port 5001 nicht durch eine Firewall blockiert wird
- Das MTX unterstÃÂ¼tzt nur eine aktive TCP-Verbindung gleichzeitig Ã¢ÂÂ andere Clients (z.B. Audac-App) trennen

**Entities zeigen veraltete Werte**
- Der Polling-Intervall betrÃÂ¤gt 10 Sekunden
- Bei Verbindungsabbruch werden die letzten bekannten Werte beibehalten
- Im HA-Log nach `audac_mtx`-Warnungen suchen

**Lovelace Card wird nicht geladen**
- Manuell unter **Einstellungen** Ã¢ÂÂ **Dashboards** Ã¢ÂÂ **Ressourcen** prÃÂ¼fen, ob `/audac_mtx/audac-mtx-card.js` eingetragen ist
- Browser-Cache leeren (Hard Reload / Strg+Shift+R)

---

## Changelog

### 1.7.2
- **Fix:** Sporadischer Ã¢ÂÂKonfigurationsfehler" beim Reload behoben
  - Verschachtelte Template-Literals im CSS-Gradient entfernt (JS Parse-Fehler)
  - `window.customCards` wird beim Laden sofort registriert
  - `connectedCallback()` ergÃÂ¤nzt fÃÂ¼r zuverlÃÂ¤ssiges Re-Render

### 1.7.1
- **Verbesserung:** LautstÃÂ¤rke-Hintergrundfarbe krÃÂ¤ftiger (38% Opacity dunkel, 26% hell)
- **Neu:** Akkordeon-Verhalten Ã¢ÂÂ nur eine Zone gleichzeitig offen

### 1.7.0
- **Verbesserung:** Zonennamen automatisch gekÃÂ¼rzt (Ã¢ÂÂAudac MTX Bar" Ã¢ÂÂ Ã¢ÂÂBar")
- **Verbesserung:** Untertitel zeigt nur noch Quelle, nicht mehr LautstÃÂ¤rke in %
- **Verbesserung:** Prozent-Badge rechts entfernt Ã¢ÂÂ LautstÃÂ¤rke als HintergrundfÃÂ¼llung
- **Verbesserung:** Mute-Badge bleibt sichtbar bei stummgeschalteten Zonen
- **Fix:** `_updateExisting()` mit try/catch Ã¢ÂÂ bei Fehler automatischer Rebuild

### 1.6.1
- **Fix:** Zonen nach Reload nicht mehr sichtbar (Timing-Bug: `hass` kam nach `_render()`)
- **Fix:** Ã¢ÂÂCustom element not found" nach Seitenreload (fehlende Versions-URL)
- **Verbesserung:** HACS-Updates aktualisieren Lovelace-Ressource automatisch

### 1.6.0
- **Fix:** Dauerhaftes Flackern der Card behoben
  - Kompletter DOM-Rebuild bei jedem HA State-Update ersetzt durch intelligentes Patching
  - Nur geÃÂ¤nderte Werte werden aktualisiert (Slider, Badge, Icon, Quelle)
  - Slider werden wÃÂ¤hrend des Ziehens nicht ÃÂ¼berschrieben
- **Neu:** Bass- und HÃÂ¶hen-Slider direkt in der Haupt-Card bedienbar

### 1.5.0
- **Fix:** Flackern beim Aufklappen einer Zone (update_entity jetzt verzÃÂ¶gert nach Animation)
- **Neu:** Bass/HÃÂ¶hen-Slider in Haupt-Card interaktiv (waren zuvor nur Anzeige)

### 1.4.0
- **Neu:** Sofortige EntitÃÂ¤ts-Aktualisierung beim Aufklappen einer Zone
- **Neu:** Akzentfarbe frei wÃÂ¤hlbar im Card-Editor (Farbpalette + Hex-Eingabe + Reset)

### 1.3.1
- **Verbesserung:** Polling-Intervall auf 15 Sekunden erhÃÂ¶ht (schont TCP-Verbindung)

### 1.3.0
- **Neu:** Befehle `SRU0x` / `SRD0x` implementiert: neue Services `routing_up` / `routing_down`
- **Neu:** Befehl `DEF` (Werksreset) in mtx_client hinzugefÃÂ¼gt
- **Neu:** Individuelle GET-Befehle `GV0x`, `GR0x`, `GM0x` in mtx_client verfÃÂ¼gbar
- **Fix:** `SVU0x` / `SVD0x` / `SAVE` / `GSV` senden jetzt korrekt Argument `0` laut Manual
- **Fix:** EingÃÂ¤nge 7 und 8 korrekt als WandeingÃÂ¤nge bezeichnet (WLI/MWX65, WMI)
- **Verbesserung:** Protokolldokumentation vervollstÃÂ¤ndigt (RS232-Parameter, vollstÃÂ¤ndige Befehlstabelle, 1-Verbindungs-Hinweis)
- **Verbesserung:** Eingangstabelle mit Hardware-Typen ergÃÂ¤nzt

### 1.2.0
- **Fix:** Doppelter `async_shutdown`-Aufruf beim Entladen der Integration behoben
- **Fix:** Quelle Ã¢ÂÂOff" (Routing 0) ist jetzt standardmÃÂ¤ÃÂig in der Quellenauswahl ausgeblendet
- **Fix:** XSS-Schutz in der Lovelace Card Ã¢ÂÂ Zonen- und Quellennamen werden korrekt escaped
- **Neu:** Debounce fÃÂ¼r LautstÃÂ¤rke-Slider (250 ms) Ã¢ÂÂ verhindert unnÃÂ¶tige Befehle beim Scrollen
- **Neu:** Exponentieller Backoff fÃÂ¼r Reconnect-Versuche (max. 30 s)
- **Verbesserung:** README mit Troubleshooting, Changelog und Service-Dokumentation ergÃÂ¤nzt

### 1.1.0
- Modell-Auswahl (MTX48 / MTX88) im Setup-Dialog
- Bulk-Abfragen (GVALL, GRALL, GMALL) mit automatischem Fallback auf Einzelabfragen
- Config-Migration v1 Ã¢ÂÂ v2
- Card Editor ÃÂ¼berarbeitet

### 1.0.0
- ErstverÃÂ¶ffentlichung


---

## Lizenz

MIT License Ã¢ÂÂ siehe [LICENSE](LICENSE)


## v1.9.2 – Lock-Reset-Fix & SCAN_INTERVAL 60 s

### Problembeschreibung (v1.9.1)
`asyncio.wait_for(_do(), COMMAND_TIMEOUT)` cancelt den inneren Task beim Timeout. Wenn der Cancel während `await lock.acquire()` passiert, kann der `asyncio.Lock`-State unter Python < 3.12 korrumpiert werden → alle folgenden Calls hängen ewig auf `await lock.acquire()` → Coordinator-Freeze.

Zusätzlich: `last_updated` in HA ändert sich nur wenn Entitätsdaten sich tatsächlich ändern. Wenn alle Zonen konstante Werte haben, erscheint das Dashboard eingefroren, obwohl der Coordinator korrekt läuft.

### Änderungen
- **`mtx_client.py`**: Nach `COMMAND_TIMEOUT` wird `self._lock.locked()` geprüft und bei positivem Befund ein neues `asyncio.Lock()` erstellt — sicheres Recovery ohne Deadlock
- **`coordinator.py`**: `SCAN_INTERVAL` von 30 s → **60 s** erhöht (das MTX-Gerät braucht ~10-45 s für alle Zonenabfragen; 60 s-Interval gibt genug Luft); vereinfachte Timeout-Behandlung ohne manuelle Backoff-Reset-Logik

## v1.9.1 â Coordinator-Backoff-Fix & StabilitÃ¤tsverbesserungen

### Problembeschreibung (v1.9.0)
Nach dem ersten erfolgreichen Update (durch `async_config_entry_first_refresh()`) liefen keine weiteren Polls mehr. Ursache: Der `asyncio.Lock` wurde wÃ¤hrend des Startup-Scans (~30â45 s fÃ¼r alle Zonen-Befehle) gehalten. Der 15-s-Scheduler feuerte wÃ¤hrenddessen, `COMMAND_TIMEOUT=8 s` lief ab â `UpdateFailed`. Nach 3 aufeinanderfolgenden Fehlern trat der HA-`DataUpdateCoordinator` in exponentiellen Backoff ein und stellte weitere Polls komplett ein.

### Ãnderungen
- **`mtx_client.py`**: `COMMAND_TIMEOUT` von 8 s â **25 s** erhÃ¶ht (mehr Spielraum beim Lock-Wait)
- **`coordinator.py`**: `SCAN_INTERVAL` von 15 s â **30 s** erhÃ¶ht (reduziert Lock-Contention); `UPDATE_TIMEOUT` auf 60 s angepasst; `last_update_success = True` nach jedem erfolgreichen Fetch gesetzt, um Backoff-Zustand explizit zurÃ¼ckzusetzen
- **Ergebnis**: Entities aktualisieren sich zuverlÃ¤ssig alle 30 s ohne Einfrieren

