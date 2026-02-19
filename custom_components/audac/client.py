"""TCP API client for Audac MTX devices."""

from __future__ import annotations

from dataclasses import dataclass


class AudacApiError(Exception):
    """Raised when the MTX API returns an error."""


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


class AudacMtxClient:
    """Simple line-oriented TCP client for MTX48/MTX88."""

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

    async def async_get_state(self, zone_count: int) -> MtxState:
        """Fetch full state for all zones using GVALL/GRALL/GMALL + GSV."""
        vol = await self._command_expect("GVALL", "0", "VALL")
        routing = await self._command_expect("GRALL", "0", "RALL")
        mute = await self._command_expect("GMALL", "0", "MALL")

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

    async def async_set_zone_volume(self, zone: int, volume_db: int) -> None:
        """Set zone volume. Argument is 0..70 where 0 is max and 70 is min."""
        if volume_db < 0 or volume_db > 70:
            raise AudacApiError("Volume argument must be in range 0..70")
        command = f"SV{zone}"
        await self._command_expect(command, str(volume_db), command)

    async def async_set_zone_source(self, zone: int, source: str) -> None:
        """Set zone input source (0..8 as string)."""
        command = f"SR{zone}"
        await self._command_expect(command, source, command)

    async def async_set_zone_mute(self, zone: int, muted: bool) -> None:
        """Set zone mute status."""
        command = f"SM{zone:02d}"
        await self._command_expect(command, "1" if muted else "0", command)

    async def async_send_raw(self, command: str, argument: str = "0") -> str:
        """Send raw MTX command and return reply argument."""
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
        _, _, _, rep_cmd, rep_arg, _ = await self._send(command, argument)
        if rep_cmd != reply_command:
            raise AudacApiError(
                f"Unexpected reply command '{rep_cmd}' for '{command}', expected '{reply_command}'"
            )
        return rep_arg

    async def _send(
        self,
        command: str,
        argument: str,
    ) -> tuple[str, str, str, str, str, str]:
        """Send one command over TCP and parse one reply frame."""
        import asyncio

        payload = (
            f"#|{self._device_address}|{self._source_id}|{command}|{argument}|U|\r\n"
        )

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=self._timeout,
            )
            writer.write(payload.encode("ascii", errors="ignore"))
            await writer.drain()
            raw = await asyncio.wait_for(reader.readline(), timeout=self._timeout)
            writer.close()
            await writer.wait_closed()
        except Exception as err:  # noqa: BLE001
            raise AudacApiError(f"TCP communication failed: {err}") from err

        if not raw:
            raise AudacApiError("Empty reply from MTX device")

        line = raw.decode("ascii", errors="ignore").strip()
        parts = line.split("|")
        if len(parts) < 7:
            raise AudacApiError(f"Invalid MTX frame: '{line}'")

        start, destination, source, rep_command, rep_argument, checksum, stop = parts[:7]

        if start != "#":
            raise AudacApiError(f"Invalid start symbol in frame: '{line}'")

        return start, destination, source, rep_command.strip(), rep_argument.strip(), checksum

    @staticmethod
    def _split_list(raw: str, label: str) -> list[str]:
        values = [item.strip() for item in raw.split("^") if item.strip() != ""]
        if not values:
            raise AudacApiError(f"Received empty {label} list")
        return values
