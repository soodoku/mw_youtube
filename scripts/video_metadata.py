"""Export one linked metadata record per candidate from cached official API responses."""

import argparse
import csv
import json
from pathlib import Path

from mw_youtube.records import save


def export(folder):
    lookups = {}
    for path in sorted((folder / "responses").glob("metadata-*.json")):
        response = json.loads(path.read_text())
        returned = {item["id"]: item for item in response["items"]}
        for vid in response["params"]["id"].split(","):
            if vid in lookups:
                raise ValueError(f"Duplicate metadata lookup for {vid}")
            lookups[vid] = (
                returned.get(vid, {}),
                response["retrieved_utc"],
                str(path.relative_to(folder)),
            )
    with (folder / "candidates.csv").open(newline="") as src:
        candidates = list(csv.DictReader(src))
    records = []
    for row in candidates:
        item, retrieved, source = lookups[row["video_id"]]
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        recording = item.get("recordingDetails", {})
        records.append(
            {
                **{k: row[k] or None for k in row},
                "view_count": int(row["view_count"]) if row["view_count"] else None,
                "channel_title": snippet.get("channelTitle"),
                "description": snippet.get("description"),
                "tags": snippet.get("tags"),
                "category_id": snippet.get("categoryId"),
                "title_language": snippet.get("defaultLanguage"),
                "location": recording.get("location"),
                "location_description": recording.get("locationDescription"),
                "like_count": int(stats["likeCount"]) if "likeCount" in stats else None,
                "comment_count": (
                    int(stats["commentCount"]) if "commentCount" in stats else None
                ),
                "content_details": item.get("contentDetails"),
                "status": item.get("status"),
                "retrieved_utc": retrieved,
                "response_file": source,
            }
        )
    save(
        folder / "video_metadata.jsonl",
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    export(parser.parse_args().snapshot)
