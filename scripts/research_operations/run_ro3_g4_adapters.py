from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

from ovc.research_operations.v0_3 import (
    DOWNSTREAM_AUTHORITY_BANNER,
    ProjectionContractError,
    ProjectionDenied,
    build_c1_console_projection,
    build_c1_fact_projection,
    build_c1_lineage_trace,
    build_downstream_trace_projection,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = ROOT / "fixtures/research_operations/v0_3/wp4_c1_lineage_projection_fixture.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _negative_control(
    name: str,
    expected_error: str,
    operation: Callable[[], Any],
) -> dict[str, Any]:
    try:
        operation()
    except (ProjectionDenied, ProjectionContractError) as exc:
        message = str(exc)
        passed = expected_error in message
        return {
            "name": name,
            "status": "PASS" if passed else "FAIL",
            "expected_error": expected_error,
            "actual_error": message,
        }
    return {
        "name": name,
        "status": "FAIL",
        "expected_error": expected_error,
        "actual_error": "NO_ERROR",
    }


def build_evidence() -> dict[str, Any]:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    context = fixture["release_context"]
    record = fixture["c1_record"]
    lineage = build_c1_lineage_trace(release_context=context, c1_record=record)
    fact = build_c1_fact_projection(
        release_context=context,
        c1_record=record,
        formula_evidence=fixture["formula_evidence"],
        lineage_trace=lineage,
    )
    downstream = build_downstream_trace_projection(
        c1_record_id=record["record_id"],
        child_references=fixture["child_references"],
    )
    console = build_c1_console_projection(
        release_context=context,
        fact_projection=fact,
        computability_projection=fixture["computability_projection"],
        assurance_projection=fixture["assurance_projection"],
        lineage_trace=lineage,
        downstream_trace=downstream,
    )

    empty_downstream = build_downstream_trace_projection(
        c1_record_id=record["record_id"],
        child_references=[],
    )
    stale_fixture = deepcopy(fixture)
    stale_fixture["release_context"]["represented_commit"] = "stale-represented-commit"
    stale_lineage = build_c1_lineage_trace(
        release_context=stale_fixture["release_context"],
        c1_record=stale_fixture["c1_record"],
    )
    stale_fact = build_c1_fact_projection(
        release_context=stale_fixture["release_context"],
        c1_record=stale_fixture["c1_record"],
        formula_evidence=stale_fixture["formula_evidence"],
        lineage_trace=stale_lineage,
    )
    stale_downstream = build_downstream_trace_projection(
        c1_record_id=stale_fixture["c1_record"]["record_id"],
        child_references=stale_fixture["child_references"],
    )
    stale_console = build_c1_console_projection(
        release_context=stale_fixture["release_context"],
        fact_projection=stale_fact,
        computability_projection=stale_fixture["computability_projection"],
        assurance_projection=stale_fixture["assurance_projection"],
        lineage_trace=stale_lineage,
        downstream_trace=stale_downstream,
    )

    write_fixture = deepcopy(fixture)
    write_fixture["computability_projection"]["git_write"] = True
    mixed_fixture = deepcopy(fixture)
    mixed_fixture["formula_evidence"]["c2_transition"] = "FORBIDDEN"
    validation_fixture = {"role": "VALIDATION", "path": "must-not-resolve"}
    scored_child = deepcopy(fixture["child_references"][0])
    scored_child["confidence"] = "FORBIDDEN"
    route_attempt = deepcopy(fixture)
    route_attempt["release_context"]["activate"] = True

    negative_controls = [
        _negative_control(
            "validation_denied_before_resolution",
            "VALIDATION_DENY_BEFORE_PATH_OBJECT_OR_RECORD_RESOLUTION",
            lambda: build_c1_lineage_trace(
                release_context=validation_fixture,
                c1_record={"path": "must-not-resolve"},
            ),
        ),
        _negative_control(
            "write_capable_console_payload",
            "READ_ONLY_PROJECTION_REQUIRED",
            lambda: build_c1_console_projection(
                release_context=write_fixture["release_context"],
                fact_projection=fact,
                computability_projection=write_fixture["computability_projection"],
                assurance_projection=write_fixture["assurance_projection"],
                lineage_trace=lineage,
                downstream_trace=downstream,
            ),
        ),
        _negative_control(
            "mixed_c1_fact_and_c2_transition",
            "FACT_PANEL_MIXED_WITH_DOWNSTREAM_AUTHORITY",
            lambda: build_c1_fact_projection(
                release_context=mixed_fixture["release_context"],
                c1_record=mixed_fixture["c1_record"],
                formula_evidence=mixed_fixture["formula_evidence"],
                lineage_trace=lineage,
            ),
        ),
        _negative_control(
            "downstream_scoring_language",
            "DOWNSTREAM_TRACE_PROHIBITED_PRESENTATION",
            lambda: build_downstream_trace_projection(
                c1_record_id=record["record_id"],
                child_references=[scored_child],
            ),
        ),
        _negative_control(
            "route_activation_before_rc_g4",
            "READ_ONLY_PROJECTION_REQUIRED",
            lambda: build_c1_lineage_trace(
                release_context=route_attempt["release_context"],
                c1_record=route_attempt["c1_record"],
            ),
        ),
    ]

    assertions = {
        "lineage_complete": lineage["status"] == "COMPLETE",
        "lineage_read_only": lineage["authority"] == "READ_ONLY_TRACE" and lineage["writes"] == "NONE",
        "fact_exact_wick_balance": fact["output"] == "-0.1428571428571428571428571428571429",
        "fact_and_downstream_separate": fact["panel_id"] != downstream["panel_id"],
        "permanent_banner_exact": downstream["banner"] == DOWNSTREAM_AUTHORITY_BANNER,
        "downstream_authority_unchanged": downstream["c2_authority"] == "UNCHANGED" and downstream["pattern_discovery_authority"] == "UNCHANGED",
        "missing_trace_explicit": empty_downstream["status"] == "TRACE_NOT_AVAILABLE",
        "route_disabled": console["route_state"] == "DISABLED_PENDING_RC_G4" and console["route_enabled"] is False,
        "live_authority_absent": console["live_consumption_authority"] == "NONE_PENDING_RC_G4",
        "validation_locked": console["validation_consumption"] == "LOCKED_UNCONSUMED",
        "stale_projection_explicit": stale_console["status"] == "STALE_PROJECTION" and stale_console["route_enabled"] is False,
        "no_writes": console["writes"] == "NONE" and console["read_only"] is True,
        "negative_controls_detected": all(item["status"] == "PASS" for item in negative_controls),
    }
    status = "PASS" if all(assertions.values()) else "BLOCK"
    return {
        "schema": "ovc-ro3-g4-adapter-evidence/v1",
        "packet_id": "RO3-WP4",
        "gate_id": "RO3-G4",
        "fixture": {
            "path": FIXTURE_PATH.relative_to(ROOT).as_posix(),
            "sha256": _sha(FIXTURE_PATH),
        },
        "projection": console,
        "lineage_trace": lineage,
        "fact_projection": fact,
        "downstream_trace": downstream,
        "empty_downstream_trace": empty_downstream,
        "stale_projection": stale_console,
        "negative_controls": negative_controls,
        "assertions": assertions,
        "status": status,
        "qa_recommendation": "PASS" if status == "PASS" else "BLOCK",
        "authority_delta": "LOCAL_READ_ONLY_PRESENTATION_ADAPTERS",
        "live_route": "DISABLED_PENDING_RC_G4",
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
        "projection_id": evidence["projection"]["projection_id"],
        "lineage_trace_id": evidence["lineage_trace"]["trace_id"],
        "negative_controls": evidence["negative_controls"],
        "output": str(args.output),
    }, indent=2, sort_keys=True))
    return 1 if args.require_pass and evidence["status"] != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
