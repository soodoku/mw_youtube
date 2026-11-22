"""Extend a ranked city draw with 3–30 sampled moments per verified upload."""

import argparse
import fcntl
import json
import os
import shutil
import subprocess
import sys
from contextlib import ExitStack
from fractions import Fraction
from pathlib import Path

from acquire_frames import DEFAULT_RESERVE, MIB, dump, now, room, sha, verify
from chrome_frames import capture, duration_seconds, player, watch
from prepare_frame_review import run as prepare
from sample_frames import draw
from sample_videos import QUEUE, REVIEW, SEED, choose, key, rank
from screen_eligibility import resolve, screen

from mw_youtube.design import frames_per_third
from mw_youtube.records import read, write_table


def read_json(path):
    return json.loads(path.read_text())


def capture_upload(snapshot, root, row, get_page):
    vid = row["video_id"]
    folder = root / vid
    folder.mkdir(parents=True, exist_ok=True)
    done = folder / "complete.json"
    if done.exists():
        verify(folder)
        return len(read_json(done)["frames"])
    page = get_page()
    actual = watch(page, vid, duration_seconds(row["duration"]))
    pilot = snapshot / "frames" / vid
    previous = verify(pilot) if (pilot / "complete.json").exists() else None
    duration = Fraction(previous["duration"]) if previous else Fraction(str(actual))
    if abs(float(duration) - actual) > 0.25:
        raise ValueError(f"{vid}: playback duration differs from frozen source")
    path = folder / "plan.json"
    if path.exists():
        plan = read_json(path)
        duration = Fraction(plan["duration"])
        if plan.get("capture_method") != "chrome":
            raise ValueError(
                "Resume this unfinished source-file extraction in acquire_frames.py"
            )
        if abs(float(duration) - actual) > 0.25 or (
            plan["seed"],
            plan["video_id"],
            plan["per_interval"],
        ) != (SEED, vid, frames_per_third(duration)):
            raise ValueError(f"{vid}: frozen duration or allocation changed")
    else:
        n = frames_per_third(duration)
        plan = dict(
            video_id=vid,
            seed=SEED,
            duration=str(duration),
            per_interval=n,
            capture_method="chrome",
            source_sha256=None,
            first_time=None,
            source=dict(
                watch_url=row["watch_url"],
                opened_utc=now(),
                browser_version=page.context.browser.version,
            ),
            moments=draw(vid, SEED, duration, n),
        )
        dump(path, plan)
    progress = folder / "capture_progress.json"
    frames = read_json(progress) if progress.exists() else {}
    original = (
        {i["requested_ms"]: i for i in read_json(pilot / "complete.json")["frames"]}
        if previous
        else {}
    )
    for m in sorted(plan["moments"], key=lambda r: r["requested_ms"]):
        ms = m["requested_ms"]
        name = f"i{m['interval']}_r{m['rank']}.jpg"
        dest = folder / name
        if name in frames and dest.exists() and sha(dest) == frames[name]["sha256"]:
            continue
        room(folder, DEFAULT_RESERVE, 8 * MIB)
        if ms in original:
            item = original[ms]
            if any(item[k] != m[k] for k in m):
                raise ValueError("Pilot draw changed position")
            if not dest.exists():
                try:
                    os.link(pilot / item["file"], dest)
                except OSError:
                    shutil.copyfile(pilot / item["file"], dest)
            if sha(dest) != item["sha256"]:
                raise ValueError("Pilot image differs from receipt")
            entry = dict(
                item,
                capture_method=previous.get("capture_method", "file"),
                source_sha256=previous["source_sha256"],
                first_time=previous["first_time"],
                source_version=previous["source_sha256"] or sha(pilot / "plan.json"),
            )
        else:
            t = capture(page, vid, actual, ms / 1000, dest)
            entry = dict(
                m,
                file=name,
                sha256=sha(dest),
                player_time_s=t,
                pts=None,
                time_base=None,
                browser_session="attached_premium",
            )
        frames[name] = entry
        dump(progress, frames)
    complete = dict(
        finished_utc=now(),
        plan_sha256=sha(path),
        frames=sorted(frames.values(), key=lambda r: r["requested_ms"]),
    )
    verify(folder, complete)
    dump(done, complete)
    progress.unlink(missing_ok=True)
    return len(frames)


def capture_status(snapshot, target):
    """Count verified files from the current draw while a capture worker is active."""
    city = read_json(snapshot / "result.json")["city"]
    run_dir = snapshot / "runs" / f"{city}{target}_per_minute"
    manifests = (
        run_dir / "selected.csv",
        snapshot / f"selected_{target}.csv",
        run_dir / "verified_so_far.csv",
    )
    manifest = next((m for m in manifests if m.exists()), None)
    if manifest is None:
        raise ValueError("No saved selection or provisional manifest")
    rows = read(manifest)
    acquired = complete = expected = in_progress = 0
    for row in rows:
        folder = snapshot / "frames" / "per_minute" / row["video_id"]
        plan = folder / "plan.json"
        expected += (
            len(read_json(plan)["moments"])
            if plan.exists()
            else 3 * frames_per_third(duration_seconds(row["duration"]))
        )
        receipt = folder / "complete.json"
        progress = folder / "capture_progress.json"
        if receipt.exists():
            verify(folder)
            acquired += len(read_json(receipt)["frames"])
            complete += 1
        elif progress.exists():
            try:
                items = read_json(progress).values()
            except FileNotFoundError:
                items = read_json(receipt)["frames"]
            for item in items:
                path = folder / item["file"]
                if sha(path) != item["sha256"]:
                    raise ValueError(f"Image checksum mismatch: {path}")
                acquired += 1
                in_progress += 1
    return dict(
        selected=len(rows),
        target=target,
        complete_videos=complete,
        verified_images=acquired,
        images_in_incomplete_videos=in_progress,
        expected_images=expected,
    )


