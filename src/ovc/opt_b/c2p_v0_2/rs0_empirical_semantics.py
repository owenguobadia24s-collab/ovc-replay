from __future__ import annotations

from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from typing import Any, Mapping

SEMANTICS_SCHEMA = "ovc-c2p2-rs0-empirical-semantics/v1"
ROW_SCHEMA = "ovc-c2p2-rs0-source-row/v1"
CANDIDATE_SCHEMA = "ovc-c2p2-rs0-empirical-candidate-material/v1"
ALLOWED_BASE_SOURCE_KINDS = frozenset({"C2_LEVEL", "C2_CONTAINER"})
FORBIDDEN_IDENTITY_FIELDS = frozenset({
    "family", "family_label", "c3_semantics", "opt_c", "opt_d", "outcome",
    "future_information", "validation", "probability", "risk", "exposure",
    "trade_signal", "execution",
})


class RS0SemanticError(ValueError):
    pass


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _decimal(value: Any, field: str) -> Decimal:
    if value is None or isinstance(value, bool):
        raise RS0SemanticError(f"RS0_NUMERIC_RESIDUAL_INPUT_INVALID:{field}")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise RS0SemanticError(f"RS0_NUMERIC_RESIDUAL_INPUT_INVALID:{field}") from exc


def _decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    text = format(value.normalize(), "f")
    return text if "." in text else text + ".0"


def _require_no_forbidden_fields(value: Mapping[str, Any]) -> None:
    forbidden = sorted(FORBIDDEN_IDENTITY_FIELDS.intersection(value))
    if forbidden:
        raise RS0SemanticError("RS0_FORBIDDEN_IDENTITY_FIELD:" + ",".join(forbidden))


