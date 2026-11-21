"""Advance the verified prefix of a city draw; persist the next unresolved rank."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from sample_videos import QUEUE, REVIEW, SEED, choose, key, rank
from screen_eligibility import resolve, screen

from mw_youtube.records import read, save, write_table


def run(snapshot, target, draw, cap=None, local=None, use_download=False):
    if cap is not None and cap <= 0:
        raise ValueError("A paid run needs a positive total cap")
    if target < 1 or not re.fullmatch("[a-z0-9][a-z0-9_-]*", draw):
        raise ValueError("Invalid draw or target")
    root = snapshot / "runs" / draw
    root.mkdir(parents=True, exist_ok=True)
    queue = rank(read(snapshot / "candidates.csv"), SEED)
    resolved = resolve(read(snapshot / "screening.csv"), screen(snapshot))
    write_table(snapshot / "resolved_screening.csv", [*QUEUE, *REVIEW], resolved)
    verified = (
        {
            key(r)
            for r in read(snapshot / "footage_reviews.csv")
            if all(r[x].strip() for x in ("timestamp", "reviewer", "evidence"))
        }
        if (snapshot / "footage_reviews.csv").exists()
        else set()
    )
    reviewed = {key(r): r for r in resolved}
    prefix = []
    next_row = None
    count = 0
    for r in queue:
        d = reviewed[key(r)]
        if d["decision"] not in ("eligible", "excluded", "unavailable") or (
            d["decision"] == "eligible" and key(r) not in verified
        ):
            next_row = {
                "rank": int(r["video_rank"]),
                "video_id": r["video_id"],
                "watch_url": r["watch_url"],
            }
            break
        prefix.append(r)
        count += d["decision"] == "eligible"
        if count == target:
            break
    selected = choose(prefix, [reviewed[key(r)] for r in prefix], target, verified)
    status = dict(
        target=target,
        verified=len(selected),
        next_review=next_row,
        prepared=[],
        coded=[],
    )
    checkpoint = root / "status.json"

    def update():
        save(checkpoint, json.dumps(status, indent=2) + "\n")

    update()
    if not selected:
        return status
    manifest = root / f"selected_{len(selected)}.csv"
    if manifest.exists() and [r["video_id"] for r in read(manifest)] != [
        r["video_id"] for r in selected
    ]:
        raise ValueError(
            "Verified sample changed; preserve this draw and create a new version"
        )
    write_table(manifest, [*QUEUE, *REVIEW], selected)
    if len(selected) == target:
        subprocess.run(
            [
                sys.executable,
                str(Path(__file__).with_name("sample_videos.py")),
                "select",
                str(snapshot),
                "--target",
                str(target),
            ],
            check=True,
        )
    coded = []

    def command(script, *args):
        subprocess.run(
            [sys.executable, str(Path(__file__).with_name(script)), *map(str, args)],
            check=True,
        )

    for row in selected:
        vid = row["video_id"]
        folder = snapshot / "frames" / vid
        coding = snapshot / "coding_v3" / vid
        if (
            not (coding / "muse_frames.csv").exists()
            or not (coding / "muse_people.csv").exists()
        ):
            with TemporaryDirectory(dir=root) as tmp:
                one = Path(tmp) / "selected.csv"
                write_table(one, [*QUEUE, *REVIEW], [row])
                source = (
                    ["--local-sources", local]
                    if local
                    else ["--allow-yt-dlp"] if use_download else []
                )
                command("acquire_frames.py", one, snapshot / "frames", *source)
            command("prepare_frame_review.py", folder, coding)
            status["prepared"].append(vid)
            update()
            if cap is not None:
                command(
                    "code_stall_frames.py",
                    folder,
                    coding,
                    "--cap-usd",
                    cap,
                    "--ledger",
                    root / "muse_ledger",
                )
        if (coding / "muse_frames.csv").exists() and (
            coding / "muse_people.csv"
        ).exists():
            coded.append(coding)
            status["coded"].append(vid)
        update()
    name = draw if len(selected) == target else f"{draw}_prefix{len(selected)}"
    command(
        "build_analysis_frames.py",
        snapshot,
        manifest,
        "--draw",
        name,
        "--coder",
        "muse",
        "--coding",
        *coded,
    )
    status["analysis_draw"] = name
    update()
    return status


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("snapshot", type=Path)
    p.add_argument("--target", type=int, default=10)
    p.add_argument("--draw", required=True)
    p.add_argument("--cap-usd", type=float)
    source = p.add_mutually_exclusive_group()
    source.add_argument("--local-sources", type=Path)
    source.add_argument("--allow-yt-dlp", action="store_true")
    args = p.parse_args()
    print(
        json.dumps(
            run(
                args.snapshot,
                args.target,
                args.draw,
                args.cap_usd,
                args.local_sources,
                args.allow_yt_dlp,
            ),
            indent=2,
        )
    )
