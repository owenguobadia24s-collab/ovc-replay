from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from ovc.shared_systems.foundation import (
    PILOT_HARD_FLOOR_DIMENSIONS,
    SECURITY_FACTORS,
    SecurityRequest,
    decide_security,
)
from ovc.shared_systems.resolution import ResolutionManifest, SharedExecutionContext
from ovc.shared_systems.terminal import (
    CONSUMERS,
    TERMINAL_STATE,
    GovernedCorpusEquivalence,
    IntegratedReplayRecord,
    OperationalBurdenEntry,
    PilotConsumerBinding,
    SharedTerminalError,
    TerminalProgrammeRecord,
    build_adoption_decision,
    build_integrated_pilot_matrix,
    build_terminal_read_model,
    evaluate_terminal_budget,
)


ROOT = Path(__file__).resolve().parents[2]
BUDGET_PATH = ROOT / (
    "registries/implementation/shared_systems_v0_1/"
    "SHSI_PILOT_ACCEPTANCE_BUDGET_v0_1.json"
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def binding(consumer: str, ordinal: int) -> PilotConsumerBinding:
    manifest = ResolutionManifest(
        f"SHSI-WP10-REQUEST-{ordinal}", "RESOLVED", (),
        "OVC-SHARED-SYSTEMS-v0.1", "SHSI-WP9-ESL-SHADOW-v0.1",
        "OVC-SHARED-SYSTEMS-v0.1", "SHSI-REGISTRY-v0.1",
        f"ovc://shared-systems/consumer/{ordinal}/v0.1", None, (),
        "SHSI-WP10-QUALIFICATION-v0.1", f"SHSI-WP10-BINDING-{ordinal}",
        "SHSI-AE-v0.2-R1", "SHSI-REFERENCE-ENV-v0.1",
    )
    context = SharedExecutionContext.freeze(f"SHSI-WP10-CONTEXT-{ordinal}", manifest)
    return PilotConsumerBinding(
        consumer, manifest, context, f"SHSI-WP{ordinal + 6}-SHADOW-PACKET-v0.1"
    )


def equivalence(consumer: str, corpus_class: str) -> GovernedCorpusEquivalence:
    return GovernedCorpusEquivalence(
        f"SHSI-WP10-EQUIV-{consumer}", consumer,
        f"corpus:{consumer}", corpus_class, "SHSI-WP10-RUN-SPEC-v0.1",
        "a" * 64, "a" * 64, "PASS",
    )


def test_integrated_matrix_contains_exactly_three_shadow_consumers() -> None:
    rows = tuple(binding(consumer, index) for index, consumer in enumerate(sorted(CONSUMERS), 1))
    matrix = build_integrated_pilot_matrix("SHSI-WP10-MATRIX-v0.1", rows)
    assert matrix.status == "PASS"
    assert {row.consumer_programme_id for row in matrix.bindings} == CONSUMERS
    assert all(not row.current_execution_binding_changed for row in matrix.bindings)
    with pytest.raises(SharedTerminalError, match="CUTOVER_OR_AUTHORITY"):
        replace(rows[0], current_execution_binding_changed=True)


def test_integrated_replay_is_restart_reshard_and_cold_resolution_exact() -> None:
    replay = IntegratedReplayRecord(
        "SHSI-WP10-REPLAY-v0.1", *("b" * 64 for _ in range(5)), "PASS"
    )
    assert replay.status == "PASS"
    with pytest.raises(SharedTerminalError, match="REPLAY_STATUS"):
        replace(replay, reshard_logical_sha256="c" * 64)


def test_governed_equivalence_informs_but_never_authorizes_adoption() -> None:
    dsai = equivalence("OVC-DSAI-v0.1", "GOVERNED_HISTORICAL")
    ready = build_adoption_decision(
        "SHSI-WP10-ADOPT-DSAI", dsai.consumer_programme_id,
        equivalence=dsai, evidence_refs=(dsai.equivalence_id,),
        rollback_ref="SHSI-WP10-ROLLBACK-DSAI",
    )
    assert ready.disposition == "EVIDENCE_ONLY_READY_FOR_OPERATOR_REVIEW"
    assert ready.operator_review_required and not ready.current_execution_binding_changed
    dmrp = equivalence("OVC-EC1-DMRP-CONFORMANCE-v0.1", "SYNTHETIC_ONLY")
    deferred = build_adoption_decision(
        "SHSI-WP10-ADOPT-DMRP", dmrp.consumer_programme_id,
        equivalence=dmrp, evidence_refs=(dmrp.equivalence_id,),
        rollback_ref="SHSI-WP10-ROLLBACK-DMRP",
    )
    assert deferred.disposition == "DEFER"
    with pytest.raises(SharedTerminalError, match="ADOPTION_DISPOSITION"):
        replace(deferred, disposition="CUTOVER")


def test_all_budget_dimensions_and_zero_tolerance_floors_pass_or_defer() -> None:
    budget = load(BUDGET_PATH)["pilot_acceptance_budget"]
    observed = {row[0]: 0.0 for row in budget["numeric_caps"]}
    floors = {name: 0 for name in PILOT_HARD_FLOOR_DIMENSIONS}
    result = evaluate_terminal_budget(
        "SHSI-WP10-BUDGET-RESULT-v0.1", budget["budget_id"],
        budget=budget, observed_dimensions=observed, hard_floor_observations=floors,
    )
    assert result.disposition == "PASS"
    assert len(result.observed_dimensions) == 18
    assert len(result.hard_floor_observations) == 9
    failed = evaluate_terminal_budget(
        "SHSI-WP10-BUDGET-RESULT-BAD", budget["budget_id"], budget=budget,
        observed_dimensions=observed,
        hard_floor_observations={**floors, "AUTHORITY_SECURITY_FALSE_ALLOWS": 1},
    )
    assert failed.disposition == "DEFER_OR_DO_NOT_MIGRATE"
    assert failed.violated_hard_floors == ("AUTHORITY_SECURITY_FALSE_ALLOWS",)


def test_operational_burden_and_protected_security_remain_bounded() -> None:
    entries = tuple(
        OperationalBurdenEntry(consumer, 0, 0, 0.0, 0.0, 0)
        for consumer in sorted(CONSUMERS)
    )
    assert sum(row.adapter_count for row in entries) == 0
    request = SecurityRequest(
        "SHSI-WP10-SECURITY", "PILOT", "VALIDATION.PROTECTED", "CAP.READ",
        "PERMISSION.READ", "AUTHORITY.NONE", "SCOPE.SHADOW", "POLICY.DENY", "VALIDATION",
    )
    factors = {name: True for name in SECURITY_FACTORS}
    factors["runtime_policy_allows"] = False
    decision = decide_security(
        "SHSI-WP10-DENY", request, factor_results=factors,
        dsai_decision_ref="DSAI-WP10-DENY",
    )
    assert decision.status == "DENY" and not decision.metadata_revealed


def test_terminal_record_and_console_projection_are_non_cutover() -> None:
    record = TerminalProgrammeRecord(
        "SHSI-WP10-TERMINAL-v0.1", "SHSI-WP10-MATRIX-v0.1",
        "SHSI-WP10-BUDGET-RESULT-v0.1",
        ("ADOPT.DSAI", "ADOPT.DMRP", "ADOPT.ESL"), (), (), (), (),
        False, TERMINAL_STATE, "COMPLETED",
    )
    projection = build_terminal_read_model(record)
    assert projection["terminal_state"] == TERMINAL_STATE
    assert projection["console_authority"] == "READ_ONLY"
    assert projection["mutation_routes"] == []
    assert projection["adoption_authority"] == "OPERATOR_REQUIRED_SEPARATE_GATE"
    with pytest.raises(SharedTerminalError, match="TERMINAL_STATE_INCONSISTENT"):
        replace(record, unresolved_incidents=("INCIDENT",))


def test_wp10_schema_declares_terminal_object_set() -> None:
    schema = load(ROOT / "schemas/shared_systems/terminal_shadow_conformance_v0_1.schema.json")
    assert {
        "PilotConsumerBinding", "IntegratedPilotMatrix", "GovernedCorpusEquivalence",
        "IntegratedReplayRecord", "PilotAcceptanceResult", "OperationalBurdenEntry",
        "ConsumerAdoptionDecision", "TerminalProgrammeRecord",
    } <= set(schema["$defs"])
