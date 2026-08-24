from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools/ci/pytest_shard_shadow.py"
CI_DIR = MODULE_PATH.parent
if str(CI_DIR) not in sys.path:
    sys.path.insert(0, str(CI_DIR))
SPEC = importlib.util.spec_from_file_location("pytest_shard_shadow", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
shadow = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = shadow
SPEC.loader.exec_module(shadow)

POLICY_PATH = (
    ROOT
    / "registries/implementation/ci_performance/CIPR_POST_PYT_PYTEST_SHARD_POLICY_v0_1.json"
)
WORKFLOW_PATH = ROOT / ".github/workflows/ci-pytest-shard-shadow.yml"
TESTS_WORKFLOW = ROOT / ".github/workflows/tests.yml"
TIERED_WORKFLOW = ROOT / ".github/workflows/ovc-tiered-tests.yml"
DECISION_PATH = (
    ROOT
    / "docs/releases/ci-performance-remediation-v0-1/cipr-wp5/CIPR_G5_DECISION.json"
)
STATE_PATH = (
    ROOT
    / "registries/implementation/ci_performance/OVC_CIPR_STATE_v0_5_POST_PYT_SHADOW_RUNNING.json"
)


class PytestShardShadowTests(unittest.TestCase):
    def records(self):
        return [
            shadow.NodeRecord("tests/a.py::test_1", "tests/a.py", 0),
            shadow.NodeRecord("tests/heavy0.py::test_a", "tests/heavy0.py", 1),
            shadow.NodeRecord("tests/b.py::TestB::test_1", "tests/b.py", 2),
            shadow.NodeRecord("tests/heavy1.py::test_a", "tests/heavy1.py", 3),
            shadow.NodeRecord("tests/c.py::test_1[param]", "tests/c.py", 4),
            shadow.NodeRecord("tests/heavy2.py::test_a", "tests/heavy2.py", 5),
            shadow.NodeRecord("tests/d.py::TestD::test_1", "tests/d.py", 6),
            shadow.NodeRecord("tests/heavy3.py::test_a", "tests/heavy3.py", 7),
        ]

    def heavy(self):
        return {
            "tests/heavy0.py": 0,
            "tests/heavy1.py": 1,
            "tests/heavy2.py": 2,
            "tests/heavy3.py": 3,
        }

    def test_assignment_is_deterministic_exact_one_and_preserves_collection_order(self):
        first = shadow.assign_records(
            self.records(), shard_count=4, heavy_path_to_shard=self.heavy()
        )
        second = shadow.assign_records(
            self.records(), shard_count=4, heavy_path_to_shard=self.heavy()
        )
        self.assertEqual(first, second)
        flattened = [record.key for shard in first for record in shard]
        self.assertEqual(len(flattened), len(set(flattened)))
        self.assertEqual(set(flattened), {record.key for record in self.records()})
        for shard in first:
            ordinals = [record.ordinal for record in shard]
            self.assertEqual(ordinals, sorted(ordinals))

    def test_each_seed_heavy_path_is_isolated_to_declared_shard(self):
        shards = shadow.assign_records(
            self.records(), shard_count=4, heavy_path_to_shard=self.heavy()
        )
        for path, index in self.heavy().items():
            self.assertTrue(
                any(record.source_path == path for record in shards[index])
            )
            for other_index, shard in enumerate(shards):
                if other_index != index:
                    self.assertFalse(
                        any(record.source_path == path for record in shard)
                    )

    def test_missing_configured_heavy_path_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "configured heavy paths missing"):
            shadow.assign_records(
                self.records(),
                shard_count=4,
                heavy_path_to_shard={"tests/not-present.py": 0},
            )

    def test_duplicate_identity_fails_closed(self):
        records = self.records()
        records.append(
            shadow.NodeRecord(records[0].key, records[0].source_path, 99)
        )
        with self.assertRaisesRegex(RuntimeError, "duplicate canonical pytest"):
            shadow.assign_records(
                records,
                shard_count=4,
                heavy_path_to_shard=self.heavy(),
            )

    def test_collection_parser_keeps_pytest_nodeids_and_rejects_duplicates(self):
        text = "\n".join(
            [
                "tests/a.py::test_a",
                "tests/b.py::TestB::test_b[param]",
                "",
                "2 tests collected in 0.12s",
            ]
        )
        self.assertEqual(
            shadow._parse_collection_output(text),
            ["tests/a.py::test_a", "tests/b.py::TestB::test_b[param]"],
        )
        with self.assertRaisesRegex(RuntimeError, "duplicate node ids"):
            shadow._parse_collection_output(
                "tests/a.py::test_a\ntests/a.py::test_a\n"
            )

    def test_manifest_includes_pytest_native_population_and_exact_union(self):
        nodeids = [
            "tests/a.py::TestA::test_legacy",
            "tests/native.py::test_native[param]",
            "tests/heavy0.py::test_a",
            "tests/heavy1.py::test_a",
            "tests/heavy2.py::test_a",
            "tests/heavy3.py::test_a",
        ]
        policy = {
            "schema": "ovc-pytest-shard-policy/v1",
            "policy_id": "TEST",
            "policy_version": "0",
            "shard_count": 4,
            "assignment_algorithm": "TEST",
            "heavy_path_to_shard": self.heavy(),
            "authority_mode": "SHADOW_ONLY_NO_REQUIRED_CHECK_SUBSTITUTION",
            "canonical_command": "pytest tests",
            "canonical_collection_command": "pytest tests --collect-only -q",
            "require_pytest_native_items": True,
        }
        with mock.patch.object(
            shadow,
            "_legacy_keys",
            return_value={"tests/a.py::TestA::test_legacy"},
        ):
            first = shadow.build_manifest(
                nodeids,
                policy,
                head_sha="a" * 40,
                execution_sha="a" * 40,
            )
            second = shadow.build_manifest(
                nodeids,
                policy,
                head_sha="a" * 40,
                execution_sha="a" * 40,
            )
        self.assertEqual(shadow._canonical_bytes(first), shadow._canonical_bytes(second))
        self.assertEqual(first["population_count"], len(nodeids))
        self.assertEqual(first["pytest_native_item_count"], len(nodeids) - 1)
        shadow.prove_manifest(first, nodeids)

    def test_packet_preserves_shadow_only_authority_and_current_required_ci(self):
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        tests_workflow = TESTS_WORKFLOW.read_text(encoding="utf-8")
        tiered_workflow = TIERED_WORKFLOW.read_text(encoding="utf-8")
        decision = json.loads(DECISION_PATH.read_text(encoding="utf-8"))
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))

        self.assertEqual(
            policy["authority_mode"],
            "SHADOW_ONLY_NO_REQUIRED_CHECK_SUBSTITUTION",
        )
        self.assertFalse(policy["required_check_substitution_active"])
        self.assertFalse(policy["runner_cutover_active"])
        self.assertTrue(policy["require_pytest_native_items"])
        self.assertEqual(policy["shard_count"], 4)

        self.assertNotIn("pull_request:", workflow)
        self.assertIn("ci-performance-post-pyt-shard-shadow", workflow)
        self.assertIn("pytest_shard_shadow.py prove", workflow)
        self.assertIn("pytest_shard_shadow.py run", workflow)
        self.assertNotIn("xdist", workflow)

        self.assertIn(
            "PYTHONPATH=src:. python3 -m pytest tests -q --tb=short",
            tests_workflow,
        )
        self.assertIn("SIQ READY admission", tiered_workflow)
        self.assertIn("OVC merge readiness", tiered_workflow)

        self.assertEqual(decision["decision"], "DEFER")
        self.assertIn(
            "construct a bounded deterministic multi-shard candidate whose exact union equals the current canonical pytest item population",
            decision["authority_granted"],
        )
        self.assertIn(
            "activate any shard as a substitute for the canonical tests required check",
            decision["authority_not_granted"],
        )

        self.assertEqual(state["status"], "RUNNING")
        self.assertFalse(state["required_check_substitution_active"])
        self.assertFalse(state["runner_cutover_active"])
        self.assertFalse(state["scientific_authority_delta"])


if __name__ == "__main__":
    unittest.main()
