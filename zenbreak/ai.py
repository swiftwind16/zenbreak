"""AI-powered contextual message generation via local Ollama."""

import json
import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import urllib.request
import urllib.error

from zenbreak.strain import BodyArea

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:7b"
CACHE_PATH = Path.home() / ".zenbreak" / "cache" / "messages.json"

SYSTEM_PROMPT = """You are a concise ergonomic health advisor for desk workers.
Given the user's current computer activity and body strain data, generate a short,
specific break reminder message (1-2 sentences max).

Be direct and prescriptive like a physical therapist. Reference the specific activity
and body area. No fluff, no greetings, no emojis.

Examples:
- "3 hours of heavy keyboard work in Cursor — your forearm extensors are overloaded. Wrist extensions now."
- "90 minutes of terminal with intense typing — your neck has been locked forward. Chin tucks and lateral stretches."
- "You've been on video calls for 2 hours straight — your shoulders are hunched and stiff. Shoulder shrugs and rolls."
- "Long late-night session in Chrome — your eyes need real rest. Palming exercise, then look out the window."
"""


@dataclass
class ActivityContext:
    """Summary of recent activity for AI message generation."""
    top_app: str
    app_category: str
    duration_min: int
    keyboard_intensity: str
    body_area: BodyArea
    strain_pct: float
    time_of_day: str  # "morning", "afternoon", "evening", "late night"


def _build_prompt(ctx: ActivityContext) -> str:
    return (
        f"User has been in {ctx.top_app} ({ctx.app_category}) for {ctx.duration_min} minutes "
        f"with {ctx.keyboard_intensity} keyboard activity. "
        f"Their {ctx.body_area.value} strain is at {ctx.strain_pct:.0f}%. "
        f"It's currently {ctx.time_of_day}. "
        f"Generate a break reminder for {ctx.body_area.value}."
    )


def generate_message(ctx: ActivityContext) -> Optional[str]:
    """Generate a contextual break message via Ollama. Returns None on failure."""
    prompt = _build_prompt(ctx)

    payload = json.dumps({
        "model": MODEL,
        "system": SYSTEM_PROMPT,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 80,
        },
    }).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            message = data.get("response", "").strip()
            if message:
                logger.info("[ai] Generated message: %s", message[:80])
                return message
    except urllib.error.URLError as e:
        logger.warning("[ai] Ollama connection failed: %s", e)
    except Exception as e:
        logger.warning("[ai] Message generation failed: %s", e)

    return None


class AIMessageCache:
    """Caches AI-generated messages to avoid blocking the main loop."""

    def __init__(self):
        self._cache: dict[str, list[str]] = {}
        self._generating = False
        self._lock = threading.Lock()

    def get_message(self, ctx: ActivityContext) -> Optional[str]:
        """Get a cached message for this body area, or trigger generation."""
        key = ctx.body_area.value
        with self._lock:
            if key in self._cache and self._cache[key]:
                return self._cache[key].pop(0)

        # Trigger background generation if not already running
        if not self._generating:
            self._generating = True
            threading.Thread(
                target=self._generate_batch,
                args=(ctx,),
                daemon=True,
            ).start()

        return None

    def _generate_batch(self, ctx: ActivityContext):
        """Generate a few messages in the background."""
        try:
            messages = []
            for _ in range(3):
                msg = generate_message(ctx)
                if msg:
                    messages.append(msg)

            if messages:
                key = ctx.body_area.value
                with self._lock:
                    if key not in self._cache:
                        self._cache[key] = []
                    self._cache[key].extend(messages)
                logger.info("[ai] Cached %d messages for %s", len(messages), key)
        except Exception as e:
            logger.warning("[ai] Batch generation failed: %s", e)
        finally:
            self._generating = False
