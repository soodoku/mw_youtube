import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import collect_candidates as collect  # noqa: E402
from expand_keywords import freeze  # noqa: E402
from sample_videos import choose, key  # noqa: E402

from mw_youtube import plan_searches, read_frames  # noqa: E402
from mw_youtube.records import read  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data/delhi_2025_street_food"


class Contracts(unittest.TestCase):
    def test_keywords_frozen_before_planning(self):
        packet = dict(
            city="delhi",
            topic="new_food",
            description="Food stalls",
            keywords=[
                dict(
                    keyword_id="en_stall",
                    language="en",
                    concept="stall",
                    phrase="{city} stall",
                ),
                dict(
                    keyword_id="hi_stall",
                    language="hi",
                    concept="stall",
                    phrase="{city} ठेला",
                ),
            ],
        )
        with self.assertRaises(ValueError):
            list(plan_searches("delhi", 2025, "new_food", vocabulary=packet))
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "draft.json"
            dest = Path(tmp) / "reviewed.json"
            src.write_text(json.dumps(packet))
            freeze(src, dest, "reviewer")
            rows = list(
                plan_searches(
                    "delhi", 2025, "new_food", vocabulary=json.loads(dest.read_text())
                )
            )
            self.assertEqual(len({r["search_id"] for r in rows}), 24)
            packet["keywords"][1]["keyword_id"] = "en_stall"
            src.write_text(json.dumps(packet))
            with self.assertRaises(ValueError):
                freeze(src, Path(tmp) / "bad.json", "reviewer")

    def test_snapshot_and_verified_selection(self):
        plan = list(plan_searches("delhi", 2025, "street_food"))
        with patch.object(
            collect, "urlopen", side_effect=AssertionError("Unexpected API call")
        ):
            self.assertEqual(collect.collect(SNAPSHOT, plan)["candidates"], 1205)
        selected = read(SNAPSHOT / "selected_1.csv")
        with self.assertRaisesRegex(ValueError, "footage confirmation"):
            choose(selected, selected, 1, set())
        self.assertEqual(
            choose(selected, selected, 1, {key(selected[0])})[0]["video_id"],
            selected[0]["video_id"],
        )

    def test_pilot_typed_primary_counts(self):
        path = next((SNAPSHOT / "analysis/pilot1/muse").glob("*_frames.csv"))
        rows = read_frames(path)
        self.assertEqual(len(rows), 6)
        self.assertAlmostEqual(sum(r["within_video_weight"] for r in rows), 1)
        self.assertEqual(
            [
                sum(r[k] for r in rows)
                for k in (
                    "primary_n_women",
                    "primary_n_men",
                    "primary_n_gender_unclear",
                )
            ],
            [0, 2, 1],
        )
        self.assertEqual(len({r["channel_id"] for r in rows}), 1)
