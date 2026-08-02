from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/development/v0_2/build_ci_admission_baseline_v0_2.py"
spec = importlib.util.spec_from_file_location("da2_builder", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def make_registry() -> dict:
    return {
        "schema": "ovc-da2-workflow-classification-registry/v2",
        "subjects": [
            {"subject_id": "A", "pull_request": 1, "commit_sha": "a" * 40, "evidence_directory": "A"},
            {"subject_id": "B", "pull_request": 2, "commit_sha": "b" * 40, "evidence_directory": "B"},
        ],
        "ruleset": {"ruleset_id": 1, "required_contexts": ["tests", "OVC tiered test selection shadow"]},
        "required_context_sources": {
            "tests": {"app_id": 15368, "app_slug": "github-actions"},
            "OVC tiered test selection shadow": {"app_id": 15368, "app_slug": "github-actions"},
        },
        "complete_suite_contexts": ["tests", "OVC tiered test selection shadow"],
        "classifications": {
            "REQUIRED": ["tests", "OVC tiered test selection shadow"],
            "RELEVANT_OPTIONAL": [],
            "EXPECTED_SKIPPED": ["skip"],
            "UNRELATED": [],
            "BLOCKING_SOURCE_MISMATCH": [],
        },
    }


def pages(key: str, values: list[dict]) -> bytes:
    return (json.dumps([{"total_count": len(values), key: values}], indent=2) + "\n").encode()


def create_evidence_zip(path: Path, *, skipped_inversion: bool = False,
                        non_skipped_inversion: bool = False,
                        wrong_app: bool = False,
                        omit_run_started: bool = False,
                        tamper_manifest: bool = False) -> None:
    files: dict[str, bytes] = {}
    for subject, sha, base_id in (("A", "a" * 40, 1000), ("B", "b" * 40, 2000)):
        runs = []
        suites = []
        checks = []
        names = ["tests", "OVC tiered test selection shadow"]
        if subject == "A":
            names.append("skip")
        for index, name in enumerate(names):
            run_id = base_id + index
            suite_id = base_id + 100 + index
            conclusion = "skipped" if name == "skip" else "success"
            run = {
                "id": run_id,
                "workflow_id": base_id + 200 + index,
                "name": name,
                "event": "pull_request",
                "path": f".github/workflows/{name.replace(' ', '-')}.yml",
                "status": "completed",
                "conclusion": conclusion,
                "created_at": "2026-08-02T20:00:00Z",
                "run_started_at": None if omit_run_started and subject == "A" and index == 0 else "2026-08-02T20:00:01Z",
                "updated_at": "2026-08-02T20:00:05Z",
                "check_suite_id": suite_id,
            }
            runs.append(run)
            app_id = 999 if wrong_app and subject == "A" and index == 0 else 15368
            app_slug = "wrong" if app_id == 999 else "github-actions"
            suites.append({"id": suite_id, "app": {"id": app_id, "slug": app_slug}})
            checks.append({
                "id": base_id + 300 + index,
                "check_suite": {"id": suite_id},
                "app": {"id": app_id, "slug": app_slug},
            })
            if conclusion == "skipped" and skipped_inversion:
                started, completed = "2026-08-02T20:00:05Z", "2026-08-02T20:00:04Z"
            elif conclusion != "skipped" and non_skipped_inversion and subject == "A" and index == 0:
                started, completed = "2026-08-02T20:00:05Z", "2026-08-02T20:00:04Z"
            else:
                started, completed = "2026-08-02T20:00:01Z", "2026-08-02T20:00:04Z"
            jobs = [{
                "id": base_id + 400 + index,
                "name": name,
                "status": "completed",
                "conclusion": conclusion,
                "started_at": started,
                "completed_at": completed,
            }]
            files[f"raw/{subject}/jobs/{run_id}.jobs.pages.json"] = pages("jobs", jobs)
        files[f"raw/{subject}/subject-summary.json"] = (
            json.dumps({"subject": subject, "commit_sha": sha, "workflow_run_count": len(runs)}) + "\n"
        ).encode()
        files[f"raw/{subject}/workflow-runs.pages.json"] = pages("workflow_runs", runs)
        files[f"raw/{subject}/check-suites.pages.json"] = pages("check_suites", suites)
        files[f"raw/{subject}/check-runs.pages.json"] = pages("check_runs", checks)
        files[f"raw/{subject}/combined-status.json"] = b'{"statuses":[]}\n'
        files[f"raw/{subject}/commit.json"] = (json.dumps({"sha": sha}) + "\n").encode()
    files["capture-metadata.json"] = b'{"capture":"synthetic"}\n'

    manifest = [
        {"relative_path": name.replace("/", "\\"), "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        for name, payload in sorted(files.items())
    ]
    manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode()
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    if tamper_manifest:
        manifest[0]["bytes"] += 1
        manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode()
        manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in files.items():
            archive.writestr(name, payload)
        archive.writestr("SHA256_MANIFEST.json", manifest_bytes)
        archive.writestr("SHA256_MANIFEST.sha256.txt", manifest_sha + "\n")


class DA2AdmissionBaselineTests(unittest.TestCase):
    def build(self, **kwargs):
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary) / "evidence.zip"
            create_evidence_zip(evidence, **kwargs)
            registry = make_registry()
            external = {"sha256": hashlib.sha256(evidence.read_bytes()).hexdigest()}
            first = module.build(evidence, registry, external)
            second = module.build(evidence, registry, external)
            return first, second

    def test_complete_evidence_is_deterministic(self):
        first, second = self.build()
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "PASS")
        self.assertFalse(first["reproducibility"]["estimated_values_used"])

    def test_skipped_job_inversion_is_not_estimated(self):
        first, _ = self.build(skipped_inversion=True)
        self.assertEqual(first["aggregate"]["skipped_job_timing_anomalies"], 1)
        anomaly = first["subjects"][0]["timing_anomalies"][0]
        self.assertEqual(anomaly["resolution"], "DURATION_NOT_EVALUABLE_NO_ESTIMATE_USED")
        skip_run = next(run for run in first["subjects"][0]["runs"] if run["workflow_name"] == "skip")
        self.assertEqual(skip_run["job_timing_status"], "NOT_EVALUABLE_SKIPPED_INVERSION_PRESENT")

    def test_non_skipped_job_inversion_blocks(self):
        with self.assertRaisesRegex(module.AdmissionEvidenceError, "negative duration"):
            self.build(non_skipped_inversion=True)

    def test_missing_run_timing_blocks(self):
        with self.assertRaisesRegex(module.AdmissionEvidenceError, "missing exact fields"):
            self.build(omit_run_started=True)

    def test_required_source_identity_mismatch_blocks(self):
        with self.assertRaisesRegex(module.AdmissionEvidenceError, "source identity mismatch"):
            self.build(wrong_app=True)

    def test_manifest_mismatch_blocks(self):
        with self.assertRaisesRegex(module.AdmissionEvidenceError, "byte-size mismatch"):
            self.build(tamper_manifest=True)

    def test_ambiguous_classification_blocks(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary) / "evidence.zip"
            create_evidence_zip(evidence)
            registry = make_registry()
            registry["classifications"]["UNRELATED"].append("tests")
            with self.assertRaisesRegex(module.AdmissionEvidenceError, "2 classifications"):
                module.build(evidence, registry, {"sha256": "x"})

    def test_materialized_repository_packet_validates(self):
        validator_path = ROOT / "scripts/development/v0_2/validate_da2_g0.py"
        validator_spec = importlib.util.spec_from_file_location("da2_validator", validator_path)
        assert validator_spec and validator_spec.loader
        validator = importlib.util.module_from_spec(validator_spec)
        validator_spec.loader.exec_module(validator)
        self.assertEqual(validator.main(), 0)


if __name__ == "__main__":
    unittest.main()
