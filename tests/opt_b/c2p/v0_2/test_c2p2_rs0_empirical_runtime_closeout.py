from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
REGISTRY = ROOT / "registries/opt_b/c2p/v0_2/research/C2P2_RS0_EMPIRICAL_RUNTIME_BINDING_v0_1.json"
SCHEMA = ROOT / "schemas/opt_b/c2p/v0_2/c2p_rs0_empirical_runtime_v0_1.json"
CANDIDATES = ROOT / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-ps0/C2P2_PS0_OBJECTPACK_CANDIDATES_v0_3.json"
CURRENTNESS = ROOT / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_CANDIDATE_CURRENTNESS_v0_2.json"
GATE = ROOT / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_FRESH_GRUN_GATE_PACKET_v0_1.json"
QA = ROOT / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_EMPIRICAL_RUNTIME_QA_v0_1.json"
CLOSEOUT = ROOT / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_EMPIRICAL_RUNTIME_CLOSEOUT_v0_1.json"


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _logical_hash(record: dict, field: str) -> str:
    payload = {key: value for key, value in record.items() if key != field}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256(raw).hexdigest()


def test_runtime_binding_is_closed_schema_valid_and_hash_exact() -> None:
    binding = _read(REGISTRY)
    schema = _read(SCHEMA)
    assert schema["additionalProperties"] is False
    assert set(binding) == set(schema["required"])
    assert binding["schema"] == schema["properties"]["schema"]["const"]
    assert binding["packet_id"] == schema["properties"]["packet_id"]["const"]
    assert binding["logical_sha256"] == _logical_hash(binding, "logical_sha256")
    implementation = ROOT / binding["implementation"]["path"]
    assert sha256(implementation.read_bytes()).hexdigest() == binding["implementation"]["sha256"]
    assert binding["status"] == "CLOSED_RESEARCH_NONACTIVE"
    assert binding["real_source_launch"] == "DENIED_UNTIL_FRESH_GRUN_PASS"
    assert binding["grun_consumed"] is False
    assert binding["selection_state"] == "COMPARATIVE_SET_ONLY_NO_WINNER"
    assert binding["active_object_pack_id"] is None


def test_final_generation_hashes_runtime_binding_and_nonactivation_are_exact() -> None:
    generation = _read(CANDIDATES)
    binding = _read(REGISTRY)
    assert generation["generation_logical_sha256"] == _logical_hash(generation, "generation_logical_sha256")
    assert generation["generation_id"] == "C2P2-PS0-EMPIRICAL-RUNTIME-GENERATION-v3"
    assert generation["selection_state"] == "NONE_SELECTED"
    assert generation["active_object_pack_id"] is None
    assert generation["real_source_evaluated"] is False
    assert generation["grun_currentness"]["fresh_grun_required"] is True
    assert generation["grun_currentness"]["runtime_closeout_complete"] is True
    for candidate in generation["candidates"]:
        assert candidate["candidate_logical_hash"] == _logical_hash(candidate, "candidate_logical_hash")
        assert candidate["activation_eligible"] is False
        assert candidate["real_source_execution_eligible"] is False
        assert candidate["real_source_launch_authority"] == "DENIED_UNTIL_FRESH_GRUN_PASS"
        assert candidate["runtime_binding"]["status"] == "EMPIRICAL_RUNTIME_CLOSED"
        assert candidate["runtime_binding"]["execution_ready"] is True
        assert candidate["runtime_binding"]["implementation_sha256"] == binding["implementation"]["sha256"]
        assert candidate["semantic_candidate_id"].endswith("-v2")
        assert candidate["supersedes_candidate_id"] == candidate["semantic_candidate_id"]


def test_currentness_and_fresh_grun_packet_stop_before_real_source_launch() -> None:
    currentness = _read(CURRENTNESS)
    gate = _read(GATE)
    assert currentness["logical_sha256"] == _logical_hash(currentness, "logical_sha256")
    assert currentness["status"] == "FINAL_TECHNICAL_GENERATION_FROZEN_FRESH_GRUN_REQUIRED"
    assert currentness["old_grun_token_disposition"] == "PRESERVED_UNCONSUMED_NOT_APPLICABLE_TO_FINAL_GENERATION"
    assert currentness["fresh_grun_required"] is True
    assert currentness["real_source_launch"] == "FORBIDDEN_UNTIL_FRESH_OPERATOR_GRUN_PASS"
    assert currentness["active_object_pack_id"] is None
    assert currentness["validation"] == "LOCKED_UNCONSUMED"

    assert gate["gate_id"] == "C2P2-RS0-FRESH-GRUN"
    assert gate["gate_classification"] == "OPERATOR_REQUIRED"
    assert gate["status"] == "AWAITING_OPERATOR_DECISION"
    assert gate["current_denials"]["real_source_launch"] == "DENIED"
    assert gate["current_denials"]["grun_consumption"] == "DENIED"
    assert gate["requested_authority"]["objectpack_selection"] == "NONE"
    assert gate["requested_authority"]["c2p_activation"] == "NONE"
    assert gate["requested_authority"]["validation"] == "LOCKED_UNCONSUMED"
    assert gate["immutable_prior_grun"]["execution_count_consumed"] == 0


def test_qa_closeout_is_exact_and_stops_at_fresh_grun() -> None:
    qa = _read(QA)
    closeout = _read(CLOSEOUT)
    assert qa["status"] == "PASS"
    assert qa["tests"] == [
        "LOCAL_RUNTIME_AND_CLOSEOUT_TARGETED_20_PASSED",
        "LOCAL_C2P_SURFACE_129_PASSED",
        "LOCAL_REPOSITORY_SUITE_4024_PASSED_2_SKIPPED_687_SUBTESTS_PASSED",
    ]
    assert qa["integration_assurance"]["github_tests_run"] == 32034956759
    assert qa["integration_assurance"]["github_tiered_run"] == 32034956762
    assert qa["integration_assurance"]["vit_siq_profile_merge_readiness"] == "PASS"
    assert qa["unresolved_issues"] == [
        "FRESH_GRUN_OPERATOR_DECISION_REQUIRED_BEFORE_REAL_SOURCE_LAUNCH",
    ]
    assert closeout["implementation_commit"] == "632893451279dd52beddbd5915edca81ea45badb"
    assert closeout["pull_request"] == 1090
    assert closeout["old_grun_token_consumed"] is False
    assert closeout["final_v3_real_source_execution_eligible"] is False
    assert closeout["mandatory_stop"] == "C2P2-RS0-FRESH-GRUN"
