"""GRT2 fail-closed capacity guard used by qualification and runtime callers."""
from __future__ import annotations


class CapacityExceeded(RuntimeError):
    """Raised when an exact workload exceeds the frozen supported scale."""

    code = "CAPACITY_EXCEEDED"


def enforce_capacity(*, observed_scale: int, capacity_failure_threshold: int) -> None:
    if isinstance(observed_scale, bool) or not isinstance(observed_scale, int) or observed_scale < 0:
        raise ValueError("GRT_CAPACITY_OBSERVED_SCALE_INVALID")
    if isinstance(capacity_failure_threshold, bool) or not isinstance(capacity_failure_threshold, int) or capacity_failure_threshold <= 0:
        raise ValueError("GRT_CAPACITY_THRESHOLD_INVALID")
    if observed_scale >= capacity_failure_threshold:
        raise CapacityExceeded(f"CAPACITY_EXCEEDED:{observed_scale}>={capacity_failure_threshold}")
