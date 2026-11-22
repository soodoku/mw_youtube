"""Freeze the human coding materials without showing model labels."""

import argparse
import hashlib
import json
import os
from html import escape
from pathlib import Path
from urllib.parse import quote

from mw_youtube.codebook import (
    BOOK,
    CONTEXT_BOOK,
    FRAME,
    book_sha,
    dictionary_html,
    schema,
)
from mw_youtube.records import KEY, META, save, table


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


def run(folder, out, catalog=None):
    rows = prepare(folder)
    out.mkdir(parents=True, exist_ok=True)
    book = CONTEXT_BOOK if catalog is not None else BOOK
    snapshot = {"codebook_sha256": book_sha(book), "frames": rows}
    if catalog is not None:
        vid = rows[0]["video_id"]
        with catalog.open() as stream:
            items = [r for line in stream if (r := json.loads(line))["video_id"] == vid]
        if len(items) != 1:
            raise ValueError(f"Expected exactly one metadata record for {vid}")
        context = {field: items[0][field] for field in book["context_fields"]}
        body = json.dumps(context, indent=2, ensure_ascii=False) + "\n"
        snapshot["video_context_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    frozen = out / "review_manifest.json"
    if frozen.exists() and json.loads(frozen.read_text()) != snapshot:
        raise ValueError("Different codebook or images; choose a new review directory")
    if catalog is not None:
        save(out / "video_context.json", body)
    save(frozen, json.dumps(snapshot, indent=2) + "\n")
    for filename, records, columns in [
        (
            "human_frames.csv",
            rows,
            [*META, *FRAME, "n_enumerated", "evidence", "reviewer", "review_date"],
        ),
        ("human_people.csv", [], [*KEY, "person_id", *book["person_fields"], "cue"]),
    ]:
        if not (out / filename).exists():
            table(out / filename, records, columns)
    save(out / "codebook.json", json.dumps(book, indent=2, ensure_ascii=False) + "\n")
    save(out / "muse_response.schema.json", json.dumps(schema(book), indent=2) + "\n")
    save(out / "codebook.html", dictionary_html(book))
    save(out / "human_review.html", gallery(folder, out, rows))
    if catalog is not None:
        page = out / "human_review.html"
        save(
            page,
            page.read_text().replace(
                "<main>",
                '<p><a href="video_context.json">Video metadata for both coders</a></p><main>',
            ),
        )
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frames", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--catalog",
        type=Path,
        help="Frozen video_metadata.jsonl for v4 vendor and host coding",
    )
    args = parser.parse_args()
    run(args.frames, args.output, args.catalog)
