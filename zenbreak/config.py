import json
import copy
from pathlib import Path

_DIR = Path(__file__).parent.parent
DEFAULT_CONFIG_PATH = _DIR / "config.default.json"
USER_CONFIG_DIR = Path.home() / ".zenbreak"
USER_CONFIG_PATH = USER_CONFIG_DIR / "config.json"


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
    with open(DEFAULT_CONFIG_PATH) as f:
        config = json.load(f)

    user_path = Path(user_config_path) if user_config_path else USER_CONFIG_PATH
    if user_path.exists():
        with open(user_path) as f:
            user_config = json.load(f)
        config = _deep_merge(config, user_config)

    return config
