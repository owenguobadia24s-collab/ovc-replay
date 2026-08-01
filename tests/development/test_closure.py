from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from ovc.development.closure import (
    ClosureError,
    compare_receipt_proposal,
    evaluate_closure,
    load_closure_policy,
    load_closure_snapshot,
    parse_closure_policy,
    parse_closure_snapshot,
    propose_merge_receipt,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "registries/development/OVC_DEVELOPMENT_ACCELERATION_CLOSURE_POLICY_v0_1.json"
FIXTURES = ROOT / "fixtures/development/closure"
PASS_PATH = FIXTURES / "closure_snapshot_pass_v0_1.json"
BLOCK_PATH = FIXTURES / "closure_snapshot_block_v0_1.json"
MANUAL_PATH = FIXTURES / "manual_receipt_pass_v0_1.json"
MERGE_SHA = "3333333333333333333333333333333333333333"


class ClosureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = load_closure_policy(POLICY_PATH)
        self.snapshot = load_closure_snapshot(PASS_PATH)
        self.manual = json.loads(MANUAL_PATH.read_text(encoding="utf-8"))

    def test_pass_closure_is_deterministic_and_no_write(self) -> None:
        before = {
            path.name: path.read_bytes()
            for path in (POLICY_PATH, PASS_PATH, MANUAL_PATH)
        }
        first = evaluate_closure(self.snapshot, self.policy)
        second = evaluate_closure(self.snapshot, self.policy)
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "PASS")
        self.assertTrue(first["eligible_for_manual_squash_merge"])
        self.assertEqual(first["proposed_merge_method"], "squash")
        self.assertTrue(first["exact_head_required"])
        self.assertFalse(first["authority"]["writes_performed"])
        self.assertFalse(first["authority"]["merge_performed"])
        self.assertEqual(first["authority"]["repository_bot_write"], "DENIED")
        after = {
            path.name: path.read_bytes()
            for path in (POLICY_PATH, PASS_PATH, MANUAL_PATH)
        }
        self.assertEqual(before, after)

    def test_receipt_proposal_matches_manual_reference(self) -> None:
        proposal = propose_merge_receipt(self.snapshot, self.policy, MERGE_SHA)
        self.assertTrue(proposal["proposal_only"])
        self.assertEqual(proposal["receipt"], self.manual)
        self.assertFalse(proposal["authority"]["merge_performed"])
        comparison = compare_receipt_proposal(proposal, self.manual)
        self.assertEqual(comparison["status"], "PASS")
        self.assertEqual(comparison["differences"], [])
        self.assertTrue(comparison["material_fields_equal"])
        self.assertFalse(comparison["authority"]["writes_performed"])

    def test_manual_receipt_difference_blocks(self) -> None:
        proposal = propose_merge_receipt(self.snapshot, self.policy, MERGE_SHA)
        changed = copy.deepcopy(self.manual)
        changed["squash_merge_sha"] = "4444444444444444444444444444444444444444"
        changed["unexpected"] = "field"
        comparison = compare_receipt_proposal(proposal, changed)
        self.assertEqual(comparison["status"], "BLOCK")
        self.assertFalse(comparison["material_fields_equal"])
        self.assertIn("$.squash_merge_sha:VALUE", comparison["differences"])
        self.assertIn("$.unexpected:MISSING_PROPOSAL", comparison["differences"])

    def test_block_fixture_surfaces_all_material_failures(self) -> None:
        snapshot = load_closure_snapshot(BLOCK_PATH)
        result = evaluate_closure(snapshot, self.policy)
        self.assertEqual(result["status"], "BLOCK")
        self.assertFalse(result["eligible_for_manual_squash_merge"])
        blockers = set(result["blockers"])
        self.assertIn("CHANGED_PATH_NOT_ALLOWED:src/market/unauthorised.py", blockers)
        self.assertIn("REQUIRED_CHECK_NOT_PASS", blockers)
        self.assertIn("QA_STATUS_NOT_PASS", blockers)
        self.assertIn("RESERVED_AUTHORITY_DELTA", blockers)
        self.assertIn("BLOCKERS_PRESENT", blockers)
        self.assertIn("WARNINGS_PRESENT", blockers)
        self.assertIn("UNRESOLVED_REVIEWS_PRESENT", blockers)
        self.assertIn("DESTRUCTIVE_ROLLBACK", blockers)
        with self.assertRaises(ClosureError):
            propose_merge_receipt(snapshot, self.policy, MERGE_SHA)

    def test_policy_identity_and_safety_boundaries_fail_closed(self) -> None:
        raw = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        weakened = copy.deepcopy(raw)
        weakened["repository_bot_write"] = "ALLOWED"
        with self.assertRaises(ClosureError):
            parse_closure_policy(weakened)
        weakened = copy.deepcopy(raw)
        weakened["merge_method"] = "merge"
        with self.assertRaises(ClosureError):
            parse_closure_policy(weakened)
        weakened = copy.deepcopy(raw)
        weakened["zero_warning_required"] = False
        with self.assertRaises(ClosureError):
            parse_closure_policy(weakened)

    def test_snapshot_normalizes_order_and_rejects_invalid_shape(self) -> None:
        raw = json.loads(PASS_PATH.read_text(encoding="utf-8"))
        reverse = copy.deepcopy(raw)
        reverse["changed_files"] = list(reversed(reverse["changed_files"]))
        reverse["required_checks"] = list(reversed(reverse["required_checks"]))
        parsed = parse_closure_snapshot(reverse)
        self.assertEqual(parsed.snapshot_id, self.snapshot.snapshot_id)

        duplicate = copy.deepcopy(raw)
        duplicate["required_checks"].append(copy.deepcopy(duplicate["required_checks"][0]))
        with self.assertRaises(ClosureError):
            parse_closure_snapshot(duplicate)
        invalid = copy.deepcopy(raw)
        invalid["pull_request"] = 0
        with self.assertRaises(ClosureError):
            parse_closure_snapshot(invalid)

    def test_receipt_requires_distinct_valid_merge_sha(self) -> None:
        with self.assertRaises(ClosureError):
            propose_merge_receipt(self.snapshot, self.policy, "bad")
        with self.assertRaises(ClosureError):
            propose_merge_receipt(self.snapshot, self.policy, self.snapshot.head_sha)
        with self.assertRaises(ClosureError):
            compare_receipt_proposal({"schema": "wrong"}, self.manual)


if __name__ == "__main__":
    unittest.main()
