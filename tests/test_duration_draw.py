import sys
import unittest
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from sample_frames import draw  # noqa: E402

from mw_youtube import frames_per_third  # noqa: E402


class DurationAllocation(unittest.TestCase):
    def test_boundaries_and_nested_frame_ranks(self):
        for seconds, expected in [
            (5, 3),
            (180, 3),
            (Fraction(180001, 1000), 6),
            (563, 12),
            (978, 18),
            (1800, 30),
            (34000, 30),
        ]:
            self.assertEqual(3 * frames_per_third(seconds), expected)
        t = Fraction(563261, 1000)
        bigger = draw("ZmBfCcLxi2c", "20261121", t, frames_per_third(t))
        old = draw("ZmBfCcLxi2c", "20261121", t, 2)
        self.assertEqual(old, [r for r in bigger if r["rank"] <= 2])
