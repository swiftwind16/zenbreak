"""AI-powered app classification for unknown apps."""

import json
import logging
import urllib.request
import urllib.error
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_PATH = Path.home() / ".zenbreak" / "app_cache.json"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:7b"

VALID_CATEGORIES = {"ide", "terminal", "browser", "video_call", "messaging", "design", "reading", "other"}


def _load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _save_cache(cache: dict):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)


def classify_app(app_name: str, bundle_id: str) -> str:
    """Classify an app into a category. Uses cache, then AI, then fallback."""
    # Check cache first
    cache = _load_cache()
    if bundle_id in cache:
        return cache[bundle_id]

    # Ask AI
    category = _ask_ollama(app_name)
    if category:
        cache[bundle_id] = category
        _save_cache(cache)
        logger.info("[classifier] %s (%s) → %s", app_name, bundle_id, category)
        return category

    # Fallback
    return "other"


def _ask_ollama(app_name: str) -> str | None:
    """Ask Ollama to classify an app. Returns category or None."""
    prompt = (
        f"What kind of app is '{app_name}'? "
        f"Reply with exactly one word from this list: "
        f"ide, terminal, browser, video_call, messaging, design, reading, other. "
        f"Nothing else, just the one word."
    )

    payload = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 10},
    }).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            answer = data.get("response", "").strip().lower().rstrip(".")
            if answer in VALID_CATEGORIES:
                return answer
            logger.warning("[classifier] Unexpected answer for %s: %s", app_name, answer)
    except urllib.error.URLError:
        logger.debug("[classifier] Ollama not available")
    except Exception as e:
        logger.warning("[classifier] Classification failed for %s: %s", app_name, e)

    return None
