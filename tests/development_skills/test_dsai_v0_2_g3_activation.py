import json
import unittest
from pathlib import Path

from ovc.development.skills.orch345 import build_packet_descriptor, resolve_orch345_authority
from ovc.development.skills.orch345_active import (
    authorize_parallel_build_pair,
    build_authorized_packet_train,
    build_authorized_portfolio_schedule,
)


ROOT = Path(__file__).resolve().parents[2]
AUTHORITY_PATH = ROOT / "registries/development/skills/orch345_bounded_authority_v0_1.json"
DECISION_PATH = ROOT / "docs/releases/development-skills-architecture-v0-2/dsai2-g3/DSAI2_G3_OPERATOR_PASS.json"


class TestDSAI2G3Activation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.authority = json.loads(AUTHORITY_PATH.read_text(encoding="utf-8"))
        cls.decision = json.loads(DECISION_PATH.read_text(encoding="utf-8"))

    def test_operator_pass_and_exact_bounded_authority(self):
        self.assertEqual(self.decision["decision"], "PASS")
        self.assertEqual(self.decision["operator_instruction"], "OVC APPROVE DSAI2-G3 PASS")
        self.assertEqual(self.authority["enabled_orchestrators"], ["ORCH-3", "ORCH-4", "ORCH-5"])
        self.assertEqual(self.authority["enabled_packet_classes"], ["LOW_RISK_IMPLEMENTATION"])
        self.assertFalse(self.authority["integration_policy"]["parallel_merge"])
        self.assertFalse(self.authority["integration_policy"]["force_push"])
        self.assertFalse(self.authority["integration_policy"]["history_rewrite"])
        self.assertEqual(self.authority["validation"], "DENIED")
        self.assertEqual(self.authority["reserved_scientific_execution_authority"], "NONE")

    def test_authority_resolver_requires_main_presence(self):
        active = resolve_orch345_authority(authority=self.authority, record_present_on_main=True)
        self.assertEqual(active["status"], "ACTIVE_AUTHORIZED")
        blocked = resolve_orch345_authority(authority=self.authority, record_present_on_main=False)
        self.assertEqual(blocked["status"], "BLOCK")
        self.assertIn("AUTHORITY_RECORD_NOT_PRESENT_ON_MAIN", blocked["reason_codes"])

    def test_active_wrappers_fail_closed_without_authority(self):
        packet = build_packet_descriptor(programme_id="P", packet_id="P-WP1", write_paths=["a"])
        with self.assertRaises(PermissionError):
            build_authorized_packet_train(
                authority_resolution={"status": "BLOCK", "record_present_on_main": False},
                programme_id="P",
                packets=[packet],
            )

    def test_orch3_authorized_train_remains_serial_integration(self):
        active = resolve_orch345_authority(authority=self.authority, record_present_on_main=True)
        p1 = build_packet_descriptor(programme_id="P", packet_id="P-WP1", write_paths=["a"], priority=1)
        p2 = build_packet_descriptor(programme_id="P", packet_id="P-WP2", prerequisites=["P-WP1"], write_paths=["b"], priority=2)
        result = build_authorized_packet_train(authority_resolution=active, programme_id="P", packets=[p1, p2])
        self.assertEqual(result["selected_packet_ids"], ["P-WP1", "P-WP2"])
        self.assertEqual(result["execution_mode"], "ACTIVE_BOUNDED")
        self.assertFalse(result["parallel_merge"])

    def test_orch4_parallel_build_never_grants_parallel_merge(self):
        active = resolve_orch345_authority(authority=self.authority, record_present_on_main=True)
        left = build_packet_descriptor(programme_id="A", packet_id="A-WP1", write_paths=["src/a"], semantic_owners=["A"])
        right = build_packet_descriptor(programme_id="B", packet_id="B-WP1", write_paths=["src/b"], semantic_owners=["B"])
        allowed = authorize_parallel_build_pair(authority_resolution=active, left=left, right=right)
        self.assertEqual(allowed["admission"], "PARALLEL_BUILD_ADMITTED_SERIAL_INTEGRATION_ONLY")
        self.assertFalse(allowed["parallel_merge"])

        conflicting = build_packet_descriptor(programme_id="B", packet_id="B-WP2", write_paths=["src/a/file.py"], semantic_owners=["B"])
        denied = authorize_parallel_build_pair(authority_resolution=active, left=left, right=conflicting)
        self.assertEqual(denied["admission"], "SERIAL_REQUIRED")
        self.assertIn("WRITE_SET_OVERLAP", denied["reason_codes"])

    def test_orch5_dispatch_preserves_operator_wait_and_dependency_block(self):
        active = resolve_orch345_authority(authority=self.authority, record_present_on_main=True)
        ready = build_packet_descriptor(programme_id="A", packet_id="A-WP1", write_paths=["a"], priority=1)
        blocked = build_packet_descriptor(programme_id="B", packet_id="B-WP1", cross_programme_dependencies=["A-DONE"], write_paths=["b"], priority=2)
        operator = build_packet_descriptor(programme_id="C", packet_id="C-G1", gate_class="OPERATOR_REQUIRED", write_paths=["c"], priority=3)
        result = build_authorized_portfolio_schedule(
            authority_resolution=active,
            packets=[ready, blocked, operator],
            completed_packet_ids=[],
            max_parallel=2,
        )
        self.assertEqual(result["selected_packet_ids"], ["A-WP1"])
        self.assertEqual(result["operator_wait"], ["C-G1"])
        self.assertEqual(result["blocked"][0]["packet_id"], "B-WP1")
        self.assertFalse(result["parallel_merge"])


if __name__ == "__main__":
    unittest.main()
