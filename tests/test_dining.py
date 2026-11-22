import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from summarize_dining import eligible, estimates  # noqa: E402

from mw_youtube.codebook import schema  # noqa: E402
from mw_youtube.design import CONFIG  # noqa: E402


class Dining(unittest.TestCase):
    def setUp(self):
        self.row = dict(
            group="woman",
            role="vendor",
            host_status="apparent_host",
            setting="restaurant_outdoor",
            at_venue="yes",
            consumption="eating_food",
            quality="partial",
            within_video_weight="0.25",
            video_id="v1",
            channel_id="c",
        )

    def test_published_schema_is_the_contributor_request_schema(self):
        book = json.loads((CONFIG / "stall_frame_codebook_v5.json").read_text())
        published = json.loads(
            (CONFIG / "stall_frame_v5_response.schema.json").read_text()
        )
        self.assertEqual(published, schema(book))
        self.assertEqual(book["model"], "muse-spark-1.3-contributor")
        person = published["properties"]["sightings"]["items"]
        self.assertFalse(person["additionalProperties"])
        for field in book["person_fields"]:
            self.assertIn(field, person["required"])
            self.assertEqual(
                person["properties"][field]["enum"], list(book["categories"][field])
            )

    def test_visible_eating_vendor_host_counts_once(self):
        self.assertTrue(eligible(self.row, "bite", "everyone", "restaurant", False))
        for role in ("exclude_both", "exclude_vendors", "exclude_hosts"):
            self.assertFalse(eligible(self.row, "bite", role, "all", False))
        self.assertFalse(eligible(self.row, "bite", "everyone", "all", True))

    def test_unknown_venue_and_cup_at_mouth(self):
        row = dict(self.row, at_venue="unclear", consumption="drinking")
        self.assertTrue(eligible(row, "all_visible", "everyone", "all", False))
        self.assertFalse(eligible(row, "bite_or_sip", "everyone", "all", False))
        row["at_venue"] = "yes"
        self.assertTrue(eligible(row, "bite_or_sip", "everyone", "all", False))
        self.assertFalse(eligible(row, "bite", "everyone", "all", False))

    def test_ratio_of_weighted_sightings_excludes_unclear_gender(self):
        rows = [
            self.row,
            dict(self.row, group="gender_unclear"),
            dict(self.row, group="man", within_video_weight="1", video_id="v2"),
        ]
        result = next(estimates(rows, rows))
        self.assertEqual(result["percent_women"], 20)
        self.assertEqual(result["n_gender_unclear"], 1)
        self.assertEqual(result["contributing_videos"], 2)
        self.assertIsNone(result["channel_low95"])
