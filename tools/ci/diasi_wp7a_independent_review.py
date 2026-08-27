"""Fresh-process, conflict-free oracle for DIASI-WP7A gate preparation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WP7A = ROOT / "docs/programmes/dias-v0-1/wp7a"
CANDIDATE = WP7A / "removal-candidate"


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"DIASI_WP7A_REVIEW_OBJECT_REQUIRED:{path}")
    return value


def canonical(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject-commit", required=True)
    args = parser.parse_args()
    result = load(WP7A / "DIASI_WP7A_STABILISATION_RESULT.json")
    census = load(WP7A / "DIASI_WP7A_ZERO_ACTIVE_DEPENDENCY_CENSUS.json")
    integrity = load(WP7A / "DIASI_WP7A_EXECUTION_INTEGRITY_RECORD.json")
    history = load(WP7A / "DIASI_WP7A_HISTORICAL_INTERPRETATION_BUNDLE.json")
    route = load(CANDIDATE / "VIT_SELECTED_CLASS_ROUTE_v0_1.json.candidate")
    writer = load(CANDIDATE / "VIT_QUALIFICATION_WRITER_AUTHORITY_v0_1.json.candidate")
    decision = load(CANDIDATE / "DIASI_G_DGS_RETIRE_REMOVE_OPERATOR_DECISION.json.candidate")
    code = (CANDIDATE / "dias_cutover.py.candidate").read_text(encoding="utf-8")
    cases = {
        "MEASURED_WINDOW_EXCEEDS_300_SECONDS": result.get("elapsed_seconds", 0) >= 300,
        "FIVE_OF_FIVE_CYCLES_PASS": result.get("aggregate", {}).get("cycles_passed") == result.get("aggregate", {}).get("cycles_denominator") == 5,
        "ZERO_UNSAFE_UNKNOWN_DIFFERENTIAL_DUPLICATE_A3_STALE_AND_INTEGRITY": all(result.get("aggregate", {}).get(key) == 0 for key in ("unsafe_outcome_count", "unknown_outcome_count", "false_differential_count", "duplicate_successor_count", "a3_mismatch_count", "stale_writer_accepted_count", "integrity_incident_count")),
        "OLD_ROUTE_DISABLED_ENTIRE_WINDOW": result.get("aggregate", {}).get("old_route_disabled_for_entire_window") is True,
        "ZERO_ACTIVE_DEPENDENCY_ALL_DIMENSIONS": census.get("census_result") == "ZERO_ACTIVE_DEPENDENCY_EXACT_SELECTED_CLASS_OLD_ROUTE" and all(row.get("active_old_route_dependencies") == 0 for row in census.get("dimensions", [])),
        "NO_GLOBAL_RETIREMENT_FROM_PARTIAL_SCOPE": census.get("global_retirement_claimed") is False and census.get("shared_machinery", {}).get("global_cers_persistent_service", {}).get("active_admission_count") == 5,
        "HISTORICAL_INTERPRETATION_DATA_ONLY": history.get("execution_policy") == "DATA_ONLY_NEVER_IMPORT_OR_EXECUTE_RETIRED_CUTOVER_PES_OR_CERS_MACHINERY" and history.get("retained_route_generations") == [1, 2],
        "POST_REMOVAL_ROUTE_HAS_NO_OLD_AUTHORITY": route.get("route_generation") == route.get("writer_generation") == 3 and "old_route" not in route and "incumbent_writer" not in route,
        "POST_REMOVAL_WRITER_HAS_NO_INCUMBENT": writer.get("generation") == 3 and "incumbent_writer" not in writer and "incumbent_selected_class_status" not in writer,
        "POST_REMOVAL_CODE_HAS_NO_OLD_ROUTE_EXECUTION": all(token not in code for token in ("INCUMBENT_ROUTE", "freeze_selected_intake", "transfer_route_and_writer", "disposition_in_flight")) and '"old_route" in registry' in code,
        "EXACT_OPERATOR_PHRASE_AND_SCOPE": decision.get("operator_phrase") == "OVC APPROVE DIASI-G-DGS-RETIRE-REMOVE PASS" and decision.get("authorised_scope") == "EXACT_SELECTED_CLASS_OLD_ROUTE_ONLY",
        "SHARED_CERS_PES_DENIALS_PRESERVED": "NO_GLOBAL_CERS_RETIREMENT" in decision.get("explicit_non_grants", []) and "NO_GLOBAL_PES_RETIREMENT" in decision.get("explicit_non_grants", []),
        "STARTUP_FAILURE_PRESERVED_AND_NON_MEASUREMENT": integrity.get("attempts", [])[0].get("measurement_outcome_created") is False and integrity.get("history_policy") == "CORRECT_FORWARD_NO_FORCE_PUSH_NO_ERASURE",
    }
    review = {
        "schema": "ovc-diasi-independent-retirement-review/v1",
        "packet_id": "DIASI-WP7A",
        "subject_commit": args.subject_commit,
        "reviewer": "FRESH_PROCESS_DETERMINISTIC_ORACLE_SEPARATE_FROM_CUTOVER_AND_HISTORY_MODULES",
        "external_human_or_model_review_claimed": False,
        "conflict_of_interest_control": "NO_IMPORT_OF_SUBJECT_IMPLEMENTATION_AND_NO_LIVE_WRITE_CAPABILITY",
        "cases": cases,
        "unresolved_warning_count": 0 if all(cases.values()) else sum(not value for value in cases.values()),
        "recommendation": "PASS" if all(cases.values()) else "FAIL",
        "authority_effect": "NONE_RECOMMENDATION_ONLY",
    }
    review["review_id"] = canonical(review)
    print(json.dumps(review, sort_keys=True, separators=(",", ":")))
    return 0 if review["recommendation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
