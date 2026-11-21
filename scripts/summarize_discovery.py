"""Count the distinct candidates contributed by each discovery choice."""

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

from mw_youtube.records import write_table


def summarize(folder):
    with (folder / "candidates.csv").open(newline="", encoding="utf8") as stream:
        channels = {
            row["video_id"]: row["channel_id"] for row in csv.DictReader(stream)
        }
    groups = defaultdict(set)
    with (folder / "search_counts.csv").open(newline="", encoding="utf8") as stream:
        for row in csv.DictReader(stream):
            for field in ("query_language", "duration_band", "concept", "phrase"):
                groups[field, row[field]]
    with (folder / "search_hits.csv").open(newline="", encoding="utf8") as stream:
        for row in csv.DictReader(stream):
            video = row["video_id"]
            if video in channels:
                for field in ("query_language", "duration_band", "concept", "phrase"):
                    groups[field, row[field]].add(video)
    memberships = Counter(
        (field, video) for (field, _), ids in groups.items() for video in ids
    )
    rows = [
        {
            "dimension": field,
            "value": value,
            "videos": len(ids),
            "exclusive_videos": sum(memberships[field, video] == 1 for video in ids),
            "channels": len({channels[i] for i in ids}),
        }
        for (field, value), ids in sorted(groups.items())
    ]
    write_table(
        folder / "discovery_yield.csv",
        ["dimension", "value", "videos", "exclusive_videos", "channels"],
        rows,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    summarize(parser.parse_args().snapshot)
