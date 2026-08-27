from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from ovc.development.identity import canonical_sha256
from ovc.development.skills.dias import DiasContractError
from ovc.development.skills.dias_shadow import (
    ADVERSARIAL_SAFE_DISPOSITIONS,
    CutoverReadinessAssessment,
    FullShadowRun,
    RetirementCoverageMatrix,
    RetirementFunctionCoverage,
    ShadowOperationalBudget,
    ShadowScenarioResult,
    ShadowSideEffectFirewall,
    assess_cutover_readiness,
)
from ovc.development.skills.dias_materialisation import REQUIRED_LIVENESS_FUNCTIONS


def full_shadow() -> FullShadowRun:
    outcomes = {"admission": "PASS", "dispatch": "PASS", "qualification": "PASS", "receipt": "PASS", "successor": "PASS", "currentness": "PASS"}
    scenarios = tuple(ShadowScenarioResult(fixture, disposition, ShadowSideEffectFirewall()) for fixture, disposition in ADVERSARIAL_SAFE_DISPOSITIONS.items())
    return FullShadowRun("DSAI_VIT_RECEIPT_ONLY_V0_1", outcomes, dict(outcomes), scenarios, True, ShadowSideEffectFirewall())


def coverage() -> RetirementCoverageMatrix:
    rows = []
    for function in REQUIRED_LIVENESS_FUNCTIONS:
        incumbent = "PES" if function in {"DETACHED_QUALIFICATION_LEDGER_ENVELOPE_WRITE", "EXACT_HEAD_POINTER_PUBLICATION", "CONTENT_ADDRESSED_IDEMPOTENT_REPLAY"} else "CERS"
        owner = "VIT_QUALIFICATION_OWNER_LOCAL" if incumbent == "PES" else "DSAI_VIT_OWNER_LOCAL"
        rows.append(RetirementFunctionCoverage(function, incumbent, owner, "SHADOW_QUALIFIED_INACTIVE", True, True, True, "ENUMERATE_FENCE_DRAIN_AT_GATE"))
    return RetirementCoverageMatrix("DSAI_VIT_RECEIPT_ONLY_V0_1", tuple(rows))


def budgets() -> tuple[ShadowOperationalBudget, ...]:
    return (
        ShadowOperationalBudget("FALSE_ALLOW", 0, "outcomes", 0, True),
        ShadowOperationalBudget("DUPLICATE_SUCCESSOR", 0, "events", 0, True),
        ShadowOperationalBudget("A3_MISMATCH", 0, "writes", 0, True),
        ShadowOperationalBudget("RECEIPT_RECONSTRUCTION", 60, "seconds", 1, False),
        ShadowOperationalBudget("LIVENESS_RECONCILIATION", 300, "seconds", 2, False),
    )


def readiness(**changes: bool) -> CutoverReadinessAssessment:
    flags = dict(route_fencing_qualified=True, writer_fencing_qualified=True, repository_protection_current=True, qualification_transfer_rehearsed=True, rollback_rehearsed=True, receipt_reconstruction_qualified=True, fresh_process_recovery_qualified=True)
    flags.update(changes)
    return assess_cutover_readiness(shadow=full_shadow(), coverage=coverage(), budgets=budgets(), **flags)


def test_all_sixteen_frozen_adversarial_fixtures_fail_safe() -> None:
    shadow = full_shadow()
    assert len(shadow.scenarios) == 16
    assert shadow.adversarial_universe_closed is True
    assert shadow.qualified is True


@pytest.mark.parametrize("fixture", sorted(ADVERSARIAL_SAFE_DISPOSITIONS))
def test_each_adversarial_fixture_is_identity_and_disposition_bound(fixture: str) -> None:
    result = next(item for item in full_shadow().scenarios if item.fixture_id == fixture)
    assert result.passed is True
    assert replace(result, observed_disposition="UNSAFE_PASS").passed is False


def test_shadow_side_effect_firewall_covers_every_live_write_family() -> None:
    firewall = ShadowSideEffectFirewall()
    assert firewall.intact is True
    assert replace(firewall, qualification_ledger_writes=1).intact is False
    assert replace(firewall, parent_rac_evidence_writes=1).intact is False


