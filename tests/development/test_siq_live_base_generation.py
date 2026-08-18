from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "ovc-tiered-tests.yml"
ASSURANCE_PREFLIGHT = ROOT / "tools" / "ci" / "vit_assurance_preflight.py"
ROUTING_PREFLIGHT = ROOT / "tools" / "ci" / "vit_routing_preflight.py"
ADMISSION = ROOT / "tools" / "ci" / "prvitr_live_admission.py"
POST_MERGE = ROOT / "tools" / "ci" / "vit_post_merge_completion.py"


class SIQLiveBaseGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")
        cls.assurance_text = ASSURANCE_PREFLIGHT.read_text(encoding="utf-8")
        cls.routing_text = ROUTING_PREFLIGHT.read_text(encoding="utf-8")
        cls.admission_text = ADMISSION.read_text(encoding="utf-8")
        cls.post_merge_text = POST_MERGE.read_text(encoding="utf-8")

    def test_same_pr_concurrency_is_scoped_to_exact_source_head(self) -> None:
        self.assertIn(
            "group: ovc-pr-${{ github.event.pull_request.number || github.ref }}-${{ github.event.pull_request.head.sha || github.sha }}",
            self.text,
        )

    def test_event_base_is_provenance_not_materialisation_authority(self) -> None:
        self.assertIn("prvitr_live_admission.py ready", self.text)
        self.assertIn("prvitr_live_admission.py acquire", self.text)
        self.assertIn("tree_is_in_commit_ancestry", self.admission_text)
        self.assertIn("build_frontier_lineage", self.admission_text)
        self.assertIn("classify_frontier_movement", self.routing_text)
        self.assertIn("same_pr=true", self.routing_text)
        self.assertNotIn("OVC_RECONCILE_REQUIRED", self.admission_text)
        self.assertNotIn("compareCommits", self.text)

    def test_live_source_head_is_rechecked_but_not_rebased(self) -> None:
        self.assertIn("def _live_pr", self.admission_text)
        self.assertGreaterEqual(
            self.admission_text.count("OVC_SIQ_SUPERSEDED_EVENT_HEAD"), 3
        )
        self.assertIn("source_head_sha", self.text)
        self.assertNotIn("candidate contains acquired current main", self.text.lower())
        self.assertNotIn("merge-base --is-ancestor", self.text)

    def test_a0_a1_a2_a3_boundaries_are_explicit(self) -> None:
        self.assertIn("A0_PIP_ONLY", self.assurance_text)
        self.assertIn("a1_proof_id", self.admission_text)
        self.assertIn("OVC_A2_PROSPECTIVE_CHECKOUT", self.text)
        self.assertIn("qualified prospective tree", self.admission_text)
        self.assertIn("post-merge A3", self.admission_text)

    def test_predecessor_resolution_remains_vit_tree_based(self) -> None:
        self.assertIn("resolve_vit_train_predecessor", self.admission_text)
        self.assertIn("_open_vit_placements", self.admission_text)
        self.assertIn("tree_is_in_commit_ancestry", self.admission_text)
        self.assertIn(
            "OVC_FINAL_INTEGRATION_VIT_TRAIN_PREDECESSOR_HELD",
            self.admission_text,
        )
        self.assertNotIn("_exact_merge_job_pass", self.admission_text)
        self.assertNotIn("number>=pr_number", self.admission_text.replace(" ", ""))

    def test_assurance_identity_reads_live_pr_and_stays_pip_bound(self) -> None:
        self.assertIn("def _live_pr_payload", self.assurance_text)
        self.assertIn(
            "https://api.github.com/repos/{repo}/pulls/{pr_number}",
            self.assurance_text,
        )
        self.assertIn("VIT_ASSURANCE_SUPERSEDED_EVENT_HEAD", self.assurance_text)
        self.assertIn("aa0_identity", self.assurance_text)
        self.assertIn("lineage.pip_id", self.assurance_text)

    def test_prewrite_freeze_is_created_only_after_physical_lease(self) -> None:
        self.assertNotIn("build_live_transaction_freeze", self.assurance_text)
        self.assertIn("build_live_transaction_freeze", self.admission_text)
        self.assertIn("OVC_ASSURANCE_GENERATION_B64", self.text)
        self.assertNotIn("OVC_TRANSACTION_FREEZE_MARKER", self.text)
        self.assertIn("print(freeze_marker)", self.admission_text)
        self.assertIn("SIQ_PHYSICAL_LANE_AFTER_A2", self.admission_text)
        self.assertIn("OVC merge readiness", self.post_merge_text)

    def test_one_writer_and_exact_final_guards_remain(self) -> None:
        self.assertIn("group: ovc-main-integration-lane-v1", self.text)
        self.assertIn("cancel-in-progress: false", self.text)
        self.assertIn("PREDECESSOR_MOVED", self.admission_text)
        self.assertIn("PRVITR_PROSPECTIVE_COMMIT_TREE_MISMATCH", self.admission_text)
        self.assertIn("ShadowGRTProof", self.admission_text)
        self.assertIn("OVC_FINAL_INTEGRATION_WINDOW_PASS", self.admission_text)
        self.assertIn("prvitr_live_admission.py finalize", self.text)


if __name__ == "__main__":
    unittest.main()
