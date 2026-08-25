from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256
from scripts.governance.grt_v0_2.integration_floor import (
    EXPECTED_POLICY_LOGICAL_SHA256,
    FLOOR_POINTER_PATH,
    IntegrationFloorError,
    POLICY_ID,
    assert_no_packet_floor_mutation,
    build_floor,
    is_floor_control_path,
    validate_floor,
    validate_policy,
)

ROOT = Path(__file__).resolve().parents[3]
POLICY = ROOT / "registries/governance/grt_v0_2/GRT_DEBTFLOOR_INTEGRATION_OWNERSHIP_v0_1.json"
SCHEMA = ROOT / "schemas/governance/grt_v0_2/grt_debt_floor_integration_ownership.schema.json"
CONTRACT = ROOT / "contracts/governance/grt_v0_2/GRT_VIT_DEBTFLOOR_INTEGRATION_OWNERSHIP_CONTRACT_v0_1.md"
EXACT = ROOT / "scripts/governance/grt_v0_2/grt_exact_integration_floor.py"
PREPARE = ROOT / "scripts/governance/grt_v0_2/prepare_next_debt_floor.py"
FIXTURE = ROOT / "fixtures/governance/grt_v0_2/debtfloor_integration_ownership/two_concurrent_packets.json"


class DebtFloorIntegrationOwnershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_policy_identity_and_schema_are_exact(self):
        validate_policy(self.policy)
        self.assertEqual(self.policy["policy_id"], POLICY_ID)
        self.assertEqual(self.policy["logical_sha256"], EXPECTED_POLICY_LOGICAL_SHA256)
        payload = dict(self.policy)
        observed = payload.pop("logical_sha256")
        self.assertEqual(canonical_sha256(payload), observed)
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["policy_id"]["const"], POLICY_ID)
        self.assertIn(str(SCHEMA.relative_to(ROOT)), POLICY.read_text(encoding="utf-8"))
        self.assertIn(str(POLICY.relative_to(ROOT)), CONTRACT.read_text(encoding="utf-8"))

    def test_floor_is_deterministic_and_commit_metadata_independent(self):
        floor = build_floor(
            policy=self.policy,
            generation=3,
            predecessor_commit="1" * 40,
            predecessor_tree="2" * 40,
            result_tree="3" * 40,
            open_grandfathered_findings=self.fixture["findings"],
        )
        again = build_floor(
            policy=self.policy,
            generation=3,
            predecessor_commit="1" * 40,
            predecessor_tree="2" * 40,
            result_tree="3" * 40,
            open_grandfathered_findings=reversed(self.fixture["findings"]),
        )
        self.assertEqual(floor, again)
        self.assertNotIn("head_commit", floor)
        self.assertNotIn("source_branch", floor)
        self.assertNotIn("commit_message", floor)
        validate_floor(floor, policy=self.policy)

    def test_ordinary_packet_floor_paths_are_forbidden(self):
        self.assertTrue(is_floor_control_path(FLOOR_POINTER_PATH))
        self.assertTrue(
            is_floor_control_path(
                "registries/governance/grt_v0_2/debt_floors/GRT_DEBT_FLOOR_G99.json"
            )
        )
        self.assertFalse(is_floor_control_path("docs/programmes/example/packet.json"))
        with self.assertRaisesRegex(IntegrationFloorError, "PACKET_MUTATION_FORBIDDEN"):
            assert_no_packet_floor_mutation([FLOOR_POINTER_PATH])
        assert_no_packet_floor_mutation(["docs/programmes/example/packet.json"])

    def test_two_concurrent_packets_keep_packet_b_pip_stable(self):
        f = self.fixture
        a_floor = build_floor(
            policy=self.policy,
            generation=f["expected"]["packet_a_floor_generation"],
            predecessor_commit=f["base"]["commit"],
            predecessor_tree=f["base"]["tree"],
            result_tree=f["packet_a"]["result_tree"],
            open_grandfathered_findings=f["findings"],
        )
        b_before = build_floor(
            policy=self.policy,
            generation=3,
            predecessor_commit=f["base"]["commit"],
            predecessor_tree=f["base"]["tree"],
            result_tree=f["packet_b"]["result_tree_before_a"],
            open_grandfathered_findings=f["findings"],
        )
        b_pip = f["packet_b"]["pip_id"]
        b_after = build_floor(
            policy=self.policy,
            generation=f["expected"]["packet_b_floor_generation_after_a"],
            predecessor_commit=f["packet_a"]["physical_commit"],
            predecessor_tree=f["packet_a"]["result_tree"],
            result_tree=f["packet_b"]["result_tree_after_a"],
            open_grandfathered_findings=f["findings"],
        )
        self.assertEqual(b_pip, f["packet_b"]["pip_id"])
        self.assertNotEqual(b_before["floor_hash"], b_after["floor_hash"])
        self.assertNotEqual(a_floor["floor_hash"], b_after["floor_hash"])
        self.assertTrue(f["packet_b"]["source_payload_unchanged"])
        self.assertFalse(f["expected"]["packet_b_pip_rebuilt"])
        self.assertFalse(f["expected"]["packet_b_floor_registry_files_in_pip"])

    def test_active_scripts_enforce_virtual_projection_and_no_write_preparation(self):
        exact = EXACT.read_text(encoding="utf-8")
        prepare = PREPARE.read_text(encoding="utf-8")
        self.assertIn('"VIRTUAL_EXACT_TREE_PROJECTION"', exact)
        self.assertIn('"candidate_floor"', exact)
        self.assertIn('"candidate_floor_hash"', exact)
        self.assertIn("floor_state_loader=legacy._floor_state", exact)
        self.assertIn("_reconstruct_physical_floor", exact)
        self.assertIn("VIRTUAL_HISTORY_NEW_OR_RECURRENT", exact)
        self.assertIn('"physical_floor_history_replay_count"', exact)
        self.assertIn("assert_no_packet_floor_mutation(changed_paths.stdout.splitlines())", exact)
        self.assertIn("_exact_g4_transition", exact)
        self.assertIn("from scripts.governance.grt_v0_2 import grt_exact as legacy", exact)
        self.assertIn('"status": "NO_PACKET_MUTATION_REQUIRED"', prepare)
        self.assertIn('"packet_tree_mutation": False', prepare)
        self.assertIn("late_binding_final_projection_required", prepare)
        self.assertIn("validate_policy(policy)", prepare)

    def test_policy_change_without_pinned_code_identity_fails(self):
        changed = json.loads(json.dumps(self.policy))
        changed["status"] = "INACTIVE"
        payload = dict(changed)
        payload.pop("logical_sha256")
        changed["logical_sha256"] = canonical_sha256(payload)
        with self.assertRaisesRegex(IntegrationFloorError, "IDENTITY_NOT_PINNED"):
            validate_policy(changed)


if __name__ == "__main__":
    unittest.main()
