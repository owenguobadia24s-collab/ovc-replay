import dataclasses
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from ovc.research_operations.spto.factorised_mechanics import (
    ANTECEDENT_HIERARCHIES,
    CARRIER_FIELDS,
    CARRIER_PACKS,
    COMPARISON_TARGET_PACK_ID,
    DECLARED_REPRESENTATIONS,
    MechanicsError,
    TARGET_HIERARCHIES,
    TARGET_PACKS,
    build_carrier_view,
    build_derivation_manifest,
    build_factorised_path,
    build_frontier_record,
    build_operation_view,
    build_population_manifest,
    build_relation,
    build_trace_set,
    build_training_frontier,
    canonical_bytes,
    carrier_pack,
    comparison_target_manifest,
    content_id,
    contract_registry,
    decoder_manifest,
    factorisation_constitution,
    reduce_trace_set,
    synthetic_qualification_fixture,
)


ROOT = Path(__file__).resolve().parents[3]


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def before_after():
    return {
        "ENV_STATUS": ("OPEN", "OPEN"),
        "ENV_LIFECYCLE": ("FORMING", "MATURE"),
        "ENV_RELATION": ("INSIDE", "INSIDE"),
        "ETR_ATOMIC": ("UP", "DOWN"),
        "ETR_COMPOUND": ("EXPAND", "EXPAND"),
        "ETR_OPEN_STATE": ("OPEN", "CLOSED"),
    }


def qualified_records(frontier_id="frontier-1"):
    supports = {
        "BASE": {"T.A": 3, "T.B": 2},
        "NO_HI": {"T.A": 4, "T.C": 2},
        "NO_MID": {"T.A": 2, "T.B": 1},
        "PATH_BEFORE_MID": {"T.A": 5, "T.C": 1},
        "NO_PATH": {"T.A": 2, "T.D": 2},
    }
    return [
        build_frontier_record(
            representation_id=representation,
            antecedent_support=3,
            selected_backoff_level=ANTECEDENT_HIERARCHIES[representation][0],
            selected_target_resolution="R18_MID_v1",
            target_supports=supports[representation],
            opportunity_denominator=7,
            training_frontier_id=frontier_id,
        )
        for representation in DECLARED_REPRESENTATIONS
    ]


def test_registry_is_exact_schema_valid_and_source_free():
    registry = load(
        "docs/programmes/c2s-sptoi-v0-1/wp6/"
        "C2S_SPTOI_WP6_FACTORISED_MECHANICS_REGISTRY_v0_1.json"
    )
    jsonschema = pytest.importorskip("jsonschema")
    schema = load("schemas/research_operations/spto/FACTORISED_MECHANICS_REGISTRY_v0_1.schema.json")
    jsonschema.Draft202012Validator(schema).validate(registry)
    assert registry == contract_registry()
    saved_id = registry.pop("registry_id")
    assert saved_id == content_id("FactorisedMechanicsRegistry/v1", registry)
    assert registry["protected_source_access"] == "NONE"
    assert registry["factorised_evidence_execution"] == "DENIED"
    assert registry["scalar_confidence"] == "FORBIDDEN"


def test_filed_synthetic_fixture_is_exact_replay_and_schema_valid():
    fixture = load(
        "docs/programmes/c2s-sptoi-v0-1/wp6/"
        "C2S_SPTOI_WP6_SYNTHETIC_QUALIFICATION_FIXTURE_v0_1.json"
    )
    jsonschema = pytest.importorskip("jsonschema")
    schema = load(
        "schemas/research_operations/spto/FACTORISED_MECHANICS_SYNTHETIC_FIXTURE_v0_1.schema.json"
    )
    jsonschema.Draft202012Validator(schema).validate(fixture)
    assert fixture == synthetic_qualification_fixture()
    saved_id = fixture.pop("bundle_id")
    assert saved_id == content_id("FactorisedMechanicsSyntheticFixture/v1", fixture)
    assert fixture["robust_frontier"]["members"] == ["SYNTH.TARGET.A"]
    assert fixture["ambiguity_shell"]["members"] == [
        "SYNTH.TARGET.B", "SYNTH.TARGET.C", "SYNTH.TARGET.D"
    ]
    assert fixture["realised_continuation_in_prospective_identity"] is False


