from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence


REVIEW_SCHEMA_V2 = "ovc-pd-wp5-pilot-review-input/v2"
CORRECTION_LEDGER_SCHEMA = "ovc-pd-wp5-correction-ledger/v1"
CORRECTED_PROJECTION_SCHEMA = "ovc-pd-wp5-corrected-review-projection/v1"
OPERATOR_ID = "OVC.OPERATOR.PRIMARY.LOCAL.V1"
PILOT_RUN_ID = "PD.PILOT.RUN.0cc5a59ca751583f3e50091c"
PILOT_NAMESPACE = "PD.PILOT.GBPUSD.20260622_20260625.v1"

ALLOWED_REVIEW_DISPOSITIONS = {
    "WORKFLOW_ACCEPTED",
    "FLAG_WORKFLOW_DEFECT",
    "FLAG_UI_FRICTION",
    "DEFER_PILOT_OBJECT",
    "REJECT_PILOT_OBJECT",
}

PILOT_CORRECTION_SPECS: dict[str, dict[str, Any]] = {
    "PDPILOT-CANDIDATE-1ae851d7446f3934e18248dc": {
        "review_disposition": "DEFER_PILOT_OBJECT",
        "finding_code": "PD-DEFER-REVIEW-BASIS-INCOMPLETE-001",
        "affected_component": "PILOT_REVIEW_DECISION_CONTRACT",
        "actual_behavior": "The v1 review accepted a deferred disposition with free-text notes but no deterministic resolution criteria or next lawful review condition.",
        "expected_behavior": "A deferred object must identify a reason code, objective resolution criteria and a next lawful review condition.",
        "resolution_criteria": [
            "A structured reason code is present.",
            "At least one objective resolution criterion is present.",
            "A next lawful review condition is present."
        ],
        "next_review_condition": "Re-review after the v2 correction projection contains complete structured defer evidence.",
        "evidence_references": [
            "docs/releases/pattern-discovery-v0-3/pd-g5p/evidence/raw/pilot-review-receipt.json.b64",
            "docs/releases/pattern-discovery-v0-3/pd-g5p/evidence/raw/pilot-defect-ledger.json.b64"
        ],
        "acceptance_test_ids": ["PD-CORR1-DEFER-STRUCTURE-001"]
    },
    "PDPILOT-CANDIDATE-4c78ddd97117f06a0c6a1339": {
        "review_disposition": "REJECT_PILOT_OBJECT",
        "finding_code": "PD-REJECT-STRUCTURAL-BASIS-MISSING-001",
        "affected_component": "PILOT_REVIEW_DECISION_CONTRACT",
        "actual_behavior": "The v1 review accepted rejection without a reason code, structural basis or exact evidence references.",
        "expected_behavior": "A rejected pilot object must carry a deterministic reason code, a non-semantic structural or workflow basis and exact evidence references.",
        "structural_basis": "The rejection record lacks the structured basis required to distinguish workflow exclusion from semantic or outcome interpretation.",
        "evidence_references": [
            "docs/releases/pattern-discovery-v0-3/pd-g5p/evidence/raw/pilot-review-receipt.json.b64",
            "docs/releases/pattern-discovery-v0-3/pd-g5p/evidence/raw/pilot-defect-ledger.json.b64"
        ],
        "acceptance_test_ids": ["PD-CORR1-REJECT-STRUCTURE-001"]
    },
    "PDPILOT-CANDIDATE-bf1e96ba941e97a4d12e8fba": {
        "review_disposition": "FLAG_WORKFLOW_DEFECT",
        "finding_code": "PD-WF-STRUCTURED-DEFECT-EVIDENCE-MISSING-001",
        "affected_component": "pilot_discovery._validate_review",
        "actual_behavior": "The v1 validator accepted FLAG_WORKFLOW_DEFECT with notes only and did not require a defect code, affected component, reproduction steps, actual/expected behavior or acceptance criteria.",
        "expected_behavior": "Workflow-defect records fail closed unless every structured defect field and evidence reference is present.",
        "reproduction_steps": [
            "Submit a v1 review decision with FLAG_WORKFLOW_DEFECT.",
            "Provide notes and an empty ui_friction_codes array only.",
            "Observe that the v1 validator accepts and signs the decision."
        ],
        "acceptance_criteria": [
            "The v2 validator rejects a workflow defect without a PD-WF code.",
            "The v2 validator rejects a workflow defect without affected component, actual behavior, expected behavior, reproduction steps, evidence references or acceptance criteria.",
            "A complete structured workflow-defect decision is normalized deterministically."
        ],
        "evidence_references": [
            "schemas/research_operations/pattern_discovery/pd_wp5_pilot_review_input_v0_1.schema.json",
            "src/ovc/research_operations/pattern_discovery/pilot_discovery.py",
            "docs/releases/pattern-discovery-v0-3/pd-g5p/evidence/raw/pilot-review-receipt.json.b64"
        ],
        "acceptance_test_ids": ["PD-CORR1-WORKFLOW-FAIL-CLOSED-001"]
    },
    "PDPILOT-CANDIDATE-d724904c774d448919877dec": {
        "review_disposition": "DEFER_PILOT_OBJECT",
        "finding_code": "PD-DEFER-NEXT-CONDITION-MISSING-002",
        "affected_component": "PILOT_REVIEW_DECISION_CONTRACT",
        "actual_behavior": "The v1 review accepted a second deferred disposition without a reason code, resolution criteria or a bounded next review condition.",
        "expected_behavior": "Every deferred object must state the exact evidence condition that permits its next review.",
        "resolution_criteria": [
            "A structured defer reason is present.",
            "Resolution criteria are evidence-based and non-semantic.",
            "The next review condition does not imply promotion or replay authority."
        ],
        "next_review_condition": "Re-review only after the corrected evidence-presentation contract is verified against the preserved pilot projection.",
        "evidence_references": [
            "docs/releases/pattern-discovery-v0-3/pd-g5p/evidence/raw/pilot-review-receipt.json.b64",
            "docs/releases/pattern-discovery-v0-3/pd-g5p/evidence/raw/pilot-defect-ledger.json.b64"
        ],
        "acceptance_test_ids": ["PD-CORR1-DEFER-STRUCTURE-002"]
    },
    "PDPILOT-CANDIDATE-f10546a0a1ec4dfbe03545c4": {
        "review_disposition": "FLAG_UI_FRICTION",
        "finding_code": "PD-UI-REVIEW-CONTEXT-MISSING-001",
        "affected_component": "apps.research_console.pattern_discovery.render_candidate_detail",
        "affected_console_surface": "Candidate Detail / Review action candidate",
        "actual_behavior": "The v1 Console exposed generic observation and limitation text areas but no disposition-specific code, affected surface, reproduction, expected behavior or acceptance criterion fields.",
        "expected_behavior": "The Candidate Detail review panel presents disposition-specific structured fields while canonical append remains disabled.",
        "reproduction_steps": [
            "Open a Pilot Discovery candidate in Candidate Detail.",
            "Inspect the Review action candidate panel.",
            "Observe that only generic evidence class, observation and limitation fields are presented."
        ],
        "acceptance_criteria": [
            "Selecting FLAG_UI_FRICTION exposes a non-empty friction code field.",
            "The affected Console surface, actual behavior, expected behavior, reproduction steps, evidence references and acceptance criteria are visible.",
            "The Freeze evidence record control remains disabled without canonical append authority."
        ],
        "evidence_references": [
            "apps/research_console/pattern_discovery.py",
            "docs/releases/pattern-discovery-v0-3/pd-g5p/evidence/raw/pilot-review-receipt.json.b64"
        ],
        "acceptance_test_ids": ["PD-CORR1-CONSOLE-STRUCTURED-REVIEW-001"]
    }
}


