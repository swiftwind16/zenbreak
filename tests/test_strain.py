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


def test_full_break_reduces_all_areas():
    tracker = StrainTracker()
    for t in range(0, 600, 5):
        tracker.update(ActivitySnapshot("Terminal", "com.apple.Terminal", 80, 5, t))

    before = {a: v for a, v in tracker.get_strain().items()}
    tracker.record_full_break(120)
    after = tracker.get_strain()

    for area in BodyArea:
        assert after[area] <= before[area]


def test_strain_bar_format():
    tracker = StrainTracker()
    bar = tracker.get_strain_bar(BodyArea.EYES, width=10)
    assert len(bar) == 10
    assert bar == "░" * 10  # no strain yet
