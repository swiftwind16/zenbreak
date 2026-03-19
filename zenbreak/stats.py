"""Daily stats tracking and streak management for ZenBreak."""

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

STATS_DIR = Path.home() / ".zenbreak" / "stats"
COMPLIANCE_THRESHOLD = 0.8  # 80% compliance to maintain streak


def _today_path() -> Path:
    return STATS_DIR / f"{date.today().isoformat()}.json"


def _load_day(day: date) -> dict:
    path = STATS_DIR / f"{day.isoformat()}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return _empty_day()


def _empty_day() -> dict:
    return {
        "breaks_taken": 0,
        "breaks_offered": 0,
        "breaks_by_area": {},
        "water_count": 0,
        "first_break_at": None,
        "last_break_at": None,
        "total_work_min": 0,
    }


def _save_day(data: dict, day: date | None = None):
    STATS_DIR.mkdir(parents=True, exist_ok=True)
    path = STATS_DIR / f"{(day or date.today()).isoformat()}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


class StatsTracker:
    """Tracks daily break stats and streaks."""

    def __init__(self):
        self._today = _load_day(date.today())
        self._current_date = date.today()

    def _check_date_rollover(self):
        """Reset stats if the date has changed."""
        if date.today() != self._current_date:
            _save_day(self._today, self._current_date)
            self._today = _load_day(date.today())
            self._current_date = date.today()

    def record_break_taken(self, area: str):
        """Record that a break was taken for a body area."""
        self._check_date_rollover()
        self._today["breaks_taken"] += 1
        now = datetime.now().strftime("%H:%M")
        if self._today["first_break_at"] is None:
            self._today["first_break_at"] = now
        self._today["last_break_at"] = now

        counts = self._today["breaks_by_area"]
        counts[area] = counts.get(area, 0) + 1

        _save_day(self._today)
        logger.info("[stats] Break taken: %s (total: %d)", area, self._today["breaks_taken"])

    def record_break_offered(self):
        """Record that a break reminder reached Level 4 (full overlay)."""
        self._check_date_rollover()
        self._today["breaks_offered"] += 1
        _save_day(self._today)

    def record_work_minutes(self, minutes: int):
        """Add active work minutes to today's total."""
        self._check_date_rollover()
        self._today["total_work_min"] += minutes
        _save_day(self._today)

    @property
    def breaks_taken(self) -> int:
        self._check_date_rollover()
        return self._today["breaks_taken"]

    @property
    def breaks_offered(self) -> int:
        self._check_date_rollover()
        return self._today["breaks_offered"]

    @property
    def compliance_pct(self) -> float:
        self._check_date_rollover()
        offered = self._today["breaks_offered"]
        if offered == 0:
            return 100.0
        return (self._today["breaks_taken"] / offered) * 100

    @property
    def streak_days(self) -> int:
        """Count consecutive days with >= 80% compliance."""
        streak = 0
        day = date.today() - timedelta(days=1)  # start from yesterday

        while True:
            data = _load_day(day)
            offered = data["breaks_offered"]
            if offered == 0:
                break  # no data for this day
            compliance = data["breaks_taken"] / offered
            if compliance >= COMPLIANCE_THRESHOLD:
                streak += 1
                day -= timedelta(days=1)
            else:
                break

        # Include today if compliance is good so far
        if self.breaks_offered > 0 and self.compliance_pct >= COMPLIANCE_THRESHOLD * 100:
            streak += 1

        return streak

    def get_summary(self) -> str:
        """Get a human-readable summary for the menu bar."""
        self._check_date_rollover()
        taken = self._today["breaks_taken"]
        offered = self._today["breaks_offered"]
        streak = self.streak_days

        parts = [f"Breaks: {taken}/{offered}" if offered > 0 else f"Breaks: {taken}"]

        if self._today["breaks_by_area"]:
            top_area = max(self._today["breaks_by_area"], key=self._today["breaks_by_area"].get)
            parts.append(f"Most: {top_area}")

        if streak > 0:
            parts.append(f"Streak: {streak}d")

        return " | ".join(parts)
