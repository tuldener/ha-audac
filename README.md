# ha-audac

Home Assistant HACS repository for Audac devices.
This is an unofficial Audac implementation and is not affiliated with or endorsed by Audac.

![Audac Unofficial Icon](assets/audac-unofficial-icon.png)

Supported devices:
- MTX48 (4 zones)
- MTX88 (8 zones)
- XMP44 (4 SourceCon slots)

## Features

- Config flow for MTX over TCP/IP (`port 5001`)
- One config entry per physical MTX device
- Per-zone entities:
  - `number` -> volume (0..70, attenuation in dB)
  - `switch` -> mute
  - `select` -> input source (0..8 mapped to labels)
- XMP44 per-slot entities:
  - `number` -> output gain argument (`SOGx` / `GOGx`)
  - `sensor` -> module, song, station, program, player status, module info
  - `switch` -> BMP42 pairing on/off (when slot module is BMP42)
- Firmware sensor
- Raw command service (`audac.send_raw_command`) for advanced commands (`SAVE`, `DEF`, `GZI01`, ...)

### XMP44 modules

Configurable per slot (`slot_module_1..4`):
- `auto` (detect via `GTPS`)
- `nmp40`
- `imp40`
- `rmp40` (FMP40 / voice file player)
- `dmp42`
- `bmp42`
- `none`

## Install (HACS)

1. HACS -> Integrations -> 3 dots -> Custom repositories
2. Add this repository URL as category `Integration`
3. Install `Audac`
4. Restart Home Assistant
5. Settings -> Devices & Services -> Add Integration -> `Audac`

## MTX protocol details

This integration uses the command framing from `MTX_Commands_Manual.pdf`:

- TCP/IP port: `5001`
- Frame format: `#|destination|source|command|argument|checksum|\r\n`
- Default device address: `X001`
- Checksum: `U` (accepted by MTX)

Polled commands:
- `GVALL` volume list
- `GRALL` routing list
- `GMALL` mute list
- `GSV` firmware

Write commands used by entities:
- `SVx` set zone volume
- `SRx` set zone routing/source
- `SM0x` set zone mute

## Service

Service: `audac.send_raw_command`

Fields:
- `entry_id` (required)
- `command` (required)
- `argument` (optional, default `0`)

## Dashboard examples

See:
- `/Users/tguldener/Documents/codex/ha-audac/examples/dashboard/tile-grid.yaml`
- `/Users/tguldener/Documents/codex/ha-audac/examples/dashboard/stacked-controls.yaml`
- `/Users/tguldener/Documents/codex/ha-audac/examples/dashboard/mini-audio-panel.yaml`
- `/Users/tguldener/Documents/codex/ha-audac/examples/dashboard/fmp-event-button.yaml`

### FMP Event Button (Dashboard only)

Custom card file:
- `/Users/tguldener/Documents/codex/ha-audac/www/audac-fmp-event-button.js`

Resource (Lovelace):

```yaml
url: /local/audac-fmp-event-button.js
type: module
```

Card example:

```yaml
type: custom:audac-fmp-event-button
xmp_entry_id: 01KJ3DBACDQQFC35G5M21QJ6SX
slot: 4
event: 1
label: Klingel Wohnzimmer
style_mode: default
```

Options:
- `xmp_entry_id` (required): Audac config entry id (XMP device)
- `slot` (required): `1..4`
- `event` (required): `1..50`
- `label` (optional): button title
- `style_mode` (optional): `default` or `bubble`

The card sends:
- Play -> `SSTRx` with argument `event^1`
- Stop -> `SSTRx` with argument `event^0`

### Optional Bubble-style

If Bubble Card is installed, you can enable an optional bubble-like style in the custom tile:

```yaml
type: custom:audac-device-tile
name: Audac Zone 1
style_mode: bubble
mute_entity: switch.audac_zone_1_mute
volume_entity: number.audac_zone_1_volume_db_attenuation
source_entity: select.audac_zone_1_source
```

`style_mode` supports:
- `default` (standard)
- `bubble` (bubble-like visual style)
