"""Deterministic synthetic single-clock qualification for the inactive RRSCG core.

The harness is deliberately synthetic. It exercises the repository R2, D9 and
D10 implementations without resolving or consuming any real-source population,
Validation token, or owner-programme execution authority.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Sequence

from .d10 import reduce_d9_state
from .d9 import build_observer_state
from .kernel import (
    PRIMARY_CONSTRAINT_VIEWS,
    PRIMARY_TARGET_PACK,
    ConstraintViewEvidence,
    compose_constraint_event,
)

SYNTHETIC_SOURCE_GENERATION_ID = "RRSCG_SYNTHETIC_SINGLE_CLOCK_QUALIFICATION_v0.1"
SINGLE_CLOCK_ID = "15M"
PARENT_CLOCK_ID = "2H_A_L"
SYNTHETIC_TARGETS = tuple(f"T{i}" for i in range(8))


class QualificationError(ValueError):
    pass


def _canonical_sha256(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class SyntheticQualificationCase:
    case_id: str
    source_sequence_index: int
    stream_segment_id: str
    first_valid_time: str
    owner_snapshot_id: str
    raw_view_records: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class QualificationRecord:
    case_id: str
    source_sequence_index: int
    stream_segment_id: str
    first_valid_time: str
    owner_snapshot_id: str
    r2_constraint_id: str
    r2_relation_resolved: bool
    r2_selected_resolution_tier: str
    r2_selected_frontier: tuple[str, ...]
    d9_state_sha256: str
    d9_resolution_tier: str
    d10_parent_d9_state_sha256: str
    d10_resolution_tier: str
    d10_selected_frontier: tuple[str, ...]

    def semantic_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "source_sequence_index": self.source_sequence_index,
            "stream_segment_id": self.stream_segment_id,
            "first_valid_time": self.first_valid_time,
            "owner_snapshot_id": self.owner_snapshot_id,
            "r2_constraint_id": self.r2_constraint_id,
            "r2_relation_resolved": self.r2_relation_resolved,
            "r2_selected_resolution_tier": self.r2_selected_resolution_tier,
            "r2_selected_frontier": list(self.r2_selected_frontier),
            "d9_state_sha256": self.d9_state_sha256,
            "d9_resolution_tier": self.d9_resolution_tier,
            "d10_parent_d9_state_sha256": self.d10_parent_d9_state_sha256,
            "d10_resolution_tier": self.d10_resolution_tier,
            "d10_selected_frontier": list(self.d10_selected_frontier),
        }

    @property
    def record_hash(self) -> str:
        return _canonical_sha256(self.semantic_dict())


@dataclass(frozen=True)
class DenominatorReconciliation:
    expected_count: int
    record_count: int
    unique_case_count: int
    unique_sequence_count: int
    r2_resolved_count: int
    d9_resolved_count: int
    d10_resolved_count: int
    d10_affected_count: int
    status: str

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _view_row(case_index: int, seed: int, view_id: str) -> dict[str, Any]:
    digest = hashlib.sha256(f"{seed}:{case_index}:{view_id}".encode()).digest()
    supported = digest[0] % 7 != 0
    if not supported:
        return {
            "view_id": view_id,
            "source_evaluable": True,
            "comparable": True,
            "antecedent_support_count": 0,
            "relation_support_records": [],
        }
    rows = []
    for offset, target_id in enumerate(SYNTHETIC_TARGETS):
        marker = digest[(offset + 1) % len(digest)]
        if marker % 4 != 0:
            rows.append({"target_id": target_id, "support_count": 2 + marker % 3})
    return {
        "view_id": view_id,
        "source_evaluable": True,
        "comparable": True,
        "antecedent_support_count": 2 + digest[9] % 5,
        "relation_support_records": rows,
    }


def generate_synthetic_cases(count: int, *, seed: int = 800031) -> tuple[SyntheticQualificationCase, ...]:
    if count <= 0:
        raise QualificationError("RRSCG_SYNTHETIC_COUNT_MUST_BE_POSITIVE")
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    cases = []
    for index in range(count):
        case_id = f"RRSCG-SYNTH-{index:08d}"
        fvt = start + timedelta(minutes=15 * index)
        segment_id = f"SEG-{index // 2048:05d}"
        snapshot_id = _canonical_sha256({
            "case_id": case_id,
            "source_generation_id": SYNTHETIC_SOURCE_GENERATION_ID,
            "clock": SINGLE_CLOCK_ID,
            "first_valid_time": fvt.isoformat().replace("+00:00", "Z"),
        })
        cases.append(SyntheticQualificationCase(
            case_id=case_id,
            source_sequence_index=index,
            stream_segment_id=segment_id,
            first_valid_time=fvt.isoformat().replace("+00:00", "Z"),
            owner_snapshot_id=snapshot_id,
            raw_view_records=tuple(_view_row(index, seed, view_id) for view_id in PRIMARY_CONSTRAINT_VIEWS),
        ))
    return tuple(cases)


def _execute_case(case: SyntheticQualificationCase) -> QualificationRecord:
    views = []
    for raw in case.raw_view_records:
        supported = bool(raw["source_evaluable"] and raw["comparable"] and int(raw["antecedent_support_count"]) >= 2)
        observed = tuple(sorted(
            (str(item["target_id"]), int(item["support_count"]))
            for item in raw["relation_support_records"]
            if int(item["support_count"]) > 0
        )) if supported else ()
        qualified = tuple((target, support) for target, support in observed if support >= 2)
        views.append(ConstraintViewEvidence(
            view_id=str(raw["view_id"]),
            supported=supported,
            antecedent_support=int(raw["antecedent_support_count"]) if supported else 0,
            qualified_frontier_supports=qualified,
            observed_frontier_supports=observed,
            target_pack_id=PRIMARY_TARGET_PACK,
            relation_min=2,
            training_frontier_id="RRSCG-SYNTHETIC-FRONTIER-v0.1",
            source_generation_id=SYNTHETIC_SOURCE_GENERATION_ID,
        ))
    event = compose_constraint_event(
        case.case_id,
        SYNTHETIC_SOURCE_GENERATION_ID,
        views,
        PRIMARY_TARGET_PACK,
        2,
        2,
    )
    state = build_observer_state(event, case.raw_view_records, stream_segment_id=case.stream_segment_id)
    reduced = reduce_d9_state(state)
    d9_sha = _canonical_sha256(state.state_shape_payload)
    if reduced.parent_d9_state_sha256 != d9_sha:
        raise QualificationError("RRSCG_D10_PARENT_D9_CONTENT_IDENTITY_MISMATCH")
    return QualificationRecord(
        case_id=case.case_id,
        source_sequence_index=case.source_sequence_index,
        stream_segment_id=case.stream_segment_id,
        first_valid_time=case.first_valid_time,
        owner_snapshot_id=case.owner_snapshot_id,
        r2_constraint_id=event.constraint_id,
        r2_relation_resolved=event.relation_resolved,
        r2_selected_resolution_tier=event.selected_resolution_tier or "NONE",
        r2_selected_frontier=tuple(sorted(event.selected_frontier)),
        d9_state_sha256=d9_sha,
        d9_resolution_tier=state.state_shape_payload["resolution_tier"] or "NONE",
        d10_parent_d9_state_sha256=reduced.parent_d9_state_sha256,
        d10_resolution_tier=reduced.selected_resolution_tier,
        d10_selected_frontier=reduced.selected_frontier,
    )


def run_synthetic_cases(cases: Iterable[SyntheticQualificationCase], *, chunk_size: int = 256) -> tuple[QualificationRecord, ...]:
    if chunk_size <= 0:
        raise QualificationError("RRSCG_CHUNK_SIZE_MUST_BE_POSITIVE")
    ordered = sorted(cases, key=lambda item: (item.source_sequence_index, item.case_id))
    case_ids = [item.case_id for item in ordered]
    sequence_ids = [item.source_sequence_index for item in ordered]
    if len(case_ids) != len(set(case_ids)):
        raise QualificationError("RRSCG_DUPLICATE_SYNTHETIC_CASE_ID")
    if len(sequence_ids) != len(set(sequence_ids)):
        raise QualificationError("RRSCG_DUPLICATE_SOURCE_SEQUENCE_INDEX")
    records = []
    for offset in range(0, len(ordered), chunk_size):
        records.extend(_execute_case(case) for case in ordered[offset:offset + chunk_size])
    return tuple(records)


def merge_qualification_records(*parts: Sequence[QualificationRecord]) -> tuple[QualificationRecord, ...]:
    values = sorted((record for part in parts for record in part), key=lambda item: (item.source_sequence_index, item.case_id))
    if len({record.case_id for record in values}) != len(values):
        raise QualificationError("RRSCG_DUPLICATE_QUALIFICATION_CASE_ID")
    if len({record.source_sequence_index for record in values}) != len(values):
        raise QualificationError("RRSCG_DUPLICATE_QUALIFICATION_SEQUENCE_INDEX")
    return tuple(values)


def qualification_content_hash(records: Sequence[QualificationRecord]) -> str:
    return _canonical_sha256([record.semantic_dict() for record in records])


def reconcile_denominators(records: Sequence[QualificationRecord], *, expected_count: int) -> DenominatorReconciliation:
    r2 = sum(record.r2_relation_resolved for record in records)
    d9 = sum(record.d9_resolution_tier != "NONE" for record in records)
    d10 = sum(record.d10_resolution_tier != "NONE" for record in records)
    affected = sum(
        record.d10_resolution_tier != record.d9_resolution_tier
        or record.d10_selected_frontier != record.r2_selected_frontier
        for record in records
    )
    ids = {record.case_id for record in records}
    seqs = {record.source_sequence_index for record in records}
    status = "PASS" if (
        len(records) == expected_count == len(ids) == len(seqs)
        and r2 == d9 == d10
    ) else "FAIL"
    return DenominatorReconciliation(
        expected_count=expected_count,
        record_count=len(records),
        unique_case_count=len(ids),
        unique_sequence_count=len(seqs),
        r2_resolved_count=r2,
        d9_resolved_count=d9,
        d10_resolved_count=d10,
        d10_affected_count=affected,
        status=status,
    )
