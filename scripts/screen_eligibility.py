"""Screen a frozen ranked queue using explicit exclusions and cached model judgments."""

import argparse
import csv
import fcntl
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from collect_candidates import save, write_table
from search_plan import CONFIG

FIELDS = [
    "city",
    "video_id",
    "video_rank",
    "input_sha256",
    "protocol_sha256",
    "decision",
    "reason",
    "place_quote",
    "setting_quote",
    "method",
    "call_id",
    "review_date",
]
ANSWER = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "decision": {"type": "string", "enum": ["eligible", "excluded", "unclear"]},
        **{k: {"type": "string"} for k in ("reason", "place_quote", "setting_quote")},
    },
    "required": ["decision", "reason", "place_quote", "setting_quote"],
}


def digest(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def explicit_exclusion(record, series):
    """Require a publisher show credit AND independent cast and episode credits."""
    desc = record["description"]
    for name in series:
        credit = re.search(
            r"^\s*Show Name\s*[:-]\s*" + re.escape(name) + r"\s*$", desc, re.I | re.M
        )
        if (
            credit
            and re.search(r"^\s*Star Cast\s*[:-]", desc, re.I | re.M)
            and re.search(
                r"^\s*Episode(?:[ \t]+(?:No\.?|Number))?[ \t]*[:-][ \t]*\d",
                desc,
                re.I | re.M,
            )
        ):
            return {
                "decision": "excluded",
                "reason": "publisher identifies an episode of a listed scripted series",
                "setting_quote": credit[0].strip(),
                "place_quote": "",
            }
    return None


def checked(answer, record):
    """A valid JSON answer can still contain fabricated or missing evidence."""
    reason = answer["reason"].strip()
    place, setting = answer["place_quote"], answer["setting_quote"]
    fields = [record["title"], record["description"]]
    quotes = [q for q in [place, setting] if q]
    supported = all(any(q in field for field in fields) for q in quotes)
    status = answer["decision"]
    if (
        not supported
        or not reason
        or (status in {"eligible", "excluded"} and not setting.strip())
        or (status == "eligible" and not place.strip())
    ):
        return {
            "decision": "unclear",
            "reason": "missing or ungrounded model evidence",
            "place_quote": "",
            "setting_quote": "",
        }
    return answer


def prepare(folder):
    config = json.loads((CONFIG / "eligibility.json").read_text())
    run = json.loads((folder / "result.json").read_text())
    if run["topic"] != config["topic"]:
        raise ValueError(f"No screening protocol for {run['topic']}")
    cities = json.loads((CONFIG / "cities.json").read_text())
    topics = json.loads((CONFIG / "topics.json").read_text())
    task = {
        "topic": topics[run["topic"]]["description"],
        "boundary": cities[run["city"]]["boundary"],
    }
    version = digest(
        [config, task, ANSWER, hashlib.sha256(Path(__file__).read_bytes()).hexdigest()]
    )
    metadata = {}
    for file in sorted((folder / "responses").glob("metadata-*.json")):
        response = json.loads(file.read_text())
        for item in response["items"]:
            metadata[item["id"]] = (item["snippet"], response["retrieved_utc"][:10])
    with (folder / "screening.csv").open(newline="", encoding="utf8") as f:
        queue = sorted(csv.DictReader(f), key=lambda row: int(row["video_rank"]))
    return config, task, version, metadata, queue


def screen(folder, through=0, cap=None, client_factory=None):
    with (folder / ".eligibility.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return screen_locked(folder, through, cap, client_factory)


def screen_locked(folder, through, cap, client_factory):
    config, task, version, metadata, queue = prepare(folder)
    cache = folder / "eligibility" / version
    cache.mkdir(parents=True, exist_ok=True)
    save(
        cache / "protocol.json",
        json.dumps(
            {"config": config, "task": task, "schema": ANSWER},
            ensure_ascii=False,
            indent=2,
        ),
    )
    client = None
    rows = []
    for row in queue:
        vid = row["video_id"]
        snippet, source_date = metadata.get(vid, ({}, ""))
        packet = {
            "video_id": vid,
            "title": snippet.get("title", row["title"]),
            "description": snippet.get("description", ""),
            **task,
        }
        fingerprint = digest(packet)
        stored = cache / f"{fingerprint}.json"
        verdict = explicit_exclusion(packet, config["scripted_series"])
        method = "rule"
        call_id = ""
        if verdict is None and stored.exists():
            saved = json.loads(stored.read_text())
            verdict, call_id = saved["verdict"], saved["call_id"]
            date = saved["review_date"]
            method = "muse"
        elif verdict is None and int(row["video_rank"]) <= through:
            if client is None:
                if client_factory is None:
                    from museclient import Client

                    client_factory = Client
                client = client_factory(
                    cap_usd=cap,
                    workdir=folder / "eligibility" / "muse",
                    model=config["model"],
                )
            messages = [
                {"role": "system", "content": config["prompt"]},
                {"role": "user", "content": json.dumps(packet, ensure_ascii=False)},
            ]
            answer, call = client.complete(
                messages,
                schema=ANSWER,
                name="eligibility",
                max_completion_tokens=1400,
                reasoning_effort="low",
                key_extra=version,
                with_call=True,
            )
            verdict = checked(answer, packet)
            call_id = call.name
            date = datetime.now(timezone.utc).date().isoformat()
            save(
                stored,
                json.dumps(
                    {
                        "input": packet,
                        "verdict": verdict,
                        "call_id": call_id,
                        "review_date": date,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            )
            method = "muse"
        if method == "rule":
            date = source_date if verdict else ""
        if verdict is None:
            method = "pending"
            verdict = {
                "decision": "pending",
                "reason": "",
                "place_quote": "",
                "setting_quote": "",
            }
        rows.append(
            {
                **{k: row[k] for k in ("city", "video_id", "video_rank")},
                "input_sha256": fingerprint,
                "protocol_sha256": version,
                **verdict,
                "method": method,
                "call_id": call_id,
                "review_date": date,
            }
        )
    write_table(folder / "machine_screening.csv", FIELDS, rows)
    return rows


def resolve(decisions, machine):
    """Use machine exclusions for unreviewed rows, preserving all reviewer judgments."""
    records = {(row["city"], row["video_id"]): row for row in machine}
    merged = []
    for row in decisions:
        evidence = records[(row["city"], row["video_id"])]
        if not row["decision"] and evidence["decision"] == "excluded":
            row = {
                **row,
                "decision": "excluded",
                "reason": evidence["reason"],
                "place": evidence["place_quote"],
                "evidence": evidence["setting_quote"],
                "reviewer": evidence["method"],
                "review_date": evidence["review_date"],
            }
        merged.append(row)
    return merged


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument(
        "--through-rank", type=int, default=0, help="Run Muse through this rank."
    )
    parser.add_argument(
        "--cap-usd", type=float, help="Total authorized Muse ledger cap."
    )
    args = parser.parse_args()
    if args.through_rank < 0 or (
        args.through_rank and not (args.cap_usd and args.cap_usd > 0)
    ):
        parser.error("A positive --through-rank requires a positive --cap-usd")
    rows = screen(args.snapshot, args.through_rank, args.cap_usd)
    print(dict(Counter((r["method"], r["decision"]) for r in rows)))
