"""C2 vNext container candidate, definition, graph and role-projection foundation.

All construction is shadow-only.  A container is an immutable interval produced
from two compatible, first-valid boundary identities.  Local/parent and
measurement/structural are explicit roles, never hidden winning selections.
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

UTC = timezone.utc
CONTAINER_FAMILIES = ("TRAILING_RANGE_SNAPSHOT", "SWING_ENVELOPE")
CONTAINER_KINDS = ("MEASUREMENT", "STRUCTURAL")
CANDIDATE_STATUSES = (
    "COMPLETE_COMPATIBLE", "PARTIAL_ONE_BOUNDARY", "REJECTED_INCOMPATIBLE",
    "REJECTED_ZERO_WIDTH", "AMBIGUOUS_PAIRING", "CENSORED_PAIRING",
)
LIFECYCLE_EVENTS = (
    "DEFINED", "REFRESHED", "SUPERSEDED", "STALE_FOR_CONSUMER",
    "RETIRED_FOR_CONSUMER", "CENSORED", "INVALIDATED_SOURCE",
)
ROLE_TYPES = (
    "LOCAL_MEASUREMENT", "LOCAL_STRUCTURAL",
    "PARENT_MEASUREMENT", "PARENT_STRUCTURAL",
)
GRAPH_RELATIONS = ("CONTAINS", "WITHIN", "OVERLAPS", "DISJOINT", "EQUAL_BOUNDS")


class ContainerContractError(ValueError):
    pass


def _require(condition: bool, marker: str) -> None:
    if not condition:
        raise ContainerContractError(marker)


def parse_time(value: str | datetime) -> datetime:
    result = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    _require(result.tzinfo is not None, "TIMEZONE_REQUIRED")
    return result.astimezone(UTC)


def iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(prefix: str, value: Any, length: int = 24) -> str:
    return f"{prefix}.{hashlib.sha256(canonical_bytes(value)).hexdigest()[:length]}"


@dataclass(frozen=True)
class PairingPolicy:
    policy_id: str
    candidate_label: str
    required_depth: str | None = None
    maturity: str = "SHADOW_EXPERIMENT"
    active: bool = False
    canonical: bool = False

    def __post_init__(self) -> None:
        _require(bool(self.policy_id) and bool(self.candidate_label), "PAIRING_POLICY_IDENTITY")
        _require(self.required_depth in {None, "S0", "S1", "S2"}, "PAIRING_POLICY_DEPTH")
        _require(self.maturity == "SHADOW_EXPERIMENT", "PAIRING_POLICY_MATURITY")
        _require(not self.active, "PAIRING_POLICY_ACTIVATION_DENIED")
        _require(not self.canonical, "CANONICAL_PAIRING_POLICY_DENIED")


def shadow_pairing_policies() -> tuple[PairingPolicy, ...]:
    return (
        PairingPolicy("PAIRING.CANDIDATE.A.ADJACENT_OPPOSITE.r1", "ADJACENT_OPPOSITE_CONFIRMED"),
        PairingPolicy("PAIRING.CANDIDATE.B.CLOSED_LEG.r1", "CLOSED_LEG_ENDPOINTS"),
        PairingPolicy("PAIRING.CANDIDATE.C.DEPTH_LOCAL.r1", "DEPTH_LOCAL_OPPOSITE", required_depth="S1"),
    )


def _base_compatible(left: Mapping[str, Any], right: Mapping[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    for key in ("instrument", "side", "clock_id", "source_release_id"):
        if left.get(key) != right.get(key):
            reasons.append(f"MISMATCH:{key}")
    if left.get("structural_depth") != right.get("structural_depth"):
        reasons.append("MISMATCH:structural_depth")
    return not reasons, reasons


def evaluate_boundary_pair(
    lower: Mapping[str, Any] | None,
    upper: Mapping[str, Any] | None,
    *,
    family: str,
    kind: str,
    pairing_policy_id: str,
    evidence_time: str | None = None,
) -> dict[str, Any]:
    _require(family in CONTAINER_FAMILIES, "CONTAINER_FAMILY")
    _require(kind in CONTAINER_KINDS, "CONTAINER_KIND")
    identity = {
        "lower_id": lower.get("level_id") if lower else None,
        "upper_id": upper.get("level_id") if upper else None,
        "family": family,
        "kind": kind,
        "pairing_policy_id": pairing_policy_id,
    }
    body: dict[str, Any] = {
        "pairing_evidence_id": digest("C2.CONTAINER.PAIRING", identity),
        "family": family, "kind": kind, "pairing_policy_id": pairing_policy_id,
        "lower_boundary_id": lower.get("level_id") if lower else None,
        "upper_boundary_id": upper.get("level_id") if upper else None,
        "status": "PARTIAL_ONE_BOUNDARY", "reason_codes": [],
        "first_valid_time": None, "compatible": False,
        "maturity": "SHADOW_EXPERIMENT", "authority": "PAIRING_EVIDENCE_ONLY",
    }
    if lower is None or upper is None:
        body["reason_codes"] = ["TWO_BOUNDARIES_REQUIRED"]
        return body
    compatible, reasons = _base_compatible(lower, upper)
    lower_value = float(lower["value"])
    upper_value = float(upper["value"])
    if lower_value > upper_value:
        compatible = False
        reasons.append("BOUNDARY_ORDER_INVALID")
    if lower_value == upper_value:
        body["status"] = "REJECTED_ZERO_WIDTH"
        body["reason_codes"] = [*reasons, "ZERO_WIDTH"]
    elif not compatible:
        body["status"] = "REJECTED_INCOMPATIBLE"
        body["reason_codes"] = reasons
    else:
        body["status"] = "COMPLETE_COMPATIBLE"
        body["compatible"] = True
        body["reason_codes"] = ["EXPLICIT_PAIRING_AND_COMPATIBILITY_PASS"]
    first_valid = max(parse_time(str(lower["first_valid_time"])), parse_time(str(upper["first_valid_time"])))
    if evidence_time is not None:
        first_valid = max(first_valid, parse_time(evidence_time))
    body["first_valid_time"] = iso(first_valid)
    return body


def _build_definition(
    *,
    family: str,
    kind: str,
    lower: Mapping[str, Any],
    upper: Mapping[str, Any],
    pairing: Mapping[str, Any],
    structural_depth: str,
    source_ids: Sequence[str],
    horizon_id: str | None,
    origin: str,
) -> dict[str, Any]:
    _require(pairing.get("status") == "COMPLETE_COMPATIBLE", "PAIRING_NOT_COMPLETE_COMPATIBLE")
    _require(pairing.get("compatible") is True, "PAIRING_NOT_COMPATIBLE")
    _require(structural_depth in {"S0", "S1", "S2", "NA"}, "STRUCTURAL_DEPTH")
    lower_value = float(lower["value"])
    upper_value = float(upper["value"])
    _require(lower_value < upper_value, "CONTAINER_REQUIRES_POSITIVE_WIDTH")
    first_valid = str(pairing["first_valid_time"])
    identity = {
        "family": family, "kind": kind,
        "lower_boundary_id": lower["level_id"], "upper_boundary_id": upper["level_id"],
        "pairing_evidence_id": pairing["pairing_evidence_id"],
        "first_valid_time": first_valid, "horizon_id": horizon_id,
        "structural_depth": structural_depth, "origin": origin,
    }
    body = {
        "schema": "c2_container/vnext-r1",
        "container_id": digest("C2.CONTAINER", identity),
        "family": family, "kind": kind,
        "lower_boundary_id": lower["level_id"], "upper_boundary_id": upper["level_id"],
        "lower_value": lower_value, "upper_value": upper_value,
        "width": upper_value - lower_value,
        "centre": (upper_value + lower_value) / 2.0,
        "centre_is_boundary": False,
        "first_valid_time": first_valid,
        "instrument": lower["instrument"], "side": lower["side"],
        "clock_id": lower["clock_id"], "source_release_id": lower.get("source_release_id"),
        "horizon_id": horizon_id, "structural_depth": structural_depth,
        "pairing_evidence_id": pairing["pairing_evidence_id"],
        "pairing_policy_id": pairing["pairing_policy_id"],
        "source_ids": list(source_ids), "origin": origin,
        "immutable": True, "maturity": "SHADOW_EXPERIMENT",
        "authority": {"active_selector": "NONE", "pairing_activation": "NONE", "release": "NONE"},
    }
    body["content_sha256"] = hashlib.sha256(canonical_bytes(body)).hexdigest()
    return body


def build_trailing_range_container(levels: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_type = {str(level["level_type"]): level for level in levels}
    lower = by_type.get("TRAILING_RANGE_LOW")
    upper = by_type.get("TRAILING_RANGE_HIGH")
    pairing = evaluate_boundary_pair(
        lower, upper, family="TRAILING_RANGE_SNAPSHOT", kind="MEASUREMENT",
        pairing_policy_id="PAIRING.TRAILING_RANGE.EXACT_POPULATION.r1",
    )
    _require(pairing["status"] == "COMPLETE_COMPATIBLE", f"TRAILING_RANGE_PAIRING:{pairing['status']}")
    _require(lower is not None and upper is not None, "TRAILING_RANGE_BOUNDARIES_REQUIRED")
    _require(lower.get("horizon_id") == upper.get("horizon_id"), "TRAILING_RANGE_HORIZON_MISMATCH")
    _require(lower.get("source_ids") == upper.get("source_ids"), "TRAILING_RANGE_POPULATION_MISMATCH")
    return _build_definition(
        family="TRAILING_RANGE_SNAPSHOT", kind="MEASUREMENT", lower=lower, upper=upper,
        pairing=pairing, structural_depth="NA",
        source_ids=[str(lower["level_id"]), str(upper["level_id"]), *[str(item) for item in lower["source_ids"]]],
        horizon_id=str(lower["horizon_id"]), origin="ENDOGENOUS_TRAILING_MEASUREMENT",
    )


def build_swing_envelope(
    lower: Mapping[str, Any] | None,
    upper: Mapping[str, Any] | None,
    *,
    policy: PairingPolicy,
    evidence_time: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    pairing = evaluate_boundary_pair(
        lower, upper, family="SWING_ENVELOPE", kind="STRUCTURAL",
        pairing_policy_id=policy.policy_id, evidence_time=evidence_time,
    )
    if pairing["status"] != "COMPLETE_COMPATIBLE":
        return pairing, None
    _require(lower is not None and upper is not None, "SWING_BOUNDARIES_REQUIRED")
    _require(lower.get("family") == "CONFIRMED_PIVOT" and upper.get("family") == "CONFIRMED_PIVOT", "SWING_BOUNDARY_FAMILY")
    _require(lower.get("level_type") == "CONFIRMED_SWING_LOW", "SWING_LOWER_TYPE")
    _require(upper.get("level_type") == "CONFIRMED_SWING_HIGH", "SWING_UPPER_TYPE")
    _require(policy.required_depth in {None, lower.get("structural_depth")}, "PAIRING_POLICY_DEPTH_MISMATCH")
    definition = _build_definition(
        family="SWING_ENVELOPE", kind="STRUCTURAL", lower=lower, upper=upper,
        pairing=pairing, structural_depth=str(lower["structural_depth"]),
        source_ids=[str(lower["level_id"]), str(upper["level_id"])],
        horizon_id=None, origin="ENDOGENOUS_PAIRED_SWING_STRUCTURE",
    )
    return pairing, definition


def make_lifecycle_event(
    container: Mapping[str, Any], *, event_type: str, event_time: str,
    reason: str, consumer_id: str | None = None, superseding_container_id: str | None = None,
) -> dict[str, Any]:
    _require(event_type in LIFECYCLE_EVENTS, "CONTAINER_LIFECYCLE_EVENT")
    _require(parse_time(event_time) >= parse_time(str(container["first_valid_time"])), "CONTAINER_EVENT_BEFORE_FIRST_VALID")
    if event_type in {"STALE_FOR_CONSUMER", "RETIRED_FOR_CONSUMER"}:
        _require(bool(consumer_id), "CONTAINER_CONSUMER_REQUIRED")
    if event_type == "SUPERSEDED":
        _require(bool(superseding_container_id), "SUPERSEDING_CONTAINER_REQUIRED")
    body = {
        "container_id": container["container_id"], "event_type": event_type,
        "event_time": iso(parse_time(event_time)), "reason": reason,
        "consumer_id": consumer_id, "superseding_container_id": superseding_container_id,
        "definition_content_sha256": container["content_sha256"],
        "authority": "APPEND_ONLY_LIFECYCLE",
    }
    return {"lifecycle_event_id": digest("C2.CONTAINER.LIFECYCLE", body), **body}


def project_lifecycle(
    containers: Sequence[Mapping[str, Any]], events: Sequence[Mapping[str, Any]],
    *, as_of_time: str, consumer_id: str | None = None,
) -> list[dict[str, Any]]:
    as_of = parse_time(as_of_time)
    by_container: dict[str, list[Mapping[str, Any]]] = {}
    for event in events:
        if parse_time(str(event["event_time"])) <= as_of:
            by_container.setdefault(str(event["container_id"]), []).append(event)
    output: list[dict[str, Any]] = []
    for raw in containers:
        container = copy.deepcopy(dict(raw))
        if parse_time(str(container["first_valid_time"])) > as_of:
            continue
        state = "AVAILABLE"
        stale = False
        superseded_by = None
        for event in sorted(by_container.get(str(container["container_id"]), []), key=lambda item: (item["event_time"], item["lifecycle_event_id"])):
            if event["event_type"] == "INVALIDATED_SOURCE":
                state = "INVALIDATED_SOURCE"
            elif event["event_type"] == "CENSORED":
                state = "CENSORED"
            elif event["event_type"] == "SUPERSEDED":
                state = "SUPERSEDED"
                superseded_by = event.get("superseding_container_id")
            elif event["event_type"] == "RETIRED_FOR_CONSUMER" and event.get("consumer_id") == consumer_id:
                state = "RETIRED_FOR_CONSUMER"
            elif event["event_type"] == "STALE_FOR_CONSUMER" and event.get("consumer_id") == consumer_id:
                stale = True
        output.append({
            "container_id": container["container_id"], "definition": container,
            "state": state, "stale_for_consumer": stale,
            "superseded_by": superseded_by, "as_of_time": iso(as_of),
            "consumer_id": consumer_id,
        })
    output.sort(key=lambda item: (item["definition"]["first_valid_time"], item["container_id"]))
    return output


def classify_geometry(left: Mapping[str, Any], right: Mapping[str, Any]) -> str:
    ll, lu = float(left["lower_value"]), float(left["upper_value"])
    rl, ru = float(right["lower_value"]), float(right["upper_value"])
    if ll == rl and lu == ru:
        return "EQUAL_BOUNDS"
    if ll <= rl and lu >= ru:
        return "CONTAINS"
    if rl <= ll and ru >= lu:
        return "WITHIN"
    if max(ll, rl) < min(lu, ru):
        return "OVERLAPS"
    return "DISJOINT"


def build_container_graph(containers: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    nodes = [copy.deepcopy(dict(item)) for item in containers]
    nodes.sort(key=lambda item: (item["first_valid_time"], item["container_id"]))
    edges: list[dict[str, Any]] = []
    for index, left in enumerate(nodes):
        for right in nodes[index + 1:]:
            relation = classify_geometry(left, right)
            body = {
                "left_container_id": left["container_id"],
                "right_container_id": right["container_id"],
                "relation": relation,
                "left_bounds": [left["lower_value"], left["upper_value"]],
                "right_bounds": [right["lower_value"], right["upper_value"]],
                "basis": "RAW_INTERVAL_GEOMETRY",
            }
            edges.append({"container_edge_id": digest("C2.CONTAINER.GRAPH.EDGE", body), **body})
    graph_body = {"container_ids": [item["container_id"] for item in nodes], "edge_ids": [item["container_edge_id"] for item in edges]}
    return {
        "container_graph_id": digest("C2.CONTAINER.GRAPH", graph_body),
        "containers": nodes, "edges": edges,
        "complete_inventory": True, "width_derived_tree": False,
        "partial_overlap_preserved": True, "authority": "SHADOW_ONLY",
    }


def build_context_link(parent_container: Mapping[str, Any], *, local_scope_id: str, role: str, as_of_time: str) -> dict[str, Any]:
    _require(role in {"PARENT_MEASUREMENT", "PARENT_STRUCTURAL"}, "PARENT_CONTAINER_ROLE")
    _require(parse_time(str(parent_container["first_valid_time"])) <= parse_time(as_of_time), "PARENT_CONTAINER_NOT_FIRST_VALID")
    _require((role == "PARENT_MEASUREMENT" and parent_container["kind"] == "MEASUREMENT") or (role == "PARENT_STRUCTURAL" and parent_container["kind"] == "STRUCTURAL"), "PARENT_CONTAINER_ROLE_KIND_MISMATCH")
    body = {
        "parent_container_id": parent_container["container_id"],
        "local_scope_id": local_scope_id, "role": role,
        "as_of_time": iso(parse_time(as_of_time)),
        "parent_first_valid_time": parent_container["first_valid_time"],
        "parent_definition_hash": parent_container["content_sha256"],
        "parent_authority_preserved": True,
        "local_container_recreated": False,
        "authority": "CONTEXT_LINK_ONLY",
    }
    return {"context_link_id": digest("C2.CONTAINER.CONTEXT.LINK", body), **body}


def evaluate_role_projection(
    containers: Sequence[Mapping[str, Any]], *, projection_id: str,
    role: str, as_of_time: str, scope_kind: str,
    lifecycle_projection: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    _require(role in ROLE_TYPES, "CONTAINER_ROLE")
    _require(scope_kind in {"LOCAL", "PARENT"}, "CONTAINER_SCOPE_KIND")
    _require(role.startswith(scope_kind), "ROLE_SCOPE_MISMATCH")
    required_kind = "MEASUREMENT" if role.endswith("MEASUREMENT") else "STRUCTURAL"
    lifecycle_by_id = {item["container_id"]: item for item in (lifecycle_projection or [])}
    as_of = parse_time(as_of_time)
    candidate_ids: list[str] = []
    eligible: list[Mapping[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    for container in containers:
        cid = str(container["container_id"])
        candidate_ids.append(cid)
        reason = None
        if container.get("kind") != required_kind:
            reason = "KIND_NOT_ALLOWED_FOR_ROLE"
        elif parse_time(str(container["first_valid_time"])) > as_of:
            reason = "NOT_FIRST_VALID_AS_OF"
        else:
            lifecycle = lifecycle_by_id.get(cid)
            if lifecycle and lifecycle.get("state") != "AVAILABLE":
                reason = "LIFECYCLE_UNAVAILABLE"
            elif lifecycle and lifecycle.get("stale_for_consumer"):
                reason = "CONSUMER_STALE"
        if reason:
            exclusions.append({"container_id": cid, "reason": reason})
        else:
            eligible.append(container)
    selected_id = None
    tie_ids: list[str] = []
    if eligible:
        latest_time = max(parse_time(str(item["first_valid_time"])) for item in eligible)
        tie_ids = sorted(str(item["container_id"]) for item in eligible if parse_time(str(item["first_valid_time"])) == latest_time)
        reason = "SELECTED_UNIQUE" if len(tie_ids) == 1 else "TIED_CANDIDATES"
        selected_id = tie_ids[0] if len(tie_ids) == 1 else None
    else:
        reason = "NO_ELIGIBLE_CANDIDATE"
    body = {
        "projection_id": projection_id, "projection_version": "r1",
        "role": role, "scope_kind": scope_kind, "as_of_time": iso(as_of),
        "candidate_ids": sorted(candidate_ids),
        "eligible_ids": sorted(str(item["container_id"]) for item in eligible),
        "exclusions": sorted(exclusions, key=lambda item: (item["reason"], item["container_id"])),
        "tie_ids": tie_ids, "selected_container_id": selected_id,
        "reason": reason, "fallback_container_id": None,
        "active": False, "canonical": False,
        "authority": "SHADOW_PROJECTION_EVIDENCE_ONLY",
    }
    return {"projection_result_id": digest("C2.CONTAINER.ROLE.PROJECTION", body), **body}


def build_legacy_container_crosswalk(legacy_records: Sequence[Mapping[str, Any]], containers: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    family_map = {
        "LOCAL_RANGE": "TRAILING_RANGE_SNAPSHOT",
        "RANGE_CONTAINER": "TRAILING_RANGE_SNAPSHOT",
        "SWING_ENVELOPE": "SWING_ENVELOPE",
        "PARENT_RANGE": None,
    }
    output: list[dict[str, Any]] = []
    for legacy in legacy_records:
        mapped_family = family_map.get(str(legacy["legacy_type"]))
        matches = []
        if mapped_family is not None:
            matches = sorted(
                str(container["container_id"]) for container in containers
                if container["family"] == mapped_family
                and container["side"] == legacy["side"]
                and float(container["lower_value"]) == float(legacy["lower_value"])
                and float(container["upper_value"]) == float(legacy["upper_value"])
            )
        body = {
            "legacy_container_id": legacy["legacy_container_id"],
            "legacy_type": legacy["legacy_type"], "mapped_family": mapped_family,
            "matched_container_ids": matches,
            "match_status": "LINK_ONLY_REQUIRED" if legacy["legacy_type"] == "PARENT_RANGE" else "MATCHED_UNIQUE" if len(matches) == 1 else "MATCHED_MULTIPLE" if len(matches) > 1 else "UNMATCHED",
            "legacy_mutated": False, "historical_name_preserved": True,
            "authority": "AUDIT_ONLY",
        }
        output.append({"crosswalk_id": digest("C2.CONTAINER.LEGACY.XWALK", body), **body})
    output.sort(key=lambda item: str(item["legacy_container_id"]))
    return output


def assert_relation_cannot_mutate_container(before: Mapping[str, Any], after: Mapping[str, Any]) -> None:
    _require(canonical_bytes(before) == canonical_bytes(after), "RELATION_MUTATED_CONTAINER_DEFINITION")
