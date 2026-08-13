"""Fail-closed WP5A representation fixture projection.

The service verifies exact repository fixture identities and presents source-owned
fixture declarations. It never executes a scientific method, chooses a winner,
reads a provider, consumes Validation, or resolves a real Research source.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .errors import AuthorityDenied, ContractError, SourceConflict

_BINDING_SCHEMA = "ovc-rcn-rn-wp5a-representation-source-bindings/v1"
_SNAPSHOT_SCHEMA = "ovc-rcn-rn-wp5a-representation-snapshot/v1"
_REQUIRED_OUTCOMES = {"RESIDUAL", "AMBIGUOUS", "NO_STABLE_FAMILY"}
_ALLOWED_SOURCE_CLASSES = {"SYNTHETIC_FIXTURE"}


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
        raise ContractError("WP5A_SOURCE_PATH_RELATIVE_REQUIRED")
    root_resolved = root.resolve()
    candidate = (root_resolved / relative).resolve(strict=False)
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise ContractError("WP5A_SOURCE_PATH_ESCAPES_REPOSITORY") from exc
    if not candidate.is_file():
        raise ContractError(f"WP5A_SOURCE_FILE_MISSING:{relative}")
    return candidate


def git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()


def _fixture_index(source: Mapping[str, Any], source_id: str) -> dict[str, dict[str, Any]]:
    fixtures = source.get("fixtures")
    if not isinstance(fixtures, list):
        raise ContractError(f"WP5A_SOURCE_FIXTURES_LIST_REQUIRED:{source_id}")
    result: dict[str, dict[str, Any]] = {}
    for row in fixtures:
        item = _object(row, f"WP5A_FIXTURE:{source_id}")
        fixture_id = item.get("id", item.get("fixture_id"))
        if not isinstance(fixture_id, str) or not fixture_id:
            raise ContractError(f"WP5A_FIXTURE_ID_REQUIRED:{source_id}")
        if fixture_id in result:
            raise ContractError(f"WP5A_DUPLICATE_FIXTURE_ID:{source_id}:{fixture_id}")
        result[fixture_id] = item
    return result


def build_wp5a_representation_snapshot(
    *,
    repository_root: Path,
    presentation: Mapping[str, Any] | Path,
    bindings: Mapping[str, Any] | Path,
) -> dict[str, Any]:
    registry = _load(bindings, "WP5A_BINDINGS")
    payload = _load(presentation, "WP5A_PRESENTATION")

    if registry.get("schema") != _BINDING_SCHEMA:
        raise ContractError("WP5A_BINDING_SCHEMA_INVALID")
    if payload.get("schema") != _SNAPSHOT_SCHEMA:
        raise ContractError("WP5A_SNAPSHOT_SCHEMA_INVALID")
    if registry.get("packet_id") != "RCN-RN-WP5A" or payload.get("packet_id") != "RCN-RN-WP5A":
        raise SourceConflict("WP5A_PACKET_IDENTITY_MISMATCH")
    if registry.get("authority_effect") != "NONE" or payload.get("authority_effect") != "NONE":
        raise AuthorityDenied("WP5A_AUTHORITY_EFFECT_MUST_BE_NONE")
    if registry.get("transport") != "GET_ONLY" or registry.get("writes") != "NONE":
        raise AuthorityDenied("WP5A_GET_ONLY_WRITE_DENY_REQUIRED")
    if registry.get("validation_consumption") != "LOCKED_UNCONSUMED":
        raise AuthorityDenied("WP5A_VALIDATION_MUST_REMAIN_LOCKED")
    if registry.get("presentation_mode") != "FIXTURE_ONLY" or registry.get("evidence_status") != "NON_EVIDENTIARY":
        raise AuthorityDenied("WP5A_FIXTURE_NON_EVIDENTIARY_REQUIRED")
    if registry.get("first_new_real_research_source") is not False:
        raise AuthorityDenied("WP5A_FIRST_NEW_REAL_RESEARCH_SOURCE_REQUIRES_OPERATOR_G5")
    if registry.get("gate_branch") != "RCN-RN-WP5A-CLOSEOUT":
        raise AuthorityDenied("WP5A_AUTO_GATE_BRANCH_INVALID")

    raw_sources = registry.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise ContractError("WP5A_SOURCE_BINDINGS_REQUIRED")

    source_bindings: dict[str, dict[str, Any]] = {}
    source_fixtures: dict[str, dict[str, dict[str, Any]]] = {}
    for raw in raw_sources:
        binding = _object(raw, "WP5A_SOURCE_BINDING")
        source_id = binding.get("source_id")
        if not isinstance(source_id, str) or not source_id:
            raise ContractError("WP5A_SOURCE_ID_REQUIRED")
        if source_id in source_bindings:
            raise ContractError(f"WP5A_DUPLICATE_SOURCE_ID:{source_id}")
        if binding.get("source_class") not in _ALLOWED_SOURCE_CLASSES:
            raise AuthorityDenied(f"WP5A_SOURCE_CLASS_NOT_AUTO_EXECUTABLE:{source_id}")
        if binding.get("first_new_real_research_source") is not False:
            raise AuthorityDenied(f"WP5A_FIRST_NEW_REAL_RESEARCH_SOURCE:{source_id}")
        path = _repo_path(Path(repository_root), str(binding.get("path", "")))
        observed_blob = git_blob_sha(path)
        if observed_blob != binding.get("git_blob_sha"):
            raise SourceConflict(f"WP5A_SOURCE_BLOB_MISMATCH:{source_id}")
        source = _load(path, f"WP5A_SOURCE:{source_id}")
        if source.get("schema") != binding.get("schema"):
            raise SourceConflict(f"WP5A_SOURCE_SCHEMA_MISMATCH:{source_id}")
        authority_field = binding.get("authority_field")
        if source.get(authority_field) != binding.get("authority_value"):
            raise AuthorityDenied(f"WP5A_SOURCE_AUTHORITY_MARKER_INVALID:{source_id}")
        source_bindings[source_id] = binding
        source_fixtures[source_id] = _fixture_index(source, source_id)

    preflight = _object(payload.get("source_preflight"), "WP5A_SOURCE_PREFLIGHT")
    if preflight.get("status") != "PASS_NO_FIRST_NEW_REAL_RESEARCH_SOURCE":
        raise AuthorityDenied("WP5A_SOURCE_PREFLIGHT_NOT_PASS")
    if preflight.get("first_new_real_research_source") is not False:
        raise AuthorityDenied("WP5A_PRESENTATION_FIRST_NEW_REAL_SOURCE")
    declared_source_ids = preflight.get("source_ids")
    if not isinstance(declared_source_ids, list) or set(declared_source_ids) != set(source_bindings):
        raise SourceConflict("WP5A_PRESENTATION_SOURCE_SET_MISMATCH")

    refs = payload.get("source_fixture_refs")
    if not isinstance(refs, list) or not refs:
        raise ContractError("WP5A_SOURCE_FIXTURE_REFS_REQUIRED")
    seen_refs: set[tuple[str, str]] = set()
    for raw in refs:
        ref = _object(raw, "WP5A_SOURCE_FIXTURE_REF")
        source_id = ref.get("source_id")
        fixture_id = ref.get("fixture_id")
        key = (str(source_id), str(fixture_id))
        if key in seen_refs:
            raise ContractError(f"WP5A_DUPLICATE_SOURCE_FIXTURE_REF:{key[0]}:{key[1]}")
        seen_refs.add(key)
        fixture = source_fixtures.get(str(source_id), {}).get(str(fixture_id))
        if fixture is None:
            raise SourceConflict(f"WP5A_SOURCE_FIXTURE_NOT_FOUND:{source_id}:{fixture_id}")
        if fixture.get("expected") != ref.get("expected"):
            raise SourceConflict(f"WP5A_SOURCE_FIXTURE_EXPECTATION_MISMATCH:{source_id}:{fixture_id}")

    methods = payload.get("methods")
    if not isinstance(methods, list) or not methods:
        raise ContractError("WP5A_METHODS_REQUIRED")
    for raw in methods:
        method = _object(raw, "WP5A_METHOD")
        if method.get("winner") is not None:
            raise ContractError(f"WP5A_METHOD_WINNER_PROHIBITED:{method.get('method_id')}")
        if method.get("selection_authority") != "NONE":
            raise AuthorityDenied(f"WP5A_METHOD_SELECTION_AUTHORITY_PROHIBITED:{method.get('method_id')}")
        if (str(method.get("source_id")), str(method.get("source_fixture_id"))) not in seen_refs:
            raise SourceConflict(f"WP5A_METHOD_SOURCE_REF_MISSING:{method.get('method_id')}")

    comparability = payload.get("comparability")
    if not isinstance(comparability, list) or not comparability:
        raise ContractError("WP5A_COMPARABILITY_REQUIRED")
    for raw in comparability:
        comparison = _object(raw, "WP5A_COMPARISON")
        if comparison.get("winner") is not None:
            raise ContractError(f"WP5A_COMPARISON_WINNER_PROHIBITED:{comparison.get('comparison_id')}")
        if comparison.get("status") == "NOT_COMPARABLE" and comparison.get("distance_engine_called") is not False:
            raise ContractError(f"WP5A_DISTANCE_ENGINE_CALLED_FOR_NOT_COMPARABLE:{comparison.get('comparison_id')}")

    outcomes = payload.get("family_outcomes")
    if not isinstance(outcomes, list):
        raise ContractError("WP5A_FAMILY_OUTCOMES_REQUIRED")
    outcome_names = {str(row.get("outcome")) for row in outcomes if isinstance(row, Mapping)}
    if outcome_names != _REQUIRED_OUTCOMES:
        raise ContractError("WP5A_EQUAL_STATUS_OUTCOME_SET_INVALID")
    for raw in outcomes:
        outcome = _object(raw, "WP5A_FAMILY_OUTCOME")
        if outcome.get("status") != "LAWFUL_EQUAL_STATUS" or outcome.get("authority_effect") != "NONE":
            raise ContractError(f"WP5A_FAMILY_OUTCOME_NOT_EQUAL_STATUS:{outcome.get('outcome')}")

    population = _object(payload.get("population"), "WP5A_POPULATION")
    counts = [population.get(key) for key in ("evaluable_count", "missing_count", "denominator")]
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in counts):
        raise ContractError("WP5A_POPULATION_COUNTS_INVALID")
    if counts[0] + counts[1] != counts[2]:
        raise ContractError("WP5A_POPULATION_DENOMINATOR_MISMATCH")
    if population.get("truncated") is not False:
        raise ContractError("WP5A_SILENT_OR_UNDECLARED_TRUNCATION")

    denominator = _object(payload.get("outcome_denominator"), "WP5A_OUTCOME_DENOMINATOR")
    outcome_counts = [
        denominator.get("residual_count"),
        denominator.get("ambiguous_count"),
        denominator.get("no_stable_family_count"),
    ]
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in outcome_counts):
        raise ContractError("WP5A_OUTCOME_COUNTS_INVALID")
    if sum(outcome_counts) != denominator.get("denominator"):
        raise ContractError("WP5A_OUTCOME_DENOMINATOR_MISMATCH")
    by_name = {str(row["outcome"]): row["count"] for row in outcomes}
    expected_counts = {
        "RESIDUAL": denominator["residual_count"],
        "AMBIGUOUS": denominator["ambiguous_count"],
        "NO_STABLE_FAMILY": denominator["no_stable_family_count"],
    }
    if by_name != expected_counts:
        raise ContractError("WP5A_OUTCOME_COUNT_PROJECTION_MISMATCH")

    guardrails = _object(payload.get("presentation_guardrails"), "WP5A_PRESENTATION_GUARDRAILS")
    required_guardrails = {
        "method_first": True,
        "family_first": False,
        "default_winner": None,
        "scientific_strength_score": None,
        "frontend_scientific_calculation": "PROHIBITED",
        "selector_authority": "NONE",
        "writes": "NONE",
        "validation_consumption": "LOCKED_UNCONSUMED",
        "no_forced_assignment": True,
        "correspondence_is_independence": False,
    }
    for key, expected in required_guardrails.items():
        if guardrails.get(key) != expected:
            raise ContractError(f"WP5A_PRESENTATION_GUARDRAIL_INVALID:{key}")
    if set(guardrails.get("equal_status_outcomes", [])) != _REQUIRED_OUTCOMES:
        raise ContractError("WP5A_GUARDRAIL_EQUAL_STATUS_SET_INVALID")

    return copy.deepcopy(payload)
