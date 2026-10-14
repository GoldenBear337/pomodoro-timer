"""Entry point: wires timer, clock overlay, tray, storage and windows together on the Tk thread."""
import argparse
import os
import queue
import sys
import tkinter as tk

from . import notify, storage, winutil
from .timer import FOCUS, LABELS, PomodoroTimer

TICK_MS = 200


class App:
    def __init__(self, demo=False):
        self.demo = demo
        self.unit = 1 if demo else 60
        self.data_dir = storage.app_dir(demo)
        self.settings = storage.load_settings(self.data_dir, demo)
        self.store = storage.Store(os.path.join(self.data_dir, "pomodoro.db"))
        if demo and self.store.is_empty():
            self.store.seed_demo()
        self.chime = notify.ensure_chime(self.data_dir)

        self._queue = queue.Queue()
        self._save_job = None
        self._quitting = False
        self.settings_window = None
        self.dashboard = None
        self.hotkey = None

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("Pomodoro")

        self.timer = PomodoroTimer(self.settings, unit=self.unit,
                                   on_session_end=self._on_session_end,
                                   on_phase_change=self._on_phase_change)

        from .overlay import ClockOverlay
        from .tray import Tray
        self.overlay = ClockOverlay(self, demo)
        self.tray = Tray(self, demo)
        self.tray.start()
        self.apply_hotkey()

    # ---- thread-safe dispatch ----

    def post(self, fn):
        """Queue a callable to run on the Tk thread (used by tray + hotkey threads)."""
        self._queue.put(fn)

    def _loop(self):
        while True:
            try:
                fn = self._queue.get_nowait()
            except queue.Empty:
                break
            fn()
            if self._quitting:
                return
        if self.instance.show_requested():
            self.settings["clock_visible"] = True
            self.overlay.show()
        self.timer.tick()
        self.overlay.update()
        self.tray.refresh()
        self.root.after(TICK_MS, self._loop)

    # ---- timer events ----

    def _on_session_end(self, rec):
        self.store.add_session(rec["kind"], rec["planned_sec"], rec["actual_sec"], rec["completed"],
                               rec["started_at"], rec["ended_at"])
        if self.dashboard:
            self.dashboard.refresh()

    def _on_phase_change(self, phase, completed):
        if not completed:
            return
        if self.settings["sound"]:
            notify.play(self.chime)
        if self.settings["notifications"]:
            unit = "sec" if self.demo else "min"
            length = f"{self.settings[phase]} {unit}"
            if phase == FOCUS:
                self.tray.notify("Break over", f"Ready to focus? ({length})")
            else:
                self.tray.notify("Focus session done 🍅", f"Time for a {LABELS[phase].lower()} ({length})")

    # ---- actions (Tk thread) ----

    def toggle(self):
        self.timer.toggle()

    def skip(self):
        self.timer.skip()

    def reset(self):
        self.timer.reset()

    def toggle_clock(self):
        self.settings["clock_visible"] = not self.settings["clock_visible"]
        self.overlay.show() if self.settings["clock_visible"] else self.overlay.hide()
        self.save_settings()

    def toggle_click_through(self):
        self.settings["click_through"] = not self.settings["click_through"]
        winutil.set_click_through(self.overlay.win, self.settings["click_through"])
        if self.settings_window:
            self.settings_window.sync_from_settings()
        self.save_settings()

    def apply_hotkey(self):
        if self.settings["hotkey"] and not self.hotkey:
            self.hotkey = winutil.GlobalHotkey("P", lambda: self.post(self.toggle))
            if not self.hotkey.ok:
                self.hotkey = None
        elif not self.settings["hotkey"] and self.hotkey:
            self.hotkey.stop()
            self.hotkey = None

    def open_settings(self):
        from .settings_ui import SettingsWindow
        if not self.settings_window:
            self.settings_window = SettingsWindow(self)
        self.settings_window.show()

    def open_dashboard(self):
        from .dashboard import Dashboard
        if not self.dashboard:
            self.dashboard = Dashboard(self)
        self.dashboard.show()

    def refresh_dashboard(self):
        if self.dashboard:
            self.dashboard.refresh()

    def on_settings_changed(self, relayout=False):
        if relayout:
            self.overlay.apply_settings()
        self.refresh_dashboard()

    def save_settings(self):
        """Debounced: slider drags would otherwise write the file dozens of times a second."""
        if self._save_job:
            self.root.after_cancel(self._save_job)
        self._save_job = self.root.after(400, self._save_now)

    def _save_now(self):
        self._save_job = None
        storage.save_settings(self.data_dir, self.settings)

    def quit(self):
        self._quitting = True
        self.timer.abandon()
        self._save_now()
        if self.hotkey:
            self.hotkey.stop()
        self.tray.stop()
        self.store.close()
        self.root.destroy()

    def run(self, instance):
        self.instance = instance
        self.root.after(TICK_MS, self._loop)
        self.root.mainloop()


def main(argv=None):
    parser = argparse.ArgumentParser(prog="Pomodoro")
    parser.add_argument("--demo", action="store_true", help="seconds instead of minutes, separate sample data")
    args = parser.parse_args(argv)

    instance = winutil.SingleInstance("PomodoroTimer" + ("_demo" if args.demo else ""))
    if not instance.is_primary:
        instance.signal_primary()
        return 0

    winutil.enable_dpi_awareness()
    App(demo=args.demo).run(instance)
    return 0


if __name__ == "__main__":
    sys.exit(main())
