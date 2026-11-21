"""Tabulate visible people by setting and role."""

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from prepare_frame_review import KEY, META, table
from stall_codebook import book_sha, validate

SCOPES = {
    "all_visible": None,
    "all_at_stall": None,
    "linked_including_unclear": {"worker", "patron", "unclear"},
    "worker_and_patron": {"worker", "patron"},
    "worker": {"worker"},
    "patron": {"patron"},
}
GROUPS = {
    "n_women": "woman",
    "n_men": "man",
    "n_gender_unclear": "gender_unclear",
    "n_younger_child": "younger_child",
    "n_age_unclear": "age_unclear",
}


def read(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def key(row):
    return tuple(str(row[k]) for k in KEY)


def summarize(frames, people):
    by_frame = defaultdict(list)
    for p in people:
        by_frame[key(p)].append(p)
    if set(by_frame) - {key(f) for f in frames}:
        raise ValueError("Sighting points to an unknown frame")
    results = []
    for f in frames:
        members = sorted(by_frame[key(f)], key=lambda p: int(p["person_id"]))
        validate(
            {
                **f,
                "n_enumerated": (
                    None if f["n_enumerated"] in (None, "") else int(f["n_enumerated"])
                ),
                "sightings": [{**p, "person_id": int(p["person_id"])} for p in members],
            }
        )
        for scope, roles in SCOPES.items():
            included = scope == "all_visible" or f["setting"] == "street_stall"
            counts = Counter(
                p["group"] for p in members if roles is None or p["role"] in roles
            )
            reportable = included and f["quality"] == "countable"
            row = {k: f[k] for k in KEY}
            row.update(
                setting=f["setting"],
                shot=f["shot"],
                service_area=f["service_area"],
                scope=scope,
                in_scope=int(included),
                quality=f["quality"],
            )
            row.update(
                {k: counts[g] if reportable else None for k, g in GROUPS.items()}
            )
            results.append(row)
    return results


def run(folder, coder):
    frames = read(folder / f"{coder}_frames.csv")
    people = read(folder / f"{coder}_people.csv")
    manifest = json.loads((folder / "review_manifest.json").read_text())
    if manifest["codebook_sha256"] != book_sha() or [
        {k: str(r[k]) for k in META} for r in manifest["frames"]
    ] != [{k: r[k] for k in META} for r in frames]:
        raise ValueError("Coding rows differ from the review manifest")
    detail = summarize(frames, people)
    table(folder / (coder + "_frame_counts.csv"), detail, list(detail[0]))
    grouped = defaultdict(list)
    for r in detail:
        grouped[(r["video_id"], r["scope"])].append(r)
    output = []
    for (vid, scope), rows in grouped.items():
        eligible = [r for r in rows if r["n_women"] is not None]
        totals = {k: sum(r[k] for r in eligible) if eligible else None for k in GROUPS}
        denom = (totals["n_women"] + totals["n_men"]) if eligible else None
        output.append(
            dict(
                video_id=vid,
                scope=scope,
                sampled_frames=len(rows),
                in_scope_frames=sum(r["in_scope"] for r in rows),
                countable_in_scope=len(eligible),
                **totals,
                classified=denom,
                women_share=totals["n_women"] / denom if denom else None,
            )
        )
    table(folder / (coder + "_video_counts.csv"), output, list(output[0]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--coder", choices=["human", "muse"], required=True)
    args = parser.parse_args()
    run(args.output, args.coder)
