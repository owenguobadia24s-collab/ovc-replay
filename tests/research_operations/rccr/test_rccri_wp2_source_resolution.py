from __future__ import annotations

import copy

import pytest

from ovc.research_operations.rccr.core import RCCRValidationError
from ovc.research_operations.rccr.source_resolution import (
    RequirementDependencyIndex,
    RequirementProfileCompiler,
    SourceResolverService,
    project_currentness,
)

HEX_A = "a" * 64
HEX_B = "b" * 64
BASE_REQS = {
    "scientific_constructs": ["structural recurrence"],
    "epistemic_requirements": ["owner-faithful structural evidence"],
    "evidence_requirements": ["exact source identity"],
    "population_requirements": ["declared population"],
    "chronology_requirements": ["first-valid chronology"],
    "inferential_requirements": ["dependency-aware interpretation"],
    "denominator_requirements": ["explicit denominator"],
    "comparability_requirements": ["declared comparability"],
    "forbidden_dependencies": ["Validation"],
    "sufficiency_conditions": ["all core requirements satisfied"],
    "partial_sufficiency_conditions": [],
    "invalidating_conditions": ["protected-source consumption"],
    "known_limitations": [],
}


def owner_source(source_id="EC1-Q01"):
    return {
        "source_id": source_id,
        "source_owner": "OVC-EC1-DMRP-CONFORMANCE-v0.1",
        "object_type": "EC1_QUESTION",
        "semantic_generation": "OVC-EC1-DISCOVERY-2021_2023-G1",
        "semantic_payload_hash": HEX_A,
        "artifact_byte_hash": HEX_B,
        "first_valid_time": "2026-08-14T09:25:00+01:00",
        "authority_state": "PRE_EVIDENTIARY_DEFINITION_ONLY",
        "source_refs": ["repo:ec1:q01"],
        "source_class": "OWNER",
    }


def test_av01_exact_source_identity_and_manifest_are_order_deterministic():
    a = owner_source("EC1-Q01")
    b = owner_source("EC1-Q02")
    b["semantic_payload_hash"] = HEX_B
    svc = SourceResolverService([a, b])
    left = svc.manifest(["EC1-Q02", "EC1-Q01"])
    right = svc.manifest(["EC1-Q01", "EC1-Q02"])
    assert left == right
    assert left["protected_payloads_opened"] is False
    with pytest.raises(RCCRValidationError) as exc:
        svc.resolve("What proportion of the intended Discovery population is evaluable?")
    assert exc.value.code == "SOURCE_NOT_FOUND_EXACT_ID"


def test_av02_external_source_is_downgraded_and_cannot_create_owner_authority():
    external = owner_source("EXT-FINDING-01")
    external.update(source_owner="EXTERNAL_LITERATURE", source_class="EXTERNAL", authority_state="UNTESTED")
    resolved = SourceResolverService([external]).resolve("EXT-FINDING-01")
    assert resolved.owner_authority_effect == "NONE"
    profile = RequirementProfileCompiler().compile(
        coverage_item_generation_id="coverage:external:1",
        resolved_source=resolved,
        derivation_mode="EXTERNAL_FINDING_CROSSWALK",
        requirements=BASE_REQS,
        reviewer="OVC_INDEPENDENT_REVIEWER",
        reviewed_at="2026-08-15T20:00:00+01:00",
    )
    assert profile["authority_effect"] == "NONE"
    assert profile["derivation_class"] == "HUMAN_REVIEWED"
    assert "EXTERNAL_SOURCE_AUTHORITY_EFFECT_NONE" in profile["derivation_refs"]


def test_av03_protected_validation_source_is_denied_before_payload_resolution():
    protected = owner_source("VALIDATION-SECRET-01")
    protected["protected"] = True
    protected["protection_class"] = "VALIDATION"
    svc = SourceResolverService([protected])
    with pytest.raises(RCCRValidationError) as exc:
        svc.resolve("VALIDATION-SECRET-01")
    assert exc.value.code == "PROTECTED_SOURCE_DENIED"


def test_missing_owner_authority_fails_closed():
    broken = owner_source()
    broken["authority_state"] = ""
    with pytest.raises(RCCRValidationError) as exc:
        SourceResolverService([broken]).resolve("EC1-Q01")
    assert exc.value.code == "MISSING_OWNER_AUTHORITY"


