"""Integration test: verify all components work together."""
from zenbreak.config import load_config
from zenbreak.activity import ActivitySnapshot
from zenbreak.strain import StrainTracker, BodyArea
from zenbreak.timers import ReminderEngine, EscalationLevel
from zenbreak.exercises import ExerciseLibrary


def test_full_flow_strain_builds_to_reminder():
    """Simulate: 40min of terminal → strain exceeds threshold → reminder fires."""
    strain = StrainTracker()
    engine = ReminderEngine(strain_threshold=50.0)
    exercises = ExerciseLibrary()

    # Simulate 40 minutes of heavy terminal use (480 snapshots at 5s intervals)
    for t in range(0, 2400, 5):
        snap = ActivitySnapshot(
            app_name="Terminal",
            bundle_id="com.apple.Terminal",
            keyboard_events=80,
            mouse_events=5,
            timestamp=float(t),
        )
        strain.update(snap)

    levels = strain.get_strain()
    max_strain = max(levels.values())
    assert max_strain >= 50.0, f"Expected strain >= 50 after 40min, got {max_strain}"

    # Engine should fire a reminder
    reminder = engine.check(levels)
    assert reminder is not None
    assert reminder.level == EscalationLevel.LEVEL_1

    # Get exercise for the area
    exercise = exercises.get_exercise(reminder.body_area)
    assert exercise is not None
    assert len(exercise.steps) > 0

    # Acknowledge and verify strain reduces
    strain.record_break(reminder.body_area, exercise.duration_sec)
    engine.acknowledge()
    new_strain = strain.get_strain()[reminder.body_area]
    assert new_strain < max_strain


def test_idle_reduces_strain():
    """Simulate: strain builds, then user goes idle, strain reduces."""
    strain = StrainTracker()

    for t in range(0, 1200, 5):
        snap = ActivitySnapshot("Terminal", "com.apple.Terminal", 80, 5, float(t))
        strain.update(snap)

    before = strain.get_strain()[BodyArea.WRISTS]
    assert before > 0

    strain.record_full_break(120)

    after = strain.get_strain()[BodyArea.WRISTS]
    assert after < before


def test_different_apps_affect_different_areas():
    """Verify that different app categories create different strain profiles."""
    # Terminal session
    terminal_strain = StrainTracker()
    for t in range(0, 600, 5):
        terminal_strain.update(
            ActivitySnapshot("Terminal", "com.apple.Terminal", 80, 5, float(t))
        )

    # Video call session
    zoom_strain = StrainTracker()
    for t in range(0, 600, 5):
        zoom_strain.update(
            ActivitySnapshot("Zoom", "us.zoom.xos", 5, 10, float(t))
        )

    # Terminal should have higher wrist strain (heavy keyboard)
    assert (
        terminal_strain.get_strain()[BodyArea.WRISTS]
        > zoom_strain.get_strain()[BodyArea.WRISTS]
    )

    # Zoom should have higher neck strain (fixed position on camera)
    assert (
        zoom_strain.get_strain()[BodyArea.NECK]
        >= zoom_strain.get_strain()[BodyArea.WRISTS]
    )
