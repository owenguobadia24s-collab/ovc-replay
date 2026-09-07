from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .identity import CBSContractError


AV_DISPOSITIONS = {
    "CBS-AV01": "HARD_FAIL", "CBS-AV02": "HARD_FAIL", "CBS-AV03": "INVALID_GENERATION",
    "CBS-AV04": "INVALID_GENERATION", "CBS-AV05": "HARD_FAIL", "CBS-AV06": "HARD_FAIL",
    "CBS-AV07": "HARD_FAIL", "CBS-AV08": "HARD_FAIL", "CBS-AV09": "HARD_FAIL",
    "CBS-AV10": "CAPACITY_EXCEEDED", "CBS-AV11": "HARD_FAIL", "CBS-AV12": "CIRCULARITY_FAIL",
    "CBS-AV13": "HARD_FAIL", "CBS-AV14": "INVALID_GENERATION", "CBS-AV15": "NOT_EVALUABLE",
    "CBS-AV16": "REPLICATION_CONTAMINATED", "CBS-AV17": "INVALID_GENERATION",
    "CBS-AV18": "HARD_FAIL", "CBS-AV19": "ASCERTAINMENT_FAIL", "CBS-AV20": "SUPPORT_MISMATCH",
    "CBS-AV21": "HARD_FAIL", "CBS-AV22": "CAUSAL_ADMISSION_FAIL",
    "CBS-AV23": "DECISION_SEARCH_EXPOSURE_FAIL", "CBS-AV24": "REPLICATION_CONTAMINATED",
    "CBS-AV25": "INVALID_GENERATION", "CBS-AV26": "MEANING_BEARING_SUCCESSOR",
    "CBS-AV27": "INDEPENDENT_REVIEW_FAIL", "CBS-AV28": "NOT_EVALUABLE",
}


def adjudicate_fixture(fixture_id: str, attack_survived: bool) -> dict[str, Any]:
    if fixture_id not in AV_DISPOSITIONS:
        raise CBSContractError("CBS_ADVERSARIAL_FIXTURE_UNKNOWN")
    if attack_survived:
        raise CBSContractError(f"CBSI_G1_SYNTH_BLOCK:{fixture_id}:{AV_DISPOSITIONS[fixture_id]}")
    return {"fixture_id": fixture_id, "required_disposition": AV_DISPOSITIONS[fixture_id], "result": "PASS_ATTACK_BLOCKED"}


def classify_amendment(*, changed_fields: Sequence[str], semantic_identity_proved: bool) -> str:
    meaning_fields = {"projection", "source_population", "tolerance", "matching", "support", "endpoint",
                      "materiality", "null", "parameter_family", "representation", "replication", "decision_rule"}
    if meaning_fields & set(changed_fields) or not semantic_identity_proved:
        return "MEANING_BEARING_SUCCESSOR"
    return "MECHANICAL_NON_MEANING"


def validate_independent_review(*, implementation_author: str, reviewer: str, fresh_process: bool, conversation_state_used: bool) -> None:
    if not reviewer or reviewer == implementation_author or not fresh_process or conversation_state_used:
        raise CBSContractError("INDEPENDENT_REVIEW_FAIL")


def validate_temporal_diversity(methods: Sequence[Mapping[str, Any]], *, broad_claim_requested: bool) -> dict[str, Any]:
    classes = {str(item.get("temporal_class", "")) for item in methods if item.get("availability") == "AVAILABLE"}
    required = {"OWNER_DEFINED_ONLINE_CAUSAL", "ONLINE_CAUSAL", "CONFIRMATION_DELAYED", "RETROSPECTIVE", "CONTROL"}
    missing = sorted(required - classes)
    if broad_claim_requested and missing:
        raise CBSContractError(f"NOT_EVALUABLE:MINIMUM_TEMPORAL_CLASS_DIVERSITY:{','.join(missing)}")
    return {"required": sorted(required), "observed": sorted(classes), "missing": missing,
            "broad_claim_evaluable": not missing}
