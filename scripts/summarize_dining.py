"""Estimate women's share of diner and all-person sightings in a frozen draw."""

import argparse
import json
import math
import random
from collections import Counter
from pathlib import Path

from mw_youtube.codebook import book_sha, validate
from mw_youtube.counts import GROUPS
from mw_youtube.design import CONFIG
from mw_youtube.records import read, save, table

VENUES = {"street_stall", "restaurant_interior", "restaurant_outdoor"}
DINING = {
    "bite": {"eating_food"},
    "bite_or_sip": {"eating_food", "drinking"},
    "meal": {"eating_food", "drinking", "between_bites"},
}
FOOD = {"visibly_eating", "own_food_in_hand", "own_food_in_front", "shared_food"}
APPARENT = {
    "apparent_diner": (FOOD, {"food_venue"}),
    "including_uncertain_venue": (FOOD, {"food_venue", "uncertain"}),
    "apparent_diner_anywhere": (FOOD, {"food_venue", "uncertain", "elsewhere"}),
    "including_personal_drinks": (FOOD | {"beverage_only"}, {"food_venue"}),
}

CONTEXT = (
    "video_id",
    "channel_id",
    "frame_id",
    "interval",
    "rank",
    "requested_ms",
    "jpeg_sha256",
    "watch_at",
    "within_video_weight",
)
SCENES = (
    "setting",
    "quality",
    "shot",
    "service_area",
    "n_enumerated",
    "evidence",
    "model",
    "call_id",
    "codebook_sha256",
)


def load_draw(design, coding):
    book = json.loads((CONFIG / "stall_frame_codebook_v5.json").read_text())
    digest = book_sha(book)
    frames, people, weights = [], [], Counter()
    seen = set()
    for r in read(design):
        packet = coding / r["video_id"] / f"i{r['interval']}_r{r['rank']}.jpg.json"
        observation = json.loads(packet.read_text())
        scene = observation["frame"]
        if (
            r["frame_id"] in seen
            or r["jpeg_sha256"] != scene["sha256"]
            or any(
                str(scene[k]) != r[k]
                for k in ("video_id", "interval", "rank", "requested_ms")
            )
            or scene["codebook_sha256"] != digest
            or scene["model"] != book["model"]
        ):
            raise ValueError(f"Frame identity or protocol mismatch for {packet}")
        seen.add(r["frame_id"])
        validate({**scene, "sightings": observation["sightings"]}, book)
        frame = {**{k: r[k] for k in CONTEXT}, **{k: scene[k] for k in SCENES}}
        for scope in ("all_visible", "bite"):
            counted = Counter(
                person["group"]
                for person in observation["sightings"]
                if eligible({**scene, **person}, scope, "everyone", "all", False)
            )
            for column, group in GROUPS.items():
                frame[f"{scope}_{column}"] = (
                    None if scene["quality"] == "unreadable" else counted[group]
                )
        frames.append(frame)
        weights[r["video_id"]] += float(r["within_video_weight"])
        people.extend(
            {**{k: frame[k] for k in (*CONTEXT, "quality", "setting")}, **person}
            for person in observation["sightings"]
        )
    if not frames or any(not math.isclose(w, 1) for w in weights.values()):
        raise ValueError("Each selected video must have a complete weighted frame draw")
    return frames, people


def eligible(row, population, roles, venue, complete):
    if complete and row["quality"] != "countable":
        return False
    if population in APPARENT:
        food, venues = APPARENT[population]
        if row["meal_evidence"] not in food or row["dining_venue"] not in venues:
            return False
    elif population != "all_visible" and (
        row["at_venue"] != "yes"
        or row["setting"] not in VENUES
        or row["consumption"] not in DINING[population]
    ):
        return False
    if venue == "stall" and row["setting"] != "street_stall":
        return False
    if venue == "restaurant" and row["setting"] not in {
        "restaurant_interior",
        "restaurant_outdoor",
    }:
        return False
    host = row["host_status"] == "apparent_host"
    vendor = row["role"] == "vendor"
    return {
        "everyone": True,
        "exclude_hosts": not host,
        "exclude_vendors": not vendor,
        "exclude_both": not (host or vendor),
        "confirmed_nonhosts_nonvendors": row["host_status"] == "not_host"
        and row["role"] in {"other", "patron"},
    }[roles]


