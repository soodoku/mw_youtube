"""Join the apparent-diner labels to the published roster and estimate shares."""

import argparse
import json
from collections import Counter
from pathlib import Path

from code_apparent_diners import BOOK, checked, group_people
from summarize_dining import APPARENT, FOOD, estimates

from mw_youtube.records import read, save, table


def run(snapshot, data, out):
    root = snapshot / "coding_apparent_diners"
    frames = read(data / "frames.csv")
    roster = group_people(read(data / "sightings.csv"))
    people, calls = [], set()
    for frame in frames:
        fid = frame["frame_id"]
        original = roster.pop(fid, [])
        if len(original) != int(frame["n_enumerated"] or 0):
            raise ValueError(f"Incomplete roster for {fid}")
        counts = Counter()
        if original:
            receipt = json.loads((root / (fid + ".json")).read_text())
            if (
                receipt["image_sha256"] != frame["jpeg_sha256"]
                or receipt["frame_id"] != fid
                or receipt["call_id"] in calls
            ):
                raise ValueError(f"Receipt mismatch for {fid}")
            calls.add(receipt["call_id"])
            labels = receipt["sightings"]
            checked(labels, original)
            by_id = {r["person_id"]: r for r in labels}
            for r in original:
                label = by_id[int(r["person_id"])]
                if (
                    label["meal_evidence"] in FOOD
                    and label["dining_venue"] == "food_venue"
                ):
                    counts[r["group"]] += 1
                people.append(
                    {
                        **r,
                        **label,
                        "meal_call_id": receipt["call_id"],
                        "meal_model": BOOK["model"],
                        "meal_protocol": BOOK["version"],
                    }
                )
        for g in ("woman", "man", "gender_unclear", "younger_child", "age_unclear"):
            frame["apparent_diner_" + g] = (
                counts[g] if frame["quality"] != "unreadable" else None
            )
    if roster:
        raise ValueError("Sighting with no frame")
    out.mkdir(parents=True, exist_ok=True)
    table(out / "frames.csv", frames, frames[0].keys())
    table(out / "sightings.csv", people, people[0].keys())
    rows = list(estimates(frames, people, ("all_visible", *APPARENT)))
    table(out / "estimates.csv", rows, rows[0].keys())
    ledger = [
        json.loads(p.read_text())
        for p in (snapshot / "coding_v5/muse_ledger").glob("*.json")
    ]
    used = [r for r in ledger if r["call_id"] in calls and r["status"] == "valid"]
    if len(used) != len(calls):
        raise ValueError("Incomplete contributor spending ledger")
    save(
        out / "spend.json",
        json.dumps(
            {
                "model": BOOK["model"],
                "frames_total": len(frames),
                "nonempty_frames_coded": len(calls),
                "meal_usage_usd": sum(r["estimated_cost_usd"] for r in used),
                "cumulative_usage_usd": sum(
                    r.get("estimated_cost_usd", 0) for r in ledger
                ),
                "cumulative_bound_usd": sum(r["charged_bound_usd"] for r in ledger),
                "cap_usd": max(r["authorized_cap_usd"] for r in ledger),
            },
            indent=2,
        )
        + "\n",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for label in ("snapshot", "tables", "output"):
        parser.add_argument(label, type=Path)
    args = parser.parse_args()
    run(args.snapshot, args.tables, args.output)
