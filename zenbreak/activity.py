"""Activity monitoring: frontmost app tracking and input intensity measurement."""

import enum
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 5
HISTORY_MAX_SECONDS = 2 * 60 * 60  # 2 hours

APP_CATEGORIES: Dict[str, str] = {
    # Terminals
    "com.apple.Terminal": "terminal",
    "com.googlecode.iterm2": "terminal",
    "dev.warp.Warp-Stable": "terminal",
    # IDEs
    "com.todesktop.230313mzl4w4u92": "ide",  # Cursor
    "com.microsoft.VSCode": "ide",
    "com.jetbrains.intellij": "ide",
    "com.jetbrains.pycharm": "ide",
    "com.apple.dt.Xcode": "ide",
    "com.sublimetext.4": "ide",
    # Browsers
    "com.apple.Safari": "browser",
    "com.google.Chrome": "browser",
    "org.mozilla.firefox": "browser",
    "com.brave.Browser": "browser",
    "company.thebrowser.Browser": "browser",
    # Video calls
    "us.zoom.xos": "video_call",
    "com.microsoft.teams2": "video_call",
    "com.google.meet": "video_call",
    "com.apple.FaceTime": "video_call",
    # Messaging
    "com.apple.MobileSMS": "messaging",
    "com.tinyspeck.slackmacgap": "messaging",
    "ru.keepcoder.Telegram": "messaging",
    "com.hnc.Discord": "messaging",
    "com.tencent.xinWeChat": "messaging",  # WeChat
    "com.tencent.WeWorkMac": "messaging",  # WeCom
    "com.facebook.archon": "messaging",
    # Reading/writing
    "notion.id": "browser",  # Notion — similar to browser usage
    "com.apple.Notes": "browser",
    "com.openai.chat": "browser",  # ChatGPT desktop
}


class InputIntensity(enum.Enum):
    """Classifies input event rate into intensity levels."""

    IDLE = "idle"
    LOW = "low"
    MEDIUM = "medium"
    HEAVY = "heavy"

    @classmethod
    def from_events_per_minute(cls, epm: float) -> "InputIntensity":
        """Classify an events-per-minute rate into an intensity level.

        IDLE: 0 events/min
        LOW: 1-20 events/min
        MEDIUM: 21-50 events/min
        HEAVY: 50+ events/min
        """
        if epm <= 0:
            return cls.IDLE
        if epm <= 20:
            return cls.LOW
        if epm <= 50:
            return cls.MEDIUM
        return cls.HEAVY


@dataclass
class ActivitySnapshot:
    """A point-in-time capture of user activity."""

    app_name: str
    bundle_id: str
    keyboard_events: float  # events per minute
    mouse_events: float  # events per minute
    timestamp: float = field(default_factory=time.time)

    @property
    def keyboard_intensity(self) -> InputIntensity:
        return InputIntensity.from_events_per_minute(self.keyboard_events)

    @property
    def mouse_intensity(self) -> InputIntensity:
        return InputIntensity.from_events_per_minute(self.mouse_events)

    @property
    def app_category(self) -> str:
        return APP_CATEGORIES.get(self.bundle_id, "other")


@dataclass
class AppSessionSummary:
    """Summary of activity for a single app over a time period."""

    app_name: str
    bundle_id: str
    category: str
    total_duration_seconds: float
    avg_keyboard_intensity: str
    avg_mouse_intensity: str
    snapshot_count: int


