from __future__ import annotations

import copy
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.ci.aa0_integration_latency_report import (
    LatencyReportError,
    canonical_json,
    compile_latency_report,
)


ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools/ci/aa0_integration_latency_report.py"
PACKET_DIR = ROOT / "docs/releases/development-skills-architecture-v0-3-vit/post-diasi-aa0-prewarm-observability"
HEAD = "a" * 40
PIP = "b" * 64
QUALIFICATION = "c" * 64
GENERATION = "d" * 64
HARNESS = "e" * 64
TREE = "f" * 40


def identity(**changes: str) -> dict[str, str]:
    row = {
        "candidate_head_sha": HEAD,
        "qualified_prospective_tree": TREE,
        "pip_id": PIP,
        "qualification_id": QUALIFICATION,
        "qualification_generation_id": GENERATION,
        "aa0_harness_id": HARNESS,
    }
    row.update(changes)
    return row


def evidence(*, merged_at: str = "2026-08-27T12:00:55Z") -> dict:
    return {
        "schema": "ovc-aa0-integration-latency-evidence/v1",
        "packet_id": "DSAI3V-AA0-PREWARM-OBSERVABILITY-MAINT-v0.1",
        "identity": identity(),
        "prewarm": {
            "identity": identity(),
            "workflow": {
                "id": 100,
                "name": "tests",
                "event": "workflow_dispatch",
                "target_head_sha": HEAD,
                "status": "completed",
                "conclusion": "success",
                "started_at": "2026-08-27T10:00:00+01:00",
                "completed_at": "2026-08-27T09:04:00Z",
            },
            "surfaces": {
                name: {
                    "disposition": "RUN_AA0",
                    "canonical_reference_executed": True,
                    "observed_at": "2026-08-27T09:03:59Z",
                }
                for name in ("repository", "unittest_parity", "runner_parity")
            },
        },
        "pr": {
            "metadata": {"number": 1400, "opened_at": "2026-08-27T12:00:00Z", "head_sha": HEAD},
            "current_head_sha": HEAD,
            "identity": identity(),
            "assurance_workflow": {
                "id": 200,
                "name": "tests",
                "event": "pull_request",
                "head_sha": HEAD,
                "status": "completed",
                "conclusion": "success",
                "started_at": "2026-08-27T12:00:01Z",
                "completed_at": "2026-08-27T12:00:30Z",
            },
            "surfaces": {
                "repository": {
                    "disposition": "EXACT_GENERATION_REUSE",
                    "canonical_reference_executed": False,
                    "observed_at": "2026-08-27T12:00:25Z",
                },
                "unittest_parity": {
                    "disposition": "EXACT_GENERATION_REUSE",
                    "canonical_reference_executed": False,
                    "observed_at": "2026-08-27T12:00:15Z",
                },
                "runner_parity": {
                    "disposition": "EXACT_GENERATION_REUSE",
                    "canonical_reference_executed": False,
                    "observed_at": "2026-08-27T12:00:14Z",
                },
            },
            "canonical_shard_jobs": {
                "manifest": "SKIPPED",
                "shard_0": "SKIPPED",
                "shard_1": "SKIPPED",
                "shard_2": "SKIPPED",
                "shard_3": "SKIPPED",
            },
        },
        "fresh_assurance": {
            "jobs": [
                {
                    "name": "VIT routing preflight",
                    "run_id": 200,
                    "job_id": 201,
                    "head_sha": HEAD,
                    "started_at": "2026-08-27T12:00:01Z",
                    "completed_at": "2026-08-27T12:00:09Z",
                    "conclusion": "success",
                },
                {
                    "name": "OVC profile assurance",
                    "run_id": 300,
                    "job_id": 301,
                    "head_sha": HEAD,
                    "started_at": "2026-08-27T12:00:01Z",
                    "completed_at": "2026-08-27T12:00:20Z",
                    "conclusion": "success",
                },
                {
                    "name": "SIQ READY admission",
                    "run_id": 300,
                    "job_id": 302,
                    "head_sha": HEAD,
                    "started_at": "2026-08-27T12:00:22Z",
                    "completed_at": "2026-08-27T12:00:40Z",
                    "conclusion": "success",
                },
                {
                    "name": "OVC merge readiness",
                    "run_id": 300,
                    "job_id": 303,
                    "head_sha": HEAD,
                    "started_at": "2026-08-27T12:00:41Z",
                    "completed_at": "2026-08-27T12:00:50Z",
                    "conclusion": "success",
                },
            ]
        },
        "materialisation": {
            "merged_at": merged_at,
            "merge_commit": "1" * 40,
            "prospective_tree": TREE,
            "physical_tree": TREE,
        },
        "completion": {
            "receipts": {
                "physical_materialisation_receipt": "2" * 64,
                "packet_completion_receipt": "3" * 64,
                "devobs_receipt": "4" * 64,
                "completion_proof": "5" * 64,
            },
            "timestamp": {"value": "2026-08-27T12:01:10Z", "source": "EXACT_LOG"},
        },
        "controls": {
            "repository_protection_active": True,
            "ruleset_id": 20229411,
            "bypass_actor_count": 0,
            "physical_writer_count": 1,
            "racpr_mode": "FALLBACK_CANONICAL_REFERENCE",
            "assurance_meaning_unchanged": True,
            "new_service_store_or_control_plane": False,
            "diasi_runtime_use_count": 0,
            "pes_runtime_use_count": 0,
            "cers_runtime_use_count": 0,
        },
    }


