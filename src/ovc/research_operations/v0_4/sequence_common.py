from __future__ import annotations

import gzip
import hashlib
import json
import math
import platform
import resource
import sqlite3
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence

from .index_common import AXES, RO4IndexError, canonical_bytes, logical_hash, sha256_file

SEQUENCE_AUTHORITY = "NON_CANONICAL_SEQUENCE_EVIDENCE"
CANDIDATE_AUTHORITY = "NON_CANONICAL_RESEARCH_CANDIDATE"
SEQUENCE_POLICY_ID = "RO4.SEQUENCE.WINDOW.v0.1"
DISTANCE_REGISTRY_ID = "RO4.SEQUENCE.DISTANCE.v0.1"
CONTROL_REGISTRY_ID = "RO4.CONTROLS.v0.1"
DIVERSITY_POLICY_ID = "RO4.SIGNATURE.DIVERSITY.v0.1"
SAMPLE_POLICY_ID = "RO4.PERFORMANCE.SAMPLE.v0.1"
MIN_STATES = 2
MAX_STATES = 16
WINDOW_CAP = 100_000
OPERATION_MODE = "NON_EVIDENTIARY_REPLAY"
BOUNDARY_SOURCE = "FIXED_ROLLING"
BANNER = (
    "NON_CANONICAL SEQUENCE EVIDENCE - repeated signatures are research evidence only; "
    "no semantic, family, probability or promotion authority."
)
COUNT_BANNER = (
    "DESCRIPTIVE COUNTS ONLY - counts are not probabilities, likelihoods, forecasts or transition expectations."
)
FORBIDDEN_VOCABULARY = {
    "setup", "signal", "opportunity", "breakout", "reversal", "continuation", "strong", "weak",
    "family", "archetype", "prediction", "probability", "valid pattern", "invalid pattern",
}
DENIED_PD_FIELDS = {
    "pd_candidate_id", "pd_fingerprint", "pd_cluster_id", "novelty", "medoid", "queue",
    "review", "answer_key", "candidate_score", "promotion",
}


@dataclass(frozen=True)
class SequenceBuildResult:
    manifest: dict[str, Any]
    benchmark: dict[str, Any]


def peak_rss_bytes() -> int:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def metadata(connection: sqlite3.Connection) -> dict[str, Any]:
    return {key: json.loads(value) for key, value in connection.execute("SELECT key,value FROM metadata")}