class ReviewCorrectionError(ValueError):
    pass


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _required_text(source: Mapping[str, Any], field: str, code: str) -> str:
    value = str(source.get(field) or "").strip()
    if not value:
        raise ReviewCorrectionError(f"{code}:{field}")
    return value


def _required_strings(source: Mapping[str, Any], field: str, code: str) -> list[str]:
    value = source.get(field)
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ReviewCorrectionError(f"{code}:{field}")
    normalized = sorted({str(item).strip() for item in value if str(item).strip()})
    if not normalized:
        raise ReviewCorrectionError(f"{code}:{field}")
    return normalized


def required_fields_for_disposition(disposition: str) -> tuple[str, ...]:
    common = ("candidate_window_id", "review_disposition", "notes", "evidence_references")
    specific = {
        "WORKFLOW_ACCEPTED": ("acceptance_basis", "acceptance_criteria"),
        "FLAG_WORKFLOW_DEFECT": (
            "finding_code", "affected_component", "actual_behavior", "expected_behavior",
            "reproduction_steps", "acceptance_criteria"
        ),
        "FLAG_UI_FRICTION": (
            "finding_code", "affected_component", "affected_console_surface", "actual_behavior",
            "expected_behavior", "reproduction_steps", "acceptance_criteria", "ui_friction_codes"
        ),
        "DEFER_PILOT_OBJECT": ("finding_code", "resolution_criteria", "next_review_condition"),
        "REJECT_PILOT_OBJECT": ("finding_code", "structural_basis"),
    }
    if disposition not in specific:
        raise ReviewCorrectionError(f"INVALID_REVIEW_DISPOSITION:{disposition}")
    return common + specific[disposition]


