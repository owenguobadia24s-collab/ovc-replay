from __future__ import annotations

from fnmatch import fnmatchcase
from typing import Any, Iterable, Mapping, Sequence

from ovc.development.identity import canonical_sha256

CLAIM_SCHEMA = "ovc-assurance-claim-spec/v1"
GRAPH_SCHEMA = "ovc-assurance-dependency-graph/v1"
GENERATION_SCHEMA = "ovc-repository-assurance-generation/v1"
IMPACT_SCHEMA = "ovc-mutation-impact-manifest/v1"
PLAN_SCHEMA = "ovc-delta-assurance-plan/v1"
CERTIFICATE_SCHEMA = "ovc-candidate-assurance-certificate/v1"
RECONCILIATION_SCHEMA = "ovc-reference-reconciliation-receipt/v1"

INHERIT_VALID = "INHERIT_VALID"
RERUN_REQUIRED = "RERUN_REQUIRED"
WIDE_RERUN_REQUIRED = "WIDE_RERUN_REQUIRED"
FULL_REFERENCE_REQUIRED = "FULL_REFERENCE_REQUIRED"
NOT_EVALUABLE = "NOT_EVALUABLE"
QUARANTINED = "QUARANTINED"
PLACEMENT_ONLY = "PLACEMENT_ONLY"

PASS = "PASS"
ASSURANCE_MODEL_DIVERGENCE = "ASSURANCE_MODEL_DIVERGENCE"


class RepositoryAssuranceError(ValueError):
    """Raised when repository-assurance continuity cannot be proven safely."""


def _record_id(record: Mapping[str, Any], *, field: str, role: str) -> str:
    logical = {key: value for key, value in record.items() if key != field}
    return canonical_sha256(logical, role=role)


def _require_hex(value: Any, *, length: int, reason: str) -> str:
    text = str(value)
    if len(text) != length or any(ch not in "0123456789abcdef" for ch in text):
        raise RepositoryAssuranceError(reason)
    return text


def _sorted_unique_strings(values: Iterable[Any], *, reason: str) -> list[str]:
    result = sorted({str(value) for value in values})
    if any(not value for value in result):
        raise RepositoryAssuranceError(reason)
    return result


def _token_matches(pattern: str, token: str) -> bool:
    if pattern == token:
        return True
    if any(mark in pattern for mark in "*?["):
        return fnmatchcase(token, pattern)
    return False


def build_assurance_claim_spec(
    *,
    claim_id: str,
    claim_class: str,
    dependencies: Iterable[str],
    harness_id: str,
    execution_profile: str,
    wide_rerun: bool = False,
    unbounded: bool = False,
    reference_only: bool = False,
) -> dict[str, Any]:
    """Build one independently reusable assurance-claim specification."""
    claim_id = str(claim_id)
    spec: dict[str, Any] = {
        "schema": CLAIM_SCHEMA,
        "claim_id": claim_id,
        "claim_class": str(claim_class),
        "dependencies": _sorted_unique_strings(
            dependencies, reason="ASSURANCE_DEPENDENCY_EMPTY"
        ),
        "harness_id": str(harness_id),
        "execution_profile": str(execution_profile),
        "wide_rerun": bool(wide_rerun),
        "unbounded": bool(unbounded),
        "reference_only": bool(reference_only),
    }
    if not claim_id:
        raise RepositoryAssuranceError("ASSURANCE_CLAIM_ID_MISSING")
    if not spec["claim_class"] or not spec["harness_id"] or not spec["execution_profile"]:
        raise RepositoryAssuranceError("ASSURANCE_CLAIM_REQUIRED_FIELD_MISSING")
    spec["claim_spec_id"] = _record_id(
        spec, field="claim_spec_id", role="OVC_ASSURANCE_CLAIM_SPEC"
    )
    return spec


