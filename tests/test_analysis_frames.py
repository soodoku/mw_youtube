import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_analysis_frames import build  # noqa: E402
from prepare_frame_review import table  # noqa: E402


class AnalysisFrameTests(unittest.TestCase):
    def test_many_search_hits_one_frame_per_moment_and_missing_video_retained(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            selected = folder / "selected_3.csv"
            ids = ("first", "second", "unavailable")
            picks = [
                dict(
                    video_id=v,
                    channel_id="same-channel",
                    city="delhi",
                    video_rank=i,
                    sample_seed="10",
                    place="Market",
                )
                for i, v in enumerate(ids, 1)
            ]
            table(selected, picks, list(picks[0]))
            rows = [
                dict(
                    **p,
                    published_utc="2025-05-01",
                    recording_date=None,
                    audio_language=None,
                    view_count=10,
                    retrieved_utc="2026-11-21",
                    watch_url="https://www.youtube.com/watch?v=" + p["video_id"],
                )
                for p in picks
            ]
            (folder / "video_metadata.jsonl").write_text(
                "".join(json.dumps(r) + "\n" for r in rows)
            )
            (folder / "result.json").write_text(
                json.dumps(dict(year=2025, topic="street_food"))
            )
            (folder / "queries.json").write_text("[]")
            (folder / "search_counts.csv").write_text("search_id\n")
            hits = [
                dict(search_id=q, video_id=v) for v in ids for q in ("English", "Hindi")
            ]
            table(folder / "search_hits.csv", hits, list(hits[0]))
            for vid in ids[:2]:
                dest = folder / "frames" / vid
                dest.mkdir(parents=True)
                plan = dict(
                    video_id=vid,
                    duration="1",
                    seed="10",
                    per_interval=1,
                    first_time="0",
                    source_sha256=vid,
                    moments=[
                        dict(interval=i, rank=1, requested_ms=m)
                        for i, m in enumerate((100, 500, 900))
                    ],
                )
                (dest / "plan.json").write_text(json.dumps(plan))
            frames, coverage, routes = build(folder, selected, [], "muse")
            self.assertEqual((len(frames), len(coverage), len(routes)), (6, 3, 6))
            self.assertEqual(len({r["channel_id"] for r in frames}), 1)
            self.assertEqual(len({r["frame_id"] for r in frames}), 6)
            self.assertTrue(
                all(r["coded"] == 0 and r["primary_n_women"] is None for r in frames)
            )
            self.assertAlmostEqual(sum(r["within_video_weight"] for r in frames), 2)
            self.assertEqual(coverage[-1]["planned_moments"], 0)
