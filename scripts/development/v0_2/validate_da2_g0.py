from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

BASELINE = ROOT / "registries/development/v0_2/OVC_DA2_WORKFLOW_ADMISSION_BASELINE_v0_2.json"
CLASSIFICATIONS = ROOT / "registries/development/v0_2/OVC_DA2_WORKFLOW_CLASSIFICATION_REGISTRY_v0_2.json"
EXTERNAL = ROOT / "docs/releases/development-acceleration-v0-2/da2-g0/DA2_G0_RAW_EVIDENCE_REFERENCE.json"
QA = ROOT / "docs/releases/development-acceleration-v0-2/da2-g0/DA2_G0_QA_PACKET.json"
DECISION = ROOT / "docs/releases/development-acceleration-v0-2/da2-g0/DA2_G0_COMPLETION_DECISION.json"
INCIDENT = ROOT / "docs/releases/development-acceleration-v0-2/da2-g0/DA2_G0_INCIDENT_RECORD.json"
PROGRAMME = ROOT / "registries/development/v0_2/OVC_DEVELOPMENT_ACCELERATION_V0_2_PROGRAMME_REGISTRY_v0_1.json"
NEXT_GATE = ROOT / "docs/releases/development-acceleration-v0-2/da2-wp1/DA2_G1_GATE_PACKET.json"


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def main() -> int:
    for path in (BASELINE, CLASSIFICATIONS, EXTERNAL, QA, DECISION, INCIDENT, PROGRAMME, NEXT_GATE):
        if not path.is_file():
            raise AssertionError(f"missing DA2 file: {path.relative_to(ROOT)}")

    baseline = load(BASELINE)
    classifications = load(CLASSIFICATIONS)
    external = load(EXTERNAL)
    qa = load(QA)
    decision = load(DECISION)
    incident = load(INCIDENT)
    programme = load(PROGRAMME)
    next_gate = load(NEXT_GATE)

    recorded = baseline["logical_sha256"]
    unhashed = dict(baseline)
    del unhashed["logical_sha256"]
    assert hashlib.sha256(canonical_bytes(unhashed)).hexdigest() == recorded

    assert baseline["status"] == "PASS"
    assert baseline["qa_recommendation"] == "PASS"
    assert baseline["workflow_mutation_authority"] == "DENIED"
    assert baseline["ruleset_mutation_authority"] == "DENIED"
    assert baseline["aggregate"]["run_count"] == 91
    assert sum(len(subject["runs"]) for subject in baseline["subjects"]) == 91
    assert len({(subject["commit_sha"], row[0]) for subject in baseline["subjects"] for row in subject["runs"]}) == 91
    assert baseline["aggregate"]["classification_counts"] == {
        "EXPECTED_SKIPPED": 10,
        "RELEVANT_OPTIONAL": 1,
        "REQUIRED": 4,
        "UNRELATED": 76,
    }
    assert baseline["aggregate"]["unrelated_failed_runs"] == 4
    assert baseline["aggregate"]["duplicate_complete_suite_runs"] == 2
    assert baseline["aggregate"]["skipped_job_timing_anomalies"] == 2
    assert baseline["reproducibility"]["estimated_values_used"] is False
    assert baseline["reproducibility"]["manifest_verified"] is True
    assert baseline["reproducibility"]["secret_scan"] == "PASS"
    assert baseline["reproducibility"]["required_source_identities_complete"] is True
    assert baseline["source_build_logical_sha256"] == "03295d1e0e9a9ac080649514d64e88df6dc144627399c0948d5d625ed371b8cc"

    for required in baseline["aggregate"]["required_runs"]:
        source = required["check_source"]
        assert source["suite_app_id"] == 15368
        assert source["suite_app_slug"] == "github-actions"
        assert {"app_id": 15368, "app_slug": "github-actions"} in source["check_run_apps"]

    anomalies = [item for subject in baseline["subjects"] for item in subject["timing_anomalies"]]
    assert len(anomalies) == 2
    assert all(item["resolution"] == "DURATION_NOT_EVALUABLE_NO_ESTIMATE_USED" for item in anomalies)

    assert external["sha256"] == "182ae439c0c12f054438edee0c8d2c03e2db79713ae498dd41258c2b17147158"
    assert external["manifest_sha256"] == "37311fb333e54cf90da32c734f57dbda5c21ac98e9507ac6f836cafc7927fafc"
    assert external["google_drive_file_id"] == "1sPYYSukegZGFGzcyFg0TzLDBk2Nd6dsp"
    assert external["repository_storage"] == "REFERENCE_ONLY_RAW_ZIP_NOT_COMMITTED"

    assert qa["status"] == "PASS"
    assert qa["qa_recommendation"] == "PASS"
    assert qa["blocking_issues"] == []
    assert qa["warnings"] == []
    assert decision["decision"] == "PASS"
    assert decision["authority_delta"] == "ACCEPT_READ_ONLY_CI_ADMISSION_BASELINE_EVIDENCE"
    assert incident["disposition"] == "SUPERSEDED_PRESERVED"
    assert programme["completed_packets"][0] == "DA2-00"

    if programme["status"] == "COMPLETED":
        assert programme["completed_packets"] == ["DA2-00", "DA2-WP1"]
        assert programme["current_packet"] is None
        assert programme["completion"]["gate_id"] == "DA2-G1"
        assert programme["completion"]["blockers"] == []
        assert programme["completion"]["next_packet"] is None
    else:
        assert programme["current_packet"]["packet_id"] == "DA2-WP1"
        assert programme["current_packet"]["status"] == "GATE_READY"
        assert programme["current_packet"]["authority_required"] == "OPERATOR_REQUIRED"

    assert next_gate["workflow_mutation_active"] is False
    assert next_gate["ruleset_mutation_active"] is False
    assert next_gate["operator_decision_required"] is True
    assert classifications["required_context_sources"]["tests"] == {"app_id": 15368, "app_slug": "github-actions"}

    print("DA2-G0 validation PASS; exact baseline preserved through programme completion")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
