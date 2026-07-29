from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

ROUTE_SCHEMA = "ovc-research-console-rc-g4-live-c1-consumption/v1"
ROUTE_ID = "RESEARCH.C1_FACT_ASSURANCE"
ROUTE_STATE = "ENABLED_LOCAL_READ_ONLY"
DOWNSTREAM_AUTHORITY_BANNER = (
    "DOWNSTREAM TRACE — READ ONLY. C2 AND PATTERN DISCOVERY AUTHORITY IS UNCHANGED."
)

SCHEMA_BINDINGS: tuple[dict[str, str], ...] = (
    {
        "object_type": "RO3.C1ConsoleProjection.v1",
        "payload_schema": "ovc-ro3-c1-console-projection/v1",
        "schema_id": "ovc://schemas/research_operations/v0_3/c1_console_projection_v0_1",
        "path": "schemas/research_operations/v0_3/c1_console_projection_v0_1.schema.json",
        "git_blob_sha": "cffb5618e942019f4dc7a0e580d4813c1537247e",
    },
    {
        "object_type": "RO3.C1FormulaEvidenceCard.v1",
        "payload_schema": "ovc-ro3-c1-formula-evidence-card/v1",
        "schema_id": "ovc://schemas/research_operations/v0_3/c1_formula_evidence_card_v0_1",
        "path": "schemas/research_operations/v0_3/c1_formula_evidence_card_v0_1.schema.json",
        "git_blob_sha": "a32ddfaa4d27f06ce33d47f4581569b6fdc1dae9",
    },
    {
        "object_type": "RO3.C1LineageTrace.v1",
        "payload_schema": "ovc-ro3-c1-lineage-trace/v1",
        "schema_id": "ovc://schemas/research_operations/v0_3/c1_lineage_trace_v0_1",
        "path": "schemas/research_operations/v0_3/c1_lineage_trace_v0_1.schema.json",
        "git_blob_sha": "f7ddd3535ca58bcef6ef620bfd6152340f7461e3",
    },
    {
        "object_type": "RO3.DownstreamTraceProjection.v1",
        "payload_schema": "ovc-ro3-downstream-trace-projection/v1",
        "schema_id": "ovc://schemas/research_operations/v0_3/downstream_trace_projection_v0_1",
        "path": "schemas/research_operations/v0_3/downstream_trace_projection_v0_1.schema.json",
        "git_blob_sha": "908c5323d3f7b5c55b6ad6becc1fd9a31f12331b",
    },
)

