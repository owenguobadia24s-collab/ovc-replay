from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASELINE = "fefac25f19a836898c3a22228036cd66617dca07"
PLAN_SHA256 = "4f0de710ab0157041f57ab781c9411a68aaf211b3b4a41f249978f07b0d580a0"
PLAN_SIZE = 193991


class ResearchOperationsG0PreflightTests(unittest.TestCase):
    def test_required_control_records_exist(self) -> None:
        required = (
            "docs/plans/research_operations/OVC_RESEARCH_OPERATIONS_FOUNDATION_IMPLEMENTATION_PLAN_v0_1.md",
            "docs/releases/research-operations-foundation/ro-g0/RO_G0_FOUNDATION_PREFLIGHT.md",
            "docs/releases/research-operations-foundation/ro-g0/RO_G0_GATE_PACKET.json",
            "registries/research_operations/RESEARCH_OPERATIONS_NAMESPACE_REGISTRY_v0_1.yaml",
            "registries/research_operations/RESEARCH_OPERATIONS_DEPENDENCY_POLICY_v0_1.yaml",
            "registries/research_operations/RESEARCH_OPERATIONS_PATH_POLICY_v0_1.yaml",
            "registries/implementation/RESEARCH_OPERATIONS_RO_G0_FOUNDATION.yaml",
        )
        for rel in required:
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_gate_packet_binds_exact_baseline_and_plan(self) -> None:
        packet = json.loads(
            (ROOT / "docs/releases/research-operations-foundation/ro-g0/RO_G0_GATE_PACKET.json").read_text(encoding="utf-8")
        )
        self.assertEqual(packet["gate_id"], "RO-G0")
        self.assertEqual(packet["result"], "PASS")
        self.assertEqual(packet["baseline"]["commit"], BASELINE)
        self.assertEqual(packet["baseline"]["open_pull_requests_at_preflight"], 0)
        self.assertEqual(packet["source_plan"]["sha256"], PLAN_SHA256)
        self.assertEqual(packet["source_plan"]["size_bytes"], PLAN_SIZE)
        self.assertEqual(len(packet["checks"]), 8)
        self.assertTrue(all(check["status"] == "PASS" for check in packet["checks"]))

    def test_namespace_is_reserved_without_implementation_leakage(self) -> None:
        namespace = (
            ROOT / "registries/research_operations/RESEARCH_OPERATIONS_NAMESPACE_REGISTRY_v0_1.yaml"
        ).read_text(encoding="utf-8")
        self.assertIn("path: src/ovc/research_operations", namespace)
        self.assertIn("import_name: ovc.research_operations", namespace)
        self.assertIn("state: RESERVED_NOT_IMPLEMENTED", namespace)
        self.assertIn("top_level_package_creation: DENIED", namespace)
        self.assertFalse((ROOT / "src/ovc/research_operations").exists())
        self.assertFalse((ROOT / "apps/research_console").exists())

    def test_dependency_policy_is_one_way_and_fail_closed(self) -> None:
        policy = (
            ROOT / "registries/research_operations/RESEARCH_OPERATIONS_DEPENDENCY_POLICY_v0_1.yaml"
        ).read_text(encoding="utf-8")
        for required in (
            "OPT_A_OPTIONAL_C1_C2_TO_RESEARCH_RECORDS_TO_QA_TO_READ_MODEL_TO_CONSOLE",
            "validation payload resolution",
            "DENIED_LOCKED_UNCONSUMED",
            "legacy/quarantine/** runtime imports",
            "direct R2 write, delete or publication",
            "direct main-branch writes, commits, pushes, merges or history rewrite",
            "reverse_rewrite: DENIED",
        ):
            self.assertIn(required, policy)

    def test_path_policy_separates_git_external_and_derived_storage(self) -> None:
        policy = (
            ROOT / "registries/research_operations/RESEARCH_OPERATIONS_PATH_POLICY_v0_1.yaml"
        ).read_text(encoding="utf-8")
        for required in (
            "environment_variable: OVC_EXTERNAL_ARTIFACT_ROOT",
            "path: var/research_operations",
            "git_state: IGNORED",
            "raw_ohlcv",
            "sqlite_databases",
            "absolute_operator_paths",
            "traversal: DENIED",
            "symlink_escape: DENIED",
            "payload_resolution: DENIED_LOCKED_UNCONSUMED",
        ):
            self.assertIn(required, policy)

    def test_active_authority_preserves_upstream_and_adds_no_market_power(self) -> None:
        authority = (ROOT / "registries/authority/ACTIVE_AUTHORITY.yaml").read_text(encoding="utf-8")
        self.assertIn("  opt_a: ACTIVE", authority)
        self.assertIn("  opt_b_c1: NONE", authority)
        self.assertIn("validation_consumption: LOCKED_UNCONSUMED", authority)
        self.assertIn("state: WP2_CONTRACTS_FROZEN_WP3_SYNTHETIC_ENGINE_AUTHORISED", authority)
        registry = (
            ROOT / "registries/implementation/RESEARCH_OPERATIONS_RO_G0_FOUNDATION.yaml"
        ).read_text(encoding="utf-8")
        self.assertIn("status: RO_G0_PASS_WP1_AUTHORISED", registry)
        for phrase in (
            "active_research: NONE",
            "market: NONE",
            "probability: NONE",
            "exposure: NONE",
            "execution: NONE",
            "agent: NONE",
        ):
            self.assertIn(phrase, registry)

    def test_ro_g0_does_not_add_runtime_or_ui_dependencies(self) -> None:
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertNotIn("streamlit", pyproject.lower())
        self.assertNotIn("sqlite", pyproject.lower())
        self.assertIn('include = ["ovc*", "ovc_evidence_store*"]', pyproject)

    def test_current_status_names_parallel_next_boundaries(self) -> None:
        status = (ROOT / "docs/CURRENT_STATUS.md").read_text(encoding="utf-8")
        self.assertIn("RO-G0", status)
        self.assertIn("RO-WP1 — Evidence envelope and record schemas", status)
        self.assertIn("OPT-B.C1 v2 WP3", status)
        self.assertIn("LOCKED_UNCONSUMED", status)


if __name__ == "__main__":
    unittest.main()
