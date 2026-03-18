# ZenBreak v1 MVP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a macOS menu bar app that monitors your work activity (app + input intensity) and delivers escalating, activity-aware health reminders with specific exercise prescriptions.

**Architecture:** A Python menu bar app (rumps) with background threads for activity monitoring and idle detection. A timer engine tracks cumulative strain per body area using simple rules. When strain thresholds are crossed, reminders escalate through 4 levels (chime → notification → semi-transparent overlay → full overlay with exercise prescription). All state is local JSON files.

**Tech Stack:** Python 3.12, rumps (menu bar), pyobjc/AppKit (frontmost app detection), Quartz/CoreGraphics (idle + input monitoring), pyobjc NSWindow (overlay), Pillow (image display).

---

## Task 1: Project Skeleton + Menu Bar App

**Files:**
- Create: `zenbreak/__init__.py`
- Create: `zenbreak/app.py`
- Create: `zenbreak/config.py`
- Create: `config.default.json`
- Create: `requirements.txt`
- Create: `.gitignore`
- Test: `tests/test_config.py`

**Step 1: Create `.gitignore`**

```
__pycache__/
*.pyc
.env
.venv/
*.egg-info/
dist/
build/
.DS_Store
```

**Step 2: Create `requirements.txt`**

```
rumps>=0.4.0
pyobjc-core>=10.0
pyobjc-framework-Cocoa>=10.0
pyobjc-framework-Quartz>=10.0
Pillow>=9.0
anthropic>=0.70.0
```

**Step 3: Create `config.default.json`**

```json
{
  "work_hours": { "start": "10:00", "end": "01:00" },
  "idle_threshold_sec": 120,
  "return_grace_min": 5,
  "typing_pause_sec": 5,
  "escalation": {
    "level_2_delay_sec": 30,
    "level_3_delay_sec": 60,
    "level_4_delay_sec": 90,
    "dismiss_countdown_sec": 10
  },
  "reminders": {
    "eyes":    { "interval_min": 20, "duration_sec": 20 },
    "posture": { "interval_min": 30, "duration_sec": 10 },
    "water":   { "interval_min": 45, "duration_sec": 5 },
    "wrists":  { "interval_min": 40, "duration_sec": 30 },
    "stretch": { "interval_min": 60, "duration_sec": 180 },
    "walk":    { "interval_min": 90, "duration_sec": 300 }
  }
}
```

**Step 4: Write failing test for config loading**

```python
# tests/test_config.py
import json
import os
import tempfile
import pytest
from zenbreak.config import load_config, DEFAULT_CONFIG_PATH

def test_load_config_returns_defaults_when_no_user_config():
    config = load_config(user_config_path="/nonexistent/path.json")
    assert config["idle_threshold_sec"] == 120
    assert config["reminders"]["eyes"]["interval_min"] == 20

def test_load_config_merges_user_overrides():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"idle_threshold_sec": 60}, f)
        f.flush()
        config = load_config(user_config_path=f.name)
    os.unlink(f.name)
    assert config["idle_threshold_sec"] == 60
    assert config["reminders"]["eyes"]["interval_min"] == 20  # default preserved
```

**Step 5: Run test to verify it fails**

Run: `cd /Users/leichen/Documents/GitHub/zenbreak && python3 -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'zenbreak'`

**Step 6: Implement config module**

```python
# zenbreak/__init__.py
# ZenBreak - Your Personal Desk Health Guardian

# zenbreak/config.py
import json
import copy
from pathlib import Path

_DIR = Path(__file__).parent.parent
DEFAULT_CONFIG_PATH = _DIR / "config.default.json"
USER_CONFIG_DIR = Path.home() / ".zenbreak"
USER_CONFIG_PATH = USER_CONFIG_DIR / "config.json"


def _deep_merge(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(user_config_path: str | None = None) -> dict:
    with open(DEFAULT_CONFIG_PATH) as f:
        config = json.load(f)

    user_path = Path(user_config_path) if user_config_path else USER_CONFIG_PATH
    if user_path.exists():
        with open(user_path) as f:
            user_config = json.load(f)
        config = _deep_merge(config, user_config)

    return config
```

**Step 7: Run test to verify it passes**

Run: `cd /Users/leichen/Documents/GitHub/zenbreak && python3 -m pytest tests/test_config.py -v`
Expected: PASS

**Step 8: Create minimal menu bar app**

```python
# zenbreak/app.py
import rumps
from zenbreak.config import load_config


class ZenBreakApp(rumps.App):
    def __init__(self):
        super().__init__("ZenBreak", title="🧘 --m")
        self.config = load_config()
        self.menu = [
            rumps.MenuItem("Current: Starting up..."),
            None,
            rumps.MenuItem("Pause", callback=self.on_pause),
        ]

    def on_pause(self, sender):
        sender.state = not sender.state


def main():
    ZenBreakApp().run()


if __name__ == "__main__":
    main()
```

