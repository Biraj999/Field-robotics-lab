from pathlib import Path
import unittest
from xml.etree import ElementTree

from canopy import Observation, read_observations, render_svg, triage


class CanopyTests(unittest.TestCase):
    def test_an_oversampled_pass_cannot_outvote_a_second_pass(self):
        observations = [Observation("A1", "morning", 24, 80)] * 9
        observations.append(Observation("A1", "afternoon", 76, 80))

        result, = triage(observations)

        self.assertEqual(result.cover, 50)
        self.assertEqual(result.spread, 52)
        self.assertEqual(result.status, "Conflicting passes")

    def test_blurred_passes_do_not_count_as_support(self):
        result, = triage([Observation("A1", "morning", 14, 60),
                         Observation("A1", "afternoon", 12, 59)])

        self.assertEqual(result.accepted_passes, 1)
        self.assertIsNone(result.spread)
        self.assertEqual(result.status, "More passes needed")

    def test_demo_classifications_and_chart(self):
        path = Path(__file__).with_name("sample.csv")
        results = triage(read_observations(path))

        self.assertEqual([result.plot for result in results], ["A2", "B1", "B2", "B3", "A1", "C1"])
        self.assertEqual([result.status for result in results], [
            "Low cover", "Conflicting passes", "More passes needed",
            "More passes needed", "Stable cover", "Stable cover",
        ])
        self.assertIsNone(results[3].cover)
        svg = render_svg(results, low_cover=40)
        ElementTree.fromstring(svg)
        self.assertEqual(svg, path.with_name("assets").joinpath("preview.svg").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