def validate_review_decision_v2(source: Mapping[str, Any]) -> dict[str, Any]:
    disposition = _required_text(source, "review_disposition", "REVIEW_V2_MISSING")
    if disposition not in ALLOWED_REVIEW_DISPOSITIONS:
        raise ReviewCorrectionError(f"INVALID_REVIEW_DISPOSITION:{disposition}")
    candidate_id = _required_text(source, "candidate_window_id", "REVIEW_V2_MISSING")
    if not candidate_id.startswith("PDPILOT-CANDIDATE-"):
        raise ReviewCorrectionError(f"INVALID_CANDIDATE_ID:{candidate_id}")

    normalized: dict[str, Any] = {
        "candidate_window_id": candidate_id,
        "review_disposition": disposition,
        "notes": _required_text(source, "notes", "REVIEW_V2_MISSING"),
        "evidence_references": _required_strings(source, "evidence_references", "REVIEW_V2_MISSING"),
        "ui_friction_codes": sorted({str(item).strip() for item in source.get("ui_friction_codes", ()) if str(item).strip()}),
    }

    if disposition == "WORKFLOW_ACCEPTED":
        normalized["acceptance_basis"] = _required_text(source, "acceptance_basis", "ACCEPTED_REVIEW_INCOMPLETE")
        normalized["acceptance_criteria"] = _required_strings(source, "acceptance_criteria", "ACCEPTED_REVIEW_INCOMPLETE")
    elif disposition == "FLAG_WORKFLOW_DEFECT":
        finding_code = _required_text(source, "finding_code", "WORKFLOW_DEFECT_INCOMPLETE")
        if not finding_code.startswith("PD-WF-"):
            raise ReviewCorrectionError(f"INVALID_WORKFLOW_DEFECT_CODE:{finding_code}")
        normalized.update({
            "finding_code": finding_code,
            "affected_component": _required_text(source, "affected_component", "WORKFLOW_DEFECT_INCOMPLETE"),
            "actual_behavior": _required_text(source, "actual_behavior", "WORKFLOW_DEFECT_INCOMPLETE"),
            "expected_behavior": _required_text(source, "expected_behavior", "WORKFLOW_DEFECT_INCOMPLETE"),
            "reproduction_steps": _required_strings(source, "reproduction_steps", "WORKFLOW_DEFECT_INCOMPLETE"),
            "acceptance_criteria": _required_strings(source, "acceptance_criteria", "WORKFLOW_DEFECT_INCOMPLETE"),
        })
    elif disposition == "FLAG_UI_FRICTION":
        finding_code = _required_text(source, "finding_code", "UI_FRICTION_INCOMPLETE")
        if not finding_code.startswith("PD-UI-"):
            raise ReviewCorrectionError(f"INVALID_UI_FRICTION_CODE:{finding_code}")
        ui_codes = _required_strings(source, "ui_friction_codes", "UI_FRICTION_INCOMPLETE")
        if any(not code.startswith("PD-UI-") for code in ui_codes):
            raise ReviewCorrectionError("INVALID_UI_FRICTION_CODES")
        normalized.update({
            "finding_code": finding_code,
            "ui_friction_codes": ui_codes,
            "affected_component": _required_text(source, "affected_component", "UI_FRICTION_INCOMPLETE"),
            "affected_console_surface": _required_text(source, "affected_console_surface", "UI_FRICTION_INCOMPLETE"),
            "actual_behavior": _required_text(source, "actual_behavior", "UI_FRICTION_INCOMPLETE"),
            "expected_behavior": _required_text(source, "expected_behavior", "UI_FRICTION_INCOMPLETE"),
            "reproduction_steps": _required_strings(source, "reproduction_steps", "UI_FRICTION_INCOMPLETE"),
            "acceptance_criteria": _required_strings(source, "acceptance_criteria", "UI_FRICTION_INCOMPLETE"),
        })
    elif disposition == "DEFER_PILOT_OBJECT":
        finding_code = _required_text(source, "finding_code", "DEFER_REVIEW_INCOMPLETE")
        if not finding_code.startswith("PD-DEFER-"):
            raise ReviewCorrectionError(f"INVALID_DEFER_CODE:{finding_code}")
        normalized.update({
            "finding_code": finding_code,
            "resolution_criteria": _required_strings(source, "resolution_criteria", "DEFER_REVIEW_INCOMPLETE"),
            "next_review_condition": _required_text(source, "next_review_condition", "DEFER_REVIEW_INCOMPLETE"),
        })
    elif disposition == "REJECT_PILOT_OBJECT":
        finding_code = _required_text(source, "finding_code", "REJECT_REVIEW_INCOMPLETE")
        if not finding_code.startswith("PD-REJECT-"):
            raise ReviewCorrectionError(f"INVALID_REJECTION_CODE:{finding_code}")
        normalized.update({
            "finding_code": finding_code,
            "structural_basis": _required_text(source, "structural_basis", "REJECT_REVIEW_INCOMPLETE"),
        })

    return normalized


