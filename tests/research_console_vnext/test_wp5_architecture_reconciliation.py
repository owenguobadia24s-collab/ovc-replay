from __future__ import annotations
import hashlib
import json
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs/implementation/research-console-vnext/rcn-rn-v0-3-wp5-materialisation"
RECON = ROOT / "docs/implementation/research-console-vnext/rcn-rn-wp5-architecture-reconciliation"
STATE = ROOT / "registries/implementation/research_console_vnext/OVC_RCN_RN_STATE_v0_2.json"
def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
class TestWp5ArchitectureReconciliation(unittest.TestCase):
    def test_source_faithful_ppm_remains_immutable(self) -> None:
        source_ref = load(SOURCE / "PLAN_SOURCE_REF.json")
        self.assertEqual(hashlib.sha256((SOURCE / "GOVERNING_SCOPE.md").read_bytes()).hexdigest(), source_ref["source_sha256"])
        self.assertEqual(load(SOURCE / "PACKET_MANIFEST_RCN_RN_WP5B.json")["packet_id"], "RCN-RN-WP5B")
        self.assertEqual(load(SOURCE / "PACKET_MANIFEST_RCN_RN_WP5C.json")["packet_id"], "RCN-RN-WP5C")
    def test_reconciled_split_and_none_authority(self) -> None:
        graph = load(RECON / "RCN_RN_WP5_RECONCILED_PACKET_GRAPH_v0_1.json")
        self.assertFalse(graph["source_plan_semantics_changed"])
        self.assertEqual(graph["legacy_lineage"]["RCN-RN-WP5B"], ["RCN-RN-WP5B1", "RCN-RN-WP5B2"])
        self.assertEqual(graph["legacy_lineage"]["RCN-RN-WP5C"], ["RCN-RN-WP5C1", "RCN-RN-WP5C2"])
        for packet_id in ("WP5B1", "WP5B2", "WP5C1", "WP5C2"):
            self.assertEqual(load(RECON / f"PACKET_MANIFEST_RCN_RN_{packet_id}.json")["authority_delta"], "NONE")
    def test_source_admission_non_transitive(self) -> None:
        matrix = load(RECON / "RCN_RN_WP5_SOURCE_ADMISSION_MATRIX_v0_1.json")
        self.assertEqual(matrix["global_rule"], "SOURCE_PRESENTATION_AUTHORITY_IS_PER_SOURCE_AND_NON_TRANSITIVE")
        self.assertIn("ONE_SOURCE_G5_PASS_IMPLIES_ANOTHER_SOURCE_G5_PASS", matrix["forbidden_inferences"])
        self.assertEqual(set(matrix["sources"]), {"DMRP", "RCCR", "PRSC_EC1", "OPT_C", "OPT_D"})
    def test_owner_sources_and_no_duplicate_cross_mode_logic(self) -> None:
        for path in [ROOT / "src/ovc/research_operations/dmrp.py", ROOT / "src/ovc/research_operations/rccr/post_pilot_read_models.py", ROOT / "contracts/research_operations/ec1/prsc/PRSC_REPRESENTATION_TEMPORAL_CONTEXT_CONTRACT_v0_1.md", ROOT / "contracts/research_operations/ec1/prsc/PRSC_MULTIPLICITY_CONTRACT_v0_1.md", ROOT / "registries/system_atlas/ATLAS_QUERY_POLICY_REGISTRY_v0_1.json"]:
            self.assertTrue(path.exists(), str(path))
        graph = load(RECON / "RCN_RN_WP5_RECONCILED_PACKET_GRAPH_v0_1.json")
        self.assertEqual(next(node for node in graph["nodes"] if node["packet_id"] == "RCN-RN-WP5B2")["console_role"], "PROJECT_OWNER_READ_MODELS_DO_NOT_REIMPLEMENT")
        self.assertFalse(graph["atlas_integration"]["correctness_dependency"])
    def test_state_advances_from_reconciliation_into_wp5b1_only(self) -> None:
        state = load(STATE)
        self.assertEqual(state["authority_delta"], "NONE")
        self.assertEqual(state["current_packet"], "RCN-RN-WP5B1")
        self.assertEqual(state["next_packet"], "RCN-RN-WP5B2")
        self.assertEqual(state["stop_boundary"], "RCN-RN-G5-FIRST-NEW-SOURCE_OR_OTHER_RESERVED_AUTHORITY_CHANGE")
        self.assertEqual(state["source_authority_overlays"]["DMRP"]["gate_id"], "RCN-RN-G5-FIRST-NEW-SOURCE[DMRP]")
        self.assertFalse(state["source_authority_overlays"]["DMRP"]["transitive"])
if __name__ == "__main__":
    unittest.main()