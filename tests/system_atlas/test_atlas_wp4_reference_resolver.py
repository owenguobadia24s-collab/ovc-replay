from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from ovc.development.skills.registry import validate_against_schema
from ovc.system_atlas.canonical import canonical_sha256
from ovc.system_atlas.resolver import (
    AtlasResolverError,
    relationship_resolution_state,
    resolve_current_vit_projection,
    resolve_reference_candidates,
)


ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "fixtures/system_atlas/wp4/ATLAS_RESOLVER_ADVERSARIAL_CASES_v0_1.json"
PREDICATES = ROOT / "registries/system_atlas/ATLAS_PREDICATE_AUTHORITY_REGISTRY_v0_1.json"
RESOLVERS = ROOT / "registries/system_atlas/ATLAS_RESOLVER_REGISTRY_v0_1.json"
REVIEWER = ROOT / "registries/system_atlas/ATLAS_INDEPENDENT_REVIEWER_BINDING_G4_ALG_20260816.json"
SCHEMA = ROOT / "schemas/system_atlas/reference_resolution_set_v0_1.schema.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def inline_local_refs(node: Any, root: dict) -> Any:
    if isinstance(node, list):
        return [inline_local_refs(item, root) for item in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        target: Any = root
        for part in node["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        return inline_local_refs(target, root)
    return {key: inline_local_refs(value, root) for key, value in node.items()}


@pytest.mark.parametrize(
    ("declared", "observed", "forbidden", "conflict", "expected"),
    [
        (True, True, False, False, "RECONCILED"),
        (True, False, False, False, "DECLARED_ONLY"),
        (False, True, False, False, "OBSERVED_ONLY"),
        (True, True, True, False, "FORBIDDEN_OBSERVED"),
        (False, True, True, False, "FORBIDDEN_OBSERVED"),
        (True, True, False, True, "CONFLICTING"),
        (None, None, False, False, "UNRESOLVED"),
    ],
)
def test_relationship_reconciliation_matrix(
    declared: bool | None, observed: bool | None, forbidden: bool, conflict: bool, expected: str
) -> None:
    assert relationship_resolution_state(
        declared=declared, observed=observed, forbidden=forbidden, authority_conflict=conflict
    ) == expected


def test_adversarial_owner_and_authority_cases_fail_honestly() -> None:
    registry = load(PREDICATES)
    for case in load(CASES)["cases"]:
        result = resolve_reference_candidates(case["candidates"], predicate_registry=registry)
        assert len(result["resolutions"]) == 1
        assert result["resolutions"][0]["resolution_status"] == case["expected_status"]
        assert result["canonical_assertions"] == []
        assert result["resolutions"][0]["canonical_eligibility"] != "ELIGIBLE"


def test_owner_conflict_preserves_all_competing_candidates() -> None:
    case = load(CASES)["cases"][0]
    result = resolve_reference_candidates(case["candidates"], predicate_registry=load(PREDICATES))
    assert len(result["conflicts"]) == 1
    conflict = result["conflicts"][0]
    assert conflict["conflict_class"] == "OWNER_CONFLICT"
    assert len(conflict["competing_candidate_ids"]) == 2
    assert result["resolutions"][0]["conflict_id"] == conflict["conflict_id"]


def test_resolver_is_permutation_invariant_and_content_addressed() -> None:
    case = load(CASES)["cases"][4]
    first = resolve_reference_candidates(case["candidates"], predicate_registry=load(PREDICATES))
    second = resolve_reference_candidates(list(reversed(case["candidates"])), predicate_registry=load(PREDICATES))
    assert first == second
    body = dict(first)
    observed_hash = body.pop("resolution_set_hash")
    assert canonical_sha256(body) == observed_hash


def test_only_explicit_identity_continuity_can_normalize_aliases() -> None:
    case = deepcopy(load(CASES)["cases"][2])
    case["candidates"][0]["subject_id"] = "ovc:alias:read"
    result = resolve_reference_candidates(
        case["candidates"],
        predicate_registry=load(PREDICATES),
        identity_bindings={"ovc:alias:read": {"canonical_id": "ovc:capability:read", "continuity_status": "EXPLICIT"}},
    )
    assert result["resolutions"][0]["subject_id"] == "ovc:capability:read"
    with pytest.raises(AtlasResolverError, match="ATLAS_IDENTITY_BINDING_NOT_EXPLICIT"):
        resolve_reference_candidates(
            case["candidates"],
            predicate_registry=load(PREDICATES),
            identity_bindings={"ovc:alias:read": {"canonical_id": "ovc:capability:read", "continuity_status": "POSSIBLE_MATCH"}},
        )


def test_missing_required_scope_is_unresolved_without_scope_widening() -> None:
    candidate = deepcopy(load(CASES)["cases"][2]["candidates"][0])
    del candidate["scope"]["dimensions"]["authority_generation"]
    result = resolve_reference_candidates([candidate], predicate_registry=load(PREDICATES))
    resolution = result["resolutions"][0]
    assert resolution["resolution_status"] == "UNRESOLVED"
    assert any("REQUIRED_SCOPE_DIMENSION_MISSING" in reason for reason in resolution["reasons"])
    assert "authority_generation" not in resolution["scope"]["dimensions"]


def test_algorithm_pass_flag_changes_eligibility_not_canonical_output() -> None:
    case = load(CASES)["cases"][2]
    pending = resolve_reference_candidates(case["candidates"], predicate_registry=load(PREDICATES))
    passed = resolve_reference_candidates(
        case["candidates"], predicate_registry=load(PREDICATES), algorithm_gate_status="PASS"
    )
    assert pending["resolutions"][0]["canonical_eligibility"] == "DENIED_PENDING_ATLAS_G4_ALG"
    assert passed["resolutions"][0]["canonical_eligibility"] == "ELIGIBLE"
    assert passed["canonical_assertions"] == []


def test_reference_resolution_set_validates_against_schema() -> None:
    case = load(CASES)["cases"][2]
    result = resolve_reference_candidates(case["candidates"], predicate_registry=load(PREDICATES))
    schema = load(SCHEMA)
    validate_against_schema(result, inline_local_refs(schema, schema))


def test_resolver_registry_and_independent_gate_are_accepted() -> None:
    registry = load(RESOLVERS)
    reviewer = load(REVIEWER)
    assert registry["status"] == "ACCEPTED_ATLAS_G4_ALG"
    assert len(registry["registered_resolvers"]) == 3
    assert {row["acceptance_status"] for row in registry["registered_resolvers"]} == {"ACCEPTED_ATLAS_G4_ALG"}
    assert reviewer["status"] == "ACCEPTED_EXTERNAL_BINDING_PENDING_REPOSITORY_MATERIALISATION"
    assert reviewer["no_self_review"] is True
    assert reviewer["operator_substitution"] is False
    assert "ATLAS-G4-ALG_PREDICATE_OWNER_AUTHORITY_ALGORITHMS" in reviewer["required_scopes"]


def test_vit_current_projection_consumes_current_resolver_without_fallback() -> None:
    projection = resolve_current_vit_projection(ROOT)
    assert projection["source_resolution"]["resolution_status"] == "RESOLVED_CURRENT"
    assert projection["historical_source_fallback_allowed"] is False
    assert {row["predicate"] for row in projection["predicates"]} == {"CURRENT", "ACTIVE", "AUTHORISED"}
    assert all(row["canonical_eligibility"] == "DENIED_PENDING_ATLAS_G4_ALG" for row in projection["predicates"])
    assert projection["canonical_assertions"] == []
    body = dict(projection)
    observed_hash = body.pop("projection_hash")
    assert canonical_sha256(body) == observed_hash
