from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PUBLICATION = ROOT / "docs" / "releases" / "opt-a-v2" / "publication"
EXPECTED = {
    "DISCOVERY": (
        "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
        "MANIFEST.OPT-A.GBPUSD.DISCOVERY.2021_2023.v2.r2",
        "0cbcafa9421449574b61bfeec24f634de99cbbbc6e7a53d09ace8f702182ab8c",
        293,
        155632392,
    ),
    "DEVELOPMENT": (
        "OPT-A.GBPUSD.DEVELOPMENT.2024.v2",
        "MANIFEST.OPT-A.GBPUSD.DEVELOPMENT.2024.v2.r2",
        "25e1be8a7edb0e96017c45bf35f4e788345f94b22a8ed9bb0874c86338ba64cc",
        101,
        52762768,
    ),
    "VALIDATION": (
        "OPT-A.GBPUSD.VALIDATION.2025.v2",
        "MANIFEST.OPT-A.GBPUSD.VALIDATION.2025.v2.r2",
        "9d855d4c7dda01182a574cba96761c2f545266580307b2e2bc764af6d933b877",
        101,
        52304577,
    ),
}


def test_wp6_report_self_hash_and_remote_identities() -> None:
    report = json.loads((PUBLICATION / "WP6_PUBLICATION_REPORT.json").read_text(encoding="utf-8"))
    claimed = report.pop("report_sha256")
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":")).encode("utf-8")
    assert hashlib.sha256(canonical).hexdigest() == claimed
    assert claimed == "b6f482d5f94a266593ad9a0012925a9a9389764206605f731e65cbb66e3f6d4a"
    assert report["result"] == "PASS"
    assert report["workflow_run_id"] == "30181995980"
    for role, (release_id, manifest_id, manifest_sha256, count, size) in EXPECTED.items():
        record = report["roles"][role]
        assert record["release_id"] == release_id
        assert record["manifest_id"] == manifest_id
        assert record["manifest_sha256"] == manifest_sha256
        assert record["file_count"] == count
        assert record["total_size_bytes"] == size
        assert record["publication"] == "PUBLISHED_MANIFEST_LAST"
        assert record["remote_verification"] == "PASS_FULL_BYTE_READBACK"


def test_a2_g4_review_preserves_non_activation_boundaries() -> None:
    review = json.loads((PUBLICATION / "A2_G4_OPERATOR_REVIEW.json").read_text(encoding="utf-8"))
    assert review["gate_id"] == "A2-G4"
    assert review["decision"] == "PASS"
    assert all(value == "PASS" for value in review["checks"].values())
    assert review["authority_delta"] == {
        "r2_publication": "COMPLETE_REMOTE_VERIFIED",
        "release_availability": "REMOTE_VERIFIED",
        "release_authority": "SHADOW_NOT_SELECTED",
        "selector_activation": "DENIED_PENDING_A2_G5",
        "validation_consumption": "LOCKED_UNCONSUMED",
        "active_opt_a_to_opt_b_handoff": "NONE",
        "market_authority": "NONE",
        "probability_exposure_trading_execution": "DENIED",
    }
    assert review["quarantine"]["record_count"] == 21410
    assert review["quarantine"]["disposition"] == "RETAIN_TRACE_AND_EXCLUDE_FROM_ACCEPTED_OBSERVATIONS"
    assert review["next_gate"] == "A2-G5_SELECTOR_SET_ACTIVATION"


def test_release_and_selector_registries_bind_exact_remote_manifests() -> None:
    releases = (ROOT / "registries" / "releases" / "OPT_A_RELEASE_REGISTRY.yaml").read_text(encoding="utf-8")
    selectors = (ROOT / "registries" / "releases" / "OPT_A_ACTIVE_SELECTORS.yaml").read_text(encoding="utf-8")
    authority = (ROOT / "registries" / "authority" / "ACTIVE_AUTHORITY.yaml").read_text(encoding="utf-8")
    for _, (_, manifest_id, manifest_sha256, _, _) in EXPECTED.items():
        assert manifest_id in releases
        assert manifest_sha256 in releases
        assert manifest_id in selectors
        assert manifest_sha256 in selectors
    assert releases.count("lifecycle_state: REMOTE_VERIFIED") == 3
    assert releases.count("authority_state: SHADOW") == 3
    assert releases.count("publication_status: PUBLISHED") == 3
    assert selectors.count("selector_state: NONE") == 3
    assert "state: NONE" in selectors
    assert "consumption_state: LOCKED_UNCONSUMED" in selectors
    assert "state: V2_REMOTE_PUBLICATION_REVIEW_PASS_NO_MARKET_AUTHORITY" in authority
    assert "selector_activation_authority: DENIED_PENDING_A2_G5" in authority
    assert "active_handoff: NONE" in authority
    assert "validation_consumption: LOCKED_UNCONSUMED" in authority


def test_publication_governance_tree_contains_no_market_payloads() -> None:
    prohibited_suffixes = {".csv", ".parquet", ".feather", ".zip", ".bin"}
    assert not any(path.suffix.lower() in prohibited_suffixes for path in PUBLICATION.rglob("*"))
