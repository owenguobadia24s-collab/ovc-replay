from __future__ import annotations

import unittest

from ovc.development.skills.vit_frontier_decoupling import classify_frontier_movement


class ProgrammeLocalMovementRegressionTests(unittest.TestCase):
    def test_cers_development_paths_are_placement_only(self) -> None:
        pip = {
            "programme_id": "OVC-DSAI-VIT-v0.3",
            "packet_id": "DSAI3V-PRVITR-VIT-FRONTIER-DECOUPLING",
            "authority_manifest_id": "a" * 64,
            "dependency_frontier_id": "b" * 64,
            "logical_changes": [
                {
                    "op": "MODIFY",
                    "path": "tools/ci/prvitr_live_admission.py",
                    "blob_sha": "c" * 40,
                    "mode": "100644",
                }
            ],
            "completion_transition": {"status": "COMPLETED"},
        }
        decision = classify_frontier_movement(
            pip=pip,
            source_predecessor_tree="1" * 40,
            current_predecessor_tree="2" * 40,
            changed_paths=(
                "src/ovc/development/skills/cers/runtime.py",
                "registries/development/skills/cers/CERS_ACTION_SIDE_EFFECT_REGISTRY_v0_2.json",
                "tests/development_skills/cers/test_cers_shadow_runtime.py",
            ),
        )
        self.assertEqual(decision.disposition, "PLACEMENT_RECOMPUTE_ONLY")
        self.assertTrue(decision.a0_reuse_allowed)
        self.assertTrue(decision.a1_renewal_required)
        self.assertTrue(decision.a2_renewal_required)
        self.assertFalse(decision.payload_rebuild_required)
        self.assertFalse(decision.authority_review_required)

    def test_vit_harness_change_still_renews_assurance(self) -> None:
        pip = {
            "programme_id": "OVC-DSAI-VIT-v0.3",
            "packet_id": "DSAI3V-PRVITR-VIT-FRONTIER-DECOUPLING",
            "authority_manifest_id": "a" * 64,
            "dependency_frontier_id": "b" * 64,
            "logical_changes": [
                {
                    "op": "MODIFY",
                    "path": "contracts/development/skills/OVC_PRVITR_VIT_FRONTIER_DECOUPLING_CONTRACT_v0_1.md",
                    "blob_sha": "c" * 40,
                    "mode": "100644",
                }
            ],
            "completion_transition": {"status": "COMPLETED"},
        }
        decision = classify_frontier_movement(
            pip=pip,
            source_predecessor_tree="1" * 40,
            current_predecessor_tree="2" * 40,
            changed_paths=("tools/ci/vit_routing_preflight.py",),
        )
        self.assertEqual(decision.disposition, "ASSURANCE_RENEWAL_REQUIRED")
        self.assertTrue(decision.a0_reuse_allowed)


if __name__ == "__main__":
    unittest.main()
