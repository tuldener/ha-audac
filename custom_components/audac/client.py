"""TCP API clients for Audac devices."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from .const import (
    XMP_MODULE_AUTO,
    XMP_MODULE_BMP42,
    XMP_MODULE_DMP42,
    XMP_MODULE_FMP40,
    XMP_MODULE_IMP40,
    XMP_MODULE_NMP40,
    XMP_MODULE_NONE,
    normalize_xmp_module,
)

LOGGER = logging.getLogger(__name__)


class AudacApiError(Exception):
    """Raised when the Audac API returns an error."""


class _AudacBaseTcpClient:
    """Shared line-oriented TCP client."""

    def __init__(
        self,
        host: str,
        port: int,
        source_id: str,
        device_address: str,
        timeout: float = 5.0,
    ) -> None:
        self._host = host
        self._port = port
        cleaned_source = source_id.replace("|", "").replace("#", "")
        self._source_id = (cleaned_source or "ha")[:4]
        self._device_address = device_address
        self._timeout = timeout

    async def async_send_raw(self, command: str, argument: str = "0") -> str:
        """Send raw command and return reply argument."""
        _, _, _, reply_command, reply_argument, _ = await self._send(command, argument)
        if reply_command != command:
            raise AudacApiError(
                f"Unexpected raw reply command '{reply_command}' for '{command}'"
            )
        return reply_argument

    async def _command_expect(
        self,
        command: str,
        argument: str,
        reply_command: str,
    ) -> str:
        _, _, _, rep_cmd, rep_arg, _ = await self._send(
            command, argument, accept_commands={reply_command}
        )
        if rep_cmd != reply_command:
            raise AudacApiError(
                f"Unexpected reply command '{rep_cmd}' for '{command}', expected '{reply_command}'"
            )
        return rep_arg

    async def _send(
        self,
        command: str,
        argument: str,
        accept_commands: set[str] | None = None,
    ) -> tuple[str, str, str, str, str, str]:
        """Send one command over TCP and parse one reply frame."""
        import asyncio

        attempts = 3
        last_error: AudacApiError | None = None
        for attempt in range(1, attempts + 1):
            try:
                return await self._send_once(command, argument, accept_commands)
            except AudacApiError as err:
                last_error = err
                if attempt >= attempts:
                    break
                # Small backoff to reduce burst timeouts on busy MTX sockets.
                await asyncio.sleep(0.15 * attempt)

        if last_error is not None:
            raise last_error
        raise AudacApiError("TCP communication failed with unknown error")

    async def _send_once(
        self,
        command: str,
        argument: str,
        accept_commands: set[str] | None = None,
    ) -> tuple[str, str, str, str, str, str]:
        """Single TCP attempt for one command."""
        import asyncio
        import time

        payload = f"#|{self._device_address}|{self._source_id}|{command}|{argument}|U|\r\n"

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=self._timeout,
            )
            writer.write(payload.encode("ascii", errors="ignore"))
            await writer.drain()
            deadline = time.monotonic() + self._timeout
            raw = b""
            while time.monotonic() < deadline:
                timeout_left = max(0.1, deadline - time.monotonic())
                raw = await asyncio.wait_for(reader.readline(), timeout=timeout_left)
                if not raw:
                    break

                line = raw.decode("ascii", errors="ignore").strip()
                parts = line.split("|")
                if len(parts) < 6:
                    continue

                start, destination, source, rep_command, rep_argument, checksum = parts[:6]
                rep_command = rep_command.strip()
                if start != "#":
                    continue

                if accept_commands is not None and rep_command not in accept_commands:
                    # Some Audac devices can push unsolicited update frames
                    # (e.g. VU/RU/MU) before the actual response.
                    continue

                writer.close()
                await writer.wait_closed()
                return (
                    start,
                    destination,
                    source,
                    rep_command,
                    rep_argument.strip(),
                    checksum,
                )

            writer.close()
            await writer.wait_closed()
        except Exception as err:  # noqa: BLE001
            err_msg = str(err).strip() or repr(err)
            raise AudacApiError(
                f"TCP communication failed ({self._host}:{self._port}, command={command}): {err_msg}"
            ) from err

        if not raw:
            raise AudacApiError("Empty reply from device")
        line = raw.decode("ascii", errors="ignore").strip()
        if accept_commands is not None:
            raise AudacApiError(
                f"Did not receive expected reply {sorted(accept_commands)} after '{command}'. "
                f"Last frame: '{line}'"
            )
        raise AudacApiError(f"Invalid frame: '{line}'")


@dataclass(slots=True)
class MtxZoneState:
    """State for a single MTX zone."""

    volume_db: int
    source: str
    mute: bool


@dataclass(slots=True)
class MtxState:
    """Normalized MTX state."""

    firmware: str | None
    zones: dict[int, MtxZoneState]


class AudacMtxClient(_AudacBaseTcpClient):
    """Simple TCP client for MTX48/MTX88."""

    async def async_get_state(
        self,
        zone_count: int,
        previous_zones: dict[int, dict[str, Any]] | None = None,
    ) -> MtxState:
        """Fetch full state for all zones using GVALL/GRALL/GMALL + GSV."""
        vol = await self._list_with_fallback(
            command="GVALL",
            reply_command="VALL",
            zone_count=zone_count,
            previous_zones=previous_zones,
            field="volume",
            default_value="0",
        )
        routing = await self._list_with_fallback(
            command="GRALL",
            reply_command="RALL",
            zone_count=zone_count,
            previous_zones=previous_zones,
            field="source",
            default_value="0",
        )
        mute = await self._list_with_fallback(
            command="GMALL",
            reply_command="MALL",
            zone_count=zone_count,
            previous_zones=previous_zones,
            field="mute",
            default_value="0",
        )

        fw: str | None
        try:
            fw = await self._command_expect("GSV", "0", "SV")
        except AudacApiError:
            fw = None

        volumes = self._split_list(vol, "volume")
        sources = self._split_list(routing, "routing")
        mutes = self._split_list(mute, "mute")

        zones: dict[int, MtxZoneState] = {}
        for zone in range(1, zone_count + 1):
            idx = zone - 1
            try:
                vol_raw = volumes[idx]
                src_raw = sources[idx]
                mute_raw = mutes[idx]
            except IndexError as err:
                raise AudacApiError(
                    f"Device returned too few zone values (expected {zone_count})"
                ) from err

            try:
                vol_db = int(vol_raw)
            except ValueError as err:
                raise AudacApiError(f"Invalid volume value '{vol_raw}' for zone {zone}") from err

            zones[zone] = MtxZoneState(
                volume_db=vol_db,
                source=str(src_raw),
                mute=str(mute_raw) == "1",
            )

        return MtxState(firmware=fw, zones=zones)

    async def _list_with_fallback(
        self,
        command: str,
        reply_command: str,
        zone_count: int,
        previous_zones: dict[int, dict[str, Any]] | None,
        field: str,
        default_value: str,
    ) -> str:
        """Read list command with fallback to previous values on temporary failures."""
        try:
            return await self._command_expect(command, "0", reply_command)
        except AudacApiError as err:
            if not previous_zones:
                raise
            fallback_values: list[str] = []
            for zone in range(1, zone_count + 1):
                zone_state = previous_zones.get(zone, {})
                value = zone_state.get(field, default_value)
                if field == "mute":
                    fallback_values.append("1" if bool(value) else "0")
                else:
                    fallback_values.append(str(value))
            LOGGER.debug(
                "%s failed, reusing previous/default %s values for this cycle: %s",
                command,
                field,
                err,
            )
            return "^".join(fallback_values)

    async def async_set_zone_volume(self, zone: int, volume_db: int) -> None:
        if volume_db < 0 or volume_db > 70:
            raise AudacApiError("Volume argument must be in range 0..70")
        command = f"SV{zone}"
        await self._command_expect(command, str(volume_db), command)

    async def async_set_zone_source(self, zone: int, source: str) -> None:
        command = f"SR{zone}"
        await self._command_expect(command, source, command)

    async def async_set_zone_mute(self, zone: int, muted: bool) -> None:
        command = f"SM{zone:02d}"
        await self._command_expect(command, "1" if muted else "0", command)

    @staticmethod
    def _split_list(raw: str, label: str) -> list[str]:
        values = [item.strip() for item in raw.split("^") if item.strip() != ""]
        if not values:
            raise AudacApiError(f"Received empty {label} list")
        return values


@dataclass(slots=True)
class XmpSlotState:
    """State for one XMP44 slot."""

    module: str
    module_label: str | None
    gain: int | None
    player_status: str | None
    song: str | None
    station: str | None
    program: str | None
    info: str | None
    pairing: str | None


@dataclass(slots=True)
class XmpState:
    """Normalized XMP44 state."""

    slots: dict[int, XmpSlotState]


class AudacXmpClient(_AudacBaseTcpClient):
    """TCP client for XMP44 and SourceCon modules."""

    _TYPE_TO_MODULE = {
        1: XMP_MODULE_DMP42,
        4: XMP_MODULE_IMP40,
        6: XMP_MODULE_FMP40,
        8: XMP_MODULE_BMP42,
        15: XMP_MODULE_NONE,
        255: XMP_MODULE_NONE,
    }

    async def async_get_state(self, slot_count: int, configured_modules: dict[int, str]) -> XmpState:
        tps = await self._command_expect("GTPS", "0", "TPS")
        detected = self._parse_tps(tps, slot_count)

        slots: dict[int, XmpSlotState] = {}
        for slot in range(1, slot_count + 1):
            configured = normalize_xmp_module(configured_modules.get(slot, XMP_MODULE_AUTO))
            module = configured if configured != XMP_MODULE_AUTO else detected.get(slot, XMP_MODULE_NONE)
            module_label = None

            gain = await self._try_int(f"GOG{slot}", f"OG{slot}")
            status = await self._try_string(f"GPSTAT{slot}", f"PSTAT{slot}")
            song = await self._try_string(f"GSON{slot}", f"SON{slot}")
            station = await self._try_string(f"GSTN{slot}", f"STN{slot}")
            program = await self._try_string(f"GPRGN{slot}", f"PRGN{slot}")
            info = await self._try_string(f"GBMPI{slot}", f"BMPI{slot}")
            pairing = await self._try_string(f"GPAIRS{slot}", f"PAIRS{slot}")

            slots[slot] = XmpSlotState(
                module=module,
                module_label=module_label,
                gain=gain,
                player_status=status,
                song=song,
                station=station,
                program=program,
                info=info,
                pairing=pairing,
            )

        return XmpState(slots=slots)

    async def async_set_slot_gain(self, slot: int, value: int) -> None:
        await self._command_expect(f"SOG{slot}", str(value), f"SOG{slot}")

    async def async_set_bmp_pairing(self, slot: int, enabled: bool) -> None:
        await self._command_expect(f"SPAIR{slot}", "1" if enabled else "0", f"SPAIR{slot}")

    async def async_set_slot_trigger(self, slot: int, trigger_number: int, start: bool) -> str:
        if trigger_number < 1 or trigger_number > 15:
            raise AudacApiError("Trigger number must be in range 1..15")
        argument = f"{int(trigger_number)}^{1 if start else 0}"
        return await self._command_expect(f"SSTR{slot}", argument, f"SSTR{slot}")

    def _parse_tps(self, raw: str, slot_count: int) -> dict[int, str]:
        parts = [p.strip() for p in raw.split("^") if p.strip()]
        result: dict[int, str] = {}
        if not parts:
            return result

        numeric_part = parts[:slot_count]
        for idx, p in enumerate(numeric_part, start=1):
            try:
                type_id = int(p)
            except ValueError:
                type_id = 15
            result[idx] = self._TYPE_TO_MODULE.get(type_id, XMP_MODULE_NMP40)
        return result

    async def _try_string(self, command: str, reply: str) -> str | None:
        try:
            return await self._command_expect(command, "0", reply)
        except AudacApiError:
            return None

    async def _try_int(self, command: str, reply: str) -> int | None:
        value = await self._try_string(command, reply)
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            return None
