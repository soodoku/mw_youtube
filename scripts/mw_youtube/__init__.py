"""Public research interface. All paths point to explicit snapshots or exports."""

from .analysis import build as build_frames
from .design import searches as plan_searches
from .tables import read_frames

__all__ = ["build_frames", "plan_searches", "read_frames"]
