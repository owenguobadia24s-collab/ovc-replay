from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.programme_genesis.grt_v0_2.bootstrap import validate_instance
from ovc.programme_genesis.grt_v0_2.integration import (
    IntegrationProofError, build_cache_key, build_conformance_proof, build_integration_context,
    build_post_merge_receipt, classify_movement, compute_impact_closure, evaluate_readiness,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "fixtures/governance/grt_v0_2/wp3d/integration_fixture.json"
SCHEMA = ROOT / "schemas/governance/grt_v0_2/integration_readiness.schema.json"


class GRT2WP3DIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def context(self):
        f = self.fixture
        return build_integration_context(
            base_commit=f["base_commit"], base_tree=f["base_tree"], head_commit=f["head_commit"], head_tree=f["head_tree"],
            integration_tree=f["integration_tree"], merge_strategy=f["merge_strategy"], constitution_hash=f["constitution_hash"],
            runtime_hash=f["runtime_hash"], scanner_hash=f["scanner_hash"], debt_floor_generation=None, debt_floor_hash=None,
        )

    def proof(self):
        f = self.fixture
        return build_conformance_proof(context=self.context(), result="PASS", findings_hash=f["findings_hash"], debt_hash=f["debt_hash"], evidence_hash=f["evidence_hash"])

    def test_cache_identity_uses_semantic_hashes_only(self) -> None:
        f = self.fixture
        key = build_cache_key(layer_id="L4", input_hashes=[f["findings_hash"]], runtime_release_hash=f["runtime_hash"], scanner_hash=f["scanner_hash"], constitution_hash=f["constitution_hash"], registry_hashes=[f["debt_hash"]])
        same = build_cache_key(layer_id="L4", input_hashes=[f["findings_hash"]], runtime_release_hash=f["runtime_hash"], scanner_hash=f["scanner_hash"], constitution_hash=f["constitution_hash"], registry_hashes=[f["debt_hash"]])
        self.assertEqual(key, same)
        self.assertEqual(len(key), 64)

    def test_ambiguous_impact_escalates_full_reference(self) -> None:
        result = compute_impact_closure(["A"], [{"source_artifact_id":"A","target_artifact_id":"B","status":"RESOLVED"},{"source_artifact_id":"B","target_artifact_id":"C","status":"AMBIGUOUS"}])
        self.assertEqual(result["affected_artifact_ids"], ["A", "B"])
        self.assertEqual(result["escalation"], "FULL_REFERENCE")

    def test_exact_pass_context_is_ready_and_schema_valid(self) -> None:
        proof = self.proof(); f = self.fixture
        movement = classify_movement(proof=proof, current_main_commit=f["base_commit"], current_head_commit=f["head_commit"], current_integration_tree=f["integration_tree"])
        readiness = evaluate_readiness(proof=proof, current_main_commit=f["base_commit"], current_head_commit=f["head_commit"], current_integration_tree=f["integration_tree"], movement_class=movement)
        self.assertEqual(readiness["status"], "READY")
        validate_instance(readiness, json.loads(SCHEMA.read_text(encoding="utf-8")))

    def test_head_or_constitution_movement_requires_renewal(self) -> None:
        proof = self.proof(); f = self.fixture
        head = classify_movement(proof=proof, current_main_commit=f["base_commit"], current_head_commit="6"*40, current_integration_tree=f["integration_tree"])
        self.assertEqual(head, "HEAD_MOVED")
        constitution = classify_movement(proof=proof, current_main_commit=f["base_commit"], current_head_commit=f["head_commit"], current_integration_tree=f["integration_tree"], constitution_hash="1"*64)
        self.assertEqual(constitution, "CONSTITUTION_CHANGED")

    def test_post_merge_tree_mismatch_is_incident(self) -> None:
        receipt = build_post_merge_receipt(proof=self.proof(), actual_merge_commit="6"*40, actual_merge_tree="7"*40)
        self.assertEqual(receipt["status"], "INCIDENT")
        self.assertFalse(receipt["post_merge_tree_equal"])
        self.assertIn("POST_MERGE_TREE_MISMATCH", receipt["reason_codes"])

    def test_pre_g3_receipt_cannot_create_debt_floor(self) -> None:
        with self.assertRaises(IntegrationProofError):
            build_post_merge_receipt(proof=self.proof(), actual_merge_commit="6"*40, actual_merge_tree=self.fixture["integration_tree"], new_debt_floor_generation=0, new_debt_floor_hash="1"*64)


if __name__ == "__main__":
    unittest.main()
