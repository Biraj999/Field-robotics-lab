import json
import math
from pathlib import Path
import unittest

from replay import Drive, calibrate, replay, rms_error


class ReplayTests(unittest.TestCase):
    def test_constant_curvature_arc(self):
        points = replay([(0, 1)], Drive(1, math.pi, 2))
        self.assertAlmostEqual(points[-1][0], 1)
        self.assertAlmostEqual(points[-1][1], 1)

    def test_held_out_route_with_corrupted_training_trial(self):
        data = json.loads(Path(__file__).with_name("fixture.json").read_text())
        nominal = replay(data["replay"], Drive(*data["nominal"]))
        fitted = replay(data["replay"], calibrate(data["straight"], data["turn"]))
        self.assertGreater(rms_error(nominal, data["reference_xy"]), 0.09)
        self.assertLess(rms_error(fitted, data["reference_xy"]), 0.01)
