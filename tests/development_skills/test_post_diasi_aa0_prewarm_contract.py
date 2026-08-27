from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from ovc.development.skills.vit_routing import build_vit_payload_lineage_record
from tools.ci.aa0_harness_identity import compute_harness_identity


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / ".github/workflows/tests.yml"
PACKET_DIR = ROOT / "docs/releases/development-skills-architecture-v0-3-vit/post-diasi-aa0-prewarm"


class PostDiasiAa0PrewarmContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    def _job(self, name: str, next_name: str | None = None) -> str:
        section = self.workflow.split(f"\n  {name}:\n", 1)[1]
        if next_name is not None:
            section = section.split(f"\n  {next_name}:\n", 1)[0]
        return section

    def test_workflow_dispatch_exposes_one_exact_optional_target(self) -> None:
        dispatch = self.workflow.split("  workflow_dispatch:\n", 1)[1].split("\npermissions:\n", 1)[0]
        self.assertEqual(dispatch.count("aa0_target_head_sha:"), 1)
        self.assertIn("required: false", dispatch)
        self.assertIn("OVC_AA0_PREWARM_TARGET_HEAD_SHA:", self.workflow)
        self.assertIn("OVC_ASSURANCE_TARGET_HEAD_SHA:", self.workflow)

    def test_every_assurance_checkout_uses_the_canonical_target(self) -> None:
        self.assertNotIn("github.event.pull_request.head.sha || github.sha", self.workflow)
        self.assertEqual(
            self.workflow.count("ref: ${{ env.OVC_ASSURANCE_TARGET_HEAD_SHA }}"),
            7,
        )

    def test_only_lineage_preflight_retains_full_history(self) -> None:
        self.assertEqual(self.workflow.count("fetch-depth: 0"), 1)
        self.assertEqual(self.workflow.count("fetch-depth: 1"), 6)

    def test_depth_one_aa0_scripts_have_no_ancestry_dependency(self) -> None:
        sources = {
            path: (ROOT / path).read_text(encoding="utf-8")
            for path in (
                "tools/ci/aa0_harness_identity.py",
                "tools/ci/pytest_shard_shadow.py",
                "tools/ci/pytest_shard_canonical.py",
                "tools/ci/pytest_unittest_parity.py",
            )
        }
        history_operations = (
            "merge-base",
            "rev-list",
            '"log"',
            '"diff"',
            '"show"',
            "--deepen",
            "--unshallow",
        )
        for path, source in sources.items():
            for operation in history_operations:
                self.assertNotIn(operation, source, f"{path} requires history via {operation}")
        self.assertIn('["git", "rev-parse", "HEAD"]', sources["tools/ci/pytest_shard_shadow.py"])
        self.assertIn('["ls-files", "-z", "--", pathspec]', sources["tools/ci/aa0_harness_identity.py"])

    def test_exact_cache_keys_bind_pip_harness_and_qualification_generation(self) -> None:
        for prefix in ("ovc-aa0-tests-v2", "ovc-aa0-unittest-v2", "ovc-aa0-runner-v2"):
            key = (
                prefix
                + "-pip-${{ needs.vit-routing-preflight.outputs.aa0_identity }}"
                + "-h-${{ steps.aa0-harness.outputs.harness_hash }}"
                + "-gen-${{ needs.vit-routing-preflight.outputs.generation_id }}"
            )
            self.assertGreaterEqual(self.workflow.count(key), 2)

    def test_exact_hits_reuse_and_misses_execute_for_all_aa0_surfaces(self) -> None:
        self.assertEqual(
            self.workflow.count('if [[ "${PRODUCER_MODE}" != "true" && "${EXACT_HIT}" == "true" ]]; then disposition=EXACT_GENERATION_REUSE'),
            3,
        )
        self.assertEqual(self.workflow.count("disposition=RUN_AA0"), 3)
        self.assertEqual(
            self.workflow.count("PRODUCER_MODE: ${{ needs.vit-routing-preflight.outputs.aa0_producer_mode }}"),
            3,
        )

    def test_canonical_shards_skip_only_when_assurance_is_reused(self) -> None:
        condition = "needs.pytest-assurance-plan.outputs.disposition == 'RUN_AA0'"
        self.assertGreaterEqual(self.workflow.count(condition), 5)
        self.assertIn(condition, self._job("pytest-shard-manifest", "pytest-shard"))
        self.assertIn(condition, self._job("pytest-shard", "pytest-unified"))

    def test_parity_execution_skips_only_on_lawful_reuse(self) -> None:
        for job_name in ("pytest-unittest-parity", "runner-parity"):
            next_job = "runner-parity" if job_name == "pytest-unittest-parity" else None
            job = self._job(job_name, next_job)
            self.assertEqual(job.count("if: steps.aa0.outputs.disposition == 'RUN_AA0'"), 3)
            self.assertEqual(job.count("Execute exact legacy unittest surface") + job.count("Prove pytest collection parity"), 1)

    def test_prewarm_does_not_consume_rac_or_mutate_protection(self) -> None:
        self.assertNotIn("REPOSITORY_ASSURANCE_PILOT_POLICY", self.workflow)
        self.assertNotIn("rac_pilot_assurance", self.workflow)
        protection = self._job("vit-routing-preflight", "pytest-assurance-plan")
        self.assertIn("name: Verify VIT-owned physical-main protection\n        if: github.event_name == 'pull_request'", protection)
        self.assertIn("OVC merge readiness", protection)
        self.assertIn("bypass.length !== 0", protection)

    def test_authority_or_frontier_change_changes_pip_and_cache_identity(self) -> None:
        def lineage(authority: str, frontier: str):
            return build_vit_payload_lineage_record(
                programme_id="PROGRAMME",
                packet_id="PACKET",
                pip_identity_payload={
                    "programme_id": "PROGRAMME",
                    "packet_id": "PACKET",
                    "authority_manifest_id": authority,
                    "dependency_frontier_id": frontier,
                    "logical_changes": [
                        {"op": "ADD", "path": "file.txt", "mode": "100644", "blob_sha": "1" * 40}
                    ],
                },
            )

        baseline = lineage("a" * 64, "b" * 64)["pip_id"]
        self.assertNotEqual(baseline, lineage("c" * 64, "b" * 64)["pip_id"])
        self.assertNotEqual(baseline, lineage("a" * 64, "d" * 64)["pip_id"])

    def test_owner_local_authority_and_frontier_are_content_addressed_and_bound(self) -> None:
        packet = json.loads((PACKET_DIR / "DSAI3V_AA0_PREWARM_MAINTENANCE_PACKET_v0_1.json").read_text())
        names = {
            "authority_manifest_id": "DSAI3V_AA0_PREWARM_AUTHORITY_MANIFEST_v0_1.json",
            "dependency_frontier_id": "DSAI3V_AA0_PREWARM_DEPENDENCY_FRONTIER_v0_1.json",
        }
        for packet_key, name in names.items():
            record = json.loads((PACKET_DIR / name).read_text())
            payload = {key: value for key, value in record.items() if key != "logical_id"}
            observed = hashlib.sha256(
                json.dumps(
                    payload,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                    allow_nan=False,
                ).encode("utf-8")
            ).hexdigest()
            self.assertEqual(record["logical_id"], observed)
            self.assertEqual(packet[packet_key], observed)
        self.assertEqual(packet["authority_delta"], "NONE")
        self.assertEqual(packet["programme_state"], "COMPLETED_NOT_REOPENED")

    def test_harness_change_invalidates_cache_identity(self) -> None:
        baseline = compute_harness_identity(ROOT)
        original = WORKFLOW_PATH.read_bytes()
        try:
            WORKFLOW_PATH.write_bytes(original + b"\n# identity-only mutation\n")
            self.assertNotEqual(baseline, compute_harness_identity(ROOT))
        finally:
            WORKFLOW_PATH.write_bytes(original)


if __name__ == "__main__":
    unittest.main()