def cluster_interval(rows, clusters, field):
    totals = {g: [0.0, 0.0] for g in sorted(clusters)}
    for r in rows:
        weight = float(r["within_video_weight"])
        totals[r[field]][0] += weight * (r["group"] == "woman")
        totals[r[field]][1] += weight
    values = list(totals.values())
    informative = sum(den > 0 for _, den in values)
    if informative < 2 or len({r["group"] for r in rows}) < 2:
        return informative, None, None
    rng = random.Random(20261121)
    shares = []
    for _ in range(2000):
        draw = rng.choices(values, k=len(values))
        den = sum(v[1] for v in draw)
        if den:
            shares.append(100 * sum(v[0] for v in draw) / den)
    shares.sort()
    return (
        informative,
        shares[int(0.025 * len(shares))],
        shares[int(0.975 * len(shares))],
    )


def estimates(frames, people, populations=("all_visible", *DINING)):
    clusters = {k: {f[k] for f in frames} for k in ("video_id", "channel_id")}
    for population in populations:
        for roles, venue, complete in specifications(population):
            rows = [
                r for r in people if eligible(r, population, roles, venue, complete)
            ]
            counts = Counter(r["group"] for r in rows)
            classified = [r for r in rows if r["group"] in {"woman", "man"}]
            den = sum(float(r["within_video_weight"]) for r in classified)
            num = sum(
                float(r["within_video_weight"])
                for r in classified
                if r["group"] == "woman"
            )
            result = {
                "population": population,
                "roles": roles,
                "venue": venue,
                "frame_quality": "countable" if complete else "readable",
                **{k: counts[g] for k, g in GROUPS.items()},
                "weighted_women": num,
                "weighted_classified": den,
                "percent_women": 100 * num / den if den else None,
            }
            for field, groups in clusters.items():
                n, low, high = cluster_interval(classified, groups, field)
                stem = field.removesuffix("_id")
                result.update(
                    {
                        f"contributing_{stem}s": n,
                        f"{stem}_low95": low,
                        f"{stem}_high95": high,
                    }
                )
            yield result


def specifications(population):
    yield "everyone", "all", False
    yield "everyone", "all", True
    if population != "all_visible":
        for roles in (
            "exclude_hosts",
            "exclude_vendors",
            "exclude_both",
            "confirmed_nonhosts_nonvendors",
        ):
            yield roles, "all", False
        for venue in ("stall", "restaurant"):
            yield "everyone", venue, False


def checked_bites(people, review):
    """Limit the sensitivity check to Muse positives supported on visual review."""
    keys = ("video_id", "interval", "rank", "person_id")

    def key(row):
        return tuple(str(row[k]) for k in keys)

    decisions = {}
    for row in read(review):
        identity = key(row)
        if identity in decisions or row["review"] not in {
            "supported",
            "disputed",
            "ambiguous",
        }:
            raise ValueError(f"Invalid or duplicate review for {identity}")
        decisions[identity] = row["review"]
    bites = [p for p in people if p["consumption"] == "eating_food"]
    if set(decisions) != {key(p) for p in bites}:
        raise ValueError("The visual check must cover every Muse bite sighting")
    return [p for p in bites if decisions[key(p)] == "supported"]


def run(design, coding, out, review=None):
    frames, people = load_draw(design, coding)
    out.mkdir(parents=True, exist_ok=True)
    table(out / "frames.csv", frames, frames[0].keys())
    book = json.loads((CONFIG / "stall_frame_codebook_v5.json").read_text())
    table(
        out / "sightings.csv",
        people,
        [*CONTEXT, "quality", "setting", "person_id", *book["person_fields"], "cue"],
    )
    entries = [
        json.loads(p.read_text()) for p in (coding / "muse_ledger").glob("*.json")
    ]
    if entries:
        calls = {v["call_id"] for v in entries if v["status"] == "valid"}
        if any(f["call_id"] not in calls for f in frames):
            raise ValueError("Frame references a missing contributor ledger entry")
        spend = {
            "model": book["model"],
            "frames": len(frames),
            "status_counts": dict(Counter(e["status"] for e in entries)),
            "usage_based_usd": sum(e.get("estimated_cost_usd", 0) for e in entries),
            "upper_bound_usd": sum(e["charged_bound_usd"] for e in entries),
            "cap_usd": max(e["authorized_cap_usd"] for e in entries),
        }
        save(out / "spend.json", json.dumps(spend, indent=2) + "\n")
    write_estimates(frames, people, out, review)


def write_estimates(frames, people, out, review=None):
    """Reproduce the estimates from the two published CSV tables alone."""
    results = list(estimates(frames, people))
    table(out / "estimates.csv", results, results[0].keys())
    if review:
        checked = list(estimates(frames, checked_bites(people, review), ("bite",)))
        table(out / "visually_supported_bites.csv", checked, checked[0].keys())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("design", "coding", "output"):
        parser.add_argument(field, type=Path)
    parser.add_argument("--bite-review", type=Path)
    args = parser.parse_args()
    run(args.design, args.coding, args.output, args.bite_review)
