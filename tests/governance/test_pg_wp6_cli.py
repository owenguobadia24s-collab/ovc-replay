import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/governance/preview_pg_upkeep_candidates.py"
REGISTRY = ROOT / "registries/governance/programme_genesis/UPKEEP_CANDIDATE_EVENT_REGISTRY_v0_1.json"
TARGET_BRANCH = "upkeep/pg-candidate-events/cli-test"


def finding() -> dict:
    return {
        "programme_id": "OVC-PG-v0.2",
        "event_type": "HEALTH_FINDING_CANDIDATE",
        "source_kind": "PROGRAMME_HEALTH_FINDING",
        "source_finding_id": "cli-finding-001",
        "source_ref": {
            "path": "docs/releases/programme-genesis-v0-2/pg-g6/PG_G6_OPERATOR_DECISION.json",
            "sha256": "b" * 64,
        },
        "observed_at": "2026-08-03T20:00:00+00:00",
        "first_valid_at": "2026-08-03T20:00:00+00:00",
        "proposed_payload": {"finding_type": "HEALTH_REVIEW", "severity": "WARN"},
    }


def environment() -> dict[str, str]:
    value = os.environ.copy()
    value["PYTHONPATH"] = str(ROOT / "src")
    return value


class ProgrammeGenesisWP6CLITests(unittest.TestCase):
    def test_preview_cli_is_deterministic_and_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            finding_path = root / "finding.json"
            finding_path.write_text(json.dumps(finding()), encoding="utf-8")
            command = [
                sys.executable,
                str(SCRIPT),
                "--finding-file",
                str(finding_path),
                "--registry",
                str(REGISTRY),
                "--existing-programme-id",
                "OVC-PG-v0.2",
                "--target-branch",
                TARGET_BRANCH,
                "--repository-root",
                str(root),
            ]
            first = subprocess.run(command, cwd=ROOT, env=environment(), text=True, capture_output=True, check=False)
            second = subprocess.run(command, cwd=ROOT, env=environment(), text=True, capture_output=True, check=False)
            self.assertEqual(0, first.returncode, first.stderr)
            self.assertEqual(first.stdout, second.stdout)
            output = json.loads(first.stdout)
            self.assertEqual("PREVIEW_ONLY_DISABLED_PENDING_PG_G7", output["status"])
            self.assertEqual("NONE", output["authority_effect"])
            self.assertEqual(1, output["candidate_count"])
            self.assertEqual("CANDIDATE_UNAPPROVED", output["candidates"][0]["status"])
            self.assertEqual([finding_path], list(root.iterdir()))

    def test_persist_flag_fails_before_pg_g7_and_creates_no_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            finding_path = root / "finding.json"
            finding_path.write_text(json.dumps(finding()), encoding="utf-8")
            command = [
                sys.executable,
                str(SCRIPT),
                "--finding-file",
                str(finding_path),
                "--registry",
                str(REGISTRY),
                "--existing-programme-id",
                "OVC-PG-v0.2",
                "--target-branch",
                TARGET_BRANCH,
                "--repository-root",
                str(root),
                "--persist",
            ]
            result = subprocess.run(command, cwd=ROOT, env=environment(), text=True, capture_output=True, check=False)
            self.assertEqual(2, result.returncode)
            self.assertIn("disabled pending PG-G7", result.stderr)
            self.assertEqual([finding_path], list(root.iterdir()))


if __name__ == "__main__":
    unittest.main()
