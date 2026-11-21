"""Freeze the human coding materials without showing model labels."""

import argparse
import csv
import hashlib
import io
import json
import os
from html import escape
from pathlib import Path
from urllib.parse import quote

from collect_candidates import save
from stall_codebook import BOOK, FRAME, PERSON, book_sha, dictionary_html, schema

META = ("video_id", "interval", "rank", "requested_ms", "jpeg", "sha256")
KEY = ("video_id", "interval", "rank")


def table(path, rows, columns):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    save(path, buffer.getvalue())


def prepare(folder):
    plan_file = folder / "plan.json"
    plan = json.loads(plan_file.read_text())
    completed = json.loads((folder / "complete.json").read_text())
    if hashlib.sha256(plan_file.read_bytes()).hexdigest() != completed["plan_sha256"]:
        raise ValueError("Changed sampling plan")
    rows = []
    for f in completed["frames"]:
        path = folder / f["file"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != f["sha256"]:
            raise ValueError(f"Changed image {path}")
        rows.append(
            {
                **{k: f[k] for k in ("interval", "rank", "requested_ms", "sha256")},
                "jpeg": f["file"],
                "video_id": plan["video_id"],
            }
        )
    expected = sorted(
        (m["interval"], m["rank"], m["requested_ms"]) for m in plan["moments"]
    )
    if (
        not rows
        or sorted((r["interval"], r["rank"], r["requested_ms"]) for r in rows)
        != expected
    ):
        raise ValueError("Incomplete frame set")
    return rows


def gallery(folder, out, rows):
    cards = []
    for row in rows:
        url = quote(os.path.relpath(folder / row["jpeg"], out))
        label = f"Interval {row['interval'] + 1}, draw {row['rank']}"
        seconds = row["requested_ms"] / 1000
        time_label = f"{int(seconds // 60):02d}:{seconds % 60:06.3f}"
        cards.append(
            f'<figure><a href="{url}"><img src="{url}" alt="{label}"></a>'
            f"<figcaption>{label} · {time_label}</figcaption></figure>"
        )
    vid = escape(rows[0]["video_id"])
    return (
        f'<!doctype html><meta charset="utf-8"><title>Frame review · {vid}</title>'
        "<style>body{font:16px system-ui;margin:2rem}main{display:grid;"
        "grid-template-columns:repeat(auto-fit,minmax(min(100%,25rem),1fr));gap:1rem}"
        "img{width:100%}figure{margin:0}figcaption{margin:.4rem 0}</style>"
        f"<h1>Frame review · {vid}</h1><p>Record setting, shot, service area and quality "
        'in the <a href="human_frames.csv">frame sheet</a> and each visible person '
        'in the <a href="human_people.csv">sightings sheet</a>. '
        'Read the <a href="codebook.html">coding dictionary</a>. Select an '
        "image to see its original resolution.</p><main>" + "".join(cards) + "</main>"
    )


def run(folder, out):
    rows = prepare(folder)
    out.mkdir(parents=True, exist_ok=True)
    snapshot = {"codebook_sha256": book_sha(), "frames": rows}
    frozen = out / "review_manifest.json"
    if frozen.exists() and json.loads(frozen.read_text()) != snapshot:
        raise ValueError("Different codebook or images; choose a new review directory")
    save(frozen, json.dumps(snapshot, indent=2) + "\n")
    for filename, records, columns in [
        (
            "human_frames.csv",
            rows,
            [*META, *FRAME, "n_enumerated", "evidence", "reviewer", "review_date"],
        ),
        ("human_people.csv", [], [*KEY, "person_id", *PERSON, "cue"]),
    ]:
        if not (out / filename).exists():
            table(out / filename, records, columns)
    save(out / "codebook.json", json.dumps(BOOK, indent=2, ensure_ascii=False) + "\n")
    save(out / "muse_response.schema.json", json.dumps(schema(), indent=2) + "\n")
    save(out / "codebook.html", dictionary_html())
    save(out / "human_review.html", gallery(folder, out, rows))
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frames", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    run(args.frames, args.output)