class Aa0IntegrationLatencyReportTests(unittest.TestCase):
    def test_exact_pr_head_binding(self) -> None:
        self.assertEqual(compile_latency_report(evidence())["pr"]["head_sha"], HEAD)

    def test_exact_prewarm_head_binding(self) -> None:
        row = evidence()
        row["prewarm"]["workflow"]["target_head_sha"] = "9" * 40
        with self.assertRaisesRegex(LatencyReportError, "HEAD_MISMATCH"):
            compile_latency_report(row)

    def test_pip_mismatch_fails_closed(self) -> None:
        row = evidence()
        row["pr"]["identity"]["pip_id"] = "9" * 64
        with self.assertRaisesRegex(LatencyReportError, "pip_id:IDENTITY_MISMATCH"):
            compile_latency_report(row)

    def test_qualification_mismatch_fails_closed(self) -> None:
        row = evidence()
        row["prewarm"]["identity"]["qualification_id"] = "9" * 64
        with self.assertRaisesRegex(LatencyReportError, "qualification_id:IDENTITY_MISMATCH"):
            compile_latency_report(row)

    def test_harness_mismatch_fails_closed(self) -> None:
        row = evidence()
        row["pr"]["identity"]["aa0_harness_id"] = "9" * 64
        with self.assertRaisesRegex(LatencyReportError, "aa0_harness_id:IDENTITY_MISMATCH"):
            compile_latency_report(row)

    def test_wrong_workflow_run_rejected(self) -> None:
        row = evidence()
        row["prewarm"]["workflow"]["event"] = "push"
        with self.assertRaisesRegex(LatencyReportError, "WRONG_WORKFLOW_RUN"):
            compile_latency_report(row)

    def test_stale_pr_head_rejected(self) -> None:
        row = evidence()
        row["pr"]["current_head_sha"] = "9" * 40
        with self.assertRaisesRegex(LatencyReportError, "STALE_OR_MISMATCHED_HEAD"):
            compile_latency_report(row)

    def test_duplicate_required_job_ambiguity_rejected(self) -> None:
        row = evidence()
        row["fresh_assurance"]["jobs"].append(copy.deepcopy(row["fresh_assurance"]["jobs"][0]))
        with self.assertRaisesRegex(LatencyReportError, "REQUIRED_JOB_AMBIGUOUS:2"):
            compile_latency_report(row)

    def test_missing_optional_completion_timestamp_is_null_with_warning(self) -> None:
        row = evidence()
        del row["completion"]["timestamp"]
        report = compile_latency_report(row)
        self.assertIsNone(report["completion"]["completion_timestamp_if_available"])
        self.assertEqual(report["warnings"][0]["code"], "COMPLETION_TIMESTAMP_UNAVAILABLE")

    def test_exact_utc_normalization(self) -> None:
        report = compile_latency_report(evidence())
        self.assertEqual(report["prewarm"]["started_at"], "2026-08-27T09:00:00.000000Z")

    def test_deterministic_canonical_output(self) -> None:
        first = canonical_json(compile_latency_report(evidence()))
        second = canonical_json(compile_latency_report(copy.deepcopy(evidence())))
        self.assertEqual(first, second)
        self.assertEqual(first, json.dumps(json.loads(first), sort_keys=True, separators=(",", ":")))

    def test_exact_prospective_physical_tree_mismatch_fails(self) -> None:
        row = evidence()
        row["materialisation"]["physical_tree"] = "8" * 40
        with self.assertRaisesRegex(LatencyReportError, "PROSPECTIVE_PHYSICAL_TREE_MISMATCH"):
            compile_latency_report(row)

    def test_qualified_prospective_tree_mismatch_fails(self) -> None:
        row = evidence()
        row["identity"]["qualified_prospective_tree"] = "7" * 40
        row["prewarm"]["identity"]["qualified_prospective_tree"] = "7" * 40
        row["pr"]["identity"]["qualified_prospective_tree"] = "7" * 40
        with self.assertRaisesRegex(LatencyReportError, "QUALIFIED_PROSPECTIVE_TREE_MISMATCH"):
            compile_latency_report(row)

    def test_successful_sub60_classification(self) -> None:
        self.assertEqual(
            compile_latency_report(evidence())["classification"],
            "POST_DIASI_AA0_PREWARM_PASS_SUB60",
        )

    def test_functional_pass_performance_miss_classification(self) -> None:
        report = compile_latency_report(evidence(merged_at="2026-08-27T12:01:00.000001Z"))
        self.assertEqual(report["classification"], "AA0_PREWARM_FUNCTIONAL_PASS_PERFORMANCE_MISS")

    def test_cache_reuse_failure_classification(self) -> None:
        row = evidence()
        surface = row["pr"]["surfaces"]["repository"]
        surface["disposition"] = "RUN_AA0"
        surface["canonical_reference_executed"] = True
        surface["failure_reason"] = "CACHE_SCOPE_MISS"
        self.assertEqual(
            compile_latency_report(row)["classification"], "AA0_PREWARM_CACHE_SCOPE_MISS"
        )

    def test_canonical_shard_execution_blocks_success(self) -> None:
        row = evidence()
        row["pr"]["canonical_shard_jobs"]["shard_2"] = "SUCCESS"
        report = compile_latency_report(row)
        self.assertEqual(report["classification"], "AA0_PREWARM_OTHER_EXACT_REUSE_FAILURE")

    def test_no_github_write_api_usage(self) -> None:
        source = TOOL.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = {
            root
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for root in (
                [alias.name.split(".", 1)[0] for alias in node.names]
                if isinstance(node, ast.Import)
                else [str(node.module).split(".", 1)[0]]
            )
        }
        self.assertTrue({"argparse", "datetime", "json", "pathlib", "re", "typing"} <= imported)
        self.assertTrue({"urllib", "requests", "http", "socket", "subprocess"}.isdisjoint(imported))
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertTrue({"write_text", "write_bytes", "unlink", "rename", "mkdir"}.isdisjoint(calls))

    def test_no_repository_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = directory / "evidence.json"
            source.write_text(json.dumps(evidence()), encoding="utf-8")
            before = sorted(path.name for path in directory.iterdir())
            proc = subprocess.run(
                [sys.executable, str(TOOL), "--evidence", str(source)],
                cwd=directory,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(sorted(path.name for path in directory.iterdir()), before)

    def test_no_rac_proof_substitution_assumption(self) -> None:
        row = evidence()
        row["controls"]["racpr_mode"] = "PROOF_SUBSTITUTION"
        report = compile_latency_report(row)
        self.assertEqual(report["classification"], "AA0_PREWARM_CORRECTNESS_BLOCKED")
        self.assertEqual(report["controls"]["racpr_mode"], "PROOF_SUBSTITUTION")

    def test_packet_authority_and_frontier_are_content_addressed(self) -> None:
        packet = json.loads(
            (PACKET_DIR / "DSAI3V_AA0_PREWARM_OBSERVABILITY_MAINTENANCE_PACKET_v0_1.json").read_text()
        )
        bindings = {
            "authority_manifest_id": "DSAI3V_AA0_PREWARM_OBSERVABILITY_AUTHORITY_MANIFEST_v0_1.json",
            "dependency_frontier_id": "DSAI3V_AA0_PREWARM_OBSERVABILITY_DEPENDENCY_FRONTIER_v0_1.json",
        }
        for field, filename in bindings.items():
            record = json.loads((PACKET_DIR / filename).read_text())
            payload = {key: value for key, value in record.items() if key != "logical_id"}
            digest = hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
            ).hexdigest()
            self.assertEqual(record["logical_id"], digest)
            self.assertEqual(packet[field], digest)
        self.assertEqual(packet["authority_delta"], "NONE")

    def test_packet_does_not_modify_measured_assurance_machinery(self) -> None:
        packet = json.loads(
            (PACKET_DIR / "DSAI3V_AA0_PREWARM_OBSERVABILITY_MAINTENANCE_PACKET_v0_1.json").read_text()
        )
        prohibited = {
            ".github/workflows/tests.yml",
            ".github/workflows/ovc-tiered-tests.yml",
            "tools/ci/vit_assurance_preflight.py",
            "tools/ci/prvitr_live_admission.py",
            "tools/ci/prvitr_rac_ready.py",
            "tools/ci/pytest_shard_canonical.py",
            "tools/ci/pytest_unittest_parity.py",
            "tools/ci/aa0_harness_identity.py",
        }
        self.assertTrue(prohibited.isdisjoint(packet["write_set"]))
        self.assertFalse(packet["assurance_machinery_changes"])


if __name__ == "__main__":
    unittest.main()
