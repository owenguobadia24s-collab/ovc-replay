from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from .classifiers import compression, displacement
from .models import Bar, TermRecord, TermStatus


@dataclass(frozen=True, slots=True)
class UnlevelledReplay:
    records: tuple[TermRecord, ...]
    segment_lengths: tuple[int, ...]
    status_counts: dict[str, int]


def contiguous_segments(bars: Iterable[Bar]) -> tuple[tuple[Bar, ...], ...]:
    ordered = tuple(bars)
    if not ordered:
        return ()
    segments: list[list[Bar]] = [[ordered[0]]]
    for bar in ordered[1:]:
        if bar.open_time == segments[-1][-1].close_time:
            segments[-1].append(bar)
        else:
            segments.append([bar])
    return tuple(tuple(segment) for segment in segments)


def replay_unlevelled_terms(bars: Iterable[Bar]) -> UnlevelledReplay:
    """Replay terms that need no external reference-level registry."""
    segments = contiguous_segments(bars)
    records: list[TermRecord] = []
    for segment in segments:
        for index in range(21, len(segment)):
            records.append(displacement(segment, index))
        for index in range(28, len(segment)):
            records.append(compression(segment, index))
    counts = Counter(f"{record.term_id}:{record.status.value}" for record in records)
    return UnlevelledReplay(tuple(records), tuple(len(segment) for segment in segments), dict(sorted(counts.items())))

