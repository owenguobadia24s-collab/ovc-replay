from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_operator_pass_is_exact_and_bounded():
    d = load("records/development/skills/CERS_G_LIVE_DISPATCH_OPERATOR_PASS_20260818T151800+0100.json")
    assert d["gate_id"] == "CERS-G-LIVE-DISPATCH"
    assert d["decision"] == "PASS"
    assert d["operator_command"] == "OVC APPROVE CERS-G-LIVE-DISPATCH PASS"
    assert d["executor"]["executor_identity"] == "OVC-SKILL-030@0.1.0+sha256:62809d0f5f1d4298fa916766912d4bec7b5a8bf7712f7382d448137f6f12f130|PACKET_EXECUTION|windows-local-python311"
    scope = d["approved_scope"]
    assert scope["programme_allowlist"] == ["OVC-DSAI3V-CERS-CONFORMANCE-v0.1"]
    assert scope["packet_allowlist"] == ["CERS-WP6"]
    assert scope["packet_class_allowlist"] == ["LOW_RISK_IMPLEMENTATION"]
    assert scope["action_classes"] == ["WRITE_FILE", "GIT_COMMIT", "PUSH_BRANCH"]
    assert scope["worker_concurrency"] == 1
    assert scope["max_speculative_depth"] == 1
    assert scope["direct_main_mutation"] is False
    assert scope["packet_executor_merge_capability"] == "NONE"
    assert scope["force_push"] is False and scope["history_rewrite"] is False


def test_authority_registry_fails_closed_outside_wp6():
    a = load("registries/development/skills/cers/CERS_LIVE_DISPATCH_AUTHORITY_v0_1.json")
    assert a["effective"] is True
    assert a["authority_effect"] == "CERS_WP6_BOUNDED_UNATTENDED_DISPATCH_ONLY"
    assert a["scope"]["packet_allowlist"] == ["CERS-WP6"]
    assert a["scope"]["worker_concurrency"] == 1
    assert a["integration"]["direct_main_mutation"] is False
    assert a["integration"]["parallel_physical_merge"] is False
    assert a["integration"]["force_push"] is False
    assert a["integration"]["history_rewrite"] is False
    assert a["side_effect_policy"]["unknown_side_effect"] == "DENY"
    assert a["scientific_selector_model_family_candidate_theory_semantic_publication_probability_risk_exposure_trading_execution"] == "NONE"


