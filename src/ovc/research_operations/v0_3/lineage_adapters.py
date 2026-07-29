from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable, Mapping


DOWNSTREAM_AUTHORITY_BANNER = (
    "DOWNSTREAM TRACE — READ ONLY. C2 AND PATTERN DISCOVERY AUTHORITY IS UNCHANGED."
)
LIVE_ROUTE_STATE = "DISABLED_PENDING_RC_G4"

_ALLOWED_SOURCES: dict[str, dict[str, str]] = {
    "DISCOVERY": {
        "c1_release_id": "OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1",
        "c1_manifest_sha256": "6abd6d1fb74e7f3797e9add2435eaa5e487b612efd2f4b5f4f4c59679820d5d2",
        "opt_a_release_id": "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
    },
    "DEVELOPMENT": {
        "c1_release_id": "OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1",
        "c1_manifest_sha256": "ca83f2d9d948be426f3d80ebc91cc981f92546dfdd07268d71938d618c51f017",
        "opt_a_release_id": "OPT-A.GBPUSD.DEVELOPMENT.2024.v2",
    },
}
_ALLOWED_CLOCKS = {"15M", "2H_A_L"}
_ALLOWED_SIDES = {"BID", "ASK"}
_ALLOWED_CHILD_TYPES = {
    "C2_STATE",
    "C2_TRANSITION",
    "PATTERN_DISCOVERY_TRIGGER",
    "PATTERN_DISCOVERY_CANDIDATE_REFERENCE",
}
_ALLOWED_OPERATION_MODES = {
    "LIVE_PROSPECTIVE",
    "TIME_GATED_REPLAY",
    "NON_EVIDENTIARY_REPLAY",
    "HISTORICAL_TRACE",
}
_WRITE_KEYS = {
    "write",
    "writes_allowed",
    "git_write",
    "r2_write",
    "selector_write",
    "release_write",
    "threshold_write",
    "mutation",
    "mutate",
    "activate",
    "promote",
    "recompute",
    "tune",
    "delete",
    "patch",
    "actions",
    "controls",
}
_DOWNSTREAM_PROHIBITED_KEYS = {
    "defect",
    "severity",
    "confidence",
    "score",
    "priority",
    "fix_priority",
    "candidate_quality",
    "recommended_action",
    "remediation",
    "tuning",
    "null_reason",
    "formula",
    "formula_output",
}
_FACT_PROHIBITED_KEYS = {
    "c2_transition",
    "c2_state",
    "pattern_discovery",
    "candidate_quality",
    "downstream_trace",
    "downstream_child_ids",
    "defect_score",
    "tuning",
    "recommended_action",
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ProjectionDenied(ValueError):
    """Raised before forbidden role content, writes or mixed authority are resolved."""


class ProjectionContractError(ValueError):
    """Raised when an RO3-WP4 projection violates the frozen contract."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _projection_id(kind: str, payload: Mapping[str, Any]) -> str:
    return f"RO3-C1-{kind}-{_digest(payload)[:20]}"


def _walk_keys(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield str(key).strip().lower()
            yield from _walk_keys(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk_keys(item)


def _guard_no_write_capability(value: Any) -> None:
    keys = set(_walk_keys(value))
    forbidden = sorted(keys.intersection(_WRITE_KEYS))
    suffix_forbidden = sorted(key for key in keys if key.endswith("_write") or key.endswith("_mutation"))
    if forbidden or suffix_forbidden:
        raise ProjectionDenied(
            f"READ_ONLY_PROJECTION_REQUIRED:{sorted(set(forbidden + suffix_forbidden))}"
        )


def _guard_role(role: str) -> dict[str, str]:
    normalized = str(role or "").strip().upper()
    if normalized == "VALIDATION":
        raise ProjectionDenied("VALIDATION_DENY_BEFORE_PATH_OBJECT_OR_RECORD_RESOLUTION")
    if normalized not in _ALLOWED_SOURCES:
        raise ProjectionDenied(f"UNKNOWN_OR_UNAUTHORISED_ROLE:{normalized or 'MISSING'}")
    return _ALLOWED_SOURCES[normalized]


def _validate_release_context(context: Mapping[str, Any]) -> dict[str, Any]:
    _guard_no_write_capability(context)
    role = str(context.get("role", "")).upper()
    expected = _guard_role(role)
    required = {
        "role",
        "c1_release_id",
        "c1_manifest_sha256",
        "formula_registry_id",
        "formula_registry_logical_sha256",
        "represented_commit",
        "source_commit",
        "clock",
        "side",
    }
    missing = sorted(required - context.keys())
    if missing:
        raise ProjectionContractError(f"release context missing fields: {missing}")
    if context["c1_release_id"] != expected["c1_release_id"]:
        raise ProjectionContractError("unexpected C1 release identity")
    if context["c1_manifest_sha256"] != expected["c1_manifest_sha256"]:
        raise ProjectionContractError("unexpected C1 manifest identity")
    if context["formula_registry_id"] != "C1.FORMULAS.v0.1":
        raise ProjectionContractError("unknown formula registry")
    if not _SHA256_RE.fullmatch(str(context["formula_registry_logical_sha256"])):
        raise ProjectionContractError("invalid formula registry logical hash")
    if str(context["clock"]) not in _ALLOWED_CLOCKS:
        raise ProjectionContractError("unknown clock")
    if str(context["side"]) not in _ALLOWED_SIDES:
        raise ProjectionContractError("unknown price side")
    return {
        "role": role,
        "c1_release_id": str(context["c1_release_id"]),
        "c1_manifest_sha256": str(context["c1_manifest_sha256"]),
        "formula_registry_id": "C1.FORMULAS.v0.1",
        "formula_registry_logical_sha256": str(context["formula_registry_logical_sha256"]),
        "represented_commit": str(context["represented_commit"]),
        "source_commit": str(context["source_commit"]),
        "clock": str(context["clock"]),
        "side": str(context["side"]),
    }


def _validate_c1_record(record: Mapping[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
    _guard_no_write_capability(record)
    expected = _guard_role(str(context["role"]))
    required = {
        "record_id",
        "record_type",
        "schema_version",
        "formula_registry_id",
        "formula_registry_sha256",
        "opt_a_release_id",
        "opt_a_manifest_id",
        "source_bar_id",
        "prior_bar_id",
        "instrument",
        "clock",
        "price_side",
        "open_time",
        "close_time",
        "first_valid_time",
        "source_lineage",
        "measurements",
        "null_reasons",
        "formula_versions",
        "authority_state",
    }
    missing = sorted(required - record.keys())
    if missing:
        raise ProjectionContractError(f"C1 record missing fields: {missing}")
    if record["record_type"] != "OPT_B_C1_BAR_PRIMITIVES" or record["schema_version"] != "0.1":
        raise ProjectionContractError("unknown C1 record schema")
    if record["formula_registry_id"] != "C1.FORMULAS.v0.1":
        raise ProjectionContractError("C1 record uses unknown formula registry")
    if record["opt_a_release_id"] != expected["opt_a_release_id"]:
        raise ProjectionContractError("C1 record uses unexpected OPT-A parent")
    if record["instrument"] != "GBPUSD":
        raise ProjectionContractError("instrument expansion is not authorised")
    if record["clock"] != context["clock"] or record["price_side"] != context["side"]:
        raise ProjectionContractError("record clock or side does not match release context")
    lineage = record["source_lineage"]
    if not isinstance(lineage, Mapping):
        raise ProjectionContractError("source_lineage must be an object")
    source_objects = sorted(set(str(item) for item in lineage.get("source_object_ids", [])))
    parent_bars = sorted(set(str(item) for item in lineage.get("parent_m1_bar_ids", [])))
    contract_versions = dict(sorted((str(k), str(v)) for k, v in (lineage.get("contract_versions") or {}).items()))
    if not source_objects or not parent_bars or len(contract_versions) < 3:
        raise ProjectionContractError("C1 source lineage is incomplete")
    return {
        "record_id": str(record["record_id"]),
        "record_type": str(record["record_type"]),
        "schema_version": str(record["schema_version"]),
        "formula_registry_id": str(record["formula_registry_id"]),
        "formula_registry_sha256": str(record["formula_registry_sha256"]),
        "opt_a_release_id": str(record["opt_a_release_id"]),
        "opt_a_manifest_id": str(record["opt_a_manifest_id"]),
        "source_bar_id": str(record["source_bar_id"]),
        "prior_bar_id": record["prior_bar_id"],
        "instrument": "GBPUSD",
        "clock": str(record["clock"]),
        "price_side": str(record["price_side"]),
        "open_time": str(record["open_time"]),
        "close_time": str(record["close_time"]),
        "first_valid_time": str(record["first_valid_time"]),
        "measurements": dict(record["measurements"]),
        "null_reasons": dict(sorted((str(k), str(v)) for k, v in record["null_reasons"].items())),
        "formula_versions": dict(sorted((str(k), str(v)) for k, v in record["formula_versions"].items())),
        "authority_state": str(record["authority_state"]),
        "source_lineage": {
            "source_object_ids": source_objects,
            "parent_m1_bar_ids": parent_bars,
            "contract_versions": contract_versions,
        },
    }


def build_c1_lineage_trace(
    *,
    release_context: Mapping[str, Any],
    c1_record: Mapping[str, Any],
) -> dict[str, Any]:
    context = _validate_release_context(release_context)
    record = _validate_c1_record(c1_record, context)
    chain = (
        {
            "layer": "OPT-B.C1",
            "object_id": record["record_id"],
            "release_id": context["c1_release_id"],
            "manifest_sha256": context["c1_manifest_sha256"],
            "formula_registry_id": record["formula_registry_id"],
            "formula_registry_sha256": record["formula_registry_sha256"],
        },
        {
            "layer": "OPT-A",
            "object_id": record["source_bar_id"],
            "release_id": record["opt_a_release_id"],
            "manifest_id": record["opt_a_manifest_id"],
            "first_valid_time": record["first_valid_time"],
        },
        {
            "layer": "PROVIDER_SOURCE",
            "object_ids": record["source_lineage"]["source_object_ids"],
        },
        {
            "layer": "M1_PARENT_BARS",
            "object_ids": record["source_lineage"]["parent_m1_bar_ids"],
        },
    )
    payload = {
        "schema": "ovc-ro3-c1-lineage-trace/v1",
        "object_type": "RO3.C1LineageTrace.v1",
        "panel_id": "RO3-C1-UPSTREAM-LINEAGE",
        "status": "COMPLETE",
        "role": context["role"],
        "c1_record_id": record["record_id"],
        "first_valid_time": record["first_valid_time"],
        "chain": list(chain),
        "contract_versions": record["source_lineage"]["contract_versions"],
        "source_refs": [
            f"c1-release:{context['c1_release_id']}",
            f"c1-manifest-sha256:{context['c1_manifest_sha256']}",
            f"c1-record:{record['record_id']}",
            f"opt-a-release:{record['opt_a_release_id']}",
            f"opt-a-bar:{record['source_bar_id']}",
        ],
        "authority": "READ_ONLY_TRACE",
        "read_only": True,
        "writes": "NONE",
    }
    return {**payload, "trace_id": _projection_id("LINEAGE", payload), "logical_sha256": _digest(payload)}


def build_c1_fact_projection(
    *,
    release_context: Mapping[str, Any],
    c1_record: Mapping[str, Any],
    formula_evidence: Mapping[str, Any],
    lineage_trace: Mapping[str, Any],
) -> dict[str, Any]:
    context = _validate_release_context(release_context)
    record = _validate_c1_record(c1_record, context)
    _guard_no_write_capability(formula_evidence)
    prohibited = sorted(set(_walk_keys(formula_evidence)).intersection(_FACT_PROHIBITED_KEYS))
    if prohibited:
        raise ProjectionDenied(f"FACT_PANEL_MIXED_WITH_DOWNSTREAM_AUTHORITY:{prohibited}")
    required = {"primitive_id", "field_name", "inputs", "formula", "unit", "domain", "first_valid_time"}
    missing = sorted(required - formula_evidence.keys())
    if missing:
        raise ProjectionContractError(f"formula evidence missing fields: {missing}")
    field_name = str(formula_evidence["field_name"])
    primitive_id = str(formula_evidence["primitive_id"])
    if field_name not in record["measurements"]:
        raise ProjectionContractError("formula evidence field is not present in the C1 record")
    if record["formula_versions"].get(field_name) != primitive_id:
        raise ProjectionContractError("formula evidence primitive does not match record formula version")
    output = record["measurements"][field_name]
    null_reason = record["null_reasons"].get(field_name)
    if formula_evidence.get("output", output) != output:
        raise ProjectionContractError("formula evidence output does not match the C1 record")
    if formula_evidence.get("null_reason", null_reason) != null_reason:
        raise ProjectionContractError("formula evidence null reason does not match the C1 record")
    if lineage_trace.get("c1_record_id") != record["record_id"] or lineage_trace.get("status") != "COMPLETE":
        raise ProjectionContractError("fact projection requires a complete matching lineage trace")
    payload = {
        "schema": "ovc-ro3-c1-formula-evidence-card/v1",
        "object_type": "RO3.C1FormulaEvidenceCard.v1",
        "panel_id": "RO3-C1-FACT-INSPECTOR",
        "role": context["role"],
        "release_id": context["c1_release_id"],
        "manifest_sha256": context["c1_manifest_sha256"],
        "c1_record_id": record["record_id"],
        "primitive_id": primitive_id,
        "field_name": field_name,
        "inputs": dict(sorted((str(k), v) for k, v in formula_evidence["inputs"].items())),
        "formula": str(formula_evidence["formula"]),
        "output": output,
        "unit": str(formula_evidence["unit"]),
        "domain": formula_evidence["domain"],
        "null_reason": null_reason,
        "first_valid_time": str(formula_evidence["first_valid_time"]),
        "lineage_trace_id": str(lineage_trace["trace_id"]),
        "authority": "DERIVED_EXPLANATION_ONLY",
        "read_only": True,
        "writes": "NONE",
    }
    return {**payload, "projection_id": _projection_id("FACT", payload), "logical_sha256": _digest(payload)}


def build_downstream_trace_projection(
    *,
    c1_record_id: str,
    child_references: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for reference in child_references:
        _guard_no_write_capability(reference)
        prohibited = sorted(set(_walk_keys(reference)).intersection(_DOWNSTREAM_PROHIBITED_KEYS))
        if prohibited:
            raise ProjectionDenied(f"DOWNSTREAM_TRACE_PROHIBITED_PRESENTATION:{prohibited}")
        required = {
            "child_id",
            "child_type",
            "source_c1_record_id",
            "source_binding",
            "operation_mode",
            "cutoff",
            "availability",
            "trace_status",
        }
        missing = sorted(required - reference.keys())
        if missing:
            raise ProjectionContractError(f"child reference missing fields: {missing}")
        if reference["source_c1_record_id"] != c1_record_id:
            raise ProjectionContractError("child reference is not bound to the selected C1 record")
        if reference["child_type"] not in _ALLOWED_CHILD_TYPES:
            raise ProjectionContractError("unknown downstream child type")
        if reference["operation_mode"] not in _ALLOWED_OPERATION_MODES:
            raise ProjectionContractError("unknown downstream operation mode")
        rows.append(
            {
                "child_id": str(reference["child_id"]),
                "child_type": str(reference["child_type"]),
                "source_c1_record_id": str(reference["source_c1_record_id"]),
                "source_binding": str(reference["source_binding"]),
                "operation_mode": str(reference["operation_mode"]),
                "cutoff": str(reference["cutoff"]),
                "availability": str(reference["availability"]),
                "trace_status": str(reference["trace_status"]),
            }
        )
    rows.sort(key=lambda item: (item["child_type"], item["child_id"]))
    status = "AVAILABLE" if rows else "TRACE_NOT_AVAILABLE"
    payload = {
        "schema": "ovc-ro3-downstream-trace-projection/v1",
        "object_type": "RO3.DownstreamTraceProjection.v1",
        "panel_id": "RO3-C1-DOWNSTREAM-TRACE",
        "banner": DOWNSTREAM_AUTHORITY_BANNER,
        "status": status,
        "c1_record_id": str(c1_record_id),
        "child_references": rows,
        "sorting": "IDENTITY_ONLY_NO_SCORE_OR_PRIORITY",
        "authority": "READ_ONLY_TRACE",
        "c2_authority": "UNCHANGED",
        "pattern_discovery_authority": "UNCHANGED",
        "read_only": True,
        "writes": "NONE",
    }
    return {**payload, "projection_id": _projection_id("DOWNSTREAM", payload), "logical_sha256": _digest(payload)}


def build_c1_console_projection(
    *,
    release_context: Mapping[str, Any],
    fact_projection: Mapping[str, Any],
    computability_projection: Mapping[str, Any],
    assurance_projection: Mapping[str, Any],
    lineage_trace: Mapping[str, Any],
    downstream_trace: Mapping[str, Any],
) -> dict[str, Any]:
    context = _validate_release_context(release_context)
    for projection in (
        fact_projection,
        computability_projection,
        assurance_projection,
        lineage_trace,
        downstream_trace,
    ):
        _guard_no_write_capability(projection)
    if fact_projection.get("panel_id") != "RO3-C1-FACT-INSPECTOR":
        raise ProjectionContractError("fact panel identity is invalid")
    if lineage_trace.get("panel_id") != "RO3-C1-UPSTREAM-LINEAGE":
        raise ProjectionContractError("lineage panel identity is invalid")
    if downstream_trace.get("panel_id") != "RO3-C1-DOWNSTREAM-TRACE":
        raise ProjectionContractError("downstream panel identity is invalid")
    if downstream_trace.get("banner") != DOWNSTREAM_AUTHORITY_BANNER:
        raise ProjectionContractError("permanent downstream authority banner is missing")
    if set(_walk_keys(fact_projection)).intersection(_FACT_PROHIBITED_KEYS):
        raise ProjectionDenied("C1_FACT_AND_DOWNSTREAM_TRACE_MUST_REMAIN_SEPARATE")
    if fact_projection.get("c1_record_id") != lineage_trace.get("c1_record_id"):
        raise ProjectionContractError("fact and lineage projections reference different C1 records")
    if fact_projection.get("c1_record_id") != downstream_trace.get("c1_record_id"):
        raise ProjectionContractError("fact and downstream projections reference different C1 records")
    stale = context["represented_commit"] != context["source_commit"]
    status = "STALE_PROJECTION" if stale else "READY_CANDIDATE"
    payload = {
        "schema": "ovc-ro3-c1-console-projection/v1",
        "object_type": "RO3.C1ConsoleProjection.v1",
        "route_id": "RESEARCH.C1_FACT_ASSURANCE",
        "route_state": LIVE_ROUTE_STATE,
        "route_enabled": False,
        "status": status,
        "source_context": context,
        "panels": {
            "fact": dict(fact_projection),
            "computability": dict(computability_projection),
            "assurance": dict(assurance_projection),
            "upstream_lineage": dict(lineage_trace),
            "downstream_trace": dict(downstream_trace),
        },
        "panel_separation": {
            "fact_panel_id": "RO3-C1-FACT-INSPECTOR",
            "downstream_panel_id": "RO3-C1-DOWNSTREAM-TRACE",
            "mixed_compact_object": "DENIED",
            "null_reason_and_c2_transition_compact_corender": "DENIED",
        },
        "authority": "LOCAL_READ_ONLY_PRESENTATION_ADAPTERS",
        "live_consumption_authority": "NONE_PENDING_RC_G4",
        "validation_consumption": "LOCKED_UNCONSUMED",
        "read_only": True,
        "writes": "NONE",
    }
    return {**payload, "projection_id": _projection_id("CONSOLE", payload), "logical_sha256": _digest(payload)}
