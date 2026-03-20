import time
from dataclasses import dataclass
from enum import Enum
from zenbreak.strain import BodyArea
from zenbreak.exercises import Exercise


class EscalationLevel(Enum):
    LEVEL_1 = 1  # menu bar flash + chime
    LEVEL_2 = 2  # notification
    LEVEL_3 = 3  # semi-transparent overlay
    LEVEL_4 = 4  # full overlay with exercise


@dataclass
class Reminder:
    body_area: BodyArea
    strain_level: float
    level: EscalationLevel
    exercise: Exercise | None = None


class ReminderEngine:
    def __init__(
        self,
        strain_threshold: float = 50.0,
        level_2_delay: int = 30,
        level_3_delay: int = 60,
        level_4_delay: int = 90,
        cooldown_sec: int = 1800,  # 30 minutes minimum between breaks
    ):
        self.strain_threshold = strain_threshold
        self.level_2_delay = level_2_delay
        self.level_3_delay = level_3_delay
        self.level_4_delay = level_4_delay
        self.cooldown_sec = cooldown_sec

        self._active_reminder: Reminder | None = None
        self._active_reminder_start: float = 0
        self._cooldown_until: float = 0
        self._paused_until: float = 0

    def check(self, strain: dict[BodyArea, float]) -> Reminder | None:
        """Check strain levels and return a reminder if one should fire."""
        now = time.time()

        if now < self._paused_until:
            return None

        if now < self._cooldown_until and self._active_reminder is None:
            return None

        if self._active_reminder is not None:
            elapsed = now - self._active_reminder_start
            if elapsed >= self.level_4_delay:
                self._active_reminder.level = EscalationLevel.LEVEL_4
            elif elapsed >= self.level_3_delay:
                self._active_reminder.level = EscalationLevel.LEVEL_3
            elif elapsed >= self.level_2_delay:
                self._active_reminder.level = EscalationLevel.LEVEL_2
            return self._active_reminder

        max_area = max(strain, key=strain.get)
        max_strain = strain[max_area]

        if max_strain < self.strain_threshold:
            return None

        self._active_reminder = Reminder(
            body_area=max_area,
            strain_level=max_strain,
            level=EscalationLevel.LEVEL_1,
        )
        self._active_reminder_start = now
        return self._active_reminder

    def acknowledge(self):
        """User acknowledged the reminder."""
        self._active_reminder = None
        self._cooldown_until = time.time() + self.cooldown_sec

    def pause(self, minutes: int):
        """Pause all reminders for N minutes."""
        self._paused_until = time.time() + minutes * 60
        self._active_reminder = None

    def resume(self):
        self._paused_until = 0

    @property
    def is_paused(self) -> bool:
        return time.time() < self._paused_until

    @property
    def has_active_reminder(self) -> bool:
        return self._active_reminder is not None
