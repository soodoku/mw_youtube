from collections import Counter, defaultdict

from .codebook import BOOK, validate
from .records import KEY

SCOPES = {
    "all_visible": None,
    "all_at_stall": None,
    "linked_including_unclear": {"worker", "vendor", "patron", "unclear"},
    "worker_and_patron": {"worker", "vendor", "patron"},
    "worker": {"worker", "vendor"},
    "patron": {"patron"},
}
HOST_SCOPES = {
    "vendor": {"vendor"},
    "apparent_host": None,
    "worker_and_patron_without_apparent_hosts": {"vendor", "patron"},
    "worker_and_patron_confirmed_nonhosts": {"vendor", "patron"},
}
GROUPS = {
    "n_women": "woman",
    "n_men": "man",
    "n_gender_unclear": "gender_unclear",
    "n_younger_child": "younger_child",
    "n_age_unclear": "age_unclear",
}


def key(row):
    return tuple(str(row[k]) for k in KEY)


def summarize(frames, people, book=BOOK):
    by_frame = defaultdict(list)
    for p in people:
        by_frame[key(p)].append(p)
    if set(by_frame) - {key(f) for f in frames}:
        raise ValueError("Sighting points to an unknown frame")
    results = []
    for f in frames:
        members = sorted(by_frame[key(f)], key=lambda p: int(p["person_id"]))
        validate(
            {
                **f,
                "n_enumerated": (
                    None if f["n_enumerated"] in (None, "") else int(f["n_enumerated"])
                ),
                "sightings": [{**p, "person_id": int(p["person_id"])} for p in members],
            },
            book,
        )
        scopes = (
            {**SCOPES, **HOST_SCOPES}
            if "host_status" in book["person_fields"]
            else SCOPES
        )
        for scope, roles in scopes.items():
            included = (
                scope in {"all_visible", "apparent_host"}
                or f["setting"] == "street_stall"
            )
            population = [p for p in members if roles is None or p["role"] in roles]
            if scope == "apparent_host":
                population = [
                    p for p in population if p["host_status"] == "apparent_host"
                ]
            elif scope == "worker_and_patron_without_apparent_hosts":
                population = [
                    p for p in population if p["host_status"] != "apparent_host"
                ]
            elif scope == "worker_and_patron_confirmed_nonhosts":
                population = [p for p in population if p["host_status"] == "not_host"]
            counts = Counter(p["group"] for p in population)
            reportable = included and f["quality"] == "countable"
            row = {k: f[k] for k in KEY}
            row.update(
                setting=f["setting"],
                shot=f["shot"],
                service_area=f["service_area"],
                scope=scope,
                in_scope=int(included),
                quality=f["quality"],
            )
            row.update(
                {k: counts[g] if reportable else None for k, g in GROUPS.items()}
            )
            results.append(row)
    return results
