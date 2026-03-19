"""Full-screen native macOS overlay for ZenBreak exercise reminders."""

import logging
import threading
import time

import objc
from Foundation import NSObject
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


class OverlayManager(NSObject):
    """Manages full-screen overlay windows for exercise reminders."""

    def init(self):
        self = objc.super(OverlayManager, self).init()
        if self is None:
            return None
        self._window = None
        self._on_dismiss = None
        self._dismiss_requested = False
        self._event_monitor = None
        return self

    @objc.python_method
    def get_is_visible(self):
        return self._window is not None

    is_visible = property(lambda self: self.get_is_visible())

    @objc.python_method
    def show(
        self,
        title: str,
        steps: list[str],
        context_line: str = "",
        video_url: str | None = None,
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
        title_y = h * 0.82 if video_url else h * 0.65
        title_label = self._make_label(
            title, NSFont.boldSystemFontOfSize_(36.0),
            NSColor.whiteColor(),
            NSMakeRect(center_x - 400, title_y, 800, 60),
        )
        title_label.setAlignment_(NSCenterTextAlignment)
        content_view.addSubview_(title_label)

        # Exercise steps
        step_y = (h * 0.72 if video_url else h * 0.55)
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

        # Embedded video player (if video URL provided)
        if video_url:
            video_id = self._extract_video_id(video_url)
            if video_id:
                from WebKit import WKWebView, WKWebViewConfiguration
                config = WKWebViewConfiguration.alloc().init()
                config.preferences().setJavaScriptEnabled_(True)

                vid_w, vid_h = 480, 270
                webview = WKWebView.alloc().initWithFrame_configuration_(
                    NSMakeRect(center_x - vid_w / 2, h * 0.25, vid_w, vid_h),
                    config,
                )
                # Embed YouTube player with autoplay, no related videos
                html = f'''<html><body style="margin:0;background:#000;">
                <iframe width="{vid_w}" height="{vid_h}"
                    src="https://www.youtube.com/embed/{video_id}?autoplay=1&rel=0&modestbranding=1&controls=1"
                    frameborder="0" allow="autoplay; encrypted-media" allowfullscreen>
                </iframe></body></html>'''
                from Foundation import NSURL
                webview.loadHTMLString_baseURL_(html, NSURL.URLWithString_("about:blank"))
                content_view.addSubview_(webview)

        # Exercise timer label (large, prominent)
        timer_label = self._make_label(
            f"Do this for {duration_sec}s",
            NSFont.boldSystemFontOfSize_(24.0),
            NSColor.colorWithCalibratedRed_green_blue_alpha_(1, 1, 1, 0.9),
            NSMakeRect(center_x - 200, h * 0.22, 400, 35),
        )
        timer_label.setAlignment_(NSCenterTextAlignment)
        content_view.addSubview_(timer_label)

        # "I did it" button — always visible, disabled during countdown
        dismiss_button = NSButton.alloc().initWithFrame_(
            NSMakeRect(center_x - 80, h * 0.14, 160, 44)
        )
        dismiss_button.setTitle_(f"I did it ({duration_sec}s)")
        dismiss_button.setBezelStyle_(1)
        dismiss_button.setFont_(NSFont.boldSystemFontOfSize_(18.0))
        dismiss_button.setEnabled_(True)
        dismiss_button.setTarget_(self)
        dismiss_button.setAction_(b"dismissClicked:")
        content_view.addSubview_(dismiss_button)

        # Emergency exit hint
        escape_hint = self._make_label(
            "Press Esc to dismiss early",
            NSFont.systemFontOfSize_(12.0),
            NSColor.colorWithCalibratedRed_green_blue_alpha_(1, 1, 1, 0.3),
            NSMakeRect(center_x - 150, h * 0.08, 300, 20),
        )
        escape_hint.setAlignment_(NSCenterTextAlignment)
        content_view.addSubview_(escape_hint)

        self._window.makeKeyAndOrderFront_(None)

        # Listen for Escape key
        self._setup_escape_key()

        # Start exercise timer, then enable dismiss button
        threading.Thread(
            target=self._run_exercise_timer,
            args=(duration_sec, timer_label, dismiss_button),
            daemon=True,
        ).start()

    @objc.python_method
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

    @objc.python_method
    def dismiss(self):
        """Hide the overlay and invoke callback."""
        self._dismiss_requested = True
        if self._event_monitor is not None:
            from AppKit import NSEvent
            NSEvent.removeMonitor_(self._event_monitor)
            self._event_monitor = None
        if self._window is not None:
            self._window.orderOut_(None)
            self._window = None
        if self._on_dismiss is not None:
            try:
                self._on_dismiss()
            except Exception as e:
                logger.warning("[overlay] on_dismiss callback failed: %s", e)

    @objc.IBAction
    def dismissClicked_(self, sender):
        self.dismiss()

    @staticmethod
    def _extract_video_id(url: str) -> str | None:
        """Extract YouTube video ID from various URL formats."""
        import re
        patterns = [
            r'youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
            r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
            r'youtu\.be/([a-zA-Z0-9_-]{11})',
            r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    @objc.python_method
    def _setup_escape_key(self):
        """Add Escape key listener to dismiss the overlay."""
        from AppKit import NSEvent, NSKeyDownMask

        def handler(event):
            if event.keyCode() == 53:  # Escape key
                self.dismiss()
            return event

        self._event_monitor = NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
            NSKeyDownMask, handler
        )

    @objc.python_method
    @objc.python_method
    def _run_exercise_timer(self, duration_sec, timer_label, dismiss_button):
        """Count down the exercise duration, then enable dismiss button."""
        for remaining in range(duration_sec, 0, -1):
            if self._dismiss_requested:
                return
            mins, secs = divmod(remaining, 60)
            if mins > 0:
                text = f"Do this for {mins}m {secs:02d}s"
            else:
                text = f"Do this for {secs}s"
            timer_label.performSelectorOnMainThread_withObject_waitUntilDone_(
                objc.selector(timer_label.setStringValue_, signature=b"v@:@"),
                text, False,
            )
            # Update button text with remaining time
            btn_text = f"I did it ({remaining}s)"
            dismiss_button.performSelectorOnMainThread_withObject_waitUntilDone_(
                objc.selector(dismiss_button.setTitle_, signature=b"v@:@"),
                btn_text, False,
            )
            time.sleep(1)

        if self._dismiss_requested:
            return

        # Exercise complete — enable button
        timer_label.performSelectorOnMainThread_withObject_waitUntilDone_(
            objc.selector(timer_label.setStringValue_, signature=b"v@:@"),
            "Done! Great job.", False,
        )
        dismiss_button.performSelectorOnMainThread_withObject_waitUntilDone_(
            objc.selector(dismiss_button.setTitle_, signature=b"v@:@"),
            "I did it", False,
        )
        # Button is already enabled — just update the title

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
