"""Pomodoro state machine. UI-agnostic; call tick() periodically."""
import time
from datetime import datetime

FOCUS = "focus"
SHORT_BREAK = "short_break"
LONG_BREAK = "long_break"

LABELS = {FOCUS: "Focus", SHORT_BREAK: "Short break", LONG_BREAK: "Long break"}


class PomodoroTimer:
    def __init__(self, settings, unit=60, clock=time.monotonic, now=datetime.now,
                 on_session_end=None, on_phase_change=None):
        """
        settings: dict with focus/short_break/long_break/long_break_every and auto_start_* keys.
        unit: seconds per configured unit (60 = minutes, 1 = demo seconds).
        on_session_end(record: dict): called when a session ends (completed or not).
        on_phase_change(phase, completed: bool): called after moving to the next phase.
        """
        self.settings = settings
        self.unit = unit
        self.clock = clock
        self.now = now
        self.on_session_end = on_session_end
        self.on_phase_change = on_phase_change

        self.phase = FOCUS
        self.round = 0  # focus sessions finished in the current cycle
        self.running = False
        self._elapsed = 0.0        # seconds accumulated before the current run
        self._run_started = None   # monotonic time the current run started
        self._started_at = None    # wall-clock time this session first started

    # ---- queries ----

    def duration(self, phase=None):
        return max(1, int(self.settings[phase or self.phase] * self.unit))

    def elapsed(self):
        extra = self.clock() - self._run_started if self.running else 0.0
        return self._elapsed + extra

    def remaining(self):
        return max(0.0, self.duration() - self.elapsed())

    def progress(self):
        return min(1.0, self.elapsed() / self.duration())

    def is_fresh(self):
        return not self.running and self._elapsed == 0

    # ---- controls ----

    def start(self):
        if self.running:
            return
        if self._started_at is None:
            self._started_at = self.now()
        self._run_started = self.clock()
        self.running = True

    def pause(self):
        if not self.running:
            return
        self._elapsed += self.clock() - self._run_started
        self._run_started = None
        self.running = False

    def toggle(self):
        self.pause() if self.running else self.start()

    def reset(self):
        """Abandon the current session and return to its full duration (stopped)."""
        self._record(completed=False)
        self._clear()

    def skip(self):
        """Abandon the current session and move to the next phase."""
        self._record(completed=False)
        self._advance(completed=False)

    def abandon(self):
        """Record an in-progress session (e.g. on quit)."""
        self._record(completed=False)
        self._clear()

    def full_reset(self):
        """Back to the first focus of a new cycle."""
        self._record(completed=False)
        self._clear()
        self.phase = FOCUS
        self.round = 0

    def tick(self):
        """Advance if the current session has run out. Returns True on a phase change."""
        if self.running and self.elapsed() >= self.duration():
            self._elapsed = float(self.duration())
            self.running = False
            self._record(completed=True)
            self._advance(completed=True)
            return True
        return False

    # ---- internals ----

    def _clear(self):
        self.running = False
        self._elapsed = 0.0
        self._run_started = None
        self._started_at = None

    def _record(self, completed):
        actual = self.elapsed()
        if self._started_at is None or (actual < 1 and not completed):
            return
        if self.on_session_end:
            self.on_session_end({
                "kind": self.phase,
                "planned_sec": self.duration(),
                "actual_sec": round(actual),
                "completed": completed,
                "started_at": self._started_at,
                "ended_at": self.now(),
            })

    def _advance(self, completed):
        finished = self.phase
        self._clear()
        if finished == FOCUS:
            self.round += 1
            every = max(1, int(self.settings["long_break_every"]))
            if self.round >= every:
                self.phase = LONG_BREAK
                self.round = 0
            else:
                self.phase = SHORT_BREAK
        else:
            self.phase = FOCUS

        auto = self.settings["auto_start_focus"] if self.phase == FOCUS else self.settings["auto_start_breaks"]
        if auto:
            self.start()
        if self.on_phase_change:
            self.on_phase_change(self.phase, completed)
