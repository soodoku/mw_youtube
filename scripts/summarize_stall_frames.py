"""Summarize one coder's linked frame and sighting tables."""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from mw_youtube.codebook import book_sha
from mw_youtube.counts import GROUPS, summarize
from mw_youtube.records import META, read, table


def run(folder, coder):
    frames = read(folder / f"{coder}_frames.csv")
    people = read(folder / f"{coder}_people.csv")
    manifest = json.loads((folder / "review_manifest.json").read_text())
    archived = json.loads((folder / "codebook.json").read_text())
    if manifest["codebook_sha256"] != book_sha(archived) or [
        {k: str(r[k]) for k in META} for r in manifest["frames"]
    ] != [{k: r[k] for k in META} for r in frames]:
        raise ValueError("Coding rows differ from the review manifest")
    detail = summarize(frames, people, archived)
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