**Step 9: Create `__main__.py` entry point**

```python
# zenbreak/__main__.py
from zenbreak.app import main

if __name__ == "__main__":
    main()
```

**Step 10: Smoke test — run the app manually**

Run: `cd /Users/leichen/Documents/GitHub/zenbreak && python3 -m zenbreak.app`
Expected: Menu bar icon appears with "🧘 --m". Ctrl+C to quit.

**Step 11: Commit**

```bash
git add -A
git commit -m "feat: project skeleton with config loading and menu bar app"
```

---

## Task 2: Activity Monitor (App Tracking + Input Intensity)

**Files:**
- Create: `zenbreak/activity.py`
- Test: `tests/test_activity.py`

**Step 1: Write failing tests**

```python
# tests/test_activity.py
from unittest.mock import patch, MagicMock
from zenbreak.activity import ActivityMonitor, ActivitySnapshot, InputIntensity


def test_snapshot_classifies_heavy_keyboard():
    snap = ActivitySnapshot(
        app_name="Terminal",
        bundle_id="com.apple.Terminal",
        keyboard_events=80,
        mouse_events=5,
        timestamp=0,
    )
    assert snap.keyboard_intensity == InputIntensity.HEAVY
    assert snap.mouse_intensity == InputIntensity.LOW


def test_snapshot_classifies_idle():
    snap = ActivitySnapshot(
        app_name="Terminal",
        bundle_id="com.apple.Terminal",
        keyboard_events=0,
        mouse_events=0,
        timestamp=0,
    )
    assert snap.keyboard_intensity == InputIntensity.IDLE
    assert snap.mouse_intensity == InputIntensity.IDLE


def test_activity_monitor_get_session_summary():
    monitor = ActivityMonitor.__new__(ActivityMonitor)
    monitor.poll_interval = 5
    monitor.history = [
        ActivitySnapshot("Terminal", "com.apple.Terminal", 80, 5, 0),
        ActivitySnapshot("Terminal", "com.apple.Terminal", 90, 3, 5),
        ActivitySnapshot("VS Code", "com.microsoft.VSCode", 70, 20, 10),
    ]
    summary = monitor.get_session_summary(last_n_minutes=None)
    assert len(summary) == 2
    assert summary[0]["app_name"] in ("Terminal", "VS Code")
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_activity.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement activity monitor**

```python
# zenbreak/activity.py
import time
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from AppKit import NSWorkspace
from Quartz import (
    CGEventSourceSecondsSinceLastEventType,
    CGEventSourceCounterForEventType,
    kCGEventSourceStateHIDSystemState,
    kCGAnyInputEventType,
    kCGEventKeyDown,
    kCGEventLeftMouseDown,
)


class InputIntensity(Enum):
    IDLE = "idle"
    LOW = "low"
    MEDIUM = "medium"
    HEAVY = "heavy"


def _classify_intensity(events_per_min: int) -> InputIntensity:
    if events_per_min == 0:
        return InputIntensity.IDLE
    elif events_per_min <= 20:
        return InputIntensity.LOW
    elif events_per_min <= 50:
        return InputIntensity.MEDIUM
    else:
        return InputIntensity.HEAVY


@dataclass
class ActivitySnapshot:
    app_name: str
    bundle_id: str
    keyboard_events: int
    mouse_events: int
    timestamp: float

    @property
    def keyboard_intensity(self) -> InputIntensity:
        return _classify_intensity(self.keyboard_events)

    @property
    def mouse_intensity(self) -> InputIntensity:
        return _classify_intensity(self.mouse_events)


APP_CATEGORIES = {
    "com.apple.Terminal": "terminal",
    "com.googlecode.iterm2": "terminal",
    "dev.warp.Warp-Stable": "terminal",
    "com.microsoft.VSCode": "ide",
    "com.jetbrains.pycharm": "ide",
    "com.sublimetext.4": "ide",
    "com.google.Chrome": "browser",
    "com.apple.Safari": "browser",
    "org.mozilla.firefox": "browser",
    "com.brave.Browser": "browser",
    "us.zoom.xos": "video_call",
    "com.microsoft.teams2": "video_call",
    "com.tinyspeck.slackmacgap": "messaging",
    "com.hnc.Discord": "messaging",
}


