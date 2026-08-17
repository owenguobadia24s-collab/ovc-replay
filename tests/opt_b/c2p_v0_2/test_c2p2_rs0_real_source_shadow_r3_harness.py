from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RELEASE = ROOT / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0"
AUTHORITY = ROOT / "registries/authority/C2P2_RS0_REAL_SOURCE_SHADOW_RUN_AUTHORITY_v0_4.json"
PRIOR_CONSUMPTION = ROOT / "registries/authority/C2P2_RS0_REAL_SOURCE_SHADOW_RUN_CONSUMPTION_v0_2.json"
R3_CONSUMPTION = ROOT / "registries/authority/C2P2_RS0_REAL_SOURCE_SHADOW_RUN_CONSUMPTION_v0_3.json"
BINDING = ROOT / "registries/opt_b/c2p/v0_2/research/C2P2_RS0_EMPIRICAL_RUNTIME_SPOOLED_ADAPTER_BINDING_v0_2.json"
EXECUTION = ROOT / "registries/implementation/c2p_v0_2/C2P2_RS0_EXECUTION_STATE_v0_2.json"
RUNNER = ROOT / "scripts/c2p2_rs0_real_source_shadow_r3.py"
WORKFLOW = ROOT / ".github/workflows/c2p2-rs0-real-source-shadow-run-r2.yml"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_r3_operator_pass_materialises_exact_single_use_authority() -> None:
    decision = load(RELEASE / "C2P2_RS0_FRESH_GRUN_R3_OPERATOR_DECISION_v0_1.json")
    authority = load(AUTHORITY)
    gate = load(RELEASE / "C2P2_RS0_FRESH_GRUN_R3_GATE_PACKET_v0_1.json")
    binding = load(BINDING)

    assert decision["gate_id"] == "C2P2-RS0-FRESH-GRUN-R3"
    assert decision["decision"] == "PASS"
    assert gate["recommended_decision"] == "PASS"
    assert gate["proposed_authority_delta"]["effect_if_pass"] == "AUTHORISE_EXACTLY_ONE_R3_REAL_SOURCE_A_B_C_COMPARATIVE_SHADOW_RUN"

    assert authority["authority_id"] == "AUTH.C2P2.RS0.REAL_SOURCE_SHADOW.ONE_RUN.v0.4"
    assert authority["state"] == "AUTHORISED_NOT_STARTED"
    assert authority["execution_count_limit"] == 1
    assert authority["execution_count_consumed"] == 0
    assert authority["run_count_remaining"] == 1
    assert authority["candidate_generation"]["generation_id"] == "C2P2-PS0-EMPIRICAL-RUNTIME-GENERATION-v3"
    assert authority["execution_adapter"]["binding_id"] == "C2P2_RS0_EMPIRICAL_RUNTIME_SPOOLED_ADAPTER_BINDING_v0_2"
    assert authority["execution_adapter"]["binding_logical_sha256"] == "01c3e85d5c4b47fbb2a102a1d4dff3774e49fcd15110157aaac3ea538a51201c"
    assert authority["execution_adapter"]["adapter_id"] == "C2P2_RS0_SOURCE_ORDER_RECOVERY_ADAPTER_v0_2"
    assert authority["source_materialisation"]["github_actions_source_artifact_id"] == 9283576949
    assert authority["non_transitive_denials"]["objectpack_selection"] == "NONE"
    assert authority["non_transitive_denials"]["c2p_activation"] == "NONE"
    assert authority["non_transitive_denials"]["validation"] == "LOCKED_UNCONSUMED"

    assert binding["logical_sha256"] == "01c3e85d5c4b47fbb2a102a1d4dff3774e49fcd15110157aaac3ea538a51201c"
    assert binding["status"] == "QUALIFIED_INACTIVE_PENDING_FRESH_GRUN_R3"
    assert binding["qualification"]["adversarial_equal_time_a_b_c_reference_equivalence"] == "PASS_EXACT"
    assert binding["qualification"]["full_cardinality_synthetic_capacity"] == "PASS"
    assert binding["qualification"]["exact_current_source_ordering_only_preflight"] == "PASS"


def test_r3_trigger_preserves_prior_consumption_and_has_no_prelaunch_r3_consumption() -> None:
    prior = load(PRIOR_CONSUMPTION)
    trigger = load(RELEASE / "C2P2_RS0_REAL_SOURCE_SHADOW_RUN_R3_TRIGGER_v0_1.json")
    packet = load(RELEASE / "C2P2_RS0_REAL_SOURCE_SHADOW_RUN_R3_PACKET_v0_1.json")
    execution = load(EXECUTION)

    assert prior["authority_id"] == "AUTH.C2P2.RS0.REAL_SOURCE_SHADOW.ONE_RUN.v0.3"
    assert prior["execution_count_consumed"] == 1
    assert prior["run_count_remaining"] == 0
    assert not R3_CONSUMPTION.exists()

    assert trigger["packet_id"] == "C2P2-RS0-REAL-SOURCE-SHADOW-RUN-R3"
    assert trigger["authority_id"] == "AUTH.C2P2.RS0.REAL_SOURCE_SHADOW.ONE_RUN.v0.4"
    assert trigger["run_count"] == 1
    assert trigger["adapter_binding_id"] == "C2P2_RS0_EMPIRICAL_RUNTIME_SPOOLED_ADAPTER_BINDING_v0_2"
    assert trigger["selection_state"] == "NONE_SELECTED"
    assert trigger["activation_state"] == "NONE"
    assert trigger["automatic_rerun_after_semantic_launch_failure"] == "FORBIDDEN"

    assert packet["status"] == "AUTHORISED_TRIGGERED_PRE_SEMANTIC_LAUNCH"
    assert packet["selection"] == "NONE"
    assert packet["activation"] == "NONE"
    assert packet["validation"] == "LOCKED_UNCONSUMED"

    assert execution["status"] == "RUNNING"
    assert execution["run_authority_consumed"] is False
    assert execution["run_count_remaining"] == 1
    assert execution["real_source_execution"] == "TRIGGERED_PRE_SEMANTIC_LAUNCH"


def test_r3_runner_and_branch_workflow_are_bound_to_recovered_source_order_adapter() -> None:
    runner = RUNNER.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "AUTH.C2P2.RS0.REAL_SOURCE_SHADOW.ONE_RUN.v0.4" in runner
    assert "C2P2_RS0_SOURCE_ORDER_RECOVERY_ADAPTER_v0_2" in runner
    assert "merge_source_factories_with_kind_segmentation" in runner
    assert "C2P2-RS0-RUN-RECOVERY-R3" in runner
    assert "C2P2-RS0-SCIENTIFIC-REVIEW-SELECTION" in runner

    assert "run/c2p2-rs0-real-source-shadow-r3-20260817" in workflow
    assert "C2P2_RS0_REAL_SOURCE_SHADOW_RUN_R3_TRIGGER_v0_1.json" in workflow
    assert "AUTH.C2P2.RS0.REAL_SOURCE_SHADOW.ONE_RUN.v0.4" in workflow
    assert "C2P2_RS0_REAL_SOURCE_SHADOW_RUN_CONSUMPTION_v0_3.json" in workflow
    assert "32010902424" in workflow
    assert "LIVE_R3_BRANCH_ADVANCED_OR_STALE_TRIGGER" in workflow
