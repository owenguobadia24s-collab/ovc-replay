from __future__ import annotations

import hashlib
import heapq
import json
import sqlite3
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterator, Mapping

from .index_common import AXES, RO4IndexError, logical_hash, sha256_file
from .sequence_common import (
    BANNER,
    BOUNDARY_SOURCE,
    CANDIDATE_AUTHORITY,
    CONTROL_REGISTRY_ID,
    COUNT_BANNER,
    DISTANCE_REGISTRY_ID,
    OPERATION_MODE,
    SEQUENCE_AUTHORITY,
    SEQUENCE_POLICY_ID,
    blind_id,
    count_cell,
    diversity_audit,
    iter_gzip_jsonl,
    recurrence_id,
    sequence_id,
    signature_id,
    write_gzip_jsonl,
    write_json,
)
from .sequence_workspace import connect_workspace, workspace_inventory

REPRESENTATIVE_MEMBER_LIMIT = 8
REVIEW_CANDIDATE_COUNT = 20


from .sequence_materialize_support import (
    _choose_not_signature,
    _control_pools,
    _different_month_control,
    _hex,
    _partition_map,
    _position_control,
    _prepare_counts,
    _seq,
    _sig,
)

def _candidate_and_control_records(
    connection: sqlite3.Connection,
    partitions: Mapping[int, dict[str, Any]],
) -> tuple[Iterator[dict[str, Any]], Iterator[dict[str, Any]], list[tuple[str, dict[str, Any], dict[str, Any]]], list[int], dict[str, int]]:
    unique, population, month_pool, denominators = _control_pools(connection)
    candidate_rows: list[dict[str, Any]] = []
    control_rows: list[dict[str, Any]] = []
    review_heap: list[tuple[int, str, dict[str, Any], dict[str, Any]]] = []
    diversity_counts: list[int] = []
    exclusions = Counter()

    query = """
      SELECT w.signature_hash,w.sequence_hash,w.pid,w.calendar_partition,w.length,w.start_index,w.sample_hash,s.member_count
      FROM windows w JOIN signature_counts s ON s.signature_hash=w.signature_hash
      WHERE s.member_count>=2
      ORDER BY w.signature_hash,w.sample_hash,w.sequence_hash
    """
    current_signature: bytes | None = None
    members: list[bytes] = []
    member_digest = hashlib.sha256()
    member_count = 0
    representative: tuple[bytes, int, str, int, int] | None = None

    def flush() -> None:
        nonlocal current_signature, members, member_digest, member_count, representative
        if current_signature is None or representative is None:
            return
        rep_seq, pid, month, length, start_index = representative
        partition = partitions[pid]
        key = (pid, length)
        matched = _choose_not_signature(unique.get(key, []), current_signature)
        broader = _choose_not_signature(population.get(key, []), current_signature)
        boundary = _position_control(
            connection, pid=pid, start_index=start_index, length=length,
            candidate_signature=current_signature, offsets=(1, -1),
        )
        temporal = _position_control(
            connection, pid=pid, start_index=start_index, length=length,
            candidate_signature=current_signature, offsets=(MAX_OFFSET(length), -MAX_OFFSET(length)),
        )
        cross_partition = _different_month_control(
            month_pool, pid=pid, length=length, month=month, candidate_signature=current_signature,
        )
        if matched is None or broader is None:
            exclusions["NO_REAL_MATCHED_OR_POPULATION_CONTROL"] += 1
            current_signature = None; members = []; member_digest = hashlib.sha256(); member_count = 0; representative = None
            return
        typed_controls: list[dict[str, Any]] = []
        for control_type, item in (
            ("MATCHED_NON_CANDIDATE", matched),
            ("BOUNDARY_SHIFT_REAL_SEQUENCE", boundary),
            ("TEMPORAL_OFFSET_REAL_SEQUENCE", temporal),
            ("CROSS_PARTITION_REAL_SEQUENCE", cross_partition),
        ):
            if item is None:
                continue
            typed_controls.append(
                {
                    "control_id": _seq(item[0]),
                    "control_type": control_type,
                    "signature_id": _sig(item[1]),
                    "source_partition_id": partition["partition_id"],
                    "calendar_partition": item[3],
                    "synthetic": false_value(),
                }
            )
        population_control = {
            "control_id": _seq(broader[0]),
            "control_type": "BROADER_POPULATION",
            "signature_id": _sig(broader[1]),
            "source_partition_id": partition["partition_id"],
            "calendar_partition": broader[3],
            "synthetic": false_value(),
        }
        candidate_core = {
            "source_release_ids": [partition["release_id"]],
            "sequence_policy_id": SEQUENCE_POLICY_ID,
            "signature_type": "EXACT",
            "exact_signature_id": _sig(current_signature),
            "member_sequence_ids": [_seq(value) for value in members],
            "full_member_count": member_count,
            "member_inventory_sha256": member_digest.hexdigest(),
            "representative_member_policy": "LOWEST_SAMPLE_HASH_FIRST_8",
            "support_counts": [
                count_cell(
                    member_count,
                    denominators[key],
                    f"{partition['partition_id']}|{month}|L{length}|{SEQUENCE_POLICY_ID}",
                )
            ],
            "matched_control_ids": [item["control_id"] for item in typed_controls],
            "population_control_ids": [population_control["control_id"]],
            "counterexample_ids": [typed_controls[0]["control_id"]],
            "boundary_stability": {
                "boundary_shift_control_ids": [item["control_id"] for item in typed_controls if item["control_type"] == "BOUNDARY_SHIFT_REAL_SEQUENCE"],
                "temporal_offset_control_ids": [item["control_id"] for item in typed_controls if item["control_type"] == "TEMPORAL_OFFSET_REAL_SEQUENCE"],
                "cross_partition_control_ids": [item["control_id"] for item in typed_controls if item["control_type"] == "CROSS_PARTITION_REAL_SEQUENCE"],
                "status": "UNADJUDICATED_NON_CANONICAL",
            },
            "operation_modes": [OPERATION_MODE],
            "authority": CANDIDATE_AUTHORITY,
            "semantic_label": "PROHIBITED",
        }
        candidate_hash = logical_hash(candidate_core)
        candidate_core["candidate_id"] = recurrence_id(candidate_hash)
        candidate_core["logical_hash"] = logical_hash(candidate_core)
        control_core = {
            "candidate_id": candidate_core["candidate_id"],
            "control_registry_id": CONTROL_REGISTRY_ID,
            "candidate_signature_id": candidate_core["exact_signature_id"],
            "candidate_representative_sequence_id": _seq(rep_seq),
            "real_controls": typed_controls + [population_control],
            "sealed_answer_key_state": "SEPARATE_NOT_OPERATOR_ACCESSIBLE",
            "synthetic_controls_operator_facing": "DENIED",
        }
        control_core["logical_hash"] = logical_hash(control_core)
        candidate_rows.append(candidate_core)
        control_rows.append(control_core)
        diversity_counts.append(member_count)
        review_key = int(candidate_hash, 16)
        review_item = (review_key, candidate_core["candidate_id"], candidate_core, control_core)
        if len(review_heap) < REVIEW_CANDIDATE_COUNT:
            heapq.heappush(review_heap, (-review_key, candidate_core["candidate_id"], candidate_core, control_core))
        elif review_key < -review_heap[0][0]:
            heapq.heapreplace(review_heap, (-review_key, candidate_core["candidate_id"], candidate_core, control_core))
        current_signature = None; members = []; member_digest = hashlib.sha256(); member_count = 0; representative = None

    for sig_hash, seq_hash, pid, month, length, start_index, _, _declared_count in connection.execute(query):
        if current_signature is not None and sig_hash != current_signature:
            flush()
        if current_signature is None:
            current_signature = sig_hash
            members = []
            member_digest = hashlib.sha256()
            member_count = 0
            representative = (seq_hash, int(pid), str(month), int(length), int(start_index))
        member_count += 1
        seq_text = _seq(seq_hash)
        member_digest.update(seq_text.encode("utf-8")); member_digest.update(b"\n")
        if len(members) < REPRESENTATIVE_MEMBER_LIMIT:
            members.append(seq_hash)
    flush()
    review = [(-key, cid, candidate, control) for key, cid, candidate, control in review_heap]
    review.sort(key=lambda item: (item[0], item[1]))
    return iter(candidate_rows), iter(control_rows), [(cid, cand, ctl) for _, cid, cand, ctl in review], diversity_counts, dict(exclusions)


