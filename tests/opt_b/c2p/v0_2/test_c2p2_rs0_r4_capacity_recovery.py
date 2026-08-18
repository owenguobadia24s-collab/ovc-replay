from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from ovc.opt_b.c2p_v0_2.rs0_empirical_runtime_indexed import necessary_match_key
from ovc.opt_b.c2p_v0_2.rs0_empirical_semantics import normalize_candidate_source_row


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "scripts/run_c2p2_rs0_semantic_scalability_qualification.py"
SPEC = importlib.util.spec_from_file_location("c2p2_rs0_r4_capacity_recovery", SCRIPT)
assert SPEC and SPEC.loader
recovery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recovery)


def test_recovery_fixture_matches_frozen_base_cardinality_and_scope_counts() -> None:
    assert recovery.BASE_CARDINALITY == 1_489_144
    assert sum(count for _, _, count in recovery.SCOPE_COUNTS) == recovery.BASE_CARDINALITY
    assert dict((f"{side}|{kind}", count) for side, kind, count in recovery.SCOPE_COUNTS) == {
        "ASK|C2_LEVEL": 558_429,
        "ASK|C2_CONTAINER": 186_143,
        "BID|C2_LEVEL": 558_429,
        "BID|C2_CONTAINER": 186_143,
    }


def test_recovery_fixture_is_semantically_valid_but_adversarial_by_candidate_key() -> None:
    first = normalize_candidate_source_row(recovery._level_row(1, "ASK"))
    second = normalize_candidate_source_row(recovery._level_row(2, "ASK"))
    a = "C2P2-PS0-OP-A-STRICT-CONTINUITY-v2"
    b = "C2P2-PS0-OP-B-RELATIONAL-CONTINUITY-v2"
    c = "C2P2-PS0-OP-C-EPISODE-ENRICHED-CONTINUITY-v2"
    assert necessary_match_key(a, first) != necessary_match_key(a, second)
    assert necessary_match_key(b, first) == necessary_match_key(b, second)
    assert necessary_match_key(c, first) == necessary_match_key(c, second)
    assert len(first["geometry_signature"]["origin"]) >= 512
    assert len(first["relation_topology"]) == 4


def test_recovery_proposed_ceiling_is_measurement_only_and_has_25pct_margin() -> None:
    assert recovery.FROZEN_EXECUTION_STORAGE_LIMIT == 6_411_935_744
    assert recovery.R4_PARTIAL_DATABASE_BYTES == 6_415_310_848
    assert recovery.DIAGNOSTIC_STORAGE_LIMIT == 20 * 1024**3
    proposed = recovery.proposed_storage_ceiling(recovery.R4_PARTIAL_DATABASE_BYTES)
    assert proposed == 8 * 1024**3
    assert proposed >= int(recovery.R4_PARTIAL_DATABASE_BYTES * recovery.SAFETY_FACTOR)
    assert recovery.round_up(1) == 1024**3


def test_operator_decision_and_recovery_authority_preserve_reserved_boundaries() -> None:
    release = ROOT / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0"
    decision = json.loads((release / "C2P2_RS0_RUN_RECOVERY_R4_OPERATOR_DECISION_v0_1.json").read_text())
    authority = json.loads((ROOT / "registries/authority/C2P2_RS0_RUN_RECOVERY_R4_AUTHORITY_v0_1.json").read_text())
    consumption = json.loads((ROOT / "registries/authority/C2P2_RS0_REAL_SOURCE_SHADOW_RUN_CONSUMPTION_v0_4.json").read_text())
    result = json.loads((release / "C2P2_RS0_REAL_SOURCE_SHADOW_RUN_R4_RESULT_v0_1.json").read_text())
    assert decision["decision"] == "PASS"
    assert decision["real_source_execution_authority"] == "NONE"
    assert decision["fresh_run_token"] == "NONE"
    assert decision["storage_limit_change"] == "NOT_AUTHORISED"
    assert authority["state"] == "AUTHORISED_RECOVERY_ONLY"
    assert authority["real_source_read"] == "FORBIDDEN"
    assert authority["real_source_execution"] == "FORBIDDEN"
    assert authority["fresh_run_token"] == "NONE"
    assert authority["diagnostic_capacity"]["storage_limit_change"] == "NOT_AUTHORISED"
    assert consumption["execution_count_consumed"] == 1
    assert consumption["run_count_remaining"] == 0
    assert result["status"] == "BLOCKED_CAPACITY_EXCEEDED_SINGLE_USE_CONSUMED"
    assert result["selection_state"] == "NONE_SELECTED_INCOMPLETE_RUN"
    assert result["active_object_pack_id"] is None


def test_clean_successor_workflow_has_no_real_source_or_reserved_authority() -> None:
    workflow = (ROOT / ".github/workflows/c2p2-rs0-r4-capacity-recovery.yml").read_text()
    assert "recover/c2p2-rs0-run-recovery-r4-r2-20260818" in workflow
    assert "C2P2_RS0_RUN_RECOVERY_R4_OPERATOR_DECISION_v0_1.json" in workflow
    assert "C2P2_RS0_REAL_SOURCE_SHADOW_RUN_CONSUMPTION_v0_4.json" in workflow
    assert "actions/download-artifact@v4" not in workflow
    assert "Launch exactly one authorised" not in workflow
    assert "C2P2-RS0-FRESH-GRUN-R5" in workflow
    assert "NO_FRESH_R5_TOKEN_MATERIALISED" in workflow
    assert "[skip ci]" in workflow


def test_r4_terminal_packet_is_blocked_not_stale_prelaunch_state() -> None:
    release = ROOT / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0"
    gate = json.loads((release / "C2P2_RS0_POST_RUN_R4_GATE_PACKET_v0_1.json").read_text())
    assert gate["gate_id"] == "C2P2-RS0-RUN-RECOVERY-R4"
    assert gate["run_status"] == "BLOCKED_CAPACITY_EXCEEDED_SINGLE_USE_CONSUMED"
    assert gate["selection_state"] == "NONE_SELECTED_INCOMPLETE_RUN"
    assert gate["active_object_pack_id"] is None
    assert gate["c2p_activation"] == "NONE"
    assert gate["validation"] == "LOCKED_UNCONSUMED"
