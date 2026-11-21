"""Acquire one selected upload, verify its sampled frames, then release the spool."""

import argparse
import csv
import fcntl
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from fractions import Fraction
from importlib.metadata import version
from pathlib import Path
from urllib.request import Request, urlopen

from collect_candidates import save
from PIL import Image
from sample_frames import displayed_frames, draw, timeline
from yt_dlp import YoutubeDL

MIB = 1024 * 1024
DEFAULT_RESERVE = 1024 * MIB
DEFAULT_CAP = 256 * MIB
CHUNK = MIB


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


class StorageLimitError(OSError):
    """The destination volume has reached the configured free-space floor."""


class RenditionLimitError(ValueError):
    """This rendition exceeds the study’s configured download size."""


def room(folder, reserve, needed):
    if shutil.disk_usage(folder).free < reserve + needed:
        raise StorageLimitError("Free-space floor reached; resume after freeing space")


def dump(path, record):
    save(path, json.dumps(record, indent=2) + "\n")


def download(vid, spool, cap, reserve):
    # One direct video stream avoids a second audio file and a merged copy.
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "format": "bestvideo[protocol=https][height<=720]/best[protocol=https][height<=720]",
    }
    with YoutubeDL(opts) as yt:
        info = yt.extract_info("https://www.youtube.com/watch?v=" + vid, download=False)
    if info["id"] != vid or info.get("is_live") or info.get("protocol") != "https":
        raise ValueError("Expected one direct HTTPS recording of the selected upload")
    size = info.get("filesize")
    if size and size > cap:
        raise RenditionLimitError("Rendition exceeds the per-video limit")
    room(spool, reserve, (size or CHUNK) + 8 * MIB)
    part = spool / (vid + ".part")
    ready = spool / (vid + ".video")
    try:
        with urlopen(
            Request(info["url"], headers=info.get("http_headers", {})), timeout=45
        ) as resp:
            length = int(resp.headers.get("Content-Length") or 0)
            if length > cap:
                raise RenditionLimitError("HTTP response exceeds the per-video limit")
            room(spool, reserve, length + 8 * MIB)
            count = 0
            with part.open("wb") as f:
                while block := resp.read(CHUNK):
                    count += len(block)
                    if count > cap:
                        raise RenditionLimitError(
                            "Video exceeded byte cap while streaming"
                        )
                    room(spool, reserve, len(block) + 8 * MIB)
                    f.write(block)
            if not count or (length and count != length) or (size and count != size):
                raise IOError("Incomplete rendition")
        dump(
            spool / (vid + ".json"),
            dict(
                format_id=info["format_id"],
                height=info.get("height"),
                bytes=count,
                acquired_utc=now(),
            ),
        )
        part.replace(ready)
    finally:
        part.unlink(missing_ok=True)
    return ready


def verify(folder, complete=None):
    if complete is None:
        complete = json.loads((folder / "complete.json").read_text())
    plan_path = folder / "plan.json"
    if sha(plan_path) != complete["plan_sha256"]:
        raise ValueError(f"Changed plan: {folder}")
    plan = json.loads(plan_path.read_text())
    frames = complete["frames"]
    if sorted(r["requested_ms"] for r in frames) != sorted(
        r["requested_ms"] for r in plan["moments"]
    ):
        raise ValueError("Frame set does not match frozen timestamps")
    for row in frames:
        path = folder / row["file"]
        if sha(path) != row["sha256"]:
            raise ValueError(f"Changed JPEG: {path}")
        with Image.open(path) as image:
            image.load()
    return plan


def extract(source, folder, vid, seed, n, provenance, reserve):
    checksum = sha(source)
    dest = folder / "plan.json"
    if dest.exists():
        plan = json.loads(dest.read_text())
        if (
            plan["video_id"],
            plan["seed"],
            plan["per_interval"],
            plan["source_sha256"],
        ) != (vid, seed, n, checksum):
            raise ValueError(
                "Source version or sampling design differs from frozen plan"
            )
        first = Fraction(plan["first_time"])
    else:
        first, end, base = timeline(source)
        plan = dict(
            video_id=vid,
            seed=seed,
            per_interval=n,
            source_sha256=checksum,
            source_bytes=source.stat().st_size,
            first_time=str(first),
            duration=str(end - first),
            stream_time_base=base,
            source=provenance,
            software={p: version(p) for p in ("av", "pillow", "yt-dlp")},
            moments=draw(vid, seed, end - first, n),
        )
        dump(dest, plan)
    frames = []
    for moment, frame in displayed_frames(source, first, plan["moments"]):
        room(folder, reserve, 8 * MIB)
        name = f"i{moment['interval']}_r{moment['rank']}.jpg"
        tmp = folder / (name + ".tmp")
        frame.to_image().convert("RGB").save(tmp, format="JPEG", quality=90)
        tmp.replace(folder / name)
        frames.append(
            {
                **moment,
                "pts": frame.pts,
                "time_base": str(frame.time_base),
                "file": name,
                "sha256": sha(folder / name),
            }
        )
    complete = dict(finished_utc=now(), plan_sha256=sha(dest), frames=frames)
    verify(folder, complete)
    dump(folder / "complete.json", complete)


