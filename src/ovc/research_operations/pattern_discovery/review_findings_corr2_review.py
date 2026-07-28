from __future__ import annotations

from typing import Any, Mapping, Sequence

from . import pilot_discovery as pilot
from .review_findings_corr2_model import (
    PACKET_ID,
    RETURN_GATE,
    EXPECTED_RUN_ID,
    EXPECTED_NAMESPACE,
    REVIEW_INPUT_SCHEMA,
    CLOSURE_LEDGER_SCHEMA,
    DEFERRED_FINDINGS,
    FINAL_DISPOSITIONS,
    Corr2Error,
    _require_text,
    _require_strings,
    parse_evidence_reference,
)

def build_rereview_template(contexts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "schema": REVIEW_INPUT_SCHEMA,
        "packet_id": PACKET_ID,
        "pilot_run_id": EXPECTED_RUN_ID,
        "operator_id": pilot.OPERATOR_ID,
        "reviewed_at_utc": "REPLACE_WITH_UTC_TIMESTAMP_ENDING_Z",
        "decisions": [
            {
                "candidate_window_id": str(context["candidate_window_id"]),
                "source_finding_code": str(context["source_finding_code"]),
                "review_disposition": "REPLACE_WITH_WORKFLOW_ACCEPTED_OR_REJECT_PILOT_OBJECT",
                "closure_code": "PD-CORR2-REPLACE-WITH-CODE",
                "decision_basis": "REPLACE_WITH_NON_SEMANTIC_DECISION_BASIS",
                "closure_criteria": ["REPLACE_WITH_VERIFIED_CLOSURE_CRITERION"],
                "notes": "REPLACE_WITH_NONEMPTY_OPERATOR_NOTES",
                "evidence_references": list(context["evidence_references"]),
            }
            for context in contexts
        ],
    }


