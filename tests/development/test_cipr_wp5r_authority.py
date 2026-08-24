from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
AUTHORITY = ROOT / "docs/releases/ci-performance-remediation-v0-1/cipr-wp5r/CIPR_WP5R_AUTHORITY_MANIFEST.json"
FRONTIER = ROOT / "docs/releases/ci-performance-remediation-v0-1/cipr-wp5r/CIPR_WP5R_DEPENDENCY_FRONTIER.json"
DECISION = ROOT / "docs/releases/ci-performance-remediation-v0-1/cipr-wp5/CIPR_G5_DECISION.json"
SHADOW_WORKFLOW = ROOT / ".github/workflows/ci-pytest-shard-shadow.yml"


def canonical_sha256(value: dict) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class CiprWp5rAuthorityTests(unittest.TestCase):
    def test_authority_manifest_identity_reproduces_and_is_shadow_only(self) -> None:
        record = json.loads(AUTHORITY.read_text(encoding="utf-8"))
        self.assertEqual(
            record["authority_manifest_id"],
            canonical_sha256(record["authority_manifest"]),
        )
        manifest = record["authority_manifest"]
        self.assertEqual(manifest["authority_class"], "OPERATOR_GRANTED_BOUNDED_SHADOW")
        self.assertIn("DETERMINISTIC_EXACT_UNION_SHARD_CANDIDATE_CONSTRUCTION", manifest["grants"])
        self.assertIn("NO_REQUIRED_CHECK_SUBSTITUTION_OR_REMOVAL", manifest["denies"])
        self.assertIn("NO_RULESET_OR_REQUIRED_CONTEXT_RETIREMENT", manifest["denies"])

    def test_dependency_frontier_identity_reproduces_and_late_binding_is_preserved(self) -> None:
        record = json.loads(FRONTIER.read_text(encoding="utf-8"))
        self.assertEqual(
            record["dependency_frontier_id"],
            canonical_sha256(record["dependency_frontier"]),
        )
        frontier = record["dependency_frontier"]
        self.assertEqual(
            frontier["physical_main_policy"],
            "LATE_PHYSICAL_PLACEMENT_MAIN_MOVEMENT_DOES_NOT_REWRITE_LOGICAL_PAYLOAD_IF_FRONTIER_UNCHANGED",
        )
        self.assertEqual(frontier["blockers"], [])

    def test_operator_defer_and_new_shadow_grant_are_exact(self) -> None:
        decision = json.loads(DECISION.read_text(encoding="utf-8"))
        self.assertEqual(decision["decision"], "DEFER")
        self.assertEqual(
            decision["operator_instruction"],
            "DEFER the obsolete shard and authorize construction + shadow qualification of the new post-PYT shard architecture",
        )
        self.assertEqual(decision["decision_effect"]["required_check_cutover"], "NOT_AUTHORISED")
        self.assertEqual(decision["decision_effect"]["post_pyt_shadow_qualification"], "AUTHORISED")

    def test_shadow_workflow_never_becomes_pull_request_required_surface(self) -> None:
        text = SHADOW_WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("pull_request:", text)
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("OVC_REQUIRED_CHECK_SUBSTITUTION=FALSE", text)


if __name__ == "__main__":
    unittest.main()
