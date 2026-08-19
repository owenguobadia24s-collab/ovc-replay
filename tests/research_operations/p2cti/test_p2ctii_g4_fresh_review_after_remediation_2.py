from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from ovc.research_operations.canonical import canonical_sha256

ROOT = Path(__file__).resolve().parents[3]
HARNESS = ROOT / "tools/reviews/p2ctii_g4_fresh_after_remediation_2.py"


def _run(seed: str) -> dict:
    completed = subprocess.run(
        [sys.executable, str(HARNESS), "--emit-json"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env={**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": str(ROOT / "src")},
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return json.loads(completed.stdout)


def test_fresh_g4_review_reproduces_complete_138_case_matrix_in_two_clean_processes() -> None:
    first = _run("71")
    second = _run("1907")
    assert first == second
    assert first["matrix_case_count"] == 138
    assert first["matrix_pass_count"] == 138
    assert first["matrix_block_count"] == 0
    assert first["fresh_remediation_evidence"]["case_count"] == 26
    assert first["fresh_remediation_evidence"]["all_pass"] is True
    assert all(
        result == "PASS"
        for result in first["fresh_remediation_evidence"]["fresh_blocker_cases"].values()
    )
    assert first["fresh_remediation_evidence"]["conflict_permutation_count"] == 6
    assert first["fresh_remediation_evidence"]["query_permutation_count"] == 6
    expected = first["logical_output_sha256"]
    body = {key: value for key, value in first.items() if key != "logical_output_sha256"}
    assert expected == canonical_sha256(body)
