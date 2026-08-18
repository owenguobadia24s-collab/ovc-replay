from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "scripts/c2p2_rs0_real_source_shadow_r5.py"
SPEC = importlib.util.spec_from_file_location("c2p2_rs0_real_source_shadow_r5", SCRIPT)
assert SPEC and SPEC.loader
r5 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r5)


def test_r5_exact_authority_capacity_and_bindings_are_launchable() -> None:
    bindings = r5.validate_repo_bindings(ROOT)
    assert r5.AUTHORITY_ID == "AUTH.C2P2.RS0.REAL_SOURCE_SHADOW.ONE_RUN.v0.6"
    assert r5.TOKEN_ID == "TOKEN.C2P2.RS0.R5.ONE_RUN.v0.6"
    assert r5.STORAGE_LIMIT == 11_811_160_064
    assert r5.MEMORY_LIMIT == 1_160_593_408
    assert bindings["capacity"]["external_storage_limit_bytes"] == 11_811_160_064
    assert bindings["capacity"]["concurrency_limit"] == 1
    assert bindings["capacity"]["checkpoint_cadence_source_records"] == 4096


def test_r5_operator_decision_is_pass_without_selection_or_activation() -> None:
    release = ROOT / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0"
    decision = json.loads((release / "C2P2_RS0_FRESH_GRUN_R5_OPERATOR_DECISION_v0_1.json").read_text())
    authority = json.loads((ROOT / "registries/authority/C2P2_RS0_REAL_SOURCE_SHADOW_RUN_AUTHORITY_v0_6.json").read_text())
    prior = json.loads((ROOT / "registries/authority/C2P2_RS0_REAL_SOURCE_SHADOW_RUN_CONSUMPTION_v0_4.json").read_text())
    assert decision["decision"] == "PASS"
    assert decision["gate_id"] == "C2P2-RS0-FRESH-GRUN-R5"
    assert decision["approved_authority_delta"]["execution_count_limit"] == 1
    assert decision["approved_authority_delta"]["execution_storage_limit_bytes"] == 11_811_160_064
    assert authority["state"] == "AUTHORISED_NOT_STARTED"
    assert authority["fresh_run_token_state"] == "UNCONSUMED"
    assert authority["execution_count_consumed"] == 0
    assert authority["run_count_remaining"] == 1
    assert prior["authority_id"] == "AUTH.C2P2.RS0.REAL_SOURCE_SHADOW.ONE_RUN.v0.5"
    assert prior["execution_count_consumed"] == 1
    assert prior["run_count_remaining"] == 0
    assert authority["candidate_generation"]["selection_state"] == "COMPARATIVE_SET_ONLY_NO_WINNER"
    assert authority["candidate_generation"]["active_object_pack_id"] is None
    assert authority["non_transitive_denials"]["objectpack_selection"] == "NONE"
    assert authority["non_transitive_denials"]["c2p_activation"] == "NONE"
    assert authority["non_transitive_denials"]["validation"] == "LOCKED_UNCONSUMED"


def test_r5_recovery_envelope_is_exactly_the_operator_approved_measurement() -> None:
    release = ROOT / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0"
    q = json.loads((release / "C2P2_RS0_R4_CAPACITY_RECOVERY_QUALIFICATION_v0_1.json").read_text())
    assert q["status"] == "PASS"
    assert q["qualification"]["github_run_id"] == 32137035782
    assert q["max_measured_database_bytes"] == 8_992_563_200
    assert q["max_measured_peak_rss_bytes"] == 429_891_584
    assert q["proposed_execution_storage_limit_bytes"] == 11_811_160_064
    assert q["real_source_read"] is False
    assert q["real_source_execution"] is False


def test_r5_workflow_is_single_use_and_has_no_automatic_selection_or_activation() -> None:
    workflow = (ROOT / ".github/workflows/c2p2-rs0-real-source-shadow-run-r5.yml").read_text()
    assert "C2P2_RS0_REAL_SOURCE_SHADOW_RUN_AUTHORITY_v0_6.json" in workflow
    assert "Prove prior R5 attempts did not reach semantic launch" in workflow
    assert "Launch exactly one authorised R5 A/B/C real-source shadow execution" in workflow
    assert "C2P2_RS0_REAL_SOURCE_SHADOW_RUN_CONSUMPTION_v0_5.json" in workflow
    assert "actions/download-artifact@v4" in workflow
    assert "pull_request:" not in workflow
    assert "ObjectPack winner" not in workflow
