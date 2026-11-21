"""Read and validate typed analysis tables while keeping YouTube identifiers as strings."""

import json
import math
from pathlib import Path

from .design import CONFIG
from .records import read

TABLES = json.loads((CONFIG / "analysis_tables.json").read_text())["tables"]


def typed_rows(rows, table):
    definition = TABLES[table]
    fields = definition["fields"]
    seen = set()
    output = []
    for raw in rows:
        if raw.keys() != fields.keys():
            raise ValueError(f"{table} columns differ: {raw.keys() ^ fields.keys()}")
        row = {}
        for k, kind in fields.items():
            value = raw[k]
            if value in ("", None):
                row[k] = None
            else:
                row[k] = {"integer": int, "number": float, "string": str}[kind](value)
                if (
                    kind == "integer"
                    and isinstance(value, float)
                    and not value.is_integer()
                ):
                    raise ValueError(f"Non-integral value in {k}")
                if kind == "number" and not math.isfinite(row[k]):
                    raise ValueError(f"Non-finite value in {k}")
        key = tuple(row[k] for k in definition["primary_key"])
        if None in key or key in seen:
            raise ValueError(f"Missing or duplicate {table} key: {key}")
        seen.add(key)
        output.append(row)
    return output


def read_frames(path):
    """Return one typed dictionary per moment. Blank CSV cells become None."""
    return typed_rows(read(Path(path)), "frames")