class ActivityMonitor:
    """Polls frontmost app and input event counts on a daemon thread."""

    def __init__(self) -> None:
        self._history: List[ActivitySnapshot] = []
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._prev_keyboard_count: Optional[int] = None
        self._prev_mouse_count: Optional[int] = None
        self._prev_poll_time: Optional[float] = None

    # -- Public API --

    def start(self) -> None:
        """Start polling in a daemon thread."""
        if self._running:
            logger.warning("[activity-monitor] Already running")
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info("[activity-monitor] Started polling every %ds", POLL_INTERVAL_SECONDS)

    def stop(self) -> None:
        """Stop the polling thread."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=POLL_INTERVAL_SECONDS + 1)
            self._thread = None
        logger.info("[activity-monitor] Stopped")

    @property
    def history(self) -> List[ActivitySnapshot]:
        with self._lock:
            return list(self._history)

    @property
    def latest(self) -> Optional[ActivitySnapshot]:
        with self._lock:
            return self._history[-1] if self._history else None

    def get_session_summary(self) -> List[AppSessionSummary]:
        """Group history by app, returning duration and average intensity per app."""
        with self._lock:
            snapshots = list(self._history)

        if not snapshots:
            return []

        grouped: Dict[str, List[ActivitySnapshot]] = {}
        for snap in snapshots:
            grouped.setdefault(snap.bundle_id, []).append(snap)

        summaries = []
        for bundle_id, snaps in grouped.items():
            count = len(snaps)
            total_duration = count * POLL_INTERVAL_SECONDS
            avg_kb = sum(s.keyboard_events for s in snaps) / count
            avg_ms = sum(s.mouse_events for s in snaps) / count

            summaries.append(
                AppSessionSummary(
                    app_name=snaps[0].app_name,
                    bundle_id=bundle_id,
                    category=APP_CATEGORIES.get(bundle_id, "other"),
                    total_duration_seconds=total_duration,
                    avg_keyboard_intensity=InputIntensity.from_events_per_minute(avg_kb).value,
                    avg_mouse_intensity=InputIntensity.from_events_per_minute(avg_ms).value,
                    snapshot_count=count,
                )
            )

        summaries.sort(key=lambda s: s.total_duration_seconds, reverse=True)
        return summaries

    # -- Internal --

    def _poll_loop(self) -> None:
        """Main polling loop running on daemon thread."""
        while self._running:
            try:
                snapshot = self._capture_snapshot()
                if snapshot is not None:
                    self._add_snapshot(snapshot)
            except Exception as e:
                logger.warning("[activity-monitor] Poll error: %s", e)
            time.sleep(POLL_INTERVAL_SECONDS)

    def _capture_snapshot(self) -> Optional[ActivitySnapshot]:
        """Capture current frontmost app and input event rates."""
        try:
            from AppKit import NSWorkspace
            from Quartz import (
                CGEventSourceCounterForEventType,
                kCGEventSourceStateHIDSystemState,
                kCGEventKeyDown,
                kCGEventLeftMouseDown,
            )
        except ImportError:
            logger.debug("[activity-monitor] macOS frameworks not available")
            return None

        workspace = NSWorkspace.sharedWorkspace()
        active_app = workspace.frontmostApplication()
        if active_app is None:
            return None

        app_name = active_app.localizedName() or "Unknown"
        bundle_id = active_app.bundleIdentifier() or "unknown"

        now = time.time()
        kb_count = CGEventSourceCounterForEventType(
            kCGEventSourceStateHIDSystemState, kCGEventKeyDown
        )
        mouse_count = CGEventSourceCounterForEventType(
            kCGEventSourceStateHIDSystemState, kCGEventLeftMouseDown
        )

        kb_epm = 0.0
        mouse_epm = 0.0

        if self._prev_poll_time is not None and self._prev_keyboard_count is not None:
            elapsed_minutes = (now - self._prev_poll_time) / 60.0
            if elapsed_minutes > 0:
                kb_delta = kb_count - self._prev_keyboard_count
                mouse_delta = mouse_count - self._prev_mouse_count
                kb_epm = max(0, kb_delta / elapsed_minutes)
                mouse_epm = max(0, mouse_delta / elapsed_minutes)

        self._prev_keyboard_count = kb_count
        self._prev_mouse_count = mouse_count
        self._prev_poll_time = now

        return ActivitySnapshot(
            app_name=app_name,
            bundle_id=bundle_id,
            keyboard_events=kb_epm,
            mouse_events=mouse_epm,
            timestamp=now,
        )

    def _add_snapshot(self, snapshot: ActivitySnapshot) -> None:
        """Add a snapshot and prune history older than HISTORY_MAX_SECONDS."""
        cutoff = time.time() - HISTORY_MAX_SECONDS
        with self._lock:
            self._history.append(snapshot)
            self._history = [s for s in self._history if s.timestamp >= cutoff]
