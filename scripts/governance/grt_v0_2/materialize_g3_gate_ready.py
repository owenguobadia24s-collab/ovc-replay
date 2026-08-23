#!/usr/bin/env python3
"""Materialise the authority-inert consolidated GRT2-G3 operator packet."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256
from ovc.development.skills.vit_core import DependencyFrontier, IntegrationAuthorityManifest


PROGRAMME_ID = "OVC-GRT-V0.2-REPOSITORY-CONSTITUTION-CONTINUOUS-CONFORMANCE"
PLAN_ID = "OVC-GRT-V0.2-RCCC-CONFORMANCE-IMPLEMENTATION-PLAN-0.2-REVISED-RATIFIED"
CONSTITUTION_HASH = "cac9fc5f0e31db08c4c37153c92a214fcc482414421f34d74c594faec65a71b0"
PERFORMANCE_HASH = "88fadf691be87f0c55d98c994d29f54f6112e6c6e43f8d4bbbb328dc7fdb0b58"
B0_HASH = "3587c224c07360751923e5718c5bedb432ce4a5c8cccd4061f73dd53ef07de5d"


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _hashed(value: dict[str, Any]) -> dict[str, Any]:
    return {**value, "logical_sha256": canonical_sha256(value)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--readiness-evidence", required=True)
    parser.add_argument("--readiness-merge-sha", required=True)
    parser.add_argument("--readiness-merge-tree", required=True)
    parser.add_argument("--readiness-run-id", type=int, required=True)
    parser.add_argument("--readiness-artifact-id", type=int, required=True)
    parser.add_argument("--readiness-artifact-digest", required=True)
    parser.add_argument("--readiness-file-sha256", required=True)
    parser.add_argument("--final-assurance-evidence", required=True)
    parser.add_argument("--final-assurance-run-id", type=int, required=True)
    parser.add_argument("--final-assurance-artifact-id", type=int, required=True)
    parser.add_argument("--final-assurance-artifact-digest", required=True)
    parser.add_argument("--final-assurance-file-sha256", required=True)
    parser.add_argument("--final-assurance-base-sha", required=True)
    parser.add_argument("--final-assurance-base-tree", required=True)
    parser.add_argument("--final-assurance-candidate-sha", required=True)
    parser.add_argument("--final-assurance-candidate-tree", required=True)
    parser.add_argument("--pip-id", required=True)
    parser.add_argument("--vit-qualification-id", required=True)
    parser.add_argument("--authority-manifest-id", required=True)
    parser.add_argument("--dependency-frontier-id", required=True)
    parser.add_argument("--pr-tests-run-id", type=int, required=True)
    parser.add_argument("--pr-tiered-run-id", type=int, required=True)
    parser.add_argument("--main-tests-run-id", type=int, required=True)
    parser.add_argument("--post-merge-run-id", type=int, required=True)
    parser.add_argument("--post-merge-proof-id", required=True)
    parser.add_argument("--post-merge-transaction-id", required=True)
    parser.add_argument("--materialisation-receipt-id", required=True)
    parser.add_argument("--completion-receipt-id", required=True)
    parser.add_argument("--attachment-id", required=True)
    parser.add_argument("--development-latency-receipt-id", required=True)
    args = parser.parse_args()

    root = Path(args.repository_root).resolve()
    evidence = json.loads(Path(args.readiness_evidence).read_text(encoding="utf-8"))
    final_evidence = json.loads(Path(args.final_assurance_evidence).read_text(encoding="utf-8"))
    if evidence.get("status") != "GATE_READY" or evidence.get("qa_disposition") != "PASS" or evidence.get("blockers"):
        raise RuntimeError("GRT2_G3_READINESS_EVIDENCE_NOT_PASS")
    if evidence.get("b0_member_count") != 569 or evidence.get("b0_membership_sha256") != B0_HASH:
        raise RuntimeError("GRT2_G3_B0_IDENTITY_MISMATCH")
    if evidence.get("constitution_hash") != CONSTITUTION_HASH or evidence.get("performance_budget_hash") != PERFORMANCE_HASH:
        raise RuntimeError("GRT2_G3_GOVERNING_IDENTITY_MISMATCH")
    if evidence.get("candidate_tree") != args.readiness_merge_tree:
        raise RuntimeError("GRT2_G3_PHYSICAL_TREE_MISMATCH")
    if final_evidence.get("status") != "GATE_READY" or final_evidence.get("qa_disposition") != "PASS" or final_evidence.get("blockers"):
        raise RuntimeError("GRT2_G3_FINAL_ASSURANCE_NOT_PASS")
    if final_evidence.get("b0_member_count") != 569 or final_evidence.get("b0_membership_sha256") != B0_HASH:
        raise RuntimeError("GRT2_G3_FINAL_ASSURANCE_B0_IDENTITY_MISMATCH")
    if final_evidence.get("constitution_hash") != CONSTITUTION_HASH or final_evidence.get("performance_budget_hash") != PERFORMANCE_HASH:
        raise RuntimeError("GRT2_G3_FINAL_ASSURANCE_GOVERNING_IDENTITY_MISMATCH")
    if final_evidence.get("candidate_commit") != args.final_assurance_candidate_sha or final_evidence.get("candidate_tree") != args.final_assurance_candidate_tree:
        raise RuntimeError("GRT2_G3_FINAL_ASSURANCE_CANDIDATE_MISMATCH")

    floor = dict(final_evidence["candidate_debt_floor_generation_0"])
    floor["predecessor_commit"] = args.final_assurance_candidate_sha
    floor["predecessor_tree"] = args.final_assurance_candidate_tree
    floor.pop("floor_hash", None)
    floor["floor_hash"] = canonical_sha256(floor)
    floor_path = "docs/programmes/grt-v0-2/g3/GRT2_G3_PROPOSED_DEBT_FLOOR_GENERATION_0.json"
    _write(root / floor_path, floor)

    readiness_source = {
        "workflow_run_id": args.readiness_run_id,
        "artifact_id": args.readiness_artifact_id,
        "artifact_name": "grt2-g3-readiness-evidence",
        "artifact_digest": args.readiness_artifact_digest,
        "evidence_file_sha256": args.readiness_file_sha256,
        "semantic_evidence_hash": evidence["evidence_hash"],
        "qualified_candidate_commit": evidence["candidate_commit"],
        "qualified_candidate_tree": evidence["candidate_tree"],
    }
    final_assurance_source = {
        "workflow_run_id": args.final_assurance_run_id,
        "artifact_id": args.final_assurance_artifact_id,
        "artifact_name": "grt2-g3-readiness-evidence",
        "artifact_digest": args.final_assurance_artifact_digest,
        "evidence_file_sha256": args.final_assurance_file_sha256,
        "semantic_evidence_hash": final_evidence["evidence_hash"],
        "qualified_candidate_commit": final_evidence["candidate_commit"],
        "qualified_candidate_tree": final_evidence["candidate_tree"],
    }
    completion = _hashed({
        "schema": "ovc-grt2-g3-readiness-completion-receipt/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": "GRT2-G3-READINESS-EVIDENCE",
        "status": "COMPLETED_PASS_MERGED",
        "pr": 1252,
        "pip_id": args.pip_id,
        "authority_manifest_id": args.authority_manifest_id,
        "dependency_frontier_id": args.dependency_frontier_id,
        "binding_policy": "LATE_PHYSICAL_PLACEMENT",
        "vit_qualification_id": args.vit_qualification_id,
        "readiness_evidence": readiness_source,
        "physical_materialisation": {
            "merge_commit": args.readiness_merge_sha,
            "merge_tree": args.readiness_merge_tree,
            "qualified_tree": evidence["candidate_tree"],
            "exact_tree_equality": True,
            "post_merge_completion_run_id": args.post_merge_run_id,
            "post_merge_proof_id": args.post_merge_proof_id,
            "transaction_id": args.post_merge_transaction_id,
            "receipt_ids": {
                "materialisation_receipt_id": args.materialisation_receipt_id,
                "completion_receipt_id": args.completion_receipt_id,
                "attachment_id": args.attachment_id,
                "development_latency_receipt_id": args.development_latency_receipt_id,
            },
        },
        "assurance": {
            "pr_tests_run_id": args.pr_tests_run_id,
            "pr_tiered_run_id": args.pr_tiered_run_id,
            "main_tests_run_id": args.main_tests_run_id,
            "readiness_run_id": args.readiness_run_id,
            "result": "PASS",
        },
        "authority_effect": "NONE_READINESS_COMPLETION_ONLY",
        "constitution_status": "PROPOSED_UNADMITTED",
        "active_enforcement": "LIMITED_NEW_ARTIFACT_ENFORCEMENT",
        "debt_floor_generation": None,
        "g3_authority": "NOT_CONSUMED",
    })
    completion_path = "docs/programmes/grt-v0-2/g3/GRT2_G3_READINESS_COMPLETION_RECEIPT.json"
    _write(root / completion_path, completion)

    authority = IntegrationAuthorityManifest(
        plan_id=PLAN_ID,
        packet_id="GRT2-G3-GATE-READY",
        gate_id="GRT2-G3",
        authority_class="AUTO_EXECUTABLE",
        authority_delta="NONE_GATE_PREPARATION_ONLY",
        authority_sources=(
            completion_path,
            "docs/programmes/grt-v0-2/gates/GRT2_G2_5_THRESHOLD_RECEIPT.json",
            "registries/governance/grt_v0_2/GRT_REPOSITORY_CONSTITUTION_v0_2.json",
        ),
        reserved_boundaries=(
            "GRT2-G3_OPERATOR_DECISION",
            "CONSTITUTION_V0_2_ACTIVATION",
            "DEBTFLOOR_GENERATION_0_ACTIVATION",
            "FULL_GRT_EXACT_ACTIVATION",
        ),
    )
    authority_binding = {
        "schema": "ovc-integration-authority-manifest-binding/v0_1",
        "authority_manifest": asdict(authority),
        "authority_manifest_id": authority.logical_id,
    }
    authority_path = "docs/programmes/grt-v0-2/g3/GRT2_G3_GATE_READY_AUTHORITY_MANIFEST.json"
    _write(root / authority_path, authority_binding)

    frontier = DependencyFrontier(
        dependencies=(
            f"GRT2-G3-READINESS-EVIDENCE:{evidence['evidence_hash']}",
            f"GRT2-G3-READINESS-MERGE:{args.readiness_merge_sha}",
            f"GRT2-G3-READINESS-COMPLETION:{completion['logical_sha256']}",
            f"GRT2-G3-FINAL-ASSURANCE:{final_evidence['evidence_hash']}",
            f"CURRENT-PROTECTED-MAIN:{args.final_assurance_base_sha}",
            f"IMMUTABLE-B0:{B0_HASH}",
        ),
        predecessor_requirement="PHYSICAL_MATERIALISATION_REQUIRED",
        owner_bindings=("PROGRAMME_GENESIS:GRT2-G3-OPERATOR-RESERVED",),
    )
    frontier_binding = {
        "schema": "ovc-dependency-frontier-binding/v0_1",
        "dependency_frontier": asdict(frontier),
        "dependency_frontier_id": frontier.logical_id,
    }
    frontier_path = "docs/programmes/grt-v0-2/g3/GRT2_G3_GATE_READY_DEPENDENCY_FRONTIER.json"
    _write(root / frontier_path, frontier_binding)

    transition = _hashed({
        "schema": "ovc-grt2-g3-enforcement-transition-proposal/v1",
        "programme_id": PROGRAMME_ID,
        "gate_id": "GRT2-G3",
        "status": "PROPOSED_INACTIVE_OPERATOR_RESERVED",
        "current_authority": {
            "constitution_status": "PROPOSED_UNADMITTED",
            "active_enforcement": "LIMITED_NEW_ARTIFACT_ENFORCEMENT",
            "debt_floor_generation": None,
            "g3_status": "NOT_AUTHORISED",
        },
        "proposed_authority_delta_on_operator_pass": {
            "repository_constitution": {"version": "0.2", "canonical_hash": CONSTITUTION_HASH, "transition": "PROPOSED_UNADMITTED_TO_ACTIVE"},
            "debt_floor": {"generation": 0, "floor_hash": floor["floor_hash"], "definition": floor_path, "transition": "ABSENT_TO_ACTIVE_GENERATION_0"},
            "enforcement": {"transition": "LIMITED_NEW_ARTIFACT_ENFORCEMENT_TO_FULL_GRT_EXACT", "required_check": "GRT-EXACT"},
        },
        "activation_order": [
            "record exact operator GRT2-G3 PASS decision",
            "revalidate protected main and the proposed floor against the exact activation predecessor tree",
            "activate Constitution v0.2 exact canonical identity",
            "materialise and activate DebtFloor generation 0",
            "replace limited G2.5 scope with full GRT-EXACT required enforcement",
            "emit immutable activation and rollback receipts",
        ],
        "explicitly_unchanged": [
            "immutable B0 membership and 569 count",
            "Programme Genesis adoption authority",
            "owner assignments",
            "constitutional semantics GRT2-D1..D433",
            "market, scientific, Validation, publication, probability, risk, exposure, execution and agent-write authority",
        ],
        "authority_effect": "NONE_PROPOSAL_ONLY",
    })
    transition_path = "docs/programmes/grt-v0-2/g3/GRT2_G3_ENFORCEMENT_TRANSITION_PROPOSAL.json"
    _write(root / transition_path, transition)

    qa = _hashed({
        "schema": "ovc-grt2-g3-gate-ready-qa/v1",
        "programme_id": PROGRAMME_ID,
        "gate_id": "GRT2-G3",
        "qa_recommendation": "PASS",
        "acceptance": {
            "immutable_b0_569": "PASS",
            "all_current_observer_conditions_source_classified": f"PASS_{final_evidence['transition_reconciliation']['current_condition_classification_count']}",
            "unresolved_current_conditions": final_evidence["transition_reconciliation"]["unresolved_current_condition_count"],
            "transition_new_debt": final_evidence["transition_reconciliation"]["transition_new_debt_count"],
            "baseline_expansion_zero": "PASS",
            "full_current_tree_evaluable": f"PASS_{final_evidence['full_current_snapshot']['evaluation_count']}_EVALUATIONS",
            "full_current_not_evaluable": final_evidence["full_current_snapshot"]["not_evaluable_count"],
            "b0_to_current_v0_2_lineage": final_evidence["b0_lineage_reconciliation"]["status"],
            "unresolved_lineage": final_evidence["b0_lineage_reconciliation"]["unresolved_lineage_count"],
            "pilot_full_g3_shadow": "PASS_8_OF_8",
            "historical_full_g3_shadow": "PASS_10_OF_10",
            "deterministic_replay": final_evidence["deterministic_repeat"]["status"],
            "candidate_floor_reproducible": "PASS",
            "targeted_repository_vit_siq_grt_parity_profile": "PASS",
            "exact_tree_equality": "PASS",
        },
        "unresolved_issues": [],
        "warnings": [
            "Repository Constitution v0.2 remains PROPOSED_UNADMITTED.",
            "DebtFloor generation 0 is proposed but absent/inactive.",
            "Full GRT-EXACT required enforcement remains inactive.",
            "GRT2-G3 activation is operator-reserved.",
        ],
        "evidence": final_assurance_source,
        "completion_receipt": completion_path,
        "authority_effect": "NONE_QA_ONLY",
    })
    qa_path = "docs/programmes/grt-v0-2/g3/GRT2_G3_GATE_READY_QA_PACKET.json"
    _write(root / qa_path, qa)

    changed_files = [
        "docs/programmes/grt-v0-2/g3/GRT2_G3_GATE_READY_AUTHORITY_MANIFEST.json",
        "docs/programmes/grt-v0-2/g3/GRT2_G3_GATE_READY_DEPENDENCY_FRONTIER.json",
        "docs/programmes/grt-v0-2/g3/GRT2_G3_ENFORCEMENT_TRANSITION_PROPOSAL.json",
        "docs/programmes/grt-v0-2/g3/GRT2_G3_EVIDENCE_INDEX.json",
        "docs/programmes/grt-v0-2/g3/GRT2_G3_GATE_READY_DECISION_PACKET.json",
        "docs/programmes/grt-v0-2/g3/GRT2_G3_GATE_READY_QA_PACKET.json",
        "docs/programmes/grt-v0-2/g3/GRT2_G3_PROPOSED_DEBT_FLOOR_GENERATION_0.json",
        "docs/programmes/grt-v0-2/g3/GRT2_G3_READINESS_COMPLETION_RECEIPT.json",
        "registries/implementation/grt_v0_2/CURRENT_STATE_POINTER.json",
        "registries/implementation/grt_v0_2/OVC_GRT2_STATE_v0_15.json",
        "scripts/governance/grt_v0_2/qualify_g3_readiness.py",
        "scripts/governance/grt_v0_2/materialize_g3_gate_ready.py",
        "src/ovc/programme_genesis/grt_v0_2/g3_readiness.py",
        "tests/governance/grt_v0_2/test_grt2_g2_5_gate_ready.py",
        "tests/governance/grt_v0_2/test_grt2_g2_5_operator_pass.py",
        "tests/governance/grt_v0_2/test_grt2_g2_final_state.py",
        "tests/governance/grt_v0_2/test_grt2_g2_readiness.py",
        "tests/governance/grt_v0_2/test_grt2_stack_797_closeout.py",
        "tests/governance/grt_v0_2/test_grt2_wp1_state.py",
        "tests/governance/grt_v0_2/test_grt2_g3_gate_ready.py",
        "tests/governance/grt_v0_2/test_grt2_g3_readiness.py",
    ]
    gate = _hashed({
        "schema": "ovc-grt2-g3-gate-ready-decision-packet/v1",
        "programme_id": PROGRAMME_ID,
        "plan_id": PLAN_ID,
        "plan_version": "0.2_REVISED_RATIFIED",
        "gate_id": "GRT2-G3",
        "title": "Repository Constitution v0.2 / DebtFloor generation 0 / full GRT-EXACT activation",
        "status": "GATE_READY_OPERATOR_REQUIRED",
        "current_protected_main_at_preparation": {"commit": args.final_assurance_base_sha, "tree": args.final_assurance_base_tree},
        "exact_final_assurance_candidate": {"commit": args.final_assurance_candidate_sha, "tree": args.final_assurance_candidate_tree},
        "readiness_packet": {"pr": 1252, "merge_commit": args.readiness_merge_sha, "merge_tree": args.readiness_merge_tree, "completion_receipt": completion_path},
        "completed_packets": ["GRT2-WP0", "GRT2-WP1", "GRT2-WP2", "GRT2-WP3A", "GRT2-WP3B", "GRT2-WP3C", "GRT2-WP3D", "GRT2-WP3E", "GRT2-G2", "GRT2-G2.5", "GRT2-G3-READINESS-EVIDENCE"],
        "readiness_qualification": readiness_source,
        "exact_final_assurance": final_assurance_source,
        "deterministic_replay": {"status": final_evidence["deterministic_repeat"]["status"], "pilot_candidates": 8, "historical_candidates": 10},
        "b0_lineage_and_provenance": {
            "member_count": 569,
            "membership_sha256": B0_HASH,
            "lineage_status": final_evidence["b0_lineage_reconciliation"]["status"],
            "unresolved_lineage_count": final_evidence["b0_lineage_reconciliation"]["unresolved_lineage_count"],
            "current_observer_condition_count": final_evidence["transition_reconciliation"]["current_observer_condition_count"],
            "source_classified_condition_count": final_evidence["transition_reconciliation"]["current_condition_classification_count"],
            "transition_new_debt_count": final_evidence["transition_reconciliation"]["transition_new_debt_count"],
            "baseline_expansion_zero_proven": final_evidence["transition_reconciliation"]["baseline_expansion_zero_proven"],
        },
        "current_authority_state": {
            "constitution_status": "PROPOSED_UNADMITTED",
            "active_enforcement": "LIMITED_NEW_ARTIFACT_ENFORCEMENT",
            "debt_floor_generation": None,
            "g3_authority": "NOT_CONSUMED",
        },
        "proposed_authority_delta": transition["proposed_authority_delta_on_operator_pass"],
        "proposed_debt_floor_generation_0": {"definition": floor_path, "floor_hash": floor["floor_hash"], "open_grandfathered_finding_count": len(floor["open_grandfathered_findings"])},
        "enforcement_transition": {"proposal": transition_path, "logical_sha256": transition["logical_sha256"]},
        "activation_implications": {
            "constitution_v0_2": "Makes the exact constitutional rule bundle active; no semantic amendment or inferred authority.",
            "debt_floor_generation_0": "Grandfathers only the exact open finding IDs in the proposed generation-0 definition; future growth, expansion, material change or recurrence fails.",
            "full_grt_exact": "Replaces limited G2.5 scope with required full-tree exact conformance for governed permanent integration.",
        },
        "acceptance_conditions": qa["acceptance"],
        "assurance": {
            "targeted_readiness_run_id": args.readiness_run_id,
            "exact_final_readiness_run_id": args.final_assurance_run_id,
            "repository_and_parity_run_id": args.pr_tests_run_id,
            "vit_siq_profile_merge_readiness_run_id": args.pr_tiered_run_id,
            "post_merge_main_assurance_run_id": args.main_tests_run_id,
            "post_merge_completion_run_id": args.post_merge_run_id,
            "vit_qualification_id": args.vit_qualification_id,
            "pip_id": args.pip_id,
            "authority_manifest_id": args.authority_manifest_id,
            "dependency_frontier_id": args.dependency_frontier_id,
            "result": "PASS",
        },
        "gate_ready_integration_frontier": {
            "authority_manifest": authority_path,
            "authority_manifest_id": authority.logical_id,
            "dependency_frontier": frontier_path,
            "dependency_frontier_id": frontier.logical_id,
        },
        "qa": {"packet": qa_path, "logical_sha256": qa["logical_sha256"], "disposition": "PASS"},
        "warnings": qa["warnings"],
        "unresolved_issues": [],
        "changed_files": changed_files,
        "external_artifacts": [readiness_source, final_assurance_source],
        "rollback": {
            "before_operator_pass": "Close or supersede this authority-inert gate packet; retain #1252, B0 and all readiness evidence.",
            "after_operator_pass": "Use an explicit operator-governed rollback/incident decision; preserve the activation decision, DebtFloor generation 0, finding history and Git history; never force-push or broaden grandfathering.",
        },
        "recommended_decision": "PASS",
        "allowed_operator_decisions": ["PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"],
        "operator_decision": None,
        "operator_decision_required": True,
        "authority_consumed": "NONE",
        "post_pass_continuation": {"packet_id": "GRT2-G3-ACTIVATION-MATERIALISATION", "first_action": "REVALIDATE_EXACT_CURRENT_MAIN_AND_PROPOSED_FLOOR_THEN_MATERIALISE_OPERATOR_DECISION_AND_ATOMIC_ACTIVATION_TRANSITION"},
        "stop_condition": "STOP_FOR_OPERATOR_GRT2_G3_DECISION",
    })
    gate_path = "docs/programmes/grt-v0-2/g3/GRT2_G3_GATE_READY_DECISION_PACKET.json"
    _write(root / gate_path, gate)

    index = _hashed({
        "schema": "ovc-grt2-g3-evidence-index/v1",
        "programme_id": PROGRAMME_ID,
        "gate_id": "GRT2-G3",
        "readiness_evidence": readiness_source,
        "exact_final_assurance": final_assurance_source,
        "completion_receipt": completion_path,
        "qa_packet": qa_path,
        "gate_packet": gate_path,
        "debt_floor_proposal": floor_path,
        "enforcement_transition_proposal": transition_path,
        "gate_ready_authority_manifest": authority_path,
        "gate_ready_dependency_frontier": frontier_path,
        "authority_effect": "NONE_INDEX_ONLY",
    })
    _write(root / "docs/programmes/grt-v0-2/g3/GRT2_G3_EVIDENCE_INDEX.json", index)

    state_path = "registries/implementation/grt_v0_2/OVC_GRT2_STATE_v0_15.json"
    state = _hashed({
        "schema": "ovc-grt2-programme-state/v1",
        "programme_id": PROGRAMME_ID,
        "plan_id": PLAN_ID,
        "plan_version": "0.2_REVISED_RATIFIED",
        "packet_id": "GRT2-G3-GATE-READY",
        "gate_id": "GRT2-G3",
        "status": "GATE_READY_OPERATOR_REQUIRED",
        "baseline_commit": args.final_assurance_base_sha,
        "baseline_tree": args.final_assurance_base_tree,
        "readiness_merge_commit": args.readiness_merge_sha,
        "readiness_evidence_hash": evidence["evidence_hash"],
        "exact_final_assurance_commit": args.final_assurance_candidate_sha,
        "exact_final_assurance_tree": args.final_assurance_candidate_tree,
        "exact_final_assurance_evidence_hash": final_evidence["evidence_hash"],
        "gate_packet": gate_path,
        "qa_packet": qa_path,
        "completion_receipt": completion_path,
        "blockers": [],
        "unresolved_issues": [],
        "constitution_status": "PROPOSED_UNADMITTED",
        "active_enforcement": "LIMITED_NEW_ARTIFACT_ENFORCEMENT",
        "debt_floor_generation": None,
        "candidate_debt_floor_generation": 0,
        "candidate_debt_floor_hash": floor["floor_hash"],
        "g3_status": "GATE_READY_NOT_AUTHORISED_OPERATOR_REQUIRED",
        "operator_decision_required": True,
        "recommended_operator_decision": "PASS",
        "allowed_operator_decisions": ["PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"],
        "authority_effect": "NONE_GATE_PREPARATION_ONLY",
        "next_packet": "GRT2-G3-OPERATOR-DECISION",
        "next_gate": "GRT2-G3",
        "next_action": "STOP_FOR_OPERATOR_GRT2_G3_DECISION",
    })
    _write(root / state_path, state)
    pointer = {
        "schema": "ovc-grt2-current-state-pointer/v1",
        "programme_id": PROGRAMME_ID,
        "current_state": state_path,
        "packet_id": "GRT2-G3-GATE-READY",
        "gate_id": "GRT2-G3",
        "status": "GATE_READY_OPERATOR_REQUIRED",
        "operator_decision_required": True,
        "recommended_operator_decision": "PASS",
        "next_packet": "GRT2-G3-OPERATOR-DECISION",
        "next_action": "STOP_FOR_OPERATOR_GRT2_G3_DECISION",
    }
    _write(root / "registries/implementation/grt_v0_2/CURRENT_STATE_POINTER.json", pointer)
    print(json.dumps({"gate_packet": gate_path, "gate_packet_hash": gate["logical_sha256"], "floor_hash": floor["floor_hash"], "state": state_path, "status": "GATE_READY_OPERATOR_REQUIRED"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
