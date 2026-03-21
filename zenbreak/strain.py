from enum import Enum
from zenbreak.activity import ActivitySnapshot, InputIntensity, get_app_category


class BodyArea(Enum):
    EYES = "eyes"
    NECK = "neck"
    WRISTS = "wrists"
    SHOULDERS = "shoulders"
    BACK = "back"
    CIRCULATION = "circulation"


# Strain points per 5-second snapshot, by activity category
STRAIN_RULES: dict[str, dict[BodyArea, float]] = {
    # Rates tuned so highest area hits 50% in ~30 min of active use.
    # Net rate = rate - decay(0.03). At 12 ticks/min:
    #   0.17 net => (0.17-0.03)*12 = 1.68%/min => 50% in ~30 min
    "terminal": {
        BodyArea.EYES: 0.17,
        BodyArea.NECK: 0.14,
        BodyArea.WRISTS: 0.12,
        BodyArea.SHOULDERS: 0.08,
        BodyArea.BACK: 0.07,
        BodyArea.CIRCULATION: 0.05,
    },
    "ide": {
        BodyArea.EYES: 0.16,
        BodyArea.NECK: 0.10,
        BodyArea.WRISTS: 0.14,
        BodyArea.SHOULDERS: 0.09,
        BodyArea.BACK: 0.07,
        BodyArea.CIRCULATION: 0.05,
    },
    "browser": {
        BodyArea.EYES: 0.14,
        BodyArea.NECK: 0.08,
        BodyArea.WRISTS: 0.06,
        BodyArea.SHOULDERS: 0.05,
        BodyArea.BACK: 0.07,
        BodyArea.CIRCULATION: 0.05,
    },
    "video_call": {
        BodyArea.EYES: 0.12,
        BodyArea.NECK: 0.14,
        BodyArea.WRISTS: 0.04,
        BodyArea.SHOULDERS: 0.10,
        BodyArea.BACK: 0.08,
        BodyArea.CIRCULATION: 0.07,
    },
    "messaging": {
        BodyArea.EYES: 0.08,
        BodyArea.NECK: 0.05,
        BodyArea.WRISTS: 0.05,
        BodyArea.SHOULDERS: 0.04,
        BodyArea.BACK: 0.04,
        BodyArea.CIRCULATION: 0.04,
    },
    "design": {  # Figma, Sketch, etc — high eye/mouse strain
        BodyArea.EYES: 0.15,
        BodyArea.NECK: 0.08,
        BodyArea.WRISTS: 0.08,
        BodyArea.SHOULDERS: 0.06,
        BodyArea.BACK: 0.06,
        BodyArea.CIRCULATION: 0.05,
    },
    "reading": {  # PDF readers, Kindle, etc
        BodyArea.EYES: 0.14,
        BodyArea.NECK: 0.07,
        BodyArea.WRISTS: 0.03,
        BodyArea.SHOULDERS: 0.04,
        BodyArea.BACK: 0.05,
        BodyArea.CIRCULATION: 0.04,
    },
    "other": {
        BodyArea.EYES: 0.10,
        BodyArea.NECK: 0.06,
        BodyArea.WRISTS: 0.05,
        BodyArea.SHOULDERS: 0.05,
        BodyArea.BACK: 0.05,
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
    def __init__(self, persist=True):
        self._strain: dict[BodyArea, float] = {area: 0.0 for area in BodyArea}
        self._health_focus: set[BodyArea] = set()
        # Always starts at 0 — strain is session-based

    def set_health_focus(self, areas: set[BodyArea]):
        """Set which body areas to prioritize (1.5x strain multiplier)."""
        self._health_focus = areas

    def update(self, snapshot: ActivitySnapshot):
        """Update strain levels based on a new activity snapshot."""
        category = get_app_category(snapshot.app_name, snapshot.bundle_id)
        rules = STRAIN_RULES.get(category, STRAIN_RULES["other"])
        kb_mult = KEYBOARD_MULTIPLIER.get(snapshot.keyboard_intensity, 1.0)

        for area, base_rate in rules.items():
            rate = base_rate
            if area in (BodyArea.WRISTS, BodyArea.SHOULDERS):
                rate *= kb_mult
            # Health focus: prioritized areas accumulate 1.5x faster
            if area in self._health_focus:
                rate *= 1.5
            # Natural decay keeps strain from maxing out permanently
            # Strain plateaus around 60-70% for the highest areas
            decay = 0.03
            new_val = self._strain[area] + rate - decay
            self._strain[area] = max(0.0, min(100.0, new_val))

    def record_break(self, area: BodyArea, duration_sec: int):
        """Reduce strain for the target area fully, and all other areas by 30%."""
        # Target area: full recovery
        self._strain[area] = 0.0
        # All other areas: reduce by 30% (you moved, shifted position)
        for other in BodyArea:
            if other != area:
                self._strain[other] *= 0.7

    def record_full_break(self, duration_sec: int):
        """Reduce strain for ALL areas (e.g., idle, walking break)."""
        for area in BodyArea:
            self._strain[area] *= 0.5

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
