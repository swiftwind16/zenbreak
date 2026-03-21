import json
import copy
from pathlib import Path

USER_CONFIG_DIR = Path.home() / ".zenbreak"
USER_CONFIG_PATH = USER_CONFIG_DIR / "config.json"

# Default config embedded — no file dependency for packaged app
DEFAULT_CONFIG = {
    "work_hours": {"start": "09:00", "end": "01:00"},
    "idle_threshold_sec": 300,
    "return_grace_min": 1,
    "typing_pause_sec": 5,
    "escalation": {
        "level_2_delay_sec": 30,
        "level_3_delay_sec": 60,
        "level_4_delay_sec": 90,
        "dismiss_countdown_sec": 10,
    },
    "reminders": {
        "eyes": {"interval_min": 20, "duration_sec": 20},
        "posture": {"interval_min": 30, "duration_sec": 10},
        "water": {"interval_min": 45, "duration_sec": 5},
        "wrists": {"interval_min": 40, "duration_sec": 30},
        "stretch": {"interval_min": 60, "duration_sec": 180},
        "walk": {"interval_min": 90, "duration_sec": 300},
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Merge override into base recursively. Override values win."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(user_config_path: str | None = None) -> dict:
    config = copy.deepcopy(DEFAULT_CONFIG)

    user_path = Path(user_config_path) if user_config_path else USER_CONFIG_PATH
    if user_path.exists():
        with open(user_path) as f:
            user_config = json.load(f)
        config = _deep_merge(config, user_config)

    return config
