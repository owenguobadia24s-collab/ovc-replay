from __future__ import annotations

import argparse
import ast
from copy import deepcopy
from datetime import datetime, timedelta
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ovc.research_operations.sff.adversarial import run_adversarial_corpus
from ovc.research_operations.sff.claims import (
    ChallengerComparison,
    FailureRecord,
    SFFFalsificationContract,
    decide_claim,
    reentry_generation,
)
from ovc.research_operations.sff.core import (
    ResearchFreezeFrontier,
    canonical_bytes,
    content_identity,
    require_first_valid_chronology,
)
from ovc.research_operations.sff.forecast import (
    ForecastModelGeneration,
    UncertaintyRecord,
    build_forecast_snapshot,
)
from ovc.research_operations.sff.frontier import (
    StructuralAntecedent,
    checkpoint,
    generate_one_step_frontier,
)
from ovc.research_operations.sff.preregistration import compile_preregistration
from ovc.research_operations.sff.risk import (
    DistributionRecord,
    ForecastRiskSetManifest,
    RiskSetEntry,
    RiskStatus,
)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, text=True, capture_output=True
    ).stdout.strip()


def rejected(call: Callable[[], Any]) -> dict[str, Any]:
    try:
        call()
    except Exception as exc:  # evidence records the exact implementation exception
        return {"kind": "REJECTED", "error_type": type(exc).__name__, "message": str(exc)}
    return {"kind": "ACCEPTED"}


def parsed_time(value: str) -> datetime:
    return datetime.fromisoformat(value)


def frontier_inputs(config: dict[str, Any], *, equality: bool = False):
    antecedent_at = parsed_time(config["chronology"]["antecedent"])
    cutoff_at = parsed_time(config["chronology"]["cutoff"])
    if equality:
        antecedent_at = cutoff_at
    antecedent = StructuralAntecedent(
        "antecedent-1", "owner-fact-1", antecedent_at, "SYNTHETIC_NODE", {"rank": 1}
    )
    freeze = ResearchFreezeFrontier(
        "freeze-1", cutoff_at, "synthetic-source", "synthetic-authority"
    )
    return antecedent, freeze


def model() -> ForecastModelGeneration:
    return ForecastModelGeneration.freeze(
        "method-v1", {"alpha": 0.25}, "calibration:synthetic:train-only"
    )


def uncertainty(*, epistemic: str = "BOUNDED") -> UncertaintyRecord:
    return UncertaintyRecord(
        epistemic, "ESTIMATED", "IN_ENVELOPE", "synthetic-evidence-v1"
    )


def challenger(*, matched: str = "PASS", population: str = "PASS") -> ChallengerComparison:
    return ChallengerComparison("credible-simpler-v1", True, matched, population)


def contract() -> SFFFalsificationContract:
    return SFFFalsificationContract(
        "falsification-v1", ("FULL_POPULATION", "MATCHED_SUPPORT", "CALIBRATION", "UNCERTAINTY")
    )


def passing_dimensions() -> dict[str, str]:
    return {dimension: "PASS" for dimension in contract().blocking_dimensions}


