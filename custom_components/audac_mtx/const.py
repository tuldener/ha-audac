"""Constants for the Audac MTX integration."""

DOMAIN = "audac_mtx"
DEFAULT_PORT = 5001
DEFAULT_SOURCE = "web"

CARD_FILENAME = "audac-mtx-card.js"
CARD_URL_PATH = f"/audac_mtx/{CARD_FILENAME}"
CARD_VERSION = "2.4.1"
CARD_URL_VERSIONED = f"{CARD_URL_PATH}?v={CARD_VERSION}"

CONF_MODEL = "model"
MODEL_MTX48 = "mtx48"
MODEL_MTX88 = "mtx88"

MODEL_ZONES = {
    MODEL_MTX48: 4,
    MODEL_MTX88: 8,
}

MODEL_NAMES = {
    MODEL_MTX48: "MTX48",
    MODEL_MTX88: "MTX88",
}

INPUT_NAMES = {
    0: "Off",
    1: "Mic 1",
    2: "Mic 2",
    3: "Line 3",
    4: "Line 4",
    5: "Line 5",
    6: "Line 6",
    7: "Wall Panel (WLI/MWX65)",
    8: "Wall Panel (WMI)",
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

VOLUME_MIN = 0
VOLUME_MAX = 70


def get_source_names(options: dict, visible_only: bool = True) -> dict[int, str]:
    result = {}
    for input_id, default_name in INPUT_NAMES.items():
        if visible_only:
            # source_0 (Off) is hidden by default; all others visible by default
            default_visible = input_id != 0
            if not options.get(f"source_{input_id}_visible", default_visible):
                continue
        result[input_id] = options.get(f"source_{input_id}_name", default_name)
    return result
