import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import collect_candidates as collect  # noqa: E402
import sample_videos as sample  # noqa: E402


class TestPipeline(unittest.TestCase):
    def test_draw(self):
        rows = [dict(city="delhi", video_id=str(i)) for i in range(8)]
        queue = sample.rank(rows, sample.SEED)
        self.assertEqual(queue, sample.rank(rows[::-1], sample.SEED))
        reviews = [
            {
                **r,
                "decision": "eligible",
                "place": "test",
                "evidence": "marker",
                "reason": "qualifies",
                "reviewer": "A",
                "review_date": "2026-11-21",
            }
            for r in queue
        ]
        reviews[1]["decision"] = "excluded"
        self.assertEqual(
            [r["video_rank"] for r in sample.choose(queue, reviews, 3)], [1, 3, 4]
        )
        reviews[2]["decision"] = "unclear"
        with self.assertRaisesRegex(ValueError, "resolve rank 3"):
            sample.choose(queue, reviews, 3)

    def test_collect_and_resume(self):
        plan = list(collect.searches("delhi", 2025, "street_food"))
        self.assertEqual(len({r["search_id"] for r in plan}), 72)
        test_plan = plan[:3]
        item = {
            "id": {"videoId": "fixture"},
            "snippet": {
                "title": "fixture",
                "channelId": "test",
                "publishedAt": "2025-01-02T00:00:00Z",
            },
        }

        def response(items):
            import io

            return io.BytesIO(json.dumps({"items": items}).encode())

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            with patch.dict("os.environ", YOUTUBE_API_KEY="fixture"):
                with patch.object(
                    collect,
                    "urlopen",
                    side_effect=[response([item]), response([]), OSError("interrupt")],
                ):
                    with self.assertRaises(OSError):
                        collect.collect(folder, test_plan)
                with patch.object(
                    collect, "urlopen", side_effect=[response([item]), response([])]
                ) as network:
                    collect.collect(folder, test_plan)
                    self.assertEqual(network.call_count, 2)
                with patch.object(collect, "urlopen", side_effect=AssertionError):
                    collect.collect(folder, test_plan)
            with (folder / "candidates.csv").open() as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["metadata_status"], "unavailable")
