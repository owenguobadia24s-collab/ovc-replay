from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .canonical import canonical_sha256
from .dmrp_candidate import assess_candidate_change
from .dmrp_execution import F0InformationLeakError, leak_scan
from .ec1_path1 import EC1CapacityError, EC1Path1InvariantError, EvidenceDependenceGraph, exact_recurring_pattern_lattice


class S0ProtocolBlock(RuntimeError):
    pass


class S0AuthorityBlock(PermissionError):
    pass


class S0ReproductionMismatch(RuntimeError):
    pass


FORBIDDEN_INPUT_CLASSES = frozenset({
    "LEGACY_C2_V2", "C2_VNEXT_FUNCTIONAL_DISCOVERY", "OPT_C", "OPT_D",
    "DEVELOPMENT_OUTCOME", "VALIDATION", "PROBABILITY", "RISK", "EXPOSURE", "EXECUTION",
})


@dataclass(frozen=True)
class S0AuthoritySnapshot:
    authority_ids: tuple[str, ...]
    validation_state: str = "LOCKED_UNCONSUMED"
    real_source_dmrp: str = "NONE"
    real_ro_append: str = "NONE"

    def assert_synthetic_only(self) -> None:
        if self.validation_state != "LOCKED_UNCONSUMED":
            raise S0AuthorityBlock("Validation must remain locked")
        if self.real_source_dmrp != "NONE" or self.real_ro_append != "NONE":
            raise S0AuthorityBlock("S0 cannot consume real-source DMRP or real RO append authority")


def assert_dependency_reachability(input_classes: Iterable[str]) -> None:
    bad = sorted(set(input_classes) & FORBIDDEN_INPUT_CLASSES)
    if bad:
        raise S0ProtocolBlock(f"AV00 forbidden input reachability: {bad}")


def assert_fvt_monotone(required_first_valid_times: Sequence[str], derived_first_valid_time: str) -> None:
    if required_first_valid_times and derived_first_valid_time < max(required_first_valid_times):
        raise S0ProtocolBlock("AV03 derived FVT precedes required evidence")


def assert_context_is_stratifier(*, base_membership_hash: str, context_enriched_membership_hash: str) -> None:
    if base_membership_hash != context_enriched_membership_hash:
        raise S0ProtocolBlock("AV08 OccurrenceContext altered base candidate membership")


def assert_no_posthoc_applicability(*, preregistered_scope_hash: str, reviewed_scope_hash: str) -> None:
    if preregistered_scope_hash != reviewed_scope_hash:
        raise S0ProtocolBlock("AV09 calendar/context concentration changed applicability after observation")


def assert_not_independent_replication(relation: str, claimed_independent: bool) -> None:
    if claimed_independent and relation in {"BID_ASK", "PARENT_CHILD_15M_2H", "OVERLAPPING_OCCURRENCE"}:
        raise S0ProtocolBlock(f"dependent evidence claimed as independent: {relation}")


def cache_key(search_universe_hash: str, parameter_pack_hash: str, stage_hash: str) -> str:
    return canonical_sha256({"search_universe_hash": search_universe_hash, "parameter_pack_hash": parameter_pack_hash, "stage_hash": stage_hash})


def assert_cache_reuse(old_key: str, new_key: str) -> str:
    return "HIT" if old_key == new_key else "MISS"


def assert_source_policy(*, exact_source_available: bool, fallback_requested: bool) -> None:
    if not exact_source_available:
        if fallback_requested:
            raise S0AuthorityBlock("AV19 exact source unavailable; provider/live fallback forbidden")
        raise S0ProtocolBlock("exact source unavailable")


def assert_no_hidden_top_n(config: Mapping[str, Any]) -> None:
    for key in ("top_n", "winner", "best_pattern", "candidate_strength_threshold"):
        value = config.get(key)
        if value not in (None, "NONE", False):
            raise S0ProtocolBlock(f"AV20 hidden selection control: {key}")


def capacity_complete(*, enumerated: int, expected_complete: int) -> None:
    if enumerated != expected_complete:
        raise EC1CapacityError("AV21 PATTERN_LATTICE_CAPACITY_INCOMPLETE")


def classify_upper_layer_need(need_cause: str) -> dict[str, str]:
    if need_cause in {"EC1_FIELD_EXCLUSION", "EC1_METHOD_LIMITATION", "EC1_REVIEW_LIMITATION"}:
        return {"classification": "SELF_INDUCED_OR_METHOD_BOUND", "activation_recommendation": "NONE"}
    return {"classification": need_cause, "activation_recommendation": "OWNER_REVIEW_ONLY"}


def assert_no_shadow_rewrite(original_hash: str, rewritten_hash: str) -> None:
    if original_hash != rewritten_hash:
        raise S0ProtocolBlock("AV23 shadow upper layer attempted to rewrite original evidence/need")


def revalidate_authority(before: S0AuthoritySnapshot, after: S0AuthoritySnapshot) -> None:
    before.assert_synthetic_only(); after.assert_synthetic_only()
    if before != after:
        raise S0AuthorityBlock("AV24 authority snapshot changed; stop at revalidation point")