def test_frozen_packs_hierarchies_and_common_target_are_complete():
    assert set(CARRIER_PACKS) == {"C_EXACT_v1", "R25_HI_v1", "R25_MID_v1", "C_BROAD_v1"}
    assert tuple(ANTECEDENT_HIERARCHIES) == ("BASE", "NO_HI", "NO_MID", "PATH_BEFORE_MID", "NO_PATH")
    assert TARGET_PACKS == ("T0_v1", "T1_v1", "R18_MID_v1", "ETR_v1", "T2_v1", "T3_v1")
    assert set(TARGET_HIERARCHIES) == {"BASE", "NO_T1", "NO_MID", "NO_ETR", "COMPACT"}
    assert comparison_target_manifest().target_pack_id == COMPARISON_TARGET_PACK_ID
    assert carrier_pack("C_BROAD_v1").omitted_fields == CARRIER_FIELDS
    assert carrier_pack("R25_HI_v1").coarse_fields == ("ETR_COMPOUND",)
    assert carrier_pack("R25_MID_v1").coarse_fields == ("ETR_ATOMIC", "ETR_COMPOUND")


def test_decoder_keeps_exact_unchanged_values_and_changed_sentinel():
    exact = build_carrier_view("occ-1", "C_EXACT_v1", before_after())
    hi = build_carrier_view("occ-1", "R25_HI_v1", before_after())
    mid = build_carrier_view("occ-1", "R25_MID_v1", before_after())
    assert dict(exact.values) == {
        "ENV_STATUS": "OPEN",
        "ENV_LIFECYCLE": "CHANGED",
        "ENV_RELATION": "INSIDE",
        "ETR_ATOMIC": "CHANGED",
        "ETR_COMPOUND": "EXPAND",
        "ETR_OPEN_STATE": "CHANGED",
    }
    assert dict(hi.values)["ETR_COMPOUND"] == "UNCHANGED"
    assert dict(mid.values)["ETR_ATOMIC"] == "CHANGED"
    assert build_carrier_view("occ-1", "C_BROAD_v1", before_after()) is None
    assert exact.carrier_morphology_id != hi.carrier_morphology_id


def test_operation_domain_and_boundary_exclusion_fail_closed():
    operation = build_operation_view(
        "occ-1", {"LEVEL_COUNT": 1, "RELATION_COUNT": -1}, {"STATUS": ("OPEN", "OPEN")}
    )
    assert operation.count_roles == (("LEVEL_COUNT", 1), ("RELATION_COUNT", -1))
    assert operation.enum_roles == (("STATUS", "UNCHANGED"),)
    with pytest.raises(MechanicsError, match="INVALID_COUNT_ROLE"):
        build_operation_view("occ-1", {"LEVEL_COUNT": 2}, {})
    with pytest.raises(MechanicsError, match="BOUNDARY_REFERENT_EXCLUDED"):
        build_operation_view("occ-1", {}, {}, boundary_roles=["UPPER_REFERENT"])
    broken = before_after()
    broken.pop("ENV_STATUS")
    with pytest.raises(MechanicsError, match="FACTORISATION_DECODER_AMBIGUOUS"):
        build_carrier_view("occ-1", "C_EXACT_v1", broken)


def test_ordered_path_requires_strict_antecedent_availability():
    operation = build_operation_view("occ-1", {"COUNT": 0}, {"STATUS": ("A", "B")})
    carrier = build_carrier_view("occ-1", "C_EXACT_v1", before_after())
    relation = build_relation("occ-1", "owner-1", "2021-12-31T23:45:00Z", carrier, operation)
    path = build_factorised_path("owner-1", [relation], "2022-01-01T00:00:00Z")
    assert path.relations == (relation,)
    with pytest.raises(MechanicsError, match="ANTECEDENT_AVAILABILITY_LEAK"):
        build_factorised_path("owner-1", [relation], "2021-12-31T23:45:00Z")


def test_population_manifest_reconciles_complete_denominators_without_survivor_drop():
    applicability = {
        "MICRO_BEARING": 5,
        "NO_MICRO": 2,
        "SEGMENT_HEAD_UNASSIGNABLE": 1,
        "CENSORED": 1,
        "NOT_EVALUABLE": 1,
    }
    manifest = build_population_manifest(
        owner_transition_opportunities=10,
        applicability=applicability,
        micro_factor_occurrences=12,
        micro_factorised_paths=5,
        grammar_evaluation_opportunities=4,
        dependence_clusters=3,
        evaluation_cohorts={"2022Q1": 4},
    )
    assert manifest.representation_views == 4 * len(DECLARED_REPRESENTATIONS)
    assert sum(dict(manifest.micro_path_applicability).values()) == 10
    with pytest.raises(MechanicsError, match="POPULATION_INCOMPLETE"):
        build_population_manifest(
            owner_transition_opportunities=10,
            applicability={"MICRO_BEARING": 5},
            micro_factor_occurrences=0,
            micro_factorised_paths=0,
            grammar_evaluation_opportunities=0,
            dependence_clusters=0,
            evaluation_cohorts={},
        )


