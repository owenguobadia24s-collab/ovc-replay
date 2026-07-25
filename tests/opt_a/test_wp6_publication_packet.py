from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "docs" / "releases" / "opt-a-v2" / "publication"
EXPECTED = {
    "discovery": ("OPT-A.GBPUSD.DISCOVERY.2021_2023.v2", 293, 155632392),
    "development": ("OPT-A.GBPUSD.DEVELOPMENT.2024.v2", 101, 52762768),
    "validation": ("OPT-A.GBPUSD.VALIDATION.2025.v2", 101, 52304577),
}


def test_manifest_spec_and_approvals_are_exactly_bound() -> None:
    spec = json.loads((PACKET / "WP6_MANIFEST_SPEC.json").read_text(encoding="utf-8"))
    assert spec["source_commit"] == "8c4c6c70da6f3f8b400d06df990500702813ff39"
    assert spec["bucket"] == "ovc-evidence"
    assert spec["prefix"] == "canonical"
    for role, (release_id, count, size) in EXPECTED.items():
        record = spec["roles"][role]
        approval = json.loads((PACKET / "approvals" / f"{role}.json").read_text(encoding="utf-8"))
        assert record["release_id"] == release_id
        assert record["expected_file_count"] == count
        assert record["expected_total_size_bytes"] == size
        assert approval["decision"] == "APPROVE"
        assert approval["release_id"] == release_id
        assert approval["manifest_id"] == record["manifest_id"]
        assert approval["manifest_sha256"] == record["expected_manifest_sha256"]
        assert approval["source_commit"] == spec["source_commit"]


def test_validation_and_selector_boundaries_remain_denied() -> None:
    spec = json.loads((PACKET / "WP6_MANIFEST_SPEC.json").read_text(encoding="utf-8"))
    assert spec["roles"]["validation"]["consumption_state"] == "LOCKED_UNCONSUMED"
    registry = (ROOT / "registries" / "implementation" / "OPT_A_WP6_R2_PUBLICATION.yaml").read_text(encoding="utf-8")
    assert "selector_activation: DENIED" in registry
    assert "validation_consumption: LOCKED_UNCONSUMED" in registry
    assert "opt_b_handoff: DENIED" in registry
    assert "market: NONE" in registry
