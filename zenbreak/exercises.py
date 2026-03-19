from dataclasses import dataclass
from zenbreak.strain import BodyArea

# YouTube search URL helper — more reliable than hardcoded video IDs
_YT = "https://www.youtube.com/results?search_query="


def _yt_search(query: str) -> str:
    return _YT + query.replace(" ", "+")


@dataclass
class Exercise:
    name: str
    body_area: BodyArea
    steps: list[str]
    duration_sec: int
    video_url: str | None = None


_EXERCISES: dict[BodyArea, list[Exercise]] = {
    BodyArea.EYES: [
        Exercise(
            name="20-20-20 Rule",
            body_area=BodyArea.EYES,
            steps=[
                "Look at something 20 feet (6m) away",
                "Focus on it for 20 seconds",
                "Blink slowly 10 times",
            ],
            duration_sec=20,
            video_url=_yt_search("20 20 20 rule eye exercise desk"),
        ),
        Exercise(
            name="Eye Rolling",
            body_area=BodyArea.EYES,
            steps=[
                "Close your eyes gently",
                "Roll eyes clockwise — 5 circles",
                "Roll eyes counter-clockwise — 5 circles",
                "Open and blink rapidly for 5 seconds",
            ],
            duration_sec=20,
            video_url=_yt_search("eye rolling exercise for eye strain"),
        ),
        Exercise(
            name="Palming",
            body_area=BodyArea.EYES,
            steps=[
                "Rub your palms together until warm",
                "Cup palms over closed eyes (no pressure)",
                "Breathe deeply and relax for 20 seconds",
                "Slowly remove hands and open eyes",
            ],
            duration_sec=30,
            video_url=_yt_search("palming eye exercise relaxation"),
        ),
    ],
    BodyArea.NECK: [
        Exercise(
            name="Neck Rolls",
            body_area=BodyArea.NECK,
            steps=[
                "Drop chin to chest",
                "Slowly roll head to the right — hold 5 sec",
                "Continue rolling to look up — hold 5 sec",
                "Roll to the left — hold 5 sec",
                "Return to center. Repeat 3x each direction",
            ],
            duration_sec=30,
            video_url=_yt_search("neck rolls stretch desk worker"),
        ),
        Exercise(
            name="Chin Tucks",
            body_area=BodyArea.NECK,
            steps=[
                "Sit up straight, look forward",
                "Pull chin straight back (make a double chin)",
                "Hold for 5 seconds",
                "Release. Repeat 10 times",
            ],
            duration_sec=30,
            video_url=_yt_search("chin tuck exercise neck posture"),
        ),
        Exercise(
            name="Lateral Neck Stretch",
            body_area=BodyArea.NECK,
            steps=[
                "Tilt right ear toward right shoulder",
                "Gently press with right hand — hold 15 sec",
                "Return to center",
                "Repeat on left side — hold 15 sec",
            ],
            duration_sec=30,
            video_url=_yt_search("lateral neck stretch desk exercise"),
        ),
    ],
    BodyArea.WRISTS: [
        Exercise(
            name="Wrist Extensions",
            body_area=BodyArea.WRISTS,
            steps=[
                "Extend right arm, palm up",
                "With left hand, gently pull fingers back — 15 sec",
                "Switch: extend left arm, pull fingers back — 15 sec",
                "Make fists, rotate wrists 10x each direction",
            ],
            duration_sec=40,
            video_url=_yt_search("wrist extension stretch for typing"),
        ),
        Exercise(
            name="Prayer Stretch",
            body_area=BodyArea.WRISTS,
            steps=[
                "Press palms together in front of chest",
                "Slowly lower hands toward waist, keeping palms together",
                "Hold the stretch for 15 seconds",
                "Shake hands out loosely for 10 seconds",
            ],
            duration_sec=30,
            video_url=_yt_search("prayer stretch wrist carpal tunnel"),
        ),
        Exercise(
            name="Finger Spreads",
            body_area=BodyArea.WRISTS,
            steps=[
                "Spread fingers as wide as possible — hold 5 sec",
                "Make a tight fist — hold 5 sec",
                "Repeat 10 times",
                "Shake hands out loosely",
            ],
            duration_sec=30,
            video_url=_yt_search("finger spread exercise hand stretch"),
        ),
    ],
    BodyArea.SHOULDERS: [
        Exercise(
            name="Shoulder Shrugs",
            body_area=BodyArea.SHOULDERS,
            steps=[
                "Raise both shoulders toward ears — hold 5 sec",
                "Drop shoulders and relax",
                "Repeat 10 times",
                "Roll shoulders backward 10x, then forward 10x",
            ],
            duration_sec=30,
            video_url=_yt_search("shoulder shrugs desk stretch"),
        ),
        Exercise(
            name="Arm Across Chest",
            body_area=BodyArea.SHOULDERS,
            steps=[
                "Bring right arm across chest",
                "Use left hand to press it closer — hold 15 sec",
                "Switch arms — hold 15 sec",
                "Drop both arms and shake out",
            ],
            duration_sec=30,
            video_url=_yt_search("arm across chest shoulder stretch"),
        ),
    ],
    BodyArea.BACK: [
        Exercise(
            name="Seated Spinal Twist",
            body_area=BodyArea.BACK,
            steps=[
                "Sit up straight in your chair",
                "Place right hand on left knee",
                "Twist torso to the left — hold 15 sec",
                "Return to center. Repeat on right side — 15 sec",
            ],
            duration_sec=30,
            video_url=_yt_search("seated spinal twist office stretch"),
        ),
        Exercise(
            name="Standing Back Extension",
            body_area=BodyArea.BACK,
            steps=[
                "Stand up, place hands on lower back",
                "Gently lean backward, looking up",
                "Hold for 10 seconds",
                "Return to neutral. Repeat 5 times",
            ],
            duration_sec=30,
            video_url=_yt_search("standing back extension desk stretch"),
        ),
    ],
    BodyArea.CIRCULATION: [
        Exercise(
            name="Stand and Walk",
            body_area=BodyArea.CIRCULATION,
            steps=[
                "Stand up from your chair",
                "Walk around for 1-2 minutes",
                "Swing your arms as you walk",
                "Take deep breaths",
            ],
            duration_sec=120,
        ),
        Exercise(
            name="Calf Raises",
            body_area=BodyArea.CIRCULATION,
            steps=[
                "Stand behind your chair, hold the back for balance",
                "Rise up on your toes — hold 3 sec",
                "Lower back down slowly",
                "Repeat 15 times",
            ],
            duration_sec=30,
            video_url=_yt_search("calf raises exercise standing desk"),
        ),
    ],
}

