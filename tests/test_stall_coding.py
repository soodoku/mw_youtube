import csv
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prepare_frame_review import run, table  # noqa: E402
from summarize_stall_frames import summarize  # noqa: E402

from mw_youtube.codebook import BOOK, FRAME, PERSON, schema, validate  # noqa: E402


class FrameCodingTests(unittest.TestCase):
    def test_review_sheet_survives_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            img = root / "frame.jpg"
            img.write_bytes(b"frozen")
            moment = {"interval": 0, "rank": 1, "requested_ms": 111}
            plan = root / "plan.json"
            plan.write_text(
                json.dumps({"video_id": "fixture0001", "moments": [moment]})
            )
            item = {
                **moment,
                "sha256": hashlib.sha256(img.read_bytes()).hexdigest(),
                "file": img.name,
            }
            (root / "complete.json").write_text(
                json.dumps(
                    {
                        "plan_sha256": hashlib.sha256(plan.read_bytes()).hexdigest(),
                        "frames": [item],
                    }
                )
            )
            dest = root / "coding"
            run(root, dest)
            sheet = dest / "human_frames.csv"
            with sheet.open(newline="") as f:
                row = next(csv.DictReader(f))
            self.assertEqual(row["quality"], "")
            row["evidence"] = "Independent reviewer entry"
            table(sheet, [row], list(row))
            run(root, dest)
            self.assertIn(row["evidence"], sheet.read_text())
            img.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "Changed image"):
                run(root, dest)

    def test_role_counts_and_closed_categories(self):
        key = {"video_id": "fixture", "interval": 0, "rank": 1}
        frame = {
            **key,
            "quality": "countable",
            "n_enumerated": 4,
            "setting": "street_stall",
            "shot": "people_and_surroundings",
            "service_area": "customer_side",
            "evidence": "Counter opens onto street",
        }
        people = [
            {
                **key,
                "person_id": i,
                "group": g,
                "role": r,
                "activity": "standing_sitting",
                "cue": "visible",
            }
            for i, (g, r) in enumerate(
                [
                    ("woman", "worker"),
                    ("man", "patron"),
                    ("woman", "patron"),
                    ("woman", "other"),
                ],
                1,
            )
        ]
        result = {
            r["scope"]: (r["n_women"], r["n_men"]) for r in summarize([frame], people)
        }
        self.assertEqual(result["worker_and_patron"], (2, 1))
        self.assertEqual(result["all_visible"], (3, 1))
        for field in FRAME:
            with self.subTest(field=field), self.assertRaises(ValueError):
                summarize([{**frame, field: "unlisted_label"}], people)
        for field in PERSON:
            with self.subTest(field=field), self.assertRaises(ValueError):
                summarize([frame], [{**p, field: "unlisted_label"} for p in people])
        self.assertEqual(summarize([{**frame, "n_enumerated": 0}], [])[0]["n_women"], 0)
        self.assertIsNone(
            summarize([{**frame, "quality": "partial"}], people)[0]["n_men"]
        )
        with self.assertRaises(ValueError):
            validate({**frame, "n_enumerated": 1, "sightings": people})

    def test_dictionary_is_response_contract(self):
        sc = schema()["properties"]
        for field in FRAME:
            self.assertEqual(sc[field]["enum"], list(BOOK["categories"][field]))
        for field in PERSON:
            self.assertEqual(
                sc["sightings"]["items"]["properties"][field]["enum"],
                list(BOOK["categories"][field]),
            )
