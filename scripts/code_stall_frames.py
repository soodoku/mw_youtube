"""Send each frozen frame to Muse and export linked frame and sighting records."""

import argparse
import base64
import json
from pathlib import Path

from collect_candidates import save
from prepare_frame_review import KEY, META, prepare, table
from stall_codebook import BOOK, FRAME, PERSON, book_sha, prompt, schema, validate


def run(folder, out, cap):
    from museclient import Client

    rows = prepare(folder)
    frozen = json.loads((out / "review_manifest.json").read_text())
    if frozen != {"codebook_sha256": book_sha(), "frames": rows}:
        raise ValueError(
            "Review manifest differs from the current frames or dictionary"
        )
    client = Client(cap_usd=cap, workdir=out / "muse", model=BOOK["model"])
    frames, people = [], []
    for row in rows:
        image = base64.b64encode((folder / row["jpeg"]).read_bytes()).decode("ascii")
        content = [
            {"type": "text", "text": prompt()},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image}"},
            },
        ]
        answer, call = client.complete(
            [{"role": "user", "content": content}],
            schema(),
            name="stall_frame",
            with_call=True,
            max_completion_tokens=4800,
            key_extra={"codebook": book_sha(), "sha256": row["sha256"]},
        )
        validate(answer)
        frame = {
            **row,
            **{k: answer[k] for k in [*FRAME, "n_enumerated", "evidence"]},
            "model": BOOK["model"],
            "call_id": call.name,
            "codebook_sha256": book_sha(),
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
            *FRAME,
            "n_enumerated",
            "evidence",
            "model",
            "call_id",
            "codebook_sha256",
        ],
    )
    table(out / "muse_people.csv", people, [*KEY, "person_id", *PERSON, "cue"])
    save(out / "muse_spend.json", json.dumps(client.spend(), indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frames", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--cap-usd", type=float, required=True)
    args = parser.parse_args()
    run(args.frames, args.output, args.cap_usd)
