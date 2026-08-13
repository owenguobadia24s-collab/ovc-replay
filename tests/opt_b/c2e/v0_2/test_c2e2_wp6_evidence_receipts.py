import json
from pathlib import Path
from tests.historical_court_record import json_at

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e2-wp6"
RUN_RECEIPT = BASE / "C2E2_WP6_RUN_EVIDENCE_RECEIPT.json"
EQUIV = BASE / "C2E2_WP6_EQUIVALENCE_PROOF.json"
COUNTS = BASE / "C2E2_WP6_POPULATION_COUNT_RECONCILIATION.json"
PRESSURE = BASE / "C2E2_WP6_CONFLICT_PRESSURE_RECEIPT.json"
COMPARATORS = BASE / "C2E2_WP6_COMPARATOR_STATUS.json"
CONSUMPTION = BASE / "C2E2_WP6_RUN_AUTH_CONSUMPTION_RECEIPT.json"
COUNTEREXAMPLES = BASE / "C2E2_WP6_COUNTEREXAMPLES.json"
CAPACITY = BASE / "C2E2_WP6_PERFORMANCE_CAPACITY_RECEIPT.json"
CANDIDATE = BASE / "C2E2_WP6_CANDIDATE_EVIDENCE_PACKET.json"
STATE = ROOT / "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_29.json"
POINTER = ROOT / "registries/implementation/c2e_v0_2/CURRENT_STATE_POINTER.json"
AUTH = ROOT / "registries/implementation/c2e_v0_2/run_authority/C2E2_SOURCE_REPLAY_AUTHORITY_REGISTRY_v0_3.json"


def load(path: Path):
    return json.loads(path.read_text())


def test_two_clean_runs_and_external_artifacts_are_preserved():
    receipt = load(RUN_RECEIPT)
    assert receipt["determinism"]["all_scientific_artifact_hashes_equal"] is True
    assert receipt["determinism"]["output_manifest_hash_equal"] is True
    assert receipt["determinism"]["logical_output_sha256"] == "18519e37a16bc1f73148f3764ec1444d1fcd36fce82e9a1d585f712fb02d6988"
    assert receipt["counts"]["frames"] == 4072
    assert receipt["counts"]["episodes"] == 92
    assert receipt["counts"]["stream_records"] == 16550
    assert receipt["capacity"]["status"] == "WITHIN_AUTHORIZED_ENVELOPE"
    assert receipt["external_artifacts"]["run_a"]["drive_file_id"] == "1ow8KUjE77trZU-NnVoSWXgDZwEN1ViTF"
    assert receipt["external_artifacts"]["run_b"]["drive_file_id"] == "1TOIghV9q6pk3euOASotYE17nYV2mwSj-"
    assert receipt["forbidden_consumption"]["validation"] == "NONE"
    assert receipt["authority"] == "INACTIVE_NONCANONICAL_SHADOW_EVIDENCE_ONLY"


def test_semantic_equivalence_proof_is_explicitly_bounded():
    proof = load(EQUIV)
    assert proof["proof_class"] == "APPROVED_SEMANTIC_EQUIVALENCE_FOR_WP6_EVIDENCE_INTEGRITY"
    assert proof["explicit_nonclaim"] == "NOT_BYTE_EQUIVALENCE_TO_CANONICAL_RUNTIME_SERIALIZED_STREAM"
    assert all(row["status"] == "PASS" for row in proof["independent_checks"])
    assert proof["independent_checks"][0]["denominator"] == 4072
    assert proof["independent_checks"][0]["mismatch_count"] == 0
    assert proof["independent_checks"][1]["matched_count"] == 488
    assert proof["independent_checks"][1]["not_evaluable_count"] == 34
    assert proof["independent_checks"][2]["conflict_count"] == 0
    assert proof["authority_effect"] == "NONE"


def test_counts_conflict_pressure_and_missingness_reconcile():
    counts = load(COUNTS)
    pressure = load(PRESSURE)
    assert counts["status"] == "PASS"
    assert all(counts["acceptance"].values())
    assert counts["lifecycle"]["membership_delta_count"] == 4072
    assert pressure["metrics"]["candidate_boundary_count"]["count"] == 8490
    assert pressure["metrics"]["candidate_not_evaluable_count"]["count"] == 34
    assert pressure["metrics"]["ambiguous_boundary_set_count"]["count"] == 0
    assert pressure["metrics"]["explicit_conflict_count"]["count"] == 0
    assert pressure["metrics"]["conflicted_episode_count"]["count"] == 0
    assert pressure["metrics"]["peer_owner_collision_count"]["count"] == 0


def test_comparators_are_read_only_and_srfd_blocker_is_not_hidden():
    comparison = load(COMPARATORS)
    assert comparison["legacy_comparator"]["status"] == "COMPLETED_READ_ONLY"
    assert comparison["legacy_comparator"]["denominator"] == 4072
    assert comparison["legacy_comparator"]["disagreement_count"] == 3524
    assert comparison["srfd_comparator"]["status"] == "UNAVAILABLE_CURRENT_LAWFUL_ROUTE"
    assert comparison["srfd_comparator"]["comparison_performed"] is False
    assert comparison["srfd_comparator"]["new_run_authority"] == "NONE"
    assert comparison["authority_effect"] == "NONE"


def test_counterexamples_capacity_and_candidate_packet_are_present():
    counterexamples = load(COUNTEREXAMPLES)
    capacity = load(CAPACITY)
    candidate = load(CANDIDATE)
    assert len(counterexamples["examples"]) >= 8
    assert capacity["status"] == "PASS"
    assert capacity["capacity_status"] == "WITHIN_T0"
    assert candidate["scientific_disposition"] == "EVIDENCE_ONLY_NO_WINNER_NO_PROMOTION"
    assert candidate["authority_effect"] == "NONE"


def test_single_use_authority_is_consumed_append_only_without_activation():
    consumption = load(CONSUMPTION)
    registry = load(AUTH)
    pointer = json_at("4adec4ab6d5f6a41e153be06d48f1cd2537fa927", POINTER)
    state = load(STATE)
    assert consumption["status"] == "CONSUMED_FOR_RUN"
    assert consumption["reuse_prohibited"] is True
    assert consumption["no_further_real_source_execution_under_token"] is True
    assert registry["active_runtime_authority"] == "NONE_TOKEN_CONSUMED"
    assert registry["unconsumed_tokens"] == []
    assert pointer["replacement_run_token_status"] == "CONSUMED_FOR_RUN"
    assert pointer["active_c2e"] == "NONE"
    assert pointer["active_boundary_pack"] == "NONE"
    assert state["authority"]["c2e_activation"] == "DENIED"
    assert state["status"] == "QA_REVIEW"
