from __future__ import annotations

import json
from pathlib import Path

from ovc.development.identity import canonical_sha256
from ovc.development.skills.repository_assurance_pilot import validate_pilot_policy


ROOT = Path(__file__).resolve().parents[2]
WP7D = ROOT / "docs/releases/development-skills-architecture-v0-3-vit/repository-assurance-continuity/wp7d"
POLICY = ROOT / "registries/development/skills/REPOSITORY_ASSURANCE_PILOT_POLICY_v0_1.json"
POINTER = ROOT / "registries/implementation/dsai3v_cipr_rac/CURRENT_STATE_POINTER.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_role_id(record: dict, field: str, role: str) -> None:
    logical = {key: value for key, value in record.items() if key != field}
    assert record[field] == canonical_sha256(logical, role=role)


def test_wp7d_rebaseline_stays_inside_exact_bounded_pilot_authority() -> None:
    authority = load(WP7D / "DSAI3V_RAC_WP7D_AUTHORITY_MANIFEST_v0_1.json")
    frontier = load(WP7D / "DSAI3V_RAC_WP7D_DEPENDENCY_FRONTIER_v0_1.json")
    implementation = load(WP7D / "DSAI3V_RAC_WP7D_IMPLEMENTATION_PACKET_v0_1.json")
    qa = load(WP7D / "DSAI3V_RAC_WP7D_QA_PACKET_v0_1.json")
    assert_role_id(authority, "authority_manifest_id", "OVC_AUTHORITY_MANIFEST")
    assert_role_id(frontier, "dependency_frontier_id", "OVC_DEPENDENCY_FRONTIER")
    assert_role_id(implementation, "implementation_packet_id", "OVC_IMPLEMENTATION_PACKET")
    assert_role_id(qa, "qa_packet_id", "OVC_QA_PACKET")
    assert authority["authority_class"] == "AUTO_EXECUTABLE"
    assert authority["authority_delta"] == "NONE_REBASELINE_WITHIN_APPROVED_PILOT"
    assert "general delta-assurance admission" in authority["denied"]
    assert implementation["pilot_class"] == "DSAI_VIT_RECEIPT_ONLY_V0_1"


def test_wp7d_control_namespace_does_not_change_receipt_eligibility_scope() -> None:
    policy = validate_pilot_policy(load(POLICY))
    control = "docs/releases/development-skills-architecture-v0-3-vit/repository-assurance-continuity/wp7d/"
    assert control in policy["control_prefixes"]
    assert control not in policy["receipt_prefixes"]
    assert policy["pilot_class"] == "DSAI_VIT_RECEIPT_ONLY_V0_1"
    assert policy["allowed_ops"] == ["ADD", "MODIFY"]
    pointer = load(POINTER)
    assert pointer["operator_stop_gate"] == "DSAI3V-RAC-G-DELTA-ASSURANCE-GENERAL"
    assert pointer["status"] in {
        "PILOT_REBASELINE_REFERENCE_PENDING",
        "PILOT_REBASELINE_REFERENCE_RENEWAL_PENDING",
        "PILOT_REBASELINED_ACTIVE",
    }
