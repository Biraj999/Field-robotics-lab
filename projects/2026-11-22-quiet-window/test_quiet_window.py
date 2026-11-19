import itertools
from pathlib import Path
import unittest

from quiet_window import Reminder, plan, read_reminders


class QuietWindowTests(unittest.TestCase):
    def test_fixture(self):
        fixture = Path(__file__).with_name("reminders.csv")
        reminders = read_reminders(fixture)
        batches = plan(reminders)
        self.assertEqual([minute for minute, _ in batches], [8, 15, 20])
        self.assertCountEqual([item for _, items in batches for item in items], reminders)
        for minute, items in batches:
            self.assertTrue(all(item.ready <= minute <= item.due for item in items))

    def test_minimum_count_against_exhaustive_search(self):
        windows = list(itertools.combinations_with_replacement(range(4), 2))
        for sample in itertools.combinations_with_replacement(windows, 3):
            reminders = [Reminder(str(i), start, end)
                         for i, (start, end) in enumerate(sample)]
            optimal = next(size for size in range(1, 4) if any(
                all(any(start <= minute <= end for minute in choice)
                    for start, end in sample)
                for choice in itertools.combinations(range(4), size)
            ))
            self.assertEqual(len(plan(reminders)), optimal, sample)
