from __future__ import annotations

import json
from pathlib import Path

import pytest

from ovc.opt_a.release_freeze import (
    ROLE_RELEASES,
    ReleaseFreezeError,
    canonical_json_sha256,
    freeze_role_release,
    sha256_file,
)


def _workspace(root: Path, role: str) -> Path:
    workspace = root / role.lower()
    observation = workspace / "observations" / "15M" / "BID" / "sample.csv"
    observation.parent.mkdir(parents=True)
    observation.write_text("timestamp,open,high,low,close,volume\n0,1,1,1,1,1\n", encoding="utf-8")
    digest, size = sha256_file(observation)
    quarantine = {
        "bucket_id": "bucket-1",
        "bucket_start": 0,
        "clock_minutes": 15,
        "clock": "15M",
        "price_side": "BID",
        "source_object_id": "SRC.TEST",
        "year_month": "2021-01",
        "expected_count": 15,
        "observed_count": 14,
        "missing_count": 1,
        "unexpected_count": 0,
        "missing_timestamps": [420000],
        "unexpected_timestamps": [],
        "reason": "INCOMPLETE_OR_NONCONTIGUOUS_M1_BUCKET",
        "disposition": "RETAIN_TRACE_AND_EXCLUDE_FROM_ACCEPTED_OBSERVATIONS",
    }
    manifest = {
        "schema": "ovc-opt-a-role-workspace-manifest/v1",
        "programme_id": "OVC-OPT-A-V2-IMPLEMENTATION-PLAN-0.2",
        "work_packet_id": "WP5",
        "gate_id": "A2-G2",
        "role": role,
        "target_release_id": ROLE_RELEASES[role],
        "authority_state": "MUTABLE_WORKSPACE",
        "qa_state": "WARN",
        "validation_consumption": "LOCKED_UNCONSUMED" if role == "VALIDATION" else "NOT_APPLICABLE",
        "source_object_count": 1,
        "observation_object_count": 1,
        "quarantined_bucket_count": 1,
        "source_objects": [],
        "observations": [{
            "clock": "15M",
            "price_side": "BID",
            "year_month": "2021-01",
            "path": "observations/15M/BID/sample.csv",
            "row_count": 1,
            "size_bytes": size,
            "sha256": digest,
            "first_timestamp_ms": 0,
            "last_timestamp_ms": 0,
        }],
        "quarantine": [quarantine],
        "coverage": {},
        "authority": {
            "release_freeze": "DENIED",
            "r2_publication": "DENIED",
            "selector_activation": "DENIED",
            "opt_b_handoff": "DENIED",
            "market": "NONE",
        },
    }
    manifest["manifest_sha256"] = canonical_json_sha256(manifest)
    (workspace / "workspace-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return workspace


def test_freeze_requires_exact_reviewed_manifest(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    workspace = _workspace(tmp_path, "DISCOVERY")
    manifest = json.loads((workspace / "workspace-manifest.json").read_text())
    monkeypatch.setitem(
        __import__("ovc.opt_a.release_freeze", fromlist=["REVIEWED_MANIFESTS"]).REVIEWED_MANIFESTS,
        "DISCOVERY",
        manifest["manifest_sha256"],
    )
    receipt = freeze_role_release(
        workspace=workspace,
        output_root=tmp_path / "releases",
        role="DISCOVERY",
        source_commit="a" * 40,
    )
    release = tmp_path / "releases" / ROLE_RELEASES["DISCOVERY"]
    assert receipt["result"] == "PASS"
    assert (release / "canonical" / "15M" / "BID" / "sample.csv").is_file()
    assert (release / "QA" / "quarantine-ledger.jsonl").is_file()
    descriptor = json.loads((release / "release-descriptor.json").read_text())
    assert descriptor["lifecycle_state"] == "RELEASE_FROZEN"
    assert descriptor["selector_state"] == "NONE"
    assert descriptor["authority"]["r2_publication"] == "DENIED_PENDING_SEPARATE_GATE"


def test_freeze_rejects_quarantine_repair(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path, "DISCOVERY")
    manifest_path = workspace / "workspace-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["quarantine"][0]["disposition"] = "FILL"
    manifest["manifest_sha256"] = canonical_json_sha256({k: v for k, v in manifest.items() if k != "manifest_sha256"})
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ReleaseFreezeError, match="not the A2-G2 reviewed identity"):
        freeze_role_release(
            workspace=workspace,
            output_root=tmp_path / "releases",
            role="DISCOVERY",
            source_commit="a" * 40,
        )


def test_freeze_refuses_overwrite(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    workspace = _workspace(tmp_path, "DEVELOPMENT")
    manifest = json.loads((workspace / "workspace-manifest.json").read_text())
    module = __import__("ovc.opt_a.release_freeze", fromlist=["REVIEWED_MANIFESTS"])
    monkeypatch.setitem(module.REVIEWED_MANIFESTS, "DEVELOPMENT", manifest["manifest_sha256"])
    output = tmp_path / "releases"
    freeze_role_release(workspace=workspace, output_root=output, role="DEVELOPMENT", source_commit="b" * 40)
    with pytest.raises(ReleaseFreezeError, match="already exists"):
        freeze_role_release(workspace=workspace, output_root=output, role="DEVELOPMENT", source_commit="b" * 40)