def validate_assurance_claim_spec(spec: Mapping[str, Any]) -> dict[str, Any]:
    if spec.get("schema") != CLAIM_SCHEMA:
        raise RepositoryAssuranceError("ASSURANCE_CLAIM_SCHEMA_INVALID")
    expected = build_assurance_claim_spec(
        claim_id=str(spec.get("claim_id", "")),
        claim_class=str(spec.get("claim_class", "")),
        dependencies=spec.get("dependencies", []),
        harness_id=str(spec.get("harness_id", "")),
        execution_profile=str(spec.get("execution_profile", "")),
        wide_rerun=bool(spec.get("wide_rerun", False)),
        unbounded=bool(spec.get("unbounded", False)),
        reference_only=bool(spec.get("reference_only", False)),
    )
    if spec.get("claim_spec_id") != expected["claim_spec_id"]:
        raise RepositoryAssuranceError("ASSURANCE_CLAIM_IDENTITY_INVALID")
    return expected


def build_assurance_dependency_graph(
    claims: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Create a deterministic claim-to-dependency graph and reverse index."""
    normalized = [validate_assurance_claim_spec(claim) for claim in claims]
    claim_ids = [claim["claim_id"] for claim in normalized]
    if len(claim_ids) != len(set(claim_ids)):
        raise RepositoryAssuranceError("ASSURANCE_CLAIM_DUPLICATE")

    reverse: dict[str, list[str]] = {}
    for claim in normalized:
        for dependency in claim["dependencies"]:
            reverse.setdefault(dependency, []).append(claim["claim_id"])

    graph: dict[str, Any] = {
        "schema": GRAPH_SCHEMA,
        "claims": sorted(normalized, key=lambda item: item["claim_id"]),
        "reverse_dependencies": {
            dependency: sorted(ids) for dependency, ids in sorted(reverse.items())
        },
    }
    graph["graph_id"] = _record_id(
        graph, field="graph_id", role="OVC_ASSURANCE_DEPENDENCY_GRAPH"
    )
    return graph


def validate_assurance_dependency_graph(graph: Mapping[str, Any]) -> dict[str, Any]:
    if graph.get("schema") != GRAPH_SCHEMA:
        raise RepositoryAssuranceError("ASSURANCE_GRAPH_SCHEMA_INVALID")
    expected = build_assurance_dependency_graph(graph.get("claims", []))
    if graph.get("graph_id") != expected["graph_id"]:
        raise RepositoryAssuranceError("ASSURANCE_GRAPH_IDENTITY_INVALID")
    if graph.get("reverse_dependencies") != expected["reverse_dependencies"]:
        raise RepositoryAssuranceError("ASSURANCE_GRAPH_REVERSE_INDEX_INVALID")
    return expected


def build_repository_assurance_generation(
    *,
    repository_tree_sha: str,
    graph_id: str,
    policy_id: str,
    harness_generation_id: str,
    passed_claim_ids: Iterable[str],
    not_evaluable_claim_ids: Iterable[str] = (),
    quarantined_claim_ids: Iterable[str] = (),
    reference_reconciliation_id: str | None = None,
    completeness: str = "COMPLETE_FOR_DECLARED_CLAIM_UNIVERSE",
) -> dict[str, Any]:
    """Certify claim states for one exact physical repository tree."""
    generation: dict[str, Any] = {
        "schema": GENERATION_SCHEMA,
        "repository_tree_sha": _require_hex(
            repository_tree_sha,
            length=40,
            reason="ASSURANCE_GENERATION_TREE_INVALID",
        ),
        "graph_id": _require_hex(
            graph_id,
            length=64,
            reason="ASSURANCE_GENERATION_GRAPH_INVALID",
        ),
        "policy_id": str(policy_id),
        "harness_generation_id": str(harness_generation_id),
        "passed_claim_ids": _sorted_unique_strings(
            passed_claim_ids, reason="ASSURANCE_PASSED_CLAIM_EMPTY"
        ),
        "not_evaluable_claim_ids": _sorted_unique_strings(
            not_evaluable_claim_ids,
            reason="ASSURANCE_NOT_EVALUABLE_CLAIM_EMPTY",
        ),
        "quarantined_claim_ids": _sorted_unique_strings(
            quarantined_claim_ids,
            reason="ASSURANCE_QUARANTINED_CLAIM_EMPTY",
        ),
        "reference_reconciliation_id": reference_reconciliation_id,
        "completeness": str(completeness),
    }
    if (
        not generation["policy_id"]
        or not generation["harness_generation_id"]
        or not generation["completeness"]
    ):
        raise RepositoryAssuranceError("ASSURANCE_GENERATION_REQUIRED_FIELD_MISSING")

    passed = set(generation["passed_claim_ids"])
    not_evaluable = set(generation["not_evaluable_claim_ids"])
    quarantined = set(generation["quarantined_claim_ids"])
    if (
        passed & not_evaluable
        or passed & quarantined
        or not_evaluable & quarantined
    ):
        raise RepositoryAssuranceError("ASSURANCE_GENERATION_CLAIM_STATE_OVERLAP")

    generation["generation_id"] = _record_id(
        generation,
        field="generation_id",
        role="OVC_REPOSITORY_ASSURANCE_GENERATION",
    )
    return generation


def validate_repository_assurance_generation(
    generation: Mapping[str, Any],
) -> dict[str, Any]:
    if generation.get("schema") != GENERATION_SCHEMA:
        raise RepositoryAssuranceError("ASSURANCE_GENERATION_SCHEMA_INVALID")
    expected = build_repository_assurance_generation(
        repository_tree_sha=str(generation.get("repository_tree_sha", "")),
        graph_id=str(generation.get("graph_id", "")),
        policy_id=str(generation.get("policy_id", "")),
        harness_generation_id=str(generation.get("harness_generation_id", "")),
        passed_claim_ids=generation.get("passed_claim_ids", []),
        not_evaluable_claim_ids=generation.get("not_evaluable_claim_ids", []),
        quarantined_claim_ids=generation.get("quarantined_claim_ids", []),
        reference_reconciliation_id=generation.get("reference_reconciliation_id"),
        completeness=str(generation.get("completeness", "")),
    )
    if generation.get("generation_id") != expected["generation_id"]:
        raise RepositoryAssuranceError("ASSURANCE_GENERATION_IDENTITY_INVALID")
    return expected


def build_mutation_impact_manifest(
    *,
    programme_id: str,
    packet_id: str,
    payload_id: str,
    changed_tokens: Iterable[str],
    classified_tokens: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Bind one immutable PIP to its exact logical mutation surface."""
    changed = _sorted_unique_strings(
        changed_tokens, reason="MUTATION_IMPACT_TOKEN_EMPTY"
    )
    classified = _sorted_unique_strings(
        changed if classified_tokens is None else classified_tokens,
        reason="MUTATION_CLASSIFIED_TOKEN_EMPTY",
    )
    if not set(classified).issubset(changed):
        raise RepositoryAssuranceError("MUTATION_CLASSIFICATION_NOT_SUBSET")

    manifest: dict[str, Any] = {
        "schema": IMPACT_SCHEMA,
        "programme_id": str(programme_id),
        "packet_id": str(packet_id),
        "payload_id": _require_hex(
            payload_id, length=64, reason="MUTATION_PAYLOAD_ID_INVALID"
        ),
        "changed_tokens": changed,
        "classified_tokens": classified,
        "unclassified_tokens": sorted(set(changed) - set(classified)),
    }
    if not manifest["programme_id"] or not manifest["packet_id"]:
        raise RepositoryAssuranceError("MUTATION_IDENTITY_MISSING")
    manifest["impact_manifest_id"] = _record_id(
        manifest,
        field="impact_manifest_id",
        role="OVC_MUTATION_IMPACT_MANIFEST",
    )
    return manifest


def validate_mutation_impact_manifest(
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    if manifest.get("schema") != IMPACT_SCHEMA:
        raise RepositoryAssuranceError("MUTATION_IMPACT_SCHEMA_INVALID")
    expected = build_mutation_impact_manifest(
        programme_id=str(manifest.get("programme_id", "")),
        packet_id=str(manifest.get("packet_id", "")),
        payload_id=str(manifest.get("payload_id", "")),
        changed_tokens=manifest.get("changed_tokens", []),
        classified_tokens=manifest.get("classified_tokens", []),
    )
    if manifest.get("impact_manifest_id") != expected["impact_manifest_id"]:
        raise RepositoryAssuranceError("MUTATION_IMPACT_IDENTITY_INVALID")
    if manifest.get("unclassified_tokens") != expected["unclassified_tokens"]:
        raise RepositoryAssuranceError("MUTATION_IMPACT_UNCLASSIFIED_INVALID")
    return expected


def _claim_intersections(
    claim: Mapping[str, Any], changed_tokens: Sequence[str]
) -> list[str]:
    intersections: set[str] = set()
    for dependency in claim["dependencies"]:
        for token in changed_tokens:
            if _token_matches(dependency, token):
                intersections.add(token)
    return sorted(intersections)


def build_delta_assurance_plan(
    *,
    base_generation: Mapping[str, Any],
    graph: Mapping[str, Any],
    impact_manifest: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Classify every registered assurance claim for one exact PIP."""
    base = validate_repository_assurance_generation(base_generation)
    normalized_graph = validate_assurance_dependency_graph(graph)
    impact = validate_mutation_impact_manifest(impact_manifest)
    if base["graph_id"] != normalized_graph["graph_id"]:
        raise RepositoryAssuranceError("DELTA_PLAN_GRAPH_GENERATION_MISMATCH")

    changed = impact["changed_tokens"]
    unclassified = impact["unclassified_tokens"]
    global_patterns = [
        str(item) for item in policy.get("global_invalidation_patterns", [])
    ]
    full_reference_reasons: list[str] = []
    if policy.get("fail_closed_on_unclassified", True) and unclassified:
        full_reference_reasons.append("UNCLASSIFIED_MUTATION")
    for pattern in global_patterns:
        if any(_token_matches(pattern, token) for token in changed):
            full_reference_reasons.append(f"GLOBAL_INVALIDATION:{pattern}")

    passed = set(base["passed_claim_ids"])
    not_evaluable = set(base["not_evaluable_claim_ids"])
    quarantined = set(base["quarantined_claim_ids"])
    dispositions: list[dict[str, Any]] = []

    for claim in normalized_graph["claims"]:
        claim_id = claim["claim_id"]
        intersections = _claim_intersections(claim, changed)
        reasons: list[str] = []
        if claim["unbounded"] or claim["reference_only"]:
            disposition = FULL_REFERENCE_REQUIRED
            reasons.append("CLAIM_UNBOUNDED_OR_REFERENCE_ONLY")
            full_reference_reasons.append(f"CLAIM:{claim_id}")
        elif claim_id in quarantined:
            disposition = QUARANTINED
            reasons.append("BASE_CLAIM_QUARANTINED")
        elif claim_id in not_evaluable:
            disposition = NOT_EVALUABLE
            reasons.append("BASE_CLAIM_NOT_EVALUABLE")
        elif claim_id not in passed:
            disposition = RERUN_REQUIRED
            reasons.append("NO_INHERITABLE_PASS")
        elif intersections:
            disposition = (
                WIDE_RERUN_REQUIRED if claim["wide_rerun"] else RERUN_REQUIRED
            )
            reasons.append("DECLARED_DEPENDENCY_INTERSECTION")
        else:
            disposition = INHERIT_VALID
            reasons.append("UNCHANGED_DECLARED_DEPENDENCIES")

        dispositions.append(
            {
                "claim_id": claim_id,
                "disposition": disposition,
                "intersections": intersections,
                "reasons": reasons,
            }
        )

    reference_required = bool(full_reference_reasons)
    if reference_required:
        for row in dispositions:
            if row["disposition"] in {
                INHERIT_VALID,
                RERUN_REQUIRED,
                WIDE_RERUN_REQUIRED,
            }:
                row["disposition"] = FULL_REFERENCE_REQUIRED
                row["reasons"].append("PLAN_LEVEL_FULL_REFERENCE_ESCALATION")

    plan: dict[str, Any] = {
        "schema": PLAN_SCHEMA,
        "base_generation_id": base["generation_id"],
        "graph_id": normalized_graph["graph_id"],
        "impact_manifest_id": impact["impact_manifest_id"],
        "payload_id": impact["payload_id"],
        "policy_id": str(policy.get("policy_id", "")),
        "claim_dispositions": sorted(
            dispositions, key=lambda item: item["claim_id"]
        ),
        "reference_required": reference_required,
        "reference_reasons": sorted(set(full_reference_reasons)),
        "payload_rebuild_required": False,
    }
    if not plan["policy_id"]:
        raise RepositoryAssuranceError("DELTA_PLAN_POLICY_ID_MISSING")
    plan["summary"] = {
        state: sum(
            1
            for row in plan["claim_dispositions"]
            if row["disposition"] == state
        )
        for state in (
            INHERIT_VALID,
            RERUN_REQUIRED,
            WIDE_RERUN_REQUIRED,
            FULL_REFERENCE_REQUIRED,
            NOT_EVALUABLE,
            QUARANTINED,
        )
    }
    plan["plan_id"] = _record_id(
        plan, field="plan_id", role="OVC_DELTA_ASSURANCE_PLAN"
    )
    return plan


def validate_delta_assurance_plan(plan: Mapping[str, Any]) -> str:
    if plan.get("schema") != PLAN_SCHEMA:
        raise RepositoryAssuranceError("DELTA_PLAN_SCHEMA_INVALID")
    expected = _record_id(
        plan, field="plan_id", role="OVC_DELTA_ASSURANCE_PLAN"
    )
    if plan.get("plan_id") != expected:
        raise RepositoryAssuranceError("DELTA_PLAN_IDENTITY_INVALID")
    return expected


def build_candidate_assurance_certificate(
    *,
    plan: Mapping[str, Any],
    executed_results: Mapping[str, str],
    reference_result: str | None = None,
) -> dict[str, Any]:
    """Prove that every blocking assurance obligation is satisfied."""
    validate_delta_assurance_plan(plan)
    results = {str(key): str(value) for key, value in executed_results.items()}
    inherited: list[str] = []
    executed: list[str] = []

    for row in plan.get("claim_dispositions", []):
        claim_id = str(row["claim_id"])
        disposition = row["disposition"]
        if disposition == INHERIT_VALID:
            inherited.append(claim_id)
        elif disposition in {RERUN_REQUIRED, WIDE_RERUN_REQUIRED}:
            if results.get(claim_id) != PASS:
                raise RepositoryAssuranceError(
                    f"CANDIDATE_ASSURANCE_CLAIM_NOT_PASS:{claim_id}"
                )
            executed.append(claim_id)
        elif disposition == FULL_REFERENCE_REQUIRED:
            if reference_result != PASS:
                raise RepositoryAssuranceError(
                    "CANDIDATE_ASSURANCE_REFERENCE_REQUIRED"
                )
        elif disposition == NOT_EVALUABLE:
            raise RepositoryAssuranceError(
                f"CANDIDATE_ASSURANCE_NOT_EVALUABLE:{claim_id}"
            )
        elif disposition == QUARANTINED:
            raise RepositoryAssuranceError(
                f"CANDIDATE_ASSURANCE_QUARANTINED:{claim_id}"
            )
        else:
            raise RepositoryAssuranceError(
                f"CANDIDATE_ASSURANCE_DISPOSITION_UNKNOWN:{disposition}"
            )

    certificate: dict[str, Any] = {
        "schema": CERTIFICATE_SCHEMA,
        "plan_id": plan["plan_id"],
        "payload_id": plan["payload_id"],
        "inherited_claim_ids": sorted(inherited),
        "executed_claim_ids": sorted(executed),
        "executed_results": {key: results[key] for key in sorted(executed)},
        "reference_result": reference_result,
        "status": PASS,
        "authority_effect": "NONE",
    }
    certificate["certificate_id"] = _record_id(
        certificate,
        field="certificate_id",
        role="OVC_CANDIDATE_ASSURANCE_CERTIFICATE",
    )
    return certificate


def validate_candidate_assurance_certificate(
    certificate: Mapping[str, Any],
) -> str:
    if certificate.get("schema") != CERTIFICATE_SCHEMA:
        raise RepositoryAssuranceError("CANDIDATE_CERTIFICATE_SCHEMA_INVALID")
    if certificate.get("status") != PASS or certificate.get("authority_effect") != "NONE":
        raise RepositoryAssuranceError("CANDIDATE_CERTIFICATE_STATE_INVALID")
    expected = _record_id(
        certificate,
        field="certificate_id",
        role="OVC_CANDIDATE_ASSURANCE_CERTIFICATE",
    )
    if certificate.get("certificate_id") != expected:
        raise RepositoryAssuranceError("CANDIDATE_CERTIFICATE_IDENTITY_INVALID")
    return expected


def build_reference_reconciliation_receipt(
    *,
    certificate: Mapping[str, Any],
    reference_results: Mapping[str, str],
    expected_claim_ids: Iterable[str],
) -> dict[str, Any]:
    """Compare the incremental certificate with the complete reference oracle."""
    validate_candidate_assurance_certificate(certificate)
    expected = _sorted_unique_strings(
        expected_claim_ids, reason="REFERENCE_EXPECTED_CLAIM_EMPTY"
    )
    results = {str(key): str(value) for key, value in reference_results.items()}
    missing = sorted(set(expected) - set(results))
    failing = sorted(
        claim_id for claim_id in expected if results.get(claim_id) != PASS
    )
    receipt: dict[str, Any] = {
        "schema": RECONCILIATION_SCHEMA,
        "certificate_id": certificate["certificate_id"],
        "expected_claim_ids": expected,
        "missing_claim_ids": missing,
        "failing_claim_ids": failing,
        "status": PASS if not missing and not failing else ASSURANCE_MODEL_DIVERGENCE,
    }
    receipt["reconciliation_id"] = _record_id(
        receipt,
        field="reconciliation_id",
        role="OVC_REFERENCE_RECONCILIATION_RECEIPT",
    )
    return receipt


def validate_reference_reconciliation_receipt(
    receipt: Mapping[str, Any],
) -> str:
    if receipt.get("schema") != RECONCILIATION_SCHEMA:
        raise RepositoryAssuranceError("REFERENCE_RECONCILIATION_SCHEMA_INVALID")
    expected = _record_id(
        receipt,
        field="reconciliation_id",
        role="OVC_REFERENCE_RECONCILIATION_RECEIPT",
    )
    if receipt.get("reconciliation_id") != expected:
        raise RepositoryAssuranceError(
            "REFERENCE_RECONCILIATION_IDENTITY_INVALID"
        )
    return expected


def advance_repository_assurance_generation(
    *,
    physical_tree_sha: str,
    graph: Mapping[str, Any],
    policy_id: str,
    harness_generation_id: str,
    certificate: Mapping[str, Any],
    reconciliation_receipt: Mapping[str, Any] | None,
    completeness: str,
) -> dict[str, Any]:
    """Create the next physical-tree generation after exact materialisation."""
    validate_candidate_assurance_certificate(certificate)
    normalized_graph = validate_assurance_dependency_graph(graph)
    reconciliation_id: str | None = None
    if reconciliation_receipt is not None:
        reconciliation_id = validate_reference_reconciliation_receipt(
            reconciliation_receipt
        )
        if reconciliation_receipt.get("status") != PASS:
            raise RepositoryAssuranceError(
                "ASSURANCE_MODEL_DIVERGENCE_BLOCKS_GENERATION_ADVANCE"
            )
        if reconciliation_receipt.get("certificate_id") != certificate.get(
            "certificate_id"
        ):
            raise RepositoryAssuranceError(
                "REFERENCE_RECONCILIATION_CERTIFICATE_MISMATCH"
            )

    all_claim_ids = [claim["claim_id"] for claim in normalized_graph["claims"]]
    return build_repository_assurance_generation(
        repository_tree_sha=physical_tree_sha,
        graph_id=normalized_graph["graph_id"],
        policy_id=policy_id,
        harness_generation_id=harness_generation_id,
        passed_claim_ids=all_claim_ids,
        reference_reconciliation_id=reconciliation_id,
        completeness=completeness,
    )


def main_movement_assurance_disposition(
    *,
    changed_tokens: Iterable[str],
    candidate_dependency_tokens: Iterable[str],
    policy: Mapping[str, Any],
) -> str:
    """Classify ordinary main movement without contaminating PIP identity."""
    changed = _sorted_unique_strings(
        changed_tokens, reason="MAIN_MOVEMENT_TOKEN_EMPTY"
    )
    dependencies = _sorted_unique_strings(
        candidate_dependency_tokens,
        reason="MAIN_MOVEMENT_DEPENDENCY_EMPTY",
    )
    global_patterns = [
        str(item) for item in policy.get("global_invalidation_patterns", [])
    ]
    if any(
        _token_matches(pattern, token)
        for pattern in global_patterns
        for token in changed
    ):
        return FULL_REFERENCE_REQUIRED
    if any(
        _token_matches(pattern, token)
        for pattern in dependencies
        for token in changed
    ):
        return RERUN_REQUIRED
    return PLACEMENT_ONLY
