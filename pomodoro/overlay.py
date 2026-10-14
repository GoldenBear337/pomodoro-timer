"""Minimal transparent clock: just the digits floating on the desktop."""
import tkinter as tk
import tkinter.font as tkfont

from . import winutil
from .tray import MODE_COLORS

KEY_COLOR = "#010203"   # painted pixels in this colour become fully transparent
HOVER_BG = "#1c1c1f"    # shown while the mouse is over the clock so controls are clickable
DARK_BG = "#141416"


def _mix(hex_a, hex_b, t):
    a = [int(hex_a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(hex_b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


class ClockOverlay:
    def __init__(self, app, demo=False):
        self.app = app
        self.demo = demo
        self.win = tk.Toplevel(app.root)
        self.win.withdraw()
        self.win.overrideredirect(True)
        self.win.attributes("-transparentcolor", KEY_COLOR)
        self.canvas = tk.Canvas(self.win, highlightthickness=0, bd=0, bg=KEY_COLOR)
        self.canvas.pack(fill="both", expand=True)

        self._hover = False
        self._leave_job = None
        self._drag = None
        self._last_text = None

        c = self.canvas
        c.bind("<ButtonPress-1>", self._on_press)
        c.bind("<B1-Motion>", self._on_motion)
        c.bind("<ButtonRelease-1>", self._on_release)
        c.bind("<Double-Button-1>", self._on_double)
        c.bind("<Button-3>", self._on_menu)
        c.bind("<Enter>", self._on_enter)
        c.bind("<Leave>", self._on_leave)

        self.menu = tk.Menu(self.win, tearoff=0)
        self.menu.add_command(label="Start / Pause", command=app.toggle)
        self.menu.add_command(label="Skip", command=app.skip)
        self.menu.add_command(label="Reset", command=app.reset)
        self.menu.add_separator()
        self.menu.add_command(label="Dashboard", command=app.open_dashboard)
        self.menu.add_command(label="Settings", command=app.open_settings)
        self.menu.add_command(label="Click-through (toggle off from tray)", command=app.toggle_click_through)
        self.menu.add_separator()
        self.menu.add_command(label="Hide clock", command=app.toggle_clock)
        self.menu.add_command(label="Quit", command=app.quit)

        self.apply_settings()

    # ---- layout ----

    def apply_settings(self):
        s = self.app.settings
        self.time_font = tkfont.Font(family=s["font_family"], size=int(s["font_size"]))
        self.small_font = tkfont.Font(family="Segoe UI", size=max(8, int(s["font_size"]) // 5))
        self.ctrl_font = tkfont.Font(family="Segoe UI Symbol", size=max(9, int(s["font_size"]) // 4))
        pad = max(8, int(s["font_size"]) // 4)
        self.pad = pad
        self.text_w = self.time_font.measure("00:00")
        self.text_h = self.time_font.metrics("linespace")
        self.ctrl_h = self.ctrl_font.metrics("linespace") + 4
        self.w = self.text_w + pad * 2
        self.h = self.text_h + pad + 10 + self.ctrl_h
        self.canvas.config(width=self.w, height=self.h)

        self.win.attributes("-alpha", float(s["opacity"]))
        self.win.attributes("-topmost", bool(s["always_on_top"]))

        x, y = s["clock_x"], s["clock_y"]
        sw, sh = self.win.winfo_screenwidth(), self.win.winfo_screenheight()
        if x is None or y is None or not (-self.w < x < sw and -self.h < y < sh):
            x, y = sw - self.w - 40, 40
        self.win.geometry(f"{self.w}x{self.h}+{int(x)}+{int(y)}")
        self._last_text = None
        self.redraw()
        if s["clock_visible"]:
            self.show()
        winutil.set_click_through(self.win, bool(s["click_through"]))

    def show(self):
        self.win.deiconify()
        self.win.lift()

    def hide(self):
        self.win.withdraw()

    # ---- drawing ----

    def update(self):
        t = self.app.timer
        secs = int(t.remaining() + 0.999)
        key = (secs, t.running, t.phase, self._hover, round(t.progress() * self.text_w))
        if key != self._last_text:
            self._last_text = key
            self.redraw()

    def redraw(self):
        s = self.app.settings
        t = self.app.timer
        c = self.canvas
        c.delete("all")
        bg = HOVER_BG if self._hover else (DARK_BG if s["dark_background"] else KEY_COLOR)
        c.config(bg=bg)

        secs = int(t.remaining() + 0.999)
        text = f"{secs // 60:02d}:{secs % 60:02d}"
        color = s["text_color"]
        if not t.running:
            color = _mix(color, "#808080", 0.45)
        pad = self.pad
        c.create_text(self.w // 2, pad // 2 + self.text_h // 2, text=text, font=self.time_font, fill=color)

        mode = MODE_COLORS[t.phase]
        bar_y = pad // 2 + self.text_h + 4
        if s["show_mode_dot"]:
            r = 3
            c.create_oval(pad - r - 4, bar_y - r, pad + r - 4, bar_y + r, fill=mode, outline=mode)
        if s["show_progress"] and not t.is_fresh():
            x0 = pad + 4
            x1 = self.w - pad
            c.create_line(x0, bar_y, x1, bar_y, fill=_mix(mode, "#202020", 0.7), width=2)
            c.create_line(x0, bar_y, x0 + (x1 - x0) * t.progress(), bar_y, fill=mode, width=2)
        if self.demo:
            c.create_text(4, 2, text="DEMO", anchor="nw", font=self.small_font, fill="#ffcc00")

        if self._hover:
            cy = bar_y + 6 + self.ctrl_h // 2
            icons = [("⏸" if t.running else "▶", "toggle"), ("⏭", "skip"), ("⟲", "reset"), ("⚙", "settings")]
            step = self.w / (len(icons) + 1)
            for i, (glyph, tag) in enumerate(icons, start=1):
                c.create_text(step * i, cy, text=glyph, font=self.ctrl_font, fill="#e8e8ea",
                              activefill="#ffffff", tags=("ctrl", tag))

    # ---- interaction ----

    def _ctrl_at(self, event):
        for item in self.canvas.find_overlapping(event.x - 2, event.y - 2, event.x + 2, event.y + 2):
            tags = self.canvas.gettags(item)
            if "ctrl" in tags:
                return next(t for t in tags if t not in ("ctrl", "current"))
        return None

    def _on_press(self, event):
        self._drag = (event.x_root, event.y_root, self.win.winfo_x(), self.win.winfo_y(), False)

    def _on_motion(self, event):
        if not self._drag:
            return
        x0, y0, wx, wy, moved = self._drag
        dx, dy = event.x_root - x0, event.y_root - y0
        if moved or abs(dx) + abs(dy) > 3:
            self._drag = (x0, y0, wx, wy, True)
            self.win.geometry(f"+{wx + dx}+{wy + dy}")

    def _on_release(self, event):
        drag, self._drag = self._drag, None
        if drag and drag[4]:
            self.app.settings["clock_x"] = self.win.winfo_x()
            self.app.settings["clock_y"] = self.win.winfo_y()
            self.app.save_settings()
            return
        action = self._ctrl_at(event)
        if action == "toggle":
            self.app.toggle()
        elif action == "skip":
            self.app.skip()
        elif action == "reset":
            self.app.reset()
        elif action == "settings":
            self.app.open_settings()

    def _on_double(self, event):
        if self._ctrl_at(event) is None:
            self.app.toggle()

    def _on_menu(self, event):
        self.menu.tk_popup(event.x_root, event.y_root)

    def _on_enter(self, _event):
        if self._leave_job:
            self.win.after_cancel(self._leave_job)
            self._leave_job = None
        if not self._hover:
            self._hover = True
            self.redraw()

    def _on_leave(self, _event):
        if self._leave_job:
            self.win.after_cancel(self._leave_job)
        self._leave_job = self.win.after(600, self._end_hover)

    def _end_hover(self):
        self._leave_job = None
        self._hover = False
        self.redraw()
