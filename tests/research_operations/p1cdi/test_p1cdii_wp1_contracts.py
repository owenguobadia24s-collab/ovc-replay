from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def load_json(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


class P1CDIIWP1ContractTests(unittest.TestCase):
    def test_exact_wp1_contract_set_exists(self) -> None:
        contract_dir = ROOT / "contracts/research_operations/p1cdi"
        expected = {
            "P1CDI_AUTHORITY_AND_NON_TRANSITIVITY_CONTRACT_v0_1.md",
            "P1CDI_SOURCE_RESOLUTION_AND_CURRENTNESS_CONTRACT_v0_1.md",
            "P1CDI_SEMANTIC_PROJECTION_AND_IDENTITY_CONTRACT_v0_1.md",
            "P1CDI_CORRESPONDENCE_EXECUTABILITY_CONTRACT_v0_1.md",
            "P1CDI_RCCR_REFERRAL_CONTRACT_v0_1.md",
            "P1CDI_DMRP_CANDIDATE_FIREWALL_CONTRACT_v0_1.md",
            "P1CDI_VISIBILITY_AND_PROTECTED_SOURCE_CONTRACT_v0_1.md",
            "P1CDI_QUERY_AND_NON_ACTUATION_CONTRACT_v0_1.md",
            "P1CDI_LIVE_SHADOW_STABILIZATION_CONTRACT_v0_1.md",
        }
        self.assertEqual(expected, {path.name for path in contract_dir.glob("*.md")})

    def test_contracts_preserve_reserved_boundaries(self) -> None:
        contract_dir = ROOT / "contracts/research_operations/p1cdi"
        text_by_name = {
            path.name: path.read_text(encoding="utf-8").lower()
            for path in contract_dir.glob("*.md")
        }
        self.assertIn("non-transitivity", text_by_name["P1CDI_AUTHORITY_AND_NON_TRANSITIVITY_CONTRACT_v0_1.md"])
        self.assertIn("two-point", text_by_name["P1CDI_SOURCE_RESOLUTION_AND_CURRENTNESS_CONTRACT_v0_1.md"])
        self.assertIn("independence_unknown", text_by_name["P1CDI_SOURCE_RESOLUTION_AND_CURRENTNESS_CONTRACT_v0_1.md"])
        self.assertIn("g2-alg", text_by_name["P1CDI_SOURCE_RESOLUTION_AND_CURRENTNESS_CONTRACT_v0_1.md"])
        self.assertIn("exact", text_by_name["P1CDI_SEMANTIC_PROJECTION_AND_IDENTITY_CONTRACT_v0_1.md"])
        self.assertIn("review", text_by_name["P1CDI_CORRESPONDENCE_EXECUTABILITY_CONTRACT_v0_1.md"])
        self.assertIn("one-way", text_by_name["P1CDI_RCCR_REFERRAL_CONTRACT_v0_1.md"])
        self.assertIn("candidate_write", text_by_name["P1CDI_DMRP_CANDIDATE_FIREWALL_CONTRACT_v0_1.md"])
        self.assertIn("before indexing", text_by_name["P1CDI_VISIBILITY_AND_PROTECTED_SOURCE_CONTRACT_v0_1.md"])
        self.assertIn("negative-reachability", text_by_name["P1CDI_VISIBILITY_AND_PROTECTED_SOURCE_CONTRACT_v0_1.md"])
        self.assertIn("non-actuation", text_by_name["P1CDI_QUERY_AND_NON_ACTUATION_CONTRACT_v0_1.md"])
        self.assertIn("operational_reliance", text_by_name["P1CDI_LIVE_SHADOW_STABILIZATION_CONTRACT_v0_1.md"])
        self.assertIn("automatic_activation", text_by_name["P1CDI_LIVE_SHADOW_STABILIZATION_CONTRACT_v0_1.md"])

    def test_closed_registries_encode_design_vocabularies(self) -> None:
        lifecycle = load_json("registries/research_operations/p1cdi/lifecycle_registry.json")
        self.assertEqual(lifecycle["status"], "CLOSED")
        self.assertEqual(
            lifecycle["inventory_activity"],
            ["ACTIVE_RESEARCH", "DORMANT", "REOPENED", "HISTORICAL", "QUARANTINED"],
        )
        self.assertEqual(lifecycle["scientific_disposition_ownership"], "SOURCE_OWNER_REFERENCE_ONLY")

        relation = load_json("registries/research_operations/p1cdi/relation_registry.json")
        self.assertEqual(relation["status"], "CLOSED")
        self.assertEqual(relation["automatic_admission"], ["EXACT_EQUIVALENT", "SOURCE_EXPLICIT_DETERMINISTIC_RELATION"])
        self.assertIn("MULTIPLE_PLAUSIBLE_CORES", relation["core"])
        self.assertIn("REPRESENTATION_ANALOGUE", relation["review_required"])

        demand = load_json("registries/research_operations/p1cdi/demand_registry.json")
        self.assertEqual(demand["status"], "CLOSED")
        self.assertEqual(demand["route_authority"], "ADVISORY_ONLY")
        self.assertEqual(demand["actuation"], "DENIED")

        visibility = load_json("registries/research_operations/p1cdi/visibility_registry.json")
        self.assertEqual(visibility["classification_timing"], "BEFORE_INDEXING")
        self.assertEqual(visibility["incomplete_classification"], "PROTECTED")
        self.assertEqual(visibility["validation"], "NEGATIVE_REACHABILITY_HARD_DENY")

        reasons = load_json("registries/research_operations/p1cdi/reason_code_registry.json")
        self.assertEqual(reasons["unknown_code_policy"], "REJECT")
        for code in ("INDEPENDENCE_UNKNOWN", "FALSE_CURRENTNESS", "VALIDATION_LEAK", "UNAUTHORISED_WRITE"):
            self.assertIn(code, reasons["codes"])

        owners = load_json("registries/research_operations/p1cdi/source_owner_registry.json")
        self.assertEqual(owners["status"], "CLOSED")
        self.assertEqual(
            owners["currentness_required_predicates"],
            [
                "SOURCE_SCIENCE",
                "P1_SCIENTIFIC_DISPOSITION",
                "CANDIDATE_PROPOSAL_FREEZE_C_ADMISSION",
                "GAP_AND_CAPABILITY_NEED",
                "EXPOSURE_AND_INDEPENDENCE",
                "VALIDATION_ACCESS",
                "P1CDI_IDENTITY_ACTIVITY_CURRENTNESS_LINEAGE",
            ],
        )
        self.assertIn("REPOSITORY_FALLBACK", owners["forbidden_resolution"])
        self.assertIn("SUMMARY_RECONSTRUCTION", owners["forbidden_resolution"])

    def test_semantic_projection_profile_is_identity_bearing_and_lossless(self) -> None:
        profile = load_json(
            "registries/research_operations/p1cdi/semantic_projection_profiles/"
            "P1CDI_SEMANTIC_PROJECTION_PROFILE_v1.json"
        )
        self.assertEqual(profile["profile_id"], "P1CDI-SEMANTIC-PROJECTION-v1")
        self.assertEqual(profile["automatic_match"], "EXACT_CANONICAL_BYTES_AND_COMPATIBLE_PROFILE_ONLY")
        self.assertEqual(profile["non_exact_match"], "REVIEW_REQUIRED")
        self.assertFalse(profile["canonicalization"]["case_folding"])
        self.assertFalse(profile["canonicalization"]["unit_conversion"])
        self.assertEqual(profile["canonicalization"]["unknown_field_policy"], "REJECT")
        identity = set(profile["identity_bearing_paths"])
        self.assertTrue({"unit_type", "structural_predicates", "applicability_scope", "first_valid_semantics"} <= identity)
        evidence_only = set(profile["evidence_only_paths"])
        self.assertTrue({"recurrence_count", "qa_state", "worker", "path", "pull_request"} <= evidence_only)
        self.assertTrue(identity.isdisjoint(evidence_only))

    def test_packet_and_programme_state_bind_exact_authority_without_expansion(self) -> None:
        packet = load_json("docs/programmes/p1cdi-v0-1/wp1/P1CDII_WP1_IMPLEMENTATION_PACKET_v0_1.json")
        qa = load_json("docs/programmes/p1cdi-v0-1/wp1/P1CDII_WP1_QA_PACKET_v0_1.json")
        decision = load_json("docs/programmes/p1cdi-v0-1/wp1/P1CDII_WP1_DELEGATED_DECISION_v0_1.json")
        state = load_json("records/research_operations/p1cdi/P1CDII_PROGRAMME_STATE_v0_1.json")
        self.assertEqual(packet["plan_sha256"], "eeb3cfef77c8a61ce2fb825f8f0f649ac35281f30d43ba24651fc329a11a0b9a")
        self.assertEqual(packet["design_sha256"], "5eaee768bc18ce9fa40c79fe1c3a91c57cbadf21ce15ba39438a0b34a55bbea3")
        self.assertEqual(packet["authority_delta"], "NONE")
        self.assertEqual(packet["status"], "APPROVED")
        self.assertEqual(packet["next_packet"], "P1CDII-WP2")
        self.assertEqual(qa["qa_result"], "PASS")
        self.assertTrue(all(result == "PASS" or result.startswith("PASS_") for result in qa["checks"].values()))
        self.assertEqual(decision["decision"], "PASS")
        self.assertEqual(decision["authority"], "DELEGATED_BY_OPERATOR_APPROVED_P1CDII_G0")
        self.assertEqual(decision["authority_delta"], "NONE")
        self.assertEqual(decision["next_packet"], "P1CDII-WP2")
        self.assertEqual(state["authority"]["P1CDII-G0"], "OPERATOR_PASS_MATERIALISED")
        self.assertEqual(state["authority"]["operational_read_only"], "DENIED")
        self.assertEqual(state["authority"]["continuous_intake"], "DENIED")
        self.assertIn(state["packets"]["P1CDII-WP1"]["status"], {"APPROVED", "COMPLETED"})
        self.assertEqual(state["packets"]["P1CDII-WP1"]["next_packet"], "P1CDII-WP2")


if __name__ == "__main__":
    unittest.main()