def prereg(config: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(config["preregistration_base"])


def run_operation(operation: str, config: dict[str, Any]) -> dict[str, Any]:
    if operation == "packet_chain":
        times = []
        for row in config["packet_chain"]:
            if git("rev-parse", f"{row['baseline_commit']}^{{tree}}") != row["baseline_tree"]:
                return {"kind": "BLOCK", "packet": row["packet"], "reason": "BASELINE_TREE_MISMATCH"}
            if git("rev-parse", f"{row['commit']}^") != row["baseline_commit"]:
                return {"kind": "BLOCK", "packet": row["packet"], "reason": "PARENT_MISMATCH"}
            times.append(parsed_time(git("show", "-s", "--format=%aI", row["commit"])))
        if git("rev-parse", f"{config['reviewed_commit']}^{{tree}}") != config["reviewed_tree"]:
            return {"kind": "BLOCK", "reason": "REVIEWED_TREE_MISMATCH"}
        return {"kind": "PASS"} if times == sorted(times) and len(set(times)) == len(times) else {"kind": "BLOCK", "reason": "COMMIT_CHRONOLOGY"}

    if operation == "reviewer_independence":
        return {"kind": "PASS"} if config["reviewer_id"] != config["implementation_author"] else {"kind": "BLOCK"}

    if operation == "canonical_order":
        left = {"b": [2, 1], "a": {"z": True}}
        right = {"a": {"z": True}, "b": [2, 1]}
        return {"kind": "SAME" if content_identity("sff-review", left) == content_identity("sff-review", right) else "DIFFERENT"}

    if operation == "semantic_mutation":
        left = {"label": "CONTINUATION"}
        right = {"label": "REVERSAL"}
        return {"kind": "DIFFERENT" if content_identity("sff-review", left) != content_identity("sff-review", right) else "SAME"}

    antecedent_at = parsed_time(config["chronology"]["antecedent"])
    cutoff_at = parsed_time(config["chronology"]["cutoff"])
    if operation == "chronology_valid":
        require_first_valid_chronology(antecedent_at=antecedent_at, cutoff_at=cutoff_at)
        return {"kind": "ACCEPTED"}
    if operation == "chronology_equal":
        return rejected(lambda: require_first_valid_chronology(antecedent_at=cutoff_at, cutoff_at=cutoff_at))
    if operation == "chronology_future":
        return rejected(lambda: require_first_valid_chronology(antecedent_at=cutoff_at + timedelta(seconds=1), cutoff_at=cutoff_at))

    if operation == "authority_static_scan":
        forbidden = {"requests", "httpx", "urllib", "socket", "boto3"}
        found = []
        for path in sorted((SRC / "ovc/research_operations/sff").glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    found.extend(name.name for name in node.names if name.name.split(".")[0] in forbidden)
                elif isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] in forbidden:
                    found.append(node.module)
        return {"kind": "PASS"} if not found else {"kind": "BLOCK", "forbidden_imports": sorted(set(found))}

    if operation == "frontier_replay":
        antecedent, freeze = frontier_inputs(config)
        args = dict(
            antecedent=antecedent,
            freeze=freeze,
            grammar_identity="grammar-v1",
            structural_labels=("CONTINUATION", "REVERSAL", "TERMINATION"),
            expected_owner_fact_id="owner-fact-1",
        )
        first = generate_one_step_frontier(**args)
        second = generate_one_step_frontier(**args)
        return {"kind": "BYTE_EQUAL" if checkpoint(first) == checkpoint(second) else "MISMATCH", "targets": len(first.targets), "source_mode": first.source_mode}
    if operation == "frontier_owner_mismatch":
        antecedent, freeze = frontier_inputs(config)
        return rejected(lambda: generate_one_step_frontier(antecedent=antecedent, freeze=freeze, grammar_identity="grammar-v1", structural_labels=("A",), expected_owner_fact_id="wrong"))
    if operation == "frontier_cutoff_equality":
        antecedent, freeze = frontier_inputs(config, equality=True)
        return rejected(lambda: generate_one_step_frontier(antecedent=antecedent, freeze=freeze, grammar_identity="grammar-v1", structural_labels=("A",), expected_owner_fact_id="owner-fact-1"))

    if operation == "risk_denominator":
        rows = [
            RiskSetEntry("t1", "o1", 0, RiskStatus.RESOLVED, "d:o1"),
            RiskSetEntry("t2", "o2", 0, RiskStatus.PREEMPTED, "d:o2"),
            RiskSetEntry("t3", "o3", 0, RiskStatus.STILL_AT_RISK, "d:o3"),
        ]
        manifest = ForecastRiskSetManifest.build("population-v1", rows)
        counts = manifest.counts()
        return {"kind": "PASS", "denominator": manifest.denominator, "count_sum": sum(counts.values()), "preempted": counts["PREEMPTED"]}
    if operation == "risk_missing_owner":
        row = RiskSetEntry("t1", "o1", 0, RiskStatus.RESOLVED, "d:o1", "MISSING")
        manifest = ForecastRiskSetManifest.build("population-v1", [row])
        return {"kind": "PASS", "status": manifest.entries[0].status.value}
    if operation == "partial_unknown_support":
        distribution = DistributionRecord({"A": 0.4}, "PARTIAL", "UNKNOWN")
        return {"kind": "PASS", "unobserved_probability": distribution.probability("B"), "allocated_mass": sum(distribution.probabilities.values())}
    if operation == "nan_distribution":
        return rejected(lambda: DistributionRecord({"A": math.nan}, "COMPLETE", "KNOWN"))
    if operation == "pseudo_independent_risk_set":
        rows = [
            RiskSetEntry("t1", "origin", 0, RiskStatus.STILL_AT_RISK, "group-1"),
            RiskSetEntry("t1", "origin", 1, RiskStatus.RESOLVED, "group-2"),
        ]
        return rejected(lambda: ForecastRiskSetManifest.build("population-v1", rows))

    distribution = DistributionRecord({"A": 0.6, "B": 0.4}, "COMPLETE", "KNOWN")
    if operation == "stale_support_abstention":
        snapshot = build_forecast_snapshot(target_id="t1", generation=model(), distribution=distribution, uncertainty=uncertainty(), support_currentness="STALE")
        return {"kind": "PASS", "status": snapshot.status, "distribution_emitted": snapshot.distribution is not None}
    if operation == "unknown_uncertainty_abstention":
        snapshot = build_forecast_snapshot(target_id="t1", generation=model(), distribution=distribution, uncertainty=uncertainty(epistemic="UNKNOWN"), support_currentness="CURRENT_SUPPORTED")
        return {"kind": "PASS", "status": snapshot.status, "distribution_emitted": snapshot.distribution is not None}
    if operation == "same_generation_update":
        return rejected(lambda: model().update_from_outcomes({"realised": 1}))

    if operation == "blocking_dimension":
        dimensions = passing_dimensions(); dimensions["UNCERTAINTY"] = "BLOCK"
        decision = decide_claim(generation_id="g1", dimension_results=dimensions, falsification=contract(), challengers=(challenger(),))
        return {"kind": "PASS", "decision": decision.decision, "blocking_failures": list(decision.blocking_failures)}
    if operation in {"failed_matched_challenger", "failed_population_challenger"}:
        failed = challenger(matched="FAIL") if operation == "failed_matched_challenger" else challenger(population="FAIL")
        decision = decide_claim(generation_id="g1", dimension_results=passing_dimensions(), falsification=contract(), challengers=(failed,))
        blockers = list(decision.blocking_failures) or []
        return {"kind": "PASS", "decision": decision.decision, "blocking_failures": blockers if blockers else []}

    if operation == "same_generation_rescue":
        failure = FailureRecord.create("g1", "semantics-v1", "ENDPOINT_FAILED", "FAILED_CONFIRMATORY")
        return rejected(lambda: reentry_generation(failure, proposed_generation_id="g1", proposed_target_semantics_id="semantics-v1"))
    if operation == "changed_semantics_reentry":
        failure = FailureRecord.create("g1", "semantics-v1", "ENDPOINT_FAILED", "FAILED_CONFIRMATORY")
        return {"kind": "PASS", "disposition": reentry_generation(failure, proposed_generation_id="g2", proposed_target_semantics_id="semantics-v2")}

    if operation == "prereg_deterministic":
        first = compile_preregistration(prereg(config)); second = compile_preregistration(prereg(config))
        receipt = first.freeze_receipt
        return {"kind": "PASS", "byte_equal": canonical_bytes(first) == canonical_bytes(second), "atomic": receipt.atomic, "protected_outcomes_accessed": receipt.protected_outcomes_accessed, "real_study_frozen": receipt.real_study_frozen}
    if operation == "prereg_missing_field":
        fields = prereg(config); del fields["dependence_plan"]
        return rejected(lambda: compile_preregistration(fields))
    if operation == "prereg_embargo_breached":
        fields = prereg(config); fields["outcome_access_embargo_manifest"]["protected_outcomes_accessed"] = True
        return rejected(lambda: compile_preregistration(fields))
    if operation == "prereg_contaminated_feasibility":
        fields = prereg(config); fields["feasibility_evidence"]["scope"] = "OUTCOME_EXPOSED_NONCONFIRMATORY"
        return rejected(lambda: compile_preregistration(fields))
    if operation == "prereg_nested_outcome_access":
        fields = prereg(config); fields["scientific_endpoint_manifest"]["protected_outcomes_accessed"] = True
        return rejected(lambda: compile_preregistration(fields))
    if operation == "prereg_adaptive_model":
        fields = prereg(config); fields["static_model_generation"]["mode"] = "ADAPTIVE"
        return rejected(lambda: compile_preregistration(fields))
    if operation == "prereg_receipt_firewall":
        compiled = compile_preregistration(prereg(config)); receipt = compiled.freeze_receipt
        return {"kind": "PASS", "status": compiled.status, "protected_outcomes_accessed": receipt.protected_outcomes_accessed, "real_study_frozen": receipt.real_study_frozen}

    if operation == "repository_adversarial_corpus":
        report = run_adversarial_corpus(ROOT / "fixtures/research_operations/sff/SFFI_WP6_ADVERSARIAL_CORPUS_v0_1.json")
        return {"kind": "PASS", "total": report["total"], "passed": report["passed"], "blocked": report["blocked"]}

    raise ValueError(f"unknown operation: {operation}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--expected", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    config = json.loads(args.input.read_text(encoding="utf-8"))
    expected_document = json.loads(args.expected.read_text(encoding="utf-8"))
    expectations = expected_document["expectations"]
    results = []
    for case in config["cases"]:
        observed = run_operation(case["operation"], config)
        expected = expectations[case["id"]]
        results.append({
            "case_id": case["id"],
            "dimension": case["dimension"],
            "expected": expected,
            "observed": observed,
            "result": "PASS" if observed == expected else "BLOCK",
        })
    output = {
        "schema": "ovc-sffi-g8-alg-independent-actual/v0.1",
        "review_id": config["review_id"],
        "reviewed_commit": config["reviewed_commit"],
        "total": len(results),
        "passed": sum(row["result"] == "PASS" for row in results),
        "blocked": sum(row["result"] == "BLOCK" for row in results),
        "results": results,
    }
    args.output.write_bytes(json.dumps(output, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n")
    print(json.dumps({key: output[key] for key in ("review_id", "reviewed_commit", "total", "passed", "blocked")}, sort_keys=True))
    return 1 if output["blocked"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