def MAX_OFFSET(length: int) -> int:
    return max(16, length * 2)


def false_value() -> bool:
    return False


def reconstruct_sequence(
    *, index_dir: Path, connection: sqlite3.Connection, sequence_text: str,
) -> dict[str, Any]:
    if not sequence_text.startswith("RO4.SEQUENCE."):
        raise RO4IndexError("INVALID_SEQUENCE_ID")
    seq_blob = bytes.fromhex(sequence_text.removeprefix("RO4.SEQUENCE."))
    row = connection.execute(
        "SELECT w.pid,w.calendar_partition,w.length,w.start_index,w.end_index,p.partition_id,p.role,p.clock,p.side,p.evaluation_scope_id,p.release_id,p.manifest_sha256,p.index_file "
        "FROM windows w JOIN partitions p ON p.pid=w.pid WHERE w.sequence_hash=?",
        (seq_blob,),
    ).fetchone()
    if row is None:
        raise RO4IndexError(f"SEQUENCE_NOT_FOUND:{sequence_text}")
    pid, month, length, start_index, end_index, partition_id, role, clock, side, scope, release_id, manifest_sha, index_file = row
    source = sqlite3.connect(index_dir / index_file)
    try:
        states = list(
            source.execute(
                "SELECT state_record_id,first_valid_time,axes_json FROM states ORDER BY first_valid_time,state_record_id LIMIT ? OFFSET ?",
                (int(length), int(start_index)),
            )
        )
        if len(states) != int(length):
            raise RO4IndexError("SEQUENCE_RECONSTRUCTION_STATE_COUNT")
        transitions = []
        for left, right in zip(states, states[1:]):
            transition = source.execute(
                "SELECT transition_id,changed_axes_json FROM transitions WHERE source_state_id=? AND target_state_id=?",
                (left[0], right[0]),
            ).fetchone()
            if transition is None:
                raise RO4IndexError("SEQUENCE_RECONSTRUCTION_MISSING_TRANSITION")
            transitions.append(transition)
    finally:
        source.close()
    return {
        "sequence_id": sequence_text,
        "source_release_id": release_id,
        "manifest_sha256": manifest_sha,
        "role": role,
        "clock": clock,
        "side": side,
        "source_partition_id": partition_id,
        "evaluation_scope_id": scope,
        "calendar_partition": month,
        "boundary_source": BOUNDARY_SOURCE,
        "sequence_policy_id": SEQUENCE_POLICY_ID,
        "member_state_ids": [item[0] for item in states],
        "member_transition_ids": [item[0] for item in transitions],
        "ordered_axis_vectors": [json.loads(item[2]) for item in states],
        "ordered_changed_axis_sets": [json.loads(item[1]) for item in transitions],
        "first_valid_at": states[0][1],
        "last_valid_at": states[-1][1],
        "operation_mode": OPERATION_MODE,
        "authority": SEQUENCE_AUTHORITY,
        "non_canonical_banner": BANNER,
        "count_banner": COUNT_BANNER,
    }
