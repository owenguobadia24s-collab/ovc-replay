from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RELEASE = ROOT / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-iad"


def load(name: str) -> dict:
    return json.loads((RELEASE / name).read_text(encoding="utf-8"))


def test_owner_census_requires_gowner_instead_of_manufacturing_positive_anchors() -> None:
    census = load("C2P2_IAD_WP2_OWNER_EVIDENCE_CENSUS_v0_1.json")
    assert census["fresh_real_source_execution"] is False
    assert census["candidate_outputs_used_to_define_anchors"] is False
    assert census["positive_same_denominator_possible_without_owner_change"] is False
    assert census["positive_different_denominator_for_persistent_referent_possible_without_owner_change"] is False
    assert census["owner_contract_extension_required"] is True
    assert census["required_gate"] == "C2P2-IAD-GOWNER"
    assert census["wp3_authorised_before_gate"] is False
    assert census["wp4_authorised_before_gate"] is False


def test_current_rs0_projection_is_recorded_as_missing_owner_anchor_provenance() -> None:
    census = load("C2P2_IAD_WP2_OWNER_EVIDENCE_CENSUS_v0_1.json")
    row = next(item for item in census["implementation_observations"] if item["path"].endswith("rs0_source_materialisation.py"))
    assert "omit" in row["finding"].lower()
    assert "lineage_id" in row["finding"]
    assert "anchor observation identity" in row["finding"]


def test_gowner_delta_is_additive_shadow_only_and_does_not_grant_reserved_science() -> None:
    gate = load("C2P2_IAD_GOWNER_GATE_PACKET_v0_1.json")
    assert gate["gate_id"] == "C2P2-IAD-GOWNER"
    assert gate["gate_classification"] == "OPERATOR_REQUIRED_MATERIAL_OWNER_IDENTITY_SEMANTICS"
    assert gate["recommended_decision"] == "PASS"
    ext = gate["proposed_owner_extension"]
    assert ext["mode"] == "ADDITIVE_SHADOW_ONLY_NO_MUTATION_OF_EXISTING_C2_IDENTITIES"
    assert "anchor_observation_id" in ext["high_low_referent_identity"]
    assert ext["candidate_firewall"] == "A_B_C_OUTPUTS_FORBIDDEN_FROM_REFERENT_IDENTITY_CONSTRUCTION"
    assert gate["sidecar_requirement"]["current_rs0_artifact_mutation"] == "FORBIDDEN"
    denials = gate["non_transitive_denials"]
    assert denials["real_source_execution"] == "NONE_PENDING_GREAL"
    assert denials["objectpack_selection"] == "NONE"
    assert denials["c2p_activation"] == "NONE"
    assert denials["ec1_candidate_defining_use"] == "FORBIDDEN"
