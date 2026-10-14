"""Settings window. Every change applies and saves immediately."""
import os
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from . import winutil

FONTS = ["Segoe UI Light", "Segoe UI", "Segoe UI Semibold", "Bahnschrift Light", "Bahnschrift",
         "Consolas", "Cascadia Mono", "Arial", "Georgia"]


class SettingsWindow:
    def __init__(self, app):
        self.app = app
        s = app.settings
        self.win = tk.Toplevel(app.root)
        self.win.title("Pomodoro — Settings" + (" [DEMO]" if app.demo else ""))
        self.win.resizable(False, False)
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self._vars = {}

        nb = ttk.Notebook(self.win)
        nb.pack(fill="both", expand=True, padx=10, pady=10)
        unit = "sec" if app.demo else "min"

        # --- Timer ---
        f = self._tab(nb, "Timer")
        self._spin(f, 0, f"Focus ({unit})", "focus", 1, 180)
        self._spin(f, 1, f"Short break ({unit})", "short_break", 1, 60)
        self._spin(f, 2, f"Long break ({unit})", "long_break", 1, 120)
        self._spin(f, 3, "Long break every (rounds)", "long_break_every", 1, 12)
        self._spin(f, 4, "Daily goal (pomodoros)", "daily_goal", 1, 30)
        self._check(f, 5, "Auto-start breaks", "auto_start_breaks")
        self._check(f, 6, "Auto-start next focus", "auto_start_focus")

        # --- Clock ---
        f = self._tab(nb, "Clock")
        ttk.Label(f, text="Opacity").grid(row=0, column=0, sticky="w", pady=3)
        self._scale(f, 0, "opacity", 0.2, 1.0)
        ttk.Label(f, text="Size").grid(row=1, column=0, sticky="w", pady=3)
        self._scale(f, 1, "font_size", 16, 120, integer=True)
        ttk.Label(f, text="Font").grid(row=2, column=0, sticky="w", pady=3)
        fv = tk.StringVar(value=s["font_family"])
        cb = ttk.Combobox(f, textvariable=fv, values=FONTS, width=22)
        cb.grid(row=2, column=1, sticky="w")
        fv.trace_add("write", lambda *_: self._set("font_family", fv.get(), relayout=True))
        ttk.Label(f, text="Color").grid(row=3, column=0, sticky="w", pady=3)
        self.color_btn = tk.Button(f, width=6, bg=s["text_color"], relief="flat", command=self._pick_color)
        self.color_btn.grid(row=3, column=1, sticky="w")
        self._check(f, 4, "Show progress line", "show_progress", relayout=True)
        self._check(f, 5, "Show mode dot (red = focus, green/blue = break)", "show_mode_dot", relayout=True)
        self._check(f, 6, "Dark background (off = pure transparent)", "dark_background", relayout=True)
        self._check(f, 7, "Always on top", "always_on_top", relayout=True)
        self._check(f, 8, "Click-through (toggle off from tray menu)", "click_through", relayout=True)
        ttk.Label(f, text="Drag the digits to move · double-click = start/pause · right-click = menu",
                  foreground="#777").grid(row=9, column=0, columnspan=2, sticky="w", pady=(8, 0))

        # --- General ---
        f = self._tab(nb, "General")
        self._check(f, 0, "Sound when a session ends", "sound")
        self._check(f, 1, "Windows notification when a session ends", "notifications")
        self._check(f, 2, "Global hotkey Ctrl+Alt+P = start/pause", "hotkey", on_change=app.apply_hotkey)
        self.autostart = tk.BooleanVar(value=winutil.get_autostart())
        ttk.Checkbutton(f, text="Start with Windows", variable=self.autostart,
                        command=self._toggle_autostart).grid(row=3, column=0, columnspan=2, sticky="w", pady=3)

        # --- Data ---
        f = self._tab(nb, "Data")
        ttk.Label(f, text="Stored only on this PC:").grid(row=0, column=0, sticky="w")
        path = ttk.Entry(f, width=48)
        path.insert(0, app.data_dir)
        path.state(["readonly"])
        path.grid(row=1, column=0, sticky="w", pady=(2, 10))
        ttk.Button(f, text="Open data folder", command=lambda: os.startfile(app.data_dir)).grid(row=2, column=0, sticky="w", pady=2)
        ttk.Button(f, text="Export sessions to CSV…", command=self._export).grid(row=3, column=0, sticky="w", pady=2)
        ttk.Button(f, text="Reset all session data…", command=self._reset_data).grid(row=4, column=0, sticky="w", pady=2)

    def _tab(self, nb, title):
        frame = ttk.Frame(nb, padding=12)
        frame.columnconfigure(1, weight=1)
        nb.add(frame, text=title)
        return frame

    def _set(self, key, value, relayout=False):
        self.app.settings[key] = value
        self.app.save_settings()
        self.app.on_settings_changed(relayout=relayout)

    def _spin(self, parent, row, label, key, lo, hi):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=3, padx=(0, 12))
        var = tk.StringVar(value=str(self.app.settings[key]))
        ttk.Spinbox(parent, from_=lo, to=hi, textvariable=var, width=6).grid(row=row, column=1, sticky="w")

        def changed(*_):
            try:
                value = int(var.get())
            except ValueError:
                return
            if lo <= value <= hi and value != self.app.settings[key]:
                self._set(key, value)
        var.trace_add("write", changed)
        self._vars[key] = var

    def _check(self, parent, row, label, key, relayout=False, on_change=None):
        var = tk.BooleanVar(value=bool(self.app.settings[key]))

        def changed():
            self._set(key, var.get(), relayout=relayout)
            if on_change:
                on_change()
        ttk.Checkbutton(parent, text=label, variable=var, command=changed).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=3)
        self._vars[key] = var

    def _scale(self, parent, row, key, lo, hi, integer=False):
        var = tk.DoubleVar(value=float(self.app.settings[key]))

        def changed(_value):
            v = int(round(var.get())) if integer else round(var.get(), 2)
            if v != self.app.settings[key]:
                self._set(key, v, relayout=True)
        ttk.Scale(parent, from_=lo, to=hi, variable=var, command=changed, length=220).grid(row=row, column=1, sticky="w")

    def _pick_color(self):
        _, hex_color = colorchooser.askcolor(self.app.settings["text_color"], parent=self.win)
        if hex_color:
            self.color_btn.config(bg=hex_color)
            self._set("text_color", hex_color, relayout=True)

    def _toggle_autostart(self):
        try:
            winutil.set_autostart(self.autostart.get())
        except OSError as e:
            messagebox.showerror("Start with Windows", str(e), parent=self.win)
            self.autostart.set(winutil.get_autostart())

    def _export(self):
        path = filedialog.asksaveasfilename(parent=self.win, defaultextension=".csv",
                                            initialfile="pomodoro_sessions.csv",
                                            filetypes=[("CSV", "*.csv")])
        if path:
            n = self.app.store.export_csv(path)
            messagebox.showinfo("Export", f"Exported {n} sessions to\n{path}", parent=self.win)

    def _reset_data(self):
        if messagebox.askyesno("Reset data", "Delete ALL session history? This cannot be undone.",
                               icon="warning", parent=self.win):
            self.app.store.reset()
            self.app.refresh_dashboard()

    def sync_from_settings(self):
        """Reflect changes made elsewhere (e.g. click-through toggled from the tray)."""
        for key, var in self._vars.items():
            if isinstance(var, tk.BooleanVar) and var.get() != bool(self.app.settings[key]):
                var.set(bool(self.app.settings[key]))

    def show(self):
        self.win.deiconify()
        self.win.lift()
        self.win.focus_force()

    def close(self):
        self.app.settings_window = None
        self.win.destroy()
