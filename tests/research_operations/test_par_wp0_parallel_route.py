import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class ParallelRouteWP0Tests(unittest.TestCase):
    def test_semantic_snapshot_preserves_ec1_g1_and_parallel_owners(self):
        doc = load("docs/releases/ec1-dmrp-conformance-v0-1/c2p-parallel-route/par-wp0/PAR_WP0_SEMANTIC_SNAPSHOT_v0_1.json")
        self.assertEqual("OVC-EC1-DISCOVERY-2021_2023-G1", doc["scientific_generation"])
        self.assertEqual("UNCHANGED", doc["generation_effect"])
        self.assertEqual("PARALLEL", doc["architecture"]["relationship"])
        self.assertFalse(doc["architecture"]["episode_identity_implies_object_identity"])
        self.assertEqual("FORBIDDEN", doc["canonical_path1"]["c2p_candidate_influence"])
        self.assertIsNone(doc["c2p_sidecar"]["active_object_pack"])

    def test_two_key_interlock_is_non_transitive_and_fail_closed(self):
        doc = load("registries/research_operations/EC1_C2P_PARALLEL_ROUTE_EXECUTION_INTERLOCK_v0_1.json")
        self.assertTrue(doc["joint_execution"]["requires_both_pass"])
        self.assertFalse(doc["joint_execution"]["authority_transitive"])
        self.assertFalse(doc["joint_execution"]["dmrp_pass_grants_c2p"])
        self.assertFalse(doc["joint_execution"]["c2p_pass_grants_dmrp"])
        self.assertEqual("DENIED", doc["path1_firewall"]["c2p_as_seed"])
        self.assertEqual("LOCKED_UNCONSUMED", doc["validation"])

    def test_path2_partition_preserves_frozen_edge_cases(self):
        doc = load("registries/research_operations/P2_EXT_PARALLEL_ROUTE_PREREG_PARTITION_v0_1.json")
        self.assertEqual("MAY_PROCEED_PARTITIONED", doc["status_after_par_wp0"])
        for i in range(1, 6):
            self.assertEqual("IMPLEMENT_WHEN_EXACT_DEPENDENCIES_BIND", doc["protocols"][f"RP-EC1-EXT-000{i}-v0.1"])
        self.assertIn("DEPENDENCY_UNAVAILABLE", doc["protocols"]["RP-EC1-EXT-0006-v0.1"])
        self.assertIn("STAGE_A_POPULATION_PENDING", doc["protocols"]["RP-EC1-EXT-0007-v0.1"])
        self.assertEqual("DENIED", doc["common_rules"]["real_source_execution"])

    def test_successor_manifest_preserves_parent_and_exact_hashes(self):
        doc = load("registries/research_operations/EC1_DMRP_PRE_EVIDENCE_EXTERNAL_ARTIFACT_BINDINGS_v0_2.json")
        self.assertEqual("EC1-DMRP-PRE-EVIDENCE-EXTERNAL-ARTIFACT-BINDINGS-v0.1", doc["supersedes_for_current_projection"])
        self.assertEqual("PRESERVED_BYTE_IDENTITIES_NO_REWRITE", doc["parent_artifact_set"])
        overlay = doc["parallel_route_overlay"]
        self.assertEqual("978ea52d35c47f1b3043206f3f1387bcc58f5adad9d3253f5afd250a1982e7ac", overlay["amendment_docx"]["sha256"])
        self.assertEqual(44, overlay["artifact_impact_census_json"]["artifact_count"])
        self.assertEqual("LOCKED_UNCONSUMED", doc["validation"])

    def test_no_current_authority_is_silently_granted(self):
        state = load("registries/implementation/ec1_dmrp_v0_1/PAR_WP0_STATE_v0_1.json")
        self.assertEqual("HOLD_RECONCILED_NOT_APPROVED", state["dmrpi_greal"])
        self.assertEqual("SEPARATE_OPERATOR_GATE_NOT_APPROVED", state["c2p2_rs0_grun"])
        self.assertEqual("NONE_RESTRICTIVE_RECONCILIATION_ONLY", state["authority_delta"])
        self.assertEqual("LOCKED_UNCONSUMED", state["validation"])


if __name__ == "__main__":
    unittest.main()
