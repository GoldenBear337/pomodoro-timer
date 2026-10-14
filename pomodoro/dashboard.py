"""Lightweight productivity dashboard drawn on a Tk canvas (no plotting libraries)."""
import tkinter as tk
from datetime import date, timedelta

BG = "#f6f6f8"
CARD = "#ffffff"
TEXT = "#1d1d22"
MUTED = "#7a7a85"
ACCENT = "#ff5f57"
ACCENT_SOFT = "#ffc9c5"
GOAL = "#2b2b33"
GRID = "#e6e6ea"
GOOD = "#2f9e5a"

W, H = 620, 470


def _fmt_minutes(secs):
    m = int(round(secs / 60))
    return f"{m // 60}h {m % 60:02d}m" if m >= 60 else f"{m}m"


class Dashboard:
    def __init__(self, app):
        self.app = app
        self.win = tk.Toplevel(app.root)
        self.win.title("Pomodoro — Dashboard" + (" [DEMO]" if app.demo else ""))
        self.win.configure(bg=BG)
        self.win.resizable(False, False)
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self.canvas = tk.Canvas(self.win, width=W, height=H, bg=BG, highlightthickness=0)
        self.canvas.pack()
        self.refresh()

    def refresh(self):
        store = self.app.store
        goal = int(self.app.settings["daily_goal"])
        focus_len = int(self.app.settings["focus"]) * self.app.unit
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        days = store.daily_focus(today - timedelta(days=6), today)
        week = store.daily_focus(week_start, today)

        today_count, today_secs = days.get(today, (0, 0))
        week_count = sum(v[0] for v in week.values())
        week_secs = sum(v[1] for v in week.values())
        rate = store.completion_rate(today - timedelta(days=6), today)
        streak = store.streak(goal, today)

        c = self.canvas
        c.delete("all")
        c.create_text(24, 22, anchor="w", text="Productivity", font=("Segoe UI Semibold", 15), fill=TEXT)
        c.create_text(W - 24, 22, anchor="e", text=today.strftime("%a %d %b %Y"), font=("Segoe UI", 10), fill=MUTED)

        # --- stat cards ---
        cards = [
            ("Today", f"{today_count}/{goal}", f"{_fmt_minutes(today_secs)} focused"),
            ("This week", str(week_count), f"{_fmt_minutes(week_secs)} focused"),
            ("Streak", f"{streak} day{'s' if streak != 1 else ''}", "reaching daily goal"),
            ("Completion", "—" if rate is None else f"{rate:.0%}", "finished vs started, 7d"),
        ]
        gap, x, y, ch = 12, 24, 46, 92
        cw = (W - 48 - gap * 3) / 4
        for i, (title, value, sub) in enumerate(cards):
            x0 = x + i * (cw + gap)
            self._card(x0, y, x0 + cw, y + ch)
            c.create_text(x0 + 14, y + 18, anchor="w", text=title, font=("Segoe UI", 9), fill=MUTED)
            color = GOOD if (i == 0 and today_count >= goal) else TEXT
            c.create_text(x0 + 14, y + 46, anchor="w", text=value, font=("Segoe UI Semibold", 18), fill=color)
            c.create_text(x0 + 14, y + 74, anchor="w", text=sub, font=("Segoe UI", 8), fill=MUTED)

        # today's goal progress bar
        py = y + ch + 18
        c.create_text(24, py, anchor="w", text="Today's goal", font=("Segoe UI", 9), fill=MUTED)
        bx0, bx1 = 110, W - 24
        c.create_rectangle(bx0, py - 5, bx1, py + 5, fill=GRID, outline="")
        frac = min(1.0, today_count / max(goal, 1))
        if frac > 0:
            c.create_rectangle(bx0, py - 5, bx0 + (bx1 - bx0) * frac, py + 5,
                               fill=GOOD if frac >= 1 else ACCENT, outline="")

        # --- 7-day bar chart (completed pomodoros per day) ---
        top = py + 26
        self._card(24, top, W - 24, H - 46)
        c.create_text(40, top + 18, anchor="w", text="Last 7 days — completed pomodoros",
                      font=("Segoe UI Semibold", 10), fill=TEXT)
        cx0, cx1 = 56, W - 44
        cy0, cy1 = top + 42, H - 80
        values = [(today - timedelta(days=6 - i)) for i in range(7)]
        counts = [days.get(d, (0, 0))[0] for d in values]
        ymax = max(max(counts), goal, 1)
        ymax = ymax + (1 if ymax % 2 else 2)
        scale = lambda v: cy1 - (cy1 - cy0) * v / ymax

        for tick in range(0, ymax + 1, max(1, ymax // 4)):
            yy = scale(tick)
            c.create_line(cx0, yy, cx1, yy, fill=GRID)
            c.create_text(cx0 - 8, yy, anchor="e", text=str(tick), font=("Segoe UI", 8), fill=MUTED)

        slot = (cx1 - cx0) / 7
        bw = slot * 0.5
        for i, (d, n) in enumerate(zip(values, counts)):
            mx = cx0 + slot * (i + 0.5)
            fill = ACCENT if d == today else ACCENT_SOFT
            if n:
                c.create_rectangle(mx - bw / 2, scale(n), mx + bw / 2, cy1, fill=fill, outline="")
                c.create_text(mx, scale(n) - 8, text=str(n), font=("Segoe UI", 8), fill=TEXT)
            label = "Today" if d == today else d.strftime("%a")
            c.create_text(mx, cy1 + 12, text=label, font=("Segoe UI", 8, "bold" if d == today else "normal"),
                          fill=TEXT if d == today else MUTED)

        gy = scale(goal)
        c.create_line(cx0, gy, cx1, gy, fill=GOAL, dash=(4, 3))
        c.create_text(cx1, gy - 3, anchor="se", text=f"goal {goal}", font=("Segoe UI", 8), fill=GOAL)

        # footer buttons
        self._button(W - 24, H - 22, "Refresh", self.refresh)
        unit = "sec" if self.app.demo else "min"
        c.create_text(24, H - 22, anchor="w", font=("Segoe UI", 8), fill=MUTED,
                      text=f"Focus length {self.app.settings['focus']} {unit} · goal {goal}/day "
                           f"(≈{_fmt_minutes(goal * focus_len)})")

    def _card(self, x0, y0, x1, y1):
        self.canvas.create_rectangle(x0, y0, x1, y1, fill=CARD, outline=GRID)

    def _button(self, x_right, y, label, command):
        c = self.canvas
        t = c.create_text(x_right - 12, y, anchor="e", text=label, font=("Segoe UI", 9), fill=TEXT, tags="btn")
        x0, y0, x1, y1 = c.bbox(t)
        r = c.create_rectangle(x0 - 12, y0 - 4, x1 + 12, y1 + 4, fill=CARD, outline=GRID, tags="btn")
        c.tag_raise(t)
        for item in (t, r):
            c.tag_bind(item, "<Button-1>", lambda _e: command())
        c.tag_bind(r, "<Enter>", lambda _e: c.config(cursor="hand2"))
        c.tag_bind(r, "<Leave>", lambda _e: c.config(cursor=""))

    def show(self):
        self.refresh()
        self.win.deiconify()
        self.win.lift()
        self.win.focus_force()

    def close(self):
        self.app.dashboard = None
        self.win.destroy()
