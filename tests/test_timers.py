import time
from zenbreak.timers import ReminderEngine, EscalationLevel
from zenbreak.strain import BodyArea


def test_reminder_engine_fires_when_strain_threshold_met():
    engine = ReminderEngine(strain_threshold=50.0)
    reminder = engine.check({
        BodyArea.EYES: 60.0,
        BodyArea.NECK: 30.0,
        BodyArea.WRISTS: 20.0,
        BodyArea.SHOULDERS: 10.0,
        BodyArea.BACK: 15.0,
        BodyArea.CIRCULATION: 10.0,
    })
    assert reminder is not None
    assert reminder.body_area == BodyArea.EYES
    assert reminder.level == EscalationLevel.LEVEL_1


def test_reminder_engine_no_fire_below_threshold():
    engine = ReminderEngine(strain_threshold=50.0)
    reminder = engine.check({
        BodyArea.EYES: 30.0,
        BodyArea.NECK: 20.0,
        BodyArea.WRISTS: 20.0,
        BodyArea.SHOULDERS: 10.0,
        BodyArea.BACK: 15.0,
        BodyArea.CIRCULATION: 10.0,
    })
    assert reminder is None


def test_escalation_progresses():
    engine = ReminderEngine(strain_threshold=50.0)
    strain = {area: 10.0 for area in BodyArea}
    strain[BodyArea.EYES] = 60.0

    r1 = engine.check(strain)
    assert r1.level == EscalationLevel.LEVEL_1

    engine._active_reminder_start -= 31
    r2 = engine.check(strain)
    assert r2.level == EscalationLevel.LEVEL_2

    engine._active_reminder_start -= 30
    r3 = engine.check(strain)
    assert r3.level == EscalationLevel.LEVEL_3

    engine._active_reminder_start -= 30
    r4 = engine.check(strain)
    assert r4.level == EscalationLevel.LEVEL_4


def test_acknowledge_resets_reminder():
    engine = ReminderEngine(strain_threshold=50.0)
    strain = {area: 10.0 for area in BodyArea}
    strain[BodyArea.EYES] = 60.0

    engine.check(strain)
    engine.acknowledge()

    assert engine._active_reminder is None
    assert engine._cooldown_until > time.time()


def test_pause_suppresses_reminders():
    engine = ReminderEngine(strain_threshold=50.0)
    engine.pause(15)

    strain = {area: 100.0 for area in BodyArea}
    reminder = engine.check(strain)
    assert reminder is None
    assert engine.is_paused


def test_resume_after_pause():
    engine = ReminderEngine(strain_threshold=50.0)
    engine.pause(15)
    engine.resume()

    assert not engine.is_paused
    strain = {area: 10.0 for area in BodyArea}
    strain[BodyArea.EYES] = 60.0
    reminder = engine.check(strain)
    assert reminder is not None
