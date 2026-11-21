"""Sample the displayed frame at reproducible times on the source presentation timeline."""

import hashlib
import heapq
from fractions import Fraction
from math import ceil

import av


def timeline(source):
    with av.open(str(source)) as container:
        stream = container.streams.video[0]
        first = last = None
        for frame in container.decode(stream):
            t = presentation(frame)
            if last is not None and t < last:
                raise ValueError("Nonmonotone frame presentation times")
            if first is None:
                first = t
            last = t
            tail = (frame.duration or 0) * frame.time_base
        if last is None:
            raise ValueError("Empty video stream")
        if tail > 0:
            end = last + tail
        elif stream.duration is not None:
            start = (
                first
                if stream.start_time is None
                else stream.start_time * stream.time_base
            )
            end = start + stream.duration * stream.time_base
        else:
            raise ValueError("Missing final frame duration")
        if end <= last:
            raise ValueError("Invalid video duration")
        return first, end, str(stream.time_base)


def presentation(frame):
    if frame.pts is None or frame.time_base is None:
        raise ValueError("Frame has no presentation timestamp")
    return frame.pts * frame.time_base


def draw(video_id, seed, duration, per_interval):
    moments = []
    for interval in range(3):
        lo = ceil(1000 * duration * interval / 3)
        hi = ceil(1000 * duration * (interval + 1) / 3)
        if hi - lo < per_interval:
            raise ValueError("Source too short for distinct millisecond draws")
        prefix = f"frames|{seed}|{video_id}|{interval}|".encode()

        def priority(ms):
            return hashlib.sha256(prefix + str(ms).encode()).digest(), ms

        for rank, ms in enumerate(
            heapq.nsmallest(per_interval, range(lo, hi), key=priority), 1
        ):
            moments.append(dict(interval=interval, rank=rank, requested_ms=ms))
    return moments


def displayed_frames(source, origin, moments):
    targets = iter(sorted(moments, key=lambda r: r["requested_ms"]))
    target = next(targets, None)
    previous = None
    with av.open(str(source)) as container:
        for current in container.decode(video=0):
            t = presentation(current) - origin
            while target is not None and Fraction(target["requested_ms"], 1000) < t:
                if previous is None:
                    raise ValueError("Requested time precedes the first frame")
                yield target, previous
                target = next(targets, None)
            if target is None:
                return
            previous = current
    while target is not None:
        if previous is None:
            raise ValueError("No decoded frame")
        yield target, previous
        target = next(targets, None)