def test_programme_state_preserves_operator_pass_and_advances_lawfully_through_persistent_preactivation():
    p = load("registries/implementation/dsai3v_cers_v0_1/CURRENT_STATE_POINTER.json")
    approved = load("registries/implementation/dsai3v_cers_v0_1/OVC_DSAI3V_CERS_STATE_v0_7.json")
    pilot = load("registries/implementation/dsai3v_cers_v0_1/OVC_DSAI3V_CERS_STATE_v0_8.json")

    assert approved["status"] == "APPROVED"
    assert approved["runtime_authority"] == "AUTHORIZED_PENDING_WP6_IMPLEMENTATION_AND_PILOT"
    gate = next(row for row in approved["packet_register"] if row["packet_id"] == "CERS-G-LIVE-DISPATCH")
    assert gate["decision"] == "PASS_OPERATOR"

    assert pilot["supersedes_state"] == "OVC_DSAI3V_CERS_STATE_v0_7.json"
    assert pilot["status"] == "G6_PASS_CONDITIONAL_EXACT_HEAD_AND_PHYSICAL_RECEIPT"
    assert pilot["runtime_authority"] == "CERS_WP6_BOUNDED_LIVE_PILOT_EXECUTED"
    assert pilot["post_pilot_dispatch_state"] == "DISABLE_NEW_DISPATCH_AFTER_BRANCH_PILOT_COMPLETION"

    if p["current_state"].endswith("OVC_DSAI3V_CERS_STATE_v0_7.json"):
        assert p["status"] == "APPROVED"
        assert p["next_packet"] == "CERS-WP6"
        return
    if p["current_state"].endswith("OVC_DSAI3V_CERS_STATE_v0_8.json"):
        assert p["status"] == "G6_PASS_CONDITIONAL_EXACT_HEAD_AND_PHYSICAL_RECEIPT"
        assert p["post_pilot_dispatch_state"] == "DISABLE_NEW_DISPATCH_AFTER_BRANCH_PILOT_COMPLETION"
        return

    persistent_plan = load("registries/implementation/dsai3v_cers_v0_1/OVC_DSAI3V_CERS_STATE_v0_9.json")
    assert persistent_plan["supersedes_state"] == "OVC_DSAI3V_CERS_STATE_v0_8.json"
    assert persistent_plan["plan_id"] == "OVC-DSAI3V-CERS-PERSISTENT-SUPERVISOR-ACTIVATION-PLAN-0.1-RATIFIED"
    assert persistent_plan["persistent_general_dispatch"] == "DENIED_PENDING_CERS-G-PERSISTENT-SUPERVISOR-ACTIVATION"
    assert persistent_plan["post_pilot_dispatch_state"] == "DISABLE_NEW_DISPATCH"
    predecessor = persistent_plan["predecessor_effectivity"]
    assert predecessor["status"] == "CERS_IMPLEMENTED_QUALIFIED_LIVE_PILOT_PASS"
    assert predecessor["merge_commit"] == "81faa31be2e59e47bc9784174f971c93a5a3a41c"
    assert predecessor["physical_tree"] == "5faa522134abfae1749a13bb9b53ae51e8054ee7"
    assert predecessor["transaction_id"] == "8e306f0506d1a2199777e267c5321425e97ff3b72a07ca9605a9ef04c47516f9"
    assert predecessor["completion_proof"] == "112fcfcec02c73b1b19d56d90c5965e45da9d2a7cc26d19706f8cd0816fde860"

    if p["current_state"].endswith("OVC_DSAI3V_CERS_STATE_v0_9.json"):
        assert p["packet_id"] == "CERS-PS-WP0"
        return

    suffix = Path(p["current_state"]).name
    version = int(suffix.split("_v0_")[1].split(".json")[0])
    current = load(p["current_state"])
    assert current["plan_id"] == "OVC-DSAI3V-CERS-PERSISTENT-SUPERVISOR-ACTIVATION-PLAN-0.1-RATIFIED"
    assert current["controller_identity"] == "DSAI_VIT_PHYSICAL_CONTROLLER"
    assert current["physical_gateway"] == "DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY"
    assert current["parallel_physical_merge"] is False

    if version in {17, 18}:
        assert p["status"] == "COMPLETED"
        assert p["decision"] == "PASS"
        assert p["next_packet"] is None
        assert current["decision_authority"] == "OPERATOR"
        assert current["persistent_run"] == "ACTIVATED"
        assert current["persistent_general_dispatch"] == "ALLOWED_EXACT_ADMITTED_SCOPE_ONLY"
        assert current["post_pilot_dispatch_state"] == "RUN"
        expected_delta = {
            17: "PERSISTENT_RUN_FOR_EXACT_ADMITTED_SCOPE_ONLY",
            18: "PERSISTENT_UNATTENDED_INVOCATION_ADMISSION_EXPANSION_FOR_EXACT_P2CTI_ASOCSI_GRT2_SCOPE_ONLY",
        }
        assert current["authority_delta"] == expected_delta[version]
        assert current["reserved_authority_unchanged"] is True
        return

    assert current["persistent_general_dispatch"] == "DENIED_PENDING_CERS-G-PERSISTENT-SUPERVISOR-ACTIVATION"
    assert current["post_pilot_dispatch_state"] == "DISABLE_NEW_DISPATCH"
    activation = next(row for row in current["packet_register"] if row["packet_id"] == "CERS-G-PERSISTENT-SUPERVISOR-ACTIVATION")
    assert activation["authority_required"] == "OPERATOR_REQUIRED"
    assert activation["authority_delta"] == "PERSISTENT_RUN_FOR_EXACT_ADMITTED_SCOPE_ONLY"
    assert activation["status"] in {"PLANNED", "GATE_PREPARATION", "GATE_READY"}

    assert 10 <= version <= 16
    expected_packet_by_version = {
        10: "CERS-PS-WP1",
        11: "CERS-PS-WP2",
        12: "CERS-PS-WP3",
        13: "CERS-PS-WP4",
        14: "CERS-PS-WP5",
        15: "CERS-G-PERSISTENT-SUPERVISOR-ACTIVATION",
        16: "CERS-G-PERSISTENT-SUPERVISOR-ACTIVATION",
    }
    assert p["packet_id"] == expected_packet_by_version[version]
    if version == 16:
        assert p["next_packet"] is None
        assert p["status"] == "GATE_READY"
        assert p["decision"] == "PENDING_OPERATOR"
    else:
        assert p["next_packet"] == expected_packet_by_version[version]


def test_gate_ready_evidence_and_external_completion_are_bound():
    d = load("records/development/skills/CERS_G_LIVE_DISPATCH_OPERATOR_PASS_20260818T151800+0100.json")
    gate = load("docs/releases/development-skills-v0-3/cers-conformance/wp1-wp5/CERS_G_LIVE_DISPATCH_GATE_PACKET_v0_1.json")
    assert gate["status"] == "GATE_READY"
    assert gate["executor"]["executor_identity"] == d["executor"]["executor_identity"]
    evidence = d["completion_evidence"]
    assert evidence["physical_tree_equality"] == "PASS"
    assert evidence["materialisation_receipt_id"] == "f12c5c6d278e47c3c0270d0948dd135350ee0f633830f7a668f7263f0666e174"
    assert evidence["completion_receipt_id"] == "3f986979f0f8bea9a3c1c55d4cd1b5f380f2cba72a2f2378d328a185a521cee8"
    assert evidence["development_latency_receipt_id"] == "b9958b44ed5ad5fded36ac4157dbe0abc010fc87147b39b03bb535ba9fccf302"
    assert evidence["completion_observability_attachment_id"] == "30037a2e8418c30259b22c4e204ff9417a3cd631cc621582f57721d7628225b6"
