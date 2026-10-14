"""System tray icon. Menu actions are queued and executed on the Tk thread by the app."""
import pystray
from PIL import Image, ImageDraw

from .timer import FOCUS, LABELS

MODE_COLORS = {"focus": "#ff5f57", "short_break": "#34c759", "long_break": "#4aa3ff"}
IDLE_COLOR = "#9a9aa0"


def make_icon(color, size=64, ring=None):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = size // 10
    d.ellipse((pad, pad, size - pad, size - pad), fill=color)
    if ring is not None:  # white arc showing progress
        d.arc((pad + 4, pad + 4, size - pad - 4, size - pad - 4), -90, -90 + 360 * ring, fill="white", width=size // 10)
    return img


class Tray:
    def __init__(self, app, demo=False):
        self.app = app
        self.demo = demo
        self._last_key = None
        self._last_menu = None
        q = app.post  # thread-safe: runs callable on the Tk thread
        timer = app.timer
        item = pystray.MenuItem
        menu = pystray.Menu(
            item(lambda _: "Pause" if timer.running else "Start", lambda: q(app.toggle)),
            item("Skip", lambda: q(app.skip)),
            item("Reset", lambda: q(app.reset)),
            pystray.Menu.SEPARATOR,
            item("Show clock", lambda: q(app.toggle_clock), checked=lambda _: app.settings["clock_visible"], default=True),
            item("Click-through clock", lambda: q(app.toggle_click_through), checked=lambda _: app.settings["click_through"]),
            item("Dashboard", lambda: q(app.open_dashboard)),
            item("Settings", lambda: q(app.open_settings)),
            pystray.Menu.SEPARATOR,
            item("Quit", lambda: q(app.quit)),
        )
        self.icon = pystray.Icon("PomodoroTimer", make_icon(IDLE_COLOR), self._title(), menu)

    def _title(self):
        t = self.app.timer
        secs = int(round(t.remaining()))
        state = "" if t.running else (" (paused)" if not t.is_fresh() else " (ready)")
        label = LABELS[t.phase]
        prefix = "[DEMO] " if self.demo else ""
        return f"{prefix}{label} {secs // 60:02d}:{secs % 60:02d}{state}"

    def start(self):
        self.icon.run_detached()

    def refresh(self):
        """Update tooltip each tick; redraw the icon only when it visibly changes."""
        t = self.app.timer
        self.icon.title = self._title()
        color = IDLE_COLOR if (t.is_fresh() and t.phase == FOCUS) else MODE_COLORS[t.phase]
        ring = None if t.is_fresh() else round(t.progress() * 12) / 12  # 12 steps is plenty at 16px
        key = (color, ring)
        if key != self._last_key:
            self._last_key = key
            self.icon.icon = make_icon(color, ring=ring)
        menu_key = (t.running, self.app.settings["clock_visible"], self.app.settings["click_through"])
        if menu_key != self._last_menu:
            self._last_menu = menu_key
            self.icon.update_menu()

    def notify(self, title, message):
        try:
            self.icon.notify(message, title)
        except Exception:
            pass

    def stop(self):
        self.icon.stop()
