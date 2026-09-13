from __future__ import annotations

from typing import Any


def assert_mechanical_only(record: dict[str, Any]) -> None:
    if record.get("authority_effect") != "NONE" or record.get("scientific_effect") != "NONE":
        raise AssertionError("BCWT-R2 authority/scientific effect leakage")
    if record.get("candidate_evaluation_admission_id_or_none"):
        raise AssertionError("BCWT-R2 must not carry CandidateEvaluationAdmission")
    if record.get("execution_role") == "C_ADMITTED_SCIENTIFIC":
        raise AssertionError("BCWT-R2 scientific execution role is reserved")
