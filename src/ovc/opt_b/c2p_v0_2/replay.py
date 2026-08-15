from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .ledger import CanonicalEventLedger
from .projection import projection_digest, rebuild_snapshots


@dataclass(frozen=True)
class ReplayResult:
    event_count: int
    stream_count: int
    ledger_digest: str
    projection_digest: str
    snapshots: tuple[Mapping[str, Any], ...]


def _materialize(events: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [dict(event) for event in events]


def replay_events(
    events: Iterable[Mapping[str, Any]],
    *,
    chunk_size: int | None = None,
    worker_partitions: int = 1,
) -> ReplayResult:
    """Replay canonical C2P events without making physical layout semantic.

    `chunk_size` and `worker_partitions` are execution-layout controls only. They
    are validated but intentionally excluded from logical result identity.
    CanonicalEventLedger.from_events supplies the deterministic reference order.
    """

    if chunk_size is not None and chunk_size <= 0:
        raise ValueError("C2P_REPLAY_CHUNK_SIZE_INVALID")
    if worker_partitions <= 0:
        raise ValueError("C2P_REPLAY_WORKER_PARTITIONS_INVALID")

    materialized = _materialize(events)
    if chunk_size is None:
        chunks: Sequence[Sequence[Mapping[str, Any]]] = (materialized,)
    else:
        chunks = tuple(
            materialized[index : index + chunk_size]
            for index in range(0, len(materialized), chunk_size)
        )

    # Simulate arbitrary physical partition delivery while retaining one exact
    # reference semantic stream. Worker/chunk topology may change cost, never
    # logical bytes.
    staged: list[Mapping[str, Any]] = []
    for chunk in chunks:
        staged.extend(chunk)

    ledger = CanonicalEventLedger.from_events(staged)
    snapshots = tuple(rebuild_snapshots(ledger))
    return ReplayResult(
        event_count=ledger.event_count,
        stream_count=len(ledger.stream_ids()),
        ledger_digest=ledger.global_digest(),
        projection_digest=projection_digest(snapshots),
        snapshots=snapshots,
    )


def prove_replay_equivalence(
    reference_events: Iterable[Mapping[str, Any]],
    candidate_events: Iterable[Mapping[str, Any]],
) -> bool:
    reference = replay_events(reference_events)
    candidate = replay_events(candidate_events)
    if (
        reference.event_count,
        reference.stream_count,
        reference.ledger_digest,
        reference.projection_digest,
    ) != (
        candidate.event_count,
        candidate.stream_count,
        candidate.ledger_digest,
        candidate.projection_digest,
    ):
        raise ValueError("C2P_REPLAY_EQUIVALENCE_MISMATCH")
    return True
