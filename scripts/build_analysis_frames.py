"""Export one frame-level draw, selected-video coverage and discovery routes."""

import argparse
import json
import re
from pathlib import Path

from mw_youtube.analysis import build
from mw_youtube.records import read, table
from mw_youtube.tables import typed_rows

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("snapshot", type=Path)
    p.add_argument("selected", type=Path)
    p.add_argument(
        "--draw", required=True, help="Short study draw name, such as pilot1"
    )
    p.add_argument("--coding", type=Path, nargs="*", default=[])
    p.add_argument("--coder", choices=("muse", "human"), required=True)
    args = p.parse_args()
    rows, coverage, hits = build(args.snapshot, args.selected, args.coding, args.coder)
    if not coverage:
        raise SystemExit("Empty selection")
    design = json.loads((args.snapshot / "result.json").read_text())
    parts = [
        design["city"],
        str(design["year"]),
        design["topic"],
        args.draw,
        args.coder,
    ]
    if any(not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", part) for part in parts):
        raise SystemExit(
            "City, topic and draw names must use lowercase letters, digits, hyphens or underscores"
        )
    prefix = "_".join(parts)
    out = args.snapshot / "analysis" / args.draw / args.coder
    out.mkdir(parents=True, exist_ok=True)
    previous = out / f"{prefix}_frames.csv"
    if previous.exists():
        old = read(previous)
        available = {r["frame_id"] for r in rows if r["coded"]}
        if any(
            r["selection_sha256"] != coverage[0]["selection_sha256"]
            or (r["coded"] == "1" and r["frame_id"] not in available)
            for r in old
        ):
            raise ValueError(
                "Existing draw would lose coded data or change selection; choose a new draw name"
            )
    outputs = [
        ("video_coverage", coverage),
        ("discovery_hits", hits),
        ("frames", rows),
    ]
    for dataset, records in outputs:
        typed_rows([{**r, "draw": args.draw} for r in records], dataset)
    for dataset, records in outputs:
        path = out / f"{prefix}_{dataset}.csv"
        if records:
            table(
                path, [{**r, "draw": args.draw} for r in records], [*records[0], "draw"]
            )
        elif path.exists():
            raise ValueError(f"Empty export would leave stale data at {path}")
    print(
        f"{out}: {len(rows)} moments, {len(coverage)} selected videos, {len(hits)} search hits"
    )
