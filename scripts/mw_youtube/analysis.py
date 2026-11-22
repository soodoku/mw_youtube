"""Join a selected video manifest, frame draws and one coder into a frame-level analysis file."""

import hashlib
import json
from collections import defaultdict
from fractions import Fraction
from math import ceil

from .codebook import FRAME, book_sha, frozen_context
from .counts import GROUPS, HOST_SCOPES, SCOPES, key, summarize
from .records import META, read


def unique(rows, field):
    by_id = {r[field]: r for r in rows}
    if len(rows) != len(by_id):
        raise ValueError(f"Repeated {field} in input")
    return by_id


def annotations(directories, coder):
    labeled = {}
    for directory in directories:
        manifest = json.loads((directory / "review_manifest.json").read_text())
        frames = read(directory / f"{coder}_frames.csv")
        archived = json.loads((directory / "codebook.json").read_text())
        if manifest["codebook_sha256"] != book_sha(archived) or [
            {k: str(r[k]) for k in META} for r in manifest["frames"]
        ] != [{k: r[k] for k in META} for r in frames]:
            raise ValueError("Annotation manifest or frame identity differs")
        frozen_context(directory, manifest, frames[0]["video_id"], archived)
        scopes = defaultdict(dict)
        for r in summarize(frames, read(directory / f"{coder}_people.csv"), archived):
            scopes[key(r)][r["scope"]] = r
        for frame in frames:
            ident = key(frame)
            if ident in labeled:
                raise ValueError(f"Repeated coding for {ident}")
            labeled[ident] = (
                {**frame, "codebook_sha256": book_sha(archived)},
                scopes[ident],
            )
    return labeled


def clock_time(ms):
    minutes, ms = divmod(ms, 60000)
    sec, millis = divmod(ms, 1000)
    return f"{minutes:02d}:{sec:02d}.{millis:03d}"


