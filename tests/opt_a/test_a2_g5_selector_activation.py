from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SELECTORS = ROOT / "registries" / "releases" / "OPT_A_ACTIVE_SELECTORS.yaml"
RELEASES = ROOT / "registries" / "releases" / "OPT_A_RELEASE_REGISTRY.yaml"
AUTHORITY = ROOT / "registries" / "authority" / "ACTIVE_AUTHORITY.yaml"
RECORD = ROOT / "docs" / "releases" / "opt-a-v2" / "activation" / "A2_G5_SELECTOR_ACTIVATION.json"

EXPECTED = {
    "discovery": (
        "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
        "MANIFEST.OPT-A.GBPUSD.DISCOVERY.2021_2023.v2.r2",
        "0cbcafa9421449574b61bfeec24f634de99cbbbc6e7a53d09ace8f702182ab8c",
        "ACTIVE_DISCOVERY",
    ),
    "development": (
        "OPT-A.GBPUSD.DEVELOPMENT.2024.v2",
        "MANIFEST.OPT-A.GBPUSD.DEVELOPMENT.2024.v2.r2",
        "25e1be8a7edb0e96017c45bf35f4e788345f94b22a8ed9bb0874c86338ba64cc",
        "ACTIVE_DEVELOPMENT",
    ),
    "validation": (
        "OPT-A.GBPUSD.VALIDATION.2025.v2",
        "MANIFEST.OPT-A.GBPUSD.VALIDATION.2025.v2.r2",
        "9d855d4c7dda01182a574cba96761c2f545266580307b2e2bc764af6d933b877",
        "ACTIVE_VALIDATION",
    ),
}


def test_activation_record_exactly_binds_all_roles() -> None:
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    assert record["decision"] == "PASS_ACTIVATE"
    assert record["atomic_update"] is True
    for role, (release_id, manifest_id, digest, authority_state) in EXPECTED.items():
        value = record["roles"][role]
        assert value["release_id"] == release_id
        assert value["manifest_id"] == manifest_id
        assert value["manifest_sha256"] == digest
        assert value["authority_state"] == authority_state
        assert value["selector_state"] == "ACTIVE"


def test_validation_lock_and_rollback_are_preserved() -> None:
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    assert record["roles"]["validation"]["consumption_state"] == "LOCKED_UNCONSUMED"
    assert record["rollback"]["target_state"] == "NONE"
    assert record["rollback"]["historical_v1_reactivation"] == "PROHIBITED"
    selectors = SELECTORS.read_text(encoding="utf-8")
    assert "all_role_selectors: NONE" in selectors
    assert "remote_object_mutation: false" in selectors


def test_selector_set_is_active_but_downstream_authority_is_none() -> None:
    selectors = SELECTORS.read_text(encoding="utf-8")
    authority = AUTHORITY.read_text(encoding="utf-8")
    releases = RELEASES.read_text(encoding="utf-8")
    assert "state: ACTIVE" in selectors
    assert selectors.count("selector_state: ACTIVE") == 3
    assert "  opt_a: ACTIVE" in authority
    for selector in ("opt_b_c1", "opt_b_c2", "c2e", "c2_5", "c3", "opt_c", "opt_d"):
        assert f"  {selector}: NONE" in authority
    assert "active_handoff: NONE" in authority
    assert "validation_consumption: LOCKED_UNCONSUMED" in authority
    assert releases.count("active_selector: true") == 3
    assert "authority_state: ACTIVE_DISCOVERY" in releases
    assert "authority_state: ACTIVE_DEVELOPMENT" in releases
    assert "authority_state: ACTIVE_VALIDATION" in releases
