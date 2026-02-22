"""Constants for the Audac integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "audac"

PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.BUTTON,
]

CONF_MODEL = "model"
CONF_SOURCE_ID = "source_id"
CONF_DEVICE_ADDRESS = "device_address"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_ZONE_COUNT = "zone_count"
CONF_ZONE_NAME_PREFIX = "zone_name_"
CONF_LINE_NAME_PREFIX = "line_name_"
CONF_SLOT_MODULE_PREFIX = "slot_module_"

DEFAULT_PORT = 5001
DEFAULT_SOURCE_ID_MTX = "mtx"
DEFAULT_SOURCE_ID_XMP = "xmp"
DEFAULT_DEVICE_ADDRESS = "X001"
DEFAULT_XMP_DEVICE_ADDRESS = "D001"
DEFAULT_SCAN_INTERVAL = 10

MODEL_MTX48 = "mtx48"
MODEL_MTX88 = "mtx88"
MODEL_XMP44 = "xmp44"

MODEL_TO_ZONES = {
    MODEL_MTX48: 4,
    MODEL_MTX88: 8,
}

XMP_SLOT_COUNT = 4

XMP_MODULE_AUTO = "auto"
XMP_MODULE_NONE = "none"
XMP_MODULE_NMP40 = "nmp40"
XMP_MODULE_IMP40 = "imp40"
XMP_MODULE_FMP40 = "fmp40"
XMP_MODULE_RMP40 = "rmp40"
XMP_MODULE_DMP42 = "dmp42"
XMP_MODULE_BMP42 = "bmp42"

XMP_MODULE_OPTIONS: dict[str, str] = {
    XMP_MODULE_AUTO: "Auto detect",
    XMP_MODULE_NONE: "No module",
    XMP_MODULE_NMP40: "NMP40 (network streaming)",
    XMP_MODULE_IMP40: "IMP40 (internet audio)",
    XMP_MODULE_FMP40: "FMP40 (voice file player)",
    XMP_MODULE_RMP40: "RMP40 (legacy alias for FMP40)",
    XMP_MODULE_DMP42: "DMP42 (DAB/FM tuner)",
    XMP_MODULE_BMP42: "BMP42 (Bluetooth)",
}


def normalize_xmp_module(value: str) -> str:
    """Normalize legacy module aliases to canonical ids."""
    module = str(value).strip().lower()
    if module == XMP_MODULE_RMP40:
        return XMP_MODULE_FMP40
    return module

DEFAULT_INPUT_LABELS = {
    "0": "None",
    "1": "Mic 1",
    "2": "Mic 2",
    "3": "Line 3",
    "4": "Line 4",
    "5": "Line 5",
    "6": "Line 6",
    "7": "WLI/MWX65",
    "8": "WMI",
}

MTX_LINE_IDS: tuple[str, ...] = ("1", "2", "3", "4", "5", "6", "7", "8")

STATE_FIRMWARE = "firmware"
STATE_ZONES = "zones"
STATE_XMP_SLOTS = "xmp_slots"

ZONE_VOLUME = "volume"
ZONE_SOURCE = "source"
ZONE_MUTE = "mute"

XMP_SLOT_MODULE = "module"
XMP_SLOT_MODULE_LABEL = "module_label"
XMP_SLOT_GAIN = "gain"
XMP_SLOT_PLAYER_STATUS = "player_status"
XMP_SLOT_SONG = "song"
XMP_SLOT_STATION = "station"
XMP_SLOT_PROGRAM = "program"
XMP_SLOT_INFO = "info"
XMP_SLOT_PAIRING = "pairing"

FMP_TRIGGER_MIN = 1
FMP_TRIGGER_MAX = 15
FMP_TRIGGER_ACTION_START = "start"
FMP_TRIGGER_ACTION_STOP = "stop"
FMP_TRIGGER_ACTION_OPTIONS: tuple[str, str] = (
    FMP_TRIGGER_ACTION_START,
    FMP_TRIGGER_ACTION_STOP,
)

SERVICE_SEND_RAW_COMMAND = "send_raw_command"
ATTR_COMMAND = "command"
ATTR_ARGUMENT = "argument"
ATTR_ENTRY_ID = "entry_id"

MTX_OK = "+"
