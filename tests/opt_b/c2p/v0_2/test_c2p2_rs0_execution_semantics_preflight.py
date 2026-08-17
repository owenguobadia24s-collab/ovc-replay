from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]

CANDIDATES = ROOT / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-ps0/C2P2_PS0_OBJECTPACK_CANDIDATES_v0_1.json"
BLOCKER = ROOT / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_EXECUTION_OBJECTPACK_SEMANTICS_BLOCKER_v0_1.json"
DECISION = ROOT / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_GSEM_OPERATOR_DECISION_v0_1.json"
REMEDIATION_AUTHORITY = ROOT / "registries/authority/C2P2_RS0_GSEM_REMEDIATION_AUTHORITY_v0_1.json"
EXECUTION_STATE = ROOT / "registries/implementation/c2p_v0_2/C2P2_RS0_EXECUTION_STATE_v0_1.json"
PROGRAMME_STATE = ROOT / "registries/implementation/c2p_v0_2/C2P2_RS0_STATE_v0_1.json"
CORE_PACK_REGISTRY = ROOT / "registries/opt_b/c2p/v0_2/OBJECT_PACK_REGISTRY_v0_2.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_ps0_b_and_c_historical_generation_preserves_original_unbound_identity_semantics() -> None:
    candidates = {row["candidate_id"]: row for row in _load(CANDIDATES)["candidates"]}
    b = candidates["C2P2-PS0-OP-B-RELATIONAL-CONTINUITY-v1"]
    c = candidates["C2P2-PS0-OP-C-EPISODE-ENRICHED-CONTINUITY-v1"]

    assert "owner_declared_geometry_compatible" in b["identity_predicates"]
    assert "owner_declared_geometry_compatible" in c["identity_predicates"]
    assert "c2e_lineage_compatible_if_declared" in c["identity_predicates"]
    assert b["candidate_logical_hash"] == "eb6cc46d9f22ef3c6257f30eb61a16030b7cf493acf07c436b8ba904a8adb770"
    assert c["candidate_logical_hash"] == "1341b42b39638f9fc10bb84b841597c9254353270240ff683be264c061a24c17"


def test_core_registry_does_not_smuggle_empirical_objectpack_activation() -> None:
    registry = _load(CORE_PACK_REGISTRY)
    assert registry["active_object_pack_id"] is None
    assert registry["entries"]
    assert all(entry["status"] == "SYNTHETIC_ONLY_NONEMPIRICAL" for entry in registry["entries"])
    assert all(entry["real_source_forbidden"] is True for entry in registry["entries"])


def test_historical_execution_blocker_is_preserved_while_current_state_advances_under_gsem_pass() -> None:
    blocker = _load(BLOCKER)
    decision = _load(DECISION)
    remediation = _load(REMEDIATION_AUTHORITY)
    state = _load(EXECUTION_STATE)
    programme = _load(PROGRAMME_STATE)

    assert blocker["gate_id"] == "C2P2-RS0-GSEM-UNBLOCK"
    assert blocker["recommended_decision"] == "PASS"
    assert blocker["tests"]["run_launched"] is False
    assert blocker["qa"]["recommendation"] == "BLOCK_EXECUTION_RETURN_TO_OPERATOR"
    historical_expected = {
        "RS0_OBJECTPACK_IDENTITY_SEMANTICS_NOT_MECHANICALLY_FROZEN",
        "RS0_EMPIRICAL_OBJECTPACK_RUNTIME_NOT_MATERIALISED",
        "RS0_COMPARATIVE_RUN_CANNOT_LAWFULLY_DEGRADE_TO_A_ONLY",
    }
    assert {row["code"] for row in blocker["blocking_findings"]} == historical_expected

    assert decision["decision"] == "PASS"
    assert decision["operator_instruction"] == "OVC APPROVE C2P2-RS0-GSEM-UNBLOCK PASS"
    assert remediation["state"] == "AUTHORISED"
    assert remediation["grun_token"]["may_consume_during_remediation"] is False

    current_execution_blockers = {"FRESH_GRUN_PASS_REQUIRED_BEFORE_REAL_SOURCE_LAUNCH"}
    assert set(state["blockers"]) == current_execution_blockers
    assert state["status"] == "GATE_READY_AWAITING_OPERATOR"
    assert state["packet_id"] == "C2P2-RS0-EMPIRICAL-RUNTIME-CLOSEOUT"
    assert state["run_authority_consumed"] is False
    assert state["run_count_remaining"] == 1
    assert state["next_packet"] == "C2P2-RS0-REAL-SOURCE-SHADOW-RUN_AFTER_FRESH_GRUN_PASS"
    assert state["mandatory_stop"] == "C2P2-RS0-FRESH-GRUN"

    assert programme["status"] == "GATE_READY_AWAITING_OPERATOR"
    assert programme["packet_id"] == "C2P2-RS0-EMPIRICAL-RUNTIME-CLOSEOUT"
    assert set(programme["blockers"]) == {"FRESH_GRUN_PASS_REQUIRED_BEFORE_REAL_SOURCE_LAUNCH"}
    assert programme["authority"]["gsem_operator_pass"] == "PASS"
    assert programme["authority"]["prior_grun_v1"] == "PASS_TOKEN_UNCONSUMED_NOT_APPLICABLE_TO_FINAL_V3"
    assert programme["authority"]["successor_candidate_real_source_launch"] == "DENIED_UNTIL_FRESH_GRUN_PASS"
    assert programme["authority"]["active_object_pack"] is None
    assert programme["selection_state"] == "COMPARATIVE_SET_ONLY_NO_WINNER"
    assert programme["mandatory_stop"] == "C2P2-RS0-FRESH-GRUN"