def assert_f0_not_e1_evidence(evidence_origin: str, target_role: str) -> None:
    if evidence_origin.startswith("F0") and target_role == "E1_SCIENTIFIC_EVIDENCE":
        raise S0ProtocolBlock("AV25 F0 calibration artifact cannot be promoted into E1 evidence")


def shard_semantic_hash(unit_semantic_pairs: Sequence[tuple[str, str]], shards: Sequence[Sequence[str]]) -> str:
    all_units = {unit: semantic for unit, semantic in unit_semantic_pairs}
    assigned = [unit for shard in shards for unit in shard]
    if len(assigned) != len(set(assigned)) or set(assigned) != set(all_units):
        raise S0ProtocolBlock("AV29 shard ownership is incomplete or duplicated")
    return canonical_sha256({unit: all_units[unit] for unit in sorted(all_units)})


def assert_reproduction(expected_hash: str, reproduced_hash: str) -> None:
    if expected_hash != reproduced_hash:
        raise S0ReproductionMismatch("AV30 decision-bearing reproduction mismatch")


def assert_corrupt_cache_handling(cache_integrity: str, action: str) -> None:
    if cache_integrity == "CORRUPT" and action != "QUARANTINE_AND_RECOMPUTE":
        raise S0ProtocolBlock("AV15 corrupt cache/checkpoint not quarantined and recomputed")


def assert_f0_parameter_change(changed_surfaces: set[str]) -> None:
    result = assess_candidate_change(changed_surfaces)
    if result.successor_generation_required is False:
        raise S0ProtocolBlock("AV18 scientific parameter mutation was treated as execution-only")


def assert_no_illegal_representation(search_pack: Mapping[str, Any]) -> None:
    forbidden = {"normalization": {"NONE", None}, "distance": {"NONE", None}, "learned_similarity": {"NONE", None}}
    for field, lawful in forbidden.items():
        if search_pack.get(field) not in lawful:
            raise S0ProtocolBlock(f"AV07 illegal representation transform: {field}")


def assert_boundary_pack_explicit(record: Mapping[str, Any]) -> None:
    if not record.get("c2e_boundary_pack_id") or not record.get("c2e_boundary_pack_sha256"):
        raise S0ProtocolBlock("AV14 C2E morphology evidence lacks exact boundary-pack identity")


def s0_feasibility_assessment(*, identity_dimension_count: int, max_predicate_cardinality: int, synthetic_unit_count: int, enumerated_conjunctions: int, closure_count: int, minimal_generator_count: int) -> dict[str, Any]:
    naive_bound = (2 ** identity_dimension_count) - 1
    status = "PASS" if identity_dimension_count <= 18 and enumerated_conjunctions <= synthetic_unit_count * max(1, naive_bound) else "CAPACITY_INCOMPLETE"
    return {
        "assessment_id": "EC1PatternLatticeFeasibilityAssessment.S0.v1",
        "status": status,
        "identity_predicate_dimensions": identity_dimension_count,
        "maximum_observed_predicate_cardinality_per_unit": max_predicate_cardinality,
        "naive_theoretical_conjunction_bound_per_full_unit": naive_bound,
        "completeness_preserving_pruning": ["DEDUPLICATE_IDENTICAL_CONJUNCTIONS", "SUPPORT_LT_2_AFTER_EXACT_OCCURRENCE_TEST"],
        "synthetic_worst_case": {"unit_count": synthetic_unit_count, "enumerated_conjunctions": enumerated_conjunctions},
        "observed_closure_count": closure_count,
        "observed_minimal_generator_count": minimal_generator_count,
        "projection_model": {
            "F0_A": "MEASURE_THREE_DETERMINISTIC_7_DAY_WINDOWS_ONE_PER_YEAR",
            "F0_B": "SELECT_MONTH_OR_QUARTER_TIER_FROM_BLINDED_F0A_OPERATIONAL_MEASUREMENTS",
            "E1": "PROJECT_FROM_F0B_THEN_FREEZE_EC1_CAPACITY_BUDGET",
        },
        "review_capacity_model": "PROJECT_ALL_PROPOSALS_AND_MINIMAL_GENERATORS_NO_HIDDEN_TOP_N",
        "known_bottlenecks": ["PREDICATE_LATTICE_ENUMERATION", "CLOSURE_AND_MINIMAL_GENERATOR_EXTRACTION", "DEPENDENCE_CLUSTER_MATERIALISATION"],
        "allowed_optimisations": ["EXACT_MEMOIZATION", "DETERMINISTIC_SHARDING", "CHECKPOINT_RESTART", "LOSSLESS_COMPACT_INDEX"],
        "authority_effect": "NONE",
    }


def run_synthetic_reference(units, *, min_support: int = 2):
    return exact_recurring_pattern_lattice(units, min_support=min_support)


def assert_f0_projection_safe(payload: Mapping[str, Any]) -> None:
    try:
        leak_scan(payload)
    except F0InformationLeakError as exc:
        raise S0ProtocolBlock(str(exc)) from exc


def assert_dependence_graph_direct(graph: EvidenceDependenceGraph) -> None:
    if graph.stored_graph_depth != 1:
        raise EC1Path1InvariantError("AV28 dependence graph recursive persistence forbidden")
