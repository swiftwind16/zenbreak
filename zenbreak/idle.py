from Quartz import (
    CGEventSourceSecondsSinceLastEventType,
    kCGEventSourceStateHIDSystemState,
    kCGAnyInputEventType,
)


def get_idle_seconds() -> float:
    """Return seconds since last keyboard/mouse input."""
    return CGEventSourceSecondsSinceLastEventType(
        kCGEventSourceStateHIDSystemState,
        kCGAnyInputEventType,
    )


def is_user_idle(threshold_sec: float = 120) -> bool:
    return get_idle_seconds() > threshold_sec
