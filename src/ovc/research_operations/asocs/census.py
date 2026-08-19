"""ASOCS WP5 deterministic census prebuild.

The engine consumes frozen 15M audit-surface records. It does not retrieve providers,
invent side/clock identity, or mark G3 complete. Real G3 completion requires the exact
bound G1 artifact and two clean logically identical executions.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping

from .audit_execution import UPPER_CONSTRUCTS, evaluate_c1_morphology, not_evaluable_record


class ASOCSCensusError(ValueError):
    pass


def _bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def content_id(value: Any) -> str:
    return hashlib.sha256(_bytes(value)).hexdigest()


def observation_trace(record: Mapping[str, Any], prior_complete: Mapping[str, Any] | None = None) -> dict[str, Any]:
    required = {"bucket_id", "interval_start", "interval_end", "region", "status"}
    if not required.issubset(record):
        raise ASOCSCensusError("MISSING_AUDIT_SURFACE_FIELDS")
    status = str(record["status"])
    trace: dict[str, Any] = {
        "schema": "ovc-asocs-observation-trace/v0_1",
        "object_id": str(record["bucket_id"]),
        "interval_start": str(record["interval_start"]),
        "interval_end": str(record["interval_end"]),
        "region": str(record["region"]),
        "source_status": status,
        "authority_class": "ASOCS_AUDIT_ONLY",
        "active": False,
        "canonical": False,
        "publication": False,
    }
    if status == "COMPLETE":
        current = {k: record[k] for k in ("open", "high", "low", "close")}
        prior = None
        contiguous = False
        if prior_complete is not None and record.get("prior_contiguous") is True:
            prior = {k: prior_complete[k] for k in ("open", "high", "low", "close")}
            contiguous = True
        trace["c1"] = evaluate_c1_morphology(current, prior=prior, prior_contiguous=contiguous)
    else:
        trace["c1"] = {
            "construct": "C1_ARITHMETIC_PRIMITIVES",
            "disposition": "NOT_EVALUABLE_SOURCE",
            "reason": "SOURCE_" + status,
        }
    trace["upper_stack"] = {name: not_evaluable_record(name) for name in UPPER_CONSTRUCTS}
    trace["trace_sha256"] = content_id(trace)
    return trace


def build_census(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [dict(r) for r in records]
    ids = [str(r.get("bucket_id")) for r in rows]
    if len(ids) != len(set(ids)):
        raise ASOCSCensusError("DUPLICATE_LOGICAL_BUCKET")
    traces: list[dict[str, Any]] = []
    previous_complete: Mapping[str, Any] | None = None
    for row in rows:
        trace = observation_trace(row, previous_complete)
        traces.append(trace)
        previous_complete = row if row.get("status") == "COMPLETE" else None
    manifest_basis = {
        "schema": "ovc-asocs-census-manifest/v0_1",
        "record_count": len(traces),
        "trace_ids": [t["trace_sha256"] for t in traces],
        "source_status_counts": {
            state: sum(t["source_status"] == state for t in traces)
            for state in sorted({t["source_status"] for t in traces})
        },
        "authority_class": "ASOCS_AUDIT_ONLY",
    }
    return {**manifest_basis, "census_sha256": content_id(manifest_basis), "traces": traces}


def checkpoint_prefix(census: Mapping[str, Any], count: int) -> dict[str, Any]:
    traces = list(census["traces"])
    if count < 0 or count > len(traces):
        raise ASOCSCensusError("CHECKPOINT_RANGE")
    prefix = [t["trace_sha256"] for t in traces[:count]]
    basis = {"count": count, "trace_ids": prefix}
    return {**basis, "prefix_sha256": content_id(basis)}


def verify_restart(checkpoint: Mapping[str, Any], census: Mapping[str, Any]) -> bool:
    return checkpoint_prefix(census, int(checkpoint["count"])) == dict(checkpoint)


def prove_two_run_equality(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    frozen = [dict(r) for r in records]
    a = build_census(frozen)
    b = build_census(frozen)
    return {
        "result": "PASS" if a["census_sha256"] == b["census_sha256"] else "FAIL",
        "run_a": a["census_sha256"],
        "run_b": b["census_sha256"],
        "logical_equal": a["census_sha256"] == b["census_sha256"],
    }
