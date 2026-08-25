from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "ovc-tiered-tests.yml"
ASSURANCE_PREFLIGHT = ROOT / "tools" / "ci" / "vit_assurance_preflight.py"
ADMISSION = ROOT / "tools" / "ci" / "prvitr_live_admission.py"
READY_SELECTOR = ROOT / "tools" / "ci" / "prvitr_rac_ready.py"


class SIQLiveBaseGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")
        cls.assurance_text = ASSURANCE_PREFLIGHT.read_text(encoding="utf-8")
        cls.admission_text = ADMISSION.read_text(encoding="utf-8")
        cls.ready_selector_text = READY_SELECTOR.read_text(encoding="utf-8")

    def test_same_pr_concurrency_is_scoped_to_exact_head_generation(self) -> None:
        self.assertIn(
            "group: ovc-pr-${{ github.event.pull_request.number || github.ref }}-${{ github.event.pull_request.head.sha || github.sha }}",
            self.text,
        )

    def test_event_base_is_provenance_not_final_readiness_authority(self) -> None:
        self.assertIn("prvitr_rac_ready.py", self.text)
        self.assertIn("import tools.ci.prvitr_live_admission as live", self.ready_selector_text)
        self.assertIn("return live.command_ready()", self.ready_selector_text)
        self.assertIn("prvitr_live_admission.py acquire", self.text)
        ready = self.admission_text.split("def command_ready()", 1)[1].split("def command_acquire()", 1)[0]
        acquire = self.admission_text.split("def command_acquire()", 1)[1].split("def command_finalize()", 1)[0]
        self.assertNotIn("current_main = _branch_sha(base_ref)", ready)
        self.assertNotIn("_branch_sha(base_ref)", self.ready_selector_text)
        self.assertIn("current_main = _branch_sha(base_ref)", acquire)
        self.assertIn("_compose_late_binding(", acquire)
        self.assertNotIn("compareCommits", self.text)

    def test_live_pr_head_is_rechecked_before_ready_and_final_pass(self) -> None:
        self.assertIn("def _live_pr", self.admission_text)
        self.assertGreaterEqual(
            self.admission_text.count("OVC_SIQ_SUPERSEDED_EVENT_HEAD"), 3
        )
        self.assertIn("live = _live_pr(pr_number)", self.admission_text)
        self.assertIn("OVC_SIQ_SUPERSEDED_EVENT_HEAD", self.ready_selector_text)

    def test_no_pr_number_or_train_predecessor_fifo_controls_live_admission(self) -> None:
        self.assertNotIn("resolve_vit_train_predecessor", self.admission_text)
        self.assertNotIn("_open_vit_placements", self.admission_text)
        self.assertNotIn("blocking_pr_number", self.admission_text)
        self.assertNotIn("sorted(_open_pulls", self.admission_text)
        self.assertIn("no physical-main predecessor is acquired during qualification", self.admission_text)
        self.assertIn("OVC_VIT_LATE_BINDING_PLACEMENT_ACQUIRED", self.admission_text)

    def test_main_movement_invalidates_ephemeral_placement_not_qualified_payload(self) -> None:
        self.assertIn("OVC_BASE_MOVED_DURING_READINESS", self.admission_text)
        self.assertIn("discard the ephemeral placement and retry the same qualified payload", self.admission_text)
        self.assertNotIn("OVC_RECONCILE_REQUIRED", self.admission_text)
        self.assertNotIn("OVC_READY_BASE_REFRESHED_BEFORE_FINAL_LEASE", self.admission_text)

    def test_assurance_identity_reads_live_pr_body_and_rejects_superseded_head(self) -> None:
        self.assertIn("def _live_pr_payload", self.assurance_text)
        self.assertIn(
            "https://api.github.com/repos/{repo}/pulls/{pr_number}",
            self.assurance_text,
        )
        self.assertIn("VIT_ASSURANCE_SUPERSEDED_EVENT_HEAD", self.assurance_text)
        self.assertIn("event_head_sha", self.assurance_text)
        self.assertIn("pr = _live_pr_payload(event)", self.assurance_text)

    def test_assurance_preflight_emits_the_normal_prewrite_pmt_freeze(self) -> None:
        self.assertIn("build_live_transaction_freeze", self.assurance_text)
        self.assertIn("encode_freeze_marker", self.assurance_text)
        self.assertIn(
            "_emit_prewrite_freeze(event=event, pr=pr, lineage_record=lineage_record)",
            self.assurance_text,
        )
        self.assertIn("GITHUB_RUN_ID", self.assurance_text)
        self.assertIn("GITHUB_RUN_ATTEMPT", self.assurance_text)

    def test_one_writer_and_exact_final_guards_remain(self) -> None:
        self.assertIn("group: ovc-main-integration-lane-v1", self.text)
        self.assertIn("cancel-in-progress: false", self.text)
        self.assertIn("OVC_BASE_MOVED_DURING_READINESS", self.admission_text)
        self.assertIn("PRVITR_LATE_BINDING_PLACEMENT_MISMATCH", self.admission_text)
        self.assertIn("ShadowGRTProof", self.admission_text)
        self.assertIn("OVC_INTEGRATION_ADMISSION_RECEIPT", self.admission_text)
        self.assertIn("OVC_FINAL_INTEGRATION_WINDOW_PASS", self.admission_text)
        self.assertIn("prvitr_live_admission.py finalize", self.text)


if __name__ == "__main__":
    unittest.main()