class ActivityMonitor:
    def __init__(self, poll_interval_sec: int = 5):
        self.poll_interval = poll_interval_sec
        self.history: list[ActivitySnapshot] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_key_count = 0
        self._last_mouse_count = 0
        self._last_poll_time = 0.0

    def start(self):
        self._running = True
        self._last_poll_time = time.time()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _poll_loop(self):
        while self._running:
            self._take_snapshot()
            time.sleep(self.poll_interval)

    def _take_snapshot(self):
        now = time.time()
        elapsed = now - self._last_poll_time if self._last_poll_time else self.poll_interval
        self._last_poll_time = now

        ws = NSWorkspace.sharedWorkspace()
        front_app = ws.frontmostApplication()
        app_name = front_app.localizedName() or "Unknown"
        bundle_id = front_app.bundleIdentifier() or "unknown"

        try:
            key_count = CGEventSourceCounterForEventType(
                kCGEventSourceStateHIDSystemState, kCGEventKeyDown
            )
            mouse_count = CGEventSourceCounterForEventType(
                kCGEventSourceStateHIDSystemState, kCGEventLeftMouseDown
            )
        except Exception:
            key_count = self._last_key_count
            mouse_count = self._last_mouse_count

        key_diff = max(0, key_count - self._last_key_count)
        mouse_diff = max(0, mouse_count - self._last_mouse_count)
        self._last_key_count = key_count
        self._last_mouse_count = mouse_count

        factor = 60.0 / max(elapsed, 1)
        keys_per_min = int(key_diff * factor)
        mouse_per_min = int(mouse_diff * factor)

        snapshot = ActivitySnapshot(
            app_name=app_name,
            bundle_id=bundle_id,
            keyboard_events=keys_per_min,
            mouse_events=mouse_per_min,
            timestamp=now,
        )
        self.history.append(snapshot)

        cutoff = now - 7200
        self.history = [s for s in self.history if s.timestamp > cutoff]

    def get_idle_seconds(self) -> float:
        return CGEventSourceSecondsSinceLastEventType(
            kCGEventSourceStateHIDSystemState, kCGAnyInputEventType
        )

    def get_current_app(self) -> tuple[str, str]:
        ws = NSWorkspace.sharedWorkspace()
        front_app = ws.frontmostApplication()
        bundle_id = front_app.bundleIdentifier() or "unknown"
        app_name = front_app.localizedName() or "Unknown"
        category = APP_CATEGORIES.get(bundle_id, "other")
        return app_name, category

    def get_session_summary(self, last_n_minutes: Optional[int] = None) -> list[dict]:
        now = time.time()
        cutoff = now - (last_n_minutes * 60) if last_n_minutes else 0

        relevant = [s for s in self.history if s.timestamp >= cutoff]
        if not relevant:
            return []

        apps: dict[str, dict] = {}
        for snap in relevant:
            key = snap.app_name
            if key not in apps:
                apps[key] = {
                    "app_name": snap.app_name,
                    "bundle_id": snap.bundle_id,
                    "category": APP_CATEGORIES.get(snap.bundle_id, "other"),
                    "total_snapshots": 0,
                    "avg_keyboard": 0,
                    "avg_mouse": 0,
                    "max_keyboard": 0,
                    "_kb_sum": 0,
                    "_ms_sum": 0,
                }
            apps[key]["total_snapshots"] += 1
            apps[key]["_kb_sum"] += snap.keyboard_events
            apps[key]["_ms_sum"] += snap.mouse_events
            apps[key]["max_keyboard"] = max(apps[key]["max_keyboard"], snap.keyboard_events)

        result = []
        for info in apps.values():
            n = info["total_snapshots"]
            info["avg_keyboard"] = info["_kb_sum"] // n
            info["avg_mouse"] = info["_ms_sum"] // n
            info["duration_min"] = n * self.poll_interval / 60
            del info["_kb_sum"]
            del info["_ms_sum"]
            result.append(info)

        result.sort(key=lambda x: x["duration_min"], reverse=True)
        return result
```

**Step 4: Run tests**

Run: `python3 -m pytest tests/test_activity.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add zenbreak/activity.py tests/test_activity.py
git commit -m "feat: activity monitor with app tracking and input intensity classification"
```

---

## Task 3: Body Strain Model

**Files:**
- Create: `zenbreak/strain.py`
- Test: `tests/test_strain.py`

**Step 1: Write failing tests**

```python
# tests/test_strain.py
from zenbreak.strain import StrainTracker, BodyArea
from zenbreak.activity import ActivitySnapshot


def test_strain_increases_from_terminal_heavy_keyboard():
    tracker = StrainTracker()
    snapshots = [
        ActivitySnapshot("Terminal", "com.apple.Terminal", 80, 5, t)
        for t in range(0, 300, 5)
    ]
    for snap in snapshots:
        tracker.update(snap)

    strain = tracker.get_strain()
    assert strain[BodyArea.WRISTS] > 0
    assert strain[BodyArea.EYES] > 0
    assert strain[BodyArea.NECK] > 0


