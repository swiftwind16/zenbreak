from enum import Enum
from zenbreak.activity import ActivitySnapshot, InputIntensity, APP_CATEGORIES


class BodyArea(Enum):
    EYES = "eyes"
    NECK = "neck"
    WRISTS = "wrists"
    SHOULDERS = "shoulders"
    BACK = "back"
    CIRCULATION = "circulation"


# Strain points per 5-second snapshot, by activity category
STRAIN_RULES: dict[str, dict[BodyArea, float]] = {
    "terminal": {
        BodyArea.EYES: 0.15,
        BodyArea.NECK: 0.12,
        BodyArea.WRISTS: 0.10,
        BodyArea.SHOULDERS: 0.06,
        BodyArea.BACK: 0.05,
        BodyArea.CIRCULATION: 0.04,
    },
    "ide": {
        BodyArea.EYES: 0.14,
        BodyArea.NECK: 0.08,
        BodyArea.WRISTS: 0.12,
        BodyArea.SHOULDERS: 0.07,
        BodyArea.BACK: 0.05,
        BodyArea.CIRCULATION: 0.04,
    },
    "browser": {
        BodyArea.EYES: 0.12,
        BodyArea.NECK: 0.06,
        BodyArea.WRISTS: 0.05,
        BodyArea.SHOULDERS: 0.04,
        BodyArea.BACK: 0.05,
        BodyArea.CIRCULATION: 0.04,
    },
    "video_call": {
        BodyArea.EYES: 0.10,
        BodyArea.NECK: 0.12,
        BodyArea.WRISTS: 0.02,
        BodyArea.SHOULDERS: 0.08,
        BodyArea.BACK: 0.06,
        BodyArea.CIRCULATION: 0.06,
    },
    "messaging": {
        BodyArea.EYES: 0.06,
        BodyArea.NECK: 0.04,
        BodyArea.WRISTS: 0.04,
        BodyArea.SHOULDERS: 0.03,
        BodyArea.BACK: 0.03,
        BodyArea.CIRCULATION: 0.03,
    },
    "other": {
        BodyArea.EYES: 0.08,
        BodyArea.NECK: 0.05,
        BodyArea.WRISTS: 0.04,
        BodyArea.SHOULDERS: 0.04,
        BodyArea.BACK: 0.04,
        BodyArea.CIRCULATION: 0.04,
    },
}

KEYBOARD_MULTIPLIER = {
    InputIntensity.IDLE: 0.2,
    InputIntensity.LOW: 0.6,
    InputIntensity.MEDIUM: 1.0,
    InputIntensity.HEAVY: 1.5,
}

BREAK_RECOVERY = {
    BodyArea.EYES: 3.0,
    BodyArea.NECK: 1.5,
    BodyArea.WRISTS: 1.0,
    BodyArea.SHOULDERS: 1.0,
    BodyArea.BACK: 0.8,
    BodyArea.CIRCULATION: 2.0,
}


class StrainTracker:
    def __init__(self):
        self._strain: dict[BodyArea, float] = {area: 0.0 for area in BodyArea}

    def update(self, snapshot: ActivitySnapshot):
        """Update strain levels based on a new activity snapshot."""
        category = APP_CATEGORIES.get(snapshot.bundle_id, "other")
        rules = STRAIN_RULES.get(category, STRAIN_RULES["other"])
        kb_mult = KEYBOARD_MULTIPLIER.get(snapshot.keyboard_intensity, 1.0)

        for area, base_rate in rules.items():
            rate = base_rate
            if area in (BodyArea.WRISTS, BodyArea.SHOULDERS):
                rate *= kb_mult
            self._strain[area] = min(100.0, self._strain[area] + rate)

    def record_break(self, area: BodyArea, duration_sec: int):
        """Reduce strain for a body area after a break."""
        recovery = BREAK_RECOVERY.get(area, 1.0) * duration_sec / 10
        self._strain[area] = max(0.0, self._strain[area] - recovery)

    def record_full_break(self, duration_sec: int):
        """Reduce strain for ALL areas (e.g., walking break)."""
        for area in BodyArea:
            self.record_break(area, duration_sec)

    def get_strain(self) -> dict[BodyArea, float]:
        return dict(self._strain)

    def get_most_strained(self) -> BodyArea:
        return max(self._strain, key=self._strain.get)

    def get_strain_bar(self, area: BodyArea, width: int = 10) -> str:
        """Return a visual bar like ████████░░ for strain level."""
        level = self._strain[area]
        filled = int(level / 100 * width)
        return "█" * filled + "░" * (width - filled)

    def get_priority_reminder(self) -> tuple[BodyArea, float]:
        """Return the body area most urgently needing a break and its strain %."""
        area = self.get_most_strained()
        return area, self._strain[area]
