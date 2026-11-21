"""Atomic writes and relational keys shared by pipeline stages."""

import csv
from pathlib import Path
from tempfile import NamedTemporaryFile

META = ("video_id", "interval", "rank", "requested_ms", "jpeg", "sha256")
KEY = ("video_id", "interval", "rank")


def read(path):
    with path.open(newline="", encoding="utf8") as f:
        return list(csv.DictReader(f))


def save(path, content):
    with NamedTemporaryFile("w", dir=path.parent, delete=False, encoding="utf8") as tmp:
        tmp.write(content)
    Path(tmp.name).replace(path)


def write_table(path, columns, rows):
    with NamedTemporaryFile(
        "w", dir=path.parent, newline="", encoding="utf8", delete=False
    ) as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    Path(f.name).replace(path)


def table(path, rows, columns):
    return write_table(path, columns, rows)
