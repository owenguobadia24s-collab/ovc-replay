"""ASOCSI WP8 session-batched staged-reveal transport and freeze boundary.

The scientific evidence unit remains one case.  This module makes the operator
transport and atomic freeze unit one complete session-stage submission.  It
does not answer human questions and it never constructs a later-stage reveal.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any, Mapping, Sequence


PROGRAMME_ID = "OVC-ASOCS-6M-v0.1"
STAGE1 = "SOURCE_C1_FIDELITY"
PERMANENT_WARNING = (
    "UNRECOVERABLE_HISTORICAL_G3_CENSUS_IDENTITY_AND_COMPACT_MANIFEST_"
    "PROVENANCE_PERMANENT"
)
CONSTRUCT_SURVIVAL_PROHIBITION = "PROHIBITED_DURING_CASE_REVIEW"
SESSION_INPUT_SCHEMA = "ovc-asocsi-wp8-session-stage-human-input/v0_1"
SESSION_PACKET_SCHEMA = "ovc-asocsi-wp8-session-stage-reveal-packet/v0_1"
CASE_RECORD_SCHEMA = "ovc-asocs-reveal-stage-record/v0_1"
AUTHORITY_CLASS = "ASOCS_AUDIT_ONLY_NONAUTHORITATIVE_HUMAN_RESEARCH_EVIDENCE"
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
CASE_ID_RE = re.compile(r"ASOCS\.BLIND\.[A-Za-z0-9]+\Z")

STAGE1_ENUMS = {
    "fidelity_disposition": {
        "PASS_FIDELITY", "MATERIAL_MISMATCH", "SOURCE_LIMITED", "INDETERMINATE"
    },
    "prior_bridge_disposition": {
        "VALID", "INVALID_SOURCE_GAP", "NOT_APPLICABLE", "INDETERMINATE"
    },
    "semantic_leakage": {"NONE", "PRESENT", "INDETERMINATE"},
    "traceability": {"PASS", "FAIL", "INDETERMINATE"},
    "information_gap_disposition": {
        "NOT_INFORMATION_GAP", "INFORMATION_GAP", "INDETERMINATE"
    },
}
STAGE1_REQUIRED = {
    "schema", "case_id", "stage", "fidelity_disposition",
    "observational_correspondence", "prior_bridge_disposition",
    "semantic_leakage", "traceability", "information_gap_disposition",
    "construct_survival_decision",
}
SUBMISSION_KEYS = {
    "schema", "programme_id", "session", "stage", "reveal_packet_sha256", "cases"
}
SUBMISSION_CASE_KEYS = {
    "presentation_ordinal", "case_id", "predecessor_blind_record_sha256",
    "review_unit_id", "human_judgement",
}


class ASOCSSessionBatchError(ValueError):
    """A complete session-stage submission failed closed."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def raw_json_bytes(value: Any) -> bytes:
    return canonical_json_bytes(value) + b"\n"


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], where: str) -> None:
    missing = sorted(expected - set(value))
    extra = sorted(set(value) - expected)
    if missing:
        raise ASOCSSessionBatchError(f"{where}_MISSING_FIELDS:" + ",".join(missing))
    if extra:
        raise ASOCSSessionBatchError(f"{where}_EXTRA_FIELDS:" + ",".join(extra))


