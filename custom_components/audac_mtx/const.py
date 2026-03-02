"""Constants for the Audac MTX integration."""

DOMAIN = "audac_mtx"
DEFAULT_PORT = 5001
DEFAULT_SOURCE = "web"

INPUT_NAMES = {
    0: "Off",
    1: "Mic 1",
    2: "Mic 2",
    3: "Line 3",
    4: "Line 4",
    5: "Line 5",
    6: "Line 6",
    7: "WLI/MWX65",
    8: "WMI",
}

BASS_TREBLE_MAP = {
    0: -14,
    1: -12,
    2: -10,
    3: -8,
    4: -6,
    5: -4,
    6: -2,
    7: 0,
    8: 2,
    9: 4,
    10: 6,
    11: 8,
    12: 10,
    13: 12,
    14: 14,
}

MAX_ZONES = 8
VOLUME_MIN = 0
VOLUME_MAX = 70
