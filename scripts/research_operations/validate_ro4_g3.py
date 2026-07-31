from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/research-operations-foundation-v0-4"
REQUIRED = [
    ROOT / "src/ovc/research_operations/v0_4/sequence_recurrence.py",
    ROOT / "src/ovc/research_operations/v0_4/sequence_workspace.py",
    ROOT / "src/ovc/research_operations/v0_4/sequence_materialize.py",
    ROOT / "src/ovc/research_operations/v0_4/sequence_finalize.py",
    ROOT / "src/ovc/research_operations/v0_4/sequence_validate.py",
    ROOT / "scripts/research_operations/build_ro4_sequence_recurrence.py",
    ROOT / "tests/research_operations/v0_4/test_ro4_g3_sequence_recurrence.py",
    ROOT / "fixtures/research_operations/v0_4/RO4_G3_SYNTHETIC_ASSURANCE_FIXTURE_v0_1.json",
    ROOT / "schemas/research_operations/v0_4/ro4_g3_evidence_manifest_v0_1.schema.json",
    ROOT / "schemas/research_operations/v0_4/ro4_g3_real_control_ledger_v0_1.schema.json",
    ROOT / "schemas/research_operations/v0_4/ro4_g3_blinded_review_batch_v0_1.schema.json",
    BASE / "ro4-wp3/RO4_G3_EVIDENCE_MANIFEST.json",
    BASE / "ro4-wp3/RO4_G3_SIGNATURE_DIVERSITY_AUDIT.json",
    BASE / "ro4-wp3/RO4_G3_MACHINE_ABLATION_ASSURANCE.json",
    BASE / "ro4-wp3/RO4_G3_PD_ISOLATION_ASSURANCE.json",
    BASE / "ro4-wp3/RO4_G3_OPERATION_MODE_ASSURANCE.json",
    BASE / "ro4-wp3/RO4_G3_DETERMINISM_RECEIPT.json",
    BASE / "ro4-wp3/RO4_G3_FULL_BUILD_BENCHMARK.json",
    BASE / "ro4-wp3/RO4_G3_INCREMENTAL_REBUILD_RECEIPT.json",
    BASE / "ro4-wp3/RO4_WP3_IMPLEMENTATION_PACKET.json",
    BASE / "ro4-g3/RO4_G3_QA_PACKET.json",
    BASE / "ro4-g3/RO4_G3_GATE_PACKET.json",
]
EXPECTED_G1 = "a6add1c87233d88b400b53ceec4efcd8c06c80d7cb4e4cfa83c73e05743bf200"
EXPECTED_G2 = "eb5435443be26e956334c4aedd12c2a5280fc815f014f24bd74b064bf4e6eaeb"
EXPECTED_G3 = "9271f3b7e25e06c49e8f9864fda7edff8adb333289886d05c89ebaf730761097"
EXPECTED_COUNTS = {
    "window_count": 4093390,
    "recurrence_candidate_count": 9147,
    "recurrence_member_count": 25191,
    "real_control_count": 9147,
    "operator_batch_count": 60,
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED if not path.is_file()]
    if missing:
        raise SystemExit("MISSING_RO4_G3_FILES:" + ",".join(missing))
    manifest = load(BASE / "ro4-wp3/RO4_G3_EVIDENCE_MANIFEST.json")
    if manifest.get("source_g1_logical_hash") != EXPECTED_G1 or manifest.get("source_g2_logical_hash") != EXPECTED_G2:
        raise SystemExit("G3_PARENT_HASH_MISMATCH")
    if manifest.get("logical_hash") != EXPECTED_G3:
        raise SystemExit("G3_LOGICAL_HASH_MISMATCH")
    for key, value in EXPECTED_COUNTS.items():
        if manifest.get(key) != value:
            raise SystemExit(f"G3_COUNT_MISMATCH:{key}")
    if manifest.get("sample_state") != "FULL_POPULATION_NO_SAMPLING":
        raise SystemExit("G3_UNDECLARED_SAMPLE")
    if manifest.get("validation_consumption") != "LOCKED_UNCONSUMED":
        raise SystemExit("VALIDATION_DENIAL_NOT_PRESERVED")
    if manifest.get("pd_population_merge") != "DENIED" or manifest.get("promotion_path") != "DENIED":
        raise SystemExit("PD_OR_PROMOTION_BOUNDARY_FAILURE")
    if manifest.get("semantic_authority") != "NONE" or manifest.get("synthetic_controls_operator_facing") != 0:
        raise SystemExit("SEMANTIC_OR_SYNTHETIC_CONTROL_AUTHORITY_FAILURE")
    if manifest.get("full_population_diversity_status") != "PASS" or manifest.get("ro4_g4_acknowledgement_required") is not False:
        raise SystemExit("G3_DIVERSITY_OR_ACKNOWLEDGEMENT_FAILURE")
    artifacts = {item["artifact_type"]: item for item in manifest.get("artifacts", [])}
    expected_artifacts = {
        "blinded_batch", "candidates", "diversity_audit", "machine_ablation_assurance",
        "operation_mode_assurance", "pd_isolation_assurance", "population_inventory",
        "real_controls", "review_signatures", "sealed_answer_key",
        "sequence_population_workspace", "vocabulary_assurance",
    }
    if set(artifacts) != expected_artifacts:
        raise SystemExit("G3_ARTIFACT_SET_MISMATCH")
    workspace = artifacts["sequence_population_workspace"]
    if workspace.get("byte_identity") != "LOGICAL_ONLY_REPLACEABLE_SQLITE" or workspace.get("logical_hash") != "120459556ba0495519ef88aed96d5cd591b2af708cca4137e7df6554a98a9d7d":
        raise SystemExit("G3_WORKSPACE_IDENTITY_SCOPE_FAILURE")
    diversity = load(BASE / "ro4-wp3/RO4_G3_SIGNATURE_DIVERSITY_AUDIT.json")
    full = diversity.get("full_population", {})
    if full.get("status") != "PASS" or full.get("normalized_shannon_entropy", 0) < 0.55:
        raise SystemExit("G3_DIVERSITY_FAILURE")
    if full.get("top_1", {}).get("count", 10**9) > 0.12 * full.get("candidate_count", 0):
        raise SystemExit("G3_TOP1_CONCENTRATION_FAILURE")
    if full.get("top_5", {}).get("count", 10**9) > 0.30 * full.get("candidate_count", 0):
        raise SystemExit("G3_TOP5_CONCENTRATION_FAILURE")
    if full.get("top_10", {}).get("count", 10**9) > 0.45 * full.get("candidate_count", 0):
        raise SystemExit("G3_TOP10_CONCENTRATION_FAILURE")
    machine = load(BASE / "ro4-wp3/RO4_G3_MACHINE_ABLATION_ASSURANCE.json")
    if machine.get("result") != "PASS" or machine.get("operator_surface_state") != "DENIED" or machine.get("operator_facing_artifacts"):
        raise SystemExit("G3_MACHINE_ABLATION_BOUNDARY_FAILURE")
    pd = load(BASE / "ro4-wp3/RO4_G3_PD_ISOLATION_ASSURANCE.json")
    if pd.get("result") != "PASS" or any(pd.get(key) != "DENIED" for key in ("population_merge", "joint_ranking", "joint_review_batch", "evidence_bridge")):
        raise SystemExit("G3_PD_ISOLATION_FAILURE")
    mode = load(BASE / "ro4-wp3/RO4_G3_OPERATION_MODE_ASSURANCE.json")
    if mode.get("result") != "PASS" or mode.get("replay_to_prospective_translation") != "DENIED" or mode.get("post_cutoff_identifier_access") != "ABSENT_NOT_HIDDEN":
        raise SystemExit("G3_OPERATION_MODE_FAILURE")
    determinism = load(BASE / "ro4-wp3/RO4_G3_DETERMINISM_RECEIPT.json")
    if determinism.get("status") != "PASS_CANONICAL_EVIDENCE_BYTE_IDENTICAL_AND_WORKSPACE_LOGICAL_IDENTICAL":
        raise SystemExit("G3_DETERMINISM_FAILURE")
    if not determinism.get("logical_hash_equal") or not all(determinism.get("canonical_evidence_artifact_hashes_equal", {}).values()) or not determinism.get("workspace_logical_hash_equal"):
        raise SystemExit("G3_RERUN_IDENTITY_FAILURE")
    benchmark = load(BASE / "ro4-wp3/RO4_G3_FULL_BUILD_BENCHMARK.json")
    if benchmark.get("status") != "PASS" or benchmark.get("full_independent_rebuild_runtime_seconds", 10000) > 900 or benchmark.get("peak_rss_bytes", 10**12) > 8 * 1024**3 or benchmark.get("existing_sequence_lookup_p95_seconds", 100) > 2:
        raise SystemExit("G3_PERFORMANCE_BOUND_FAILURE")
    if benchmark.get("max_calendar_partition_count", 100001) > benchmark.get("window_cap", 100000):
        raise SystemExit("G3_WINDOW_CAP_FAILURE")
    incremental = load(BASE / "ro4-wp3/RO4_G3_INCREMENTAL_REBUILD_RECEIPT.json")
    if incremental.get("status") != "PASS" or not incremental.get("unchanged_partition_hashes_preserved") or incremental.get("workspace_logical_hash_before") != incremental.get("workspace_logical_hash_after"):
        raise SystemExit("G3_INCREMENTAL_REBUILD_FAILURE")
    fixture = load(ROOT / "fixtures/research_operations/v0_4/RO4_G3_SYNTHETIC_ASSURANCE_FIXTURE_v0_1.json")
    if not fixture.get("synthetic") or fixture.get("operator_evidence") is not False:
        raise SystemExit("G3_FIXTURE_AUTHORITY_FAILURE")
    gate = load(BASE / "ro4-g3/RO4_G3_GATE_PACKET.json")
    if gate.get("authority_delta") != "NON_CANONICAL_RESEARCH_CANDIDATE" or gate.get("operator_decision_required") is not False:
        raise SystemExit("G3_AUTHORITY_DELTA_FAILURE")
    if gate.get("status") not in {"QA_REVIEW", "APPROVED_PENDING_FINAL_HEAD_CHECKS_AND_MERGE", "APPROVED_MERGE_READY_AFTER_FINAL_HEAD_CI"}:
        raise SystemExit("G3_GATE_STATUS_FAILURE")
    qa = load(BASE / "ro4-g3/RO4_G3_QA_PACKET.json")
    if qa.get("blocking_issues"):
        raise SystemExit("G3_BLOCKING_ISSUE_PRESENT")
    active_search_roots = [ROOT / "src", ROOT / "fixtures/research_operations/v0_4", BASE]
    forbidden_external = [path for search_root in active_search_roots for pattern in ("*.jsonl.gz", "*.sqlite", "*.db", "*.parquet") for path in search_root.rglob(pattern)]
    if forbidden_external:
        raise SystemExit("G3_EXTERNAL_ARTIFACT_BYTES_COMMITTED:" + ",".join(str(path.relative_to(ROOT)) for path in forbidden_external))
    source_text = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "src/ovc/research_operations/v0_4").glob("sequence_*.py"))
    if "ACTIVE_VALIDATION" in source_text:
        raise SystemExit("G3_FORBIDDEN_VALIDATION_AUTHORITY_IN_RUNTIME")
    print("PASS: RO4-G3 sequence and recurrence evidence is full-population, deterministic, diverse, controlled, PD-isolated and non-promotable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
