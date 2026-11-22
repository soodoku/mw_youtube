"""Apply the contributor frame coder to a frozen selection with one shared ledger."""

import argparse
import csv
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from code_stall_frames import run as code
from prepare_frame_review import run as prepare

from mw_youtube.design import CONFIG


def run(snapshot, selection, cap, workers, pilot=None):
    book = json.loads((CONFIG / "stall_frame_codebook_v5.json").read_text())
    output = snapshot / "coding_v5"
    with selection.open() as stream:
        videos = [row["video_id"] for row in csv.DictReader(stream)]
    if len(set(videos)) != len(videos):
        raise ValueError("Duplicate selected video")
    if pilot is not None and set(pilot) - set(videos):
        raise ValueError("Pilot includes an unselected video")

    def one(video):
        folder = snapshot / "frames" / "per_minute" / video
        packet = output / video
        rows = prepare(folder, packet, snapshot / "video_metadata.jsonl", book)
        only = None if pilot is None else pilot[video]
        if only is not None and set(only) - {r["jpeg"] for r in rows}:
            raise ValueError(f"Unknown pilot frame for {video}")
        code(folder, packet, cap, output / "muse_ledger", only)
        print(video, len(rows) if only is None else len(only), flush=True)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(one, videos if pilot is None else pilot))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("selection", type=Path)
    parser.add_argument("--cap-usd", required=True, type=float)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--pilot", type=Path, help="JSON mapping video IDs to JPEG names"
    )
    args = parser.parse_args()
    run(
        args.snapshot,
        args.selection,
        args.cap_usd,
        args.workers,
        json.loads(args.pilot.read_text()) if args.pilot else None,
    )
