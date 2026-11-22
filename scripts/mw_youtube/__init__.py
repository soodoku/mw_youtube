"""Public research interface. All paths point to explicit snapshots or exports."""

from .analysis import build as build_frames
from .design import frames_per_third
from .design import searches as plan_searches
from .tables import read_frames

__all__ = ["build_frames", "frames_per_third", "plan_searches", "read_frames"]