def test_training_frontier_is_static_and_strictly_prequential():
    frontier = build_training_frontier(
        "2022Q1",
        "2022-01-01T00:00:00Z",
        "2022-04-01T00:00:00Z",
        [("train-2", "2021-06-01T00:00:00Z"), ("train-1", "2021-01-01T00:15:00Z")],
        [("eval-1", "2022-01-01T00:15:00Z")],
    )
    assert frontier.training_end_exclusive_utc == frontier.evaluation_start_utc
    assert frontier.static_within_cohort is True
    assert frontier.training_event_ids == ("train-1", "train-2")
    with pytest.raises(MechanicsError, match="TRAINING_FRONTIER_LEAK"):
        build_training_frontier(
            "2022Q1", "2022-01-01T00:00:00Z", "2022-04-01T00:00:00Z",
            [("late", "2022-01-01T00:00:00Z")], [],
        )


def test_complete_declared_set_reduces_exact_intersection_and_union_minus_intersection():
    trace_set = build_trace_set(qualified_records(), "SYNTHETIC.GENERATION.v1")
    core, shell, state = reduce_trace_set(trace_set)
    assert trace_set.complete is True
    assert core.members == ("T.A",)
    assert shell.members == ("T.B", "T.C", "T.D")
    assert state.antecedent_support_min == 3
    assert state.robust_core_size == 1
    assert state.ambiguity_shell_size == 3
    assert state.scope == "DECLARED_REPRESENTATION_SET"
    assert not hasattr(state, "confidence")
    assert dict(shell.provenance)["T.B"] == ("BASE",)


def test_incomplete_declared_set_is_not_evaluable_and_preserves_available_traces():
    trace_set = build_trace_set(qualified_records()[:-1], "SYNTHETIC.GENERATION.v1")
    core, shell, state = reduce_trace_set(trace_set)
    assert trace_set.complete is False
    assert len(trace_set.traces) == 4
    assert core.members == () and shell.members == ()
    assert state.status == "CORE_NOT_EVALUABLE_REPRESENTATION_SET_INCOMPLETE"


def test_derivation_manifest_changes_when_any_dependency_changes():
    records = qualified_records()
    trace_set = build_trace_set(records, "SYNTHETIC.GENERATION.v1")
    core, _, _ = reduce_trace_set(trace_set)
    first = build_derivation_manifest(
        "RobustContinuationFrontier", core.frontier_id,
        {"protocol": "p1", "trace_set": trace_set.trace_set_id},
    )
    second = build_derivation_manifest(
        "RobustContinuationFrontier", core.frontier_id,
        {"protocol": "p2", "trace_set": trace_set.trace_set_id},
    )
    assert first.manifest_id != second.manifest_id


def test_constitution_decoder_and_canonical_identity_are_frozen_and_float_free():
    constitution = factorisation_constitution()
    decoder = decoder_manifest(["vector-b", "vector-a"])
    assert constitution.carrier_fields == CARRIER_FIELDS
    assert decoder.fixed_test_vector_ids == ("vector-a", "vector-b")
    assert canonical_bytes({"a": [1, True]}) == canonical_bytes({"a": [1, True]})
    with pytest.raises(MechanicsError, match="NON_CANONICAL_FLOAT"):
        canonical_bytes({"confidence": 0.5})


def test_programme_pointer_advances_without_granting_scientific_authority():
    pointer = load("registries/implementation/c2s_sptoi_v0_1/CURRENT_STATE_POINTER.json")
    state = load(pointer["current_state"])
    gate = load("docs/programmes/c2s-sptoi-v0-1/wp6/C2S_SPTOI_G6_RICH_MECH_DELEGATED_DECISION_v0_1.json")
    assert pointer["current_packet"] == "C2S-SPTOI-WP6"
    assert pointer["next_packet"] == "C2S-SPTOI-WP7"
    assert state["protected_source_access"] == "NONE"
    assert state["factorised_evidence_execution"] == "DENIED"
    assert state["validation"] == "LOCKED_UNCONSUMED"
    assert gate["decision"] == "PASS_SOURCE_FREE_MECHANICS"
    assert gate["authority_effect"] == "NONE_MECHANICAL_QUALIFICATION_ONLY"


def test_wp6_authority_and_dependency_frontier_identities_are_exact():
    authority = load(
        "docs/programmes/c2s-sptoi-v0-1/wp6/C2S_SPTOI_WP6_AUTHORITY_MANIFEST_v0_1.json"
    )
    frontier = load(
        "docs/programmes/c2s-sptoi-v0-1/wp6/C2S_SPTOI_WP6_DEPENDENCY_FRONTIER_v0_1.json"
    )
    canonical = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(canonical(authority["authority_manifest"])).hexdigest() == authority["authority_manifest_id"]
    body = copy.deepcopy(frontier)
    identity = body.pop("dependency_frontier_id")
    assert hashlib.sha256(canonical(body)).hexdigest() == identity
