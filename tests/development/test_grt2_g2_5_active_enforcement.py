from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class GRT2G25ActiveEnforcementTests(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_current_authority_is_operator_rolled_back_limited_enforcement(self) -> None:
        authority = json.loads(
            (ROOT / "registries/authority/GRT2_ACTIVE_ENFORCEMENT_AUTHORITY_v0_3.json").read_text(encoding="utf-8")
        )
        self.assertEqual(authority["gate_id"], "GRT2-G3")
        self.assertEqual(authority["authority_status"], "ACTIVE_ON_MAIN_MATERIALISATION")
        self.assertEqual(authority["enforcement_mode"], "LIMITED_NEW_ARTIFACT_ENFORCEMENT")
        self.assertEqual(authority["g3_status"], "ROLLED_BACK_TO_G2_5_LIMITED_ENFORCEMENT")
        self.assertFalse(authority["full_grt_exact_required"])
        self.assertFalse(authority["ordinary_packet_debt_floor_generation_required"])

    def test_historical_g2_5_candidate_population_still_replays_under_limited_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "reconciliation.json"
            cp = self._run(
                "python",
                "scripts/governance/grt_v0_2/reconcile_g2_5_pilot.py",
                "--manifest",
                "docs/programmes/grt-v0-2/gates/GRT2_G2_5_RETROSPECTIVE_CANDIDATE_MANIFEST.json",
                "--out",
                str(output),
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stdout + cp.stderr)
            result = json.loads(output.read_text(encoding="utf-8"))
            summary = result["summary"]
            self.assertGreaterEqual(summary["eligible_candidate_count"], 8)
            self.assertGreaterEqual(summary["real_candidate_count"], 4)
            self.assertTrue(summary["candidate_threshold_met"])
            self.assertTrue(summary["elapsed_threshold_met"])
            self.assertTrue(summary["threshold_met"])
            self.assertEqual(summary["blocking_false_positive_count"], 0)
            self.assertEqual(summary["unresolved_false_negative_count"], 0)
            self.assertEqual(summary["scope_leakage_count"], 0)
            self.assertEqual(result["g3_status"], "ROLLED_BACK_TO_G2_5_LIMITED_ENFORCEMENT")

    def test_pull_request_candidate_is_enforced_inside_existing_required_listener(self) -> None:
        if os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
            self.skipTest("PR exact candidate enforcement is CI-only")
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        self.assertTrue(event_path, "GITHUB_EVENT_PATH_REQUIRED")
        event = json.loads(Path(event_path).read_text(encoding="utf-8"))
        pull = event.get("pull_request") or {}
        base = ((pull.get("base") or {}).get("sha"))
        head = ((pull.get("head") or {}).get("sha"))
        self.assertTrue(base and head, "PULL_REQUEST_BASE_HEAD_REQUIRED")
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "candidate.json"
            cp = self._run(
                "python",
                "scripts/governance/grt_v0_2/reconcile_g2_5_pilot.py",
                "--candidate",
                "--base",
                base,
                "--head",
                head,
                "--out",
                str(output),
            )
            self.assertEqual(cp.returncode, 0, msg=cp.stdout + cp.stderr)
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["enforcement_result"], "PASS")
            self.assertEqual(result["g3_status"], "ROLLED_BACK_TO_G2_5_LIMITED_ENFORCEMENT")


if __name__ == "__main__":
    unittest.main()
