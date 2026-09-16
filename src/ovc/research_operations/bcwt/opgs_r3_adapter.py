from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

OPGS_R3_STREAM_SHA256 = "86ea8dafdf7183ebf19c4b5c6d208f1f34f035d3a557c35ccbeef4efa5326d07"
_LOAD_BEARING = ("D10", "D12", "D14", "D15", "D16")
_NON_RELATIONS = {None, "UNSUPPORTED", "FRAME_NOT_EVALUABLE"}


def normalize_opgs_r3_accounts(accounts: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize the frozen OPGS-R3 account stream for the G0-frozen BCWT predicate.

    Input order is authoritative stream order. Sequence numbers are local to each of the
    seven uninterrupted source segments and exist only to assert exact adjacency.
    D17 blocks membership only where a load-bearing distinction is explicitly
    NOT_EVALUABLE; upstream UNRESOLVED values remain explicit and are handled by the
    frozen candidate rules rather than being promoted or discarded.
    """
    next_sequence: dict[str, int] = defaultdict(int)
    normalized: list[dict[str, Any]] = []
    for account in accounts:
        segment = str(account["segment"])
        start_sequence = next_sequence[segment]
        end_sequence = start_sequence + 1
        next_sequence[segment] = end_sequence
        distinctions = account["distinctions"]
        frame = account["frame_account"]
        before = frame.get("local_relation_before")
        after = frame.get("local_relation_after")
        d16_evaluable = (
            distinctions["D16"]["state"] == "OBSERVED"
            and before not in _NON_RELATIONS
            and after not in _NON_RELATIONS
        )
        d17_load_bearing_evaluable = all(
            distinctions[key]["state"] != "NOT_EVALUABLE" for key in _LOAD_BEARING
        )
        normalized.append({
            "population_unit_id": account["account_id"],
            "segment_id": segment,
            "start_sequence_id": start_sequence,
            "end_sequence_id": end_sequence,
            "start_fvt_ms": account["start_percept_ref"]["cutoff_fvt_ms"],
            "end_fvt_ms": account["end_percept_ref"]["cutoff_fvt_ms"],
            "source_ref": {
                "opgs_transition_stream_sha256": OPGS_R3_STREAM_SHA256,
                "account_id": account["account_id"],
                "start_snapshot_id": account["start_percept_ref"]["snapshot_id"],
                "end_snapshot_id": account["end_percept_ref"]["snapshot_id"],
            },
            "d10_local_frame_relocation": distinctions["D10"]["state"],
            "d12_continuation_persistence": distinctions["D12"]["state"],
            "d14_internal_reorganisation": distinctions["D14"]["state"],
            "d15_same_uninterrupted_segment": distinctions["D15"]["state"] == "OBSERVED",
            "d16_relation_before": before,
            "d16_relation_after": after,
            "d16_evaluable": d16_evaluable,
            "d17_load_bearing_evaluable": d17_load_bearing_evaluable,
        })
    return normalized
