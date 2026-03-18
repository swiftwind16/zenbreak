"""Full-screen native macOS overlay for ZenBreak exercise reminders.

Uses pyobjc to create borderless NSWindow overlays with calming gradients,
exercise instructions, and a countdown-gated dismiss button.
"""

import logging
import subprocess
import threading
import time

import objc
from AppKit import (
    NSApplication,
    NSBackingStoreBuffered,
    NSBezierPath,
    NSBorderlessWindowMask,
    NSButton,
    NSCenterTextAlignment,
    NSColor,
    NSFont,
    NSMakeRect,
    NSScreen,
    NSTextField,
    NSView,
    NSWindow,
)

logger = logging.getLogger(__name__)


class GradientView(NSView):
    """NSView subclass that draws a calming blue-green gradient background."""

    def drawRect_(self, rect):
        start_color = NSColor.colorWithCalibratedRed_green_blue_alpha_(
            0.05, 0.15, 0.25, 1.0
        )
        end_color = NSColor.colorWithCalibratedRed_green_blue_alpha_(
            0.08, 0.30, 0.35, 1.0
        )

        path = NSBezierPath.bezierPathWithRect_(rect)
        gradient = __import__(
            "AppKit", fromlist=["NSGradient"]
        ).NSGradient.alloc().initWithStartingColor_endingColor_(
            start_color, end_color
        )
        gradient.drawInBezierPath_angle_(path, 90.0)