def validate_rereview_input(review: Mapping[str, Any], contexts: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if review.get("schema") != REVIEW_INPUT_SCHEMA:
        raise Corr2Error("INVALID_CORR2_REREVIEW_SCHEMA")
    if review.get("packet_id") != PACKET_ID or review.get("pilot_run_id") != EXPECTED_RUN_ID:
        raise Corr2Error("CORR2_REREVIEW_IDENTITY_MISMATCH")
    if review.get("operator_id") != pilot.OPERATOR_ID:
        raise Corr2Error("CORR2_OPERATOR_ID_MISMATCH")
    reviewed_at = _require_text(review, "reviewed_at_utc", "CORR2_REVIEW_MISSING")
    if not reviewed_at.endswith("Z"):
        raise Corr2Error("CORR2_REVIEWED_AT_MUST_END_Z")
    source = review.get("decisions")
    if not isinstance(source, list):
        raise Corr2Error("CORR2_DECISIONS_NOT_LIST")
    expected = {str(item["candidate_window_id"]): item for item in contexts}
    observed: dict[str, dict[str, Any]] = {}
    for item in source:
        if not isinstance(item, Mapping):
            raise Corr2Error("INVALID_CORR2_DECISION")
        candidate_id = _require_text(item, "candidate_window_id", "CORR2_DECISION_MISSING")
        if candidate_id not in expected or candidate_id in observed:
            raise Corr2Error(f"UNEXPECTED_OR_DUPLICATE_CORR2_CANDIDATE:{candidate_id}")
        if item.get("source_finding_code") != DEFERRED_FINDINGS[candidate_id]:
            raise Corr2Error(f"CORR2_SOURCE_FINDING_MISMATCH:{candidate_id}")
        disposition = _require_text(item, "review_disposition", "CORR2_DECISION_MISSING")
        if disposition not in FINAL_DISPOSITIONS:
            raise Corr2Error(f"CORR2_FINAL_DISPOSITION_REQUIRED:{candidate_id}:{disposition}")
        closure_code = _require_text(item, "closure_code", "CORR2_DECISION_MISSING")
        if not closure_code.startswith("PD-CORR2-"):
            raise Corr2Error(f"INVALID_CORR2_CLOSURE_CODE:{closure_code}")
        references = _require_strings(item, "evidence_references", "CORR2_DECISION_MISSING")
        expected_refs = set(expected[candidate_id]["evidence_references"])
        if not set(references).issubset(expected_refs):
            raise Corr2Error(f"UNRESOLVED_OR_UNAUTHORISED_REFERENCE:{candidate_id}")
        required_paths = {"review/queue-items.jsonl", "review/console-bundle.json", "derived/fingerprints.jsonl"}
        resolved_paths = {parse_evidence_reference(reference)[0] for reference in references}
        if not required_paths.issubset(resolved_paths):
            raise Corr2Error(f"CORR2_REQUIRED_CONTEXT_MISSING:{candidate_id}")
        observed[candidate_id] = {
            "candidate_window_id": candidate_id,
            "source_finding_code": DEFERRED_FINDINGS[candidate_id],
            "review_disposition": disposition,
            "closure_code": closure_code,
            "decision_basis": _require_text(item, "decision_basis", "CORR2_DECISION_MISSING"),
            "closure_criteria": _require_strings(item, "closure_criteria", "CORR2_DECISION_MISSING"),
            "notes": _require_text(item, "notes", "CORR2_DECISION_MISSING"),
            "evidence_references": references,
            "research_role": pilot.RESEARCH_ROLE,
            "operation_mode": pilot.OPERATION_MODE,
            "pilot_only": True,
            "promotion_eligibility": "NON_PROMOTABLE",
            "canonical_discovery_population": False,
            "canonical_append": "DENIED",
            "semantic_interpretation": "DENIED",
            "later_outcome_use": "DENIED",
            "identity_namespace": EXPECTED_NAMESPACE,
        }
    if set(observed) != set(expected):
        raise Corr2Error(f"INCOMPLETE_CORR2_REREVIEW:{sorted(set(expected) - set(observed))}")
    return [observed[key] for key in sorted(observed)]


def build_closure_ledger(decisions: Sequence[Mapping[str, Any]], *, receipt_sha256: str) -> dict[str, Any]:
    if {str(item.get("candidate_window_id")) for item in decisions} != set(DEFERRED_FINDINGS):
        raise Corr2Error("CORR2_CLOSURE_DECISION_SET_INVALID")
    findings = [
        {
            "finding_code": "PD-WF-STRUCTURED-REVIEW-EVIDENCE-MISSING-001",
            "status": "CLOSED_BY_CORR2_FAIL_CLOSED_VALIDATOR_AND_TESTS",
            "closure_evidence": [
                "src/ovc/research_operations/pattern_discovery/review_corrections.py",
                "tests/research_operations/pattern_discovery/test_c1c_g5_corr2.py",
            ],
        },
        {
            "finding_code": "PD-UI-STRUCTURED-REVIEW-CONTEXT-MISSING-001",
            "status": "CLOSED_BY_CORR2_READ_ONLY_CONSOLE_CONTEXT",
            "closure_evidence": [
                "apps/research_console/pattern_discovery.py",
                "src/ovc/research_operations/pattern_discovery/review_findings_corr2.py",
                "tests/research_operations/pattern_discovery/test_c1c_g5_corr2.py",
            ],
        },
    ]
    findings.extend({
        "finding_code": str(item["source_finding_code"]),
        "candidate_window_id": str(item["candidate_window_id"]),
        "status": "CLOSED_BY_OPERATOR_CORR2_REREVIEW",
        "final_disposition": str(item["review_disposition"]),
        "closure_code": str(item["closure_code"]),
        "evidence_references": list(item["evidence_references"]),
    } for item in decisions)
    body = {
        "schema": CLOSURE_LEDGER_SCHEMA,
        "packet_id": PACKET_ID,
        "gate_id": RETURN_GATE,
        "pilot_run_id": EXPECTED_RUN_ID,
        "pilot_namespace": EXPECTED_NAMESPACE,
        "source_rereview_receipt_file_sha256": receipt_sha256,
        "findings": findings,
        "finding_count": len(findings),
        "unresolved_finding_count": 0,
        "contract_changes_required": False,
        "accepted_object_preserved": "PDPILOT-CANDIDATE-622511909d36a69adc34fa4f",
        "rejected_negative_control_preserved": "PDPILOT-CANDIDATE-5bb7163e87d9b8521a1e235e",
        "second_machine_replay_required": False,
        "pilot_only": True,
        "promotion_eligibility": "NON_PROMOTABLE",
        "canonical_append": "DENIED",
        "status": "C1C_G5_CORR2_FINDINGS_CLOSED_RETURN_GATE_READY",
    }
    return {**body, "ledger_sha256": pilot.logical_sha(body)}


