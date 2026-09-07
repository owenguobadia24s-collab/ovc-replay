"""Deterministic, source-free mechanics for C2S-SPTOI factorised grammar.

This module materialises the mechanical contracts frozen by
OVC-EML-GRAMMAR-0002-RP-0.1-R1.  It deliberately does not load protected
source, infer C2 semantics, execute a scientific search, or expose a scalar
confidence.  Concrete C0C-derived packs remain qualification fixtures only.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence


PROTOCOL_ID = "OVC-EML-GRAMMAR-0002-RP-0.1-R1"
PROTOCOL_SHA256 = "a4eaaa43d051628e6fc6da4151ed9500f68a832d85240188cdf0f656a1893fd5"
STUDY_GENERATION_ID = "OVC-EML-GRAMMAR-0002-DEVELOPMENT-2021_2023-G1-R1"
MECHANICS_MATURITY = "SOURCE_FREE_QUALIFICATION"
C0C_PACK_MATURITY = "C0C_CONFORMANCE_FIXTURE_ONLY"

CARRIER_FIELDS = (
    "ENV_STATUS",
    "ENV_LIFECYCLE",
    "ENV_RELATION",
    "ETR_ATOMIC",
    "ETR_COMPOUND",
    "ETR_OPEN_STATE",
)
CARRIER_PACKS = {
    "C_EXACT_v1": (),
    "R25_HI_v1": ("ETR_COMPOUND",),
    "R25_MID_v1": ("ETR_ATOMIC", "ETR_COMPOUND"),
    "C_BROAD_v1": CARRIER_FIELDS,
}
ANTECEDENT_HIERARCHIES = {
    "BASE": ("EXACT", "HI", "MID", "PATH", "OP"),
    "NO_HI": ("EXACT", "MID", "PATH", "OP"),
    "NO_MID": ("EXACT", "HI", "PATH", "OP"),
    "PATH_BEFORE_MID": ("EXACT", "HI", "PATH", "MID", "OP"),
    "NO_PATH": ("EXACT", "HI", "MID", "OP"),
}
DECLARED_REPRESENTATION_SET_ID = "REPSET_FG_CORE_v1"
DECLARED_REPRESENTATIONS = tuple(ANTECEDENT_HIERARCHIES)
TARGET_PACKS = ("T0_v1", "T1_v1", "R18_MID_v1", "ETR_v1", "T2_v1", "T3_v1")
TARGET_HIERARCHIES = {
    "BASE": TARGET_PACKS,
    "NO_T1": ("T0_v1", "R18_MID_v1", "ETR_v1", "T2_v1", "T3_v1"),
    "NO_MID": ("T0_v1", "T1_v1", "ETR_v1", "T2_v1", "T3_v1"),
    "NO_ETR": ("T0_v1", "T1_v1", "R18_MID_v1", "T2_v1", "T3_v1"),
    "COMPACT": ("T0_v1", "R18_MID_v1", "T2_v1", "T3_v1"),
}
COMPARISON_TARGET_PACK_ID = "R18_MID_v1"
PRIMARY_SUPPORT_MIN = 2
RELATION_SUPPORT_MIN = 2
SUPPORT_SENSITIVITIES = (3, 5)
MICRO_APPLICABILITY_STATES = (
    "MICRO_BEARING",
    "NO_MICRO",
    "SEGMENT_HEAD_UNASSIGNABLE",
    "CENSORED",
    "NOT_EVALUABLE",
)
POPULATION_UNITS = (
    "OwnerTransitionOpportunity",
    "MicroPathApplicability",
    "MicroFactorOccurrence",
    "MicroFactorisedPath",
    "GrammarEvaluationOpportunity",
    "RepresentationView",
    "DependenceCluster",
)


class MechanicsError(ValueError):
    """A typed, fail-closed mechanical qualification failure."""

    def __init__(self, reason_code: str, detail: str):
        super().__init__(f"{reason_code}: {detail}")
        self.reason_code = reason_code
        self.detail = detail


def _normalise(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return {
            "$contract": value.__class__.__name__,
            "fields": {field.name: _normalise(getattr(value, field.name)) for field in dataclasses.fields(value)},
        }
    if isinstance(value, Mapping):
        return {"$map": [[str(key), _normalise(value[key])] for key in sorted(value, key=str)]}
    if isinstance(value, tuple):
        return {"$tuple": [_normalise(item) for item in value]}
    if isinstance(value, list):
        return {"$list": [_normalise(item) for item in value]}
    if isinstance(value, (set, frozenset)):
        items = [_normalise(item) for item in value]
        items.sort(key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))
        return {"$set": items}
    if isinstance(value, bool) or value is None or isinstance(value, (int, str)):
        return value
    if isinstance(value, float):
        raise MechanicsError("NON_CANONICAL_FLOAT", "floating-point values are forbidden in mechanical identities")
    raise MechanicsError("UNSUPPORTED_CANONICAL_TYPE", repr(type(value)))


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        _normalise(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def content_id(contract: str, value: Any) -> str:
    return hashlib.sha256(contract.encode("utf-8") + b"\n" + canonical_bytes(value)).hexdigest()


def representation_morphology_id(pack_id: str, value: Any) -> str:
    return content_id(f"RepresentationMorphologyID:{pack_id}", value)


def _parse_utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MechanicsError("INVALID_FVT", value) from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise MechanicsError("INVALID_FVT", "timestamps must be UTC and timezone-aware")
    return parsed


@dataclass(frozen=True)
class MomentConfigurationRef:
    moment_id: str
    owner_snapshot_id: str
    owner_generation_id: str
    first_valid_time_utc: str
    effective_time_utc: str


@dataclass(frozen=True)
class StateFormBundle:
    bundle_id: str
    moment_ref: MomentConfigurationRef
    target_forms: tuple[tuple[str, str], ...]
    source_role: str = "OWNER_PRIMARY_STATE_TARGET_SPINE"


@dataclass(frozen=True)
class MicroOperationRepresentationPack:
    pack_id: str
    count_role_domain: tuple[int, int, int]
    enum_role_domain: tuple[str, str]
    boundary_referents_excluded: bool
    maturity: str = C0C_PACK_MATURITY


@dataclass(frozen=True)
class MicroOperationView:
    occurrence_id: str
    pack_id: str
    count_roles: tuple[tuple[str, int], ...]
    enum_roles: tuple[tuple[str, str], ...]
    operation_morphology_id: str


@dataclass(frozen=True)
class MicroCarrierRepresentationPack:
    pack_id: str
    exact_fields: tuple[str, ...]
    coarse_fields: tuple[str, ...]
    omitted_fields: tuple[str, ...]
    maturity: str = C0C_PACK_MATURITY


@dataclass(frozen=True)
class MicroCarrierContextView:
    occurrence_id: str
    pack_id: str
    values: tuple[tuple[str, str], ...]
    carrier_morphology_id: str


@dataclass(frozen=True)
class CarrierOperationRelation:
    occurrence_id: str
    owner_interval_id: str
    first_valid_time_utc: str
    carrier_view: MicroCarrierContextView | None
    operation_view: MicroOperationView
    relation_id: str


@dataclass(frozen=True)
class MicroFactorisedPath:
    owner_interval_id: str
    relations: tuple[CarrierOperationRelation, ...]
    path_id: str


@dataclass(frozen=True)
class GrammarEvidencePopulationManifest:
    owner_transition_opportunities: int
    micro_path_applicability: tuple[tuple[str, int], ...]
    micro_factor_occurrences: int
    micro_factorised_paths: int
    grammar_evaluation_opportunities: int
    representation_views: int
    dependence_clusters: int
    evaluation_cohorts: tuple[tuple[str, int], ...]
    manifest_id: str


@dataclass(frozen=True)
class GrammarEvidenceTrainingFrontierManifest:
    cohort_id: str
    training_start_utc: str
    training_end_exclusive_utc: str
    evaluation_start_utc: str
    evaluation_end_exclusive_utc: str
    training_event_ids: tuple[str, ...]
    evaluation_event_ids: tuple[str, ...]
    static_within_cohort: bool
    frontier_id: str


@dataclass(frozen=True)
class MicroFactorisationConstitution:
    protocol_id: str
    carrier_fields: tuple[str, ...]
    operation_count_domain: tuple[int, int, int]
    operation_enum_domain: tuple[str, str]
    boundary_referents_excluded: bool
    missing_policy: str
    constitution_id: str


@dataclass(frozen=True)
class CarrierDecoderManifest:
    protocol_id: str
    decoder_version: str
    unchanged_rule: str
    changed_rule: str
    fixed_test_vector_ids: tuple[str, ...]
    decoder_id: str


@dataclass(frozen=True)
class FrontierComparisonTargetPackManifest:
    target_pack_id: str
    projection_rule: str
    target_hierarchy_ids: tuple[str, ...]
    manifest_id: str


@dataclass(frozen=True)
class ContinuationFrontierEvidenceRecord:
    representation_id: str
    comparison_target_pack_id: str
    antecedent_support: int
    selected_backoff_level: str | None
    selected_target_resolution: str | None
    target_supports: tuple[tuple[str, int], ...]
    opportunity_denominator: int
    training_frontier_id: str
    support_min: int
    relation_min: int
    evaluability: str
    record_id: str


@dataclass(frozen=True)
class GrammarRepresentationTrace:
    representation_id: str
    frontier_record: ContinuationFrontierEvidenceRecord
    source_generation_id: str
    cutoff_safe: bool
    trace_id: str


@dataclass(frozen=True)
class GrammarRepresentationTraceSet:
    representation_set_id: str
    traces: tuple[GrammarRepresentationTrace, ...]
    complete: bool
    trace_set_id: str


@dataclass(frozen=True)
class RobustContinuationFrontier:
    representation_set_id: str
    comparison_target_pack_id: str
    members: tuple[str, ...]
    status: str
    frontier_id: str


@dataclass(frozen=True)
class RepresentationAmbiguityShell:
    representation_set_id: str
    comparison_target_pack_id: str
    members: tuple[str, ...]
    provenance: tuple[tuple[str, tuple[str, ...]], ...]
    status: str
    shell_id: str


@dataclass(frozen=True)
class GrammarEvidenceStateCore:
    antecedent_support_min: int | None
    backoff_level_set: tuple[str, ...]
    robust_core_size: int
    ambiguity_shell_size: int
    target_resolution_set: tuple[str, ...]
    scope: str
    status: str
    state_core_id: str


@dataclass(frozen=True)
class GrammarEvidenceDerivationManifest:
    output_contract: str
    output_id: str
    dependencies: tuple[tuple[str, str], ...]
    dependency_closure_complete: bool
    manifest_id: str


def operation_pack() -> MicroOperationRepresentationPack:
    return MicroOperationRepresentationPack(
        pack_id="O_RELATION_v1",
        count_role_domain=(-1, 0, 1),
        enum_role_domain=("CHANGED", "UNCHANGED"),
        boundary_referents_excluded=True,
    )


def carrier_pack(pack_id: str) -> MicroCarrierRepresentationPack:
    if pack_id not in CARRIER_PACKS:
        raise MechanicsError("UNKNOWN_CARRIER_PACK", pack_id)
    coarse = tuple(CARRIER_PACKS[pack_id])
    omitted = CARRIER_FIELDS if pack_id == "C_BROAD_v1" else ()
    exact = () if omitted else tuple(field for field in CARRIER_FIELDS if field not in coarse)
    return MicroCarrierRepresentationPack(pack_id, exact, () if omitted else coarse, tuple(omitted))


def build_operation_view(
    occurrence_id: str,
    count_roles: Mapping[str, int],
    enum_before_after: Mapping[str, tuple[str, str]],
    *,
    boundary_roles: Iterable[str] = (),
) -> MicroOperationView:
    if tuple(boundary_roles):
        raise MechanicsError("BOUNDARY_REFERENT_EXCLUDED", "boundary roles cannot enter first-generation Operation")
    if any(value not in (-1, 0, 1) for value in count_roles.values()):
        raise MechanicsError("INVALID_COUNT_ROLE", "Operation count roles are exactly {-1,0,+1}")
    enum_roles = tuple(
        sorted((name, "UNCHANGED" if before == after else "CHANGED") for name, (before, after) in enum_before_after.items())
    )
    counts = tuple(sorted((name, int(value)) for name, value in count_roles.items()))
    value = (counts, enum_roles)
    return MicroOperationView(
        occurrence_id=occurrence_id,
        pack_id=operation_pack().pack_id,
        count_roles=counts,
        enum_roles=enum_roles,
        operation_morphology_id=representation_morphology_id(operation_pack().pack_id, value),
    )


def build_carrier_view(
    occurrence_id: str,
    pack_id: str,
    before_after: Mapping[str, tuple[str, str]],
) -> MicroCarrierContextView | None:
    pack = carrier_pack(pack_id)
    if pack.omitted_fields:
        return None
    if set(before_after) != set(CARRIER_FIELDS):
        missing = sorted(set(CARRIER_FIELDS) - set(before_after))
        extra = sorted(set(before_after) - set(CARRIER_FIELDS))
        raise MechanicsError("FACTORISATION_DECODER_AMBIGUOUS", f"missing={missing}; extra={extra}")
    values = []
    for field in CARRIER_FIELDS:
        before, after = before_after[field]
        if not before or not after:
            raise MechanicsError("FACTORISATION_DECODER_AMBIGUOUS", f"empty enum at {field}")
        if field in pack.coarse_fields:
            value = "UNCHANGED" if before == after else "CHANGED"
        else:
            value = before if before == after else "CHANGED"
        values.append((field, value))
    frozen = tuple(values)
    return MicroCarrierContextView(
        occurrence_id=occurrence_id,
        pack_id=pack_id,
        values=frozen,
        carrier_morphology_id=representation_morphology_id(pack_id, frozen),
    )


def build_relation(
    occurrence_id: str,
    owner_interval_id: str,
    first_valid_time_utc: str,
    carrier_view: MicroCarrierContextView | None,
    operation_view: MicroOperationView,
) -> CarrierOperationRelation:
    _parse_utc(first_valid_time_utc)
    if operation_view.occurrence_id != occurrence_id or (
        carrier_view is not None and carrier_view.occurrence_id != occurrence_id
    ):
        raise MechanicsError("OCCURRENCE_ID_MISMATCH", occurrence_id)
    body = (occurrence_id, owner_interval_id, first_valid_time_utc, carrier_view, operation_view)
    return CarrierOperationRelation(
        occurrence_id,
        owner_interval_id,
        first_valid_time_utc,
        carrier_view,
        operation_view,
        content_id("CarrierOperationRelation/v1", body),
    )


def build_factorised_path(
    owner_interval_id: str,
    relations: Sequence[CarrierOperationRelation],
    target_first_valid_time_utc: str,
) -> MicroFactorisedPath:
    target_fvt = _parse_utc(target_first_valid_time_utc)
    ordered = tuple(relations)
    if any(relation.owner_interval_id != owner_interval_id for relation in ordered):
        raise MechanicsError("CROSS_INTERVAL_PATH", owner_interval_id)
    fvts = tuple(_parse_utc(relation.first_valid_time_utc) for relation in ordered)
    if fvts != tuple(sorted(fvts)):
        raise MechanicsError("NON_CANONICAL_PATH_ORDER", owner_interval_id)
    if any(fvt >= target_fvt for fvt in fvts):
        raise MechanicsError("ANTECEDENT_AVAILABILITY_LEAK", owner_interval_id)
    return MicroFactorisedPath(
        owner_interval_id,
        ordered,
        content_id("MicroFactorisedPath/v1", (owner_interval_id, ordered)),
    )


def build_population_manifest(
    *,
    owner_transition_opportunities: int,
    applicability: Mapping[str, int],
    micro_factor_occurrences: int,
    micro_factorised_paths: int,
    grammar_evaluation_opportunities: int,
    dependence_clusters: int,
    evaluation_cohorts: Mapping[str, int],
) -> GrammarEvidencePopulationManifest:
    if set(applicability) != set(MICRO_APPLICABILITY_STATES):
        raise MechanicsError("POPULATION_INCOMPLETE", "all MicroPathApplicability states are required")
    counts = tuple(sorted((key, int(value)) for key, value in applicability.items()))
    if any(value < 0 for _, value in counts) or sum(value for _, value in counts) != owner_transition_opportunities:
        raise MechanicsError("POPULATION_INCOMPLETE", "applicability must reconcile every owner transition")
    if grammar_evaluation_opportunities > dict(counts)["MICRO_BEARING"]:
        raise MechanicsError("POPULATION_INCOMPLETE", "evaluation opportunities exceed micro-bearing opportunities")
    representation_views = grammar_evaluation_opportunities * len(DECLARED_REPRESENTATIONS)
    cohorts = tuple(sorted((key, int(value)) for key, value in evaluation_cohorts.items()))
    body = (
        owner_transition_opportunities, counts, micro_factor_occurrences, micro_factorised_paths,
        grammar_evaluation_opportunities, representation_views, dependence_clusters, cohorts,
    )
    return GrammarEvidencePopulationManifest(*body, content_id("GrammarEvidencePopulationManifest/v1", body))


def build_training_frontier(
    cohort_id: str,
    evaluation_start_utc: str,
    evaluation_end_exclusive_utc: str,
    training_events: Sequence[tuple[str, str]],
    evaluation_events: Sequence[tuple[str, str]],
) -> GrammarEvidenceTrainingFrontierManifest:
    eval_start = _parse_utc(evaluation_start_utc)
    eval_end = _parse_utc(evaluation_end_exclusive_utc)
    if eval_start >= eval_end:
        raise MechanicsError("TRAINING_FRONTIER_LEAK", "empty or inverted evaluation cohort")
    train_sorted = tuple(sorted(training_events, key=lambda item: (item[1], item[0])))
    eval_sorted = tuple(sorted(evaluation_events, key=lambda item: (item[1], item[0])))
    if any(_parse_utc(fvt) >= eval_start for _, fvt in train_sorted):
        raise MechanicsError("TRAINING_FRONTIER_LEAK", cohort_id)
    if any(not (eval_start <= _parse_utc(fvt) < eval_end) for _, fvt in eval_sorted):
        raise MechanicsError("TRAINING_FRONTIER_LEAK", f"evaluation event outside {cohort_id}")
    training_start = train_sorted[0][1] if train_sorted else evaluation_start_utc
    body = (
        cohort_id, training_start, evaluation_start_utc, evaluation_start_utc,
        evaluation_end_exclusive_utc, tuple(event_id for event_id, _ in train_sorted),
        tuple(event_id for event_id, _ in eval_sorted), True,
    )
    return GrammarEvidenceTrainingFrontierManifest(
        *body, content_id("GrammarEvidenceTrainingFrontierManifest/v1", body)
    )


def factorisation_constitution() -> MicroFactorisationConstitution:
    body = (
        PROTOCOL_ID, CARRIER_FIELDS, (-1, 0, 1), ("CHANGED", "UNCHANGED"), True,
        "NOT_EVALUABLE_NEVER_ZERO_OR_UNCHANGED_DEFAULT",
    )
    return MicroFactorisationConstitution(*body, content_id("MicroFactorisationConstitution/v1", body))


def decoder_manifest(test_vector_ids: Sequence[str]) -> CarrierDecoderManifest:
    vectors = tuple(sorted(test_vector_ids))
    if not vectors:
        raise MechanicsError("DECODER_TEST_VECTORS_MISSING", "at least one fixed vector is required")
    body = (
        PROTOCOL_ID, "CARRIER_DECODER_v1", "RETAIN_EXACT_BEFORE_VALUE",
        "CANONICAL_CHANGED_SENTINEL", vectors,
    )
    return CarrierDecoderManifest(*body, content_id("CarrierDecoderManifest/v1", body))


def comparison_target_manifest() -> FrontierComparisonTargetPackManifest:
    body = (
        COMPARISON_TARGET_PACK_ID,
        "PROJECT_EVERY_VIEW_TO_CANONICAL_R18_MID_ALPHABET_BEFORE_SET_REDUCTION",
        tuple(TARGET_HIERARCHIES),
    )
    return FrontierComparisonTargetPackManifest(*body, content_id("FrontierComparisonTargetPackManifest/v1", body))


def build_frontier_record(
    *,
    representation_id: str,
    antecedent_support: int,
    selected_backoff_level: str | None,
    selected_target_resolution: str | None,
    target_supports: Mapping[str, int],
    opportunity_denominator: int,
    training_frontier_id: str,
    support_min: int = PRIMARY_SUPPORT_MIN,
    relation_min: int = RELATION_SUPPORT_MIN,
) -> ContinuationFrontierEvidenceRecord:
    if representation_id not in DECLARED_REPRESENTATIONS:
        raise MechanicsError("UNDECLARED_REPRESENTATION", representation_id)
    if support_min not in (PRIMARY_SUPPORT_MIN, *SUPPORT_SENSITIVITIES):
        raise MechanicsError("UNDECLARED_SUPPORT_POLICY", str(support_min))
    supports = tuple(sorted((target, int(count)) for target, count in target_supports.items()))
    evaluability = "EVALUABLE" if antecedent_support >= support_min else "ABSTAIN_INSUFFICIENT_SUPPORT"
    if evaluability == "EVALUABLE" and selected_backoff_level not in ANTECEDENT_HIERARCHIES[representation_id]:
        raise MechanicsError("INVALID_BACKOFF_LEVEL", repr(selected_backoff_level))
    if selected_target_resolution is not None and selected_target_resolution not in TARGET_PACKS:
        raise MechanicsError("INVALID_TARGET_RESOLUTION", selected_target_resolution)
    body = (
        representation_id, COMPARISON_TARGET_PACK_ID, int(antecedent_support), selected_backoff_level,
        selected_target_resolution, supports, int(opportunity_denominator), training_frontier_id,
        int(support_min), int(relation_min), evaluability,
    )
    return ContinuationFrontierEvidenceRecord(*body, content_id("ContinuationFrontierEvidenceRecord/v1", body))


def select_antecedent_backoff(
    hierarchy_id: str,
    supports_by_level: Mapping[str, int],
    support_min: int = PRIMARY_SUPPORT_MIN,
) -> tuple[str | None, int]:
    """Select the first recurrence-qualified level in one frozen hierarchy."""
    if hierarchy_id not in ANTECEDENT_HIERARCHIES:
        raise MechanicsError("UNKNOWN_ANTECEDENT_HIERARCHY", hierarchy_id)
    if support_min not in (PRIMARY_SUPPORT_MIN, *SUPPORT_SENSITIVITIES):
        raise MechanicsError("UNDECLARED_SUPPORT_POLICY", str(support_min))
    if any(not isinstance(count, int) or count < 0 for count in supports_by_level.values()):
        raise MechanicsError("INVALID_SUPPORT_MAP", "support counts must be non-negative integers")
    for level in ANTECEDENT_HIERARCHIES[hierarchy_id]:
        support = int(supports_by_level.get(level, 0))
        if support >= support_min:
            return level, support
    return None, max((int(supports_by_level.get(level, 0)) for level in ANTECEDENT_HIERARCHIES[hierarchy_id]), default=0)


def select_target_resolution(
    hierarchy_id: str,
    relation_supports_by_pack: Mapping[str, int],
    relation_min: int = RELATION_SUPPORT_MIN,
) -> tuple[str | None, int]:
    """Select the richest relation-qualified target in one frozen hierarchy."""
    if hierarchy_id not in TARGET_HIERARCHIES:
        raise MechanicsError("UNKNOWN_TARGET_HIERARCHY", hierarchy_id)
    if relation_min < 1:
        raise MechanicsError("INVALID_RELATION_SUPPORT_MIN", str(relation_min))
    if any(not isinstance(count, int) or count < 0 for count in relation_supports_by_pack.values()):
        raise MechanicsError("INVALID_SUPPORT_MAP", "relation counts must be non-negative integers")
    for pack_id in TARGET_HIERARCHIES[hierarchy_id]:
        support = int(relation_supports_by_pack.get(pack_id, 0))
        if support >= relation_min:
            return pack_id, support
    return None, max((int(relation_supports_by_pack.get(pack_id, 0)) for pack_id in TARGET_HIERARCHIES[hierarchy_id]), default=0)


def project_frontier_to_comparison_target(
    source_pack_id: str,
    target_supports: Mapping[str, int],
    projection: Mapping[str, str] | None = None,
) -> tuple[tuple[str, int], ...]:
    """Project and aggregate a support map on the one frozen comparison alphabet."""
    if source_pack_id not in TARGET_PACKS:
        raise MechanicsError("UNKNOWN_TARGET_PACK", source_pack_id)
    if any(not isinstance(count, int) or count < 0 for count in target_supports.values()):
        raise MechanicsError("INVALID_SUPPORT_MAP", "target supports must be non-negative integers")
    if source_pack_id == COMPARISON_TARGET_PACK_ID:
        mapping = {target_id: target_id for target_id in target_supports}
    else:
        if projection is None or set(projection) != set(target_supports):
            raise MechanicsError("COMPARISON_TARGET_PACK_MISSING", source_pack_id)
        mapping = projection
    aggregated: Counter[str] = Counter()
    for target_id, count in target_supports.items():
        comparison_id = mapping[target_id]
        if not comparison_id:
            raise MechanicsError("COMPARISON_TARGET_PACK_MISSING", target_id)
        aggregated[comparison_id] += int(count)
    return tuple(sorted(aggregated.items()))


def build_trace_set(
    records: Sequence[ContinuationFrontierEvidenceRecord], source_generation_id: str
) -> GrammarRepresentationTraceSet:
    by_id = {record.representation_id: record for record in records}
    if len(by_id) != len(records):
        raise MechanicsError("REPRESENTATION_SET_INCOMPLETE", "duplicate representation trace")
    complete = set(by_id) == set(DECLARED_REPRESENTATIONS)
    traces = []
    for representation_id in DECLARED_REPRESENTATIONS:
        if representation_id not in by_id:
            continue
        record = by_id[representation_id]
        body = (representation_id, record, source_generation_id, True)
        traces.append(GrammarRepresentationTrace(*body, content_id("GrammarRepresentationTrace/v1", body)))
    frozen = tuple(traces)
    body = (DECLARED_REPRESENTATION_SET_ID, frozen, complete)
    return GrammarRepresentationTraceSet(*body, content_id("GrammarRepresentationTraceSet/v1", body))


def reduce_trace_set(
    trace_set: GrammarRepresentationTraceSet,
) -> tuple[RobustContinuationFrontier, RepresentationAmbiguityShell, GrammarEvidenceStateCore]:
    if not trace_set.complete or tuple(trace.representation_id for trace in trace_set.traces) != DECLARED_REPRESENTATIONS:
        status = "CORE_NOT_EVALUABLE_REPRESENTATION_SET_INCOMPLETE"
        core_body = (DECLARED_REPRESENTATION_SET_ID, COMPARISON_TARGET_PACK_ID, (), status)
        core = RobustContinuationFrontier(*core_body, content_id("RobustContinuationFrontier/v1", core_body))
        shell_body = (DECLARED_REPRESENTATION_SET_ID, COMPARISON_TARGET_PACK_ID, (), (), status)
        shell = RepresentationAmbiguityShell(*shell_body, content_id("RepresentationAmbiguityShell/v1", shell_body))
        state_body = (None, (), 0, 0, (), "DECLARED_REPRESENTATION_SET", status)
        state = GrammarEvidenceStateCore(*state_body, content_id("GrammarEvidenceStateCore/v1", state_body))
        return core, shell, state
    if any(trace.frontier_record.evaluability != "EVALUABLE" for trace in trace_set.traces):
        raise MechanicsError("CORE_NOT_EVALUABLE", "every declared view must be recurrence-qualified")
    per_view = {
        trace.representation_id: {
            target for target, count in trace.frontier_record.target_supports
            if count >= trace.frontier_record.relation_min
        }
        for trace in trace_set.traces
    }
    sets = list(per_view.values())
    intersection = set(sets[0])
    union = set()
    for members in sets:
        intersection &= members
        union |= members
    shell_members = union - intersection
    core_values = tuple(sorted(intersection))
    shell_values = tuple(sorted(shell_members))
    provenance = tuple(
        (target, tuple(rep for rep in DECLARED_REPRESENTATIONS if target in per_view[rep]))
        for target in shell_values
    )
    status = "QUALIFIED_SOURCE_FREE_MECHANICS"
    core_body = (DECLARED_REPRESENTATION_SET_ID, COMPARISON_TARGET_PACK_ID, core_values, status)
    core = RobustContinuationFrontier(*core_body, content_id("RobustContinuationFrontier/v1", core_body))
    shell_body = (DECLARED_REPRESENTATION_SET_ID, COMPARISON_TARGET_PACK_ID, shell_values, provenance, status)
    shell = RepresentationAmbiguityShell(*shell_body, content_id("RepresentationAmbiguityShell/v1", shell_body))
    state_body = (
        min(trace.frontier_record.antecedent_support for trace in trace_set.traces),
        tuple(sorted({trace.frontier_record.selected_backoff_level for trace in trace_set.traces if trace.frontier_record.selected_backoff_level})),
        len(core_values), len(shell_values),
        tuple(sorted({trace.frontier_record.selected_target_resolution for trace in trace_set.traces if trace.frontier_record.selected_target_resolution})),
        "DECLARED_REPRESENTATION_SET", status,
    )
    state = GrammarEvidenceStateCore(*state_body, content_id("GrammarEvidenceStateCore/v1", state_body))
    return core, shell, state


def build_derivation_manifest(
    output_contract: str,
    output_id: str,
    dependencies: Mapping[str, str],
) -> GrammarEvidenceDerivationManifest:
    if not dependencies or any(not name or not identity for name, identity in dependencies.items()):
        raise MechanicsError("DERIVATION_DEPENDENCY_INCOMPLETE", output_contract)
    frozen = tuple(sorted(dependencies.items()))
    body = (output_contract, output_id, frozen, True)
    return GrammarEvidenceDerivationManifest(*body, content_id("GrammarEvidenceDerivationManifest/v1", body))


def contract_registry() -> dict[str, Any]:
    """Return the complete frozen WP6 registry without activating science."""
    carrier = {pack_id: dataclasses.asdict(carrier_pack(pack_id)) for pack_id in CARRIER_PACKS}
    registry = {
        "schema": "ovc-c2s-sptoi-factorised-mechanics-registry/v0.1",
        "protocol_id": PROTOCOL_ID,
        "protocol_sha256": PROTOCOL_SHA256,
        "study_generation_id": STUDY_GENERATION_ID,
        "maturity": MECHANICS_MATURITY,
        "c0c_pack_maturity": C0C_PACK_MATURITY,
        "operation_pack": dataclasses.asdict(operation_pack()),
        "carrier_packs": carrier,
        "antecedent_hierarchies": {key: list(value) for key, value in ANTECEDENT_HIERARCHIES.items()},
        "declared_representation_set": {
            "id": DECLARED_REPRESENTATION_SET_ID,
            "members": list(DECLARED_REPRESENTATIONS),
            "scope": "DECLARED_REPRESENTATION_SET",
        },
        "target_packs": list(TARGET_PACKS),
        "target_hierarchies": {key: list(value) for key, value in TARGET_HIERARCHIES.items()},
        "comparison_target_pack": dataclasses.asdict(comparison_target_manifest()),
        "support_policy": {"primary": 2, "relation": 2, "sensitivities": [3, 5], "support_1": "DESCRIPTIVE_ONLY"},
        "population_units": list(POPULATION_UNITS),
        "micro_applicability_states": list(MICRO_APPLICABILITY_STATES),
        "protected_source_access": "NONE",
        "factorised_evidence_execution": "DENIED",
        "validation": "LOCKED_UNCONSUMED",
        "scalar_confidence": "FORBIDDEN",
        "authority_effect": "NONE_MECHANICAL_QUALIFICATION_ONLY",
    }
    # Registry identity is computed over the JSON-domain value that is filed,
    # not over Python tuple implementation details.
    registry = json.loads(json.dumps(registry, sort_keys=True))
    registry["registry_id"] = content_id("FactorisedMechanicsRegistry/v1", registry)
    return registry


def synthetic_qualification_fixture() -> dict[str, Any]:
    """Build the immutable, source-free WP6 truth fixture and replay outputs."""
    before_after = {
        "ENV_STATUS": ("OPEN", "OPEN"),
        "ENV_LIFECYCLE": ("FORMING", "MATURE"),
        "ENV_RELATION": ("INSIDE", "INSIDE"),
        "ETR_ATOMIC": ("UP", "DOWN"),
        "ETR_COMPOUND": ("EXPAND", "EXPAND"),
        "ETR_OPEN_STATE": ("OPEN", "CLOSED"),
    }
    operation = build_operation_view(
        "SYNTH.OCC.1", {"LEVEL_COUNT": 1, "RELATION_COUNT": -1},
        {"ENV_STATUS": ("OPEN", "OPEN"), "ETR_OPEN_STATE": ("OPEN", "CLOSED")},
    )
    carrier_views = {
        pack_id: build_carrier_view("SYNTH.OCC.1", pack_id, before_after)
        for pack_id in CARRIER_PACKS
    }
    relation = build_relation(
        "SYNTH.OCC.1", "SYNTH.OWNER.INTERVAL.1", "2021-12-31T23:45:00Z",
        carrier_views["C_EXACT_v1"], operation,
    )
    path = build_factorised_path(
        "SYNTH.OWNER.INTERVAL.1", [relation], "2022-01-01T00:00:00Z"
    )
    population = build_population_manifest(
        owner_transition_opportunities=5,
        applicability={
            "MICRO_BEARING": 2, "NO_MICRO": 1, "SEGMENT_HEAD_UNASSIGNABLE": 1,
            "CENSORED": 1, "NOT_EVALUABLE": 0,
        },
        micro_factor_occurrences=2,
        micro_factorised_paths=2,
        grammar_evaluation_opportunities=1,
        dependence_clusters=1,
        evaluation_cohorts={"2022Q1": 1},
    )
    frontier = build_training_frontier(
        "2022Q1", "2022-01-01T00:00:00Z", "2022-04-01T00:00:00Z",
        [("SYNTH.TRAIN.1", "2021-06-01T00:00:00Z"), ("SYNTH.TRAIN.2", "2021-12-31T23:45:00Z")],
        [("SYNTH.EVAL.1", "2022-01-01T00:15:00Z")],
    )
    target_supports = {
        "BASE": {"SYNTH.TARGET.A": 3, "SYNTH.TARGET.B": 2},
        "NO_HI": {"SYNTH.TARGET.A": 4, "SYNTH.TARGET.C": 2},
        "NO_MID": {"SYNTH.TARGET.A": 2, "SYNTH.TARGET.B": 1},
        "PATH_BEFORE_MID": {"SYNTH.TARGET.A": 5, "SYNTH.TARGET.C": 1},
        "NO_PATH": {"SYNTH.TARGET.A": 2, "SYNTH.TARGET.D": 2},
    }
    records = tuple(
        build_frontier_record(
            representation_id=representation_id,
            antecedent_support=3,
            selected_backoff_level=ANTECEDENT_HIERARCHIES[representation_id][0],
            selected_target_resolution=COMPARISON_TARGET_PACK_ID,
            target_supports=target_supports[representation_id],
            opportunity_denominator=2,
            training_frontier_id=frontier.frontier_id,
        )
        for representation_id in DECLARED_REPRESENTATIONS
    )
    trace_set = build_trace_set(records, "SYNTHETIC.WP6.GENERATION.v1")
    core, shell, state = reduce_trace_set(trace_set)
    derivation = build_derivation_manifest(
        "GrammarEvidenceStateCore", state.state_core_id,
        {
            "protocol": PROTOCOL_SHA256,
            "registry": contract_registry()["registry_id"],
            "population": population.manifest_id,
            "training_frontier": frontier.frontier_id,
            "trace_set": trace_set.trace_set_id,
            "robust_frontier": core.frontier_id,
            "ambiguity_shell": shell.shell_id,
        },
    )
    value = {
        "schema": "ovc-c2s-sptoi-factorised-mechanics-synthetic-fixture/v0.1",
        "fixture_id": "C2S-SPTOI-WP6-SYNTHETIC-TRUTH-v1",
        "maturity": "SYNTHETIC_QUALIFICATION_ONLY",
        "source_generation_id": "SYNTHETIC.WP6.GENERATION.v1",
        "operation_view": dataclasses.asdict(operation),
        "carrier_views": {
            pack_id: None if view is None else dataclasses.asdict(view)
            for pack_id, view in carrier_views.items()
        },
        "factorised_path": dataclasses.asdict(path),
        "population_manifest": dataclasses.asdict(population),
        "training_frontier_manifest": dataclasses.asdict(frontier),
        "factorisation_constitution": dataclasses.asdict(factorisation_constitution()),
        "decoder_manifest": dataclasses.asdict(decoder_manifest([operation.operation_morphology_id])),
        "comparison_target_manifest": dataclasses.asdict(comparison_target_manifest()),
        "frontier_records": [dataclasses.asdict(record) for record in records],
        "trace_set": dataclasses.asdict(trace_set),
        "robust_frontier": dataclasses.asdict(core),
        "ambiguity_shell": dataclasses.asdict(shell),
        "state_core": dataclasses.asdict(state),
        "derivation_manifest": dataclasses.asdict(derivation),
        "realised_continuation_in_prospective_identity": False,
        "protected_source_access": "NONE",
        "authority_effect": "NONE_SYNTHETIC_MECHANICAL_QUALIFICATION_ONLY",
    }
    value = json.loads(json.dumps(value, sort_keys=True))
    value["bundle_id"] = content_id("FactorisedMechanicsSyntheticFixture/v1", value)
    return value
