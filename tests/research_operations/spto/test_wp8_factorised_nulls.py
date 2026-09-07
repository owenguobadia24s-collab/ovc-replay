import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from ovc.research_operations.spto.factorised_mechanics import DECLARED_REPRESENTATIONS, content_id
from ovc.research_operations.spto.factorised_nulls import (
    NULL_SPECS,
    REPLICAS_PER_NULL,
    assess_null_adequacy,
    build_null_qualification_pack,
    derive_representation_bundle,
    synthetic_null_events,
    transform_null_world,
)


ROOT = Path(__file__).resolve().parents[3]
PACK = "docs/programmes/c2s-sptoi-v0-1/wp8/C2S_SPTOI_WP8_FACTORISED_NULL_QUALIFICATION_PACK_v0_1.json"


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_filed_pack_rebuilds_exactly_and_schema_validates():
    filed = load(PACK)
    assert filed == build_null_qualification_pack()
    body = copy.deepcopy(filed)
    identity = body.pop("pack_id")
    assert identity == content_id("FactorisedNullQualificationPack/v1", body)
    jsonschema = pytest.importorskip("jsonschema")
    schema = load("schemas/research_operations/spto/FACTORISED_NULL_QUALIFICATION_PACK_v0_1.schema.json")
    jsonschema.Draft202012Validator(schema).validate(filed)


def test_exact_six_null_families_and_replica_denominators_are_retained():
    pack = load(PACK)
    assert set(NULL_SPECS) == {"FG-NC", "FG-NO", "FG-NORD", "FG-NCORE", "FG-NFO", "FG-NBROAD"}
    assert Counter(row["null_id"] for row in pack["replicas"]) == {null_id: 128 for null_id in NULL_SPECS}
    assert pack["primary_replica_count"] == 640
    assert pack["sensitivity_replica_count"] == 128
    assert pack["total_replica_count"] == 768


@pytest.mark.parametrize("null_id", sorted(NULL_SPECS))
def test_every_null_preserves_fixed_population_targets_chronology_and_path_lengths(null_id):
    source = synthetic_null_events()
    world = transform_null_world(null_id, 7, source)
    bundle = derive_representation_bundle(world)
    assessment = assess_null_adequacy(null_id, source, world, bundle)
    assert assessment["event_membership_preserved"] is True
    assert assessment["targets_preserved"] is True
    assert assessment["chronology_and_break_strata_preserved"] is True
    assert assessment["path_length_schedule_preserved"] is True
    assert assessment["adequate"] is True


def test_one_world_derives_complete_declared_set_per_replica():
    world = transform_null_world("FG-NCORE", 11, synthetic_null_events())
    bundle = derive_representation_bundle(world)
    assert bundle["source_world_id"] == world["source_world_id"]
    assert bundle["representation_set"] == list(DECLARED_REPRESENTATIONS)
    assert [row[0] for row in bundle["view_ids"]] == list(DECLARED_REPRESENTATIONS)
    assert len({row[1] for row in bundle["view_ids"]}) == len(DECLARED_REPRESENTATIONS)


def test_order_null_preserves_exact_within_interval_multiset():
    source = synthetic_null_events()
    world = transform_null_world("FG-NORD", 12, source)
    by_id = {event["event_id"]: event for event in world["events"]}
    for event in source:
        original = Counter(json.dumps(row, sort_keys=True) for row in event["path"])
        transformed = Counter(json.dumps(row, sort_keys=True) for row in by_id[event["event_id"]]["path"])
        assert original == transformed


def test_seed_and_world_id_are_deterministic_and_replica_specific():
    source = synthetic_null_events()
    first = transform_null_world("FG-NC", 1, source)
    repeat = transform_null_world("FG-NC", 1, source)
    other = transform_null_world("FG-NC", 2, source)
    assert first == repeat
    assert first["seed_hex"] != other["seed_hex"]
    assert first["source_world_id"] != other["source_world_id"]


def test_inadequate_world_makes_claim_not_evaluable_without_substitution():
    source = synthetic_null_events()
    world = transform_null_world("FG-NC", 0, source)
    world["events"].pop()
    bundle = derive_representation_bundle(world)
    assessment = assess_null_adequacy("FG-NC", source, world, bundle)
    assert assessment["adequate"] is False
    assert assessment["failure_disposition"] == "AFFECTED_CLAIM_NOT_EVALUABLE_NO_SUBSTITUTION"


def test_pointer_advances_to_diagnostics_without_real_source_authority():
    pointer = load("registries/implementation/c2s_sptoi_v0_1/CURRENT_STATE_POINTER.json")
    state = load(pointer["current_state"])
    gate = load("docs/programmes/c2s-sptoi-v0-1/wp8/C2S_SPTOI_G8_NULL_ALG_DELEGATED_DECISION_v0_1.json")
    assert pointer["current_packet"] == "C2S-SPTOI-WP8"
    assert pointer["next_packet"] == "C2S-SPTOI-WP9"
    assert state["protected_source_access"] == "NONE"
    assert state["factorised_evidence_execution"] == "DENIED"
    assert gate["decision"] == "PASS_SOURCE_FREE_NULL_QUALIFICATION"


def test_wp8_authority_and_dependency_frontier_identities_are_exact():
    authority = load("docs/programmes/c2s-sptoi-v0-1/wp8/C2S_SPTOI_WP8_AUTHORITY_MANIFEST_v0_1.json")
    frontier = load("docs/programmes/c2s-sptoi-v0-1/wp8/C2S_SPTOI_WP8_DEPENDENCY_FRONTIER_v0_1.json")
    canonical = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(canonical(authority["authority_manifest"])).hexdigest() == authority["authority_manifest_id"]
    body = copy.deepcopy(frontier)
    identity = body.pop("dependency_frontier_id")
    assert hashlib.sha256(canonical(body)).hexdigest() == identity
