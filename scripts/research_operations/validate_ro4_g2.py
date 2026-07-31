from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/research-operations-foundation-v0-4"
REQUIRED = [
    ROOT / "src/ovc/research_operations/v0_4/matrix_persistence_conflict.py",
    ROOT / "scripts/research_operations/build_ro4_matrix_persistence_conflict.py",
    ROOT / "tests/research_operations/v0_4/test_ro4_g2_matrix_persistence_conflict.py",
    ROOT / "schemas/research_operations/v0_4/cross_scale_alignment_projection_v0_1.schema.json",
    ROOT / "schemas/research_operations/v0_4/ro4_g2_evidence_manifest_v0_1.schema.json",
    ROOT / "fixtures/research_operations/v0_4/RO4_G2_SYNTHETIC_ASSURANCE_FIXTURE_v0_1.json",
    BASE / "ro4-wp2/RO4_G2_EVIDENCE_MANIFEST.json",
    BASE / "ro4-wp2/RO4_G2_FULL_BUILD_BENCHMARK.json",
    BASE / "ro4-wp2/RO4_G2_DETERMINISM_RECEIPT.json",
    BASE / "ro4-wp2/RO4_WP2_IMPLEMENTATION_PACKET.json",
    BASE / "ro4-g2/RO4_G2_QA_PACKET.json",
    BASE / "ro4-g2/RO4_G2_GATE_PACKET.json",
]
EXPECTED_G1 = "a6add1c87233d88b400b53ceec4efcd8c06c80d7cb4e4cfa83c73e05743bf200"
EXPECTED_G2 = "eb5435443be26e956334c4aedd12c2a5280fc815f014f24bd74b064bf4e6eaeb"
EXPECTED_COUNTS = {
    "conflict_runs": 370,
    "cross_scale_projections": 191670,
    "matrices": 60,
    "persistence_runs": 678322,
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED if not path.is_file()]
    if missing:
        raise SystemExit("MISSING_RO4_G2_FILES:" + ",".join(missing))
    manifest = load(BASE / "ro4-wp2/RO4_G2_EVIDENCE_MANIFEST.json")
    if manifest.get("source_g1_logical_hash") != EXPECTED_G1:
        raise SystemExit("G2_PARENT_G1_HASH_MISMATCH")
    if manifest.get("logical_hash") != EXPECTED_G2:
        raise SystemExit("G2_LOGICAL_HASH_MISMATCH")
    if manifest.get("counts") != EXPECTED_COUNTS:
        raise SystemExit("G2_COUNT_RECONCILIATION_FAILURE")
    if manifest.get("validation_consumption") != "LOCKED_UNCONSUMED":
        raise SystemExit("VALIDATION_DENIAL_NOT_PRESERVED")
    if manifest.get("composite_or_winner") != "PROHIBITED":
        raise SystemExit("COMPOSITE_OR_WINNER_NOT_PROHIBITED")
    if manifest.get("count_presentation") != "EXACT_COUNT_WITH_VISIBLE_ELIGIBLE_DENOMINATOR":
        raise SystemExit("COUNT_ONLY_PRESENTATION_NOT_FROZEN")
    if manifest.get("matched_real_controls") != "REQUIRED_AND_MATERIALISED_FOR_ALL_CONFLICT_RUNS":
        raise SystemExit("MATCHED_REAL_CONTROL_REQUIREMENT_FAILED")
    artifacts = {item["artifact_type"]: item for item in manifest.get("artifacts", [])}
    if set(artifacts) != {"matrices", "persistence", "conflicts", "cross_scale"}:
        raise SystemExit("G2_ARTIFACT_SET_MISMATCH")
    if sum(item["size_bytes"] for item in artifacts.values()) != 103556019:
        raise SystemExit("G2_EXTERNAL_BYTE_INVENTORY_MISMATCH")
    benchmark = load(BASE / "ro4-wp2/RO4_G2_FULL_BUILD_BENCHMARK.json")
    if benchmark.get("status") != "PASS" or benchmark.get("logical_hash") != EXPECTED_G2:
        raise SystemExit("G2_BENCHMARK_FAILURE")
    if benchmark.get("runtime_seconds", 10000) > 600 or benchmark.get("peak_rss_bytes", 10**12) > 8 * 1024**3:
        raise SystemExit("G2_PERFORMANCE_BOUND_FAILURE")
    receipt = load(BASE / "ro4-wp2/RO4_G2_DETERMINISM_RECEIPT.json")
    if receipt.get("status") != "PASS_BYTE_IDENTICAL_ALL_FOUR_DERIVED_ARTIFACTS":
        raise SystemExit("G2_DETERMINISM_FAILURE")
    if not all(receipt.get("artifact_hashes_equal", {}).values()):
        raise SystemExit("G2_ARTIFACT_RERUN_HASH_FAILURE")
    fixture = load(ROOT / "fixtures/research_operations/v0_4/RO4_G2_SYNTHETIC_ASSURANCE_FIXTURE_v0_1.json")
    if not fixture.get("synthetic") or fixture.get("operator_evidence") is not False:
        raise SystemExit("G2_FIXTURE_AUTHORITY_FAILURE")
    gate = load(BASE / "ro4-g2/RO4_G2_GATE_PACKET.json")
    if gate.get("authority_delta") != "LOCAL_READ_ONLY_DERIVED" or gate.get("operator_decision_required") is not False:
        raise SystemExit("G2_AUTHORITY_DELTA_FAILURE")
    if gate.get("status") not in {"QA_REVIEW", "APPROVED_PENDING_FINAL_HEAD_CHECKS_AND_MERGE"}:
        raise SystemExit("G2_GATE_STATUS_FAILURE")
    qa = load(BASE / "ro4-g2/RO4_G2_QA_PACKET.json")
    if qa.get("blocking_issues"):
        raise SystemExit("G2_BLOCKING_ISSUE_PRESENT")
    forbidden_external = list(ROOT.rglob("*.jsonl.gz")) + list(ROOT.rglob("*.sqlite"))
    if forbidden_external:
        raise SystemExit("G2_EXTERNAL_ARTIFACT_BYTES_COMMITTED:" + ",".join(str(path.relative_to(ROOT)) for path in forbidden_external))
    print("PASS: RO4-G2 matrix, persistence, conflict and cross-scale evidence is deterministic, count-only, source-bound and non-activating")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
