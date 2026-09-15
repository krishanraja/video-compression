from __future__ import annotations

import unittest

from video_compression.profiles import infer_profile, quality_for_label
from video_compression.segments import parse_time


class ProfileTests(unittest.TestCase):
    def test_infers_common_purposes(self) -> None:
        self.assertEqual(infer_profile("send on WhatsApp").name, "share")
        self.assertEqual(infer_profile("YouTube upload").name, "social")
        self.assertEqual(infer_profile("must play anywhere").name, "universal")

    def test_quality_labels_move_in_expected_direction(self) -> None:
        self.assertLess(quality_for_label(24, "high"), quality_for_label(24, "balanced"))
        self.assertGreater(quality_for_label(24, "small"), quality_for_label(24, "balanced"))


class TimeTests(unittest.TestCase):
    def test_parses_seconds_and_clock_values(self) -> None:
        self.assertEqual(parse_time(4.5), 4.5)
        self.assertEqual(parse_time("01:02"), 62.0)
        self.assertEqual(parse_time("01:02:03.5"), 3723.5)


if __name__ == "__main__":
    unittest.main()

