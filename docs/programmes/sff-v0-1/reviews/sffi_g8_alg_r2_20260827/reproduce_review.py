from __future__ import annotations

import argparse
import ast
from copy import deepcopy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ovc.research_operations.sff.claims import ChallengerComparison, decide_claim
from ovc.research_operations.sff.core import SFFContractError
from ovc.research_operations.sff.preregistration import compile_preregistration
from ovc.research_operations.sff.risk import DistributionRecord


def load_base_harness(config: dict[str, Any]):
    path = ROOT / config["base_harness"]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != config["base_harness_sha256"]:
        raise RuntimeError(f"BASE_HARNESS_IDENTITY_MISMATCH:{digest}")
    spec = importlib.util.spec_from_file_location("sffi_g8_r1_harness", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("BASE_HARNESS_LOAD_FAILURE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def nonfinite_matrix() -> dict[str, Any]:
    rejected = []
    for label, value in (("NaN", math.nan), ("+Infinity", math.inf), ("-Infinity", -math.inf)):
        try:
            DistributionRecord({"A": value}, "COMPLETE", "KNOWN")
        except SFFContractError as exc:
            if str(exc) == "probabilities must be finite":
                rejected.append(label)
    return {"kind": "PASS", "rejected": rejected}


def multi_challenger_noncompensation(base) -> dict[str, Any]:
    decision = decide_claim(
        generation_id="g-r2",
        dimension_results=base.passing_dimensions(),
        falsification=base.contract(),
        challengers=(
            ChallengerComparison("matched-failure", True, "FAIL", "PASS"),
            ChallengerComparison("population-failure", True, "PASS", "FAIL"),
        ),
    )
    return {"kind": "PASS", "decision": decision.decision, "blocking_failures": list(decision.blocking_failures)}


def deep_nested_outcome_access(config: dict[str, Any], base) -> dict[str, Any]:
    fields = deepcopy(config["preregistration_base"])
    fields["scientific_endpoint_manifest"]["nested"] = [
        {"deeper": [{"protected_outcomes_accessed": True}]}
    ]
    return base.rejected(lambda: compile_preregistration(fields))


def call_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def string_error(raise_node: ast.Raise) -> str | None:
    exc = raise_node.exc
    if not isinstance(exc, ast.Call) or not exc.args:
        return None
    argument = exc.args[0]
    return argument.value if isinstance(argument, ast.Constant) and isinstance(argument.value, str) else None


def adversarial_production_path_source() -> dict[str, Any]:
    source_path = SRC / "ovc/research_operations/sff/adversarial.py"
    corpus_path = ROOT / "fixtures/research_operations/sff/SFFI_WP6_ADVERSARIAL_CORPUS_v0_1.json"
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    exercise = functions["_exercise"]
    calls = {name for node in ast.walk(exercise) if isinstance(node, ast.Call) if (name := call_name(node))}
    required_calls = {
        "require_first_valid_chronology", "validate_no_future_leakage", "validate_frozen_identity",
        "evaluate_with_opt_c", "DistributionRecord", "validate_declared_population", "build",
        "validate_calibration_separation", "validate_endpoint", "validate_frozen_scope", "create",
        "reentry_generation", "build_forecast_snapshot", "clean_rebuild", "update_from_outcomes",
        "validate_state_separation", "compile_preregistration", "classify_feasibility",
        "reconcile_population", "validate_capacity_budget", "validate_atomic_freeze", "validate_method_binding",
    }
    helper_names = (
        "validate_frozen_identity", "validate_no_future_leakage", "validate_declared_population",
        "validate_calibration_separation", "validate_frozen_scope", "validate_capacity_budget",
    )
    guarded = [
        name for name in helper_names
        if any(isinstance(node, ast.If) for node in ast.walk(functions[name]))
        and any(isinstance(node, ast.Raise) for node in ast.walk(functions[name]))
    ]
    expected_literals = {
        row["expected"]
        for row in json.loads(corpus_path.read_text(encoding="utf-8"))["cases"]
    }
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(exercise):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    unguarded = []
    for node in ast.walk(exercise):
        if not isinstance(node, ast.Raise):
            continue
        message = string_error(node)
        if message not in expected_literals:
            continue
        cursor = parents.get(node)
        guarded_by_condition = False
        while cursor is not None and cursor is not exercise:
            if isinstance(cursor, ast.If):
                guarded_by_condition = True
                break
            cursor = parents.get(cursor)
        if not guarded_by_condition:
            unguarded.append(message)
    return {
        "kind": "PASS",
        "required_calls_present": required_calls <= calls,
        "guarded_helper_count": len(guarded),
        "unguarded_expected_literal_raises": sorted(unguarded),
    }


def run_operation(operation: str, config: dict[str, Any], base) -> dict[str, Any]:
    if operation == "nonfinite_matrix":
        return nonfinite_matrix()
    if operation == "multi_challenger_noncompensation":
        return multi_challenger_noncompensation(base)
    if operation == "deep_nested_outcome_access":
        return deep_nested_outcome_access(config, base)
    if operation == "adversarial_production_path_source":
        return adversarial_production_path_source()
    return base.run_operation(operation, config)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--expected", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    config = json.loads(args.input.read_text(encoding="utf-8"))
    expectations = json.loads(args.expected.read_text(encoding="utf-8"))["expectations"]
    base = load_base_harness(config)
    results = []
    for case in config["cases"]:
        observed = run_operation(case["operation"], config, base)
        expected = expectations[case["id"]]
        results.append({
            "case_id": case["id"], "dimension": case["dimension"],
            "expected": expected, "observed": observed,
            "result": "PASS" if observed == expected else "BLOCK",
        })
    output = {
        "schema": "ovc-sffi-g8-alg-r2-independent-actual/v0.1",
        "review_id": config["review_id"], "reviewed_commit": config["reviewed_commit"],
        "total": len(results), "passed": sum(row["result"] == "PASS" for row in results),
        "blocked": sum(row["result"] == "BLOCK" for row in results), "results": results,
    }
    args.output.write_bytes(json.dumps(output, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n")
    print(json.dumps({key: output[key] for key in ("review_id", "reviewed_commit", "total", "passed", "blocked")}, sort_keys=True))
    return 1 if output["blocked"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