class OverlayManager:
    """Manages full-screen overlay windows for exercise reminders.

    Attributes:
        on_dismiss: Optional callback invoked when the user dismisses the overlay.
    """

    def __init__(self, on_dismiss=None):
        self.on_dismiss = on_dismiss
        self._window = None
        self._countdown_thread = None
        self._dismiss_requested = False

    @property
    def is_visible(self):
        """Return True if the overlay window is currently visible."""
        if self._window is None:
            return False
        return self._window.isVisible()

    def show(self, title, steps, context_line="", countdown_seconds=30):
        """Show a full-screen exercise overlay with countdown-gated dismiss.

        Args:
            title: Heading text for the exercise (e.g., "Neck Stretch").
            steps: List of exercise step strings, displayed as a numbered list.
            context_line: Optional context line (e.g., "You've been coding for 45 min").
            countdown_seconds: Seconds before the dismiss button appears.
        """
        logger.info(
            "[overlay] Showing full overlay: title=%s, steps=%d, countdown=%ds",
            title,
            len(steps),
            countdown_seconds,
        )

        screen = NSScreen.mainScreen()
        frame = screen.frame()

        self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            NSBorderlessWindowMask,
            NSBackingStoreBuffered,
            False,
        )
        self._window.setLevel_(4)  # NSFloatingWindowLevel (3) + 1
        self._window.setCollectionBehavior_(1 << 0)  # Appear on all spaces
        self._window.setOpaque_(True)
        self._window.setBackgroundColor_(NSColor.clearColor())

        content_view = GradientView.alloc().initWithFrame_(frame)
        self._window.setContentView_(content_view)

        center_x = frame.size.width / 2.0
        top_y = frame.size.height

        # Title label
        title_label = self._make_label(
            text=title,
            font=NSFont.boldSystemFontOfSize_(36.0),
            color=NSColor.whiteColor(),
            frame=NSMakeRect(
                center_x - 400, top_y - 150, 800, 50
            ),
        )
        title_label.setAlignment_(NSCenterTextAlignment)
        content_view.addSubview_(title_label)

        # Exercise steps as numbered list
        step_y = top_y - 220
        for i, step_text in enumerate(steps, start=1):
            step_label = self._make_label(
                text=f"{i}. {step_text}",
                font=NSFont.systemFontOfSize_(20.0),
                color=NSColor.whiteColor(),
                frame=NSMakeRect(center_x - 350, step_y, 700, 30),
            )
            content_view.addSubview_(step_label)
            step_y -= 35

        # Context line
        if context_line:
            context_label = self._make_label(
                text=context_line,
                font=NSFont.systemFontOfSize_(14.0),
                color=NSColor.colorWithCalibratedRed_green_blue_alpha_(
                    1.0, 1.0, 1.0, 0.7
                ),
                frame=NSMakeRect(center_x - 400, step_y - 30, 800, 25),
            )
            context_label.setAlignment_(NSCenterTextAlignment)
            content_view.addSubview_(context_label)

        # Countdown label
        countdown_label = self._make_label(
            text=f"Dismiss available in {countdown_seconds}s",
            font=NSFont.systemFontOfSize_(18.0),
            color=NSColor.colorWithCalibratedRed_green_blue_alpha_(
                1.0, 1.0, 1.0, 0.8
            ),
            frame=NSMakeRect(center_x - 200, 120, 400, 30),
        )
        countdown_label.setAlignment_(NSCenterTextAlignment)
        content_view.addSubview_(countdown_label)

        # "I did it" button (hidden initially)
        dismiss_button = NSButton.alloc().initWithFrame_(
            NSMakeRect(center_x - 80, 60, 160, 44)
        )
        dismiss_button.setTitle_("I did it")
        dismiss_button.setBezelStyle_(1)  # NSRoundedBezelStyle
        dismiss_button.setFont_(NSFont.boldSystemFontOfSize_(16.0))
        dismiss_button.setHidden_(True)
        dismiss_button.setTarget_(self)
        dismiss_button.setAction_(objc.selector(self._on_dismiss_clicked_, signature=b"v@:@"))
        content_view.addSubview_(dismiss_button)

        self._window.makeKeyAndOrderFront_(None)

        # Start countdown in background thread
        self._dismiss_requested = False
        self._countdown_thread = threading.Thread(
            target=self._run_countdown,
            args=(countdown_seconds, countdown_label, dismiss_button),
            daemon=True,
        )
        self._countdown_thread.start()

    def show_semi_transparent(self, message):
        """Show a simpler semi-transparent overlay with just a message.

        Args:
            message: Text to display centered on the overlay.
        """
        logger.info("[overlay] Showing semi-transparent overlay: %s", message)

        screen = NSScreen.mainScreen()
        frame = screen.frame()

        self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            NSBorderlessWindowMask,
            NSBackingStoreBuffered,
            False,
        )
        self._window.setLevel_(4)
        self._window.setCollectionBehavior_(1 << 0)
        self._window.setOpaque_(False)
        self._window.setAlphaValue_(0.5)
        self._window.setBackgroundColor_(
            NSColor.colorWithCalibratedRed_green_blue_alpha_(0.0, 0.0, 0.0, 1.0)
        )

        content_view = NSView.alloc().initWithFrame_(frame)
        self._window.setContentView_(content_view)

        center_x = frame.size.width / 2.0
        center_y = frame.size.height / 2.0

        message_label = self._make_label(
            text=message,
            font=NSFont.boldSystemFontOfSize_(28.0),
            color=NSColor.whiteColor(),
            frame=NSMakeRect(center_x - 400, center_y - 25, 800, 50),
        )
        message_label.setAlignment_(NSCenterTextAlignment)
        content_view.addSubview_(message_label)

        self._window.makeKeyAndOrderFront_(None)

    def dismiss(self):
        """Hide the overlay window and invoke the on_dismiss callback."""
        logger.info("[overlay] Dismissing overlay")
        self._dismiss_requested = True

        if self._window is not None:
            self._window.orderOut_(None)
            self._window = None

        if self.on_dismiss is not None:
            try:
                self.on_dismiss()
            except Exception as e:
                logger.warning("[overlay] on_dismiss callback failed: %s", e)

    @objc.python_method
    def _on_dismiss_clicked_(self, sender):
        """Handle dismiss button click."""
        self.dismiss()

    _on_dismiss_clicked_ = objc.selector(
        _on_dismiss_clicked_, signature=b"v@:@"
    )

    @objc.python_method
    def _run_countdown(self, seconds, countdown_label, dismiss_button):
        """Run the countdown timer in a background thread.

        Updates the countdown label each second via the main thread,
        then reveals the dismiss button when the countdown reaches zero.
        """
        for remaining in range(seconds, 0, -1):
            if self._dismiss_requested:
                return
            text = f"Dismiss available in {remaining}s"
            countdown_label.performSelectorOnMainThread_withObject_waitUntilDone_(
                objc.selector(countdown_label.setStringValue_, signature=b"v@:@"),
                text,
                False,
            )
            time.sleep(1)

        if self._dismiss_requested:
            return

        # Countdown complete: update label and show button
        countdown_label.performSelectorOnMainThread_withObject_waitUntilDone_(
            objc.selector(countdown_label.setStringValue_, signature=b"v@:@"),
            "Ready to dismiss!",
            False,
        )
        dismiss_button.performSelectorOnMainThread_withObject_waitUntilDone_(
            objc.selector(dismiss_button.setHidden_, signature=b"v@:c"),
            False,
            False,
        )

    @staticmethod
    def _make_label(text, font, color, frame):
        """Create a styled NSTextField label.

        Args:
            text: The string to display.
            font: NSFont instance for the label.
            color: NSColor for the text.
            frame: NSRect defining position and size.

        Returns:
            Configured NSTextField instance.
        """
        label = NSTextField.alloc().initWithFrame_(frame)
        label.setStringValue_(text)
        label.setFont_(font)
        label.setTextColor_(color)
        label.setBezeled_(False)
        label.setDrawsBackground_(False)
        label.setEditable_(False)
        label.setSelectable_(False)
        return label
