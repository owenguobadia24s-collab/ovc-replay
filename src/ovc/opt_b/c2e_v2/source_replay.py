"""Exact bounded real-source replay orchestration for C2E2-WP6.

The module consumes only the operator-approved C2 vNext observation
materialisation.  It projects stable comparison content from already-lawful C2
facts, builds the v0.3 C2E handoff, evaluates the frozen June candidate pack,
and emits an inactive append-only C2E stream.  It has no provider intake,
sampling, Validation, outcome, family, semantic, probability, risk, exposure or
execution path.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .candidate import build_candidate
from .empirical_boundary_rules import evaluate_boundary_predicates as evaluate_legacy_predicates
from .empirical_boundary_rules_v2 import evaluate_boundary_predicates as evaluate_boundary_predicates_v2
from .handoff_v0_3 import build_input_frame_v0_3
from .lifecycle import EpisodeEngine
from .models import build_record
from .resolver import resolve_candidates
from .serialization import canonical_bytes, sha256_hex
from .stable_signatures import build_comparison_signatures

PROGRAMME_ID = "OVC-C2E-CAUSAL-EPISODE-CONFORMANCE-v0.2"
PACKET_ID = "C2E2-WP6"
TARGET_END = "2026-07-01T00:00:00Z"
C2AR_PACKAGE_ID = "C2AR.INTEGRATED.SHADOW.PACKAGE.v1"
C2AR_PACKAGE_SHA256 = "150de1997be8801baa59db6d0fe98b11cb21a6b70525b908537aeb31bfd00cc3"
C2AR_PERMISSION = "READ_ONLY_SHADOW_RESEARCH_ONLY"
RULE_IDS = (
    "C2E.RULE.JUNE.BASELINE.CENSOR_GAP.v1",
    "C2E.RULE.JUNE.BASELINE.CENSOR_RELEASE_END.v1",
    "C2E.RULE.JUNE.BASELINE.RE_PARENT.v1",
    "C2E.RULE.JUNE.BASELINE.PHASE_MUTATION.v1",
    "C2E.RULE.JUNE.BASELINE.CONTINUATION.v1",
    "C2E.RULE.JUNE.BASELINE.BIRTH.v1",
)
PROHIBITED_DEPENDENCIES = ("FDI_C2G", "OUTCOME", "VALIDATION", "C2_5", "C3")


class SourceReplayError(RuntimeError):
    pass


def _require(condition: bool, marker: str) -> None:
    if not condition:
        raise SourceReplayError(marker)


def _loads(text: str) -> Any:
    return json.loads(text, parse_float=str, parse_int=int)


def load_json(path: Path) -> dict[str, Any]:
    return dict(_loads(path.read_text(encoding="utf-8")))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [dict(_loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _plain_decimal(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, str):
        try:
            decimal = Decimal(value)
        except (InvalidOperation, ValueError):
            return value
        _require(decimal.is_finite(), "NONFINITE_SOURCE_DECIMAL")
        return format(decimal, "f")
    if isinstance(value, float):
        raise SourceReplayError("RUNTIME_FLOAT_SOURCE_DENIED")
    if isinstance(value, list):
        return [_plain_decimal(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _plain_decimal(item) for key, item in value.items()}
    return value


def _content_id(prefix: str, value: Any) -> str:
    return f"{prefix}.{sha256_hex(value)[:24]}"


def _level_role(level: Mapping[str, Any]) -> dict[str, Any]:
    return _plain_decimal({
        "role_kind": "LEVEL",
        "horizon_id": level.get("horizon_id"),
        "level_type": level.get("level_type"),
        "origin": level.get("origin"),
        "structural_depth": level.get("structural_depth"),
        "value": level.get("value"),
    })


def _container_role(container: Mapping[str, Any]) -> dict[str, Any]:
    return _plain_decimal({
        "role_kind": "CONTAINER",
        "horizon_id": container.get("horizon_id"),
        "kind": container.get("kind"),
        "origin": container.get("origin"),
        "structural_depth": container.get("structural_depth"),
        "pairing_policy_id": container.get("pairing_policy_id"),
        "lower_value": container.get("lower_value"),
        "upper_value": container.get("upper_value"),
        "centre": container.get("centre"),
        "width": container.get("width"),
    })


def _object_role(
    object_id: str,
    levels: Mapping[str, Mapping[str, Any]],
    containers: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if object_id in levels:
        return _level_role(levels[object_id])
    if object_id in containers:
        return _container_role(containers[object_id])
    raise SourceReplayError(f"STABLE_OBJECT_ROLE_NOT_FOUND:{object_id}")


def _relation(
    raw: Mapping[str, Any],
    levels: Mapping[str, Mapping[str, Any]],
    containers: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    allowed = {
        "object_id", "object_kind", "topology", "mode", "source_precision",
        "equal_at_source_precision", "absolute_distance", "signed_distance",
        "signed_distance_to_lower", "signed_distance_to_upper", "relation_id",
        "subject_probe_id", "first_valid_time",
    }
    unknown = sorted(set(raw) - allowed)
    _require(not unknown, f"UNKNOWN_RELATION_FIELD:{','.join(unknown)}")
    result: dict[str, Any] = {
        "object_kind": str(raw.get("object_kind")),
        "object_role": _object_role(str(raw["object_id"]), levels, containers),
        "topology": str(raw.get("topology")),
        "mode": str(raw.get("mode")),
        "source_precision": int(raw.get("source_precision", 0)),
    }
    for key in (
        "equal_at_source_precision", "absolute_distance", "signed_distance",
        "signed_distance_to_lower", "signed_distance_to_upper",
    ):
        if key in raw:
            result[key] = _plain_decimal(raw[key])
    return result


def _component(
    axis: str,
    profiles: list[Mapping[str, Any]],
    *,
    levels: Mapping[str, Mapping[str, Any]],
    containers: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    _require(bool(profiles), f"PROFILE_AXIS_EMPTY:{axis}")
    for profile in profiles:
        _require(profile.get("axis") == axis, f"PROFILE_AXIS_MISMATCH:{axis}")
        _require(profile.get("semantic_label") is None, "SEMANTIC_PROFILE_INPUT_DENIED")
        _require(profile.get("selected_object_id") is None, "SELECTED_OBJECT_PROFILE_INPUT_DENIED")
        _require(profile.get("fallback_object_id") is None, "FALLBACK_OBJECT_PROFILE_INPUT_DENIED")
        _require(not profile.get("numeric_thresholds"), "NUMERIC_THRESHOLD_PROFILE_INPUT_DENIED")
    reasons = sorted({str(reason) for profile in profiles for reason in profile.get("reason_codes", [])})
    status = "COMPUTABLE" if all(profile.get("computability") == "COMPUTABLE" for profile in profiles) else "NOT_COMPUTABLE"

    source_object_ids: list[str] = []
    if axis == "LOCATION":
        _require(len(profiles) == 1, "LOCATION_PROFILE_CARDINALITY")
        facts = profiles[0].get("facts", {})
        relations = [_relation(row, levels, containers) for row in facts.get("relations", [])]
        relations.sort(key=canonical_bytes)
        stable_facts = {
            "complete_scoped_inventory": bool(facts.get("complete_scoped_inventory", False)),
            "exclusions": sorted(str(item) for item in facts.get("exclusions", [])),
            "relations": relations,
        }
        source_object_ids = sorted({_content_id("C2.STABLE.OBJECT", row["object_role"]) for row in relations})
    elif axis == "MOTION":
        rows = []
        for profile in profiles:
            facts = profile.get("facts", {})
            _require(not facts.get("relation_deltas", []), "MOTION_RELATION_DELTAS_UNSUPPORTED_IN_FROZEN_SOURCE")
            row = {
                "horizon_id": str(facts.get("horizon_id")),
                "membership_status": str(facts.get("membership_status")),
                "price_delta": _plain_decimal(facts.get("price_delta")),
                "computability": str(profile.get("computability")),
                "reason_codes": sorted(str(item) for item in profile.get("reason_codes", [])),
            }
            rows.append(row)
            source_object_ids.append(row["horizon_id"])
        rows.sort(key=lambda row: row["horizon_id"])
        stable_facts = {"horizons": rows}
        source_object_ids = sorted(set(source_object_ids))
    elif axis == "ORGANISATION":
        _require(len(profiles) == 1, "ORGANISATION_PROFILE_CARDINALITY")
        facts = profiles[0].get("facts", {})
        _require(facts.get("swing_graph") is None, "SWING_GRAPH_NOT_IN_APPROVED_REAL_MATERIALISATION")
        role_by_id: dict[str, dict[str, Any]] = {}
        stable_containers = []
        for row in facts.get("containers", []):
            container_id = str(row.get("container_id"))
            _require(container_id in containers, f"ORGANISATION_CONTAINER_MISSING:{container_id}")
            role = _container_role(containers[container_id])
            role_by_id[container_id] = role
            stable_containers.append(role)
        stable_containers.sort(key=canonical_bytes)
        edges = []
        for edge in facts.get("container_edges", []):
            left = str(edge.get("left_container_id")); right = str(edge.get("right_container_id"))
            _require(left in role_by_id and right in role_by_id, "ORGANISATION_EDGE_CONTAINER_MISSING")
            edges.append({"basis": str(edge.get("basis")), "relation": str(edge.get("relation")), "left": role_by_id[left], "right": role_by_id[right]})
        edges.sort(key=canonical_bytes)
        stable_facts = {"complete_inventory": bool(facts.get("complete_inventory", False)), "containers": stable_containers, "container_edges": edges, "swing_graph": None}
        source_object_ids = sorted({_content_id("C2.STABLE.CONTAINER", role) for role in stable_containers})
    elif axis == "INTERACTION":
        _require(len(profiles) == 1, "INTERACTION_PROFILE_CARDINALITY")
        facts = profiles[0].get("facts", {})
        _require(not facts.get("crossings", []), "INTERACTION_CROSSING_SURFACE_OUTSIDE_FROZEN_MATERIALISATION")
        _require(not facts.get("relation_deltas", []), "INTERACTION_RELATION_DELTAS_OUTSIDE_FROZEN_MATERIALISATION")
        changes = []
        for row in facts.get("reference_changes", []):
            changes.append({
                "previous": _object_role(str(row.get("previous_object_id")), levels, containers),
                "current": _object_role(str(row.get("current_object_id")), levels, containers),
                "is_crossing": bool(row.get("is_crossing", False)),
                "reason": str(row.get("reason")),
            })
        changes.sort(key=canonical_bytes)
        stable_facts = {"crossings": [], "relation_deltas": [], "reference_changes": changes}
        source_object_ids = sorted({_content_id("C2.STABLE.REFERENCE.CHANGE", row) for row in changes})
    else:
        raise SourceReplayError(f"UNKNOWN_AXIS:{axis}")
    return {"axis": axis, "status": status, "reason_codes": reasons, "source_object_ids": source_object_ids, "facts": stable_facts}


def comparison_source(
    bundle: Mapping[str, Any],
    profiles: Mapping[str, Mapping[str, Any]],
    contexts: Mapping[str, Mapping[str, Any]],
    levels: Mapping[str, Mapping[str, Any]],
    containers: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    structural = {
        axis: _component(axis, [profiles[profile_id] for profile_id in bundle["profile_output_ids"][axis]], levels=levels, containers=containers)
        for axis in ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION")
    }
    fixed = contexts[str(bundle["context_bundle_id"])].get("fixed_parent_observation_link", {})
    parent_id = fixed.get("parent_observation_id")
    parent_status = "AVAILABLE" if fixed.get("computability") == "COMPUTABLE" and parent_id else "NOT_COMPUTABLE"
    parent = {
        "selected_parent_observation_ids": [str(parent_id)] if parent_id else [],
        "selected_parent_object_ids": [],
        "dependency_states": [{
            "dependency_id": "DEP.PARENT_CONTEXT",
            "role": "REQUIRED",
            "status": parent_status,
            "reason_codes": sorted(str(item) for item in fixed.get("reason_codes", [])),
        }],
    }
    return {"structural": structural, "parent": parent}


def _parent(record_id: str, kind: str, first_valid_time: str, content_sha256: str | None = None) -> dict[str, Any]:
    result = {"record_id": str(record_id), "kind": str(kind), "first_valid_time": str(first_valid_time)}
    if content_sha256:
        result["content_sha256"] = str(content_sha256)
    return result


def _dependencies(bundle: Mapping[str, Any], profiles: Mapping[str, Mapping[str, Any]], context: Mapping[str, Any]) -> list[dict[str, Any]]:
    fixed = context.get("fixed_parent_observation_link", {})
    parent_status = "AVAILABLE" if fixed.get("computability") == "COMPUTABLE" and fixed.get("parent_observation_id") else "NOT_COMPUTABLE"
    all_computable = all(profiles[profile_id].get("computability") == "COMPUTABLE" for ids in bundle["profile_output_ids"].values() for profile_id in ids)
    rows = [
        {"dependency_id": "DEP.CONTINUITY", "role": "REQUIRED", "status": "AVAILABLE", "source_record_ids": [str(bundle["observation_id"])], "reason_codes": []},
        {"dependency_id": "DEP.SOURCE_RELEASE", "role": "REQUIRED", "status": "AVAILABLE", "source_record_ids": [], "reason_codes": []},
        {"dependency_id": "DEP.STRUCTURAL", "role": "REQUIRED", "status": "AVAILABLE", "source_record_ids": sorted(profile_id for ids in bundle["profile_output_ids"].values() for profile_id in ids), "reason_codes": [] if all_computable else ["TECHNICAL_PARTIAL_COMPUTABILITY"]},
        {"dependency_id": "DEP.PARENT_CONTEXT", "role": "OPTIONAL", "status": parent_status, "source_record_ids": [str(bundle["context_bundle_id"])], "reason_codes": sorted(str(item) for item in fixed.get("reason_codes", []))},
    ]
    rows.extend({"dependency_id": dep, "role": "PROHIBITED", "status": "UNAVAILABLE", "source_record_ids": [], "reason_codes": ["PROHIBITED_SOURCE_ABSENT"]} for dep in PROHIBITED_DEPENDENCIES)
    return sorted(rows, key=lambda row: row["dependency_id"])


def build_frame(
    bundle: Mapping[str, Any], *, predecessor_observation_id: str | None,
    observations: Mapping[str, Mapping[str, Any]], parent_observations: Mapping[str, Mapping[str, Any]],
    profiles: Mapping[str, Mapping[str, Any]], memberships: Mapping[str, Mapping[str, Any]],
    contexts: Mapping[str, Mapping[str, Any]], levels: Mapping[str, Mapping[str, Any]],
    containers: Mapping[str, Mapping[str, Any]], relation_sets: Mapping[str, Mapping[str, Any]],
    materialisation_manifest: Mapping[str, Any], source_build_commit: str,
) -> dict[str, Any]:
    observation = observations[str(bundle["observation_id"])]
    context = contexts[str(bundle["context_bundle_id"])]
    parent_records: list[dict[str, Any]] = []
    for axis in ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION"):
        for profile_id in bundle["profile_output_ids"][axis]:
            profile = profiles[profile_id]
            parent_records.append(_parent(profile_id, axis, profile["as_of_time"], profile.get("content_sha256")))
    for level_id in bundle.get("level_ids", []):
        row = levels[level_id]; parent_records.append(_parent(level_id, "LEVEL", row["first_valid_time"], row.get("content_sha256")))
    for container_id in bundle.get("container_ids", []):
        row = containers[container_id]; parent_records.append(_parent(container_id, "CONTAINER", row["first_valid_time"], row.get("content_sha256")))
    for membership_id in bundle.get("horizon_membership_ids", []):
        row = memberships[membership_id]
        parent_records.append(_parent(membership_id, "HORIZON_MEMBERSHIP", row.get("available_at") or row.get("as_of_first_valid_time")))
    for relation_set_id in bundle.get("relation_set_ids", []):
        parent_records.append(_parent(relation_set_id, "RELATION_SET", relation_sets[relation_set_id]["as_of_time"]))
    parent_records.append(_parent(bundle["context_bundle_id"], "CONTEXT", context["local_first_valid_time"], context.get("content_sha256")))

    fixed = context.get("fixed_parent_observation_link", {}); fixed_links: list[str] = []
    if fixed.get("link_id"):
        fixed_links.append(str(fixed["link_id"])); parent_records.append(_parent(fixed["link_id"], "FIXED_PARENT_LINK", fixed["local_first_valid_time"], fixed.get("content_sha256")))
    axis_link = context.get("parent_axis_context_link", {}); axis_links: list[str] = []
    if axis_link.get("link_id"):
        axis_links.append(str(axis_link["link_id"])); parent_records.append(_parent(axis_link["link_id"], "PARENT_AXIS_LINK", axis_link["local_first_valid_time"], axis_link.get("content_sha256")))
    structural_links: list[str] = []
    for link in context.get("parent_structural_links_by_depth", []):
        if link.get("link_id"):
            structural_links.append(str(link["link_id"])); parent_records.append(_parent(link["link_id"], "STRUCTURAL_PARENT_LINK", link.get("local_first_valid_time") or context["local_first_valid_time"], link.get("content_sha256")))
    parent_observation_id = fixed.get("parent_observation_id")
    if parent_observation_id:
        row = parent_observations[str(parent_observation_id)]
        parent_records.append(_parent(str(parent_observation_id), "FIXED_PARENT_OBSERVATION", row["first_valid_time"], row.get("content_sha256")))
    by_id: dict[str, dict[str, Any]] = {}
    for row in parent_records:
        if row["record_id"] in by_id:
            _require(by_id[row["record_id"]] == row, f"PARENT_RECORD_CONFLICT:{row['record_id']}")
        by_id[row["record_id"]] = row
    parent_records = [by_id[record_id] for record_id in sorted(by_id)]

    payload = {
        "source_binding": {
            "c2ar_package_id": C2AR_PACKAGE_ID, "c2ar_package_sha256": C2AR_PACKAGE_SHA256,
            "research_consumer_permission": C2AR_PERMISSION, "active": False, "canonical": False,
            "source_release_id": materialisation_manifest["materialisation_id"],
            "source_manifest_id": f"C2VNEXT.MATERIALISATION.MANIFEST.{materialisation_manifest['logical_sha256']}",
            "c2_release_id": materialisation_manifest["materialisation_id"],
            "c2_contract_id": "C2VNEXT.REAL.OBSERVATION.MATERIALISATION.v1",
            "source_build_commit": source_build_commit,
        },
        "identity": {
            "instrument_id": "GBPUSD", "side": str(bundle["side"]), "scope_id": "LOCAL_15M", "scale_id": "15M",
            "clock_id": "UTC_15M", "lattice_id": "LATTICE.15M.UTC_0000.v1",
            "observation_id": str(bundle["observation_id"]), "c2_record_id": str(bundle["observation_id"]),
            "parameter_pack_id": C2AR_PACKAGE_ID, "contract_id": "C2E.HANDOFF.SIGNATURE.v0_3", "schema_id": "c2e_input_frame/v0_3",
        },
        "chronology": {
            "source_time": str(observation["interval_start"]), "candidate_onset_time": str(observation["interval_start"]),
            "first_valid_time": str(observation["first_valid_time"]), "evaluation_cutoff": str(observation["first_valid_time"]),
            "continuity_segment_id": str(observation["continuity"]["segment_id"]), "predecessor_observation_id": predecessor_observation_id,
        },
        "structural": {
            "location_record_ids": sorted(str(item) for item in bundle["profile_output_ids"]["LOCATION"]),
            "motion_record_ids": sorted(str(item) for item in bundle["profile_output_ids"]["MOTION"]),
            "organisation_record_ids": sorted(str(item) for item in bundle["profile_output_ids"]["ORGANISATION"]),
            "interaction_record_ids": sorted(str(item) for item in bundle["profile_output_ids"]["INTERACTION"]),
            "level_record_ids": sorted(str(item) for item in bundle.get("level_ids", [])),
            "container_record_ids": sorted(str(item) for item in bundle.get("container_ids", [])),
            "relation_set_id": None, "transition_record_ids": [], "run_record_ids": [],
        },
        "context": {"context_resolution_bundle_id": str(bundle["context_bundle_id"]), "fixed_parent_links": sorted(fixed_links), "structural_object_links": sorted(structural_links), "parent_axis_links": sorted(axis_links)},
        "evidence": {
            "dependency_results": _dependencies(bundle, profiles, context), "availability_status": "AVAILABLE",
            "technical_status": "COMPUTABLE" if all(profiles[profile_id].get("computability") == "COMPUTABLE" for ids in bundle["profile_output_ids"].values() for profile_id in ids) else "PARTIALLY_COMPUTABLE",
            "assurance": [{"assertion_id": "C2VNEXT_RM1_EXACT_SOURCE", "status": "ASSURED"}],
            "consumer_eligibility": "INELIGIBLE_INACTIVE_SHADOW", "authority_state": "UNAUTHORIZED_ACTIVE_C2E", "reason_codes": [],
        },
        "lineage": {
            "parent_record_ids": [row["record_id"] for row in parent_records],
            "artifact_hashes": {"c2ar_package": C2AR_PACKAGE_SHA256, "materialisation_manifest": str(materialisation_manifest["logical_sha256"]), "target_bundles": str(materialisation_manifest["files"]["target_bundles"]["sha256"])},
            "source_build_commit": source_build_commit,
        },
        "parent_records": parent_records,
        "comparison_source": comparison_source(bundle, profiles, contexts, levels, containers),
    }
    return build_input_frame_v0_3(payload)


def population_identity(bundles: list[Mapping[str, Any]], manifest: Mapping[str, Any]) -> str:
    rows = [{"observation_id": bundle["observation_id"], "side": bundle["side"], "first_valid_time": bundle["first_valid_time"], "context_bundle_id": bundle["context_bundle_id"], "profile_output_ids": bundle["profile_output_ids"]} for bundle in bundles]
    rows.sort(key=lambda row: (row["side"], row["first_valid_time"], row["observation_id"]))
    return sha256_hex({"materialisation_id": manifest["materialisation_id"], "unit": "C2EInputFrame_CANDIDATE_SOURCE", "count": len(rows), "rows": rows})


def load_materialisation(root: Path, *, expected_manifest_sha: str, expected_target_sha: str, expected_population_sha: str) -> dict[str, Any]:
    manifest = load_json(root / "materialisation-manifest.json")
    _require(manifest.get("logical_sha256") == expected_manifest_sha, "MATERIALISATION_MANIFEST_IDENTITY_DRIFT")
    for item in manifest["files"].values():
        path = root / item["file_name"]
        _require(path.is_file(), f"MATERIALISATION_FILE_MISSING:{item['file_name']}")
        _require(sha256_file(path) == item["sha256"], f"MATERIALISATION_FILE_HASH_DRIFT:{item['file_name']}")
    _require(manifest["files"]["target_bundles"]["sha256"] == expected_target_sha, "TARGET_BUNDLE_MANIFEST_HASH_DRIFT")
    bundles = load_jsonl(root / manifest["files"]["target_bundles"]["file_name"])
    _require(len(bundles) == 4072, "TARGET_FRAME_COUNT_DRIFT")
    _require(population_identity(bundles, manifest) == expected_population_sha, "TARGET_POPULATION_IDENTITY_DRIFT")
    return {
        "manifest": manifest, "bundles": bundles,
        "observations": {row["observation_id"]: row for row in load_jsonl(root / manifest["files"]["observations_15m"]["file_name"])},
        "parent_observations": {row["observation_id"]: row for row in load_jsonl(root / manifest["files"]["observations_2h"]["file_name"])},
        "profiles": {row["profile_output_id"]: row for row in load_jsonl(root / manifest["files"]["profiles"]["file_name"])},
        "memberships": {row["membership_id"]: row for row in load_jsonl(root / manifest["files"]["memberships"]["file_name"])},
        "contexts": {row["bundle_id"]: row for row in load_jsonl(root / manifest["files"]["contexts"]["file_name"])},
        "levels": {row["level_id"]: row for row in load_jsonl(root / manifest["files"]["levels"]["file_name"])},
        "containers": {row["container_id"]: row for row in load_jsonl(root / manifest["files"]["containers"]["file_name"])},
        "relation_sets": {row["relation_set_id"]: row for row in load_jsonl(root / manifest["files"]["relation_sets"]["file_name"])},
    }


def _rule(pack: Mapping[str, Any], rule_id: str) -> dict[str, Any]:
    for rule in pack["rules"]:
        if rule["boundary_rule_id"] == rule_id:
            return dict(rule)
    raise SourceReplayError(f"BOUNDARY_RULE_MISSING:{rule_id}")


@dataclass
class ReplayResult:
    frame_index: list[dict[str, Any]]
    evaluations: list[dict[str, Any]]
    records: list[dict[str, Any]]
    disagreements: list[dict[str, Any]]
    blocked_candidates: list[dict[str, Any]]
    counters: dict[str, int]


def run_source_replay(materialisation: Mapping[str, Any], pack: Mapping[str, Any], *, source_build_commit: str) -> ReplayResult:
    engine = EpisodeEngine(str(pack["boundary_pack_id"]))
    frame_index: list[dict[str, Any]] = []
    evaluations: list[dict[str, Any]] = []
    disagreements: list[dict[str, Any]] = []
    blocked_candidates: list[dict[str, Any]] = []
    counters = {name: 0 for name in ("birth", "continuation", "phase_mutation", "re_parent", "censor_gap", "censor_release_end", "legacy_disagreements", "candidate_not_evaluable", "resolver_conflicts")}
    by_side = {"ASK": [], "BID": []}
    for bundle in materialisation["bundles"]:
        by_side[str(bundle["side"])].append(bundle)
    for side in by_side:
        by_side[side].sort(key=lambda row: (row["first_valid_time"], row["observation_id"]))

    phase_state: dict[str, tuple[str, list[str]]] = {}
    for side in ("ASK", "BID"):
        previous: dict[str, Any] | None = None
        active_episode_id: str | None = None
        for bundle in by_side[side]:
            frame = build_frame(
                bundle, predecessor_observation_id=previous["identity"]["observation_id"] if previous else None,
                observations=materialisation["observations"], parent_observations=materialisation["parent_observations"],
                profiles=materialisation["profiles"], memberships=materialisation["memberships"], contexts=materialisation["contexts"],
                levels=materialisation["levels"], containers=materialisation["containers"], relation_sets=materialisation["relation_sets"],
                materialisation_manifest=materialisation["manifest"], source_build_commit=source_build_commit,
            )
            frame_index.append({
                "schema": "c2e_input_frame_index/v0_1", "frame_id": frame["frame_id"], "logical_hash": frame["logical_hash"],
                "lineage_hash": frame["lineage_hash"], "observation_id": frame["identity"]["observation_id"], "side": side,
                "first_valid_time": frame["chronology"]["first_valid_time"], "continuity_segment_id": frame["chronology"]["continuity_segment_id"],
                "predecessor_observation_id": frame["chronology"].get("predecessor_observation_id"),
                "structural_signature_sha256": frame["comparison"]["structural_signature_sha256"],
                "parent_signature_sha256": frame["comparison"]["parent_signature_sha256"], "context_bundle_id": frame["context"].get("context_resolution_bundle_id"),
                "source_relation_set_count": sum(1 for item in frame["lineage"]["parent_record_ids"] if str(item).startswith("C2.RELATION.SET.")),
                "authority": "INACTIVE_NONCANONICAL_SHADOW",
            })
            corrected = evaluate_boundary_predicates_v2(frame, previous)
            legacy = evaluate_legacy_predicates(frame, previous)
            if corrected != legacy:
                counters["legacy_disagreements"] += 1
                disagreements.append({"schema": "c2e_boundary_disagreement/v0_1", "side": side, "frame_id": frame["frame_id"], "first_valid_time": frame["chronology"]["first_valid_time"], "corrected_matched_rules": [rule_id for rule_id in RULE_IDS if corrected[rule_id]], "legacy_matched_rules": [rule_id for rule_id in RULE_IDS if legacy[rule_id]], "authority": "COMPARATOR_ONLY"})
            candidates = []
            for rule_id in RULE_IDS:
                candidate = build_candidate(_rule(pack, rule_id), frame, matched=corrected[rule_id], effective_time=frame["chronology"]["first_valid_time"])
                if candidate is not None:
                    if not candidate["evaluable"]:
                        counters["candidate_not_evaluable"] += 1; blocked_candidates.append(candidate)
                    candidates.append(candidate)
            resolved = resolve_candidates(pack, candidates)
            if resolved["status"] != "RESOLVED":
                counters["resolver_conflicts"] += 1
                raise SourceReplayError(f"BOUNDARY_RESOLUTION_CONFLICT:{side}:{frame['frame_id']}:{resolved['reason_codes']}")
            actions = []
            for candidate in resolved["resolved"]:
                action = candidate["lifecycle_action"]
                if action == "CENSOR_GAP":
                    _require(active_episode_id is not None, "NO_ACTIVE_EPISODE_TO_CENSOR")
                    engine.censor(episode_id=active_episode_id, candidate_id=candidate["candidate_id"], reason="CENSOR_GAP", effective_time=candidate["effective_time"], first_valid_time=candidate["first_valid_time"])
                    counters["censor_gap"] += 1; active_episode_id = None
                elif action == "RE_PARENT":
                    _require(active_episode_id is not None, "NO_ACTIVE_EPISODE_TO_REPARENT")
                    engine.re_parent(episode_id=active_episode_id, candidate_id=candidate["candidate_id"], effective_time=candidate["effective_time"], first_valid_time=candidate["first_valid_time"], reason_codes=["C2E_UPSTREAM_PARENT_SIGNATURE_CHANGE"])
                    counters["re_parent"] += 1
                elif action == "PHASE_MUTATION":
                    _require(active_episode_id is not None, "NO_ACTIVE_EPISODE_TO_PHASE")
                    start_time, source_ids = phase_state[active_episode_id]
                    phase = engine.phase_mutation(episode_id=active_episode_id, candidate_id=candidate["candidate_id"], phase_type="STRUCTURAL_SIGNATURE_INTERVAL", start_time=start_time, end_time=candidate["effective_time"], source_record_ids=source_ids, effective_time=candidate["effective_time"], first_valid_time=candidate["first_valid_time"])
                    phase_state[active_episode_id] = (candidate["effective_time"], sorted(frame["structural"]["location_record_ids"] + frame["structural"]["motion_record_ids"] + frame["structural"]["organisation_record_ids"] + frame["structural"]["interaction_record_ids"]))
                    counters["phase_mutation"] += 1
                elif action == "CONTINUATION":
                    _require(active_episode_id is not None, "NO_ACTIVE_EPISODE_TO_CONTINUE")
                    engine.continue_episode(episode_id=active_episode_id, frame=frame, candidate_id=candidate["candidate_id"], effective_time=candidate["effective_time"], first_valid_time=candidate["first_valid_time"])
                    counters["continuation"] += 1
                elif action == "BIRTH":
                    genesis = engine.birth(frame=frame, boundary_rule_id=candidate["boundary_rule_id"], candidate_id=candidate["candidate_id"], effective_time=candidate["effective_time"], first_valid_time=candidate["first_valid_time"])
                    active_episode_id = genesis["episode_id"]
                    phase_state[active_episode_id] = (candidate["effective_time"], sorted(frame["structural"]["location_record_ids"] + frame["structural"]["motion_record_ids"] + frame["structural"]["organisation_record_ids"] + frame["structural"]["interaction_record_ids"]))
                    counters["birth"] += 1
                else:
                    raise SourceReplayError(f"UNSUPPORTED_LIFECYCLE_ACTION:{action}")
                actions.append(action)
            evaluations.append({"schema": "c2e_boundary_evaluation/v0_2", "side": side, "frame_id": frame["frame_id"], "first_valid_time": frame["chronology"]["first_valid_time"], "matched_rules": [rule_id for rule_id in RULE_IDS if corrected[rule_id]], "resolved_actions": actions, "blocked_candidate_ids": [candidate["candidate_id"] for candidate in candidates if not candidate["evaluable"]], "authority": "INACTIVE_NONCANONICAL_SHADOW"})
            previous = frame
        _require(previous is not None and active_episode_id is not None, "SIDE_POPULATION_EMPTY_OR_UNOWNED")
        release = build_candidate(_rule(pack, RULE_IDS[1]), previous, matched=True, effective_time=TARGET_END)
        _require(release is not None and release["evaluable"], "RELEASE_END_CANDIDATE_NOT_EVALUABLE")
        engine.censor(episode_id=active_episode_id, candidate_id=release["candidate_id"], reason="CENSOR_RELEASE_END", effective_time=TARGET_END, first_valid_time=TARGET_END)
        counters["censor_release_end"] += 1
        evaluations.append({"schema": "c2e_boundary_evaluation/v0_2", "side": side, "frame_id": previous["frame_id"], "first_valid_time": TARGET_END, "matched_rules": [RULE_IDS[1]], "resolved_actions": ["CENSOR_RELEASE_END"], "blocked_candidate_ids": [], "authority": "INACTIVE_NONCANONICAL_SHADOW"})

    membership_count = sum(1 for record in engine.stream.records if record.get("schema") == "c2e_membership_delta/v0_2")
    _require(membership_count == 4072, f"MEMBERSHIP_COUNT_RECONCILIATION_FAILED:{membership_count}")
    for episode_id in sorted(engine.genesis):
        engine.stream.append(engine.snapshot(episode_id, as_of_time=TARGET_END, first_valid_time=TARGET_END))
    _require(counters["birth"] == len(engine.genesis), "BIRTH_EPISODE_COUNT_MISMATCH")
    _require(counters["censor_release_end"] == 2, "RELEASE_END_SIDE_COUNT_MISMATCH")
    return ReplayResult(frame_index, evaluations, list(engine.stream.records), disagreements, blocked_candidates, counters)


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    with path.open("wb") as handle:
        count = 0
        for row in rows:
            handle.write(canonical_bytes(row) + b"\n"); count += 1
    return {"file_name": path.name, "record_count": count, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)}


def write_run(result: ReplayResult, out_dir: Path, *, source_binding: Mapping[str, Any], boundary_pack_id: str, code_hashes: list[str]) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "frame_index": write_jsonl(out_dir / "c2e-input-frame-index-v0_3.jsonl", result.frame_index),
        "evaluations": write_jsonl(out_dir / "c2e-boundary-evaluations-v2.jsonl", result.evaluations),
        "stream": write_jsonl(out_dir / "c2e-event-stream-v0_2.jsonl", result.records),
        "disagreements": write_jsonl(out_dir / "c2e-boundary-disagreement-ledger.jsonl", result.disagreements),
        "blocked_candidates": write_jsonl(out_dir / "c2e-not-evaluable-candidates.jsonl", result.blocked_candidates),
    }
    id_fields = ("episode_id", "snapshot_id", "phase_segment_id", "boundary_event_id", "membership_delta_id", "lineage_edge_id")
    ordered_ids = []; ordered_hashes = []; counts: dict[str, int] = {}
    for record in result.records:
        record_id = next((record[field] for field in id_fields if field in record), None)
        _require(record_id is not None, "STREAM_RECORD_ID_MISSING")
        ordered_ids.append(record_id); ordered_hashes.append(record["logical_hash"]); counts[record["schema"]] = counts.get(record["schema"], 0) + 1
    stream_manifest = build_record("stream_manifest", {"source_binding": copy.deepcopy(dict(source_binding)), "boundary_pack_id": boundary_pack_id, "schema_ids": sorted(counts), "code_hashes": sorted(code_hashes), "ordered_record_ids": ordered_ids, "ordered_record_hashes": ordered_hashes, "counts": counts, "missingness": {"not_evaluable_candidates": len(result.blocked_candidates)}, "authority": "INACTIVE_NONCANONICAL_SHADOW"})
    (out_dir / "c2e-stream-manifest-v0_2.json").write_bytes(canonical_bytes(stream_manifest) + b"\n")
    files["stream_manifest"] = {"file_name": "c2e-stream-manifest-v0_2.json", "record_count": 1, "size_bytes": (out_dir / "c2e-stream-manifest-v0_2.json").stat().st_size, "sha256": sha256_file(out_dir / "c2e-stream-manifest-v0_2.json")}
    checkpoint = build_record("checkpoint", {"stream_manifest_id": stream_manifest["stream_manifest_id"], "completed_partitions": ["ASK", "BID"], "logical_cursor": "TARGET_END:2026-07-01T00:00:00Z", "semantic_prefix_hash": sha256_hex(ordered_hashes), "replaceable": True, "authority": "OPERATIONAL_NON_SEMANTIC"})
    (out_dir / "c2e-checkpoint-final-v0_2.json").write_bytes(canonical_bytes(checkpoint) + b"\n")
    files["checkpoint"] = {"file_name": "c2e-checkpoint-final-v0_2.json", "record_count": 1, "size_bytes": (out_dir / "c2e-checkpoint-final-v0_2.json").stat().st_size, "sha256": sha256_file(out_dir / "c2e-checkpoint-final-v0_2.json")}
    logical_files = {key: value["sha256"] for key, value in sorted(files.items())}
    receipt = {"schema": "c2e_wp6_run_output_manifest/v0_1", "programme_id": PROGRAMME_ID, "packet_id": PACKET_ID, "boundary_pack_id": boundary_pack_id, "source_binding": copy.deepcopy(dict(source_binding)), "files": files, "counters": copy.deepcopy(result.counters), "frame_count": len(result.frame_index), "stream_record_count": len(result.records), "episode_count": result.counters["birth"], "logical_output_sha256": sha256_hex(logical_files), "authority": "INACTIVE_NONCANONICAL_SHADOW", "provider_intake": "NONE", "sampling": "NONE", "validation_consumption": "NONE"}
    (out_dir / "c2e-wp6-run-output-manifest.json").write_bytes(canonical_bytes(receipt) + b"\n")
    return receipt
