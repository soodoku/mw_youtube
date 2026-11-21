"""Plan the pilot searches or save a dated, resumable YouTube search snapshot."""

import argparse
import csv
import fcntl
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from search_plan import CONFIG, searches


def save(path, content):
    with NamedTemporaryFile("w", dir=path.parent, delete=False, encoding="utf8") as tmp:
        tmp.write(content)
    Path(tmp.name).replace(path)


def snapshot(folder, name, resource, params):
    path = folder / f"{name}.json"
    if path.exists():
        record = json.loads(path.read_text())
        if record["params"] != params or record["resource"] != resource:
            raise ValueError(
                f"Search definition changed for {name}; use a new snapshot"
            )
        return record
    key = os.environ.get("YOUTUBE_API_KEY") or os.environ.get("YOUTUBE_DATA_API_KEY")
    if not key:
        raise SystemExit("Set YOUTUBE_API_KEY to collect a new snapshot.")
    req = Request(
        f"https://www.googleapis.com/youtube/v3/{resource}?{urlencode(params)}",
        headers={"X-Goog-Api-Key": key},
    )
    try:
        with urlopen(req, timeout=45) as resp:
            data = json.load(resp)
    except HTTPError as exc:
        raise SystemExit(
            f"{name}: YouTube HTTP {exc.code}; saved requests can be resumed."
        ) from None
    if not isinstance(data.get("items"), list):
        raise ValueError(f"Invalid response for {name}; no checkpoint written")
    record = {
        "resource": resource,
        "params": params,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "items": data["items"],
    }
    save(path, json.dumps(record, ensure_ascii=False, indent=2))
    return record


def write_table(path, columns, rows):
    with NamedTemporaryFile(
        "w", dir=path.parent, newline="", encoding="utf8", delete=False
    ) as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    Path(f.name).replace(path)


def collect(folder, plan):
    raw = folder / "responses"
    raw.mkdir(parents=True, exist_ok=True)
    definition = json.dumps(plan, ensure_ascii=False, indent=2)
    manifest = folder / "queries.json"
    if manifest.exists() and manifest.read_text() != definition:
        raise SystemExit("This snapshot uses a different search plan.")
    save(manifest, definition)
    counts = []
    hits = []
    candidates = {}
    for search in plan:
        params = search["params"]
        record = snapshot(raw, search["search_id"], "search", params)
        criteria = {k: v for k, v in search.items() if k != "params"}
        counts.append(
            {
                **criteria,
                "phrase": params["q"],
                "hits": len(record["items"]),
                "retrieved_utc": record["retrieved_utc"],
            }
        )
        for rank, item in enumerate(record["items"], 1):
            video = item["id"]["videoId"]
            city = search["city"]
            hits.append(
                dict(
                    **criteria,
                    phrase=params["q"],
                    result_rank=rank,
                    video_id=video,
                    retrieved_utc=record["retrieved_utc"],
                )
            )
            published = datetime.fromisoformat(
                item["snippet"]["publishedAt"].replace("Z", "+00:00")
            )
            begin = datetime.fromisoformat(
                params["publishedAfter"].replace("Z", "+00:00")
            )
            end = datetime.fromisoformat(
                params["publishedBefore"].replace("Z", "+00:00")
            )
            if begin <= published <= end:
                candidates.setdefault((city, video), item["snippet"])
    search_fields = [k for k in plan[0] if k != "params"] + ["phrase"]
    write_table(
        folder / "search_counts.csv", [*search_fields, "hits", "retrieved_utc"], counts
    )
    write_table(
        folder / "search_hits.csv",
        [*search_fields, "result_rank", "video_id", "retrieved_utc"],
        hits,
    )
    ids = sorted({video for _, video in candidates})
    metadata = {}
    for start in range(0, len(ids), 50):
        stop = start + 50
        batch = ",".join(ids[start:stop])
        tag = hashlib.sha256(batch.encode()).hexdigest()
        record = snapshot(
            raw,
            f"metadata-{tag}",
            "videos",
            {
                "part": "snippet,contentDetails,status,recordingDetails,statistics",
                "id": batch,
            },
        )
        metadata.update({item["id"]: item for item in record["items"]})
    rows = []
    for (city, video), snippet in sorted(candidates.items()):
        item = metadata.get(video, {})
        rows.append(
            dict(
                city=city,
                video_id=video,
                watch_url="https://www.youtube.com/watch?v=" + video,
                title=item.get("snippet", snippet)["title"],
                audio_language=item.get("snippet", {}).get("defaultAudioLanguage", ""),
                recording_date=item.get("recordingDetails", {}).get(
                    "recordingDate", ""
                ),
                view_count=item.get("statistics", {}).get("viewCount", ""),
                channel_id=snippet["channelId"],
                published_utc=snippet["publishedAt"],
                duration=item.get("contentDetails", {}).get("duration", ""),
                metadata_status="returned" if item else "unavailable",
            )
        )
    write_table(
        folder / "candidates.csv",
        [
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
        ],
        rows,
    )
    from video_metadata import export

    export(folder)
    result = {
        "schema_version": 2,
        "city": plan[0]["city"],
        "year": plan[0]["year"],
        "topic": plan[0]["topic"],
        "searches": len(plan),
        "hits": len(hits),
        "candidates": len(rows),
        "channels": len({row["channel_id"] for row in rows}),
        "files": {
            "queries": "queries.json",
            "search_counts": "search_counts.csv",
            "search_hits": "search_hits.csv",
            "candidates": "candidates.csv",
            "video_metadata": "video_metadata.jsonl",
        },
    }
    save(folder / "result.json", json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "collect"])
    destinations = parser.add_mutually_exclusive_group()
    destinations.add_argument("--snapshot", type=Path)
    destinations.add_argument(
        "--wave", help="Store a repeat search in its own named wave directory"
    )
    parser.add_argument("--city", required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--config", type=Path, default=CONFIG)
    args = parser.parse_args()
    plan = list(searches(args.city, args.year, args.topic, args.config))
    if args.action == "plan":
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        if not args.snapshot:
            args.snapshot = Path("data") / f"{args.city}_{args.year}_{args.topic}"
            if args.wave:
                if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", args.wave):
                    parser.error(
                        "Use letters, digits, underscores and hyphens for a wave"
                    )
                args.snapshot = args.snapshot / "waves" / args.wave
        args.snapshot.mkdir(parents=True, exist_ok=True)
        with (args.snapshot / ".collection.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            print(json.dumps(collect(args.snapshot, plan), indent=2))
