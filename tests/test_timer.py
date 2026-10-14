import unittest
from datetime import datetime, timedelta

from pomodoro.timer import FOCUS, LONG_BREAK, SHORT_BREAK, PomodoroTimer


class FakeClock:
    def __init__(self):
        self.t = 0.0
        self.start = datetime(2026, 1, 5, 9, 0, 0)

    def __call__(self):
        return self.t

    def now(self):
        return self.start + timedelta(seconds=self.t)

    def advance(self, secs):
        self.t += secs


def make(**overrides):
    settings = {"focus": 25, "short_break": 5, "long_break": 15, "long_break_every": 4,
                "auto_start_breaks": False, "auto_start_focus": False}
    settings.update(overrides)
    clock = FakeClock()
    records, phases = [], []
    timer = PomodoroTimer(settings, unit=60, clock=clock, now=clock.now,
                          on_session_end=records.append,
                          on_phase_change=lambda p, c: phases.append((p, c)))
    return timer, clock, records, phases


class TimerTests(unittest.TestCase):
    def test_counts_down_and_completes_focus(self):
        timer, clock, records, phases = make()
        timer.start()
        clock.advance(10 * 60)
        self.assertAlmostEqual(timer.remaining(), 15 * 60)
        self.assertFalse(timer.tick())
        clock.advance(15 * 60)
        self.assertTrue(timer.tick())
        self.assertEqual(timer.phase, SHORT_BREAK)
        self.assertFalse(timer.running)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["kind"], FOCUS)
        self.assertTrue(records[0]["completed"])
        self.assertEqual(records[0]["actual_sec"], 25 * 60)
        self.assertEqual(phases, [(SHORT_BREAK, True)])

    def test_pause_freezes_time(self):
        timer, clock, _, _ = make()
        timer.start()
        clock.advance(60)
        timer.pause()
        clock.advance(600)
        self.assertAlmostEqual(timer.remaining(), 24 * 60)
        timer.start()
        clock.advance(60)
        self.assertAlmostEqual(timer.remaining(), 23 * 60)

    def test_long_break_every_n_rounds(self):
        timer, clock, _, _ = make(long_break_every=2)
        seen = []
        for _ in range(4):
            timer.start()
            clock.advance(timer.duration())
            timer.tick()
            seen.append(timer.phase)
        self.assertEqual(seen, [SHORT_BREAK, FOCUS, LONG_BREAK, FOCUS])

    def test_skip_records_incomplete_and_advances(self):
        timer, clock, records, _ = make()
        timer.start()
        clock.advance(300)
        timer.skip()
        self.assertEqual(timer.phase, SHORT_BREAK)
        self.assertEqual(len(records), 1)
        self.assertFalse(records[0]["completed"])
        self.assertEqual(records[0]["actual_sec"], 300)

    def test_reset_keeps_phase_and_records_partial(self):
        timer, clock, records, _ = make()
        timer.start()
        clock.advance(120)
        timer.reset()
        self.assertEqual(timer.phase, FOCUS)
        self.assertTrue(timer.is_fresh())
        self.assertEqual(timer.remaining(), 25 * 60)
        self.assertEqual(len(records), 1)

    def test_reset_unstarted_records_nothing(self):
        timer, _, records, _ = make()
        timer.reset()
        timer.skip()
        self.assertEqual(records, [])

    def test_auto_start_breaks(self):
        timer, clock, _, _ = make(auto_start_breaks=True)
        timer.start()
        clock.advance(25 * 60)
        timer.tick()
        self.assertEqual(timer.phase, SHORT_BREAK)
        self.assertTrue(timer.running)
        clock.advance(5 * 60)
        timer.tick()
        self.assertEqual(timer.phase, FOCUS)
        self.assertFalse(timer.running)  # auto_start_focus is off

    def test_demo_unit_seconds(self):
        timer, clock, _, _ = make(focus=20)
        timer.unit = 1
        timer.start()
        clock.advance(20)
        self.assertTrue(timer.tick())


if __name__ == "__main__":
    unittest.main()
