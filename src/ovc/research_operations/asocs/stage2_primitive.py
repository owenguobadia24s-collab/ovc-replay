from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

STAGE = "C2_PRIMITIVE_STRUCTURE"
PRIMITIVE_COMPONENTS = ("C2_HORIZON", "C2_LEVEL", "C2_CONTAINER", "C2_RELATION")
NOT_EVALUABLE_REASONS = (
    "NO_LAWFUL_ACTIVE_INPUT_IDENTITY",
    "PRICE_SIDE_UNRESOLVED",
    "TIMESTAMP_TIMEZONE_UNRESOLVED",
    "NO_MEANING_BEARING_SHADOW_REIMPLEMENTATION",
)
ALLOWED_DISPOSITIONS = {
    "COHERENT", "COHERENT_SCOPE_RESTRICTED", "MECHANICALLY_VALID_EMPIRICALLY_WEAK",
    "OVER_SENSITIVE", "UNDER_SENSITIVE", "SEMANTICALLY_OVERLOADED", "POSSIBLE_REDUNDANCY",
    "REPRESENTATION_ARTEFACT", "INFORMATION_GAP", "NEEDS_REDEFINITION", "INVALID",
    "INDETERMINATE", "SOURCE_LIMITED",
}
ALLOWED_CONFIDENCE = {"HIGH", "MODERATE", "LOW"}
ALLOWED_EVALUABILITY = {"EVALUABLE", "INFORMATION_GAP", "SOURCE_LIMITED", "INDETERMINATE"}


class Stage2PrimitiveError(ValueError):
    pass


def canonical_sha256(value: Mapping[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_reveal_index(index: Mapping[str, Any]) -> None:
    if index.get("session") != 1 or index.get("stage") != STAGE:
        raise Stage2PrimitiveError("SESSION_OR_STAGE_MISMATCH")
    if index.get("case_count") != 25 or len(index.get("case_ids", [])) != 25:
        raise Stage2PrimitiveError("SESSION1_CASE_COUNT_MISMATCH")
    if index.get("stage1_review_route_status") != "SUPERSEDED_UNCOMPLETED":
        raise Stage2PrimitiveError("STAGE1_SUPERSESSION_STATE_MISMATCH")
    if index.get("stage1_scientific_conclusion") != "NOT_ESTABLISHED":
        raise Stage2PrimitiveError("STAGE1_CONCLUSION_MUST_REMAIN_NOT_ESTABLISHED")
    profile = index.get("frozen_primitive_profile")
    if not isinstance(profile, Mapping) or tuple(profile.keys()) != PRIMITIVE_COMPONENTS:
        raise Stage2PrimitiveError("PRIMITIVE_PROFILE_MISMATCH")
    for component in PRIMITIVE_COMPONENTS:
        record = profile[component]
        if record.get("construct") != component or record.get("disposition") != "NOT_EVALUABLE":
            raise Stage2PrimitiveError("PRIMITIVE_NON_EVALUABILITY_MISMATCH")
        if tuple(record.get("reason_codes", ())) != NOT_EVALUABLE_REASONS:
            raise Stage2PrimitiveError("PRIMITIVE_REASON_MISMATCH")
        if record.get("authority_class") != "ASOCS_AUDIT_ONLY":
            raise Stage2PrimitiveError("PRIMITIVE_AUTHORITY_MISMATCH")
        if record.get("active") is not False or record.get("canonical") is not False or record.get("publication") is not False:
            raise Stage2PrimitiveError("PRIMITIVE_AUTHORITY_FLAG_MISMATCH")
    firewall = index.get("later_stage_firewall", {})
    if firewall.get("stage2_complete_session_freeze_required_before_stage3") is not True:
        raise Stage2PrimitiveError("STAGE2_FREEZE_BEFORE_STAGE3_REQUIRED")
    if firewall.get("stage3_reveal_started") is not False:
        raise Stage2PrimitiveError("STAGE3_MUST_NOT_BE_REVEALED")
    if index.get("human_judgements") != []:
        raise Stage2PrimitiveError("HUMAN_JUDGEMENTS_MUST_BE_EMPTY_AT_PREPARATION")


def validate_human_submission(index: Mapping[str, Any], submission: Mapping[str, Any]) -> None:
    validate_reveal_index(index)
    if submission.get("session") != 1 or submission.get("stage") != STAGE:
        raise Stage2PrimitiveError("SUBMISSION_SESSION_OR_STAGE_MISMATCH")
    answers = submission.get("cases")
    if not isinstance(answers, list) or len(answers) != 25:
        raise Stage2PrimitiveError("SUBMISSION_CASE_COUNT_MISMATCH")
    expected_ids = index["case_ids"]
    for expected_id, answer in zip(expected_ids, answers):
        if answer.get("case_id") != expected_id:
            raise Stage2PrimitiveError("SUBMISSION_CASE_ID_OR_ORDER_MISMATCH")
        if answer.get("comparison_evaluability") not in ALLOWED_EVALUABILITY:
            raise Stage2PrimitiveError("INVALID_COMPARISON_EVALUABILITY")
        if answer.get("construct_survival_decision") != "PROHIBITED_DURING_CASE_REVIEW":
            raise Stage2PrimitiveError("CONSTRUCT_SURVIVAL_DECISION_PROHIBITED")
        components = answer.get("component_judgements")
        if not isinstance(components, Mapping) or tuple(components.keys()) != ("HORIZON", "LEVEL", "CONTAINER", "RELATION"):
            raise Stage2PrimitiveError("COMPONENT_JUDGEMENT_MISMATCH")
        for component in components.values():
            if component.get("disposition") not in ALLOWED_DISPOSITIONS:
                raise Stage2PrimitiveError("INVALID_COMPONENT_DISPOSITION")
            if component.get("confidence") not in ALLOWED_CONFIDENCE:
                raise Stage2PrimitiveError("INVALID_COMPONENT_CONFIDENCE")
            if not isinstance(component.get("notes"), str):
                raise Stage2PrimitiveError("COMPONENT_NOTES_MUST_BE_STRING")


def build_freeze_payload(index: Mapping[str, Any], submission: Mapping[str, Any], raw_input_sha256: str) -> dict[str, Any]:
    """Validate and bind supplied human input; never synthesize a scientific answer."""
    validate_human_submission(index, submission)
    if len(raw_input_sha256) != 64:
        raise Stage2PrimitiveError("RAW_INPUT_SHA256_REQUIRED")
    return {
        "schema": "ovc-asocsi-stage2-c2-primitive-structure-freeze/v0_1",
        "programme_id": index["programme_id"],
        "session": 1,
        "stage": STAGE,
        "reveal_index_sha256": canonical_sha256(index),
        "raw_human_input_sha256": raw_input_sha256,
        "case_count": 25,
        "human_judgements": submission["cases"],
        "complete_session_stage_freeze": True,
        "stage3_reveal_allowed_after_this_freeze": True,
        "agent_synthesized_human_answers": False,
        "construct_survival_decision": "PROHIBITED_DURING_CASE_REVIEW",
    }
