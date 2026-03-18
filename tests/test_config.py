import json
import os
import tempfile
from zenbreak.config import load_config


def test_load_config_returns_defaults_when_no_user_config():
    config = load_config(user_config_path="/nonexistent/path.json")
    assert config["idle_threshold_sec"] == 120
    assert config["reminders"]["eyes"]["interval_min"] == 20


def test_load_config_merges_user_overrides():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"idle_threshold_sec": 60}, f)
        f.flush()
        config = load_config(user_config_path=f.name)
    os.unlink(f.name)
    assert config["idle_threshold_sec"] == 60
    assert config["reminders"]["eyes"]["interval_min"] == 20