_ALLOWED_SOURCES: dict[str, dict[str, str]] = {
    "DISCOVERY": {
        "c1_release_id": "OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v1",
        "c1_manifest_sha256": "6abd6d1fb74e7f3797e9add2435eaa5e487b612efd2f4b5f4f4c59679820d5d2",
    },
    "DEVELOPMENT": {
        "c1_release_id": "OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v1",
        "c1_manifest_sha256": "ca83f2d9d948be426f3d80ebc91cc981f92546dfdd07268d71938d618c51f017",
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
_LOCATION_OR_SECRET_KEYS = {
    "path",
    "paths",
    "local_path",
    "remote_key",
    "secret",
    "secrets",
    "token",
    "credentials",
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
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_RECORD_RE = re.compile(r"^c1:[0-9a-f]{64}$")
_PRIMITIVE_RE = re.compile(r"^C1-[A-Z0-9-]+\.v0\.1$")


class C1ProjectionDenied(ValueError):
    """Raised when a payload exceeds RC-G4 local read-only presentation authority."""


class C1ProjectionContractError(ValueError):
    """Raised when a payload does not satisfy the exact accepted RO3-G4 contract."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _git_blob_sha(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode("ascii")
    try:
        digest = hashlib.sha1(usedforsecurity=False)
    except TypeError:  # pragma: no cover - older Python compatibility
        digest = hashlib.sha1()
    digest.update(header)
    digest.update(content)
    return digest.hexdigest()


def _walk_keys(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield str(key).strip().lower()
            yield from _walk_keys(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk_keys(item)


def _guard_read_only(value: Any) -> None:
    if isinstance(value, Mapping):
        for raw_key, item in value.items():
            key = str(raw_key).strip().lower()
            if key == "writes" and item != "NONE":
                raise C1ProjectionDenied("C1_PROJECTION_WRITE_DENIED")
            if key == "read_only" and item is not True:
                raise C1ProjectionDenied("C1_PROJECTION_READ_ONLY_REQUIRED")
            if key in _WRITE_KEYS or key.endswith("_write") or key.endswith("_mutation"):
                raise C1ProjectionDenied(f"C1_PROJECTION_CAPABILITY_DENIED:{key}")
            if key in _LOCATION_OR_SECRET_KEYS:
                raise C1ProjectionDenied(f"C1_PROJECTION_LOCATION_OR_SECRET_DENIED:{key}")
            _guard_read_only(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _guard_read_only(item)


def _repo_root(schema_root: str | Path | None) -> Path:
    return Path(schema_root) if schema_root is not None else Path(__file__).resolve().parents[2]


def _verify_schema_bindings(schema_root: str | Path | None) -> list[dict[str, str]]:
    root = _repo_root(schema_root)
    verified: list[dict[str, str]] = []
    for binding in SCHEMA_BINDINGS:
        relative = binding["path"]
        source = root / relative
        try:
            raw = source.read_bytes()
            parsed = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise C1ProjectionContractError(f"C1_SCHEMA_BINDING_UNAVAILABLE:{relative}") from exc
        if _git_blob_sha(raw) != binding["git_blob_sha"]:
            raise C1ProjectionContractError(f"C1_SCHEMA_BLOB_MISMATCH:{relative}")
        if parsed.get("$id") != binding["schema_id"]:
            raise C1ProjectionContractError(f"C1_SCHEMA_ID_MISMATCH:{relative}")
        verified.append(dict(binding))
    return verified


def _require(mapping: Mapping[str, Any], required: set[str], label: str) -> None:
    missing = sorted(required - set(mapping))
    if missing:
        raise C1ProjectionContractError(f"{label}_MISSING_FIELDS:{missing}")


def _verify_logical_identity(
    value: Mapping[str, Any], *, identity_key: str, prefix: str, label: str
) -> None:
    _require(value, {identity_key, "logical_sha256"}, label)
    logical_sha256 = str(value["logical_sha256"])
    if not _SHA256_RE.fullmatch(logical_sha256):
        raise C1ProjectionContractError(f"{label}_LOGICAL_SHA_INVALID")
    payload = {key: item for key, item in value.items() if key not in {identity_key, "logical_sha256"}}
    expected = _sha256(payload)
    if logical_sha256 != expected:
        raise C1ProjectionContractError(f"{label}_LOGICAL_SHA_MISMATCH")
    if str(value[identity_key]) != f"{prefix}{expected[:20]}":
        raise C1ProjectionContractError(f"{label}_IDENTITY_MISMATCH")


def _validate_source_context(context: Mapping[str, Any]) -> dict[str, str]:
    role = str(context.get("role", "")).upper()
    if role == "VALIDATION":
        raise C1ProjectionDenied("VALIDATION_DENIED_BEFORE_PANEL_OR_RECORD_RESOLUTION")
    if role not in _ALLOWED_SOURCES:
        raise C1ProjectionDenied(f"C1_PROJECTION_ROLE_DENIED:{role or 'MISSING'}")
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
    _require(context, required, "C1_SOURCE_CONTEXT")
    expected = _ALLOWED_SOURCES[role]
    if context["c1_release_id"] != expected["c1_release_id"]:
        raise C1ProjectionContractError("C1_SOURCE_RELEASE_IDENTITY_MISMATCH")
    if context["c1_manifest_sha256"] != expected["c1_manifest_sha256"]:
        raise C1ProjectionContractError("C1_SOURCE_MANIFEST_IDENTITY_MISMATCH")
    if context["formula_registry_id"] != "C1.FORMULAS.v0.1":
        raise C1ProjectionContractError("C1_FORMULA_REGISTRY_DENIED")
    if not _SHA256_RE.fullmatch(str(context["formula_registry_logical_sha256"])):
        raise C1ProjectionContractError("C1_FORMULA_REGISTRY_HASH_INVALID")
    if str(context["clock"]) not in _ALLOWED_CLOCKS:
        raise C1ProjectionContractError("C1_CLOCK_DENIED")
    if str(context["side"]) not in _ALLOWED_SIDES:
        raise C1ProjectionContractError("C1_SIDE_DENIED")
    represented = str(context["represented_commit"])
    source = str(context["source_commit"])
    if len(represented) < 7 or len(source) < 7:
        raise C1ProjectionContractError("C1_SOURCE_COMMIT_IDENTITY_INVALID")
    if represented != source:
        raise C1ProjectionDenied("C1_STALE_PROJECTION_DENIED")
    return {key: str(context[key]) for key in sorted(required)}


def _validate_fact(panel: Mapping[str, Any], context: Mapping[str, str]) -> dict[str, Any]:
    required = {
        "schema", "object_type", "panel_id", "role", "release_id", "manifest_sha256",
        "c1_record_id", "primitive_id", "field_name", "inputs", "formula", "output",
        "unit", "domain", "null_reason", "first_valid_time", "lineage_trace_id",
        "authority", "read_only", "writes", "projection_id", "logical_sha256",
    }
    _require(panel, required, "C1_FACT_PANEL")
    _guard_read_only(panel)
    prohibited = sorted(set(_walk_keys(panel)).intersection(_FACT_PROHIBITED_KEYS))
    if prohibited:
        raise C1ProjectionDenied(f"C1_FACT_PANEL_MIXED_AUTHORITY:{prohibited}")
    if panel["schema"] != "ovc-ro3-c1-formula-evidence-card/v1":
        raise C1ProjectionContractError("C1_FACT_SCHEMA_DENIED")
    if panel["object_type"] != "RO3.C1FormulaEvidenceCard.v1" or panel["panel_id"] != "RO3-C1-FACT-INSPECTOR":
        raise C1ProjectionContractError("C1_FACT_PANEL_IDENTITY_DENIED")
    if panel["role"] != context["role"] or panel["release_id"] != context["c1_release_id"]:
        raise C1ProjectionContractError("C1_FACT_SOURCE_BINDING_MISMATCH")
    if panel["manifest_sha256"] != context["c1_manifest_sha256"]:
        raise C1ProjectionContractError("C1_FACT_MANIFEST_BINDING_MISMATCH")
    if not _RECORD_RE.fullmatch(str(panel["c1_record_id"])):
        raise C1ProjectionContractError("C1_FACT_RECORD_ID_INVALID")
    if not _PRIMITIVE_RE.fullmatch(str(panel["primitive_id"])):
        raise C1ProjectionContractError("C1_FACT_PRIMITIVE_ID_INVALID")
    if panel["authority"] != "DERIVED_EXPLANATION_ONLY":
        raise C1ProjectionContractError("C1_FACT_AUTHORITY_DENIED")
    _verify_logical_identity(panel, identity_key="projection_id", prefix="RO3-C1-FACT-", label="C1_FACT")
    return dict(panel)


def _validate_lineage(panel: Mapping[str, Any], context: Mapping[str, str], record_id: str) -> dict[str, Any]:
    required = {
        "schema", "object_type", "panel_id", "status", "role", "c1_record_id",
        "first_valid_time", "chain", "contract_versions", "source_refs", "authority",
        "read_only", "writes", "trace_id", "logical_sha256",
    }
    _require(panel, required, "C1_LINEAGE_PANEL")
    _guard_read_only(panel)
    if panel["schema"] != "ovc-ro3-c1-lineage-trace/v1":
        raise C1ProjectionContractError("C1_LINEAGE_SCHEMA_DENIED")
    if panel["object_type"] != "RO3.C1LineageTrace.v1" or panel["panel_id"] != "RO3-C1-UPSTREAM-LINEAGE":
        raise C1ProjectionContractError("C1_LINEAGE_PANEL_IDENTITY_DENIED")
    if panel["role"] != context["role"] or panel["c1_record_id"] != record_id:
        raise C1ProjectionContractError("C1_LINEAGE_SOURCE_BINDING_MISMATCH")
    if panel["status"] != "COMPLETE":
        raise C1ProjectionDenied("C1_LINEAGE_INCOMPLETE")
    if not isinstance(panel["chain"], list) or len(panel["chain"]) < 4:
        raise C1ProjectionContractError("C1_LINEAGE_CHAIN_INCOMPLETE")
    if panel["authority"] != "READ_ONLY_TRACE":
        raise C1ProjectionContractError("C1_LINEAGE_AUTHORITY_DENIED")
    _verify_logical_identity(panel, identity_key="trace_id", prefix="RO3-C1-LINEAGE-", label="C1_LINEAGE")
    return dict(panel)


def _validate_downstream(panel: Mapping[str, Any], record_id: str) -> dict[str, Any]:
    required = {
        "schema", "object_type", "panel_id", "banner", "status", "c1_record_id",
        "child_references", "sorting", "authority", "c2_authority",
        "pattern_discovery_authority", "read_only", "writes", "projection_id", "logical_sha256",
    }
    _require(panel, required, "C1_DOWNSTREAM_PANEL")
    _guard_read_only(panel)
    if panel["schema"] != "ovc-ro3-downstream-trace-projection/v1":
        raise C1ProjectionContractError("C1_DOWNSTREAM_SCHEMA_DENIED")
    if panel["object_type"] != "RO3.DownstreamTraceProjection.v1" or panel["panel_id"] != "RO3-C1-DOWNSTREAM-TRACE":
        raise C1ProjectionContractError("C1_DOWNSTREAM_PANEL_IDENTITY_DENIED")
    if panel["banner"] != DOWNSTREAM_AUTHORITY_BANNER:
        raise C1ProjectionDenied("C1_DOWNSTREAM_AUTHORITY_BANNER_REQUIRED")
    if panel["c1_record_id"] != record_id:
        raise C1ProjectionContractError("C1_DOWNSTREAM_SOURCE_BINDING_MISMATCH")
    if panel["sorting"] != "IDENTITY_ONLY_NO_SCORE_OR_PRIORITY":
        raise C1ProjectionDenied("C1_DOWNSTREAM_SORTING_AUTHORITY_DENIED")
    if panel["authority"] != "READ_ONLY_TRACE" or panel["c2_authority"] != "UNCHANGED" or panel["pattern_discovery_authority"] != "UNCHANGED":
        raise C1ProjectionDenied("C1_DOWNSTREAM_AUTHORITY_DELTA_DENIED")
    references = panel["child_references"]
    if not isinstance(references, list):
        raise C1ProjectionContractError("C1_DOWNSTREAM_REFERENCES_INVALID")
    for reference in references:
        if not isinstance(reference, Mapping):
            raise C1ProjectionContractError("C1_DOWNSTREAM_REFERENCE_INVALID")
        prohibited = sorted(set(_walk_keys(reference)).intersection(_DOWNSTREAM_PROHIBITED_KEYS))
        if prohibited:
            raise C1ProjectionDenied(f"C1_DOWNSTREAM_PRESENTATION_DENIED:{prohibited}")
        required_reference = {
            "child_id", "child_type", "source_c1_record_id", "source_binding",
            "operation_mode", "cutoff", "availability", "trace_status",
        }
        _require(reference, required_reference, "C1_DOWNSTREAM_REFERENCE")
        if set(reference) != required_reference:
            raise C1ProjectionDenied("C1_DOWNSTREAM_REFERENCE_EXTRA_FIELDS_DENIED")
        if reference["source_c1_record_id"] != record_id:
            raise C1ProjectionContractError("C1_DOWNSTREAM_REFERENCE_BINDING_MISMATCH")
        if reference["child_type"] not in _ALLOWED_CHILD_TYPES:
            raise C1ProjectionContractError("C1_DOWNSTREAM_CHILD_TYPE_DENIED")
        if reference["operation_mode"] not in _ALLOWED_OPERATION_MODES:
            raise C1ProjectionContractError("C1_DOWNSTREAM_OPERATION_MODE_DENIED")
    _verify_logical_identity(panel, identity_key="projection_id", prefix="RO3-C1-DOWNSTREAM-", label="C1_DOWNSTREAM")
    return dict(panel)


def _validate_support_panel(panel: Mapping[str, Any], panel_id: str, label: str) -> dict[str, Any]:
    _guard_read_only(panel)
    if panel.get("panel_id") != panel_id:
        raise C1ProjectionContractError(f"{label}_PANEL_IDENTITY_DENIED")
    if panel.get("read_only") is not True or panel.get("writes") != "NONE":
        raise C1ProjectionDenied(f"{label}_READ_ONLY_REQUIRED")
    return dict(panel)


def validate_c1_projection_payload(
    payload: Mapping[str, Any], *, schema_root: str | Path | None = None
) -> dict[str, Any]:
    """Validate an accepted disabled RO3-G4 projection and expose an RC-G4 live envelope.

    Validation role is denied before nested panels are inspected. The accepted RO3-G4
    projection remains immutable and disabled; this function creates a separate local
    consumption envelope under the operator-approved RC-G4 authority.
    """

    verified_bindings = _verify_schema_bindings(schema_root)
    if not isinstance(payload, Mapping):
        raise C1ProjectionContractError("C1_PROJECTION_ROOT_NOT_OBJECT")
    source_context = payload.get("source_context")
    if not isinstance(source_context, Mapping):
        raise C1ProjectionContractError("C1_SOURCE_CONTEXT_MISSING")
    context = _validate_source_context(source_context)

    required = {
        "schema", "object_type", "route_id", "route_state", "route_enabled", "status",
        "source_context", "panels", "panel_separation", "authority",
        "live_consumption_authority", "validation_consumption", "read_only", "writes",
        "projection_id", "logical_sha256",
    }
    _require(payload, required, "C1_CONSOLE_PROJECTION")
    _guard_read_only(payload)
    if payload["schema"] != "ovc-ro3-c1-console-projection/v1" or payload["object_type"] != "RO3.C1ConsoleProjection.v1":
        raise C1ProjectionContractError("C1_CONSOLE_SCHEMA_DENIED")
    if payload["route_id"] != ROUTE_ID or payload["route_state"] != "DISABLED_PENDING_RC_G4" or payload["route_enabled"] is not False:
        raise C1ProjectionContractError("C1_ACCEPTED_SOURCE_ROUTE_IDENTITY_MISMATCH")
    if payload["status"] != "READY_CANDIDATE":
        raise C1ProjectionDenied("C1_SOURCE_PROJECTION_NOT_READY")
    if payload["authority"] != "LOCAL_READ_ONLY_PRESENTATION_ADAPTERS" or payload["live_consumption_authority"] != "NONE_PENDING_RC_G4":
        raise C1ProjectionContractError("C1_ACCEPTED_ADAPTER_AUTHORITY_MISMATCH")
    if payload["validation_consumption"] != "LOCKED_UNCONSUMED":
        raise C1ProjectionDenied("C1_VALIDATION_BOUNDARY_INVALID")

    panels = payload["panels"]
    if not isinstance(panels, Mapping) or set(panels) != {
        "fact", "computability", "assurance", "upstream_lineage", "downstream_trace"
    }:
        raise C1ProjectionContractError("C1_PANEL_SET_MISMATCH")
    fact = _validate_fact(panels["fact"], context)
    record_id = str(fact["c1_record_id"])
    lineage = _validate_lineage(panels["upstream_lineage"], context, record_id)
    if fact["lineage_trace_id"] != lineage["trace_id"]:
        raise C1ProjectionContractError("C1_FACT_LINEAGE_IDENTITY_MISMATCH")
    downstream = _validate_downstream(panels["downstream_trace"], record_id)
    computability = _validate_support_panel(panels["computability"], "RO3-C1-COMPUTABILITY", "C1_COMPUTABILITY")
    assurance = _validate_support_panel(panels["assurance"], "RO3-C1-ASSURANCE", "C1_ASSURANCE")

    separation = payload["panel_separation"]
    expected_separation = {
        "fact_panel_id": "RO3-C1-FACT-INSPECTOR",
        "downstream_panel_id": "RO3-C1-DOWNSTREAM-TRACE",
        "mixed_compact_object": "DENIED",
        "null_reason_and_c2_transition_compact_corender": "DENIED",
    }
    if separation != expected_separation:
        raise C1ProjectionDenied("C1_PANEL_SEPARATION_CONTRACT_DENIED")
    _verify_logical_identity(payload, identity_key="projection_id", prefix="RO3-C1-CONSOLE-", label="C1_CONSOLE")

    return {
        "schema": ROUTE_SCHEMA,
        "route_id": ROUTE_ID,
        "route_state": ROUTE_STATE,
        "route_enabled": True,
        "availability": "AVAILABLE",
        "authority": "LOCAL_READ_ONLY_C1_PRESENTATION",
        "deployment": "LOCAL_ONLY_NO_REMOTE_DEPLOY",
        "source_projection_id": str(payload["projection_id"]),
        "source_logical_sha256": str(payload["logical_sha256"]),
        "source_context": context,
        "panels": {
            "fact": fact,
            "computability": computability,
            "assurance": assurance,
            "upstream_lineage": lineage,
            "downstream_trace": downstream,
        },
        "panel_separation": expected_separation,
        "schema_bindings": verified_bindings,
        "validation_consumption": "LOCKED_UNCONSUMED",
        "c2_authority": "UNCHANGED",
        "pattern_discovery_authority": "UNCHANGED",
        "read_only": True,
        "writes": "NONE",
    }


def _unavailable(reason: str, schema_bindings: list[dict[str, str]] | None = None) -> dict[str, Any]:
    return {
        "schema": ROUTE_SCHEMA,
        "route_id": ROUTE_ID,
        "route_state": ROUTE_STATE,
        "route_enabled": True,
        "availability": "NOT_EVALUATED",
        "reason": reason,
        "authority": "LOCAL_READ_ONLY_C1_PRESENTATION",
        "deployment": "LOCAL_ONLY_NO_REMOTE_DEPLOY",
        "panels": {},
        "panel_separation": {
            "fact_panel_id": "RO3-C1-FACT-INSPECTOR",
            "downstream_panel_id": "RO3-C1-DOWNSTREAM-TRACE",
            "mixed_compact_object": "DENIED",
            "null_reason_and_c2_transition_compact_corender": "DENIED",
        },
        "schema_bindings": schema_bindings or [],
        "validation_consumption": "LOCKED_UNCONSUMED",
        "c2_authority": "UNCHANGED",
        "pattern_discovery_authority": "UNCHANGED",
        "read_only": True,
        "writes": "NONE",
    }


def load_c1_projection(
    path: str | Path | None = None, *, schema_root: str | Path | None = None
) -> dict[str, Any]:
    """Load the locally materialised RO3-G4 projection through the approved RC-G4 route."""

    try:
        bindings = _verify_schema_bindings(schema_root)
    except (C1ProjectionDenied, C1ProjectionContractError) as exc:
        return _unavailable(str(exc))
    source = Path(
        path
        or os.environ.get(
            "OVC_RO3_C1_CONSOLE_PROJECTION",
            "var/research_operations/console/ro3_c1_console_projection.json",
        )
    )
    if not source.is_file():
        return _unavailable("C1_PROJECTION_UNAVAILABLE", bindings)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return _unavailable("C1_PROJECTION_INVALID_JSON", bindings)
    try:
        return validate_c1_projection_payload(payload, schema_root=schema_root)
    except (C1ProjectionDenied, C1ProjectionContractError) as exc:
        return _unavailable(str(exc), bindings)


def projection_identity(projection: Mapping[str, Any]) -> dict[str, Any]:
    context = projection.get("source_context") if isinstance(projection.get("source_context"), Mapping) else {}
    return {
        "route_id": projection.get("route_id", ROUTE_ID),
        "route_state": projection.get("route_state", ROUTE_STATE),
        "route_enabled": bool(projection.get("route_enabled", True)),
        "availability": projection.get("availability", "NOT_EVALUATED"),
        "source_projection_id": projection.get("source_projection_id", "NOT_EVALUATED"),
        "role": context.get("role", "NOT_EVALUATED"),
        "release_id": context.get("c1_release_id", "NOT_EVALUATED"),
        "manifest_sha256": context.get("c1_manifest_sha256", "NOT_EVALUATED"),
        "authority": projection.get("authority", "LOCAL_READ_ONLY_C1_PRESENTATION"),
        "writes": "NONE",
    }
