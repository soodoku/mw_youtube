"""The same dictionary drives the Muse request, validation, and human instructions."""

import hashlib
import json
from html import escape
from pathlib import Path

BOOK = json.loads(
    (
        Path(__file__).resolve().parents[1] / "config/stall_frame_codebook.json"
    ).read_text()
)
FRAME = BOOK["frame_fields"]
PERSON = BOOK["person_fields"]


def book_sha():
    return hashlib.sha256(
        json.dumps(BOOK, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def prompt():
    sections = ["Code one street-food video frame.", *BOOK["instructions"]]
    for field, choices in BOOK["categories"].items():
        sections.append(
            field + "\n" + "\n".join(f"{k}: {v}" for k, v in choices.items())
        )
    return "\n\n".join(sections)


def dictionary_html():
    return (
        '<!doctype html><meta charset="utf-8"><title>Frame codebook</title>'
        "<style>body{max-width:54rem;margin:2rem auto;font:17px/1.5 system-ui}"
        "pre{white-space:pre-wrap;font:inherit}</style><h1>Frame coding dictionary</h1><pre>"
        + escape(prompt())
        + "</pre>"
    )


def object_schema(properties):
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def choices(fields):
    return {k: {"type": "string", "enum": list(BOOK["categories"][k])} for k in fields}


def schema():
    person = object_schema(
        {
            "person_id": {"type": "integer", "minimum": 1},
            **choices(PERSON),
            "cue": {"type": "string"},
        }
    )
    return object_schema(
        {
            **choices(FRAME),
            "n_enumerated": {"type": ["integer", "null"], "minimum": 0},
            "evidence": {"type": "string"},
            "sightings": {"type": "array", "items": person},
        }
    )


def validate(answer):
    for field in FRAME:
        if answer[field] not in BOOK["categories"][field]:
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
        if any(p[f] not in BOOK["categories"][f] for f in PERSON):
            raise ValueError("Unrecognized sighting category")
