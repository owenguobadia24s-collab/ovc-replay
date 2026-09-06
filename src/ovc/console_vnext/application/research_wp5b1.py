"""Fail-closed fixture-only DMRP projection for RCN-RN-WP5B1."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping

from .errors import AuthorityDenied, ContractError, SourceConflict
from .research_wp5a import git_blob_sha

_BINDING_SCHEMA = "ovc-rcn-rn-wp5b1-dmrp-source-bindings/v1"
_SNAPSHOT_SCHEMA = "ovc-rcn-rn-wp5b1-dmrp-snapshot/v1"
_ALLOWED_SOURCE_CLASSES = {"SYNTHETIC_FIXTURE"}
_REQUIRED_SOURCE_IDS = {
    "DMRP_WP1_SYNTHETIC_RECORDS",
    "DMRP_WP2_SYNTHETIC_CANDIDATE",
    "DMRP_WP3_PATH2_SYNTHETIC_READINESS",
}


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{label}_OBJECT_REQUIRED")
    return dict(value)


def _load(value: Mapping[str, Any] | Path, label: str) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return copy.deepcopy(dict(value))
    try:
        raw = json.loads(Path(value).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"{label}_INVALID_JSON") from exc
    return _object(raw, label)


def _repo_path(root: Path, relative: str) -> Path:
    if not relative or Path(relative).is_absolute():
        raise ContractError("WP5B1_SOURCE_PATH_RELATIVE_REQUIRED")
    base = root.resolve()
    candidate = (base / relative).resolve(strict=False)
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise ContractError("WP5B1_SOURCE_PATH_ESCAPES_REPOSITORY") from exc
    if not candidate.is_file():
        raise ContractError(f"WP5B1_SOURCE_FILE_MISSING:{relative}")
    return candidate


def _index_wp1(source: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    rows = source.get("fixtures")
    if not isinstance(rows, list):
        raise ContractError("WP5B1_WP1_FIXTURES_LIST_REQUIRED")
    result: dict[str, dict[str, Any]] = {}
    for raw in rows:
        row = _object(raw, "WP5B1_WP1_FIXTURE")
        record_type = row.get("record_type")
        if not isinstance(record_type, str) or not record_type:
            raise ContractError("WP5B1_WP1_RECORD_TYPE_REQUIRED")
        result[record_type] = _object(row.get("scientific_payload"), f"WP5B1_{record_type}")
    return result


def build_wp5b1_dmrp_snapshot(
    *,
    repository_root: Path,
    presentation: Mapping[str, Any] | Path,
    bindings: Mapping[str, Any] | Path,
) -> dict[str, Any]:
    registry = _load(bindings, "WP5B1_BINDINGS")
    payload = _load(presentation, "WP5B1_PRESENTATION")

    if registry.get("schema") != _BINDING_SCHEMA:
        raise ContractError("WP5B1_BINDING_SCHEMA_INVALID")
    if payload.get("schema") != _SNAPSHOT_SCHEMA:
        raise ContractError("WP5B1_SNAPSHOT_SCHEMA_INVALID")
    if registry.get("packet_id") != "RCN-RN-WP5B1" or payload.get("packet_id") != "RCN-RN-WP5B1":
        raise SourceConflict("WP5B1_PACKET_IDENTITY_MISMATCH")
    for document in (registry, payload):
        if document.get("authority_effect") != "NONE":
            raise AuthorityDenied("WP5B1_AUTHORITY_EFFECT_MUST_BE_NONE")
    if registry.get("transport") != "GET_ONLY" or registry.get("writes") != "NONE":
        raise AuthorityDenied("WP5B1_GET_ONLY_WRITE_DENY_REQUIRED")
    if registry.get("presentation_mode") != "FIXTURE_ONLY" or registry.get("evidence_status") != "NON_EVIDENTIARY":
        raise AuthorityDenied("WP5B1_FIXTURE_NON_EVIDENTIARY_REQUIRED")
    if registry.get("validation_consumption") != "LOCKED_UNCONSUMED":
        raise AuthorityDenied("WP5B1_VALIDATION_MUST_REMAIN_LOCKED")
    if registry.get("first_new_real_research_source") is not False:
        raise AuthorityDenied("WP5B1_FIRST_NEW_REAL_SOURCE_REQUIRES_G5")
    if registry.get("operator_escalation_gate") != "RCN-RN-G5-FIRST-NEW-SOURCE[DMRP]":
        raise AuthorityDenied("WP5B1_OPERATOR_GATE_BINDING_INVALID")

    source_rows = registry.get("sources")
    if not isinstance(source_rows, list) or not source_rows:
        raise ContractError("WP5B1_SOURCE_BINDINGS_REQUIRED")
    if {str(row.get("source_id")) for row in source_rows if isinstance(row, Mapping)} != _REQUIRED_SOURCE_IDS:
        raise SourceConflict("WP5B1_SOURCE_SET_INVALID")

    sources: dict[str, dict[str, Any]] = {}
    for raw in source_rows:
        binding = _object(raw, "WP5B1_SOURCE_BINDING")
        source_id = str(binding.get("source_id", ""))
        if binding.get("source_class") not in _ALLOWED_SOURCE_CLASSES:
            raise AuthorityDenied(f"WP5B1_SOURCE_CLASS_NOT_AUTO_EXECUTABLE:{source_id}")
        if binding.get("first_new_real_research_source") is not False:
            raise AuthorityDenied(f"WP5B1_FIRST_NEW_REAL_SOURCE:{source_id}")
        path = _repo_path(Path(repository_root), str(binding.get("path", "")))
        if git_blob_sha(path) != binding.get("git_blob_sha"):
            raise SourceConflict(f"WP5B1_SOURCE_BLOB_MISMATCH:{source_id}")
        source = _load(path, f"WP5B1_SOURCE:{source_id}")
        if source.get("schema") != binding.get("schema"):
            raise SourceConflict(f"WP5B1_SOURCE_SCHEMA_MISMATCH:{source_id}")
        marker = str(binding.get("authority_field", ""))
        if source.get(marker) != binding.get("authority_value"):
            raise AuthorityDenied(f"WP5B1_SOURCE_AUTHORITY_MARKER_INVALID:{source_id}")
        sources[source_id] = source

    preflight = _object(payload.get("source_preflight"), "WP5B1_SOURCE_PREFLIGHT")
    if preflight.get("status") != "PASS_NO_FIRST_NEW_REAL_RESEARCH_SOURCE":
        raise AuthorityDenied("WP5B1_SOURCE_PREFLIGHT_NOT_PASS")
    if preflight.get("first_new_real_research_source") is not False:
        raise AuthorityDenied("WP5B1_PRESENTATION_FIRST_NEW_REAL_SOURCE")
    if set(preflight.get("source_ids", [])) != _REQUIRED_SOURCE_IDS:
        raise SourceConflict("WP5B1_PREFLIGHT_SOURCE_SET_MISMATCH")

    wp1 = _index_wp1(sources["DMRP_WP1_SYNTHETIC_RECORDS"])
    study = wp1.get("DMRP_STUDY")
    cycle = wp1.get("EVIDENCE_CYCLE_GENERATION")
    question = wp1.get("RESEARCH_QUESTION_RECORD")
    if not study or not cycle or not question:
        raise SourceConflict("WP5B1_PATH1_SOURCE_RECORDS_INCOMPLETE")
    path1 = _object(payload.get("path1"), "WP5B1_PATH1")
    expected_path1 = {
        "research_mode": study.get("research_mode"),
        "research_role": study.get("research_role"),
        "study_id": study.get("study_id"),
        "cycle_id": cycle.get("cycle_id"),
        "question_id": question.get("question_id"),
        "validation_access_state": study.get("validation_access_state"),
    }
    for key, expected in expected_path1.items():
        if path1.get(key) != expected:
            raise SourceConflict(f"WP5B1_PATH1_SOURCE_MISMATCH:{key}")
    if path1.get("research_mode") != "PATH_1_EMPIRICAL" or path1.get("validation_access_state") != "LOCKED_UNCONSUMED":
        raise AuthorityDenied("WP5B1_PATH1_MODE_OR_VALIDATION_INVALID")

    wp3 = sources["DMRP_WP3_PATH2_SYNTHETIC_READINESS"]
    path2 = _object(payload.get("path2"), "WP5B1_PATH2")
    training = wp3.get("training")
    guided = wp3.get("guided_formalisation")
    intake = wp3.get("intake")
    if not isinstance(training, list) or not training or not isinstance(guided, list) or not guided or not isinstance(intake, list):
        raise SourceConflict("WP5B1_PATH2_SOURCE_RECORDS_INCOMPLETE")
    intake_by_id = {str(row.get("id")): row for row in intake if isinstance(row, Mapping)}
    if path2.get("training_id") != training[0].get("id") or path2.get("guided_formalisation_id") != guided[0].get("id"):
        raise SourceConflict("WP5B1_PATH2_SOURCE_IDENTITY_MISMATCH")
    if intake_by_id.get(str(path2.get("divergent_intake_id")), {}).get("disposition") != path2.get("divergent_disposition"):
        raise SourceConflict("WP5B1_PATH2_DIVERGENT_DISPOSITION_MISMATCH")
    if wp3.get("real_source_authority") != "NONE" or path2.get("real_source_authority") != "NONE":
        raise AuthorityDenied("WP5B1_PATH2_REAL_SOURCE_AUTHORITY_PROHIBITED")

    wp2 = sources["DMRP_WP2_SYNTHETIC_CANDIDATE"]
    candidate = _object(payload.get("candidate_generation"), "WP5B1_CANDIDATE")
    series = _object(wp2.get("series"), "WP5B1_SOURCE_SERIES")
    generation = _object(wp2.get("generation"), "WP5B1_SOURCE_GENERATION")
    if candidate.get("series_id") != series.get("series_id") or candidate.get("origin_mode") != series.get("origin_mode"):
        raise SourceConflict("WP5B1_CANDIDATE_SERIES_IDENTITY_MISMATCH")
    if candidate.get("generation") != generation.get("generation"):
        raise SourceConflict("WP5B1_CANDIDATE_GENERATION_MISMATCH")
    if candidate.get("population_id") != _object(generation.get("population_binding"), "WP5B1_POP_BINDING").get("population_id"):
        raise SourceConflict("WP5B1_CANDIDATE_POPULATION_MISMATCH")
    memberships = wp2.get("membership")
    if not isinstance(memberships, list):
        raise ContractError("WP5B1_MEMBERSHIP_LIST_REQUIRED")
    observed: dict[str, int] = {}
    for pair in memberships:
        if not isinstance(pair, list) or len(pair) != 2:
            raise ContractError("WP5B1_MEMBERSHIP_PAIR_INVALID")
        observed[str(pair[1])] = observed.get(str(pair[1]), 0) + 1
    if candidate.get("membership") != observed:
        raise SourceConflict("WP5B1_CANDIDATE_MEMBERSHIP_MISMATCH")

    cross_mode = payload.get("cross_mode")
    if not isinstance(cross_mode, list) or not cross_mode:
        raise ContractError("WP5B1_CROSS_MODE_REQUIRED")
    for raw in cross_mode:
        row = _object(raw, "WP5B1_CROSS_MODE_ROW")
        if row.get("path1_candidate_series_id") != series.get("series_id"):
            raise SourceConflict("WP5B1_CROSS_MODE_CANDIDATE_IDENTITY_MISMATCH")
        if row.get("identity_merge") is not False or row.get("winner") is not None or row.get("ranking") is not None:
            raise ContractError("WP5B1_CROSS_MODE_COERCION_PROHIBITED")
        if row.get("independence") == "ESTABLISHED":
            raise ContractError("WP5B1_CORRESPONDENCE_CANNOT_ESTABLISH_INDEPENDENCE")

    negative = payload.get("negative_divergent_evidence")
    if not isinstance(negative, list) or not negative:
        raise ContractError("WP5B1_NEGATIVE_DIVERGENT_EVIDENCE_REQUIRED")
    statuses = {str(row.get("status")) for row in negative if isinstance(row, Mapping)}
    if not {"NOT_EVALUABLE", "UNFORMALISABLE"}.issubset(statuses):
        raise ContractError("WP5B1_NEGATIVE_EVIDENCE_NOT_PRESERVED")

    guardrails = _object(payload.get("presentation_guardrails"), "WP5B1_GUARDRAILS")
    expected_guardrails = {
        "candidate_construction": "PROHIBITED",
        "candidate_repair": "PROHIBITED",
        "candidate_identity_merge": "PROHIBITED",
        "candidate_promotion": "NONE",
        "path_winner": None,
        "ranking": "NONE",
        "correspondence_is_independence": False,
        "missing_exposure_implies_independence": False,
        "frontend_scientific_calculation": "PROHIBITED",
        "writes": "NONE",
        "validation_consumption": "LOCKED_UNCONSUMED",
        "first_new_real_research_source": False,
    }
    for key, expected in expected_guardrails.items():
        if guardrails.get(key) != expected:
            raise ContractError(f"WP5B1_PRESENTATION_GUARDRAIL_INVALID:{key}")

    return copy.deepcopy(payload)
