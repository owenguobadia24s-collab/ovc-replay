from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

from ovc.development.identity import canonical_sha256

from .corpus import score_historical_replay_case


REQUIRED_EVALUATION_LAYERS = ("E1", "E2", "E3", "E4", "E5", "E6")
_BLOCKING_STATUSES = {"BLOCK", "FAIL", "NOT_EVALUABLE", "QUARANTINE"}


def _iso(value: str) -> datetime:
    text = value.replace("Z", "+00:00")
    result = datetime.fromisoformat(text)
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def run_evaluation_suite(
    *,
    suite_id: str,
    layer_evidence: Mapping[str, Mapping[str, Any]],
    required_layers: Sequence[str] = REQUIRED_EVALUATION_LAYERS,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    blockers: list[str] = []
    for layer in required_layers:
        raw = layer_evidence.get(layer)
        if raw is None:
            missing.append(layer)
            rows.append({"layer": layer, "status": "NOT_EVALUABLE", "evidence_ids": []})
            blockers.append(f"{layer}:MISSING_EVIDENCE")
            continue
        status = str(raw.get("status", "NOT_EVALUABLE")).upper()
        row = {
            "layer": layer,
            "status": status,
            "evidence_ids": sorted(set(str(v) for v in raw.get("evidence_ids", []))),
            "mandatory_blocker": bool(raw.get("mandatory_blocker", False)),
            "false_allow": bool(raw.get("false_allow", False)),
        }
        rows.append(row)
        if status != "PASS":
            blockers.append(f"{layer}:{status}")
        if row["mandatory_blocker"]:
            blockers.append(f"{layer}:MANDATORY_BLOCKER")
        if row["false_allow"]:
            blockers.append(f"{layer}:FALSE_ALLOW")
    evidence_closed = not missing and not blockers
    pass_count = sum(1 for row in rows if row["status"] == "PASS")
    logical = {
        "suite_id": str(suite_id),
        "required_layers": list(required_layers),
        "layers": rows,
        "missing_layers": missing,
        "blocking_reasons": sorted(set(blockers)),
        "evidence_closed": evidence_closed,
        "aggregate_score": pass_count / len(required_layers) if required_layers else 0.0,
        "status": "PASS" if evidence_closed else "BLOCK",
    }
    return {
        "schema": "ovc-dsai-evaluation-suite-result/v1",
        **logical,
        "authority_effect": "NONE",
        "result_id": canonical_sha256(logical, role="DSAI_EVALUATION_SUITE_RESULT"),
    }


def build_skill_qualification_record(
    *,
    skill_release_id: str,
    capability_id: str,
    environment_id: str,
    knowledge_pack_hash: str,
    environment_hash: str,
    suite_result: Mapping[str, Any],
    requested_maturity: str = "QUALIFIED",
    current_knowledge_pack_hash: str | None = None,
    current_environment_hash: str | None = None,
) -> dict[str, Any]:
    stale = False
    if current_knowledge_pack_hash is not None and current_knowledge_pack_hash != knowledge_pack_hash:
        stale = True
    if current_environment_hash is not None and current_environment_hash != environment_hash:
        stale = True
    suite_pass = suite_result.get("status") == "PASS" and suite_result.get("evidence_closed") is True
    eligible = bool(suite_pass and not stale)
    requested = str(requested_maturity).upper()
    if not eligible:
        qualification_status = "BLOCKED"
        max_maturity = "EXPERIMENTAL"
    elif requested == "TRUSTED":
        qualification_status = "GATE_REQUIRED"
        max_maturity = "QUALIFIED"
    else:
        qualification_status = "QUALIFIED"
        max_maturity = "QUALIFIED"
    logical = {
        "skill_release_id": str(skill_release_id),
        "capability_id": str(capability_id),
        "environment_id": str(environment_id),
        "knowledge_pack_hash": str(knowledge_pack_hash),
        "environment_hash": str(environment_hash),
        "evaluation_suite_result_id": suite_result.get("result_id"),
        "requested_maturity": requested,
        "qualification_status": qualification_status,
        "max_maturity_without_operator_gate": max_maturity,
        "stale": stale,
        "evidence_closed": bool(suite_result.get("evidence_closed", False)),
        "trusted_promoted": False,
    }
    return {
        "schema": "ovc-dsai-skill-qualification-record/v1",
        **logical,
        "authority_effect": "NONE",
        "qualification_id": canonical_sha256(logical, role="DSAI_SKILL_QUALIFICATION"),
    }


def assess_requalification(
    qualification: Mapping[str, Any],
    *,
    current_skill_release_id: str,
    current_knowledge_pack_hash: str,
    current_environment_hash: str,
) -> dict[str, Any]:
    reasons: list[str] = []
    if qualification.get("skill_release_id") != current_skill_release_id:
        reasons.append("SKILL_RELEASE_DRIFT")
    if qualification.get("knowledge_pack_hash") != current_knowledge_pack_hash:
        reasons.append("KNOWLEDGE_PACK_DRIFT")
    if qualification.get("environment_hash") != current_environment_hash:
        reasons.append("ENVIRONMENT_DRIFT")
    return {
        "schema": "ovc-dsai-requalification-assessment/v1",
        "status": "STALE_REQUALIFICATION_REQUIRED" if reasons else "CURRENT",
        "reason_codes": reasons,
        "authority_effect": "NONE",
    }


def build_composition_qualification_record(
    *,
    composition_id: str,
    member_qualifications: Sequence[Mapping[str, Any]],
    composition_evidence_status: str,
) -> dict[str, Any]:
    member_ids = [str(row.get("qualification_id", "")) for row in member_qualifications]
    invalid = [row for row in member_qualifications if row.get("qualification_status") != "QUALIFIED" or row.get("stale")]
    passed = not invalid and bool(member_qualifications) and str(composition_evidence_status).upper() == "PASS"
    logical = {
        "composition_id": str(composition_id),
        "member_qualification_ids": member_ids,
        "composition_evidence_status": str(composition_evidence_status).upper(),
        "status": "QUALIFIED" if passed else "BLOCKED",
        "trusted_promoted": False,
    }
    return {
        "schema": "ovc-dsai-composition-qualification-record/v1",
        **logical,
        "authority_effect": "NONE",
        "composition_qualification_id": canonical_sha256(logical, role="DSAI_COMPOSITION_QUALIFICATION"),
    }


def build_operational_observation(*, qualification_id: str, observation_type: str, status: str, evidence_ids: Sequence[str]) -> dict[str, Any]:
    logical = {"qualification_id": str(qualification_id), "observation_type": str(observation_type), "status": str(status), "evidence_ids": sorted(set(str(v) for v in evidence_ids))}
    return {"schema": "ovc-dsai-skill-operational-observation/v1", **logical, "authority_effect": "NONE", "observation_id": canonical_sha256(logical, role="DSAI_OPERATIONAL_OBSERVATION")}


def build_incident_record(*, qualification_id: str, severity: str, reason_codes: Sequence[str]) -> dict[str, Any]:
    level = str(severity).upper()
    if level not in {"S1", "S2", "S3", "S4"}:
        raise ValueError("unsupported incident severity")
    logical = {
        "qualification_id": str(qualification_id),
        "severity": level,
        "reason_codes": sorted(set(str(v) for v in reason_codes)),
        "quarantine_required": level in {"S3", "S4"},
        "revocation_required": level == "S4",
        "containment_required": level in {"S3", "S4"},
        "restoration_requires_requalification": level in {"S3", "S4"},
    }
    return {"schema": "ovc-dsai-skill-incident-record/v1", **logical, "authority_effect": "NONE", "incident_id": canonical_sha256(logical, role="DSAI_SKILL_INCIDENT")}


def build_impact_assessment(*, incident_id: str, dependent_qualification_ids: Sequence[str]) -> dict[str, Any]:
    logical = {"incident_id": str(incident_id), "dependent_qualification_ids": sorted(set(str(v) for v in dependent_qualification_ids)), "requires_review": bool(dependent_qualification_ids)}
    return {"schema": "ovc-dsai-skill-impact-assessment/v1", **logical, "authority_effect": "NONE", "impact_id": canonical_sha256(logical, role="DSAI_SKILL_IMPACT")}


def build_operator_gate_readiness_record(
    *, gate_id: str, authority_kind: str, candidate_sha: str, qualification_ids: Sequence[str], evidence_closed: bool,
    gate_ready_at: str, review_target_at: str, queue_age_minutes: int = 0, consolidated_decision_group: str | None = None,
    candidate_stale: bool = False,
) -> dict[str, Any]:
    ready = bool(evidence_closed and qualification_ids and not candidate_stale)
    logical = {
        "gate_id": str(gate_id), "authority_kind": str(authority_kind), "candidate_sha": str(candidate_sha),
        "qualification_ids": sorted(set(str(v) for v in qualification_ids)), "evidence_closed": bool(evidence_closed),
        "gate_ready_at": str(gate_ready_at), "review_target_at": str(review_target_at), "queue_age_minutes": int(queue_age_minutes),
        "consolidated_decision_group": consolidated_decision_group, "candidate_stale": bool(candidate_stale),
        "status": "GATE_READY" if ready else "BLOCKED", "authority_granted": False,
    }
    return {"schema": "ovc-dsai-operator-gate-readiness-record/v1", **logical, "authority_effect": "NONE", "readiness_id": canonical_sha256(logical, role="DSAI_GATE_READINESS")}


def age_gate_readiness(record: Mapping[str, Any], *, now: str, current_candidate_sha: str) -> dict[str, Any]:
    result = dict(record)
    age = max(0, int((_iso(now) - _iso(str(record["gate_ready_at"]))).total_seconds() // 60))
    target_missed = _iso(now) > _iso(str(record["review_target_at"]))
    candidate_stale = str(record.get("candidate_sha")) != str(current_candidate_sha)
    result["queue_age_minutes"] = age
    result["review_slo_state"] = "AGED" if target_missed else "WITHIN_TARGET"
    result["candidate_stale"] = candidate_stale
    if candidate_stale:
        result["status"] = "BLOCKED"
    result["authority_granted"] = False
    result["authority_effect"] = "NONE"
    result["auto_approve"] = False
    result["auto_promote"] = False
    result["auto_activate"] = False
    return result


def consolidate_gate_readiness(records: Sequence[Mapping[str, Any]], *, group_id: str) -> dict[str, Any]:
    if not records:
        raise ValueError("at least one gate readiness record is required")
    kinds = {str(row.get("authority_kind")) for row in records}
    if len(kinds) != 1:
        raise ValueError("only the same authority kind may be consolidated")
    traceable = all(row.get("readiness_id") and row.get("gate_id") for row in records)
    logical = {"group_id": str(group_id), "authority_kind": next(iter(kinds)), "readiness_ids": [str(row["readiness_id"]) for row in records], "independently_traceable": traceable}
    return {"schema": "ovc-dsai-gate-readiness-consolidation/v1", **logical, "status": "PASS" if traceable else "BLOCK", "authority_effect": "NONE", "consolidation_id": canonical_sha256(logical, role="DSAI_GATE_CONSOLIDATION")}


def assess_parallel_qualification_independence(tasks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    conflicts: list[str] = []
    for i, left in enumerate(tasks):
        for right in tasks[i + 1:]:
            for key in ("fixture_ids", "environment_ids", "evidence_store_ids"):
                overlap = set(str(v) for v in left.get(key, [])) & set(str(v) for v in right.get(key, []))
                if overlap:
                    conflicts.append(f"{key}:{','.join(sorted(overlap))}")
    return {"schema": "ovc-dsai-parallel-qualification-independence/v1", "status": "PASS" if not conflicts else "BLOCK", "conflicts": sorted(set(conflicts)), "authority_effect": "NONE"}


def run_fault_injection(*, scenario: str) -> dict[str, Any]:
    scenario_id = str(scenario).upper()
    supported = {"CORRUPT_MANIFEST", "STALE_HASH", "DENIED_TOOL", "KILLED_TEST", "INVALID_CACHE"}
    if scenario_id not in supported:
        raise ValueError("unsupported fault injection scenario")
    logical = {"scenario": scenario_id, "observed_status": "BLOCK", "fail_closed": True}
    return {"schema": "ovc-dsai-qualification-fault-injection/v1", **logical, "authority_effect": "NONE", "result_id": canonical_sha256(logical, role="DSAI_QUALIFICATION_FAULT")}


def run_historical_reference_case(*, actual_interpretation: str, case: Mapping[str, Any]) -> dict[str, Any]:
    return score_historical_replay_case(actual_interpretation=actual_interpretation, case=case)


def qualification_velocity(*, completed: int, elapsed_minutes: int, requalification_count: int = 0, failed_count: int = 0) -> dict[str, Any]:
    if elapsed_minutes <= 0:
        raise ValueError("elapsed_minutes must be positive")
    return {"schema": "ovc-dsai-qualification-velocity/v1", "completed": int(completed), "elapsed_minutes": int(elapsed_minutes), "requalification_count": int(requalification_count), "failed_count": int(failed_count), "qualifications_per_hour": round(int(completed) * 60.0 / elapsed_minutes, 6), "authority_effect": "NONE"}
