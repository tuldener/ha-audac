"""Constants for the Audac integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "audac"

PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
]

CONF_MODEL = "model"
CONF_SOURCE_ID = "source_id"
CONF_DEVICE_ADDRESS = "device_address"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_ZONE_COUNT = "zone_count"
CONF_ZONE_NAME_PREFIX = "zone_name_"
CONF_LINE_NAME_PREFIX = "line_name_"

DEFAULT_PORT = 5001
DEFAULT_SOURCE_ID = "ha"
DEFAULT_DEVICE_ADDRESS = "X001"
DEFAULT_SCAN_INTERVAL = 10

MODEL_MTX48 = "mtx48"
MODEL_MTX88 = "mtx88"
MODEL_TO_ZONES = {
    MODEL_MTX48: 4,
    MODEL_MTX88: 8,
}

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

ZONE_VOLUME = "volume"
ZONE_SOURCE = "source"
ZONE_MUTE = "mute"

SERVICE_SEND_RAW_COMMAND = "send_raw_command"
ATTR_COMMAND = "command"
ATTR_ARGUMENT = "argument"
ATTR_ENTRY_ID = "entry_id"

MTX_OK = "+"