def test_full_shadow_requires_exact_old_new_outcome_equivalence() -> None:
    shadow = full_shadow()
    assert shadow.exact_equivalence is True
    assert replace(shadow, new_route_outcomes={"admission": "PASS"}).qualified is False


def test_cutover_coverage_is_exact_scoped_and_inactive() -> None:
    matrix = coverage()
    assert matrix.cutover_scope_closed is True
    assert matrix.global_freeze_authorised is False
    assert matrix.removal_eligible is False
    with pytest.raises(DiasContractError):
        replace(matrix, functions=matrix.functions[:-1])
    with pytest.raises(DiasContractError):
        replace(matrix, global_freeze_authorised=True)


def test_frozen_shadow_budgets_are_met_without_live_performance_claim() -> None:
    assert all(item.met for item in budgets())
    assert replace(budgets()[3], observed=61).met is False


def test_g5_readiness_requires_every_safety_and_rehearsal_condition() -> None:
    assessment = readiness()
    assert assessment.ready is True
    assert assessment.live_authority is False
    assert len(assessment.shadow_run_id) == 64
    assert readiness(repository_protection_current=False).ready is False
    assert readiness(rollback_rehearsed=False).ready is False


def test_g5_readiness_does_not_grant_cutover_authority() -> None:
    assessment = readiness()
    assert replace(assessment, live_authority=True).ready is False


def test_wp5_court_record_auto_ratifies_g5_and_stops_at_reserved_gate() -> None:
    root = Path(__file__).resolve().parents[3]
    wp5 = root / "docs/programmes/dias-v0-1/wp5"
    authority = json.loads((wp5 / "DIASI_WP5_VIT_AUTHORITY_MANIFEST.json").read_text(encoding="utf-8"))
    frontier = json.loads((wp5 / "DIASI_WP5_VIT_DEPENDENCY_FRONTIER.json").read_text(encoding="utf-8"))
    gate = json.loads((wp5 / "DIASI_G_DGS_CUTOVER_DRAIN_OPERATOR_GATE_PACKET.json").read_text(encoding="utf-8"))
    g5 = json.loads((wp5 / "DIASI_G5_DGS_CUTOVER_READY_PASS.json").read_text(encoding="utf-8"))
    assert canonical_sha256(authority["payload"]) == authority["logical_id"]
    assert canonical_sha256(frontier["payload"]) == frontier["logical_id"]
    assert g5["decision"] == "PASS" and g5["live_authority"] is False
    assert gate["gate_id"] == "DIASI-G-DGS-CUTOVER-DRAIN"
    assert gate["canonical_operator_phrase"] == "OVC APPROVE DIASI-G-DGS-CUTOVER-DRAIN PASS"
    assert gate["recommendation"] == "PASS"
    assert "CERS_PES_DELETION_OR_REMOVAL" in gate["explicit_denials"]
    pointer = json.loads((root / "registries/implementation/dias_v0_1/CURRENT_STATE_POINTER.json").read_text(encoding="utf-8"))
    state = json.loads((root / pointer["current_state"]).read_text(encoding="utf-8"))
    assert state["operator_decision_required"] is True
    assert state["live_cutover"] is False
    assert state["next_reserved_operator_gate"] == "DIASI-G-DGS-CUTOVER-DRAIN"


def test_wp4b_algorithmic_review_replays_in_a_fresh_process() -> None:
    root = Path(__file__).resolve().parents[3]
    completed = subprocess.run(
        [sys.executable, "tools/ci/diasi_wp4b_algorithmic_review.py", "--subject-commit", "7afc0483c024d6dc488dacb7fb07a3d5827a6f12"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    observed = json.loads(completed.stdout)
    recorded = json.loads((root / "docs/programmes/dias-v0-1/wp5/DIASI_WP4B_INDEPENDENT_ALGORITHMIC_REVIEW.json").read_text(encoding="utf-8"))
    assert observed == recorded
    assert observed["status"] == "PASS"
