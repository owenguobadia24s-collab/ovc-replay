from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from ovc.development.test_selection import (
    TestSelectionError,
    load_test_profile_registry,
    parse_test_profile_registry,
    select_test_manifest,
)


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "registries/development/OVC_DEVELOPMENT_ACCELERATION_TEST_PROFILE_REGISTRY_v0_1.json"
FIXTURES = ROOT / "fixtures/development/test_selection"


def read_paths(name: str) -> list[str]:
    return [line for line in (FIXTURES / name).read_text(encoding="utf-8").splitlines() if line]


class TestSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = load_test_profile_registry(REGISTRY_PATH)

    def test_fast_packet_and_final_head_profiles(self) -> None:
        fast = select_test_manifest(read_paths("fast_paths.txt"), self.registry)
        self.assertEqual(fast["status"], "PASS")
        self.assertEqual(fast["selected_profile"], "FAST")
        self.assertEqual(fast["unknown_paths"], [])

        packet = select_test_manifest(read_paths("packet_paths.txt"), self.registry)
        self.assertEqual(packet["status"], "PASS")
        self.assertEqual(packet["selected_profile"], "PACKET")
        self.assertIn("authority-boundary", packet["retained_checks"])

        final = select_test_manifest(read_paths("packet_paths.txt"), self.registry, stage="FINAL_HEAD")
        self.assertEqual(final["selected_profile"], "FINAL_HEAD")
        self.assertIn("PYTHONPATH=src python -m unittest discover -s tests -v", final["commands"])

    def test_unknown_path_escalates_and_never_skips(self) -> None:
        result = select_test_manifest(read_paths("unknown_paths.txt"), self.registry)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["selected_profile"], "FINAL_HEAD")
        self.assertEqual(result["unknown_paths"], ["src/unregistered/new_component.py"])
        self.assertIn("unknown-path-final-head-escalation", result["retained_checks"])

    def test_gate_replay_is_orthogonal_and_cannot_substitute(self) -> None:
        result = select_test_manifest(
            read_paths("packet_paths.txt"),
            self.registry,
            stage="GATE_REPLAY",
            gate_id="DA-G3",
            gate_command="PYTHONPATH=src python scripts/development/validate_da_g3.py",
        )
        self.assertEqual(result["selected_profile"], "GATE_REPLAY")
        self.assertEqual(result["commands"], ["PYTHONPATH=src python scripts/development/validate_da_g3.py"])
        self.assertTrue(result["final_assurance_required"])
        self.assertEqual(result["final_assurance_profile"], "FINAL_HEAD")
        self.assertEqual(result["gate_replay_substitution"], "PROHIBITED")
        self.assertFalse(result["local_success_substitutes_remote_required_check"])

    def test_manifest_is_order_independent_and_root_free(self) -> None:
        paths = read_paths("packet_paths.txt")
        first = select_test_manifest(paths, self.registry)
        second = select_test_manifest(list(reversed(paths)) + [paths[0]], self.registry)
        self.assertEqual(first, second)
        serialized = json.dumps(first, sort_keys=True)
        self.assertNotIn(str(ROOT), serialized)
        self.assertNotIn("created_at", serialized)
        self.assertEqual(len(first["selection_manifest_id"]), 64)

    def test_ambiguous_highest_priority_rules_block(self) -> None:
        raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        raw["rules"].extend([
            {
                "rule_id": "AMB-A",
                "pattern": "ambiguous/*",
                "priority": 999,
                "owner": "A",
                "minimum_profile": "FAST",
                "commands": ["command-a"],
                "retained_checks": ["check-a"]
            },
            {
                "rule_id": "AMB-B",
                "pattern": "ambiguous/**",
                "priority": 999,
                "owner": "B",
                "minimum_profile": "PACKET",
                "commands": ["command-b"],
                "retained_checks": ["check-b"]
            }
        ])
        registry = parse_test_profile_registry(raw)
        result = select_test_manifest(["ambiguous/value.txt"], registry)
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["ambiguous_paths"], ["ambiguous/value.txt"])
        self.assertEqual(result["blockers"], ["AMBIGUOUS_PATH:ambiguous/value.txt"])

    def test_registry_rejects_assurance_weakening_and_bad_requests(self) -> None:
        raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        weakened = copy.deepcopy(raw)
        weakened["final_assurance"]["complete_repository_suite"] = False
        with self.assertRaises(TestSelectionError):
            parse_test_profile_registry(weakened)
        with self.assertRaises(TestSelectionError):
            select_test_manifest([], self.registry)
        with self.assertRaises(TestSelectionError):
            select_test_manifest(["../unsafe"], self.registry)
        with self.assertRaises(TestSelectionError):
            select_test_manifest(["docs/x.md"], self.registry, stage="GATE_REPLAY")
        with self.assertRaises(TestSelectionError):
            select_test_manifest(["docs/x.md"], self.registry, gate_id="DA-G3")

    def test_workflow_changes_force_final_head(self) -> None:
        result = select_test_manifest([".github/workflows/ovc-tiered-tests.yml"], self.registry)
        self.assertEqual(result["selected_profile"], "FINAL_HEAD")
        self.assertIn("complete-repository-suite", result["retained_checks"])

    def test_cli_emits_compact_manifest_and_exit_codes(self) -> None:
        script = ROOT / "scripts/development/ovc_test_select.py"
        with tempfile.TemporaryDirectory() as raw:
            output = Path(raw) / "manifest.json"
            command = [
                sys.executable,
                str(script),
                "--registry", str(REGISTRY_PATH),
                "--changed-paths-file", str(FIXTURES / "packet_paths.txt"),
                "--output", str(output),
            ]
            completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            stdout = json.loads(completed.stdout)
            persisted = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(stdout, persisted)
            self.assertEqual(stdout["selected_profile"], "PACKET")

            blocked = subprocess.run(
                [sys.executable, str(script), "--registry", str(REGISTRY_PATH)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(blocked.returncode, 2)
            self.assertEqual(json.loads(blocked.stdout)["reason"], "TEST_SELECTION_REQUEST_INVALID")


if __name__ == "__main__":
    unittest.main()
