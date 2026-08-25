from __future__ import annotations

import json
from pathlib import Path

from ovc.development.identity import canonical_sha256
from ovc.development.skills.repository_assurance_pilot import (
    assurance_surface_id,
    classify_candidate,
    validate_pilot_baseline,
    validate_pilot_policy,
)
from ovc.development.skills.vit_routing import build_vit_payload_lineage_record


ROOT = Path(__file__).resolve().parents[2]
WP7 = ROOT / "docs/releases/development-skills-architecture-v0-3-vit/repository-assurance-continuity/wp7"
WP7B = ROOT / "docs/releases/development-skills-architecture-v0-3-vit/repository-assurance-continuity/wp7b"
POLICY = ROOT / "registries/development/skills/REPOSITORY_ASSURANCE_PILOT_POLICY_v0_1.json"
STATE = ROOT / "registries/implementation/dsai3v_cipr_rac/OVC_DSAI3V_CIPR_RAC_STATE_v0_5_PILOT_BASELINE_ACTIVE.json"
POINTER = ROOT / "registries/implementation/dsai3v_cipr_rac/CURRENT_STATE_POINTER.json"
BASELINE = WP7 / "DSAI3V_RAC_PILOT_BASELINE_CERTIFICATE_v0_1.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_role_id(record: dict, field: str, role: str) -> None:
    logical = {key: value for key, value in record.items() if key != field}
    assert record[field] == canonical_sha256(logical, role=role)


def receipt_lineage(path: str) -> dict:
    pip = {
        "schema_version": "packet-integration-payload/v0.1",
        "programme_id": "RAC-PILOT-QUALIFICATION",
        "packet_id": "RAC-PILOT-RECEIPT-CASE",
        "logical_changes": [
            {"op": "ADD", "path": path, "mode": "100644", "blob_sha": "1" * 40}
        ],
        "authority_manifest_id": "2" * 64,
        "dependency_frontier_id": "3" * 64,
        "completion_transition": {"status": "COMPLETED"},
    }
    return build_vit_payload_lineage_record(
        programme_id=pip["programme_id"],
        packet_id=pip["packet_id"],
        pip_identity_payload=pip,
    )


def test_wp7b_is_auto_executable_only_inside_the_operator_approved_pilot() -> None:
    authority = load(WP7B / "DSAI3V_RAC_WP7B_AUTHORITY_MANIFEST_v0_1.json")
    frontier = load(WP7B / "DSAI3V_RAC_WP7B_DEPENDENCY_FRONTIER_v0_1.json")
    implementation = load(WP7B / "DSAI3V_RAC_WP7B_IMPLEMENTATION_PACKET_v0_1.json")
    assert_role_id(authority, "authority_manifest_id", "OVC_AUTHORITY_MANIFEST")
    assert_role_id(frontier, "dependency_frontier_id", "OVC_DEPENDENCY_FRONTIER")
    assert_role_id(implementation, "implementation_packet_id", "OVC_IMPLEMENTATION_PACKET")
    assert authority["authority_class"] == "AUTO_EXECUTABLE"
    assert authority["authority_delta"] == "NONE_BEYOND_OPERATOR_APPROVED_BOUNDED_PILOT"
    assert implementation["pilot_class"] == "DSAI_VIT_RECEIPT_ONLY_V0_1"
    assert "general delta-assurance admission" in authority["denied"]


def test_active_policy_is_exact_bounded_and_has_fail_closed_fallback() -> None:
    policy = validate_pilot_policy(load(POLICY))
    state = load(STATE)
    pointer = load(POINTER)
    assert policy["status"] == "ACTIVE_BOUNDED_PILOT"
    assert policy["pilot_class"] == "DSAI_VIT_RECEIPT_ONLY_V0_1"
    assert state["general_delta_assurance_active"] is False
    assert state["required_check_substitution_active"] is False
    assert state["runner_cutover_active"] is False
    assert pointer["operator_stop_gate"] == "DSAI3V-RAC-G-DELTA-ASSURANCE-GENERAL"
    result = classify_candidate(
        root=ROOT,
        candidate_head_sha="4" * 40,
        lineage_record=receipt_lineage(
            "docs/releases/development-skills-v0-3/example/EXAMPLE_RECEIPT_v0_1.json"
        ),
        policy=policy,
        baseline=None,
    )
    assert result == {
        "eligible": False,
        "reason": "BASELINE_MISSING",
        "pilot_class": "DSAI_VIT_RECEIPT_ONLY_V0_1",
    }


def test_exact_baseline_certificate_when_materialised() -> None:
    policy = validate_pilot_policy(load(POLICY))
    if not BASELINE.is_file():
        # The first immutable activation candidate deliberately obtains canonical
        # reference assurance before the control-only certificate successor exists.
        assert policy["status"] == "ACTIVE_BOUNDED_PILOT"
        return
    baseline = validate_pilot_baseline(load(BASELINE), policy)
    assert baseline["pilot_class"] == "DSAI_VIT_RECEIPT_ONLY_V0_1"
    assert baseline["reference_status"] == "PASS"
    assert baseline["reference_source"] == "EXACT_FULL_REFERENCE_BEFORE_ACTIVATION"
    assert baseline["assurance_surface_id"] == assurance_surface_id(
        ROOT, baseline["source_commit_sha"], policy
    )
    assert baseline["source_tree_sha"] == (
        __import__("subprocess").check_output(
            ["git", "-C", str(ROOT), "rev-parse", f"{baseline['source_commit_sha']}^{{tree}}"],
            text=True,
        ).strip()
    )