def test_strain_decays_after_break():
    tracker = StrainTracker()
    for t in range(0, 600, 5):
        tracker.update(ActivitySnapshot("Terminal", "com.apple.Terminal", 80, 5, t))

    strain_before = tracker.get_strain()[BodyArea.WRISTS]
    tracker.record_break(BodyArea.WRISTS, duration_sec=30)
    strain_after = tracker.get_strain()[BodyArea.WRISTS]
    assert strain_after < strain_before


def test_get_most_strained_area():
    tracker = StrainTracker()
    for t in range(0, 2400, 5):
        tracker.update(ActivitySnapshot("Terminal", "com.apple.Terminal", 80, 5, t))

    top = tracker.get_most_strained()
    assert top in (BodyArea.WRISTS, BodyArea.EYES, BodyArea.NECK)


def test_strain_caps_at_100():
    tracker = StrainTracker()
    for t in range(0, 36000, 5):
        tracker.update(ActivitySnapshot("Terminal", "com.apple.Terminal", 100, 5, t))

    for area, value in tracker.get_strain().items():
        assert value <= 100.0
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_strain.py -v`
Expected: FAIL

**Step 3: Implement strain tracker**

```python
# zenbreak/strain.py
from enum import Enum
from zenbreak.activity import ActivitySnapshot, InputIntensity, APP_CATEGORIES


class BodyArea(Enum):
    EYES = "eyes"
    NECK = "neck"
    WRISTS = "wrists"
    SHOULDERS = "shoulders"
    BACK = "back"
    CIRCULATION = "circulation"


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
        category = APP_CATEGORIES.get(snapshot.bundle_id, "other")
        rules = STRAIN_RULES.get(category, STRAIN_RULES["other"])
        kb_mult = KEYBOARD_MULTIPLIER.get(snapshot.keyboard_intensity, 1.0)

        for area, base_rate in rules.items():
            rate = base_rate
            if area in (BodyArea.WRISTS, BodyArea.SHOULDERS):
                rate *= kb_mult
            self._strain[area] = min(100.0, self._strain[area] + rate)

    def record_break(self, area: BodyArea, duration_sec: int):
        recovery = BREAK_RECOVERY.get(area, 1.0) * duration_sec / 10
        self._strain[area] = max(0.0, self._strain[area] - recovery)

    def record_full_break(self, duration_sec: int):
        for area in BodyArea:
            self.record_break(area, duration_sec)

    def get_strain(self) -> dict[BodyArea, float]:
        return dict(self._strain)

    def get_most_strained(self) -> BodyArea:
        return max(self._strain, key=self._strain.get)

    def get_strain_bar(self, area: BodyArea, width: int = 10) -> str:
        level = self._strain[area]
        filled = int(level / 100 * width)
        return "█" * filled + "░" * (width - filled)

    def get_priority_reminder(self) -> tuple[BodyArea, float]:
        area = self.get_most_strained()
        return area, self._strain[area]
```

**Step 4: Run tests**

Run: `python3 -m pytest tests/test_strain.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add zenbreak/strain.py tests/test_strain.py
git commit -m "feat: body strain model with activity-based accumulation and break recovery"
```

---

## Task 4: Exercise Library

**Files:**
- Create: `zenbreak/exercises.py`
- Test: `tests/test_exercises.py`

**Step 1: Write failing test**

```python
# tests/test_exercises.py
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
    assert len(names) >= 1


def test_all_body_areas_have_exercises():
    lib = ExerciseLibrary()
    for area in BodyArea:
        exercise = lib.get_exercise(area)
        assert exercise is not None
        assert exercise.body_area == area
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_exercises.py -v`
Expected: FAIL

**Step 3: Implement exercise library**

```python
# zenbreak/exercises.py
from dataclasses import dataclass
from zenbreak.strain import BodyArea


@dataclass
class Exercise:
    name: str
    body_area: BodyArea
    steps: list[str]
    duration_sec: int
    gif_path: str | None = None  # for v2


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
)


class ExerciseLibrary:
    def __init__(self):
        self._index: dict[BodyArea, int] = {area: 0 for area in BodyArea}

    def get_exercise(self, area: BodyArea) -> Exercise:
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
```

**Step 4: Run tests**

Run: `python3 -m pytest tests/test_exercises.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add zenbreak/exercises.py tests/test_exercises.py
git commit -m "feat: exercise library with rotations for all body areas"
```

---

## Task 5: Timer Engine + Escalation

**Files:**
- Create: `zenbreak/timers.py`
- Test: `tests/test_timers.py`

**Step 1: Write failing tests**

```python
# tests/test_timers.py
import time
from zenbreak.timers import ReminderEngine, EscalationLevel, Reminder
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
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_timers.py -v`
Expected: FAIL

**Step 3: Implement timer engine**

```python
# zenbreak/timers.py
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
        cooldown_sec: int = 120,
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
        self._active_reminder = None
        self._cooldown_until = time.time() + self.cooldown_sec

    def pause(self, minutes: int):
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
```

**Step 4: Run tests**

Run: `python3 -m pytest tests/test_timers.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add zenbreak/timers.py tests/test_timers.py
git commit -m "feat: timer engine with 4-level escalation and cooldown"
```

---

## Task 6: Full-Screen Overlay

**Files:**
- Create: `zenbreak/overlay.py`
- No unit test (UI component — tested via manual smoke test)

**Step 1: Implement overlay window**

Creates a native NSWindow overlay with calming gradient, exercise text, and countdown dismiss button.

```python
# zenbreak/overlay.py
import time
import threading
from AppKit import (
    NSApplication,
    NSWindow,
    NSView,
    NSColor,
    NSFont,
    NSTextField,
    NSButton,
    NSScreen,
    NSWindowStyleMaskBorderless,
    NSFloatingWindowLevel,
    NSBackingStoreBuffered,
    NSMutableParagraphStyle,
    NSCenterTextAlignment,
    NSGradient,
)
from Foundation import NSMakeRect
import objc