def event(out, vid, status, **details):
    # Remote exception messages can include expiring signed URLs.
    with (out / "attempts.jsonl").open("a") as log:
        log.write(
            json.dumps(dict(video_id=vid, utc=now(), status=status, **details)) + "\n"
        )


def run(
    manifest,
    out,
    local=None,
    seed="20261121",
    n=2,
    cap=DEFAULT_CAP,
    reserve=DEFAULT_RESERVE,
    allow_yt_dlp=False,
):
    if n < 1 or cap < 1 or reserve < 0:
        raise ValueError("Invalid sampling or disk limits")
    with manifest.open(newline="", encoding="utf8") as f:
        selected = list(csv.DictReader(f))
    ids = [r["video_id"] for r in selected]
    if (
        not ids
        or len(set(ids)) != len(ids)
        or any(not re.fullmatch(r"[A-Za-z0-9_-]{11}", i) for i in ids)
    ):
        raise ValueError("Expected a nonempty manifest of unique YouTube IDs")
    if any(r.get("decision") != "eligible" for r in selected):
        raise ValueError("Input includes an unresolved or excluded video")
    out.mkdir(parents=True, exist_ok=True)
    spool = out / "spool"
    spool.mkdir(exist_ok=True)
    with (out / ".acquisition.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        for vid in ids:
            folder = out / vid
            folder.mkdir(exist_ok=True)
            owned = spool / (vid + ".video")
            meta = spool / (vid + ".json")
            if any(p.stem != vid for p in spool.iterdir()):
                # Completed earlier IDs may precede the interrupted one on resume.
                if not (folder / "complete.json").exists():
                    raise ValueError(
                        "Pending source belongs to another video; resume original manifest"
                    )
            stage = "verify"
            try:
                if (folder / "complete.json").exists():
                    plan = verify(folder)
                    if (plan["video_id"], plan["seed"], plan["per_interval"]) != (
                        vid,
                        seed,
                        n,
                    ):
                        raise ValueError(
                            "Completed sample has different parameters; use a new output"
                        )
                else:
                    stage = "acquire"
                    event(out, vid, "started", cap_bytes=cap, reserve_bytes=reserve)
                    room(out, reserve, 8 * MIB)
                    if owned.exists():
                        source = owned
                        provenance = json.loads(meta.read_text())
                    elif local is not None:
                        source = local / (vid + ".mp4")
                        provenance = {"local_source": str(source.resolve())}
                    elif allow_yt_dlp:
                        source = download(vid, spool, cap, reserve)
                        provenance = json.loads(meta.read_text())
                    else:
                        raise ValueError(
                            "Supply --local-sources DIRECTORY for frame extraction"
                        )
                    stage = "extract"
                    extract(source, folder, vid, seed, n, provenance, reserve)
                    event(out, vid, "completed", source_bytes=source.stat().st_size)
                owned.unlink(missing_ok=True)
                meta.unlink(missing_ok=True)
            except Exception as exc:
                event(out, vid, "failed", stage=stage, error_type=type(exc).__name__)
                raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("selected", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--local-sources", type=Path, help="Existing files named VIDEO_ID.mp4"
    )
    parser.add_argument(
        "--allow-yt-dlp",
        action="store_true",
        help="Explicitly use the unofficial downloader",
    )
    parser.add_argument("--seed", default="20261121")
    parser.add_argument("--per-interval", type=int, default=2)
    parser.add_argument("--max-video-mib", type=int, default=256)
    parser.add_argument("--reserve-mib", type=int, default=1024)
    args = parser.parse_args()
    run(
        args.selected,
        args.output,
        args.local_sources,
        args.seed,
        args.per_interval,
        args.max_video_mib * MIB,
        args.reserve_mib * MIB,
        args.allow_yt_dlp,
    )
