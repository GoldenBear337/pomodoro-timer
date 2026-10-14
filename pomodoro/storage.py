"""Local persistence: settings.json + pomodoro.db (SQLite) under %APPDATA%\\PomodoroTimer."""
import csv
import json
import os
import random
import sqlite3
from datetime import date, datetime, timedelta

APP_NAME = "PomodoroTimer"
TS_FORMAT = "%Y-%m-%d %H:%M:%S"

DEFAULT_SETTINGS = {
    # Timer (minutes; seconds in demo mode)
    "focus": 25,
    "short_break": 5,
    "long_break": 15,
    "long_break_every": 4,
    "daily_goal": 8,
    # Behaviour
    "auto_start_breaks": True,
    "auto_start_focus": False,
    "sound": True,
    "notifications": True,
    "hotkey": True,
    # Clock appearance
    "clock_visible": True,
    "clock_x": None,
    "clock_y": None,
    "opacity": 0.85,
    "font_family": "Segoe UI Light",
    "font_size": 40,
    "text_color": "#ffffff",
    "show_progress": True,
    "show_mode_dot": True,
    "dark_background": False,
    "always_on_top": True,
    "click_through": False,
}

DEMO_OVERRIDES = {"focus": 20, "short_break": 5, "long_break": 10, "long_break_every": 2}


def app_dir(demo=False):
    base = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), APP_NAME)
    path = os.path.join(base, "demo") if demo else base
    os.makedirs(path, exist_ok=True)
    return path


def load_settings(folder, demo=False):
    settings = dict(DEFAULT_SETTINGS)
    if demo:
        settings.update(DEMO_OVERRIDES)
    path = os.path.join(folder, "settings.json")
    try:
        with open(path, encoding="utf-8") as f:
            saved = json.load(f)
        settings.update({k: v for k, v in saved.items() if k in DEFAULT_SETTINGS})
    except (OSError, ValueError):
        pass
    return settings


def save_settings(folder, settings):
    path = os.path.join(folder, "settings.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


class Store:
    """Session history. One row per focus/break session."""

    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                planned_sec INTEGER NOT NULL,
                actual_sec INTEGER NOT NULL,
                completed INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT NOT NULL
            )"""
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_started ON sessions(started_at)")
        self.conn.commit()

    def close(self):
        self.conn.close()

    def is_empty(self):
        return self.conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0

    def add_session(self, kind, planned_sec, actual_sec, completed, started_at, ended_at):
        self.conn.execute(
            "INSERT INTO sessions (kind, planned_sec, actual_sec, completed, started_at, ended_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (kind, int(planned_sec), int(actual_sec), int(bool(completed)),
             started_at.strftime(TS_FORMAT), ended_at.strftime(TS_FORMAT)),
        )
        self.conn.commit()

    def reset(self):
        self.conn.execute("DELETE FROM sessions")
        self.conn.commit()

    # ---- stats (focus sessions only) ----

    def daily_focus(self, start, end):
        """{date: (completed_count, focus_seconds)} for start..end inclusive."""
        rows = self.conn.execute(
            "SELECT substr(started_at, 1, 10) AS d, SUM(completed), SUM(actual_sec)"
            " FROM sessions WHERE kind = 'focus' AND d BETWEEN ? AND ? GROUP BY d",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        result = {}
        for d, count, secs in rows:
            result[date.fromisoformat(d)] = (count or 0, secs or 0)
        return result

    def completion_rate(self, start, end):
        """Completed focus sessions / started focus sessions, or None if none started."""
        done, total = self.conn.execute(
            "SELECT SUM(completed), COUNT(*) FROM sessions"
            " WHERE kind = 'focus' AND substr(started_at, 1, 10) BETWEEN ? AND ?",
            (start.isoformat(), end.isoformat()),
        ).fetchone()
        return (done or 0) / total if total else None

    def streak(self, goal, today=None):
        """Consecutive days (ending today, or yesterday if today isn't met yet) reaching the goal."""
        today = today or date.today()
        days = self.daily_focus(today - timedelta(days=366), today)
        met = lambda d: days.get(d, (0, 0))[0] >= max(goal, 1)
        day = today if met(today) else today - timedelta(days=1)
        count = 0
        while met(day):
            count += 1
            day -= timedelta(days=1)
        return count

    def export_csv(self, path):
        rows = self.conn.execute(
            "SELECT id, kind, planned_sec, actual_sec, completed, started_at, ended_at"
            " FROM sessions ORDER BY started_at"
        ).fetchall()
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "kind", "planned_sec", "actual_sec", "completed", "started_at", "ended_at"])
            writer.writerows(rows)
        return len(rows)

    def seed_demo(self, days=14, focus_min=25, seed=7):
        """Fill with plausible sample history so the dashboard has something to show."""
        rng = random.Random(seed)
        today = date.today()
        for back in range(days, 0, -1):
            day = today - timedelta(days=back)
            if day.weekday() >= 5 and rng.random() < 0.6:
                continue
            t = datetime.combine(day, datetime.min.time()) + timedelta(hours=9, minutes=rng.randint(0, 40))
            for _ in range(rng.randint(4, 11)):
                completed = rng.random() > 0.12
                actual = focus_min * 60 if completed else rng.randint(3, focus_min - 2) * 60
                self.add_session("focus", focus_min * 60, actual, completed, t, t + timedelta(seconds=actual))
                t += timedelta(seconds=actual + 5 * 60 + rng.randint(0, 20) * 60)
