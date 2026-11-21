"""Build the screening queue or draw verified videos from a frozen queue."""

import argparse
import csv
import hashlib
from collections import Counter, defaultdict
from pathlib import Path

from collect_candidates import write_table
from screen_eligibility import resolve, screen

SEED = "20261121"
KEY = ["city", "video_id"]
REVIEW = ["decision", "reason", "place", "evidence", "reviewer", "review_date"]
CANDIDATE = [
    "city",
    "video_id",
    "watch_url",
    "title",
    "channel_id",
    "published_utc",
    "duration",
    "metadata_status",
    "audio_language",
    "recording_date",
    "view_count",
]
QUEUE = [*CANDIDATE, "video_rank", "sample_seed"]


def read(path, required):
    with path.open(newline="", encoding="utf8") as f:
        reader = csv.DictReader(f)
        if not set(required).issubset(reader.fieldnames or []):
            raise ValueError(f"Missing columns in {path}")
        return list(reader)


def key(row):
    return row["city"], row["video_id"]


def rank(rows, seed):
    if len({key(r) for r in rows}) != len(rows):
        raise ValueError("Duplicate city/video candidate")

    def priority(row):
        city, video = key(row)
        return city, hashlib.sha256(f"{seed}|{city}|{video}".encode()).digest(), video

    counts = Counter()
    ordered = []
    for row in sorted(rows, key=priority):
        city = row["city"]
        counts[city] += 1
        ordered.append({**row, "sample_seed": seed, "video_rank": counts[city]})
    return ordered


def choose(queue, decisions, n):
    if n < 1:
        raise ValueError("Target must be positive")
    if len(decisions) != len({key(r) for r in decisions}):
        raise ValueError("Duplicate screening decision")
    if {key(r) for r in decisions} != {key(r) for r in queue}:
        raise ValueError("Screening sheet does not match the candidate list")
    reviewed = {key(r): r for r in decisions}
    selected = []
    groups = defaultdict(list)
    for row in queue:
        groups[row["city"]].append(row)
    for city, rows in groups.items():
        count = 0
        for row in rows:
            decision = reviewed[key(row)]
            status = decision["decision"]
            if status not in {"eligible", "excluded", "unavailable"}:
                raise ValueError(
                    f"{city}: resolve rank {row['video_rank']} ({status or 'unreviewed'})"
                )
            for field in ("reason", "reviewer", "review_date"):
                if not decision[field].strip():
                    raise ValueError(f"{key(row)} lacks {field}")
            if status == "eligible":
                if not decision["place"].strip() or not decision["evidence"].strip():
                    raise ValueError(f"{key(row)} lacks place or evidence")
                selected.append({**row, **{f: decision[f] for f in REVIEW}})
                count += 1
                if count == n:
                    break
    if len({r["video_id"] for r in selected}) != len(selected):
        raise ValueError("A video qualifies for both cities; resolve its location")
    return selected


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["queue", "select"])
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--target", type=int, default=10)
    parser.add_argument(
        "--manual-only", action="store_true", help="Use only the reviewer sheet."
    )
    args = parser.parse_args()
    folder = args.snapshot
    queue = rank(read(folder / "candidates.csv", CANDIDATE), SEED)
    sheet = folder / "screening.csv"
    if args.action == "queue":
        if sheet.exists():
            raise SystemExit("Screening sheet already exists; preserving reviews.")
        write_table(sheet, [*QUEUE, *REVIEW], queue)
    else:
        decisions = read(sheet, [*KEY, *REVIEW])
        resolved = decisions if args.manual_only else resolve(decisions, screen(folder))
        write_table(folder / "resolved_screening.csv", [*QUEUE, *REVIEW], resolved)
        selected = choose(queue, resolved, args.target)
        dest = folder / f"selected_{args.target}.csv"
        if dest.exists():
            old = read(dest, [*QUEUE, *REVIEW])
            if old != [{k: str(r[k]) for k in [*QUEUE, *REVIEW]} for r in selected]:
                raise SystemExit(
                    "Existing draw differs; preserve it and version the review."
                )
        else:
            write_table(dest, [*QUEUE, *REVIEW], selected)
        counts = Counter(row["city"] for row in selected)
        for city in sorted(
            {row["city"] for row in read(folder / "search_counts.csv", ["city"])}
        ):
            print(f"{city}: {counts[city]}/{args.target} eligible videos selected")
