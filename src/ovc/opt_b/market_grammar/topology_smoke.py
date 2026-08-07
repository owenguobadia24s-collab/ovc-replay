"""MG-WP8 deterministic full-component topology smoke.

Inactive, noncanonical SHADOW_EXPERIMENT only. The only mocked market boundary is the
bounded revised-C2 fixture declared by the WP8 fixture pack. All downstream operations
use the real MG-WP2..WP7 component implementations and frozen comparison registries.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
import json
from typing import Mapping, Sequence

from .clock_alignment import ClockProfile, ContextStatus, build_alignment_ledger
from .episode_ledger import C2LedgerInput, build_episode_ledger
from .family_hierarchy import SensitivityPack, StructuralRecord, build_hierarchy, build_sensitivity_result
from .family_variants import VariantAssignmentStatus, build_variant_ledger
from .typed_grammar import compile_grammar, parse_grammar

AUTHORITY_STATE = "SHADOW_EXPERIMENT"
SCHEMA = "ovc-mg-wp8-topology-smoke-result/v1"
MAX_RUNTIME_SECONDS = 14_400
MAX_RETAINED_BYTES = 10 * 1024 * 1024 * 1024
FEATURES = ("interaction", "location", "motion", "organisation", "quality")
ALLOWED_FIXTURE_FIELDS = frozenset({
    "schema", "authority", "programme_id", "packet_id", "mocked_boundaries",
    "build_cutoff", "candidate_migration_ledger_sha256", "pack_ids", "runtime_metadata",
    "c2_records", "state_structural_features", "clock_parents", "clock_children",
    "grammar_transition", "parse_child_record_id",
})
FORBIDDEN_TOKENS = ("outcome", "future_path", "future_price", "return", "mfe", "mae", "probability", "risk", "exposure", "execution", "trade")


def _canon(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: object) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _logical_fixture(fixture: Mapping[str, object]) -> dict[str, object]:
    keys = set(fixture)
    unknown = sorted(keys - ALLOWED_FIXTURE_FIELDS)
    if unknown:
        raise ValueError("unsupported WP8 fixture fields: " + ", ".join(unknown))
    for key in keys:
        lowered = key.lower()
        if any(token in lowered for token in FORBIDDEN_TOKENS):
            raise ValueError("future/outcome/exposure fixture field is forbidden: " + key)
    logical = {key: deepcopy(value) for key, value in fixture.items() if key != "runtime_metadata"}
    if logical.get("authority") != "SYNTHETIC_NON_AUTHORITATIVE":
        raise ValueError("WP8 market fixture must remain SYNTHETIC_NON_AUTHORITATIVE")
    if logical.get("packet_id") != "MG-WP8":
        raise ValueError("WP8 fixture packet_id mismatch")
    return logical


def _verify_migration_ledger(ledger: Mapping[str, object], expected_sha256: str) -> None:
    supplied = str(ledger.get("ledger_sha256", ""))
    if supplied != expected_sha256:
        raise ValueError("candidate migration ledger SHA-256 binding mismatch")
    unhashed = dict(ledger)
    unhashed.pop("ledger_sha256", None)
    if _hash(unhashed) != supplied:
        raise ValueError("candidate migration ledger self-hash mismatch")
    if ledger.get("candidate_count") != 14 or len(ledger.get("migration_records", [])) != 14:
        raise ValueError("WP8 requires all fourteen candidate migration records")
    allowed = {"MAPPED", "SUPERSEDED", "QUARANTINED", "UNRESOLVED"}
    counts = dict(ledger.get("migration_status_counts", {}))
    if any(status not in allowed for status in counts):
        raise ValueError("candidate migration ledger contains unsupported disposition")
    if sum(int(value) for value in counts.values()) != 14:
        raise ValueError("candidate migration disposition count must equal fourteen")
    if ledger.get("canonical") is not False or ledger.get("promotion_authority") != "NONE":
        raise ValueError("candidate migration ledger may not carry promotion authority")


def _selected_packs(registry: Mapping[str, object], pack_ids: Sequence[str]) -> tuple[SensitivityPack, ...]:
    if registry.get("canonical_pack_id") is not None or registry.get("comparison_only") is not True:
        raise ValueError("sensitivity registry must remain comparison-only and noncanonical")
    by_id = {str(item["pack_id"]): item for item in registry.get("packs", [])}
    if tuple(pack_ids) != ("MG-C2G-S-0.20-v0.1", "MG-C2G-S-0.35-v0.1"):
        raise ValueError("WP8 is frozen to the existing 0.20 and 0.35 comparison packs")
    selected = []
    for pack_id in pack_ids:
        if pack_id not in by_id:
            raise ValueError("unknown sensitivity pack: " + pack_id)
        if by_id[pack_id].get("canonical") is not False:
            raise ValueError("WP8 sensitivity packs must be noncanonical")
        selected.append(SensitivityPack.from_mapping(by_id[pack_id]))
    return tuple(selected)


def _state_records(c2_records: Sequence[C2LedgerInput], feature_map: Mapping[str, object]) -> tuple[StructuralRecord, ...]:
    values = []
    for record in c2_records:
        raw = dict(feature_map.get(record.record_id, {}))
        if set(raw) != set(FEATURES):
            raise ValueError("state structural projection must provide exactly five structural features")
        values.append(StructuralRecord(
            record_id=record.record_id,
            record_type="STATE",
            source_release_id=record.source_release_id,
            instrument_id=record.instrument_id,
            side=record.side,
            scope_id=record.scope_id,
            clock_id=record.clock_id,
            first_valid_time=record.first_valid_time,
            source_sha256=record.source_sha256,
            structural_features=raw,
        ))
    return tuple(values)


def _transition_records(episode_ledger, state_by_id: Mapping[str, StructuralRecord]) -> tuple[StructuralRecord, ...]:
    values = []
    for index, episode in enumerate(episode_ledger.episodes):
        if len(episode.member_record_ids) < 2:
            continue
        left = state_by_id[episode.member_record_ids[0]]
        right = state_by_id[episode.member_record_ids[-1]]
        features = {key: abs(right.structural_features[key] - left.structural_features[key]) for key in FEATURES}
        payload = {"episode_id": episode.episode_id, "left": left.record_id, "right": right.record_id, "features": {key: str(value) for key, value in features.items()}}
        values.append(StructuralRecord(
            record_id=f"WP8.TRANSITION.{index + 1}",
            record_type="TRANSITION",
            source_release_id=left.source_release_id,
            instrument_id=left.instrument_id,
            side=left.side,
            scope_id=left.scope_id,
            clock_id=left.clock_id,
            first_valid_time=right.first_valid_time,
            source_sha256=_hash(payload),
            structural_features=features,
        ))
    if len(values) < 2:
        raise ValueError("topology smoke requires at least two transition records")
    return tuple(values)


def _episode_records(episode_ledger, state_by_id: Mapping[str, StructuralRecord]) -> tuple[StructuralRecord, ...]:
    values = []
    for episode in episode_ledger.episodes:
        members = [state_by_id[item] for item in episode.member_record_ids]
        if not members:
            raise ValueError("episode has no state members")
        features = {key: sum((item.structural_features[key] for item in members), Decimal("0")) / Decimal(len(members)) for key in FEATURES}
        values.append(StructuralRecord(
            record_id=episode.episode_id,
            record_type="EPISODE",
            source_release_id=episode.source_release_id,
            instrument_id=episode.instrument_id,
            side=episode.side,
            scope_id=episode.scope_id,
            clock_id=episode.clock_id,
            first_valid_time=episode.end_first_valid_time,
            source_sha256=_hash(episode.to_dict()),
            structural_features=features,
        ))
    if len(values) < 2:
        raise ValueError("topology smoke requires at least two episode records")
    return tuple(values)


def _grammar_release(family_id: str, variant_id: str | None, transition: Mapping[str, object]):
    transition_from = str(transition["from"])
    transition_to = str(transition["to"])
    object_binding = str(transition["object_binding"])
    release_id = "MG.C2P.GRAMMAR.WP8." + _hash({"episode_family_id": family_id, "episode_variant_id": variant_id, "transition": dict(transition)})[:24]
    layers = {
        "context": {"operator":"CONTEXT_AVAILABILITY","input_type":"CONTEXT","output_type":"PREDICATE","domain":"CONTEXT","required_fields":[],"children":[],"parameters":{"required_state":"AVAILABLE"}},
        "location": None,
        "condition": None,
        "episode_phase": {"operator":"RUN_LENGTH","input_type":"PREDICATE","output_type":"PREDICATE","domain":"SEQUENCE","required_fields":[],"children":[{"operator":"CONTEXT_AVAILABILITY","input_type":"CONTEXT","output_type":"PREDICATE","domain":"CONTEXT","required_fields":[],"children":[],"parameters":{"required_state":"AVAILABLE"}}],"parameters":{"min":1,"max":8}},
        "event": None,
        "response": None,
        "transition": {"operator":"RELATION_TRANSITION","input_type":"RELATION_TRANSITION","output_type":"PREDICATE","domain":"INTERACTION","required_fields":["transition_evidence"],"children":[],"parameters":{"from":transition_from,"to":transition_to,"object_binding":object_binding}},
        "possible_resolution": None,
    }
    base = {"grammar_release_id": release_id, "layers": layers, "invalidating_conditions":["RESET_BOUNDARY"], "canonical":False, "published":False, "authority_state":AUTHORITY_STATE}
    release = {**base, "release_sha256": _hash(base)}
    return compile_grammar(release)


def _assignment_hash(*results) -> str:
    surface = []
    for result in results:
        surface.append({"result_id": result.result_id, "families":[item.to_dict() for item in result.families], "assignments":[item.to_dict() for item in result.assignments]})
    return _hash(surface)


def run_topology_smoke(fixture: Mapping[str, object], sensitivity_registry: Mapping[str, object], migration_ledger: Mapping[str, object]) -> dict[str, object]:
    logical = _logical_fixture(fixture)
    expected_migration_sha = str(logical["candidate_migration_ledger_sha256"])
    _verify_migration_ledger(migration_ledger, expected_migration_sha)
    packs = _selected_packs(sensitivity_registry, tuple(map(str, logical["pack_ids"])))
    input_sha256 = _hash({"fixture": logical, "selected_packs":[pack.to_dict() for pack in packs], "candidate_migration_ledger_sha256": expected_migration_sha})

    c2_values = tuple(C2LedgerInput.from_mapping(item) for item in logical["c2_records"])
    episode_ledger = build_episode_ledger(c2_values, build_cutoff=str(logical["build_cutoff"]))
    if not episode_ledger.episodes or any(item.status.value != "COMPLETED" for item in episode_ledger.episodes):
        raise ValueError("WP8 fixture must produce completed C2E episodes")

    state_records = _state_records(c2_values, logical["state_structural_features"])
    state_by_id = {item.record_id: item for item in state_records}
    transition_records = _transition_records(episode_ledger, state_by_id)
    episode_records = _episode_records(episode_ledger, state_by_id)

    state_result = build_sensitivity_result(state_records, packs[0], build_cutoff=str(logical["build_cutoff"]))
    transition_result = build_sensitivity_result(transition_records, packs[0], build_cutoff=str(logical["build_cutoff"]))
    episode_results = tuple(build_sensitivity_result(episode_records, pack, build_cutoff=str(logical["build_cutoff"])) for pack in packs)
    hierarchy = build_hierarchy(episode_results)
    variants = build_variant_ledger(episode_results[0], episode_records)
    if not state_result.families or not transition_result.families or not episode_results[0].families or not variants.variants:
        raise ValueError("real C2G components failed to produce the required topology")

    alignment = build_alignment_ledger(logical["clock_children"], logical["clock_parents"], ClockProfile())
    resolutions = {item.child_record_id: item for item in alignment.resolutions}
    missing = resolutions.get("WP8.CHILD.NO_PARENT")
    if missing is None or missing.status is not ContextStatus.UNAVAILABLE:
        raise ValueError("WP8 requires an explicit UNAVAILABLE missing-context example")
    parse_resolution = resolutions[str(logical["parse_child_record_id"])]
    if parse_resolution.status is not ContextStatus.AVAILABLE:
        raise ValueError("WP8 parse path requires AVAILABLE exact parent context")

    first_episode = episode_records[0]
    assignments = {item.record_id: item for item in episode_results[0].assignments}
    primary_assignment = assignments[first_episode.record_id]
    if primary_assignment.primary_family_id is None:
        raise ValueError("episode grammar seed requires an assigned episode family")
    explanations = {item.record_id: item for item in variants.explanations}
    explanation = explanations[first_episode.record_id]
    if explanation.status not in {VariantAssignmentStatus.VARIANT_ASSIGNED, VariantAssignmentStatus.VARIANT_AMBIGUOUS}:
        raise ValueError("episode grammar seed requires a stable or ambiguous declared variant")
    variant_distance = None
    if explanation.variant_id is not None:
        for variant_id, distance in explanation.candidate_variant_distances:
            if variant_id == explanation.variant_id:
                variant_distance = distance
                break

    grammar = _grammar_release(primary_assignment.primary_family_id, explanation.variant_id, logical["grammar_transition"])
    completed_phase_ids = [phase.phase_id for episode in episode_ledger.episodes for phase in episode.phases]
    parse_evidence = {
        "fields": {"transition_evidence": True},
        "context_status": parse_resolution.status.value,
        "transitions": [dict(logical["grammar_transition"])],
        "observations": [{"phase_present": True} for _ in completed_phase_ids],
        "nearest_family_id": primary_assignment.primary_family_id,
        "nearest_variant_id": explanation.variant_id,
        "family_distance": primary_assignment.nearest_distance,
        "variant_distance": variant_distance,
        "current_phases": [completed_phase_ids[-1]],
        "completed_phases": completed_phase_ids[:-1],
        "lawful_next_phases": ["SMOKE_TERMINAL"],
        "missing_evidence": [],
        "conflicting_evidence": [],
        "invalidation_reasons": [],
        "upstream_lineage": [episode_ledger.ledger_id, state_result.result_id, transition_result.result_id, episode_results[0].result_id, hierarchy.hierarchy_id, variants.ledger_id, alignment.ledger_id, expected_migration_sha],
    }
    parse_result = parse_grammar(grammar, parse_evidence)
    if parse_result.status.value != "GRAMMAR_MATCH":
        raise ValueError("WP8 integrated parse did not reach GRAMMAR_MATCH")

    structural_assignment_sha256 = _assignment_hash(state_result, transition_result, *episode_results)
    provenance_diagnostic_sha256 = _hash({
        "structural_assignment_sha256": structural_assignment_sha256,
        "c2_source_sha256": sorted(item.source_sha256 for item in c2_values),
        "migration_source_artifacts": migration_ledger.get("source_artifacts", {}),
    })
    if provenance_diagnostic_sha256 == structural_assignment_sha256:
        raise ValueError("provenance diagnostic surface must remain separately identified")

    candidate_ids = sorted(str(item["rule_candidate_id"]) for item in migration_ledger["migration_records"])
    projection = {
        "projection_id": "MG.WP8.READONLY." + _hash({"parse_id":parse_result.parse_id,"candidate_ids":candidate_ids})[:24],
        "authority_state": AUTHORITY_STATE,
        "canonical": False,
        "mutation_controls": False,
        "episode_ledger_id": episode_ledger.ledger_id,
        "state_family_result_id": state_result.result_id,
        "transition_family_result_id": transition_result.result_id,
        "episode_family_result_ids": [item.result_id for item in episode_results],
        "hierarchy_id": hierarchy.hierarchy_id,
        "variant_ledger_id": variants.ledger_id,
        "alignment_ledger_id": alignment.ledger_id,
        "grammar_release_id": grammar.grammar_release_id,
        "parse_id": parse_result.parse_id,
        "candidate_migration_ledger_sha256": expected_migration_sha,
    }
    result = {
        "schema": SCHEMA,
        "programme_id": logical["programme_id"],
        "packet_id": "MG-WP8",
        "authority": "INACTIVE_NONCANONICAL_SHADOW_EXPERIMENT_IMPLEMENTATION_ONLY",
        "canonical": False,
        "published": False,
        "input_sha256": input_sha256,
        "mocked_boundaries": logical["mocked_boundaries"],
        "component_counts": {
            "c2_records": len(c2_values),
            "episodes": len(episode_ledger.episodes),
            "state_families": len(state_result.families),
            "transition_families": len(transition_result.families),
            "episode_families_by_pack": [len(item.families) for item in episode_results],
            "hierarchy_edges": len(hierarchy.edges),
            "variants": len(variants.variants),
            "candidate_migrations": len(candidate_ids),
        },
        "component_ids": {
            "episode_ledger_id": episode_ledger.ledger_id,
            "state_result_id": state_result.result_id,
            "transition_result_id": transition_result.result_id,
            "episode_result_ids": [item.result_id for item in episode_results],
            "hierarchy_id": hierarchy.hierarchy_id,
            "variant_ledger_id": variants.ledger_id,
            "alignment_ledger_id": alignment.ledger_id,
        },
        "context_status_counts": {status.value: sum(1 for item in alignment.resolutions if item.status is status) for status in ContextStatus},
        "missing_context_resolution": missing.to_dict(),
        "sensitivity_comparison": {
            "pack_ids": [pack.pack_id for pack in packs],
            "canonical_pack_id": None,
            "hierarchy": hierarchy.to_dict(),
            "episode_variant_ledger": variants.to_dict(),
        },
        "candidate_migration": {
            "ledger_sha256": expected_migration_sha,
            "candidate_ids": candidate_ids,
            "migration_status_counts": migration_ledger["migration_status_counts"],
            "promotion_authority": "NONE",
        },
        "provenance_ablation": {
            "structural_assignment_sha256": structural_assignment_sha256,
            "provenance_inclusive_diagnostic_sha256": provenance_diagnostic_sha256,
            "structural_assignments_include_provenance": False,
            "diagnostic_only": True,
        },
        "grammar_release": grammar.to_dict(),
        "parse_result": parse_result.to_dict(),
        "read_only_projection": projection,
        "capacity": {
            "max_runtime_seconds": MAX_RUNTIME_SECONDS,
            "max_retained_bytes": MAX_RETAINED_BYTES,
            "runtime_measurement": "QA_ONLY_EXCLUDED_FROM_CANONICAL_IDENTITY",
        },
    }
    result["capacity"]["retained_payload_bytes_before_result_hash"] = len(_canon(result).encode("utf-8"))
    if result["capacity"]["retained_payload_bytes_before_result_hash"] >= MAX_RETAINED_BYTES:
        raise ValueError("CAPACITY_EXCEEDED: retained output exceeds 10 GiB")
    result["result_sha256"] = _hash(result)
    return result


def make_checkpoint(result: Mapping[str, object]) -> dict[str, object]:
    return {
        "schema": "ovc-mg-wp8-checkpoint/v1",
        "packet_id": "MG-WP8",
        "input_sha256": result["input_sha256"],
        "result_sha256": result["result_sha256"],
        "authority": "CHECKPOINT_BINDING_ONLY",
    }


def resume_topology_smoke(fixture: Mapping[str, object], sensitivity_registry: Mapping[str, object], migration_ledger: Mapping[str, object], checkpoint: Mapping[str, object]) -> dict[str, object]:
    if checkpoint.get("schema") != "ovc-mg-wp8-checkpoint/v1" or checkpoint.get("packet_id") != "MG-WP8":
        raise ValueError("invalid WP8 checkpoint")
    result = run_topology_smoke(fixture, sensitivity_registry, migration_ledger)
    if checkpoint.get("input_sha256") != result["input_sha256"]:
        raise ValueError("checkpoint input SHA-256 mismatch")
    if checkpoint.get("result_sha256") != result["result_sha256"]:
        raise ValueError("checkpoint result SHA-256 mismatch")
    return result
