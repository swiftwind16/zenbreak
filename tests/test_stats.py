import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from zenbreak.stats import StatsTracker, _empty_day, _save_day, _load_day, STATS_DIR


def test_record_break_taken():
    tracker = StatsTracker()
    tracker._today = _empty_day()
    tracker.record_break_taken("eyes")
    assert tracker.breaks_taken == 1
    assert tracker._today["breaks_by_area"]["eyes"] == 1


def test_record_multiple_breaks():
    tracker = StatsTracker()
    tracker._today = _empty_day()
    tracker.record_break_taken("eyes")
    tracker.record_break_taken("wrists")
    tracker.record_break_taken("eyes")
    assert tracker.breaks_taken == 3
    assert tracker._today["breaks_by_area"]["eyes"] == 2
    assert tracker._today["breaks_by_area"]["wrists"] == 1


def test_compliance_pct():
    tracker = StatsTracker()
    tracker._today = _empty_day()
    tracker._today["breaks_taken"] = 8
    tracker._today["breaks_offered"] = 10
    assert tracker.compliance_pct == 80.0


def test_compliance_pct_no_offers():
    tracker = StatsTracker()
    tracker._today = _empty_day()
    assert tracker.compliance_pct == 100.0


def test_get_summary():
    tracker = StatsTracker()
    tracker._today = _empty_day()
    tracker._today["breaks_taken"] = 5
    tracker._today["breaks_offered"] = 8
    tracker._today["breaks_by_area"] = {"eyes": 3, "wrists": 2}
    summary = tracker.get_summary()
    assert "5/8" in summary
    assert "eyes" in summary