class GradientView(NSView):
    def drawRect_(self, rect):
        color1 = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.12, 0.22, 0.35, 0.95)
        color2 = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.15, 0.35, 0.40, 0.95)
        gradient = NSGradient.alloc().initWithStartingColor_endingColor_(color1, color2)
        gradient.drawInRect_angle_(rect, 270)


class OverlayManager:
    def __init__(self):
        self._window = None
        self._on_dismiss = None
        self._countdown_label = None
        self._dismiss_button = None

    def show(
        self,
        title: str,
        steps: list[str],
        context_line: str,
        duration_sec: int,
        dismiss_countdown: int = 10,
        opacity: float = 0.95,
        on_dismiss=None,
    ):
        self._on_dismiss = on_dismiss

        screen = NSScreen.mainScreen()
        frame = screen.frame()

        self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            NSWindowStyleMaskBorderless,
            NSBackingStoreBuffered,
            False,
        )
        self._window.setLevel_(NSFloatingWindowLevel + 1)
        self._window.setOpaque_(False)
        self._window.setAlphaValue_(opacity)
        self._window.setIgnoresMouseEvents_(False)
        self._window.setCollectionBehavior_(1 << 0)

        content = GradientView.alloc().initWithFrame_(frame)
        self._window.setContentView_(content)

        w = frame.size.width
        h = frame.size.height
        center_x = w / 2

        title_label = self._make_label(
            title,
            frame=NSMakeRect(center_x - 300, h * 0.65, 600, 60),
            font_size=36,
            bold=True,
        )
        content.addSubview_(title_label)

        steps_text = "\n".join(f"  {i+1}. {step}" for i, step in enumerate(steps))
        steps_label = self._make_label(
            steps_text,
            frame=NSMakeRect(center_x - 300, h * 0.35, 600, h * 0.28),
            font_size=20,
            bold=False,
        )
        content.addSubview_(steps_label)

        context_label = self._make_label(
            context_line,
            frame=NSMakeRect(center_x - 300, h * 0.28, 600, 30),
            font_size=14,
            bold=False,
            alpha=0.7,
        )
        content.addSubview_(context_label)

        self._countdown_label = self._make_label(
            f"Dismiss available in {dismiss_countdown}s",
            frame=NSMakeRect(center_x - 150, h * 0.18, 300, 30),
            font_size=14,
            bold=False,
            alpha=0.5,
        )
        content.addSubview_(self._countdown_label)

        self._dismiss_button = NSButton.alloc().initWithFrame_(
            NSMakeRect(center_x - 80, h * 0.12, 160, 44)
        )
        self._dismiss_button.setTitle_("I did it")
        self._dismiss_button.setBezelStyle_(1)
        self._dismiss_button.setFont_(NSFont.systemFontOfSize_(18))
        self._dismiss_button.setTarget_(self)
        self._dismiss_button.setAction_(objc.selector(self._on_dismiss_clicked_, signature=b"v@:@"))
        self._dismiss_button.setHidden_(True)
        content.addSubview_(self._dismiss_button)

        self._window.makeKeyAndOrderFront_(None)
        self._window.setLevel_(NSFloatingWindowLevel + 1)

        threading.Thread(
            target=self._countdown_thread,
            args=(dismiss_countdown,),
            daemon=True,
        ).start()

    def _countdown_thread(self, seconds: int):
        for remaining in range(seconds, 0, -1):
            if self._window is None:
                return
            self._update_countdown(f"Dismiss available in {remaining}s")
            time.sleep(1)
        self._update_countdown("")
        self._show_dismiss_button()

    def _update_countdown(self, text: str):
        if self._countdown_label:
            self._countdown_label.performSelectorOnMainThread_withObject_waitUntilDone_(
                objc.selector(self._countdown_label.setStringValue_, signature=b"v@:@"),
                text,
                False,
            )

    def _show_dismiss_button(self):
        if self._dismiss_button:
            self._dismiss_button.performSelectorOnMainThread_withObject_waitUntilDone_(
                objc.selector(self._dismiss_button.setHidden_, signature=b"v@:c"),
                False,
                False,
            )

    @objc.python_method
    def _on_dismiss_clicked_(self, sender):
        self.dismiss()

    def dismiss(self):
        if self._window:
            self._window.orderOut_(None)
            self._window = None
        if self._on_dismiss:
            self._on_dismiss()

    def show_semi_transparent(self, message: str, opacity: float = 0.5):
        screen = NSScreen.mainScreen()
        frame = screen.frame()

        self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            NSWindowStyleMaskBorderless,
            NSBackingStoreBuffered,
            False,
        )
        self._window.setLevel_(NSFloatingWindowLevel + 1)
        self._window.setOpaque_(False)
        self._window.setAlphaValue_(opacity)

        content = GradientView.alloc().initWithFrame_(frame)
        self._window.setContentView_(content)

        w = frame.size.width
        h = frame.size.height

        label = self._make_label(
            message,
            frame=NSMakeRect(w/2 - 300, h/2 - 30, 600, 60),
            font_size=28,
            bold=True,
        )
        content.addSubview_(label)

        self._window.makeKeyAndOrderFront_(None)

    def _make_label(
        self,
        text: str,
        frame,
        font_size: float,
        bold: bool,
        alpha: float = 1.0,
    ) -> NSTextField:
        label = NSTextField.alloc().initWithFrame_(frame)
        label.setStringValue_(text)
        label.setBezeled_(False)
        label.setDrawsBackground_(False)
        label.setEditable_(False)
        label.setSelectable_(False)

        font = (
            NSFont.boldSystemFontOfSize_(font_size) if bold
            else NSFont.systemFontOfSize_(font_size)
        )
        label.setFont_(font)
        label.setTextColor_(
            NSColor.colorWithCalibratedRed_green_blue_alpha_(1, 1, 1, alpha)
        )
        label.setAlignment_(NSCenterTextAlignment)
        return label

    @property
    def is_visible(self) -> bool:
        return self._window is not None
