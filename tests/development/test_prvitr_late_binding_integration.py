from pathlib import Path
import unittest

from ovc.development.skills.vit_late_binding import (
    LateBindingPlacement,
    QualifiedPayloadCandidate,
    classify_main_movement_impact,
    evaluate_runnable_frontier,
)
from ovc.development.skills.vit_routing import (
    PAYLOAD_LINEAGE_SCHEMA,
    build_vit_payload_lineage_record,
    validate_vit_lineage_record,
)

ROOT = Path(__file__).resolve().parents[2]
ADMISSION = ROOT / "tools/ci/prvitr_live_admission.py"
WORKFLOW = ROOT / ".github/workflows/ovc-tiered-tests.yml"


class LateBindingIntegrationTests(unittest.TestCase):
    def _candidate(self, cid: str, pr: int, state: str = "QUALIFIED", deps=(), satisfied=(), conflicts=(), rank=0):
        return QualifiedPayloadCandidate(
            candidate_id=cid,
            pr_number=pr,
            pip_id=(f"{pr:064x}")[-64:],
            head_sha=(f"{pr:040x}")[-40:],
            qualification_state=state,
            authority_class="AUTO_EXECUTABLE",
            authority_delta="NONE",
            required_dependencies=tuple(deps),
            satisfied_dependencies=tuple(satisfied),
            conflict_blockers=tuple(conflicts),
            fairness_rank=rank,
        )

    def test_unready_earlier_candidate_does_not_block_later_runnable_candidate(self):
        a = self._candidate("A", 100, state="WAITING_QA", rank=0)
        c = self._candidate("C", 102, rank=2)
        decision = evaluate_runnable_frontier((a, c))
        self.assertEqual(decision.selected_candidate_id, "C")
        self.assertEqual(decision.runnable_candidate_ids, ("C",))
        self.assertIn("A", decision.blocked)

    def test_real_dependency_blocks_even_when_candidate_is_otherwise_qualified(self):
        b = self._candidate("B", 101, state="WAITING_QA")
        d = self._candidate("D", 103, deps=("B",), satisfied=())
        c = self._candidate("C", 102)
        decision = evaluate_runnable_frontier((b, d, c))
        self.assertEqual(decision.selected_candidate_id, "C")
        self.assertTrue(any(reason.startswith("DEPENDENCY:B") for reason in decision.blocked["D"]))

    def test_pr_number_is_tie_breaker_only_among_runnable_candidates(self):
        blocked_old = self._candidate("OLD", 1, state="FAILED", rank=0)
        new = self._candidate("NEW", 999, rank=999)
        decision = evaluate_runnable_frontier((blocked_old, new))
        self.assertEqual(decision.selected_candidate_id, "NEW")

    def test_payload_lineage_contains_no_physical_placement(self):
        pip = {
            "schema_version": "packet-integration-payload/v0.1",
            "programme_id": "PROGRAMME",
            "packet_id": "PACKET",
            "logical_changes": [{"op": "ADD", "path": "x.txt", "blob_sha": "1" * 40, "mode": "100644"}],
            "authority_manifest_id": "a" * 64,
            "dependency_frontier_id": "b" * 64,
            "completion_transition": {"status": "COMPLETED"},
        }
        record = build_vit_payload_lineage_record(
            programme_id="PROGRAMME",
            packet_id="PACKET",
            pip_identity_payload=pip,
        )
        self.assertEqual(record["schema"], PAYLOAD_LINEAGE_SCHEMA)
        self.assertNotIn("generation", record)
        self.assertNotIn("placement", record)
        self.assertEqual(record["binding_policy"], "LATE_PHYSICAL_PLACEMENT")
        validated = validate_vit_lineage_record(record)
        self.assertTrue(validated.late_binding)
        self.assertIsNone(validated.placement_id)

    def test_late_placement_identity_changes_with_base_without_changing_pip(self):
        common = dict(
            pip_id="a" * 64,
            candidate_head_sha="1" * 40,
            physical_base_tree="2" * 40,
            prospective_tree_sha="3" * 40,
            authority_manifest_id="b" * 64,
            dependency_frontier_id="c" * 64,
        )
        first = LateBindingPlacement(physical_base_sha="4" * 40, **common)
        second = LateBindingPlacement(physical_base_sha="5" * 40, **common)
        self.assertNotEqual(first.placement_id, second.placement_id)
        self.assertEqual(first.pip_id, second.pip_id)

    def test_main_movement_is_placement_only_when_no_relevant_frontier_changed(self):
        self.assertEqual(
            classify_main_movement_impact(
                payload_changed=False,
                dependency_frontier_changed=False,
                authority_changed=False,
                assurance_dependency_intersection=False,
            ),
            "PLACEMENT_ONLY",
        )
        self.assertEqual(
            classify_main_movement_impact(
                payload_changed=False,
                dependency_frontier_changed=False,
                authority_changed=False,
                assurance_dependency_intersection=True,
            ),
            "ASSURANCE_RENEWAL_REQUIRED",
        )

    def test_runtime_has_no_train_predecessor_wait(self):
        admission = ADMISSION.read_text(encoding="utf-8")
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("resolve_vit_train_predecessor", admission)
        self.assertNotIn("VIT_TRAIN_PREDECESSOR", admission)
        self.assertNotIn("PREDECESSOR_TIMEOUT_SECONDS", admission)
        self.assertIn("merge-tree", admission)
        self.assertIn("OVC_READY_PHYSICAL_BASE_BINDING=NONE", workflow)
        self.assertIn("git checkout --detach", workflow)


if __name__ == "__main__":
    unittest.main()
