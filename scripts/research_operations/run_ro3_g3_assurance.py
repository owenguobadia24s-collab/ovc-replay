from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import replace
from pathlib import Path

from ovc.opt_b.c1 import build, dumps
from ovc.research_operations.v0_3 import (
    load_invariant_registry,
    parse_formula_registry,
    run_metamorphic_assurance,
)

ROOT = Path(__file__).resolve().parents[2]
INVARIANT_PATH = ROOT / "registries/research_operations/v0_3/C1_METAMORPHIC_INVARIANT_REGISTRY_v0_1.yaml"
FORMULA_PATH = ROOT / "registries/opt_b/c1/C1_FORMULA_REGISTRY_v0_1.yaml"
FIXTURE_PATH = ROOT / "fixtures/research_operations/v0_3/wp3_metamorphic_cases.json"
G0_MERGE_COMMIT = "4d701ad78af8597e182565eb301739501b51dff6"


def _git_blob(revision: str, path: Path) -> str:
    relative = path.relative_to(ROOT).as_posix()
    return subprocess.check_output(
        ["git", "rev-parse", f"{revision}:{relative}"],
        cwd=ROOT,
        text=True,
    ).strip()


def _current_blob(path: Path) -> str:
    return subprocess.check_output(
        ["git", "hash-object", path.relative_to(ROOT).as_posix()],
        cwd=ROOT,
        text=True,
    ).strip()


def _corrupted_engine(current: dict, prior: dict | None):
    result = build(current, prior)
    measurements = dict(result.measurements)
    measurements["body_abs"] = "999"
    return replace(result, measurements=measurements)


def build_evidence() -> dict:
    invariant_text = INVARIANT_PATH.read_text(encoding="utf-8")
    formula_text = FORMULA_PATH.read_text(encoding="utf-8")
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    invariant_registry = load_invariant_registry(invariant_text)
    formula_registry = parse_formula_registry(formula_text)

    actual = run_metamorphic_assurance(
        invariant_registry,
        formula_registry,
        build,
        fixture["current"],
        fixture["prior"],
        dumps,
    )
    negative_control = run_metamorphic_assurance(
        invariant_registry,
        formula_registry,
        _corrupted_engine,
        fixture["current"],
        fixture["prior"],
        dumps,
    )

    g0_blob = _git_blob(G0_MERGE_COMMIT, INVARIANT_PATH)
    current_blob = _current_blob(INVARIANT_PATH)
    registry_unchanged = g0_blob == current_blob
    negative_control_detected = negative_control["status"] == "BLOCK"
    status = "PASS" if actual["status"] == "PASS" and registry_unchanged and negative_control_detected else "BLOCK"
    return {
        "schema": "ovc-ro3-g3-assurance-evidence/v1",
        "gate_id": "RO3-G3",
        "invariant_registry": {
            "path": INVARIANT_PATH.relative_to(ROOT).as_posix(),
            "g0_merge_commit": G0_MERGE_COMMIT,
            "g0_blob_sha": g0_blob,
            "current_blob_sha": current_blob,
            "unchanged_since_g0": registry_unchanged,
            "logical_sha256": invariant_registry["registry_logical_sha256"],
            "primitive_count": invariant_registry["formula_count"],
            "source_of_expectations": invariant_registry["source_of_expectations"],
        },
        "formula_registry": {
            "path": FORMULA_PATH.relative_to(ROOT).as_posix(),
            "registry_id": formula_registry["registry_id"],
            "logical_sha256": formula_registry["registry_logical_sha256"],
            "primitive_count": formula_registry["formula_count"],
        },
        "actual_implementation_run": actual,
        "negative_control_run": negative_control,
        "negative_control_detected": negative_control_detected,
        "status": status,
        "qa_recommendation": "PASS" if status == "PASS" else "BLOCK",
        "authority_effect": "QA_EVIDENCE_ONLY",
        "writes": "NONE",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()
    evidence = build_evidence()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": evidence["status"],
        "qa_recommendation": evidence["qa_recommendation"],
        "actual_failed_assertion_count": evidence["actual_implementation_run"]["failed_assertion_count"],
        "actual_failed_assertions": evidence["actual_implementation_run"]["failed_assertions"],
        "negative_control_detected": evidence["negative_control_detected"],
        "invariant_registry_unchanged": evidence["invariant_registry"]["unchanged_since_g0"],
        "output": str(args.output),
    }, indent=2, sort_keys=True))
    if args.require_pass and evidence["status"] != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
