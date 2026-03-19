"""Gamification: XP, health ranks, streaks, and daily challenges."""

import json
import logging
import random
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

GAME_PATH = Path.home() / ".zenbreak" / "game.json"

# Health ranks
RANKS = [
    (0, "Beginner"),
    (100, "Aware"),
    (300, "Active"),
    (600, "Consistent"),
    (1000, "Dedicated"),
    (1500, "Athlete"),
    (2500, "Guardian"),
    (4000, "Zen Master"),
]

# Daily challenges
CHALLENGES = [
    {"id": "five_breaks", "text": "Complete 5 breaks today", "target": 5, "type": "break_count"},
    {"id": "all_areas", "text": "Hit all 6 body areas", "target": 6, "type": "unique_areas"},
    {"id": "wrist_focus", "text": "Take 3 wrist breaks", "target": 3, "type": "area_count", "area": "wrists"},
    {"id": "early_bird", "text": "Complete a break before 10am", "target": 1, "type": "early_break"},
    {"id": "no_skips", "text": "Do every break offered", "target": 1, "type": "no_skips"},
    {"id": "video_watcher", "text": "Watch 2 demo videos", "target": 2, "type": "video_count"},
]

# XP rewards
XP_BREAK = 10
XP_BREAK_WITH_VIDEO = 15
XP_FIRST_BREAK_BONUS = 20
XP_CHALLENGE_COMPLETE = 50


def _load_game() -> dict:
    if GAME_PATH.exists():
        with open(GAME_PATH) as f:
            return json.load(f)
    return {
        "total_xp": 0,
        "streak_days": 0,
        "streak_freeze_available": True,
        "last_active_date": None,
        "today": _empty_today(),
    }


def _empty_today() -> dict:
    return {
        "date": date.today().isoformat(),
        "xp_earned": 0,
        "breaks_taken": 0,
        "areas_hit": [],
        "videos_watched": 0,
        "breaks_offered": 0,
        "breaks_skipped": 0,
        "first_break_given": False,
        "challenge_id": None,
        "challenge_complete": False,
    }


def _save_game(data: dict):
    GAME_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GAME_PATH, "w") as f:
        json.dump(data, f, indent=2)