def sha256_lines(values: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(value.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def sequence_id(hex_digest: str) -> str:
    return "RO4.SEQUENCE." + hex_digest


def signature_id(hex_digest: str) -> str:
    return "RO4.SIGNATURE." + hex_digest


def recurrence_id(hex_digest: str) -> str:
    return "RO4.RECURRENCE." + hex_digest


def blind_id(value: str) -> str:
    return "RO4.BLIND." + hashlib.sha256(("RO4.BLIND.v0.1|" + value).encode("utf-8")).hexdigest()


def sample_hash(value: str) -> bytes:
    return hashlib.sha256((value + SAMPLE_POLICY_ID + "|v0.1").encode("utf-8")).digest()


def clock_seconds(clock: str) -> int:
    if clock == "15M":
        return 900
    if clock == "2H_A_L":
        return 7200
    raise RO4IndexError(f"UNAUTHORISED_SEQUENCE_CLOCK:{clock}")


def axis_vector(axes_json: str) -> dict[str, Any]:
    value = json.loads(axes_json)
    if set(value) != set(AXES):
        raise RO4IndexError("SEQUENCE_FIVE_AXIS_SET_MISMATCH")
    return {axis: value[axis] for axis in AXES}


def changed_axis_set(changed_json: str) -> list[str]:
    raw = json.loads(changed_json)
    if not isinstance(raw, list) or any(axis not in AXES for axis in raw):
        raise RO4IndexError("INVALID_CHANGED_AXIS_SET")
    order = {axis: index for index, axis in enumerate(AXES)}
    return sorted(set(raw), key=order.__getitem__)


def signature_core(
    *,
    role: str,
    clock: str,
    side: str,
    evaluation_scope_id: str,
    state_axes: Sequence[dict[str, Any]],
    changed_axes: Sequence[list[str]],
) -> dict[str, Any]:
    parent_marker = (
        "SOURCE_SCOPE_WITH_2H_PARENT" if "WITH-2H-PARENT" in evaluation_scope_id
        else "SOURCE_SCOPE_LOCAL_ONLY"
    )
    return {
        "signature_type": "EXACT",
        "role": role,
        "clock": clock,
        "side": side,
        "ordered_axis_vectors": list(state_axes),
        "ordered_changed_axis_sets": list(changed_axes),
        "raw_durations": [clock_seconds(clock)] * max(0, len(state_axes) - 1),
        "context_markers": [evaluation_scope_id],
        "parent_change_markers": [parent_marker] * max(0, len(state_axes) - 1),
        "registry_versions": {
            "sequence_policy_id": SEQUENCE_POLICY_ID,
            "distance_registry_id": DISTANCE_REGISTRY_ID,
            "state_value_registry": "C2.STATE_VALUES.v0.1",
            "axis_registry": "C2.AXES.v0.1",
        },
        "distance_registry_id": DISTANCE_REGISTRY_ID,
        "authority": SEQUENCE_AUTHORITY,
    }


def exact_signature_hash(**kwargs: Any) -> str:
    return logical_hash(signature_core(**kwargs))


def declared_distance(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    left_vectors = left["ordered_axis_vectors"]
    right_vectors = right["ordered_axis_vectors"]
    maximum_states = max(len(left_vectors), len(right_vectors), 1)
    common_states = min(len(left_vectors), len(right_vectors))
    axis_mismatch = 0
    for index in range(common_states):
        for axis in AXES:
            if left_vectors[index][axis] != right_vectors[index][axis]:
                axis_mismatch += 1
    axis_mismatch += abs(len(left_vectors) - len(right_vectors)) * len(AXES)
    axis_denominator = maximum_states * len(AXES)

    left_changes = left["ordered_changed_axis_sets"]
    right_changes = right["ordered_changed_axis_sets"]
    maximum_transitions = max(len(left_changes), len(right_changes), 1)
    common_transitions = min(len(left_changes), len(right_changes))
    transition_mismatch = sum(left_changes[i] != right_changes[i] for i in range(common_transitions))
    transition_mismatch += abs(len(left_changes) - len(right_changes))

    left_durations = left.get("raw_durations", [])
    right_durations = right.get("raw_durations", [])
    duration_difference = sum(abs(a - b) for a, b in zip(left_durations, right_durations))
    duration_difference += sum(left_durations[common_transitions:]) + sum(right_durations[common_transitions:])

    left_context = set(left.get("context_markers", []))
    right_context = set(right.get("context_markers", []))
    context_difference = len(left_context.symmetric_difference(right_context))

    missingness = 0
    for vectors in (left_vectors, right_vectors):
        for vector in vectors:
            for axis in AXES:
                if vector[axis].get("status") in {"NOT_EVALUATED", "NOT_EVALUABLE", "QUARANTINED"}:
                    missingness += 1

    weighted = (
        axis_mismatch / axis_denominator
        + transition_mismatch / maximum_transitions
        + 0.5 * duration_difference
        + 0.5 * context_difference
        + missingness
    )
    return {
        "registry_id": DISTANCE_REGISTRY_ID,
        "components": {
            "axis_mismatch": {"raw": axis_mismatch, "denominator": axis_denominator, "weight": "1.0"},
            "transition_mismatch": {"raw": transition_mismatch, "denominator": maximum_transitions, "weight": "1.0"},
            "duration_difference": {"raw": duration_difference, "weight": "0.5"},
            "context_difference": {"raw": context_difference, "weight": "0.5"},
            "missingness": {"raw": missingness, "weight": "1.0"},
        },
        "total_distance": str(weighted),
        "tie_break": ["TOTAL_DISTANCE_ASC", "EXACT_SIGNATURE_ID_ASC", "SEQUENCE_ID_ASC"],
        "learned_weights": "PROHIBITED",
        "recommendation": "PROHIBITED",
    }


def count_cell(count: int, denominator: int, slice_identity: str) -> dict[str, Any]:
    return {
        "count": count,
        "eligible_denominator": denominator,
        "excluded_count": 0,
        "missing_count": 0,
        "slice_identity": slice_identity,
        "display_style": "UNIFORM_NON_DATA_DRIVEN_IDENTITY_ORDERED",
        "display_text": f"{count} of {denominator} eligible records",
    }


def diversity_audit(population_id: str, signature_counts: Sequence[int], *, batch: bool = False) -> dict[str, Any]:
    ordered = sorted((count for count in signature_counts if count > 0), reverse=True)
    total = sum(ordered)
    distinct = len(ordered)
    if total and distinct > 1:
        entropy = -sum((count / total) * math.log(count / total) for count in ordered) / math.log(distinct)
    elif total and distinct == 1:
        entropy = 0.0
    else:
        entropy = 0.0
    top1 = sum(ordered[:1])
    top5 = sum(ordered[:5])
    top10 = sum(ordered[:10])
    if total < 100:
        status = "INSUFFICIENT_SAMPLE_FOR_DIVERSITY_AUDIT"
    elif (
        entropy < 0.55
        or top1 / total > 0.12
        or top5 / total > 0.30
        or top10 / total > 0.45
        or (batch and top1 / total > 0.20)
    ):
        status = "SIGNATURE_CONCENTRATION_WARNING"
    else:
        status = "PASS"
    core = {
        "population_id": population_id,
        "candidate_count": total,
        "distinct_exact_signature_count": distinct,
        "normalized_shannon_entropy": round(entropy, 12),
        "top_1": count_cell(top1, total, population_id + "|TOP1"),
        "top_5": count_cell(top5, total, population_id + "|TOP5"),
        "top_10": count_cell(top10, total, population_id + "|TOP10"),
        "review_batch_signature_cap": 0.2,
        "status": status,
        "acknowledgement_record_id": None,
        "exception_disclosure": None,
    }
    core["audit_id"] = "RO4.DIVERSITY." + logical_hash(core)
    core["logical_hash"] = logical_hash(core)
    return core


def write_json(path: Path, value: Any) -> dict[str, Any]:
    path.write_bytes(canonical_bytes(value))
    return {"file": path.name, "sha256": sha256_file(path), "size_bytes": path.stat().st_size}


def write_gzip_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    digest = hashlib.sha256()
    count = 0
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=1, mtime=0) as handle:
            for record in records:
                line = canonical_bytes(record)
                digest.update(line)
                handle.write(line)
                count += 1
    return {
        "file": path.name,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "record_count": count,
        "record_stream_sha256": digest.hexdigest(),
    }


def iter_gzip_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.endswith("\n"):
                raise RO4IndexError(f"UNTERMINATED_SEQUENCE_JSONL:{path.name}:{line_number}")
            value = json.loads(line)
            if not isinstance(value, dict):
                raise RO4IndexError(f"NON_OBJECT_SEQUENCE_JSONL:{path.name}:{line_number}")
            yield value


def machine_identity() -> dict[str, Any]:
    return {"machine": "LOCAL_REFERENCE_RUNNER", "os": f"{platform.system()} {platform.release()}", "python": platform.python_version()}