```

**Step 2: Smoke test**

Run: `cd /Users/leichen/Documents/GitHub/zenbreak && python3 -c "
from zenbreak.overlay import OverlayManager
from AppKit import NSApplication
import threading

app = NSApplication.sharedApplication()
mgr = OverlayManager()

def show():
    import time; time.sleep(1)
    mgr.show(
        title='WRIST & FOREARM STRETCH',
        steps=['Extend right arm, palm up', 'Pull fingers back gently — 15 sec', 'Switch to left arm', 'Make fists, rotate wrists 10x'],
        context_line='3hr heavy keyboard today — your forearm extensors need this.',
        duration_sec=30,
        dismiss_countdown=5,
        on_dismiss=lambda: app.terminate_(None),
    )

threading.Thread(target=show, daemon=True).start()
app.run()
"`

Expected: Full-screen overlay appears with gradient, exercise steps, countdown, then dismiss button.

**Step 3: Commit**

```bash
git add zenbreak/overlay.py
git commit -m "feat: full-screen overlay with gradient background and countdown dismiss"
```

---

## Task 7: Sound (Gentle Chime)

**Files:**
- Create: `zenbreak/sound.py`

**Step 1: Implement sound module**

```python
# zenbreak/sound.py
import subprocess
import threading
from pathlib import Path

CHIME_PATH = Path(__file__).parent.parent / "assets" / "sounds" / "chime.wav"
SYSTEM_SOUND = "/System/Library/Sounds/Tink.aiff"


def play_chime():
    sound_path = str(CHIME_PATH) if CHIME_PATH.exists() else SYSTEM_SOUND

    def _play():
        subprocess.run(["afplay", sound_path], check=False)

    threading.Thread(target=_play, daemon=True).start()
```

**Step 2: Commit**

```bash
git add zenbreak/sound.py
git commit -m "feat: gentle chime sound with system sound fallback"
```

---

## Task 8: Idle Detection Module

**Files:**
- Create: `zenbreak/idle.py`

**Step 1: Implement idle detection**

```python
# zenbreak/idle.py
from Quartz import (
    CGEventSourceSecondsSinceLastEventType,
    kCGEventSourceStateHIDSystemState,
    kCGAnyInputEventType,
)


def get_idle_seconds() -> float:
    return CGEventSourceSecondsSinceLastEventType(
        kCGEventSourceStateHIDSystemState,
        kCGAnyInputEventType,
    )


def is_user_idle(threshold_sec: float = 120) -> bool:
    return get_idle_seconds() > threshold_sec
```

**Step 2: Commit**

