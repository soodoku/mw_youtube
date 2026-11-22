"""The same dictionary drives the Muse request, validation, and human instructions."""

import hashlib
import json
from html import escape

from .design import CONFIG

BOOK = json.loads((CONFIG / "stall_frame_codebook.json").read_text())
CONTEXT_BOOK = json.loads((CONFIG / "stall_frame_codebook_v4.json").read_text())
FRAME = BOOK["frame_fields"]
PERSON = BOOK["person_fields"]


def book_sha(book=BOOK):
    return hashlib.sha256(
        json.dumps(book, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def prompt(book=BOOK):
    sections = ["Code one street-food video frame.", *book["instructions"]]
    for field, choices in book["categories"].items():
        sections.append(
            field + "\n" + "\n".join(f"{k}: {v}" for k, v in choices.items())
        )
    return "\n\n".join(sections)


def dictionary_html(book=BOOK):
    return (
        '<!doctype html><meta charset="utf-8"><title>Frame codebook</title>'
        "<style>body{max-width:54rem;margin:2rem auto;font:17px/1.5 system-ui}"
        "pre{white-space:pre-wrap;font:inherit}</style><h1>Frame coding dictionary</h1><pre>"
        + escape(prompt(book))
        + "</pre>"
    )


def frozen_context(directory, manifest, video_id, book):
    """Read exactly the publisher text that both coders received for this upload."""
    if "context_fields" not in book:
        return None
    body = (directory / "video_context.json").read_bytes()
    data = json.loads(body)
    if (
        set(data) != set(book["context_fields"])
        or data["video_id"] != video_id
        or hashlib.sha256(body).hexdigest() != manifest.get("video_context_sha256")
    ):
        raise ValueError("Video context differs from the frozen review manifest")
    return body.decode()


def object_schema(properties):
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def choices(fields, book):
    return {k: {"type": "string", "enum": list(book["categories"][k])} for k in fields}


def schema(book=BOOK):
    person = object_schema(
        {
            "person_id": {"type": "integer", "minimum": 1},
            **choices(book["person_fields"], book),
            "cue": {"type": "string"},
        }
    )
    return object_schema(
        {
            **choices(book["frame_fields"], book),
            "n_enumerated": {"type": ["integer", "null"], "minimum": 0},
            "evidence": {"type": "string"},
            "sightings": {"type": "array", "items": person},
        }
    )


def validate(answer, book=BOOK):
    for field in book["frame_fields"]:
        if answer[field] not in book["categories"][field]:
            raise ValueError(f"Unknown {field}")
    people = answer["sightings"]
    expected = None if answer["quality"] == "unreadable" else len(people)
    if answer["n_enumerated"] != expected:
        raise ValueError("Frame enumeration differs from the submitted sightings")
    if not answer["evidence"].strip():
        raise ValueError("Missing frame evidence")
    if answer["quality"] == "unreadable" and (
        people or any(answer[k] != "unclear" for k in FRAME if k != "quality")
    ):
        raise ValueError("Unreadable frame has observations")
    for i, p in enumerate(people, 1):
        if p["person_id"] != i or not p["cue"].strip():
            raise ValueError("Sightings need consecutive IDs and visible cues")
        if any(p[f] not in book["categories"][f] for f in book["person_fields"]):
            raise ValueError("Unrecognized sighting category")
