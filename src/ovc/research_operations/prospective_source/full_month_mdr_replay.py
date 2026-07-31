from __future__ import annotations

from typing import Sequence

from . import full_month_mdr_compute as implementation
from .full_month_mdr_compute import *  # noqa: F401,F403
from .models import ProspectiveBar, parse_utc


def complete_segments(
    bars: Sequence[ProspectiveBar],
) -> list[list[ProspectiveBar]]:
    """Return every complete contiguous segment without dropping boundary bars."""

    ordered = sorted(bars, key=lambda item: item.start_utc)
    segments: list[list[ProspectiveBar]] = []
    current: list[ProspectiveBar] = []
    expected_seconds = implementation.CLOCK_SECONDS[ordered[0].clock] if ordered else 0
    previous_end: str | None = None

    for bar in ordered:
        if bar.quality_state != "COMPLETE":
            if current:
                segments.append(current)
                current = []
            previous_end = None
            continue

        duration = int(
            (parse_utc(bar.end_utc) - parse_utc(bar.start_utc)).total_seconds()
        )
        if duration != expected_seconds:
            raise implementation.ComputeError(
                f"unexpected bar duration:{bar.clock}:{bar.start_utc}"
            )

        if (
            previous_end is not None
            and parse_utc(bar.start_utc) != parse_utc(previous_end)
        ):
            if current:
                segments.append(current)
            current = []

        current.append(bar)
        previous_end = bar.end_utc

    if current:
        segments.append(current)
    return segments


# Functions defined in the implementation module resolve globals in that module.
# Bind the corrected, tested policy before exposing its execute/main entrypoints.
implementation.complete_segments = complete_segments


if __name__ == "__main__":
    raise SystemExit(implementation.main())
