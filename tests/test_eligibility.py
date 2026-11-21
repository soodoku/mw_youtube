import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import screen_eligibility as eligibility  # noqa: E402


class EligibilityTests(unittest.TestCase):
    def test_rule_requires_named_series_and_credits(self):
        show = "Taarak Mehta Ka Ooltah Chashmah"
        desc = f"Show Name: {show}\nStar Cast: Person\nEpisode No: 12"
        self.assertIsNotNone(
            eligibility.explicit_exclusion({"description": desc}, [show])
        )
        for text in (
            "Street food full episode",
            desc.replace(show, "Food Walks"),
            desc.splitlines()[0],
        ):
            self.assertIsNone(
                eligibility.explicit_exclusion({"description": text}, [show])
            )

    def test_quote_required_and_review_overrides(self):
        record = {"title": "Noodles", "description": "Filmed at a home in Lahore"}
        answer = {
            "decision": "excluded",
            "reason": "outside city",
            "place_quote": "",
            "setting_quote": "Filmed in Karachi",
        }
        self.assertEqual(eligibility.checked(answer, record)["decision"], "unclear")
        answer["setting_quote"] = "Filmed at a home in Lahore"
        self.assertEqual(eligibility.checked(answer, record)["decision"], "excluded")
        row = {"city": "delhi", "video_id": "fixture", "decision": "unclear"}
        machine = {**row, **answer, "method": "muse", "review_date": "2026-11-21"}
        self.assertEqual(eligibility.resolve([row], [machine]), [row])
        self.assertEqual(
            eligibility.resolve([{**row, "decision": ""}], [machine])[0]["decision"],
            "excluded",
        )

    def test_replay(self):
        calls = []

        class FakeClient:
            def __init__(self, **kwargs):
                pass

            def complete(self, messages, **kwargs):
                calls.append(messages)
                return {
                    "decision": "excluded",
                    "reason": "other city",
                    "place_quote": "",
                    "setting_quote": "Filmed in Lahore",
                }, Path("fixture-call")

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "responses").mkdir()
            (p / "result.json").write_text(
                json.dumps({"city": "delhi", "topic": "street_food"})
            )
            (p / "responses/metadata-1.json").write_text(
                json.dumps(
                    {
                        "retrieved_utc": "2026-11-21",
                        "items": [
                            {
                                "id": "fixture",
                                "snippet": {
                                    "title": "Food",
                                    "description": "Filmed in Lahore",
                                },
                            }
                        ],
                    }
                )
            )
            with (p / "screening.csv").open("w", newline="") as f:
                w = csv.DictWriter(
                    f, fieldnames=["city", "video_id", "video_rank", "title"]
                )
                w.writeheader()
                w.writerow(
                    dict(city="delhi", video_id="fixture", video_rank=1, title="Food")
                )
            first = eligibility.screen(p, 1, 1, FakeClient)
            self.assertEqual(first, eligibility.screen(p))
            self.assertEqual(first[0]["decision"], "excluded")
            self.assertEqual(len(calls), 1)
