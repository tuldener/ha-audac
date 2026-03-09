"""TCP client for communicating with the Audac XMP44 modular audio system.

Inherits the shared TCP protocol from AudacClient and adds
XMP44-specific slot/module commands.

Protocol:
  Address: D001
  Slots:   4 (SourceCon module slots)

Module types (from GTPS):
  1  = DMP40/DSP40 (DAB/DAB+ & FM Tuner)
  2  = TMP40/TSP40 (FM Tuner)
  3  = MMP40/MSP40 (Media Player/Recorder)
  4  = IMP40/ISP40 (Internet Radio)
  6  = FMP40       (Voice File Interface)
  8  = BMP40       (Bluetooth Receiver)
  9  = NMP40       (Network Audio Player)
  15 = No module installed
  255 = Not supported
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from .audac_client import AudacClient, INTER_COMMAND_DELAY
from .const import DEFAULT_PORT, DEFAULT_SOURCE

_LOGGER = logging.getLogger(__name__)

# Module type IDs returned by GTPS
MODULE_DMP40 = 1   # DAB/DAB+ & FM Tuner
MODULE_TMP40 = 2   # FM Tuner
MODULE_MMP40 = 3   # Media Player/Recorder
MODULE_IMP40 = 4   # Internet Radio
MODULE_FMP40 = 6   # Voice File Interface
MODULE_BMP40 = 8   # Bluetooth Receiver
MODULE_NMP40 = 9   # Network Audio Player
MODULE_EMPTY = 15  # No module installed
MODULE_UNSUPPORTED = 255

MODULE_NAMES = {
    MODULE_DMP40: "DMP40",
    MODULE_TMP40: "TMP40",
    MODULE_MMP40: "MMP40",
    MODULE_IMP40: "IMP40",
    MODULE_FMP40: "FMP40",
    MODULE_BMP40: "BMP40",
    MODULE_NMP40: "NMP40",
    MODULE_EMPTY: None,
    MODULE_UNSUPPORTED: None,
}

MODULE_DESCRIPTIONS = {
    MODULE_DMP40: "DAB/DAB+ & FM Tuner",
    MODULE_TMP40: "FM Tuner",
    MODULE_MMP40: "Media Player/Recorder",
    MODULE_IMP40: "Internet Radio",
    MODULE_FMP40: "Voice File Interface",
    MODULE_BMP40: "Bluetooth Receiver",
    MODULE_NMP40: "Network Audio Player",
}

# Modules that support media playback commands (play/stop/pause/next/prev)
MODULES_WITH_PLAYBACK = {MODULE_MMP40, MODULE_BMP40, MODULE_NMP40}

# Modules that support song info (GPSIx)
MODULES_WITH_SONG_INFO = {MODULE_MMP40, MODULE_BMP40, MODULE_NMP40, MODULE_IMP40}

# Modules that support tuner commands (frequency, presets, program name)
MODULES_WITH_TUNER = {MODULE_DMP40, MODULE_TMP40}

# Modules that support DAB band switching
MODULES_WITH_DAB = {MODULE_DMP40}

# Hard timeout for the entire get_all_slots() call
GET_ALL_SLOTS_TIMEOUT = 45.0

# XMP44 has 4 slots
XMP44_SLOTS = 4


class XMP44Client(AudacClient):
    """Client for Audac XMP44 modular audio system."""

    DEVICE_ADDRESS = "D001"

    def __init__(self, host: str, port: int = DEFAULT_PORT, source: str = DEFAULT_SOURCE) -> None:
        super().__init__(host, port, source)
        self._module_types: dict[int, int] = {}
        self._module_names: dict[int, str | None] = {}
        self._module_versions: dict[int, str] = {}

    @property
    def module_types(self) -> dict[int, int]:
        """Return {slot: module_type_id} mapping."""
        return self._module_types

    @property
    def module_names(self) -> dict[int, str | None]:
        """Return {slot: module_name} mapping (None for empty slots)."""
        return self._module_names

    # ── Module detection ────────────────────────────────────────────

    def set_module_config(self, module_config: dict[int, int]) -> None:
        """Set module types from config options (manual configuration).

        Args:
            module_config: {slot: module_type_id} mapping from user config.
        """
        self._module_types = {}
        self._module_names = {}
        for slot, type_id in module_config.items():
            self._module_types[slot] = type_id
            self._module_names[slot] = MODULE_NAMES.get(type_id)
            _LOGGER.debug("XMP44 slot %d configured as: %s (%s)",
                          slot, MODULE_NAMES.get(type_id, "empty"), type_id)

    async def detect_modules(self) -> dict[int, int]:
        """Query GTPS to detect installed modules and their versions.

        Returns {slot: module_type_id} mapping.
        Response format: TPS|type1^type2^type3^type4^name1 version^name2 version^...
        """
        resp = await self._send_and_receive("GTPS", "0", timeout=5.0)
        data = self._get_data_field(resp)
        if not data or data == "+":
            _LOGGER.warning("XMP44: GTPS returned no data")
            return {}

        values = data.split("^")
        self._module_types = {}
        self._module_names = {}
        self._module_versions = {}

        # First 4 values are module type IDs
        for slot in range(1, XMP44_SLOTS + 1):
            idx = slot - 1
            if idx < len(values):
                try:
                    type_id = int(values[idx])
                    self._module_types[slot] = type_id
                    self._module_names[slot] = MODULE_NAMES.get(type_id)
                except (ValueError, TypeError):
                    self._module_types[slot] = MODULE_EMPTY
                    self._module_names[slot] = None
            else:
                self._module_types[slot] = MODULE_EMPTY
                self._module_names[slot] = None

        # Remaining values are "ModuleName Vx.y.z" strings
        for slot in range(1, XMP44_SLOTS + 1):
            idx = XMP44_SLOTS + (slot - 1)
            if idx < len(values):
                version_str = values[idx].strip()
                self._module_versions[slot] = version_str
                _LOGGER.debug("XMP44 slot %d: type=%d (%s) version=%s",
                              slot, self._module_types.get(slot, MODULE_EMPTY),
                              self._module_names.get(slot, "empty"), version_str)

        return self._module_types

    def get_installed_slots(self) -> list[int]:
        """Return list of slot numbers that have a module installed."""
        return [
            slot for slot, type_id in self._module_types.items()
            if type_id not in (MODULE_EMPTY, MODULE_UNSUPPORTED)
        ]

    def slot_has_playback(self, slot: int) -> bool:
        return self._module_types.get(slot, MODULE_EMPTY) in MODULES_WITH_PLAYBACK

    def slot_has_song_info(self, slot: int) -> bool:
        return self._module_types.get(slot, MODULE_EMPTY) in MODULES_WITH_SONG_INFO

    def slot_has_tuner(self, slot: int) -> bool:
        return self._module_types.get(slot, MODULE_EMPTY) in MODULES_WITH_TUNER

    def slot_has_dab(self, slot: int) -> bool:
        return self._module_types.get(slot, MODULE_EMPTY) in MODULES_WITH_DAB

    # ── General commands (all modules) ──────────────────────────────

    async def set_output_gain(self, slot: int, gain_db: int) -> bool:
        """Set output gain. Argument = abs(gain_db) + 8. Max +8dB=0, 0dB=8, -20dB=28."""
        arg = max(0, 8 - gain_db)
        resp = await self._send_and_receive(f"SOG{slot}", str(arg))
        return self._is_success(resp)

    async def get_output_gain(self, slot: int) -> int | None:
        """Get output gain. Returns gain in dB (e.g. -20, 0, +8)."""
        val = await self._get_single_value(f"GOG{slot}")
        if val is None:
            return None
        return 8 - val  # Convert from argument to dB

    # ── Playback commands (MMP40, BMP40, NMP40) ─────────────────────

    async def play(self, slot: int) -> bool:
        resp = await self._send_and_receive(f"SPPLAY{slot}", "0")
        return self._is_success(resp)

    async def stop(self, slot: int) -> bool:
        resp = await self._send_and_receive(f"SPSTOP{slot}", "0")
        return self._is_success(resp)

    async def pause(self, slot: int) -> bool:
        resp = await self._send_and_receive(f"SPPAUS{slot}", "0")
        return self._is_success(resp)

    async def next_track(self, slot: int) -> bool:
        resp = await self._send_and_receive(f"SPNEXT{slot}", "0")
        return self._is_success(resp)

    async def previous_track(self, slot: int) -> bool:
        resp = await self._send_and_receive(f"SPPREV{slot}", "0")
        return self._is_success(resp)

    async def fast_forward(self, slot: int) -> bool:
        resp = await self._send_and_receive(f"SPFFW{slot}", "0")
        return self._is_success(resp)

    async def fast_rewind(self, slot: int) -> bool:
        resp = await self._send_and_receive(f"SPFRW{slot}", "0")
        return self._is_success(resp)

    async def go_to_start(self, slot: int) -> bool:
        resp = await self._send_and_receive(f"SPGTST{slot}", "0")
        return self._is_success(resp)

    async def set_repeat(self, slot: int, mode: int) -> bool:
        """Set repeat mode: 0=one, 1=folder, 2=x times, 3=off, 4=all."""
        resp = await self._send_and_receive(f"SPRP{slot}", str(mode))
        return self._is_success(resp)

    async def set_random(self, slot: int, enabled: bool) -> bool:
        resp = await self._send_and_receive(f"SPRND{slot}", "1" if enabled else "0")
        return self._is_success(resp)

    async def get_song_info(self, slot: int) -> dict[str, Any] | None:
        """Get currently playing song info: name, artist, album, length, position."""
        resp = await self._send_and_receive(f"GPSI{slot}", "0")
        data = self._get_data_field(resp)
        if not data or data == "+":
            return None
        values = data.split("^")
        result: dict[str, Any] = {}
        if len(values) >= 1:
            result["title"] = values[0]
        if len(values) >= 2:
            result["artist"] = values[1]
        if len(values) >= 3:
            result["album"] = values[2]
        if len(values) >= 4:
            try:
                result["duration"] = int(values[3])
            except ValueError:
                pass
        if len(values) >= 5:
            try:
                result["position"] = int(values[4])
            except ValueError:
                pass
        return result

    async def get_player_status(self, slot: int) -> str:
        """Get player status: 'playing', 'paused', 'stopped', 'recording'."""
        resp = await self._send_and_receive(f"GPSTAT{slot}", "0")
        data = self._get_data_field(resp)
        if not data or data == "+":
            return "unknown"
        values = data.split("^")
        if len(values) >= 3:
            try:
                paused = int(values[0])
                playing = int(values[1])
                recording = int(values[2])
                if recording:
                    return "recording"
                if playing:
                    return "playing"
                if paused:
                    return "paused"
                return "stopped"
            except (ValueError, TypeError):
                pass
        return "unknown"

    # ── Tuner commands (DMP40, TMP40) ───────────────────────────────

    async def set_frequency(self, slot: int, freq_khz: int) -> bool:
        """Set FM frequency in integer format (e.g. 10410 for 104.10 MHz)."""
        resp = await self._send_and_receive(f"SFREQ{slot}", str(freq_khz))
        return self._is_success(resp)

    async def get_frequency(self, slot: int) -> int | None:
        """Get current tuning frequency in integer format."""
        return await self._get_single_value(f"GFREQ{slot}")

    async def search_up(self, slot: int) -> bool:
        resp = await self._send_and_receive(f"SFSUP{slot}", "0")
        return self._is_success(resp)

    async def search_down(self, slot: int) -> bool:
        resp = await self._send_and_receive(f"SFSDN{slot}", "0")
        return self._is_success(resp)

    async def select_preset(self, slot: int, preset: int) -> bool:
        """Select preset 1-10."""
        resp = await self._send_and_receive(f"SELPR{slot}", str(preset))
        return self._is_success(resp)

    async def get_presets(self, slot: int) -> str | None:
        """Get all stored presets for a slot."""
        return await self._get_string_value(f"GPRES{slot}")

    async def get_program_name(self, slot: int) -> str | None:
        return await self._get_string_value(f"GPRGN{slot}")

    async def get_program_text(self, slot: int) -> str | None:
        return await self._get_string_value(f"GPRGT{slot}")

    async def get_signal_strength(self, slot: int) -> int | None:
        return await self._get_single_value(f"GSIGS{slot}")

    async def get_stereo_state(self, slot: int) -> bool | None:
        val = await self._get_single_value(f"GSTST{slot}")
        if val is None:
            return None
        return val == 1

    async def set_stereo(self, slot: int, stereo: bool) -> bool:
        resp = await self._send_and_receive(f"SSTSE{slot}", "1" if stereo else "0")
        return self._is_success(resp)

    # ── DAB-specific commands (DMP40 only) ──────────────────────────

    async def switch_band(self, slot: int) -> bool:
        """Toggle between FM and DAB."""
        resp = await self._send_and_receive(f"SSBND{slot}", "0")
        return self._is_success(resp)

    async def get_band(self, slot: int) -> str | None:
        """Get current band: 'DAB' or 'FM'."""
        val = await self._get_single_value(f"GBND{slot}")
        if val is None:
            return None
        return "FM" if val == 1 else "DAB"

    async def get_dab_channel(self, slot: int) -> int | None:
        return await self._get_single_value(f"GCH{slot}")

    # ── Internet radio commands (IMP40) ─────────────────────────────

    async def get_song_name(self, slot: int) -> str | None:
        """Get name of currently playing track (IMP40)."""
        return await self._get_string_value(f"GSON{slot}")

    async def get_station_name(self, slot: int) -> str | None:
        """Get DB station name of currently playing station."""
        return await self._get_string_value(f"GSTN{slot}")

    async def get_favourites(self, slot: int, start_index: int = 0) -> list[dict[str, Any]]:
        """Get favourite stations starting from index.

        Returns list of {index, name, pointer} dicts.
        Response format: index^name^pointer^index^name^pointer^...
        """
        resp = await self._send_and_receive(f"GFAV{slot}", str(start_index), timeout=5.0)
        data = self._get_data_field(resp)
        if not data or data == "+":
            return []
        values = data.split("^")
        stations = []
        # Groups of 3: index, name, pointer
        for i in range(0, len(values) - 2, 3):
            try:
                name = values[i + 1].strip()
                pointer = values[i + 2].strip()
                if name and pointer:
                    stations.append({
                        "index": int(values[i]),
                        "name": name,
                        "pointer": pointer,
                    })
            except (ValueError, IndexError):
                continue
        return stations

    async def get_all_favourites(self, slot: int) -> list[dict[str, Any]]:
        """Load all favourites by paginating through the list (10 at a time)."""
        all_stations: list[dict[str, Any]] = []
        start = 0
        for _ in range(10):  # Max 100 stations (10 pages of 10)
            batch = await self.get_favourites(slot, start)
            if not batch:
                break
            all_stations.extend(batch)
            start += 10
            await asyncio.sleep(INTER_COMMAND_DELAY)
            if len(batch) < 10:
                break
        return all_stations

    async def select_station(self, slot: int, pointer: int) -> bool:
        """Select a favourite station by pointer."""
        resp = await self._send_and_receive(f"DWSEST{slot}", str(pointer))
        return self._is_success(resp)

    # ── Voice file commands (FMP40) ─────────────────────────────────

    async def trigger_start(self, slot: int, trigger_num: int) -> bool:
        resp = await self._send_and_receive(f"SSTR{slot}", f"{trigger_num}^1")
        return self._is_success(resp)

    async def trigger_stop(self, slot: int, trigger_num: int) -> bool:
        resp = await self._send_and_receive(f"SSTR{slot}", f"{trigger_num}^0")
        return self._is_success(resp)

    # ── Bluetooth commands (BMP40) ──────────────────────────────────

    async def get_bluetooth_info(self, slot: int) -> dict[str, str] | None:
        """Get BMP40 info: version, name, address."""
        resp = await self._send_and_receive(f"GBMPI{slot}", "0")
        data = self._get_data_field(resp)
        if not data or data == "+":
            return None
        values = data.split("^")
        result = {}
        if len(values) >= 1:
            result["version"] = values[0]
        if len(values) >= 2:
            result["name"] = values[1]
        if len(values) >= 3:
            result["address"] = values[2]
        return result

    async def get_pairing_state(self, slot: int) -> int | None:
        """Get pairing state: 0=success, 1=timeout, 2=failed, 3=enabled, 4=disabled."""
        return await self._get_single_value(f"GPAIRS{slot}")

    async def set_pairing(self, slot: int, enabled: bool) -> bool:
        resp = await self._send_and_receive(f"SPAIR{slot}", "1" if enabled else "0")
        return self._is_success(resp)

    async def get_paired_devices(self, slot: int) -> str | None:
        return await self._get_string_value(f"GPAIRL{slot}")

    async def get_connected_device(self, slot: int) -> str | None:
        return await self._get_string_value(f"GCONNL{slot}")

    async def disconnect_device(self, slot: int) -> bool:
        resp = await self._send_and_receive(f"SDISC{slot}", "0")
        return self._is_success(resp)

    async def forget_device(self, slot: int, device_num: int) -> bool:
        """Forget paired device 1-8."""
        resp = await self._send_and_receive(f"SFORGET{slot}", str(device_num))
        return self._is_success(resp)

    # ── Network player commands (NMP40) ─────────────────────────────

    async def get_player_name(self, slot: int) -> str | None:
        return await self._get_string_value(f"GPNAME{slot}")

    async def set_player_name(self, slot: int, name: str) -> bool:
        resp = await self._send_and_receive(f"SPNAME{slot}", name)
        return self._is_success(resp)

    async def get_player_ip(self, slot: int) -> str | None:
        return await self._get_string_value(f"GPIP{slot}")

    # ── Media recorder commands (MMP40) ─────────────────────────────

    async def get_recorder_mode(self, slot: int) -> str | None:
        """Get mode: 'player' or 'recorder'."""
        val = await self._get_single_value(f"GRRM{slot}")
        if val is None:
            return None
        return "recorder" if val == 1 else "player"

    async def set_recorder_mode(self, slot: int, recorder: bool) -> bool:
        resp = await self._send_and_receive(f"SRRM{slot}", "1" if recorder else "0")
        return self._is_success(resp)

    async def start_recording(self, slot: int) -> bool:
        resp = await self._send_and_receive(f"SRSTA{slot}", "0")
        return self._is_success(resp)

    async def stop_recording(self, slot: int) -> bool:
        resp = await self._send_and_receive(f"SRSTO{slot}", "0")
        return self._is_success(resp)

    async def pause_recording(self, slot: int) -> bool:
        resp = await self._send_and_receive(f"SRPAU{slot}", "0")
        return self._is_success(resp)

    async def cancel_recording(self, slot: int) -> bool:
        resp = await self._send_and_receive(f"SRCAN{slot}", "0")
        return self._is_success(resp)

    # ── Polling helper ──────────────────────────────────────────────

    async def get_all_slots(self) -> dict[int, dict[str, Any]]:
        """Fetch status for all installed slots.

        Returns {slot: slot_data} where slot_data contains:
        - module_type: int (module type ID)
        - module_name: str (e.g. "BMP40")
        - status: str (playing/paused/stopped/unknown)
        - output_gain: int (dB)
        - Plus module-specific data (song_info, frequency, station_name, etc.)
        """
        try:
            return await asyncio.wait_for(
                self._get_all_slots_inner(),
                timeout=GET_ALL_SLOTS_TIMEOUT,
            )
        except asyncio.TimeoutError:
            _LOGGER.warning("get_all_slots() timed out — forcing disconnect")
            self._writer = None
            self._reader = None
            self._consecutive_failures += 1
            raise ConnectionError("get_all_slots timed out") from None

    async def _get_all_slots_inner(self) -> dict[int, dict[str, Any]]:
        if not self._module_types:
            _LOGGER.warning("XMP44: No module configuration set — configure modules in integration options")
            return {}

        slots: dict[int, dict[str, Any]] = {}
        for slot in range(1, XMP44_SLOTS + 1):
            type_id = self._module_types.get(slot, MODULE_EMPTY)
            if type_id in (MODULE_EMPTY, MODULE_UNSUPPORTED):
                continue

            slot_data: dict[str, Any] = {
                "module_type": type_id,
                "module_name": MODULE_NAMES.get(type_id, f"Unknown ({type_id})"),
                "module_description": MODULE_DESCRIPTIONS.get(type_id, ""),
                "module_version": self._module_versions.get(slot, ""),
                "status": "unknown",
                "output_gain": 0,
            }

            try:
                # Output gain (all modules)
                gain = await self.get_output_gain(slot)
                if gain is not None:
                    slot_data["output_gain"] = gain
                await asyncio.sleep(INTER_COMMAND_DELAY)

                # Player status (playback modules)
                if type_id in MODULES_WITH_PLAYBACK:
                    status = await self.get_player_status(slot)
                    slot_data["status"] = status
                    await asyncio.sleep(INTER_COMMAND_DELAY)

                # Song info (playback + internet radio)
                if type_id in MODULES_WITH_SONG_INFO:
                    song_info = await self.get_song_info(slot)
                    if song_info:
                        slot_data["song_info"] = song_info
                    await asyncio.sleep(INTER_COMMAND_DELAY)

                # Tuner info
                if type_id in MODULES_WITH_TUNER:
                    freq = await self.get_frequency(slot)
                    if freq is not None:
                        slot_data["frequency"] = freq
                    await asyncio.sleep(INTER_COMMAND_DELAY)

                    prog_name = await self.get_program_name(slot)
                    if prog_name:
                        slot_data["program_name"] = prog_name
                    await asyncio.sleep(INTER_COMMAND_DELAY)

                    signal = await self.get_signal_strength(slot)
                    if signal is not None:
                        slot_data["signal_strength"] = signal
                    await asyncio.sleep(INTER_COMMAND_DELAY)

                    if type_id in MODULES_WITH_DAB:
                        band = await self.get_band(slot)
                        if band:
                            slot_data["band"] = band
                        await asyncio.sleep(INTER_COMMAND_DELAY)

                # Internet radio: station name + song name
                if type_id == MODULE_IMP40:
                    station = await self.get_station_name(slot)
                    if station:
                        slot_data["station_name"] = station
                    await asyncio.sleep(INTER_COMMAND_DELAY)

                    song_name = await self.get_song_name(slot)
                    if song_name:
                        slot_data["song_name"] = song_name
                    await asyncio.sleep(INTER_COMMAND_DELAY)

                # Bluetooth: pairing state
                if type_id == MODULE_BMP40:
                    bt_info = await self.get_bluetooth_info(slot)
                    if bt_info:
                        slot_data["bluetooth_info"] = bt_info
                    await asyncio.sleep(INTER_COMMAND_DELAY)

                    connected = await self.get_connected_device(slot)
                    if connected:
                        slot_data["connected_device"] = connected
                    await asyncio.sleep(INTER_COMMAND_DELAY)

                # NMP40: player name + IP
                if type_id == MODULE_NMP40:
                    pname = await self.get_player_name(slot)
                    if pname:
                        slot_data["player_name"] = pname
                    await asyncio.sleep(INTER_COMMAND_DELAY)

            except ConnectionError:
                raise
            except Exception as err:
                _LOGGER.warning("Error polling XMP44 slot %d: %s", slot, err)

            slots[slot] = slot_data

        return slots