def build(snapshot, selection, directories, coder, frame_root=None, host_fields=False):
    selection_sha = hashlib.sha256(
        selection.read_text(encoding="utf8").encode()
    ).hexdigest()
    selected = unique(read(selection), "video_id")
    catalog = unique(
        [
            json.loads(line)
            for line in (snapshot / "video_metadata.jsonl").read_text().splitlines()
        ],
        "video_id",
    )
    labeled = annotations(directories, coder)
    host_fields = host_fields or any(
        "vendor" in scopes for _, scopes in labeled.values()
    )
    design = json.loads((snapshot / "result.json").read_text())
    digest = hashlib.sha256()
    for name in ("queries.json", "search_counts.csv", "search_hits.csv"):
        digest.update(
            hashlib.sha256(
                (snapshot / name).read_text(encoding="utf8").encode()
            ).digest()
        )
    collection_id = digest.hexdigest()
    hits = [
        {**r, "collection_id": collection_id}
        for r in read(snapshot / "search_hits.csv")
        if r["video_id"] in selected
    ]
    hit_counts = defaultdict(set)
    for hit in hits:
        hit_counts[hit["video_id"]].add(hit["search_id"])
    if set(hit_counts) != set(selected):
        raise ValueError("Selected video lacks a discovery hit")
    output = []
    coverage = []
    for vid, sel in selected.items():
        folder = (frame_root or snapshot / "frames") / vid
        meta = catalog[vid]
        if (
            not meta["channel_id"]
            or meta["channel_id"] != sel["channel_id"]
            or meta["city"] != sel["city"]
        ):
            raise ValueError(f"Video metadata does not match selection for {vid}")
        identifiers = dict(
            snapshot=snapshot.name,
            collection_id=collection_id,
            selection_sha256=selection_sha,
            city=sel["city"],
            publication_year=design["year"],
            topic=design["topic"],
            video_id=vid,
            channel_id=meta["channel_id"],
        )
        flow = {
            **identifiers,
            "video_rank": sel["video_rank"],
            "planned_moments": 0,
            "extracted": 0,
            "coded": 0,
        }
        coverage.append(flow)
        if not (folder / "plan.json").exists():
            continue
        plan = json.loads((folder / "plan.json").read_text())
        if plan["video_id"] != vid:
            raise ValueError("Wrong source plan")
        done = folder / "complete.json"
        if done.exists():
            receipt = json.loads(done.read_text())
            if (
                receipt["plan_sha256"]
                != hashlib.sha256((folder / "plan.json").read_bytes()).hexdigest()
            ):
                raise ValueError("Changed source plan")
            images = unique(receipt["frames"], "requested_ms")
        else:
            images = {}
        duration = Fraction(plan["duration"])
        duration_ms = ceil(1000 * duration)
        n = plan["per_interval"]
        flow["planned_moments"] = len(plan["moments"])
        expected = {(i, j) for i in range(3) for j in range(1, n + 1)}
        drawn = [(r["interval"], r["rank"]) for r in plan["moments"]]
        unique(plan["moments"], "requested_ms")
        if len(drawn) != len(expected) or set(drawn) != expected:
            raise ValueError("Invalid interval/rank grid")
        if done.exists() and set(images) != {
            r["requested_ms"] for r in plan["moments"]
        }:
            raise ValueError("Incomplete extraction receipt")
        for moment in sorted(plan["moments"], key=lambda x: x["requested_ms"]):
            interval, rank, ms = (
                moment[k] for k in ("interval", "rank", "requested_ms")
            )
            identity = (vid, str(interval), str(rank))
            item = images.get(ms)
            frame, counts = labeled.pop(identity, ({}, {}))
            if frame and (
                not item
                or int(frame["requested_ms"]) != ms
                or frame["sha256"] != item["sha256"]
            ):
                raise ValueError(f"Coding does not match frozen image {identity}")
            if item and (item["interval"], item["rank"]) != (interval, rank):
                raise ValueError("Extraction and frame draw disagree")
            flow["extracted"] += int(bool(item))
            flow["coded"] += int(bool(frame))
            grid = ceil(1000 * duration * (interval + 1) / 3) - ceil(
                1000 * duration * interval / 3
            )
            source = {**plan, **(item or {})}
            elapsed = (
                Fraction(item["pts"]) * Fraction(item["time_base"])
                - Fraction(source["first_time"])
                if item and item["pts"] is not None
                else None
            )
            source_version = (
                source.get("source_version")
                or source["source_sha256"]
                or hashlib.sha256((folder / "plan.json").read_bytes()).hexdigest()
            )
            row = {
                **identifiers,
                "searches_returning_video": len(hit_counts[vid]),
                "video_rank": sel["video_rank"],
                "video_seed": sel["sample_seed"],
                "frame_seed": plan["seed"],
                "place": sel["place"],
                "published_utc": meta["published_utc"],
                "recording_date": meta["recording_date"],
                "audio_language": meta["audio_language"],
                "view_count": meta["view_count"],
                "metadata_retrieved_utc": meta["retrieved_utc"],
                "source_sha256": source["source_sha256"],
                "video_duration_s": float(duration),
                **moment,
                "frame_id": f"{vid}_{source_version}_{ms}",
                "requested_time": clock_time(ms),
                "capture_method": source.get("capture_method", "file"),
                "player_time_s": item.get("player_time_s") if item else None,
                "displayed_time_s": float(elapsed) if elapsed is not None else None,
                "pts": item["pts"] if item else None,
                "time_base": item["time_base"] if item else None,
                "source_first_time_s": source["first_time"],
                "jpeg": item["file"] if item else None,
                "jpeg_sha256": item["sha256"] if item else None,
                "extracted": int(bool(item)),
                "watch_at": meta["watch_url"] + "&t=" + str(ms // 1000) + "s",
                "interval_grid_ms": grid,
                "draws_per_interval": n,
                "p_moment_given_video": n / grid,
                "within_video_weight": grid / (duration_ms * n),
                "coded": int(bool(frame)),
                "coder": coder,
                "codebook_sha256": frame.get("codebook_sha256"),
                "model": frame.get("model"),
                "call_id": frame.get("call_id"),
                **{k: frame.get(k) for k in FRAME},
                "n_enumerated": frame.get("n_enumerated"),
            }
            for scope in (*SCOPES, *(HOST_SCOPES if host_fields else ())):
                for col in GROUPS:
                    row[f"{scope}_{col}"] = counts.get(scope, {}).get(col)
            # Clearly off-site frames make zero contribution to a whole-video stall tally.
            for col in GROUPS:
                val = row[f"worker_and_patron_{col}"]
                offsite = frame.get("setting") in {
                    "other_public_space",
                    "restaurant_interior",
                    "other_setting",
                }
                known_empty = (
                    frame.get("quality") == "countable"
                    and int(frame["n_enumerated"]) == 0
                )
                if offsite or known_empty:
                    val = 0
                row["primary_" + col] = val
            w, m = row["primary_n_women"], row["primary_n_men"]
            row["primary_n_classified"] = None if w is None else w + m
            output.append(row)
    if labeled:
        raise ValueError("Coded frames outside selection or draw")
    return output, coverage, hits
