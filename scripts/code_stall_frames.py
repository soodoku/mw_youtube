"""Send each frozen frame to Muse and export linked frame and sighting records."""

import argparse
import base64
import json
from pathlib import Path

from prepare_frame_review import KEY, META, prepare, table

from mw_youtube.codebook import book_sha, frozen_context, prompt, schema, validate
from mw_youtube.records import save


def run(folder, out, cap, ledger=None):
    from museclient import Client

    rows = prepare(folder)
    frozen = json.loads((out / "review_manifest.json").read_text())
    book = json.loads((out / "codebook.json").read_text())
    expected = {"codebook_sha256": book_sha(book), "frames": rows}
    instruction = prompt(book)
    context = frozen_context(out, frozen, rows[0]["video_id"], book)
    if context is not None:
        expected["video_context_sha256"] = frozen["video_context_sha256"]
        instruction += "\n\nPublisher metadata (quoted JSON):\n" + context
    if frozen != expected:
        raise ValueError(
            "Review manifest differs from the current frames or dictionary"
        )
    client = Client(
        cap_usd=cap, workdir=out / "muse", model=book["model"], ledger=ledger
    )
    frames, people = [], []
    for row in rows:
        image = base64.b64encode((folder / row["jpeg"]).read_bytes()).decode("ascii")
        content = [
            {"type": "text", "text": instruction},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image}"},
            },
        ]
        answer, call = client.complete(
            [{"role": "user", "content": content}],
            schema(book),
            name="stall_frame",
            with_call=True,
            max_completion_tokens=4800,
            key_extra={
                "codebook": book_sha(book),
                "sha256": row["sha256"],
                **(
                    {"context_sha256": expected["video_context_sha256"]}
                    if context
                    else {}
                ),
            },
        )
        validate(answer, book)
        frame = {
            **row,
            **{
                k: answer[k]
                for k in [*book["frame_fields"], "n_enumerated", "evidence"]
            },
            "model": book["model"],
            "call_id": call.name,
            "codebook_sha256": book_sha(book),
        }
        ids = {k: row[k] for k in KEY}
        people.extend({**ids, **p} for p in answer["sightings"])
        frames.append(frame)
        save(
            out / (row["jpeg"] + ".json"),
            json.dumps({"frame": frame, "sightings": answer["sightings"]}, indent=2)
            + "\n",
        )
    table(
        out / "muse_frames.csv",
        frames,
        [
            *META,
            *book["frame_fields"],
            "n_enumerated",
            "evidence",
            "model",
            "call_id",
            "codebook_sha256",
        ],
    )
    table(
        out / "muse_people.csv",
        people,
        [*KEY, "person_id", *book["person_fields"], "cue"],
    )
    save(out / "muse_spend.json", json.dumps(client.spend(), indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frames", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--cap-usd", type=float, required=True)
    parser.add_argument(
        "--ledger", type=Path, required=True, help="Shared spending ledger for the draw"
    )
    args = parser.parse_args()
    run(args.frames, args.output, args.cap_usd, args.ledger)
