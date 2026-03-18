"""Tests for the activity monitoring module."""

import time

from zenbreak.activity import (
    APP_CATEGORIES,
    POLL_INTERVAL_SECONDS,
    ActivityMonitor,
    ActivitySnapshot,
    InputIntensity,
)


class TestInputIntensityClassification:
    """Verify events-per-minute thresholds map to correct intensity levels."""

    def test_snapshot_classifies_heavy_keyboard(self) -> None:
        """80 keyboard events/min = HEAVY, 5 mouse events/min = LOW."""
        snapshot = ActivitySnapshot(
            app_name="VS Code",
            bundle_id="com.microsoft.VSCode",
            keyboard_events=80,
            mouse_events=5,
            timestamp=time.time(),
        )
        assert snapshot.keyboard_intensity is InputIntensity.HEAVY
        assert snapshot.mouse_intensity is InputIntensity.LOW

    def test_snapshot_classifies_idle(self) -> None:
        """0 events = IDLE for both keyboard and mouse."""
        snapshot = ActivitySnapshot(
            app_name="Finder",
            bundle_id="com.apple.finder",
            keyboard_events=0,
            mouse_events=0,
            timestamp=time.time(),
        )
        assert snapshot.keyboard_intensity is InputIntensity.IDLE
        assert snapshot.mouse_intensity is InputIntensity.IDLE

    def test_medium_intensity(self) -> None:
        """30 events/min = MEDIUM."""
        assert InputIntensity.from_events_per_minute(30) is InputIntensity.MEDIUM

    def test_boundary_low_to_medium(self) -> None:
        """20 events/min = LOW, 21 = MEDIUM."""
        assert InputIntensity.from_events_per_minute(20) is InputIntensity.LOW
        assert InputIntensity.from_events_per_minute(21) is InputIntensity.MEDIUM

    def test_boundary_medium_to_heavy(self) -> None:
        """50 events/min = MEDIUM, 51 = HEAVY."""
        assert InputIntensity.from_events_per_minute(50) is InputIntensity.MEDIUM
        assert InputIntensity.from_events_per_minute(51) is InputIntensity.HEAVY


class TestAppCategory:
    """Verify bundle ID to category mapping."""

    def test_known_bundle_id_returns_category(self) -> None:
        snapshot = ActivitySnapshot(
            app_name="Terminal",
            bundle_id="com.apple.Terminal",
            keyboard_events=10,
            mouse_events=2,
        )
        assert snapshot.app_category == "terminal"

    def test_unknown_bundle_id_returns_other(self) -> None:
        snapshot = ActivitySnapshot(
            app_name="Some App",
            bundle_id="com.unknown.app",
            keyboard_events=0,
            mouse_events=0,
        )
        assert snapshot.app_category == "other"


class TestActivityMonitorSessionSummary:
    """Verify get_session_summary groups history by app correctly."""

    def test_activity_monitor_get_session_summary(self) -> None:
        """Create monitor with mock history, verify grouping by app."""
        monitor = ActivityMonitor()
        now = time.time()

        # Simulate 3 snapshots in VS Code (heavy typing)
        for i in range(3):
            monitor._history.append(
                ActivitySnapshot(
                    app_name="VS Code",
                    bundle_id="com.microsoft.VSCode",
                    keyboard_events=80,
                    mouse_events=10,
                    timestamp=now - (5 - i) * POLL_INTERVAL_SECONDS,
                )
            )

        # Simulate 2 snapshots in Chrome (light browsing)
        for i in range(2):
            monitor._history.append(
                ActivitySnapshot(
                    app_name="Google Chrome",
                    bundle_id="com.google.Chrome",
                    keyboard_events=5,
                    mouse_events=30,
                    timestamp=now - (2 - i) * POLL_INTERVAL_SECONDS,
                )
            )

        summaries = monitor.get_session_summary()

        assert len(summaries) == 2

        # Sorted by duration descending, so VS Code first
        vscode_summary = summaries[0]
        assert vscode_summary.app_name == "VS Code"
        assert vscode_summary.bundle_id == "com.microsoft.VSCode"
        assert vscode_summary.category == "ide"
        assert vscode_summary.snapshot_count == 3
        assert vscode_summary.total_duration_seconds == 3 * POLL_INTERVAL_SECONDS
        assert vscode_summary.avg_keyboard_intensity == "heavy"
        assert vscode_summary.avg_mouse_intensity == "low"

        chrome_summary = summaries[1]
        assert chrome_summary.app_name == "Google Chrome"
        assert chrome_summary.bundle_id == "com.google.Chrome"
        assert chrome_summary.category == "browser"
        assert chrome_summary.snapshot_count == 2
        assert chrome_summary.total_duration_seconds == 2 * POLL_INTERVAL_SECONDS
        assert chrome_summary.avg_keyboard_intensity == "low"
        assert chrome_summary.avg_mouse_intensity == "medium"

    def test_empty_history_returns_empty_list(self) -> None:
        monitor = ActivityMonitor()
        assert monitor.get_session_summary() == []
