import rumps
import time
from datetime import datetime

from zenbreak.config import load_config
from zenbreak.activity import ActivityMonitor, APP_CATEGORIES, AppSessionSummary
from zenbreak.strain import StrainTracker, BodyArea
from zenbreak.timers import ReminderEngine, EscalationLevel
from zenbreak.exercises import ExerciseLibrary
from zenbreak.overlay import OverlayManager
from zenbreak.sound import play_chime
from zenbreak.idle import get_idle_seconds


class ZenBreakApp(rumps.App):
    def __init__(self):
        super().__init__("ZenBreak", title="🧘 --m")
        self.config = load_config()

        # Core components
        self.activity = ActivityMonitor()
        self.strain = StrainTracker()
        self.engine = ReminderEngine(
            strain_threshold=50.0,
            level_2_delay=self.config["escalation"]["level_2_delay_sec"],
            level_3_delay=self.config["escalation"]["level_3_delay_sec"],
            level_4_delay=self.config["escalation"]["level_4_delay_sec"],
        )
        self.exercises = ExerciseLibrary()
        self.overlay = OverlayManager.alloc().init()

        # State
        self._idle_paused = False
        self._return_grace_until = 0.0
        self._last_level = None

        # Stats
        self.breaks_taken = 0
        self.breaks_total = 0

        # Build menu — use no-op callback so items aren't greyed out
        _noop = lambda _: None
        self.current_activity_item = rumps.MenuItem("Current: Starting up...", callback=_noop)
        self.strain_item = rumps.MenuItem("Strain: Calculating...", callback=_noop)
        self.next_break_item = rumps.MenuItem("Next break: Calculating...", callback=_noop)
        self.stats_item = rumps.MenuItem("Today: 0 breaks taken", callback=_noop)

        self.menu = [
            self.current_activity_item,
            self.strain_item,
            self.next_break_item,
            None,
            self.stats_item,
            None,
            self._build_break_menu(),
            None,
            rumps.MenuItem("Pause 15 min", callback=lambda _: self.pause(15)),
            rumps.MenuItem("Pause 30 min", callback=lambda _: self.pause(30)),
            rumps.MenuItem("Pause 1 hour", callback=lambda _: self.pause(60)),
            rumps.MenuItem("Resume", callback=lambda _: self.resume()),
        ]

    def run(self, **kwargs):
        self.activity.start()
        super().run(**kwargs)

    @rumps.timer(5)
    def tick(self, _):
        """Main loop — runs every 5 seconds."""
        now = time.time()

        if not self._in_work_hours():
            self.title = "🧘 off"
            return

        # Check idle
        idle_sec = get_idle_seconds()
        idle_threshold = self.config["idle_threshold_sec"]

        if idle_sec > idle_threshold:
            if not self._idle_paused:
                self._idle_paused = True
                self.title = "🧘 away"
                if self.overlay.is_visible:
                    self.overlay.dismiss()
            return

        # Returning from idle
        if self._idle_paused:
            self._idle_paused = False
            grace = self.config["return_grace_min"] * 60
            self._return_grace_until = now + grace
            self.strain.record_full_break(int(idle_sec * 0.5))

        # Grace period after returning
        if now < self._return_grace_until:
            remaining = int(self._return_grace_until - now)
            self.title = f"🧘 {remaining // 60}m grace"
            return

        # Feed latest activity snapshot into strain model
        if self.activity.history:
            latest = self.activity.history[-1]
            self.strain.update(latest)

        # Update menu bar info
        self._update_menu_info()

        # Check if reminder should fire
        strain_levels = self.strain.get_strain()
        reminder = self.engine.check(strain_levels)

        if reminder is None:
            self._last_level = None
            top_area, top_strain = self.strain.get_priority_reminder()
            if top_strain > 0:
                remaining_pct = max(0, 50.0 - top_strain)
                if self.activity.history and top_strain > 5:
                    rate = max(0.05, top_strain / max(1, len(self.activity.history)))
                    est_min = max(1, int(remaining_pct / rate / 12))
                    self.title = f"🧘 {est_min}m"
                else:
                    self.title = "🧘 --m"
            return

        self._handle_reminder(reminder)

    def _handle_reminder(self, reminder):
        """Act on a reminder at its current escalation level."""
        area = reminder.body_area
        exercise = self.exercises.get_exercise(area)
        reminder.exercise = exercise

        # Only act on level transitions to avoid re-triggering
        if reminder.level == self._last_level:
            return
        self._last_level = reminder.level

        if reminder.level == EscalationLevel.LEVEL_1:
            play_chime()
            self.title = f"⚠️ {area.value}!"

        elif reminder.level == EscalationLevel.LEVEL_2:
            rumps.notification(
                title=f"ZenBreak — {exercise.name}",
                subtitle=f"Your {area.value} need attention",
                message=exercise.steps[0] if exercise.steps else "Take a break",
            )
            self.title = f"⚠️ {area.value}!"

        elif reminder.level == EscalationLevel.LEVEL_3:
            if not self.overlay.is_visible:
                self.overlay.show_semi_transparent(
                    f"Your {area.value} need a break — {exercise.name}",
                    opacity=0.5,
                )
            self.title = f"🛑 {area.value}!"

        elif reminder.level == EscalationLevel.LEVEL_4:
            # Dismiss semi-transparent overlay first
            if self.overlay.is_visible:
                self.overlay.dismiss()

            self.breaks_total += 1
            summary = self._get_activity_context(area)
            self.overlay.show(
                title=exercise.name.upper(),
                steps=exercise.steps,
                context_line=summary,
                duration_sec=exercise.duration_sec,
                dismiss_countdown=self.config["escalation"]["dismiss_countdown_sec"],
                on_dismiss=self._on_break_taken,
            )
            self.title = "🛑 BREAK"

    def _on_break_taken(self):
        """Called when user clicks 'I did it'."""
        self.breaks_taken += 1
        reminder = self.engine._active_reminder
        if reminder and reminder.exercise:
            self.strain.record_break(
                reminder.body_area, reminder.exercise.duration_sec
            )
        self.engine.acknowledge()
        self._last_level = None
        self.stats_item.title = (
            f"Today: {self.breaks_taken}/{self.breaks_total} breaks taken"
        )
        self.title = "🧘 ✓"

    def _get_activity_context(self, area: BodyArea) -> str:
        """Generate a context line about current activity."""
        summary = self.activity.get_session_summary()
        if not summary:
            return f"Your {area.value} need attention."
        top = summary[0]
        duration = int(top.total_duration_seconds / 60)
        return f"{duration}min of {top.app_name} — your {area.value} need this."

    def _update_menu_info(self):
        """Update menu bar items with current status."""
        try:
            latest = self.activity.latest
            if latest:
                category = APP_CATEGORIES.get(latest.bundle_id, "other")
                self.current_activity_item.title = f"Current: {latest.app_name} ({category})"
            else:
                self.current_activity_item.title = "Current: Waiting for data..."
        except Exception:
            self.current_activity_item.title = "Current: Monitoring..."

        strain = self.strain.get_strain()
        top_areas = sorted(BodyArea, key=lambda a: strain[a], reverse=True)[:3]

        def _level_icon(pct: float) -> str:
            if pct >= 30:
                return "!!"
            elif pct >= 20:
                return "!"
            return ""

        parts = []
        for a in top_areas:
            pct = strain[a]
            icon = _level_icon(pct)
            parts.append(f"{a.value} {pct:.0f}%{icon}")
        self.strain_item.title = f"Strain: {' | '.join(parts)}"

        top_area, top_strain = self.strain.get_priority_reminder()
        if top_strain >= 30:
            self.next_break_item.title = f"Break needed: {top_area.value} ({top_strain:.0f}%)"
        elif top_strain > 0:
            remaining = 50.0 - top_strain
            self.next_break_item.title = f"Next break: {top_area.value} at 30% (now {top_strain:.0f}%)"
        else:
            self.next_break_item.title = "Next break: All good!"

    def _build_break_menu(self):
        """Build 'Take a break' submenu with all body areas."""
        menu = rumps.MenuItem("Take a break now")
        menu.add(rumps.MenuItem("Auto (most strained)", callback=lambda _: self._trigger_break_now()))
        menu.add(None)  # separator
        for area in BodyArea:
            menu.add(rumps.MenuItem(
                area.value.capitalize(),
                callback=lambda _, a=area: self._trigger_break_for(a),
            ))
        return menu

    def _trigger_break_for(self, area: BodyArea):
        """Trigger a break for a specific body area."""
        exercise = self.exercises.get_exercise(area)
        self.breaks_total += 1
        if self.overlay.is_visible:
            self.overlay.dismiss()
        self.overlay.show(
            title=exercise.name.upper(),
            steps=exercise.steps,
            context_line="",
            duration_sec=exercise.duration_sec,
            dismiss_countdown=self.config["escalation"]["dismiss_countdown_sec"],
            on_dismiss=self._on_break_taken,
        )
        self.title = "🛑 BREAK"

    def _trigger_break_now(self):
        """Manually trigger a break for the most strained body area."""
        area, _ = self.strain.get_priority_reminder()
        self._trigger_break_for(area)

    def _in_work_hours(self) -> bool:
        """Check if current time is within configured work hours."""
        now = datetime.now()
        start_h, start_m = map(int, self.config["work_hours"]["start"].split(":"))
        end_h, end_m = map(int, self.config["work_hours"]["end"].split(":"))

        current_minutes = now.hour * 60 + now.minute
        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m

        # Handle overnight schedule (e.g., 10:00 to 01:00)
        if end_minutes < start_minutes:
            return current_minutes >= start_minutes or current_minutes <= end_minutes
        return start_minutes <= current_minutes <= end_minutes

    def pause(self, minutes: int):
        self.engine.pause(minutes)
        self.title = f"🧘 ⏸ {minutes}m"
        if self.overlay.is_visible:
            self.overlay.dismiss()

    def resume(self):
        self.engine.resume()
        self.title = "🧘 --m"


def main():
    ZenBreakApp().run()


if __name__ == "__main__":
    main()