class GameEngine:
    """Manages XP, ranks, streaks, and daily challenges."""

    def __init__(self):
        self._data = _load_game()
        self._check_new_day()

    def _check_new_day(self):
        """Handle date rollover: update streaks, pick new challenge."""
        today_str = date.today().isoformat()
        today_data = self._data.get("today", {})

        if today_data.get("date") == today_str:
            return  # same day

        # Process yesterday
        last_date = self._data.get("last_active_date")
        yesterday_breaks = today_data.get("breaks_taken", 0)

        if last_date:
            last = date.fromisoformat(last_date)
            gap = (date.today() - last).days

            if gap == 1:
                # Yesterday — check if streak continues
                if yesterday_breaks >= 3:
                    self._data["streak_days"] += 1
                    self._data["streak_freeze_available"] = True
                else:
                    self._data["streak_days"] = 0
            elif gap == 2 and self._data.get("streak_freeze_available"):
                # Missed one day — use freeze
                self._data["streak_freeze_available"] = False
                logger.info("[game] Streak freeze used")
            elif gap > 1:
                self._data["streak_days"] = 0

        # Start fresh today
        self._data["today"] = _empty_today()
        self._data["today"]["challenge_id"] = self._pick_challenge()
        self._data["last_active_date"] = today_str
        _save_game(self._data)

    def _pick_challenge(self) -> str:
        return random.choice(CHALLENGES)["id"]

    def record_break(self, area: str, watched_video: bool = False) -> int:
        """Record a completed break. Returns XP earned."""
        self._check_new_day()
        today = self._data["today"]

        # Base XP
        xp = XP_BREAK_WITH_VIDEO if watched_video else XP_BREAK

        # First break bonus
        if not today["first_break_given"]:
            xp += XP_FIRST_BREAK_BONUS
            today["first_break_given"] = True

        # Update today's data
        today["breaks_taken"] += 1
        today["xp_earned"] += xp
        if area not in today["areas_hit"]:
            today["areas_hit"].append(area)
        if watched_video:
            today["videos_watched"] += 1

        # Check challenge completion
        if not today["challenge_complete"]:
            if self._check_challenge():
                today["challenge_complete"] = True
                xp += XP_CHALLENGE_COMPLETE
                today["xp_earned"] += XP_CHALLENGE_COMPLETE
                logger.info("[game] Challenge complete! +%d XP", XP_CHALLENGE_COMPLETE)

        # Add to total
        self._data["total_xp"] += xp
        _save_game(self._data)

        logger.info("[game] Break recorded: %s, +%d XP (total: %d)", area, xp, self._data["total_xp"])
        return xp

    def record_break_offered(self):
        """Record that a break was offered (for no-skip tracking)."""
        self._check_new_day()
        self._data["today"]["breaks_offered"] += 1
        _save_game(self._data)

    def record_break_skipped(self):
        """Record that a break was skipped/escaped early."""
        self._check_new_day()
        self._data["today"]["breaks_skipped"] += 1
        _save_game(self._data)

    def _check_challenge(self) -> bool:
        """Check if today's challenge is complete."""
        today = self._data["today"]
        challenge_id = today.get("challenge_id")
        if not challenge_id:
            return False

        challenge = next((c for c in CHALLENGES if c["id"] == challenge_id), None)
        if not challenge:
            return False

        if challenge["type"] == "break_count":
            return today["breaks_taken"] >= challenge["target"]
        elif challenge["type"] == "unique_areas":
            return len(today["areas_hit"]) >= challenge["target"]
        elif challenge["type"] == "area_count":
            area = challenge["area"]
            return today["areas_hit"].count(area) >= challenge["target"]
        elif challenge["type"] == "early_break":
            return datetime.now().hour < 10 and today["breaks_taken"] > 0
        elif challenge["type"] == "no_skips":
            return today["breaks_offered"] > 0 and today["breaks_skipped"] == 0
        elif challenge["type"] == "video_count":
            return today["videos_watched"] >= challenge["target"]
        return False

    @property
    def total_xp(self) -> int:
        return self._data["total_xp"]

    @property
    def rank(self) -> tuple[int, str]:
        """Return (level_number, rank_title)."""
        xp = self._data["total_xp"]
        level = 1
        title = "Beginner"
        for i, (threshold, name) in enumerate(RANKS):
            if xp >= threshold:
                level = i + 1
                title = name
        return level, title

    @property
    def xp_to_next_rank(self) -> int | None:
        """XP needed for next rank, or None if max."""
        xp = self._data["total_xp"]
        for threshold, _ in RANKS:
            if xp < threshold:
                return threshold - xp
        return None

    @property
    def streak_days(self) -> int:
        self._check_new_day()
        # Include today if 3+ breaks taken
        streak = self._data["streak_days"]
        if self._data["today"]["breaks_taken"] >= 3:
            return streak + 1
        return streak

    @property
    def today_challenge(self) -> dict | None:
        """Return today's challenge with progress info."""
        self._check_new_day()
        today = self._data["today"]
        challenge_id = today.get("challenge_id")
        if not challenge_id:
            return None

        challenge = next((c for c in CHALLENGES if c["id"] == challenge_id), None)
        if not challenge:
            return None

        # Calculate progress
        progress = 0
        if challenge["type"] == "break_count":
            progress = today["breaks_taken"]
        elif challenge["type"] == "unique_areas":
            progress = len(today["areas_hit"])
        elif challenge["type"] == "area_count":
            progress = today["areas_hit"].count(challenge.get("area", ""))
        elif challenge["type"] == "early_break":
            progress = 1 if (datetime.now().hour < 10 and today["breaks_taken"] > 0) else 0
        elif challenge["type"] == "no_skips":
            progress = 1 if today["breaks_skipped"] == 0 else 0
        elif challenge["type"] == "video_count":
            progress = today["videos_watched"]

        return {
            "text": challenge["text"],
            "progress": min(progress, challenge["target"]),
            "target": challenge["target"],
            "complete": today["challenge_complete"],
        }

    def get_menu_summary(self) -> tuple[str, str]:
        """Return (rank_line, challenge_line) for menu display."""
        level, title = self.rank
        xp = self.total_xp
        rank_line = f"Level {level}: {title} · {xp} XP"

        challenge = self.today_challenge
        if challenge:
            if challenge["complete"]:
                challenge_line = f"Challenge complete!"
            else:
                challenge_line = f"{challenge['text']} ({challenge['progress']}/{challenge['target']})"
        else:
            challenge_line = ""

        return rank_line, challenge_line