def run(snapshot, target, cap=None):
    if cap is not None and cap <= 0:
        raise ValueError("Expected a positive total spending cap")
    if target <= 0:
        raise ValueError("Positive target required")
    queue = rank(read(snapshot / "candidates.csv"), SEED)
    rows = resolve(read(snapshot / "screening.csv"), screen(snapshot))
    reviewed = {key(r): r for r in rows}
    if len(reviewed) != len(rows) or set(reviewed) != {key(r) for r in queue}:
        raise ValueError("Screening does not match frozen queue")
    checks = {
        key(r)
        for r in read(snapshot / "footage_reviews.csv")
        if all(r[k].strip() for k in ("reviewer", "timestamp", "evidence"))
    }
    selected = []
    pending = []
    for row in queue:
        d = reviewed[key(row)]
        if d["decision"] == "eligible" and key(d) in checks:
            selected.extend(choose([row], [d], 1, checks))
            if len(selected) == target:
                break
        elif d["decision"] not in {"excluded", "unavailable"}:
            pending.append(int(row["video_rank"]))
    root = snapshot / "frames" / "per_minute"
    run_dir = snapshot / "runs" / f"{queue[0]['city']}{target}_per_minute"
    run_dir.mkdir(parents=True, exist_ok=True)
    confirmed = len(selected) == target and not pending
    manifest = run_dir / ("selected.csv" if confirmed else "verified_so_far.csv")
    if (run_dir / "selected.csv").exists() and (
        not confirmed
        or [r["video_id"] for r in read(run_dir / "selected.csv")]
        != [r["video_id"] for r in selected]
    ):
        raise ValueError("The frozen selection changed")
    if confirmed:
        for prior in (snapshot / "runs").glob("*_per_minute/selected.csv"):
            ids = [r["video_id"] for r in read(prior)]
            current = [r["video_id"] for r in selected]
            common = min(len(current), len(ids))
            if ids[:common] != current[:common]:
                raise ValueError(
                    f"Frozen samples disagree on the ranked prefix: {prior}"
                )
    if not manifest.exists() or not confirmed:
        write_table(manifest, [*QUEUE, *REVIEW], selected)
    status = dict(
        target=target,
        selection_final=confirmed,
        verified=len(selected),
        next_review=pending[0] if pending else None,
        completed={},
        errors={},
    )
    report = run_dir / "status.json"
    dump(report, status)
    with ExitStack() as stack:
        page = None

        def get_page():
            nonlocal page
            if page is None:
                page = stack.enter_context(player())
            return page

        for row in selected:
            vid = row["video_id"]
            try:
                count = capture_upload(snapshot, root, row, get_page)
                coding = snapshot / "coding_v4" / vid
                prepare(root / vid, coding, snapshot / "video_metadata.jsonl")
                status["completed"][vid] = count
                dump(report, status)
                if cap is not None:
                    from code_stall_frames import run as code
                    from summarize_stall_frames import run as summarize

                    if (
                        not (coding / "muse_frames.csv").exists()
                        or not (coding / "muse_people.csv").exists()
                    ):
                        code(
                            root / vid,
                            coding,
                            cap,
                            snapshot / "coding_v4" / "muse_ledger",
                        )
                    summarize(coding, "muse")
                print(row["video_rank"], vid, count, "ready", flush=True)
            except Exception as exc:
                status["errors"][vid] = type(exc).__name__
                print(
                    row["video_rank"],
                    vid,
                    type(exc).__name__,
                    str(exc).splitlines()[0][:180],
                    flush=True,
                )
            dump(report, status)
    if selected:
        coded = []
        for row in selected:
            directory = snapshot / "coding_v4" / row["video_id"]
            if (directory / "muse_frames.csv").exists() and (
                directory / "muse_people.csv"
            ).exists():
                coded.append(directory)
        # A changing provisional sample gets a distinct manifest digest for each export.
        name = (
            run_dir.name
            if confirmed
            else f"{run_dir.name}_provisional_{sha(manifest)[:10]}"
        )
        subprocess.run(
            [
                sys.executable,
                str(Path(__file__).with_name("build_analysis_frames.py")),
                str(snapshot),
                str(manifest),
                "--host-fields",
                "--frame-root",
                str(root),
                "--draw",
                name,
                "--coder",
                "muse",
                "--coding",
                *map(str, coded),
            ],
            check=True,
        )
        status["analysis_draw"] = name
        dump(report, status)
    print(
        manifest,
        status["verified"],
        "verified;",
        sum(status["completed"].values()),
        "frames",
        flush=True,
    )
    return status


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--target", type=int, default=30)
    parser.add_argument(
        "--cap-usd", type=float, help="Optional cumulative v4 Muse ledger cap"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Count saved images without starting capture",
    )
    args = parser.parse_args()
    if args.status:
        print(json.dumps(capture_status(args.snapshot, args.target), indent=2))
        raise SystemExit(0)
    folder = args.snapshot / "frames" / "per_minute"
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        status = run(args.snapshot, args.target, args.cap_usd)
    if status["errors"]:
        raise SystemExit(1)
