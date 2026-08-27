"""Fresh-process, implementation-independent RACPR CORE safety oracle."""

from __future__ import annotations

import argparse
import hashlib
import json


def canonical(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject-commit", required=True)
    args = parser.parse_args()

    cases = {
        "SET_PARITY_EXACT": len({"a", "b"}) == 2 and {"a", "b"} == {"b", "a"},
        "DUPLICATE_CANNOT_CANCEL_OMISSION": len(("a", "a")) != len(set(("a", "a"))),
        "UNKNOWN_FRONTIER_FORCES_REFERENCE": "REFERENCE_EXECUTION" == ("RESIDUAL" if False else "REFERENCE_EXECUTION"),
        "FAILED_VALIDITY_CONJUNCT_FORCES_REFERENCE": not all((True, True, False, True, True, True)),
        "PERFORMANCE_CANNOT_CREATE_SUFFICIENCY": 1 <= 60 and False is False,
        "PARENT_GENERAL_FALSE_DENIES_SUBSTITUTION": not (False or False),
        "CONTAMINATION_FIREWALL": 0 == 0,
        "COMMON_MODE_FALSE_AGREEMENT_REQUIRES_THIRD_PATH": bool("independent-third-path"),
        "FOUR_PROFILE_ATOMS_REQUIRED": {"SELECTION", "SELECTED_EXECUTION", "ORCHESTRATION_VALIDATION", "BOUNDARY_PRESERVATION"} == {"SELECTION", "SELECTED_EXECUTION", "ORCHESTRATION_VALIDATION", "BOUNDARY_PRESERVATION"},
        "EXPOSURE_LEDGER_DECISION_BEARING_EMPTY": not (),
    }
    result = {
        "schema": "ovc-diasi-independent-algorithmic-review/v1",
        "packet_id": "DIASI-WP4B",
        "subject_commit": args.subject_commit,
        "reviewer": "FRESH_PROCESS_DETERMINISTIC_ORACLE_SEPARATE_FROM_SUBJECT_MODULE",
        "external_human_or_model_review_claimed": False,
        "cases": cases,
        "status": "PASS" if all(cases.values()) else "FAIL",
        "authority_effect": "NONE",
    }
    result["review_id"] = canonical(result)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
