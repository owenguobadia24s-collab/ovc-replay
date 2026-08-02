#!/usr/bin/env python3
"""Validate DA-WP5 deterministic compact evidence export and authority boundaries."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ovc.development.evidence_export import (  # noqa: E402
    ExportFile,
    ExportRequest,
    build_plan,
    execute_export,
    load_profile,
    load_request,
)
from ovc.development.identity import canonical_json_bytes  # noqa: E402

BASELINE = "544dc2f6477ce415321f9419a62586fcffa0d02c"
PROFILE_ID = "OVC.DEVELOPMENT.ACCELERATION.COMPACT-EVIDENCE-EXPORT.v0.1"
REQUIRED = [
    "contracts/development/OVC_COMPACT_EVIDENCE_EXPORT_CONTRACT_v0_1.md",
    "schemas/development/compact_evidence_export_profile_v0_1.schema.json",
    "schemas/development/compact_evidence_export_request_v0_1.schema.json",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_EVIDENCE_EXPORT_PROFILE_v0_1.json",
    "src/ovc/development/evidence_export.py",
    "scripts/development/run_da_wp5_export.py",
    "fixtures/development/evidence_export/export_request_pass_v0_1.json",
    "fixtures/development/evidence_export/export_request_block_v0_1.json",
    "tests/development/test_evidence_export.py",
    "docs/releases/development-acceleration-v0-1/da-g5/DA_WP5_IMPLEMENTATION_PACKET.json",
    "docs/releases/development-acceleration-v0-1/da-g5/DA_G5_QA_PACKET.json",
    "docs/releases/development-acceleration-v0-1/da-g5/DA_G5_GATE_PACKET.json",
    "docs/releases/development-acceleration-v0-1/da-g5/DA_G5_DELEGATED_DECISION.json",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_PROGRAMME_STATE_v0_1.json",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_IMPLEMENTATION_REGISTRY_v0_1.yaml",
]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def load(path: str) -> dict[str, object]:
    value = json.loads(read(path))
    assert isinstance(value, dict)
    return value


def main() -> int:
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing DA-WP5 files: {missing}")

    for schema_path in REQUIRED[1:3]:
        schema = load(schema_path)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False

    profile = load_profile(ROOT / REQUIRED[3])
    assert profile.profile_id == PROFILE_ID
    assert profile.programme_id == "OVC-DEV-ACCEL-v0.1"
    assert profile.active is True
    assert profile.allowed_source_roots == (
        "docs/releases/development-acceleration-v0-1",
        "registries/development",
    )
    assert profile.max_file_bytes == 1048576
    assert profile.max_bundle_bytes == 10485760

    passing_fixture = load_request(ROOT / REQUIRED[6])
    assert passing_fixture.source_commit == BASELINE
    try:
        load_request(ROOT / REQUIRED[7])
    except ValueError as exc:
        assert str(exc).startswith("DUPLICATE_PATH:")
    else:
        raise AssertionError("blocking fixture unexpectedly parsed")

    with tempfile.TemporaryDirectory() as temp_name:
        base = Path(temp_name)
        repo = base / "repo"
        external = base / "external"
        first_path = repo / "docs/releases/development-acceleration-v0-1/validator/packet.json"
        second_path = repo / "registries/development/validator.yaml"
        first_path.parent.mkdir(parents=True)
        second_path.parent.mkdir(parents=True)
        first_bytes = b'{"status":"PASS"}\n'
        second_bytes = b"status: READY\n"
        first_path.write_bytes(first_bytes)
        second_path.write_bytes(second_bytes)
        request = ExportRequest(
            export_id="DA-EXPORT-VALIDATOR",
            programme_id=profile.programme_id,
            profile_id=profile.profile_id,
            source_commit=BASELINE,
            files=(
                ExportFile("registries/development/validator.yaml", len(second_bytes), hashlib.sha256(second_bytes).hexdigest(), "REGISTRY"),
                ExportFile("docs/releases/development-acceleration-v0-1/validator/packet.json", len(first_bytes), hashlib.sha256(first_bytes).hexdigest(), "PACKET"),
            ),
        )
        plan = build_plan(repo, external, request, profile)
        result = execute_export(plan)
        assert result["status"] == "PASS"
        assert execute_export(plan)["status"] == "IDEMPOTENT_REUSE"
        assert (plan.destination / "manifest.json").read_bytes() == canonical_json_bytes(plan.manifest) + b"\n"
        assert (plan.destination / "files" / request.files[0].path).read_bytes() == second_bytes
        assert (plan.destination / "files" / request.files[1].path).read_bytes() == first_bytes
        assert not plan.staging.exists()

    implementation = load(REQUIRED[9])
    qa = load(REQUIRED[10])
    gate = load(REQUIRED[11])
    decision = load(REQUIRED[12])
    programme = load(REQUIRED[13])
    assert implementation["packet_id"] == "DA-WP5"
    assert implementation["baseline_main_commit"] == BASELINE
    assert implementation["authority_delta"] == "COPY_ONLY_COMPACT_EVIDENCE_EXPORT"
    assert implementation["status"] in {"IMPLEMENTED_PENDING_CI", "QA_REVIEW", "APPROVED", "COMPLETED"}
    assert qa["status"] in {"QA_REVIEW", "PASS"}
    assert qa["blocking_issues"] == []
    assert gate["gate_id"] == "DA-G5"
    assert gate["reserved_authority_delta"] == "NONE"
    assert gate["status"] in {"PENDING_CI", "APPROVED", "COMPLETED"}
    assert decision["decision"] in {"PENDING", "PASS"}
    if decision["decision"] == "PASS":
        assert decision["decision_authority"] == "DELEGATED_APPROVED_PLAN"
        assert decision["authority_delta"] == "COPY_ONLY_COMPACT_EVIDENCE_EXPORT"
    assert programme["current_packet"] in {"DA-WP5", "DA-G6"}
    authority = programme["authority"]
    assert authority["direct_main_write"] == "PROHIBITED"
    assert authority["merge_pull_request"] == "PROHIBITED_TO_BOT"
    assert authority["approve_pull_request"] == "PROHIBITED_TO_BOT"
    assert authority["force_push"] == "PROHIBITED"
    assert authority["history_rewrite"] == "PROHIBITED"
    assert authority["market"] == "NONE"
    assert authority["validation"] == "DENIED"
    assert authority["exposure"] == "NONE"
    assert authority["execution"] == "NONE"

    module = read(REQUIRED[4])
    runner = read(REQUIRED[5])
    for token in ("subprocess", "requests", "urllib", "httpx", "socket", "boto3", "rclone"):
        assert token not in module
        assert token not in runner
    assert not re.search(r"from ovc\.opt_|import ovc\.opt_|pattern_discovery|research_operations", module)
    assert not re.search(r"\.unlink\(|rmtree\(|os\.remove\(|git\s+(?:push|merge|reset)", module + "\n" + runner, re.I)
    assert "OVC_EXTERNAL_ARTIFACT_ROOT" in runner
    assert "EXTERNAL_ROOT_REQUIRED" in runner

    print("DA-WP5 compact evidence exporter validation PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
