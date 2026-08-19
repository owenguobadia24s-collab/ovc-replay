"""ASOCS WP5 deterministic full-population census.

Consumes the frozen ASOCS 15M audit surface, preserves source missingness and
lineage, evaluates only the lawfully admitted C1 morphology route, and fails
closed for every exact-active upper-stack construct. G3 completion additionally
requires the exact G1 source binding and two clean logically identical runs.
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


def _object_id(record: Mapping[str, Any]) -> str:
    value = record.get("bucket_id") or record.get("bar_id")
    if not value:
        raise ASOCSCensusError("MISSING_LOGICAL_OBJECT_ID")
    return str(value)


def _is_contiguous(prior: Mapping[str, Any] | None, current: Mapping[str, Any]) -> bool:
    return bool(
        prior is not None
        and prior.get("status") == "COMPLETE"
        and str(prior.get("interval_end")) == str(current.get("interval_start"))
    )


def observation_trace(
    record: Mapping[str, Any],
    prior_complete: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    required = {"interval_start", "interval_end", "region", "status"}
    if not required.issubset(record):
        raise ASOCSCensusError("MISSING_AUDIT_SURFACE_FIELDS")
    status = str(record["status"])
    trace: dict[str, Any] = {
        "schema": "ovc-asocs-observation-trace/v0_2",
        "object_id": _object_id(record),
        "clock": str(record.get("clock", "15M")),
        "interval_start": str(record["interval_start"]),
        "interval_end": str(record["interval_end"]),
        "effective_time": str(record.get("effective_time", record["interval_end"])),
        "first_valid_time": str(record.get("first_valid_time", record["interval_end"])),
        "region": str(record["region"]),
        "source_status": status,
        "source_lineage": {
            "parent_source_row_ids": [str(x) for x in record.get("parent_source_row_ids", [])],
            "missing_parent_slots": [str(x) for x in record.get("missing_parent_slots", [])],
            "repair_applied": bool(record.get("repair_applied", False)),
        },
        "authority_class": "ASOCS_AUDIT_ONLY",
        "active": False,
        "canonical": False,
        "publication": False,
    }
    if status == "COMPLETE":
        current = {k: record[k] for k in ("open", "high", "low", "close")}
        contiguous = _is_contiguous(prior_complete, record)
        prior = (
            {k: prior_complete[k] for k in ("open", "high", "low", "close")}
            if contiguous and prior_complete is not None
            else None
        )
        trace["c1"] = evaluate_c1_morphology(current, prior=prior, prior_contiguous=contiguous)
    else:
        trace["c1"] = {
            "construct": "C1_ARITHMETIC_PRIMITIVES",
            "disposition": "NOT_EVALUABLE_SOURCE",
            "reason": "SOURCE_" + status,
            "authority_class": "ASOCS_AUDIT_ONLY",
            "active": False,
            "canonical": False,
            "publication": False,
        }
    trace["upper_stack"] = {name: not_evaluable_record(name) for name in UPPER_CONSTRUCTS}
    trace["trace_sha256"] = content_id(trace)
    return trace


def build_census(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [dict(r) for r in records]
    ids = [_object_id(r) for r in rows]
    if len(ids) != len(set(ids)):
        raise ASOCSCensusError("DUPLICATE_LOGICAL_BUCKET")
    traces: list[dict[str, Any]] = []
    previous: Mapping[str, Any] | None = None
    for row in rows:
        trace = observation_trace(row, previous)
        traces.append(trace)
        previous = row
    region_status_counts: dict[str, dict[str, int]] = {}
    target_month_status_counts: dict[str, dict[str, int]] = {}
    for t in traces:
        region = str(t["region"])
        status = str(t["source_status"])
        region_status_counts.setdefault(region, {})[status] = region_status_counts.setdefault(region, {}).get(status, 0) + 1
        if region == "TARGET":
            month = str(t["interval_start"])[:7]
            target_month_status_counts.setdefault(month, {})[status] = target_month_status_counts.setdefault(month, {}).get(status, 0) + 1
    manifest_basis = {
        "schema": "ovc-asocs-census-manifest/v0_2",
        "record_count": len(traces),
        "target_record_count": sum(t["region"] == "TARGET" for t in traces),
        "trace_ids": [t["trace_sha256"] for t in traces],
        "ordered_trace_ids_sha256": content_id([t["trace_sha256"] for t in traces]),
        "source_status_counts": {
            state: sum(t["source_status"] == state for t in traces)
            for state in sorted({t["source_status"] for t in traces})
        },
        "region_status_counts": {
            r: dict(sorted(v.items())) for r, v in sorted(region_status_counts.items())
        },
        "target_month_status_counts": {
            m: dict(sorted(v.items())) for m, v in sorted(target_month_status_counts.items())
        },
        "c1_morphology_evaluable_count": sum(t["source_status"] == "COMPLETE" for t in traces),
        "upper_stack_constructs": list(UPPER_CONSTRUCTS),
        "upper_stack_disposition": "NOT_EVALUABLE_EXACT_ACTIVE_INTERFACE",
        "authority_class": "ASOCS_AUDIT_ONLY",
        "active": False,
        "canonical": False,
        "publication": False,
    }
    census_identity_basis = {k: v for k, v in manifest_basis.items() if k != "trace_ids"}
    census_identity_basis["trace_ids"] = manifest_basis["trace_ids"]
    return {
        **manifest_basis,
        "census_sha256": content_id(census_identity_basis),
        "traces": traces,
    }


def compact_manifest(census: Mapping[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in census.items() if k not in {"traces", "trace_ids"}}


def checkpoint_prefix(census: Mapping[str, Any], count: int) -> dict[str, Any]:
    traces = list(census["traces"])
    if count < 0 or count > len(traces):
        raise ASOCSCensusError("CHECKPOINT_RANGE")
    prefix = [t["trace_sha256"] for t in traces[:count]]
    basis = {"count": count, "trace_ids": prefix}
    return {"count": count, "prefix_sha256": content_id(basis)}


def verify_restart(checkpoint: Mapping[str, Any], census: Mapping[str, Any]) -> bool:
    return checkpoint_prefix(census, int(checkpoint["count"])) == dict(checkpoint)


def prove_two_run_equality(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    frozen = [dict(r) for r in records]
    a = build_census(frozen)
    b = build_census(frozen)
    trace_equal = [t["trace_sha256"] for t in a["traces"]] == [t["trace_sha256"] for t in b["traces"]]
    logical_equal = a["census_sha256"] == b["census_sha256"] and trace_equal
    return {
        "result": "PASS" if logical_equal else "FAIL",
        "run_a": a["census_sha256"],
        "run_b": b["census_sha256"],
        "ordered_trace_ids_equal": trace_equal,
        "logical_equal": logical_equal,
    }