def validate_review_input_v2(
    review: Mapping[str, Any],
    *,
    expected_candidate_ids: Iterable[str],
    pilot_run_id: str,
    operator_id: str = OPERATOR_ID,
    pilot_markings: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if review.get("schema") != REVIEW_SCHEMA_V2:
        raise ReviewCorrectionError("INVALID_REVIEW_V2_SCHEMA")
    if review.get("pilot_run_id") != pilot_run_id:
        raise ReviewCorrectionError("REVIEW_V2_PILOT_ID_MISMATCH")
    if review.get("operator_id") != operator_id:
        raise ReviewCorrectionError("REVIEW_V2_OPERATOR_ID_MISMATCH")
    _required_text(review, "reviewed_at_utc", "REVIEW_V2_MISSING")
    decisions = review.get("decisions")
    if not isinstance(decisions, list):
        raise ReviewCorrectionError("REVIEW_V2_DECISIONS_NOT_LIST")

    expected = {str(item) for item in expected_candidate_ids}
    observed: set[str] = set()
    normalized: list[dict[str, Any]] = []
    markings = dict(pilot_markings or {})
    for source in decisions:
        if not isinstance(source, Mapping):
            raise ReviewCorrectionError("INVALID_REVIEW_V2_DECISION")
        item = validate_review_decision_v2(source)
        candidate_id = item["candidate_window_id"]
        if candidate_id not in expected or candidate_id in observed:
            raise ReviewCorrectionError(f"UNEXPECTED_OR_DUPLICATE_CANDIDATE:{candidate_id}")
        observed.add(candidate_id)
        normalized.append({**item, **markings})
    if observed != expected:
        raise ReviewCorrectionError(f"INCOMPLETE_REVIEW_V2:{sorted(expected - observed)}")
    return sorted(normalized, key=lambda item: item["candidate_window_id"])


def build_correction_ledger() -> dict[str, Any]:
    entries = [
        {"candidate_window_id": candidate_id, **PILOT_CORRECTION_SPECS[candidate_id]}
        for candidate_id in sorted(PILOT_CORRECTION_SPECS)
    ]
    body = {
        "schema": CORRECTION_LEDGER_SCHEMA,
        "packet_id": "PD-WP5-CORR1",
        "gate_id": "PD-G5P",
        "pilot_run_id": PILOT_RUN_ID,
        "pilot_namespace": PILOT_NAMESPACE,
        "source_review_receipt_file_sha256": "2486d9f7097c434fd52d4d5fd0cd086df8117887b6bf4b70a9ef6cf50869ab81",
        "source_defect_ledger_file_sha256": "a9e0102e042e3919871c7c0b135a60e4d3d27d8483f2e8eaa55fd366ee6d174d",
        "entries": entries,
        "entry_count": len(entries),
        "correction_scope": "VERSIONED_REVIEW_VALIDATION_AND_READ_ONLY_PRESENTATION_ONLY",
        "second_pilot_replay_recommendation": "NOT_REQUIRED",
        "second_pilot_replay_authorised": False,
        "canonical_discovery_authorised": False,
        "status": "CORRECTION_SPECIFICATION_COMPLETE",
    }
    return {**body, "ledger_sha256": canonical_sha256(body)}


def build_corrected_review_projection(review_receipt: Mapping[str, Any]) -> dict[str, Any]:
    if review_receipt.get("pilot_run_id") != PILOT_RUN_ID:
        raise ReviewCorrectionError("CORRECTION_SOURCE_PILOT_MISMATCH")
    decisions = review_receipt.get("decisions")
    if not isinstance(decisions, list):
        raise ReviewCorrectionError("CORRECTION_SOURCE_DECISIONS_INVALID")
    by_id = {str(item.get("candidate_window_id")): dict(item) for item in decisions if isinstance(item, Mapping)}
    if not set(PILOT_CORRECTION_SPECS).issubset(by_id):
        raise ReviewCorrectionError("CORRECTION_SOURCE_OBJECTS_MISSING")
    rows = []
    for candidate_id in sorted(PILOT_CORRECTION_SPECS):
        original = by_id[candidate_id]
        spec = PILOT_CORRECTION_SPECS[candidate_id]
        if original.get("review_disposition") != spec["review_disposition"]:
            raise ReviewCorrectionError(f"CORRECTION_DISPOSITION_MISMATCH:{candidate_id}")
        rows.append({
            "candidate_window_id": candidate_id,
            "original_review_disposition": original["review_disposition"],
            "original_notes": str(original.get("notes") or ""),
            "correction": spec,
            "pilot_only": True,
            "promotion_eligibility": "NON_PROMOTABLE",
            "canonical_append": "DENIED",
        })
    body = {
        "schema": CORRECTED_PROJECTION_SCHEMA,
        "packet_id": "PD-WP5-CORR1",
        "pilot_run_id": PILOT_RUN_ID,
        "pilot_namespace": PILOT_NAMESPACE,
        "rows": rows,
        "row_count": len(rows),
        "source_receipt_logical_sha256": canonical_sha256(review_receipt),
        "source_artifacts_mutated": False,
        "second_pilot_replay_required": False,
        "canonical_discovery_authorised": False,
        "status": "READ_ONLY_CORRECTION_PROJECTION_COMPLETE",
    }
    return {**body, "projection_sha256": canonical_sha256(body)}
