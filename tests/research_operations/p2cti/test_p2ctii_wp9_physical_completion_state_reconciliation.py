from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
STATE_PATH = ROOT / "records/research_operations/p2cti/P2CTII_PROGRAMME_STATE_v0_1.json"
GATE_PATH = (
    ROOT
    / "docs/programmes/p2cti-v0-1/wp9/"
    "P2CTII_G_OBSERVABILITY_ACTIVATE_GATE_PACKET_v0_1.json"
)

PHYSICAL_COMPLETION = {
    "status": "COMPLETED",
    "merge_commit": "6d2d73d027a955a3ded29ca5ba1ae80ce2976102",
    "result_tree": "31651456d4a92b906bc716ef7621c748b071695d",
    "physical_materialisation_receipt_id": (
        "247c2b13feac5339a26f03bb9343538da5d7c657c70c1774f9c9a51c2c42b189"
    ),
    "packet_completion_receipt_id": (
        "c4d22682cbae1e725fba79d1365a418f6f7312251a558b7027d2327a724c554f"
    ),
    "development_latency_receipt_id": (
        "f6aeba83ee5b43c517df34a1e4374c28c5e982eedba1b9695043c873b647db53"
    ),
    "completion_attachment_id": (
        "5851009662a782ce165cc2f21f15a525497e4a82e9059c4c465402b50f5a3da6"
    ),
    "completion_proof_id": (
        "43517263c8d3a46de7f10037b402a6fd0e08023957eb3a395a736b5dd7b49e99"
    ),
}

STATE_NON_GRANTS = [
    "RESEARCH_CONSOLE_SOURCE_PRESENTATION_AUTHORITY",
    "P2CTI_CONTINUOUS_INTAKE_WRITES",
    "THEORY_SEMANTIC_FREEZE",
    "P2_6_CANDIDATE_FORMATION",
    "RESEARCH_CANDIDATE_GENERATION_FREEZE",
    "OPT_C_ADMISSION",
    "CAPABILITY_ACTIVATION",
    "VALIDATION",
    "PUBLICATION",
    "PROBABILITY",
    "RISK",
    "EXPOSURE",
    "TRADING",
    "EXECUTION",
    "AGENT_WRITE",
]

GATE_NON_GRANTS = [
    "RESEARCH_CONSOLE_SOURCE_PRESENTATION_AUTHORITY",
    "P2CTI_CONTINUOUS_INTAKE_WRITES",
    "THEORY_SEMANTIC_FREEZE",
    "P2_6_CANDIDATE_FORMATION",
    "RESEARCH_CANDIDATE_GENERATION_FREEZE",
    "OPT_C_ADMISSION",
    "VALIDATION",
    "PUBLICATION",
    "PROBABILITY",
    "RISK",
    "EXPOSURE",
    "TRADING",
    "EXECUTION",
    "AGENT_WRITE",
]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_programme_state_records_exact_wp9_physical_completion() -> None:
    state = _load(STATE_PATH)
    wp9 = next(row for row in state["completed_packets"] if row["packet_id"] == "P2CTII-WP9")

    assert {key: wp9[key] for key in PHYSICAL_COMPLETION} == PHYSICAL_COMPLETION
    assert wp9["decision"] == "PASS_SHADOW_STABLE"
    assert wp9["authority_delta"] == "NONE"
    assert "EFFECTIVE_ON_VIT_POST_MERGE_PACKET_COMPLETION_RECEIPT" not in STATE_PATH.read_text(
        encoding="utf-8"
    )


def test_programme_records_observability_pass_without_write_or_consumer_grants() -> None:
    state = _load(STATE_PATH)
    gate = next(
        row for row in state["completed_packets"]
        if row["packet_id"] == "P2CTII-G-OBSERVABILITY-ACTIVATE"
    )

    assert gate["status"] == "COMPLETED"
    assert gate["decision"] == "PASS"
    assert gate["authority_delta"] == "OPERATIONAL_READ_ONLY_P2CTI_CURRENT_PROJECTION"
    assert state["packet_id"] == "P2CTII-WP10"
    assert state["status"] == "READY"
    assert state["authority_delta"] == "NONE"
    assert state["operational_current_pointer_publication"] == "ALLOWED_P2CTI_OPERATIONAL_READ_ONLY_ONLY"
    assert state["operational_reliance"] is True
    assert state["p2ctii_observability_gate_status"] == "PASS_ACTIVE"
    assert state["authority_required"] == "AUTO_EXECUTABLE"
    assert state["explicit_non_grants"] == STATE_NON_GRANTS


def test_consolidated_operator_packet_remains_exact_approved_subject() -> None:
    gate = _load(GATE_PATH)
    expected_gate_completion = {**PHYSICAL_COMPLETION, "authority_effect": "NONE"}
    expected_hashes = {
        key: value
        for key, value in PHYSICAL_COMPLETION.items()
        if key not in {"status", "merge_commit", "result_tree"}
    }

    assert gate["gate_id"] == "P2CTII-G-OBSERVABILITY-ACTIVATE"
    assert gate["wp9_physical_completion"] == expected_gate_completion
    assert gate["external_artifact_hashes"] == expected_hashes
    assert gate["current_authority"] == "READ_ONLY_SHADOW_ONLY_NO_OPERATIONAL_RELIANCE"
    assert gate["proposed_authority_delta"] == "ACTIVATE_OPERATIONAL_READ_ONLY_P2CTI_CURRENT_PROJECTION_ONLY"
    assert gate["recommended_decision"] == "PASS"
    assert gate["explicit_non_grants"] == GATE_NON_GRANTS
    assert gate["unresolved_issues"] == []
