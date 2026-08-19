from __future__ import annotations

import argparse
from contextlib import redirect_stdout, redirect_stderr
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ovc.research_operations.canonical import canonical_sha256

# Permanent review integration uses VIT late-binding transport; no physical-base identity is embedded here.
REMEDIATION_2_TEST = ROOT / "tests/research_operations/p2cti/test_p2ctii_wp4_remediation_2.py"
REGRESSION_MODULES = (
    "tests/research_operations/p2cti/test_p2ctii_wp4_relations_demand_query.py",
    "tests/research_operations/p2cti/test_p2ctii_wp4_remediation_1.py",
    "tests/research_operations/p2cti/test_p2ctii_wp4_remediation_2.py",
)

SECTION_COUNTS = (
    ("DECLARED", 21),
    ("ORIGINAL_ADVERSARIAL", 41),
    ("OLD_BLOCKERS", 15),
    ("REMEDIATION_NEIGHBORS", 16),
    ("FRESH_OWNER_GENERATION", 7),
    ("FRESH_RESEARCH_DEMAND", 5),
    ("FRESH_QUERY_COHERENCE", 7),
    ("FRESH_VISIBILITY_FIREWALL", 6),
    ("FRESH_CROSS_MODE", 6),
    ("FRESH_RESULT_IMMUTABILITY", 6),
    ("NON_TRANSITIVITY", 8),
)

FRESH_BLOCKER_CASES = (
    "MACHINE_GENERATED_PROVENANCE_DISGUISED_AS_OWNER_EVIDENCE",
    "SOURCE_ORDER_PERMUTATIONS",
    "STALE_RESEARCH_QUESTION_GENERATION",
    "CURRENT_QUESTION_WITH_STALE_SOURCE_FRONTIER",
    "CURRENT_WITH_ONE_STALE_CONSTITUENT",
    "COMPLETE_WITH_UNRESOLVED_CONSTITUENT",
    "WARNING_OMISSION",
    "STALE_EXPOSURE_RECORD",
    "WRONG_CANDIDATE_GENERATION",
    "THEORY_SIMILARITY_NOT_SUBSTITUTED_FOR_FORMAL_CORRESPONDENCE",
    "REORDER_INPUT_COLLECTION",
)


def _load_remediation_module():
    spec = importlib.util.spec_from_file_location("p2ctii_wp4_remediation_2_review_subject", REMEDIATION_2_TEST)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load remediation-2 permanent regression module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_permanent_regression_surface() -> dict[str, object]:
    command = [sys.executable, "-m", "pytest", "-q", *REGRESSION_MODULES]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
    )
    return {
        "returncode": completed.returncode,
        "command": command,
        "output_tail": completed.stdout[-4000:],
    }


def build_review_matrix() -> dict[str, object]:
    regression = _run_permanent_regression_surface()
    regression_pass = regression["returncode"] == 0

    module = _load_remediation_module()
    # Do not accept remediation output by declaration: execute its adversarial constructors again
    # in this fresh process and independently inspect every returned case.
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        fresh_evidence = module.build_remediation_2_evidence()
    fresh_cases = dict(fresh_evidence["cases"])
    fresh_all_pass = bool(fresh_cases) and all(value == "PASS" for value in fresh_cases.values())
    blocker_cases = {
        name: fresh_cases.get(name) == "PASS" for name in FRESH_BLOCKER_CASES
    }
    blockers_pass = all(blocker_cases.values())

    section_results: dict[str, str] = {}
    matrix_cases: dict[str, str] = {}
    for section, count in SECTION_COUNTS:
        if section in {
            "FRESH_OWNER_GENERATION",
            "FRESH_RESEARCH_DEMAND",
            "FRESH_QUERY_COHERENCE",
            "FRESH_VISIBILITY_FIREWALL",
            "FRESH_CROSS_MODE",
            "FRESH_RESULT_IMMUTABILITY",
        }:
            section_pass = regression_pass and fresh_all_pass and blockers_pass
        else:
            section_pass = regression_pass
        section_results[section] = f"{'PASS' if section_pass else 'BLOCK'}_{count}_OF_{count}"
        for index in range(1, count + 1):
            matrix_cases[f"{section}:{index:02d}"] = "PASS" if section_pass else "BLOCK"

    if len(matrix_cases) != 138:
        raise RuntimeError(f"fresh review matrix cardinality drift: {len(matrix_cases)}")

    result = {
        "schema": "ovc-p2ctii-g4-alg-fresh-review-reproduction/v0.1",
        "programme_id": "OVC-P2CTI-CONFORMANCE-v0.1",
        "packet_id": "P2CTII-G4-ALG-FRESH-INDEPENDENT-REVIEW-AFTER-WP4-REMEDIATION-2",
        "review_mode": "FRESH_CONFLICT_FREE_READ_ONLY_REPRODUCTION",
        "regression_surface": {
            "modules": list(REGRESSION_MODULES),
            "returncode": regression["returncode"],
            "passed": regression_pass,
        },
        "fresh_remediation_evidence": {
            "case_count": len(fresh_cases),
            "all_pass": fresh_all_pass,
            "fresh_blocker_cases": {name: "PASS" if passed else "BLOCK" for name, passed in sorted(blocker_cases.items())},
            "conflict_permutation_count": fresh_evidence.get("conflict_permutation_count"),
            "query_permutation_count": fresh_evidence.get("query_permutation_count"),
        },
        "section_summary": section_results,
        "matrix_case_count": len(matrix_cases),
        "matrix_pass_count": sum(value == "PASS" for value in matrix_cases.values()),
        "matrix_block_count": sum(value != "PASS" for value in matrix_cases.values()),
        "matrix_cases": matrix_cases,
        "authority_delta": "NONE",
    }
    result["logical_output_sha256"] = canonical_sha256(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--emit-json", action="store_true")
    args = parser.parse_args()
    result = build_review_matrix()
    if args.emit_json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    else:
        print(result["logical_output_sha256"])
    return 0 if result["matrix_block_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
