"""Add meal evidence to the frozen person roster with the existing Muse client."""

import argparse
import base64
import hashlib
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from mw_youtube.codebook import choices, object_schema
from mw_youtube.design import CONFIG
from mw_youtube.records import read, save

BOOK = json.loads((CONFIG / "apparent_diner.json").read_text())
FIELDS = tuple(BOOK["categories"])
PERSON = object_schema(
    {
        "person_id": {"type": "integer", "minimum": 1},
        **choices(FIELDS, BOOK),
        "meal_cue": {"type": "string"},
    }
)
SCHEMA = object_schema({"sightings": {"type": "array", "items": PERSON}})


def checked(rows, roster):
    ids = [r["person_id"] for r in rows]
    expected = [int(p["person_id"]) for p in roster]
    if sorted(ids) != sorted(expected):
        raise ValueError("Meal labels do not match the original person roster")
    for r in rows:
        if not r["meal_cue"].strip() or any(
            r[k] not in BOOK["categories"][k] for k in FIELDS
        ):
            raise ValueError("Missing meal cue or invalid label")


def group_people(people):
    roster = defaultdict(list)
    for r in people:
        roster[r["frame_id"]].append(r)
    return roster


def run(snapshot, data, cap, workers, pilot=None):
    from museclient import BudgetError, Client

    root = snapshot / "coding_apparent_diners"
    root.mkdir(exist_ok=True)
    client = Client(
        cap_usd=cap,
        model=BOOK["model"],
        workdir=root / "muse",
        ledger=snapshot / "coding_v5" / "muse_ledger",
    )
    roster = group_people(read(data / "sightings.csv"))
    frames = read(data / "frames.csv")
    context_keys = json.loads((CONFIG / "stall_frame_codebook_v5.json").read_text())[
        "context_fields"
    ]
    with (snapshot / "video_metadata.jsonl").open() as records:
        videos = {
            v["video_id"]: {k: v[k] for k in context_keys}
            for v in map(json.loads, records)
        }
    prompt = (
        "\n".join(BOOK["instructions"])
        + "\n"
        + json.dumps(BOOK["categories"], ensure_ascii=False)
    )

    def annotate(frame):
        vid = frame["video_id"]
        name = f"i{frame['interval']}_r{frame['rank']}.jpg"
        people = roster[frame["frame_id"]]
        if pilot is not None and name not in pilot.get(vid, []):
            return
        if not people:
            return
        raw = (snapshot / "frames/per_minute" / vid / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != frame["jpeg_sha256"]:
            raise ValueError(f"Image changed for {frame['frame_id']}")
        locations = [{k: p[k] for k in ("person_id", "cue")} for p in people]
        instruction = (
            prompt
            + "\nPublisher metadata and sighting pointers:\n"
            + json.dumps(
                {"publisher": videos[vid], "people": locations}, ensure_ascii=False
            )
        )
        content = [
            {"type": "text", "text": instruction},
            {
                "type": "image_url",
                "image_url": {
                    "url": "data:image/jpeg;base64,"
                    + base64.b64encode(raw).decode("ascii")
                },
            },
        ]
        answer, call = client.complete(
            [{"role": "user", "content": content}],
            SCHEMA,
            name="apparent_diners",
            max_completion_tokens=4800,
            with_call=True,
            key_extra={"version": BOOK["version"], "frame": frame["frame_id"]},
        )
        checked(answer["sightings"], people)
        save(
            root / (frame["frame_id"] + ".json"),
            json.dumps(
                {
                    "call_id": call.name,
                    "frame_id": frame["frame_id"],
                    "image_sha256": frame["jpeg_sha256"],
                    **answer,
                },
                indent=2,
            )
            + "\n",
        )

    deferred = []

    def attempt(frame):
        try:
            annotate(frame)
        except BudgetError:
            return frame

    with ThreadPoolExecutor(max_workers=workers) as pool:
        deferred = [r for r in pool.map(attempt, frames) if r is not None]
    for frame in deferred:
        annotate(frame)
    print(client.spend(), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("tables", type=Path)
    parser.add_argument("--cap-usd", type=float, required=True)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--pilot", type=Path)
    args = parser.parse_args()
    run(
        args.snapshot,
        args.tables,
        args.cap_usd,
        args.workers,
        json.loads(args.pilot.read_text()) if args.pilot else None,
    )
