"""Full-screen native macOS overlay for ZenBreak exercise reminders."""

import logging
import threading
import time

import objc
from AppKit import (
    NSBackingStoreBuffered,
    NSBezierPath,
    NSButton,
    NSCenterTextAlignment,
    NSColor,
    NSFont,
    NSGradient,
    NSMakeRect,
    NSScreen,
    NSTextField,
    NSView,
    NSWindow,
    NSWindowStyleMaskBorderless,
    NSFloatingWindowLevel,
)

logger = logging.getLogger(__name__)


class GradientView(NSView):
    """NSView subclass that draws a calming blue-green gradient background."""

    def drawRect_(self, rect):
        color1 = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.12, 0.22, 0.35, 0.95)
        color2 = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.15, 0.35, 0.40, 0.95)
        gradient = NSGradient.alloc().initWithStartingColor_endingColor_(color1, color2)
        path = NSBezierPath.bezierPathWithRect_(rect)
        gradient.drawInBezierPath_angle_(path, 270.0)


class OverlayManager:
    """Manages full-screen overlay windows for exercise reminders."""

    def __init__(self):
        self._window = None
        self._on_dismiss = None
        self._dismiss_requested = False

    @property
    def is_visible(self):
        return self._window is not None

    def show(
        self,
        title: str,
        steps: list[str],
        context_line: str = "",
        duration_sec: int = 30,
        dismiss_countdown: int = 10,
        opacity: float = 0.95,
        on_dismiss=None,
    ):
        """Show full-screen overlay with exercise prescription."""
        self._on_dismiss = on_dismiss
        self._dismiss_requested = False

        screen = NSScreen.mainScreen()
        frame = screen.frame()

        self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            NSWindowStyleMaskBorderless,
            NSBackingStoreBuffered,
            False,
        )
        self._window.setLevel_(NSFloatingWindowLevel + 1)
        self._window.setCollectionBehavior_(1 << 0)
        self._window.setOpaque_(False)
        self._window.setAlphaValue_(opacity)
        self._window.setIgnoresMouseEvents_(False)

        content_view = GradientView.alloc().initWithFrame_(frame)
        self._window.setContentView_(content_view)

        w = frame.size.width
        h = frame.size.height
        center_x = w / 2.0

        # Title
        title_label = self._make_label(
            title, NSFont.boldSystemFontOfSize_(36.0),
            NSColor.whiteColor(),
            NSMakeRect(center_x - 400, h * 0.65, 800, 60),
        )
        title_label.setAlignment_(NSCenterTextAlignment)
        content_view.addSubview_(title_label)

        # Exercise steps
        step_y = h * 0.55
        for i, step_text in enumerate(steps, start=1):
            step_label = self._make_label(
                f"  {i}. {step_text}",
                NSFont.systemFontOfSize_(20.0),
                NSColor.whiteColor(),
                NSMakeRect(center_x - 350, step_y, 700, 30),
            )
            content_view.addSubview_(step_label)
            step_y -= 35

        # Context line
        if context_line:
            ctx_label = self._make_label(
                context_line, NSFont.systemFontOfSize_(14.0),
                NSColor.colorWithCalibratedRed_green_blue_alpha_(1, 1, 1, 0.7),
                NSMakeRect(center_x - 400, step_y - 30, 800, 25),
            )
            ctx_label.setAlignment_(NSCenterTextAlignment)
            content_view.addSubview_(ctx_label)

        # Countdown label
        countdown_label = self._make_label(
            f"Dismiss available in {dismiss_countdown}s",
            NSFont.systemFontOfSize_(16.0),
            NSColor.colorWithCalibratedRed_green_blue_alpha_(1, 1, 1, 0.5),
            NSMakeRect(center_x - 200, h * 0.18, 400, 30),
        )
        countdown_label.setAlignment_(NSCenterTextAlignment)
        content_view.addSubview_(countdown_label)

        # "I did it" button (hidden initially)
        dismiss_button = NSButton.alloc().initWithFrame_(
            NSMakeRect(center_x - 80, h * 0.12, 160, 44)
        )
        dismiss_button.setTitle_("I did it")
        dismiss_button.setBezelStyle_(1)
        dismiss_button.setFont_(NSFont.boldSystemFontOfSize_(18.0))
        dismiss_button.setHidden_(True)
        dismiss_button.setTarget_(self)
        dismiss_button.setAction_(
            objc.selector(self._on_dismiss_clicked_, signature=b"v@:@")
        )
        content_view.addSubview_(dismiss_button)

        self._window.makeKeyAndOrderFront_(None)

        # Start countdown
        threading.Thread(
            target=self._run_countdown,
            args=(dismiss_countdown, countdown_label, dismiss_button),
            daemon=True,
        ).start()

    def show_semi_transparent(self, message: str, opacity: float = 0.5):
        """Show a semi-transparent overlay with just a message."""
        screen = NSScreen.mainScreen()
        frame = screen.frame()

        self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            NSWindowStyleMaskBorderless,
            NSBackingStoreBuffered,
            False,
        )
        self._window.setLevel_(NSFloatingWindowLevel + 1)
        self._window.setCollectionBehavior_(1 << 0)
        self._window.setOpaque_(False)
        self._window.setAlphaValue_(opacity)

        content_view = GradientView.alloc().initWithFrame_(frame)
        self._window.setContentView_(content_view)

        w = frame.size.width
        h = frame.size.height

        label = self._make_label(
            message, NSFont.boldSystemFontOfSize_(28.0),
            NSColor.whiteColor(),
            NSMakeRect(w / 2 - 400, h / 2 - 25, 800, 50),
        )
        label.setAlignment_(NSCenterTextAlignment)
        content_view.addSubview_(label)

        self._window.makeKeyAndOrderFront_(None)

    def dismiss(self):
        """Hide the overlay and invoke callback."""
        self._dismiss_requested = True
        if self._window is not None:
            self._window.orderOut_(None)
            self._window = None
        if self._on_dismiss is not None:
            try:
                self._on_dismiss()
            except Exception as e:
                logger.warning("[overlay] on_dismiss callback failed: %s", e)

    @objc.python_method
    def _on_dismiss_clicked_(self, sender):
        self.dismiss()

    _on_dismiss_clicked_ = objc.selector(
        _on_dismiss_clicked_, signature=b"v@:@"
    )

    @objc.python_method
    def _run_countdown(self, seconds, countdown_label, dismiss_button):
        for remaining in range(seconds, 0, -1):
            if self._dismiss_requested:
                return
            text = f"Dismiss available in {remaining}s"
            countdown_label.performSelectorOnMainThread_withObject_waitUntilDone_(
                objc.selector(countdown_label.setStringValue_, signature=b"v@:@"),
                text, False,
            )
            time.sleep(1)

        if self._dismiss_requested:
            return

        countdown_label.performSelectorOnMainThread_withObject_waitUntilDone_(
            objc.selector(countdown_label.setStringValue_, signature=b"v@:@"),
            "", False,
        )
        dismiss_button.performSelectorOnMainThread_withObject_waitUntilDone_(
            objc.selector(dismiss_button.setHidden_, signature=b"v@:c"),
            False, False,
        )

    @staticmethod
    def _make_label(text, font, color, frame):
        label = NSTextField.alloc().initWithFrame_(frame)
        label.setStringValue_(text)
        label.setFont_(font)
        label.setTextColor_(color)
        label.setBezeled_(False)
        label.setDrawsBackground_(False)
        label.setEditable_(False)
        label.setSelectable_(False)
        return label
