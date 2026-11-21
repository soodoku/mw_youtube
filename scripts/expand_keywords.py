"""Draft or freeze a city-specific multilingual search vocabulary before collection."""

import argparse
import json
from pathlib import Path

from mw_youtube.design import CONFIG, validate_vocabulary
from mw_youtube.records import save

SCHEMA = json.loads((CONFIG / "keywords.schema.json").read_text())
MODEL = "muse-spark-1.3-contributor"
PROMPT = (
    "Suggest discoverable publisher search phrases for this topic in each requested language. "
    "Use idiomatic variants across distinct concepts. Each phrase must contain the literal "
    "placeholder {city} exactly once. Give each entry a unique lowercase ASCII keyword_id. "
    "Use no inferred gender or crowd criterion. The research team will review the draft."
)


def propose(city, topic, description, out, cap, ledger):
    from museclient import Client

    if out.exists():
        raise ValueError("Draft already exists; preserve the reviewed input")
    languages = list(json.loads((CONFIG / "cities.json").read_text())[city]["names"])
    request = dict(city=city, topic=topic, description=description, languages=languages)
    client = Client(
        cap_usd=cap, ledger=ledger, workdir=out.parent / "keyword_calls", model=MODEL
    )
    answer, call = client.complete(
        [
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": json.dumps(request, ensure_ascii=False)},
        ],
        schema=SCHEMA,
        name="query_keywords",
        with_call=True,
        max_completion_tokens=4000,
    )
    draft = {
        **request,
        **answer,
        "model": MODEL,
        "prompt": PROMPT,
        "call_id": call.name,
    }
    validate_vocabulary(draft, city, topic, languages)
    save(out, json.dumps(draft, indent=2, ensure_ascii=False) + "\n")


def freeze(draft, out, reviewer):
    if out.exists() or not reviewer.strip():
        raise ValueError(
            "Provide a reviewer and a new destination for the frozen vocabulary"
        )
    packet = json.loads(draft.read_text())
    langs = json.loads((CONFIG / "cities.json").read_text())[packet["city"]]["names"]
    validate_vocabulary(packet, packet["city"], packet["topic"], langs)
    from datetime import datetime, timezone

    packet.update(
        reviewer=reviewer.strip(), reviewed_utc=datetime.now(timezone.utc).isoformat()
    )
    save(out, json.dumps(packet, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    q = sub.add_parser("propose")
    for name in ("city", "topic", "description"):
        q.add_argument("--" + name, required=True)
    q.add_argument("--cap-usd", type=float, required=True)
    q.add_argument("--ledger", type=Path, required=True)
    q.add_argument("output", type=Path)
    f = sub.add_parser("freeze")
    f.add_argument("draft", type=Path)
    f.add_argument("output", type=Path)
    f.add_argument("--reviewer", required=True)
    args = p.parse_args()
    if args.action == "freeze":
        freeze(args.draft, args.output, args.reviewer)
    else:
        propose(
            args.city,
            args.topic,
            args.description,
            args.output,
            args.cap_usd,
            args.ledger,
        )
