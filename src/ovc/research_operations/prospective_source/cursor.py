from __future__ import annotations

from .models import ProspectiveCursor, canonical_hash


def advance_cursor(
    previous: ProspectiveCursor | None,
    *,
    source_slice_id: str,
    interval_end_utc: str,
    transition_id: str | None,
) -> ProspectiveCursor:
    if previous is not None:
        if previous.source_slice_id != source_slice_id:
            raise ValueError("cursor source slice mismatch")
        if interval_end_utc < previous.last_source_interval_end_utc:
            raise ValueError("cursor cannot move backwards")
        if interval_end_utc == previous.last_source_interval_end_utc and transition_id == previous.last_transition_id:
            return previous
        sequence = previous.sequence + 1
    else:
        sequence = 1
    body = {
        "source_slice_id": source_slice_id,
        "last_source_interval_end_utc": interval_end_utc,
        "last_transition_id": transition_id,
        "sequence": sequence,
    }
    return ProspectiveCursor(
        cursor_id=f"RPS.CURSOR.{canonical_hash(body)[:24]}",
        source_slice_id=source_slice_id,
        last_source_interval_end_utc=interval_end_utc,
        last_transition_id=transition_id,
        sequence=sequence,
        state_hash=canonical_hash(body),
    )


def reconcile_cursor(cursor: ProspectiveCursor, expected_state_hash: str) -> None:
    if cursor.state_hash != expected_state_hash:
        raise ValueError("cursor state hash mismatch")
