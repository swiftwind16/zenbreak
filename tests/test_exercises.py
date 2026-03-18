from zenbreak.exercises import ExerciseLibrary, Exercise
from zenbreak.strain import BodyArea


def test_get_exercise_for_body_area():
    lib = ExerciseLibrary()
    exercise = lib.get_exercise(BodyArea.WRISTS)
    assert isinstance(exercise, Exercise)
    assert exercise.body_area == BodyArea.WRISTS
    assert len(exercise.steps) > 0
    assert exercise.duration_sec > 0


def test_get_exercise_rotates():
    lib = ExerciseLibrary()
    exercises = [lib.get_exercise(BodyArea.EYES) for _ in range(3)]
    names = {e.name for e in exercises}
    assert len(names) == 3  # 3 unique eye exercises


def test_all_body_areas_have_exercises():
    lib = ExerciseLibrary()
    for area in BodyArea:
        exercise = lib.get_exercise(area)
        assert exercise is not None
        assert exercise.body_area == area


def test_water_and_posture_reminders():
    lib = ExerciseLibrary()
    water = lib.get_water_reminder()
    assert water.name == "Drink Water"
    assert len(water.steps) > 0

    posture = lib.get_posture_reminder()
    assert posture.name == "Posture Check"
    assert len(posture.steps) > 0