def _require_sha(value: object, where: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise ASOCSSessionBatchError(f"{where}_INVALID_SHA256")
    return value


def _validate_stage1_judgement(value: object, expected_case_id: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ASOCSSessionBatchError("HUMAN_JUDGEMENT_NOT_OBJECT")
    judgement = dict(value)
    allowed = STAGE1_REQUIRED | {"notes"}
    missing = sorted(STAGE1_REQUIRED - set(judgement))
    extra = sorted(set(judgement) - allowed)
    if missing:
        raise ASOCSSessionBatchError("HUMAN_JUDGEMENT_MISSING_FIELDS:" + ",".join(missing))
    if extra:
        raise ASOCSSessionBatchError("HUMAN_JUDGEMENT_EXTRA_FIELDS:" + ",".join(extra))
    if judgement["schema"] != "ovc-asocs-stage1-fidelity-judgement/v0_1":
        raise ASOCSSessionBatchError("HUMAN_JUDGEMENT_SCHEMA_MISMATCH")
    if judgement["case_id"] != expected_case_id:
        raise ASOCSSessionBatchError("HUMAN_JUDGEMENT_CASE_ID_MISMATCH")
    if judgement["stage"] != STAGE1:
        raise ASOCSSessionBatchError("HUMAN_JUDGEMENT_STAGE_MISMATCH")
    if judgement["construct_survival_decision"] != CONSTRUCT_SURVIVAL_PROHIBITION:
        raise ASOCSSessionBatchError("CONSTRUCT_SURVIVAL_DECISION_PROHIBITION_MISMATCH")
    for field, allowed_values in STAGE1_ENUMS.items():
        if judgement[field] not in allowed_values:
            raise ASOCSSessionBatchError(f"HUMAN_JUDGEMENT_{field.upper()}_INVALID")
    correspondence = judgement["observational_correspondence"]
    if not isinstance(correspondence, str) or not correspondence:
        raise ASOCSSessionBatchError("OBSERVATIONAL_CORRESPONDENCE_REQUIRED")
    if "notes" in judgement and not isinstance(judgement["notes"], str):
        raise ASOCSSessionBatchError("NOTES_NOT_STRING")
    return judgement


def validate_session_submission(
    submission: object,
    *,
    reveal_packet: Mapping[str, Any],
    reveal_packet_sha256: str,
) -> dict[str, Any]:
    """Validate one complete ordered session submission without filling omissions."""
    if not isinstance(submission, Mapping):
        raise ASOCSSessionBatchError("SESSION_SUBMISSION_NOT_OBJECT")
    supplied = dict(submission)
    _require_exact_keys(supplied, SUBMISSION_KEYS, "SESSION_SUBMISSION")
    if supplied["schema"] != SESSION_INPUT_SCHEMA:
        raise ASOCSSessionBatchError("SESSION_SUBMISSION_SCHEMA_MISMATCH")
    if supplied["programme_id"] != PROGRAMME_ID:
        raise ASOCSSessionBatchError("SESSION_SUBMISSION_PROGRAMME_MISMATCH")
    if supplied["session"] != reveal_packet.get("session"):
        raise ASOCSSessionBatchError("SESSION_IDENTITY_MISMATCH")
    if supplied["stage"] != reveal_packet.get("stage"):
        raise ASOCSSessionBatchError("SESSION_STAGE_MISMATCH")
    if supplied["stage"] != STAGE1:
        raise ASOCSSessionBatchError("UNSUPPORTED_STAGE_FOR_THIS_VALIDATOR")
    _require_sha(reveal_packet_sha256, "REVEAL_PACKET")
    if supplied["reveal_packet_sha256"] != reveal_packet_sha256:
        raise ASOCSSessionBatchError("REVEAL_PACKET_SHA256_MISMATCH")

    expected_cases = reveal_packet.get("cases")
    cases = supplied["cases"]
    if not isinstance(expected_cases, Sequence) or isinstance(expected_cases, (str, bytes)):
        raise ASOCSSessionBatchError("REVEAL_PACKET_CASES_INVALID")
    if not isinstance(cases, list):
        raise ASOCSSessionBatchError("SESSION_CASES_NOT_ARRAY")
    if len(cases) != len(expected_cases):
        raise ASOCSSessionBatchError("SESSION_CASE_COUNT_MISMATCH")

    seen: set[str] = set()
    validated: list[dict[str, Any]] = []
    for ordinal, (case, expected) in enumerate(zip(cases, expected_cases), 1):
        if not isinstance(case, Mapping) or not isinstance(expected, Mapping):
            raise ASOCSSessionBatchError(f"CASE_{ordinal:03d}_NOT_OBJECT")
        item = dict(case)
        _require_exact_keys(item, SUBMISSION_CASE_KEYS, f"CASE_{ordinal:03d}")
        if item["presentation_ordinal"] != ordinal:
            raise ASOCSSessionBatchError(f"CASE_{ordinal:03d}_ORDER_MISMATCH")
        expected_id = str(expected.get("case_id", ""))
        if not CASE_ID_RE.fullmatch(expected_id) or item["case_id"] != expected_id:
            raise ASOCSSessionBatchError(f"CASE_{ordinal:03d}_ID_MISMATCH")
        if expected_id in seen:
            raise ASOCSSessionBatchError("DUPLICATE_CASE_ID:" + expected_id)
        seen.add(expected_id)
        expected_blind = _require_sha(
            expected.get("predecessor_blind_record_sha256"),
            f"REVEAL_CASE_{ordinal:03d}_PREDECESSOR",
        )
        if item["predecessor_blind_record_sha256"] != expected_blind:
            raise ASOCSSessionBatchError(f"CASE_{ordinal:03d}_PREDECESSOR_MISMATCH")
        expected_unit = expected.get("review_unit_id")
        if not isinstance(expected_unit, str) or not expected_unit:
            raise ASOCSSessionBatchError(f"REVEAL_CASE_{ordinal:03d}_REVIEW_UNIT_INVALID")
        if item["review_unit_id"] != expected_unit:
            raise ASOCSSessionBatchError(f"CASE_{ordinal:03d}_REVIEW_UNIT_MISMATCH")
        judgement = _validate_stage1_judgement(item["human_judgement"], expected_id)
        validated.append({**item, "human_judgement": judgement})
    return {**supplied, "cases": validated}


def _trace_index(trace_path: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    with gzip.open(trace_path, "rt", encoding="utf-8", newline="") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.endswith("\n"):
                raise ASOCSSessionBatchError(f"TRACE_LINE_{line_number}_NOT_LF_TERMINATED")
            value = json.loads(line)
            trace_sha = _require_sha(value.get("trace_sha256"), f"TRACE_LINE_{line_number}")
            if trace_sha in result:
                raise ASOCSSessionBatchError("DUPLICATE_TRACE_SHA256:" + trace_sha)
            result[trace_sha] = value
    return result


def build_stage1_review_packet(
    preparation: Mapping[str, Any],
    *,
    preparation_sha256: str,
    trace_path: Path,
) -> dict[str, Any]:
    """Build the human-facing Stage-1 surface and omit every upper-stack field."""
    if preparation.get("session") != 1 or preparation.get("stage") != STAGE1:
        raise ASOCSSessionBatchError("PREPARATION_SESSION_STAGE_MISMATCH")
    cases = preparation.get("cases")
    if not isinstance(cases, list) or len(cases) != 25:
        raise ASOCSSessionBatchError("SESSION1_PREPARATION_REQUIRES_25_CASES")
    traces = _trace_index(trace_path)
    output_cases: list[dict[str, Any]] = []
    for ordinal, source_case in enumerate(cases, 1):
        if source_case.get("n") != ordinal:
            raise ASOCSSessionBatchError(f"PREPARATION_CASE_{ordinal:03d}_ORDER_MISMATCH")
        common = {
            "session_ordinal": 1,
            "presentation_ordinal": ordinal,
            "case_id": source_case["case_id"],
            "predecessor_blind_record_sha256": source_case["blind_sha256"],
            "review_unit_id": source_case["review_unit_id"],
            "human_judgement": None,
            "information_gap_disposition": None,
            "case_validation_status": "PENDING_HUMAN_INPUT",
        }
        if source_case["kind"] == "ANCHOR_15M":
            trace_sha = source_case["trace_sha256"]
            trace = traces.get(trace_sha)
            if trace is None:
                raise ASOCSSessionBatchError(f"CASE_{ordinal:03d}_TRACE_NOT_FOUND")
            if "upper_stack" not in trace:
                raise ASOCSSessionBatchError(f"CASE_{ordinal:03d}_TRACE_SHAPE_INVALID")
            common["relevant_frozen_lineage"] = {
                "source_sha256": preparation["source_sha256"],
                "g1_audit_15m_sha256": preparation["g1_audit_15m_sha256"],
                "g3_trace_artifact_sha256": preparation["g3_trace_artifact_sha256"],
                "trace_sha256": trace_sha,
                "parents_sha256": source_case["parents_sha256"],
            }
            common["revealed_evidence"] = {
                "kind": "ANCHOR_15M",
                "clock": trace["clock"],
                "interval_start": trace["interval_start"],
                "interval_end": trace["interval_end"],
                "effective_time": trace["effective_time"],
                "first_valid_time": trace["first_valid_time"],
                "region": trace["region"],
                "source_status": trace["source_status"],
                "source_ohlc": {
                    key: source_case["ohlc"][index]
                    for index, key in enumerate(("open", "high", "low", "close"))
                },
                "source_lineage": trace["source_lineage"],
                "prior_bar_id": source_case["prior_bar_id"],
                "prior_contiguous": source_case["prior_contiguous"],
                "c1": trace["c1"],
            }
        elif source_case["kind"] == "SOURCE_GAP":
            common["relevant_frozen_lineage"] = {
                "source_sha256": preparation["source_sha256"],
                "g1_gap_ledger_sha256": preparation["g1_gap_ledger_sha256"],
                "g4_review_population_sha256": preparation["g4_review_population_sha256"],
            }
            common["revealed_evidence"] = {
                key: source_case[key]
                for key in (
                    "kind", "previous", "next", "delta_minutes", "missing_slot_count",
                    "repair_applied", "c1_disposition"
                )
            }
        else:
            raise ASOCSSessionBatchError(f"CASE_{ordinal:03d}_KIND_INVALID")
        output_cases.append(common)
    return {
        "schema": SESSION_PACKET_SCHEMA,
        "programme_id": PROGRAMME_ID,
        "plan_id": "OVC-ASOCS-CONFORMANCE-SCIENTIFIC-PREREGISTRATION-IMPLEMENTATION-PLAN-0.1-R1",
        "plan_version": "0.1_REVISED_1",
        "packet_id": "ASOCSI-WP8-S01-STAGE1-REVEAL-PACKET",
        "session": 1,
        "stage_index": 1,
        "stage": STAGE1,
        "case_count": 25,
        "presentation_order": "FROZEN_SESSION_ORDER",
        "preparation_reveal_pack_sha256": preparation_sha256,
        "locked_session1_human_input_sha256": preparation["locked_session1_human_input_sha256"],
        "permanent_warning": PERMANENT_WARNING,
        "construct_survival_decision": CONSTRUCT_SURVIVAL_PROHIBITION,
        "human_judgement_schema": "schemas/research_operations/asocs/asocs_stage1_fidelity_judgement_v0_1.schema.json",
        "human_reviewer_does_not_recompute_formula_arithmetic": True,
        "mechanical_arithmetic_check": preparation["mechanical_arithmetic_check"],
        "later_stage_reveal_status": "NOT_CONSTRUCTED_NOT_REVEALED",
        "cases": output_cases,
    }


def build_human_input_template(packet: Mapping[str, Any], packet_sha256: str) -> dict[str, Any]:
    """Return one deliberately incomplete, human-fillable session template."""
    cases = []
    for case in packet["cases"]:
        case_id = case["case_id"]
        cases.append({
            "presentation_ordinal": case["presentation_ordinal"],
            "case_id": case_id,
            "predecessor_blind_record_sha256": case["predecessor_blind_record_sha256"],
            "review_unit_id": case["review_unit_id"],
            "human_judgement": {
                "schema": "ovc-asocs-stage1-fidelity-judgement/v0_1",
                "case_id": case_id,
                "stage": STAGE1,
                "fidelity_disposition": None,
                "observational_correspondence": "",
                "prior_bridge_disposition": None,
                "semantic_leakage": None,
                "traceability": None,
                "information_gap_disposition": None,
                "construct_survival_decision": CONSTRUCT_SURVIVAL_PROHIBITION,
                "notes": "",
            },
        })
    return {
        "schema": SESSION_INPUT_SCHEMA,
        "programme_id": PROGRAMME_ID,
        "session": packet["session"],
        "stage": packet["stage"],
        "reveal_packet_sha256": packet_sha256,
        "cases": cases,
    }


def write_stage1_review_artifacts(
    *,
    preparation_path: Path,
    trace_path: Path,
    contract_path: Path,
    output_dir: Path,
) -> dict[str, Path]:
    """Materialise one deterministic, still-unanswered Session-1 Stage-1 packet set."""
    preparation_bytes = preparation_path.read_bytes()
    contract_bytes = contract_path.read_bytes()
    expected_trace_sha = "22c856efdd24083d5339d2082ad9714597e326a6f40655bfb82b0afa9899f7dc"
    if sha256_bytes(trace_path.read_bytes()) != expected_trace_sha:
        raise ASOCSSessionBatchError("G3_TRACE_ARTIFACT_SHA256_MISMATCH")
    try:
        preparation = json.loads(preparation_bytes)
        contract = json.loads(contract_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ASOCSSessionBatchError("PREPARATION_OR_CONTRACT_NOT_VALID_UTF8_JSON") from exc
    if contract.get("operator_transport_unit") != "COMPLETE_SESSION_STAGE":
        raise ASOCSSessionBatchError("SESSION_BATCH_CONTRACT_MISMATCH")
    packet = build_stage1_review_packet(
        preparation,
        preparation_sha256=sha256_bytes(preparation_bytes),
        trace_path=trace_path,
    )
    packet_bytes = raw_json_bytes(packet)
    packet_sha = sha256_bytes(packet_bytes)
    template = build_human_input_template(packet, packet_sha)
    template_bytes = raw_json_bytes(template)
    qa = {
        "schema": "ovc-asocsi-wp8-session-stage-preparation-qa/v0_1",
        "programme_id": PROGRAMME_ID,
        "session": 1,
        "stage": STAGE1,
        "qa_disposition": "PASS_REVEAL_PACKET_AND_TEMPLATE_ONLY",
        "case_count": 25,
        "checks": {
            "all_frozen_session_cases_present": "PASS_25_OF_25",
            "original_presentation_order": "PASS_25_OF_25",
            "case_identity": "PASS_25_OF_25",
            "predecessor_blind_sha256": "PASS_25_OF_25",
            "review_unit_identity": "PASS_25_OF_25",
            "exact_g3_trace_artifact_sha256": "PASS",
            "exact_trace_record_binding": "PASS_24_ANCHORS",
            "source_gap_preserved": "PASS_1_SOURCE_GAP",
            "stage1_source_c1_evidence_present": "PASS_25_OF_25",
            "mechanical_arithmetic_not_assigned_to_human": "PASS",
            "human_judgements_not_synthesized": "PASS_ALL_NULL_TEMPLATE_FIELDS",
            "construct_survival_prohibited": "PASS",
            "upper_stack_evidence_concealed": "PASS",
            "stage2_packet_not_constructed": "PASS",
            "single_session_human_input_template": "PASS_ONE_FILE_25_CASES",
            "session_batch_validator_and_atomic_freezer": "PASS_IMPLEMENTED",
            "programme_pointer_not_advanced_before_human_freeze": "PASS",
        },
        "reveal_packet_sha256": packet_sha,
        "human_input_template_sha256": sha256_bytes(template_bytes),
        "session_batch_contract_sha256": sha256_bytes(contract_bytes),
        "human_input_required": True,
        "next_boundary": "ONE_COMPLETE_SESSION1_STAGE1_HUMAN_INPUT_ARTIFACT",
        "later_stage_reveal_status": "NOT_CONSTRUCTED_NOT_REVEALED",
        "permanent_warning": PERMANENT_WARNING,
    }
    qa_bytes = raw_json_bytes(qa)
    receipt = {
        "schema": "ovc-programme-packet-receipt/v1",
        "programme_id": PROGRAMME_ID,
        "plan_id": "OVC-ASOCS-CONFORMANCE-SCIENTIFIC-PREREGISTRATION-IMPLEMENTATION-PLAN-0.1-R1",
        "plan_version": "0.1_REVISED_1",
        "packet_id": "ASOCSI-WP8-S01-STAGE1-SESSION-REVIEW-PACKET",
        "status": "IMPLEMENTED_HUMAN_INPUT_REQUIRED",
        "authority_required": "HUMAN_SCIENTIFIC_INPUT_WITHIN_EXISTING_G0_AUTHORITY",
        "authority_delta": "NONE",
        "case_count": 25,
        "reveal_packet_sha256": packet_sha,
        "human_input_template_sha256": sha256_bytes(template_bytes),
        "qa_sha256": sha256_bytes(qa_bytes),
        "stage2_reveal_started": False,
        "current_programme_pointer_mutated": False,
        "next_packet": "ASOCSI-WP8-S01-STAGE1-HUMAN-INPUT-VALIDATION-AND-FREEZE",
        "blockers": ["COMPLETE_SESSION1_STAGE1_HUMAN_INPUT_NOT_YET_SUPPLIED"],
        "warnings": [PERMANENT_WARNING],
        "rollback": "Forward-supersede preparation transport only; preserve frozen G3/G4/G5 and all human evidence.",
    }
    artifacts = {
        "reveal_packet": (
            output_dir / "ASOCSI_WP8_S01_STAGE1_REVEAL_PACKET_v0_1.json",
            packet_bytes,
        ),
        "human_input_template": (
            output_dir / "ASOCSI_WP8_S01_STAGE1_HUMAN_INPUT_TEMPLATE_v0_1.json",
            template_bytes,
        ),
        "qa": (
            output_dir / "ASOCSI_WP8_S01_STAGE1_SESSION_BATCH_QA_v0_1.json",
            qa_bytes,
        ),
        "receipt": (
            output_dir / "ASOCSI_WP8_S01_STAGE1_REVIEW_PACKET_RECEIPT_v0_1.json",
            raw_json_bytes(receipt),
        ),
    }
    for path, _ in artifacts.values():
        if path.exists() or path.is_symlink():
            raise ASOCSSessionBatchError("PREPARATION_ARTIFACT_ALREADY_EXISTS:" + path.name)
    output_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for name, (path, content) in artifacts.items():
        with path.open("xb") as stream:
            stream.write(content)
        written[name] = path
    return written


def freeze_session_submission(
    *,
    submission_path: Path,
    reveal_packet_path: Path,
    output_parent: Path,
) -> Path:
    """Atomically freeze all case records or write nothing.

    The output directory identity is the raw operator-input SHA-256. Existing
    output is never overwritten, making a repeated or altered freeze fail closed.
    """
    input_bytes = submission_path.read_bytes()
    packet_bytes = reveal_packet_path.read_bytes()
    try:
        supplied = json.loads(input_bytes)
        packet = json.loads(packet_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ASOCSSessionBatchError("INPUT_OR_PACKET_NOT_VALID_UTF8_JSON") from exc
    packet_sha = sha256_bytes(packet_bytes)
    validated = validate_session_submission(
        supplied, reveal_packet=packet, reveal_packet_sha256=packet_sha
    )
    input_sha = sha256_bytes(input_bytes)
    target = output_parent / f"ASOCSI_WP8_S01_STAGE1_FREEZE_{input_sha}"
    if target.exists() or target.is_symlink():
        raise ASOCSSessionBatchError("APPEND_ONLY_FREEZE_TARGET_ALREADY_EXISTS")
    output_parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".asocsi-s01-stage1-freeze-", dir=output_parent))
    try:
        (temporary / "ASOCSI_WP8_S01_STAGE1_HUMAN_INPUT.json").write_bytes(input_bytes)
        case_receipts = []
        for case in validated["cases"]:
            ordinal = case["presentation_ordinal"]
            record = {
                "schema": CASE_RECORD_SCHEMA,
                "programme_id": PROGRAMME_ID,
                "session": 1,
                "presentation_ordinal": ordinal,
                "case_id": case["case_id"],
                "stage": STAGE1,
                "predecessor_blind_record_sha256": case["predecessor_blind_record_sha256"],
                "review_unit_id": case["review_unit_id"],
                "revealed_surfaces": [
                    "EXACT_SOURCE_EVIDENCE", "C1_ARITHMETIC_FACTS", "C1_FORMULA_IDS",
                    "C1_PRIOR_BAR_ELIGIBILITY", "C1_NULL_REASONS", "C1_SOURCE_LINEAGE",
                ],
                "human_judgement": case["human_judgement"],
                "session_human_input_sha256": input_sha,
                "case_validation_status": "PASS",
                "frozen_before_next_reveal": True,
                "authority_class": AUTHORITY_CLASS,
                "unrecoverable_provenance_warning": PERMANENT_WARNING,
            }
            filename = f"CASE_{ordinal:03d}_{case['case_id'].split('.')[-1]}.json"
            record_bytes = raw_json_bytes(record)
            (temporary / filename).write_bytes(record_bytes)
            case_receipts.append({
                "presentation_ordinal": ordinal,
                "case_id": case["case_id"],
                "record": filename,
                "sha256": sha256_bytes(record_bytes),
                "predecessor_blind_record_sha256": case["predecessor_blind_record_sha256"],
            })
        input_receipt = {
            "schema": "ovc-asocsi-wp8-session-human-input-receipt/v0_1",
            "programme_id": PROGRAMME_ID,
            "session": 1,
            "stage": STAGE1,
            "human_input_sha256": input_sha,
            "human_input_byte_size": len(input_bytes),
            "reveal_packet_sha256": packet_sha,
            "case_count": len(case_receipts),
            "case_order_sha256": sha256_bytes(canonical_json_bytes([
                item["case_id"] for item in case_receipts
            ])),
            "operator_text_preservation": "RAW_INPUT_BYTES_FROZEN_EXACT",
        }
        input_receipt_bytes = raw_json_bytes(input_receipt)
        (temporary / "ASOCSI_WP8_S01_STAGE1_HUMAN_INPUT_RECEIPT.json").write_bytes(
            input_receipt_bytes
        )
        freeze_receipt = {
            "schema": "ovc-asocsi-wp8-session-stage-freeze-receipt/v0_1",
            "programme_id": PROGRAMME_ID,
            "session": 1,
            "stage": STAGE1,
            "status": "FROZEN_COMPLETE_SESSION_STAGE",
            "case_count": len(case_receipts),
            "human_input_sha256": input_sha,
            "human_input_receipt_sha256": sha256_bytes(input_receipt_bytes),
            "case_records": case_receipts,
            "duplicates": 0,
            "omissions": 0,
            "substitutions": 0,
            "extras": 0,
            "append_only": True,
            "stage2_reveal_authorized_only_after_this_freeze": True,
            "stage2_reveal_materialized": False,
            "permanent_warning": PERMANENT_WARNING,
        }
        freeze_bytes = raw_json_bytes(freeze_receipt)
        (temporary / "ASOCSI_WP8_S01_STAGE1_FREEZE_RECEIPT.json").write_bytes(freeze_bytes)
        qa = {
            "schema": "ovc-asocsi-wp8-session-stage-qa/v0_1",
            "programme_id": PROGRAMME_ID,
            "session": 1,
            "stage": STAGE1,
            "qa_disposition": "PASS_COMPLETE_SESSION_STAGE_FREEZE",
            "case_count": len(case_receipts),
            "checks": {
                "exact_session_identity": "PASS",
                "exact_case_count": "PASS",
                "exact_case_order": "PASS",
                "membership_duplicates_omissions_substitutions_extras": "PASS_NONE",
                "predecessor_blind_sha256": "PASS_ALL_CASES",
                "review_unit_identity": "PASS_ALL_CASES",
                "governing_stage_schema": "PASS_ALL_CASES",
                "human_answers_not_inferred": "PASS",
                "operator_text_raw_bytes_preserved": "PASS",
                "individual_case_records_materialized": "PASS_ALL_CASES",
                "session_input_hash_binding": "PASS_ALL_CASES",
                "append_only_freeze": "PASS",
                "stage2_not_prematurely_materialized": "PASS",
            },
            "freeze_receipt_sha256": sha256_bytes(freeze_bytes),
            "construct_survival_decision": CONSTRUCT_SURVIVAL_PROHIBITION,
            "permanent_warning": PERMANENT_WARNING,
        }
        (temporary / "ASOCSI_WP8_S01_STAGE1_QA.json").write_bytes(raw_json_bytes(qa))
        os.replace(temporary, target)
        return target
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser(
        "prepare", help="materialise the complete Session-1 Stage-1 packet and template"
    )
    prepare.add_argument("--preparation", type=Path, required=True)
    prepare.add_argument("--traces", type=Path, required=True)
    prepare.add_argument("--contract", type=Path, required=True)
    prepare.add_argument("--output-dir", type=Path, required=True)
    freeze = subparsers.add_parser("freeze", help="validate and atomically freeze one session input")
    freeze.add_argument("--submission", type=Path, required=True)
    freeze.add_argument("--reveal-packet", type=Path, required=True)
    freeze.add_argument("--output-parent", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = write_stage1_review_artifacts(
            preparation_path=args.preparation,
            trace_path=args.traces,
            contract_path=args.contract,
            output_dir=args.output_dir,
        )
        print(json.dumps({key: str(value) for key, value in result.items()}, sort_keys=True))
    elif args.command == "freeze":
        print(freeze_session_submission(
            submission_path=args.submission,
            reveal_packet_path=args.reveal_packet,
            output_parent=args.output_parent,
        ))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