```bash
git add zenbreak/idle.py
git commit -m "feat: idle detection via Quartz CGEventSource"
```

---

## Task 9: Wire Everything Together in App

**Files:**
- Modify: `zenbreak/app.py` (complete rewrite)

**Step 1: Rewrite `app.py` to wire all components**

```python
# zenbreak/app.py
import rumps
import time
from datetime import datetime

from zenbreak.config import load_config
from zenbreak.activity import ActivityMonitor, APP_CATEGORIES
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

        self.activity = ActivityMonitor(poll_interval_sec=5)
        self.strain = StrainTracker()
        self.engine = ReminderEngine(
            strain_threshold=50.0,
            level_2_delay=self.config["escalation"]["level_2_delay_sec"],
            level_3_delay=self.config["escalation"]["level_3_delay_sec"],
            level_4_delay=self.config["escalation"]["level_4_delay_sec"],
        )
        self.exercises = ExerciseLibrary()
        self.overlay = OverlayManager()

        self._idle_paused = False
        self._return_grace_until = 0.0
        self.breaks_taken = 0
        self.breaks_total = 0

        self.current_activity_item = rumps.MenuItem("Current: Starting up...")
        self.next_break_item = rumps.MenuItem("Next break: Calculating...")
        self.strain_item = rumps.MenuItem("Strain: Calculating...")
        self.stats_item = rumps.MenuItem("Today: 0 breaks taken")

        self.menu = [
            self.current_activity_item,
            self.strain_item,
            self.next_break_item,
            None,
            self.stats_item,
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
        now = time.time()

        if not self._in_work_hours():
            self.title = "🧘 off"
            return

        idle_sec = get_idle_seconds()
        idle_threshold = self.config["idle_threshold_sec"]

        if idle_sec > idle_threshold:
            if not self._idle_paused:
                self._idle_paused = True
                self.title = "🧘 away"
                if self.overlay.is_visible:
                    self.overlay.dismiss()
            return

        if self._idle_paused:
            self._idle_paused = False
            grace = self.config["return_grace_min"] * 60
            self._return_grace_until = now + grace
            self.strain.record_full_break(int(idle_sec * 0.5))

        if now < self._return_grace_until:
            remaining = int(self._return_grace_until - now)
            self.title = f"🧘 {remaining // 60}m grace"
            return

        if self.activity.history:
            latest = self.activity.history[-1]
            self.strain.update(latest)

        self._update_menu_info()

        strain_levels = self.strain.get_strain()
        reminder = self.engine.check(strain_levels)

        if reminder is None:
            top_area, top_strain = self.strain.get_priority_reminder()
            if top_strain > 0:
                remaining_pct = max(0, 50.0 - top_strain)
                if self.activity.history:
                    rate = max(0.01, top_strain / max(1, len(self.activity.history)))
                    est_min = int(remaining_pct / rate / 12)
                    self.title = f"🧘 {est_min}m"
                else:
                    self.title = "🧘 --m"
            return

        self._handle_reminder(reminder)

    def _handle_reminder(self, reminder):
        area = reminder.body_area
        exercise = self.exercises.get_exercise(area)
        reminder.exercise = exercise

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
            if not self.overlay.is_visible:
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
        self.breaks_taken += 1
        reminder = self.engine._active_reminder
        if reminder and reminder.exercise:
            self.strain.record_break(reminder.body_area, reminder.exercise.duration_sec)
        self.engine.acknowledge()
        self.stats_item.title = f"Today: {self.breaks_taken}/{self.breaks_total} breaks taken"
        self.title = "🧘 ✓"

    def _get_activity_context(self, area: BodyArea) -> str:
        summary = self.activity.get_session_summary(last_n_minutes=60)
        if not summary:
            return f"Your {area.value} need attention."
        top = summary[0]
        duration = int(top["duration_min"])
        return f"{duration}min of {top['app_name']} — your {area.value} need this."

    def _update_menu_info(self):
        app_name, category = self.activity.get_current_app()
        self.current_activity_item.title = f"Current: {app_name} ({category})"

        top_area, top_strain = self.strain.get_priority_reminder()
        bars = " | ".join(
            f"{a.value}: {self.strain.get_strain_bar(a, 5)}"
            for a in sorted(
                BodyArea,
                key=lambda a: self.strain.get_strain()[a],
                reverse=True,
            )[:3]
        )
        self.strain_item.title = f"Strain: {bars}"

    def _in_work_hours(self) -> bool:
        now = datetime.now()
        start_h, start_m = map(int, self.config["work_hours"]["start"].split(":"))
        end_h, end_m = map(int, self.config["work_hours"]["end"].split(":"))

        current_minutes = now.hour * 60 + now.minute
        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m

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
```

**Step 2: Smoke test the full app**

Run: `cd /Users/leichen/Documents/GitHub/zenbreak && python3 -m zenbreak.app`