def test_same_wording_different_exact_source_remains_distinct():
    a = owner_source("PATH2-THEORY-A")
    b = copy.deepcopy(a)
    b["source_id"] = "PATH2-THEORY-B"
    b["source_refs"] = ["repo:path2:theory-b"]
    svc = SourceResolverService([a, b])
    compiler = RequirementProfileCompiler()
    pa = compiler.compile(
        coverage_item_generation_id="coverage:a",
        resolved_source=svc.resolve("PATH2-THEORY-A"),
        derivation_mode="SOURCE_EXPLICIT",
        requirements=BASE_REQS,
    )
    pb = compiler.compile(
        coverage_item_generation_id="coverage:b",
        resolved_source=svc.resolve("PATH2-THEORY-B"),
        derivation_mode="SOURCE_EXPLICIT",
        requirements=BASE_REQS,
    )
    assert pa["requirement_profile_id"] != pb["requirement_profile_id"]


def test_formatting_equivalent_requirement_inputs_compile_identically():
    svc = SourceResolverService([owner_source()])
    resolved = svc.resolve("EC1-Q01")
    left = RequirementProfileCompiler().compile(
        coverage_item_generation_id="coverage:q01",
        resolved_source=resolved,
        derivation_mode="SOURCE_CROSSWALK",
        requirements={**BASE_REQS, "evidence_requirements": ["z", "a"]},
        derivation_refs=["mapping:z", "mapping:a"],
    )
    right = RequirementProfileCompiler().compile(
        coverage_item_generation_id="coverage:q01",
        resolved_source=resolved,
        derivation_mode="SOURCE_CROSSWALK",
        requirements={**BASE_REQS, "evidence_requirements": ["a", "z"]},
        derivation_refs=["mapping:a", "mapping:z"],
    )
    assert left == right


def test_semantic_choice_and_operator_formalisation_route_to_human_review():
    resolved = SourceResolverService([owner_source()]).resolve("EC1-Q01")
    compiler = RequirementProfileCompiler()
    with pytest.raises(RCCRValidationError) as exc:
        compiler.compile(
            coverage_item_generation_id="coverage:q01",
            resolved_source=resolved,
            derivation_mode="PROTOCOL_DERIVED",
            requirements=BASE_REQS,
            semantic_choice_required=True,
        )
    assert exc.value.code == "HUMAN_REVIEW_REQUIRED"
    with pytest.raises(RCCRValidationError):
        compiler.compile(
            coverage_item_generation_id="coverage:q01",
            resolved_source=resolved,
            derivation_mode="OPERATOR_FORMALISED",
            requirements=BASE_REQS,
        )


def test_theory_implication_without_explicit_falsifier_requires_review():
    resolved = SourceResolverService([owner_source()]).resolve("EC1-Q01")
    with pytest.raises(RCCRValidationError) as exc:
        RequirementProfileCompiler().compile(
            coverage_item_generation_id="coverage:q01",
            resolved_source=resolved,
            derivation_mode="THEORY_IMPLICATION_DERIVED",
            requirements=BASE_REQS,
            theory_falsifiers_explicit=False,
        )
    assert exc.value.code == "HUMAN_REVIEW_REQUIRED"


def test_dependency_index_is_idempotent_and_collision_fail_closed():
    resolved = SourceResolverService([owner_source()]).resolve("EC1-Q01")
    profile = RequirementProfileCompiler().compile(
        coverage_item_generation_id="coverage:q01",
        resolved_source=resolved,
        derivation_mode="SOURCE_EXPLICIT",
        requirements=BASE_REQS,
    )
    index = RequirementDependencyIndex()
    index.register(profile)
    index.register(profile)
    assert "EC1-Q01" in index.dependencies(profile["requirement_profile_id"])
    mutated = copy.deepcopy(profile)
    mutated["derivation_refs"] = ["other-source"]
    with pytest.raises(RCCRValidationError) as exc:
        index.register(mutated)
    assert exc.value.code == "DEPENDENCY_INDEX_COLLISION"


def test_currentness_is_source_and_protocol_specific():
    assert project_currentness(
        prior_source_token="s1", current_source_token="s1", prior_protocol_token="p1", current_protocol_token="p1"
    ) == "CURRENT"
    assert project_currentness(
        prior_source_token="s1", current_source_token="s2", prior_protocol_token="p1", current_protocol_token="p1"
    ) == "STALE_SOURCE"
    assert project_currentness(
        prior_source_token="s1", current_source_token="s1", prior_protocol_token="p1", current_protocol_token="p2"
    ) == "STALE_PROTOCOL"