WATER_REMINDER = Exercise(
    name="Drink Water",
    body_area=BodyArea.CIRCULATION,
    steps=[
        "Drink a full glass of water",
        "You've been working — stay hydrated",
    ],
    duration_sec=10,
)

POSTURE_REMINDER = Exercise(
    name="Posture Check",
    body_area=BodyArea.BACK,
    steps=[
        "Sit up straight — ears over shoulders",
        "Shoulders back and down",
        "Feet flat on the floor",
        "Screen at eye level, arm's length away",
    ],
    duration_sec=10,
    video_url=_yt_search("desk posture check ergonomic sitting"),
)


class ExerciseLibrary:
    def __init__(self):
        self._index: dict[BodyArea, int] = {area: 0 for area in BodyArea}

    def get_exercise(self, area: BodyArea) -> Exercise:
        """Get the next exercise for a body area, rotating through available ones."""
        exercises = _EXERCISES.get(area, [])
        if not exercises:
            return Exercise(
                name=f"{area.value} break",
                body_area=area,
                steps=["Take a short break and move around."],
                duration_sec=30,
            )
        idx = self._index[area] % len(exercises)
        self._index[area] = idx + 1
        return exercises[idx]

    def get_water_reminder(self) -> Exercise:
        return WATER_REMINDER

    def get_posture_reminder(self) -> Exercise:
        return POSTURE_REMINDER
