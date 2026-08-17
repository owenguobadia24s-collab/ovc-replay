import unittest

from ovc.development.prvit_remediation import (
    ImmutableVITLineagePointer,
    IntegrationAssuranceGeneration,
    PRVITRemediationError,
    ShadowGRTProof,
    ShadowPlacement,
    TypedAssuranceResult,
    ancestry_disposition,
    build_post_materialisation_receipt,
    classify_main_movement,
    compare_legacy_and_shadow,
    evaluate_shadow_admission,
    semantic_dispatch_key,
)

A = "a" * 64
B = "b" * 64
C = "c" * 64
D = "d" * 64
T1 = "1" * 40
T2 = "2" * 40
T3 = "3" * 40


def assurance(state="PASS", required=True, run="run-1"):
    return TypedAssuranceResult("tests", state, B, f"evidence:{state}", required, run)


def placement(frontier=B):
    return ShadowPlacement(A, T1, T2, C, frontier)


def grt(tree=T2, state="PASS"):
    return ShadowGRTProof(tree, "proof", "grt-v0.2", state)


class PRVITRShadowRemediationTests(unittest.TestCase):
    def test_prvit_r01_main_move_is_placement_only(self):
        decision = classify_main_movement(
            same_pip=True,
            dependency_frontier_changed=False,
            authority_changed=False,
        )
        self.assertEqual(decision.disposition, "PLACEMENT_RECOMPUTE_ONLY")
        self.assertTrue(decision.a0_reuse_allowed)
        self.assertFalse(decision.payload_rebuild_required)

    def test_prvit_r02_invalid_placement_does_not_mutate_a0(self):
        a0 = assurance()
        disposition, reasons = evaluate_shadow_admission(
            pip_id=A,
            placement=placement(D),
            assurances=[a0],
            grt=grt(),
            authority_manifest_id=C,
            dependency_frontier_id=B,
        )
        self.assertEqual(a0.state, "PASS")
        self.assertEqual(disposition, "BLOCK")
        self.assertIn("PLACEMENT_FRONTIER_MISMATCH", reasons)

    def test_prvit_r03_blocked_upstream_is_not_fail(self):
        result = assurance("BLOCKED_UPSTREAM")
        disposition, reasons = evaluate_shadow_admission(
            pip_id=A,
            placement=placement(),
            assurances=[result],
            grt=grt(),
        )
        self.assertEqual(result.state, "BLOCKED_UPSTREAM")
        self.assertEqual(disposition, "BLOCK")
        self.assertTrue(any("BLOCKED_UPSTREAM" in reason for reason in reasons))

    def test_prvit_r04_required_fail_blocks(self):
        disposition, _ = evaluate_shadow_admission(
            pip_id=A,
            placement=placement(),
            assurances=[assurance("FAIL")],
            grt=grt(),
        )
        self.assertEqual(disposition, "BLOCK")

    def test_prvit_r05_not_applicable_only_when_optional(self):
        disposition, _ = evaluate_shadow_admission(
            pip_id=A,
            placement=placement(),
            assurances=[assurance("NOT_APPLICABLE", False)],
            grt=grt(),
        )
        self.assertEqual(disposition, "SHADOW_READY")
        with self.assertRaisesRegex(PRVITRemediationError, "REQUIRED_ASSURANCE_NOT_APPLICABLE"):
            assurance("NOT_APPLICABLE", True)

    def test_prvit_r06_rerun_creates_new_generation(self):
        p = placement()
        result1 = assurance(run="run-1")
        result2 = assurance(run="run-2")
        generation1 = IntegrationAssuranceGeneration(
            A, T2, p.placement_id, T1, C, B, "policy-v1",
            (result1.result_id,), ("run-1",),
        )
        generation2 = IntegrationAssuranceGeneration(
            A, T2, p.placement_id, T1, C, B, "policy-v1",
            (result2.result_id,), ("run-2",), generation1.generation_id,
        )
        self.assertNotEqual(generation1.generation_id, generation2.generation_id)
        self.assertEqual(generation2.supersedes_generation_id, generation1.generation_id)

    def test_prvit_r07_pr_metadata_cannot_change_pointer(self):
        pointer1 = ImmutableVITLineagePointer(A, "records/development/vit/lineage/a.json", B)
        pointer2 = ImmutableVITLineagePointer(A, "records/development/vit/lineage/a.json", B)
        self.assertEqual(pointer1.pointer_id, pointer2.pointer_id)

    def test_prvit_r08_duplicate_dispatch_is_idempotent(self):
        key = semantic_dispatch_key("programme", "packet", A)
        self.assertEqual(semantic_dispatch_key("programme", "packet", A), key)
        self.assertNotEqual(semantic_dispatch_key("programme", "other", A), key)

    def test_prvit_r09_compare_api_cannot_override_git(self):
        self.assertEqual(
            ancestry_disposition(compare_api_status=404, local_git_ancestor=True),
            "PASS_GIT_NATIVE",
        )
        self.assertEqual(
            ancestry_disposition(compare_api_status=200, local_git_ancestor=False),
            "FAIL_NOT_ANCESTOR",
        )
        self.assertEqual(
            ancestry_disposition(compare_api_status=404, local_git_ancestor=None),
            "NOT_EVALUABLE_GIT_PROOF_REQUIRED",
        )

    def test_prvit_r10_tree_mismatch_blocks(self):
        disposition, reasons = evaluate_shadow_admission(
            pip_id=A,
            placement=placement(),
            assurances=[assurance()],
            grt=grt(T3),
        )
        self.assertEqual(disposition, "BLOCK")
        self.assertIn("PROSPECTIVE_GRT_TREE_MISMATCH", reasons)
        with self.assertRaisesRegex(PRVITRemediationError, "POST_WRITE_TREE_MISMATCH"):
            build_post_materialisation_receipt(
                transaction_id="txn",
                pip_id=A,
                qualified_tree=T2,
                physical_commit=T3,
                physical_tree=T3,
                completed_packet="packet",
            )

    def test_shadow_only_allow_never_silently_authoritative(self):
        comparison = compare_legacy_and_shadow(
            legacy_allowed=False,
            shadow_disposition="SHADOW_READY",
        )
        self.assertFalse(comparison["equivalent"])
        self.assertEqual(
            comparison["classification"],
            "SHADOW_ONLY_ALLOW_REQUIRES_INVESTIGATION",
        )


if __name__ == "__main__":
    unittest.main()