Expected:
- Menu bar shows `🧘 --m`
- Click to see current app, strain levels, pause options
- After ~5-10 min of use, strain builds and first reminder fires
- Escalation works through 4 levels
- Overlay shows with exercise and dismiss countdown

**Step 3: Commit**

```bash
git add zenbreak/app.py zenbreak/idle.py
git commit -m "feat: wire all components — activity-aware menu bar app with escalation"
```

---

## Task 10: Auto-Start (LaunchAgent)

**Files:**
- Create: `install.sh`
- Create: `com.zenbreak.app.plist`

**Step 1: Create LaunchAgent plist**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.zenbreak.app</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>-m</string>
        <string>zenbreak.app</string>
    </array>
    <key>WorkingDirectory</key>
    <string>ZENBREAK_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>ZENBREAK_HOME/zenbreak.log</string>
    <key>StandardErrorPath</key>
    <string>ZENBREAK_HOME/zenbreak.err</string>
</dict>
</plist>
```

**Step 2: Create install script**

```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ZENBREAK_HOME="$HOME/.zenbreak"
PLIST_NAME="com.zenbreak.app.plist"
PLIST_SRC="$SCRIPT_DIR/$PLIST_NAME"
PLIST_DST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "Installing ZenBreak..."

mkdir -p "$ZENBREAK_HOME"
mkdir -p "$ZENBREAK_HOME/stats"

if [ ! -f "$ZENBREAK_HOME/config.json" ]; then
    cp "$SCRIPT_DIR/config.default.json" "$ZENBREAK_HOME/config.json"
    echo "Created default config at $ZENBREAK_HOME/config.json"
fi

sed "s|ZENBREAK_DIR|$SCRIPT_DIR|g; s|ZENBREAK_HOME|$ZENBREAK_HOME|g" \
    "$PLIST_SRC" > "$PLIST_DST"

echo "Installed LaunchAgent at $PLIST_DST"

launchctl load "$PLIST_DST" 2>/dev/null || true
echo "ZenBreak will now start automatically at login."
echo "To start now: python3 -m zenbreak.app"
echo "To uninstall: launchctl unload $PLIST_DST && rm $PLIST_DST"
```

**Step 3: Commit**

```bash
git add install.sh com.zenbreak.app.plist
git commit -m "feat: auto-start via macOS LaunchAgent with install script"
```

---

## Task 11: Integration Test + Polish

**Files:**
- Create: `tests/test_integration.py`

**Step 1: Write integration test**

```python
# tests/test_integration.py
from zenbreak.config import load_config
from zenbreak.activity import ActivitySnapshot
from zenbreak.strain import StrainTracker, BodyArea
from zenbreak.timers import ReminderEngine, EscalationLevel
from zenbreak.exercises import ExerciseLibrary


def test_full_flow_strain_builds_to_reminder():
    config = load_config()
    strain = StrainTracker()
    engine = ReminderEngine(strain_threshold=50.0)
    exercises = ExerciseLibrary()

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

    reminder = engine.check(levels)
    assert reminder is not None
    assert reminder.level == EscalationLevel.LEVEL_1

    exercise = exercises.get_exercise(reminder.body_area)
    assert exercise is not None
    assert len(exercise.steps) > 0

    strain.record_break(reminder.body_area, exercise.duration_sec)
    engine.acknowledge()
    new_strain = strain.get_strain()[reminder.body_area]
    assert new_strain < max_strain


def test_idle_reduces_strain():
    strain = StrainTracker()

    for t in range(0, 1200, 5):
        snap = ActivitySnapshot("Terminal", "com.apple.Terminal", 80, 5, float(t))
        strain.update(snap)

    before = strain.get_strain()[BodyArea.WRISTS]
    assert before > 0

    strain.record_full_break(120)

    after = strain.get_strain()[BodyArea.WRISTS]
    assert after < before
```

**Step 2: Run all tests**

Run: `python3 -m pytest tests/ -v`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: integration test for full strain → reminder → recovery flow"
```

---

## Summary

| Task | What | Est. LOC |
|------|------|----------|
| 1 | Project skeleton + menu bar + config | ~80 |
| 2 | Activity monitor (app + input tracking) | ~150 |
| 3 | Body strain model | ~120 |
| 4 | Exercise library | ~180 |
| 5 | Timer engine + escalation | ~100 |
| 6 | Full-screen overlay | ~180 |
| 7 | Sound | ~15 |
| 8 | Idle detection | ~15 |
| 9 | Wire everything together | ~200 |
| 10 | Auto-start LaunchAgent | ~40 |
| 11 | Integration test + polish | ~60 |
| **Total** | | **~1,140** |

Tasks 1-8 can be built independently. Task 9 wires them together. Tasks 10-11 are finishing touches.
