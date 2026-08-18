from __future__ import annotations

from dataclasses import asdict
import json
import unittest

from ovc.development.skills.vit_frontier_decoupling import (
    FrontierIntegrationAssuranceGeneration,
    assurance_generation_from_record,
)


class PRVITRFinalizeSequenceParityTests(unittest.TestCase):
    def test_json_rehydration_restores_tuple_sequence_parity_before_a2_finalize(self) -> None:
        preliminary = FrontierIntegrationAssuranceGeneration(
            source_head_id="a" * 64,
            source_head_commit="b" * 40,
            pip_id="c" * 64,
            vit_generation_id="d" * 64,
            placement_id="e" * 64,
            predecessor_commit="f" * 40,
            predecessor_tree="1" * 40,
            prospective_result_tree="2" * 40,
            authority_manifest_id="3" * 64,
            dependency_frontier_id="4" * 64,
            policy_id="PRVITR-VIT-FRONTIER-DECOUPLING-POLICY-v0.1",
            a0_result_ids=("5" * 64,),
            a1_proof_id="6" * 64,
            source_run_ids=("github-actions-run:1",),
        )
        persisted = json.loads(json.dumps(asdict(preliminary)))
        self.assertIsInstance(persisted["a0_result_ids"], list)
        self.assertIsInstance(persisted["a2_result_ids"], list)
        self.assertIsInstance(persisted["source_run_ids"], list)

        restored = assurance_generation_from_record(
            persisted,
            expected_id=preliminary.assurance_generation_id,
        )
        self.assertIsInstance(restored.a0_result_ids, tuple)
        self.assertIsInstance(restored.a2_result_ids, tuple)
        self.assertIsInstance(restored.source_run_ids, tuple)
        self.assertEqual(restored.assurance_generation_id, preliminary.assurance_generation_id)

        final = FrontierIntegrationAssuranceGeneration(
            source_head_id=restored.source_head_id,
            source_head_commit=restored.source_head_commit,
            pip_id=restored.pip_id,
            vit_generation_id=restored.vit_generation_id,
            placement_id=restored.placement_id,
            predecessor_commit=restored.predecessor_commit,
            predecessor_tree=restored.predecessor_tree,
            prospective_result_tree=restored.prospective_result_tree,
            authority_manifest_id=restored.authority_manifest_id,
            dependency_frontier_id=restored.dependency_frontier_id,
            policy_id=restored.policy_id,
            a0_result_ids=restored.a0_result_ids,
            a1_proof_id=restored.a1_proof_id,
            assurance_stage="A2_QUALIFIED",
            a2_result_ids=("7" * 64,),
            source_run_ids=restored.source_run_ids + ("github-actions-run:2",),
            supersedes_assurance_generation_id=restored.assurance_generation_id,
        )
        self.assertEqual(final.assurance_stage, "A2_QUALIFIED")
        self.assertEqual(final.a2_result_ids, ("7" * 64,))


if __name__ == "__main__":
    unittest.main()
