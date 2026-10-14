import csv
import os
import shutil
import tempfile
import unittest
from datetime import date, datetime, timedelta

from pomodoro.storage import DEFAULT_SETTINGS, Store, load_settings, save_settings

TODAY = date(2026, 3, 11)


def at(day, hour=9):
    return datetime.combine(day, datetime.min.time()) + timedelta(hours=hour)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.store = Store(os.path.join(self.dir, "test.db"))

    def tearDown(self):
        self.store.close()
        shutil.rmtree(self.dir)

    def add_focus(self, day, completed=True, secs=1500):
        start = at(day)
        self.store.add_session("focus", 1500, secs, completed, start, start + timedelta(seconds=secs))

    def test_daily_focus_counts_completed_and_sums_time(self):
        self.add_focus(TODAY)
        self.add_focus(TODAY)
        self.add_focus(TODAY, completed=False, secs=600)
        self.store.add_session("short_break", 300, 300, True, at(TODAY), at(TODAY))
        days = self.store.daily_focus(TODAY, TODAY)
        self.assertEqual(days[TODAY], (2, 3600))

    def test_completion_rate(self):
        self.assertIsNone(self.store.completion_rate(TODAY, TODAY))
        for completed in (True, True, True, False):
            self.add_focus(TODAY, completed=completed)
        self.assertAlmostEqual(self.store.completion_rate(TODAY, TODAY), 0.75)

    def test_streak_counts_consecutive_goal_days(self):
        for back in (1, 2, 3, 5):  # gap at 4 days ago
            for _ in range(2):
                self.add_focus(TODAY - timedelta(days=back))
        # today not yet met → streak counts from yesterday
        self.assertEqual(self.store.streak(goal=2, today=TODAY), 3)
        self.add_focus(TODAY)
        self.add_focus(TODAY)
        self.assertEqual(self.store.streak(goal=2, today=TODAY), 4)
        self.assertEqual(self.store.streak(goal=3, today=TODAY), 0)

    def test_export_csv(self):
        self.add_focus(TODAY)
        path = os.path.join(self.dir, "out.csv")
        self.assertEqual(self.store.export_csv(path), 1)
        with open(path, encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
        self.assertEqual(rows[0][1], "kind")
        self.assertEqual(rows[1][1], "focus")

    def test_reset_and_seed(self):
        self.store.seed_demo()
        self.assertFalse(self.store.is_empty())
        self.store.reset()
        self.assertTrue(self.store.is_empty())

    def test_settings_roundtrip_ignores_unknown_keys(self):
        s = load_settings(self.dir)
        self.assertEqual(s, DEFAULT_SETTINGS)
        s["focus"] = 50
        s["bogus"] = 1
        save_settings(self.dir, s)
        loaded = load_settings(self.dir)
        self.assertEqual(loaded["focus"], 50)
        self.assertNotIn("bogus", loaded)

    def test_demo_settings_use_second_defaults(self):
        self.assertEqual(load_settings(self.dir, demo=True)["focus"], 20)


if __name__ == "__main__":
    unittest.main()