def normalize_candidate_source_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize one exact C2 source row into empirical Candidate material.

    C2E rows and parent-observation rows are evidence/context only and can never
    become base C2P candidates through this route.
    """
    record = dict(row)
    _require_no_forbidden_fields(record)
    if record.get("schema") != ROW_SCHEMA or record.get("source_role") != "C2_VNEXT":
        raise RS0SemanticError("RS0_BASE_CANDIDATE_REQUIRES_C2_VNEXT")
    source_kind = str(record.get("source_record_kind", ""))
    if source_kind not in ALLOWED_BASE_SOURCE_KINDS:
        raise RS0SemanticError(f"RS0_BASE_CANDIDATE_SOURCE_FORBIDDEN:{source_kind}")
    if record.get("instrument") != "GBPUSD" or record.get("side") not in {"BID", "ASK"}:
        raise RS0SemanticError("RS0_BASE_CANDIDATE_SCOPE_INVALID")
    if record.get("clock") != "15M":
        raise RS0SemanticError("RS0_BASE_CANDIDATE_CLOCK_INVALID")
    fvt = str(record.get("first_valid_time", ""))
    cutoff = str(record.get("evaluation_cutoff", ""))
    if not fvt or not cutoff or fvt > cutoff:
        raise RS0SemanticError("RS0_BASE_CANDIDATE_CAUSALITY_INVALID")
    geometry = record.get("geometry_signature")
    if not isinstance(geometry, Mapping):
        raise RS0SemanticError("RS0_GEOMETRY_SIGNATURE_REQUIRED")
    _require_no_forbidden_fields(geometry)
    relation_topology = record.get("relation_topology")
    if not isinstance(relation_topology, list):
        raise RS0SemanticError("RS0_RELATION_TOPOLOGY_LIST_REQUIRED")
    topology = sorted(set(str(item) for item in relation_topology))

    if source_kind == "C2_LEVEL":
        required = ("horizon_id", "level_type", "value", "origin", "structural_depth")
        if any(field not in geometry for field in required):
            raise RS0SemanticError("RS0_LEVEL_OWNER_FIELDS_INCOMPLETE")
        structural_role_id = "LEVEL"
        geometry_kind_id = "POINT_REFERENCE"
        owner_geometry_class = {
            "horizon_id": geometry["horizon_id"],
            "level_type": geometry["level_type"],
            "origin": geometry["origin"],
            "structural_depth": geometry["structural_depth"],
        }
        numeric_state = {"value": geometry["value"]}
    else:
        required = (
            "horizon_id", "kind", "lower_value", "upper_value",
            "centre", "width", "origin", "structural_depth",
        )
        if any(field not in geometry for field in required):
            raise RS0SemanticError("RS0_CONTAINER_OWNER_FIELDS_INCOMPLETE")
        structural_role_id = "RANGE"
        geometry_kind_id = "INTERVAL"
        owner_geometry_class = {
            "horizon_id": geometry["horizon_id"],
            "kind": geometry["kind"],
            "origin": geometry["origin"],
            "structural_depth": geometry["structural_depth"],
        }
        numeric_state = {
            field: geometry[field]
            for field in ("lower_value", "upper_value", "centre", "width")
        }

    hard_scope = {
        "instrument": record["instrument"],
        "side": record["side"],
        "clock": record["clock"],
        "structural_role_id": structural_role_id,
        "geometry_kind_id": geometry_kind_id,
    }
    payload = {
        "schema": CANDIDATE_SCHEMA,
        "source_record_id": str(record.get("source_record_id", "")),
        "source_record_kind": source_kind,
        "first_valid_time": fvt,
        "evaluation_cutoff": cutoff,
        "hard_scope": hard_scope,
        "structural_role_id": structural_role_id,
        "geometry_kind_id": geometry_kind_id,
        "geometry_signature": dict(geometry),
        "owner_geometry_class": owner_geometry_class,
        "numeric_geometry_state": numeric_state,
        "relation_topology": topology,
    }
    if not payload["source_record_id"]:
        raise RS0SemanticError("RS0_SOURCE_RECORD_ID_REQUIRED")
    payload["candidate_material_hash"] = _canonical_hash(payload)
    return payload


def geometry_residuals(previous: Mapping[str, Any], current: Mapping[str, Any]) -> dict[str, str]:
    if previous.get("source_record_kind") != current.get("source_record_kind"):
        raise RS0SemanticError("RS0_RESIDUAL_SOURCE_KIND_MISMATCH")
    old = previous.get("numeric_geometry_state")
    new = current.get("numeric_geometry_state")
    if not isinstance(old, Mapping) or not isinstance(new, Mapping) or set(old) != set(new):
        raise RS0SemanticError("RS0_RESIDUAL_FIELD_SET_MISMATCH")
    return {
        field: _decimal_text(_decimal(new[field], field) - _decimal(old[field], field))
        for field in sorted(old)
    }


def owner_declared_geometry_compatible(
    previous: Mapping[str, Any], current: Mapping[str, Any]
) -> tuple[bool, dict[str, str]]:
    """Exact class equality; numeric movement is evidence only, never a threshold."""
    compatible = (
        previous.get("source_record_kind") == current.get("source_record_kind")
        and previous.get("hard_scope") == current.get("hard_scope")
        and previous.get("owner_geometry_class") == current.get("owner_geometry_class")
    )
    residuals = geometry_residuals(previous, current) if compatible else {}
    return compatible, residuals


def c2e_dependency_disposition(
    structural_role_id: str,
    dependency_registry: Mapping[str, Any],
    *,
    exact_dependency_evidence: Mapping[str, Any] | None = None,
) -> str:
    """Current registry intentionally declares no episode-relative base role.

    Any future declaration fails closed unless the registry itself supplies an
    exact supported execution mode; no episode similarity or membership may be
    inferred here.
    """
    entries = dependency_registry.get("entries")
    if not isinstance(entries, list):
        raise RS0SemanticError("RS0_C2E_DEPENDENCY_REGISTRY_INVALID")
    matched = [row for row in entries if row.get("structural_role_id") == structural_role_id]
    if not matched:
        return "NOT_APPLICABLE_C2_ONLY"
    if len(matched) != 1:
        raise RS0SemanticError("RS0_C2E_DEPENDENCY_ROLE_AMBIGUOUS")
    row = matched[0]
    if row.get("execution_mode") != "EXACT_BOUND":
        raise RS0SemanticError("RS0_C2E_DEPENDENCY_ROLE_UNBOUND")
    if exact_dependency_evidence is None:
        return "NOT_EVALUABLE_REQUIRED_C2E_EVIDENCE_MISSING"
    expected_pack = row.get("boundary_pack_sha256")
    if expected_pack and exact_dependency_evidence.get("boundary_pack_sha256") != expected_pack:
        return "INCOMPATIBLE_C2E_BOUNDARY_PACK"
    previous_episode_ids = exact_dependency_evidence.get("previous_episode_ids")
    current_episode_ids = exact_dependency_evidence.get("current_episode_ids")
    if not isinstance(previous_episode_ids, list) or not isinstance(current_episode_ids, list):
        return "NOT_EVALUABLE_REQUIRED_C2E_LINEAGE_MISSING"
    return (
        "COMPATIBLE_EXACT_DECLARED_LINEAGE"
        if set(previous_episode_ids).intersection(current_episode_ids)
        else "INCOMPATIBLE_EXACT_DECLARED_LINEAGE"
    )


def evaluate_pair(
    candidate_id: str,
    previous: Mapping[str, Any],
    current: Mapping[str, Any],
    dependency_registry: Mapping[str, Any],
    *,
    prior_terminal_break: bool = False,
    explicit_discontinuity: bool = False,
    exact_dependency_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate identity-mechanical pair predicates for one frozen research candidate."""
    if candidate_id not in {
        "C2P2-PS0-OP-A-STRICT-CONTINUITY-v2",
        "C2P2-PS0-OP-B-RELATIONAL-CONTINUITY-v2",
        "C2P2-PS0-OP-C-EPISODE-ENRICHED-CONTINUITY-v2",
    }:
        raise RS0SemanticError("RS0_EMPIRICAL_CANDIDATE_ID_UNKNOWN")
    same_hard_scope = previous.get("hard_scope") == current.get("hard_scope")
    chronology_contiguous = (
        not explicit_discontinuity
        and str(previous.get("first_valid_time", "")) <= str(previous.get("evaluation_cutoff", ""))
        and str(current.get("first_valid_time", "")) <= str(current.get("evaluation_cutoff", ""))
        and str(previous.get("first_valid_time", "")) <= str(current.get("first_valid_time", ""))
    )
    no_terminal_break = not prior_terminal_break
    exact_geometry = previous.get("geometry_signature") == current.get("geometry_signature")
    owner_compatible, residuals = owner_declared_geometry_compatible(previous, current)
    topology_equal = previous.get("relation_topology") == current.get("relation_topology")
    c2e_disposition = c2e_dependency_disposition(
        str(current.get("structural_role_id", "")),
        dependency_registry,
        exact_dependency_evidence=exact_dependency_evidence,
    )

    if candidate_id.endswith("STRICT-CONTINUITY-v2"):
        pack_predicates = {
            "same_geometry_signature": exact_geometry,
        }
    elif candidate_id.endswith("RELATIONAL-CONTINUITY-v2"):
        pack_predicates = {
            "same_relation_topology": topology_equal,
            "owner_declared_geometry_compatible": owner_compatible,
        }
    else:
        pack_predicates = {
            "owner_declared_geometry_compatible": owner_compatible,
            "c2e_lineage_compatible_if_declared": c2e_disposition
            in {"NOT_APPLICABLE_C2_ONLY", "COMPATIBLE_EXACT_DECLARED_LINEAGE"},
        }

    predicate_results = {
        "same_hard_scope": same_hard_scope,
        **pack_predicates,
        "no_terminal_break": no_terminal_break,
        "chronology_contiguous": chronology_contiguous,
    }
    return {
        "schema": "ovc-c2p2-rs0-empirical-pair-evaluation/v1",
        "candidate_id": candidate_id,
        "predicate_results": predicate_results,
        "geometry_residuals": residuals,
        "numeric_residual_policy": "EVIDENCE_ONLY_NO_PASS_THRESHOLD",
        "c2e_dependency_disposition": c2e_disposition,
        "same_object_pair_supported": all(predicate_results.values()),
    }
