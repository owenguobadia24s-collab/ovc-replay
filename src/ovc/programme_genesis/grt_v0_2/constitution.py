from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .bootstrap import (
    DIALECT,
    PROFILE_ID,
    VALIDATOR_RELEASE,
    BootstrapValidationError,
    load_json,
    validate_instance,
    validate_manifest_dag,
    validate_registry_unique,
    validate_schema,
)
from .serialization import SERIALIZATION_ID, canonical_sha256, file_sha256


CONSTITUTION_ID = "OVC-GRT-REPOSITORY-CONSTITUTION-v0.2"
CONSTITUTION_STATUS = "PROPOSED_UNADMITTED"
BASELINE_COMMIT = "d41a29f9895482de0d1515efc2ca0aebf8016b45"
BASELINE_TREE = "7f4fba22eec37ab7c257334fb6ac1624bd4bf23f"

SCHEMA_DIR = Path("schemas/governance/grt_v0_2")
REGISTRY_DIR = Path("registries/governance/grt_v0_2")
CONTRACT_DIR = Path("contracts/governance/grt_v0_2")

OBSERVED_ROOTS = (
    ".agents",
    ".github",
    "apps",
    "artifacts",
    "benchmarks",
    "contracts",
    "data",
    "design",
    "docs",
    "fixtures",
    "legacy",
    "plans",
    "qa",
    "records",
    "registries",
    "schemas",
    "scripts",
    "src",
    "tests",
    "tools",
)

ARTIFACT_CLASSES = (
    "IMPLEMENTATION",
    "CONTRACT",
    "SCHEMA",
    "REGISTRY",
    "FIXTURE",
    "TEST",
    "WORKFLOW",
    "PLAN",
    "DESIGN_SPECIFICATION",
    "DECISION_RECORD",
    "PROGRAMME_STATE",
    "DOCUMENTATION",
    "READ_MODEL",
    "GENERATED_ARTIFACT",
    "EVIDENCE_POINTER",
    "TOOLING",
    "CONFIGURATION",
    "MIGRATION",
    "ARCHIVE_INDEX",
)

LIFECYCLE_CLASSES = (
    "CURRENT_AUTHORITATIVE",
    "CURRENT_IMPLEMENTATION",
    "CURRENT_SUPPORTING",
    "PROPOSED_UNADMITTED",
    "HISTORICAL_IMMUTABLE",
    "DERIVED_GENERATED",
    "QUARANTINED",
    "EPHEMERAL_LOCAL",
)

RELATIONSHIP_TYPES = (
    "OWNED_BY",
    "GOVERNED_BY",
    "CROSSWALKS_TO",
    "IMPLEMENTS",
    "TESTS",
    "FIXTURES",
    "DOCUMENTS",
    "DEPENDS_ON",
    "GENERATED_FROM",
    "SUPERSEDES",
    "COMPATIBLE_WITH",
    "ARCHIVES",
    "PROJECTS",
    "REFERENCES",
    "QUARANTINES",
)

POLICY_FILES = (
    "REPOSITORY_CONSTITUTION_v0_2.md",
    "GRT_CURRENT_STATE_POLICY_v0_1.md",
    "GRT_INFORMATION_ARCHITECTURE_POLICY_v0_1.md",
    "GRT_SUPERSESSION_POLICY_v0_1.md",
    "GRT_CONSTITUTION_AMENDMENT_PROTOCOL_v0_1.md",
    "GRT_OVERRIDE_PROTOCOL_v0_1.md",
    "GRT_HISTORICAL_DISPOSITION_POLICY_v0_1.md",
    "GRT_BOOTSTRAP_VALIDATION_CONTRACT_v0_1.md",
)

SCHEMA_FILES = (
    "repository_constitution.schema.json",
    "repository_root_record.schema.json",
    "artifact_class.schema.json",
    "lifecycle_class.schema.json",
    "artifact_relationship.schema.json",
    "grt_conformance_rule.schema.json",
    "current_state_obligation.schema.json",
    "constitution_amendment.schema.json",
    "conformance_override.schema.json",
    "historical_disposition.schema.json",
    "information_architecture_policy.schema.json",
    "supersession_policy.schema.json",
    "bootstrap_validation_manifest.schema.json",
)

RULE_SEEDS: tuple[dict[str, Any], ...] = (
    {
        "rule_id": "GRT-R001",
        "rule_version": "1",
        "rule_family": "ROOTS_AND_PLACEMENT",
        "name": "PERMANENT_ROOT_REGISTERED",
        "subject_selector": {"artifact_types": [], "lifecycle_classes": [], "root_statuses": ["PERMANENT_CURRENT", "DEPRECATED_NO_NEW_WRITES"]},
        "applicability_predicate": "permanent_top_level_directory_observed",
        "evidence_requirements": ["exact_tree_path", "root_registry_entry"],
        "cardinality_contract": {"minimum": 1, "maximum": 1},
        "violation_predicate": "no_exact_root_registry_entry",
        "default_severity": "ERROR",
        "debt_effect": "ACTIONABLE_DEBT",
        "candidate_admission_effect": "FAIL",
        "historical_policy": "PRESERVE_FINDING_LINEAGE",
        "remediation_class": "REGISTER_OR_DISPOSITION_ROOT",
        "authority_class": "AUTO_EXECUTABLE_IF_SOURCE_EXPLICIT",
    },
    {
        "rule_id": "GRT-R005",
        "rule_version": "1",
        "rule_family": "ROOTS_AND_PLACEMENT",
        "name": "DEPRECATED_ROOT_NEW_WRITE_FORBIDDEN",
        "subject_selector": {"artifact_types": [], "lifecycle_classes": [], "root_statuses": ["DEPRECATED_NO_NEW_WRITES"]},
        "applicability_predicate": "candidate_adds_or_moves_canonical_content_into_deprecated_root",
        "evidence_requirements": ["predecessor_tree", "candidate_tree", "root_registry_entry"],
        "cardinality_contract": {"minimum": 0, "maximum": 0},
        "violation_predicate": "new_canonical_write_in_deprecated_root",
        "default_severity": "BLOCKER",
        "debt_effect": "ACTIONABLE_DEBT",
        "candidate_admission_effect": "FAIL",
        "historical_policy": "PREEXISTING_CONTENT_MAY_REMAIN",
        "remediation_class": "MOVE_TO_LAWFUL_ROOT_OR_REMOVE_CANDIDATE_WRITE",
        "authority_class": "AUTO_EXECUTABLE",
    },
    {
        "rule_id": "GRT-R100",
        "rule_version": "1",
        "rule_family": "ARTIFACT_CLASSIFICATION",
        "name": "GOVERNED_ARTIFACT_CLASSIFIED",
        "subject_selector": {"artifact_types": list(ARTIFACT_CLASSES), "lifecycle_classes": list(LIFECYCLE_CLASSES), "root_statuses": []},
        "applicability_predicate": "permanent_governed_component_observed",
        "evidence_requirements": ["repository_artifact_identity", "artifact_class_registry_entry"],
        "cardinality_contract": {"minimum": 1, "maximum": 1},
        "violation_predicate": "missing_or_ambiguous_artifact_class",
        "default_severity": "ERROR",
        "debt_effect": "ACTIONABLE_DEBT",
        "candidate_admission_effect": "FAIL",
        "historical_policy": "LEGACY_LOCATOR_ALLOWED_WITH_EXPLICIT_LIFECYCLE",
        "remediation_class": "MATERIALISE_CLASSIFICATION",
        "authority_class": "AUTO_EXECUTABLE_IF_SOURCE_EXPLICIT",
    },
    {
        "rule_id": "GRT-R200",
        "rule_version": "1",
        "rule_family": "OWNERSHIP",
        "name": "CURRENT_IMPLEMENTATION_OWNER_REQUIRED",
        "subject_selector": {"artifact_types": ["IMPLEMENTATION"], "lifecycle_classes": ["CURRENT_IMPLEMENTATION"], "root_statuses": []},
        "applicability_predicate": "current_implementation_artifact",
        "evidence_requirements": ["OWNED_BY relationship", "programme authority record"],
        "cardinality_contract": {"minimum": 1, "maximum": 1},
        "violation_predicate": "owner_missing_or_conflicting_without_shared_service_contract",
        "default_severity": "ERROR",
        "debt_effect": "ACTIONABLE_DEBT",
        "candidate_admission_effect": "FAIL",
        "historical_policy": "HISTORICAL_OWNER_GAPS_DISPOSITIONED_SEPARATELY",
        "remediation_class": "MATERIALISE_OWNER_OR_OPERATOR_RESOLVE",
        "authority_class": "OPERATOR_REQUIRED_IF_CONFLICTING",
    },
    {
        "rule_id": "GRT-R300",
        "rule_version": "1",
        "rule_family": "GENESIS_BINDINGS",
        "name": "REQUIRED_GENESIS_BINDING_PRESENT",
        "subject_selector": {"artifact_types": ["IMPLEMENTATION", "PLAN", "PROGRAMME_STATE"], "lifecycle_classes": ["CURRENT_AUTHORITATIVE", "CURRENT_IMPLEMENTATION"], "root_statuses": []},
        "applicability_predicate": "artifact_class_requires_native_genesis_binding",
        "evidence_requirements": ["CROSSWALKS_TO relationship", "current PGN authority record"],
        "cardinality_contract": {"minimum": 1, "maximum": 1},
        "violation_predicate": "required_current_genesis_binding_absent_or_deferred",
        "default_severity": "ERROR",
        "debt_effect": "ACTIONABLE_DEBT",
        "candidate_admission_effect": "FAIL",
        "historical_policy": "NO_PROVISIONAL_OR_INFERRED_CURRENT_CROSSWALK",
        "remediation_class": "PGN_AUTHORITY_REQUIRED_CURRENT",
        "authority_class": "OPERATOR_REQUIRED_IF_ADOPTION_MISSING",
    },
    {
        "rule_id": "GRT-R421",
        "rule_version": "1",
        "rule_family": "COMPANIONS_AND_ORPHANS",
        "name": "ORPHAN_SCHEMA_FORBIDDEN",
        "subject_selector": {"artifact_types": ["SCHEMA"], "lifecycle_classes": ["CURRENT_SUPPORTING", "CURRENT_AUTHORITATIVE"], "root_statuses": []},
        "applicability_predicate": "current_schema_artifact",
        "evidence_requirements": ["GOVERNED_BY or DOCUMENTS relationship", "validation consumer evidence"],
        "cardinality_contract": {"minimum": 1, "maximum": 2147483647},
        "violation_predicate": "schema_has_no_lawful_governance_or_consumer_relationship",
        "default_severity": "WARNING",
        "debt_effect": "ACTIONABLE_DEBT",
        "candidate_admission_effect": "FAIL",
        "historical_policy": "HISTORICAL_SCHEMA_MAY_BE_EXPLICITLY_DISPOSITIONED",
        "remediation_class": "BIND_OR_DISPOSITION_SCHEMA",
        "authority_class": "AUTO_EXECUTABLE_IF_SOURCE_EXPLICIT",
    },
    {
        "rule_id": "GRT-R500",
        "rule_version": "1",
        "rule_family": "DEPENDENCIES",
        "name": "REQUIRED_DEPENDENCY_RESOLVES",
        "subject_selector": {"artifact_types": list(ARTIFACT_CLASSES), "lifecycle_classes": ["CURRENT_AUTHORITATIVE", "CURRENT_IMPLEMENTATION", "CURRENT_SUPPORTING"], "root_statuses": []},
        "applicability_predicate": "declared_dependency_role_is_required",
        "evidence_requirements": ["DEPENDS_ON relationship", "target artifact lifecycle"],
        "cardinality_contract": {"minimum": 1, "maximum": 1},
        "violation_predicate": "required_dependency_missing_ambiguous_or_incompatible",
        "default_severity": "ERROR",
        "debt_effect": "ACTIONABLE_DEBT",
        "candidate_admission_effect": "FAIL",
        "historical_policy": "HISTORICAL_UNRESOLVED_DEPENDENCY_REQUIRES_DISPOSITION",
        "remediation_class": "MATERIALISE_OR_REMOVE_REQUIRED_DEPENDENCY",
        "authority_class": "AUTO_EXECUTABLE_UNLESS_SEMANTIC_CHANGE",
    },
    {
        "rule_id": "GRT-R600",
        "rule_version": "1",
        "rule_family": "SUPERSESSION",
        "name": "CURRENT_DEPENDENCY_ON_SUPERSEDED_ARTIFACT_FORBIDDEN",
        "subject_selector": {"artifact_types": list(ARTIFACT_CLASSES), "lifecycle_classes": ["CURRENT_AUTHORITATIVE", "CURRENT_IMPLEMENTATION", "CURRENT_SUPPORTING"], "root_statuses": []},
        "applicability_predicate": "current_artifact_has_required_dependency",
        "evidence_requirements": ["DEPENDS_ON relationship", "target supersession/lifecycle"],
        "cardinality_contract": {"minimum": 0, "maximum": 0},
        "violation_predicate": "required_dependency_targets_superseded_or_historical_artifact_without_compatibility_contract",
        "default_severity": "ERROR",
        "debt_effect": "ACTIONABLE_DEBT",
        "candidate_admission_effect": "FAIL",
        "historical_policy": "HISTORICAL_REFERENCES_REMAIN_ADDRESSABLE",
        "remediation_class": "REBIND_OR_DECLARE_COMPATIBILITY",
        "authority_class": "AUTO_EXECUTABLE_UNLESS_FROZEN_CONTRACT_CHANGE",
    },
    {
        "rule_id": "GRT-R700",
        "rule_version": "1",
        "rule_family": "CURRENT_STATE_AND_DOCUMENTATION",
        "name": "CURRENT_STATE_ROLE_EXPLICIT",
        "subject_selector": {"artifact_types": ["PROGRAMME_STATE", "DOCUMENTATION", "DECISION_RECORD"], "lifecycle_classes": list(LIFECYCLE_CLASSES), "root_statuses": []},
        "applicability_predicate": "artifact_can_be_interpreted_as_current_state",
        "evidence_requirements": ["explicit lifecycle_class", "source-bound current-state role"],
        "cardinality_contract": {"minimum": 1, "maximum": 1},
        "violation_predicate": "current_state_role_missing_or_filename_inferred",
        "default_severity": "ERROR",
        "debt_effect": "ACTIONABLE_DEBT",
        "candidate_admission_effect": "FAIL",
        "historical_policy": "CURRENT_FINAL_RATIFIED_FILENAME_HAS_NO_AUTHORITY_EFFECT",
        "remediation_class": "MATERIALISE_CURRENT_STATE_ROLE",
        "authority_class": "AUTO_EXECUTABLE_IF_SOURCE_EXPLICIT",
    },
    {
        "rule_id": "GRT-R805",
        "rule_version": "1",
        "rule_family": "WORKFLOWS_AND_TOOLING",
        "name": "WORKFLOW_GOVERNANCE_RECORD_REQUIRED",
        "subject_selector": {"artifact_types": ["WORKFLOW"], "lifecycle_classes": ["CURRENT_SUPPORTING", "CURRENT_IMPLEMENTATION"], "root_statuses": []},
        "applicability_predicate": "repository_workflow_is_current",
        "evidence_requirements": ["owner", "purpose", "permissions", "required-check role", "rollback"],
        "cardinality_contract": {"minimum": 1, "maximum": 1},
        "violation_predicate": "workflow_governance_record_missing_or_stale",
        "default_severity": "WARNING",
        "debt_effect": "ACTIONABLE_DEBT",
        "candidate_admission_effect": "FAIL",
        "historical_policy": "DISABLED_HISTORICAL_WORKFLOW_MAY_BE_DISPOSITIONED",
        "remediation_class": "MATERIALISE_WORKFLOW_GOVERNANCE",
        "authority_class": "AUTO_EXECUTABLE_IF_SOURCE_EXPLICIT",
    },
    {
        "rule_id": "GRT-R900",
        "rule_version": "1",
        "rule_family": "BASELINE_AND_INTEGRITY",
        "name": "ORIGINAL_BASELINE_IMMUTABLE",
        "subject_selector": {"artifact_types": ["EVIDENCE_POINTER", "REGISTRY"], "lifecycle_classes": ["HISTORICAL_IMMUTABLE"], "root_statuses": []},
        "applicability_predicate": "artifact_is_grt_debt_baseline_b0",
        "evidence_requirements": ["source commit", "source tree", "topology hash", "569 member payload hashes"],
        "cardinality_contract": {"minimum": 569, "maximum": 569},
        "violation_predicate": "baseline_source_identity_count_or_member_payload_changed",
        "default_severity": "BLOCKER",
        "debt_effect": "NON_DEBT_OBSERVATION",
        "candidate_admission_effect": "FAIL",
        "historical_policy": "NEVER_REWRITE",
        "remediation_class": "RESTORE_EXACT_SOURCE_OR_BLOCK",
        "authority_class": "OPERATOR_REQUIRED_IF_SOURCE_CONTRADICTION",
    },
    {
        "rule_id": "GRT-R954",
        "rule_version": "1",
        "rule_family": "BASELINE_AND_INTEGRITY",
        "name": "RULE_SEMANTIC_CHANGE_OPERATOR_APPROVED",
        "subject_selector": {"artifact_types": ["CONTRACT", "REGISTRY", "CONFIGURATION"], "lifecycle_classes": ["CURRENT_AUTHORITATIVE", "PROPOSED_UNADMITTED"], "root_statuses": []},
        "applicability_predicate": "constitution_rule_semantics_or_legality_changes",
        "evidence_requirements": ["ConstitutionAmendment", "impact analysis", "operator decision", "finding/debt migration"],
        "cardinality_contract": {"minimum": 1, "maximum": 1},
        "violation_predicate": "semantic_change_without_complete_operator_approved_amendment",
        "default_severity": "BLOCKER",
        "debt_effect": "NON_DEBT_OBSERVATION",
        "candidate_admission_effect": "FAIL",
        "historical_policy": "PRIOR_GENERATIONS_IMMUTABLE",
        "remediation_class": "COMPLETE_AMENDMENT_PROTOCOL",
        "authority_class": "OPERATOR_REQUIRED",
    },
)

CURRENT_STATE_OBLIGATIONS: tuple[dict[str, Any], ...] = (
    {
        "obligation_id": "GRT.CURRENT.DESIGN_SPECIFICATION.v1",
        "role": "CURRENT_DESIGN_SPECIFICATION",
        "artifact_types": ["DESIGN_SPECIFICATION"],
        "minimum": 0,
        "maximum": 1,
        "source_binding_required": True,
        "stale_policy": "SUPERSEDE_OR_EXPLICITLY_HISTORICISE",
        "authority_effect": "NONE",
    },
    {
        "obligation_id": "GRT.CURRENT.IMPLEMENTATION_PLAN.v1",
        "role": "CURRENT_IMPLEMENTATION_PLAN",
        "artifact_types": ["PLAN"],
        "minimum": 0,
        "maximum": 1,
        "source_binding_required": True,
        "stale_policy": "SUPERSEDE_OR_EXPLICITLY_HISTORICISE",
        "authority_effect": "NONE",
    },
    {
        "obligation_id": "GRT.CURRENT.PROGRAMME_STATE.v1",
        "role": "CURRENT_PROGRAMME_STATE",
        "artifact_types": ["PROGRAMME_STATE"],
        "minimum": 1,
        "maximum": 1,
        "source_binding_required": True,
        "stale_policy": "FAIL_CURRENT_PROJECTION",
        "authority_effect": "NONE",
    },
    {
        "obligation_id": "GRT.CURRENT.DECISION_RECORD.v1",
        "role": "CURRENT_DECISION_RECORD",
        "artifact_types": ["DECISION_RECORD"],
        "minimum": 0,
        "maximum": 2147483647,
        "source_binding_required": True,
        "stale_policy": "PRESERVE_IMMUTABLE_DECISIONS",
        "authority_effect": "NONE",
    },
    {
        "obligation_id": "GRT.CURRENT.AUTHORITY_RECORD.v1",
        "role": "CURRENT_AUTHORITY_RECORD",
        "artifact_types": ["REGISTRY", "DECISION_RECORD"],
        "minimum": 0,
        "maximum": 1,
        "source_binding_required": True,
        "stale_policy": "FAIL_AUTHORITY_PROJECTION",
        "authority_effect": "NONE",
    },
    {
        "obligation_id": "GRT.CURRENT.RELEASE_POINTER.v1",
        "role": "CURRENT_RELEASE_POINTER",
        "artifact_types": ["REGISTRY", "EVIDENCE_POINTER"],
        "minimum": 0,
        "maximum": 1,
        "source_binding_required": True,
        "stale_policy": "FAIL_RELEASE_PROJECTION",
        "authority_effect": "NONE",
    },
    {
        "obligation_id": "GRT.CURRENT.READ_MODEL.v1",
        "role": "CURRENT_READ_MODEL",
        "artifact_types": ["READ_MODEL"],
        "minimum": 0,
        "maximum": 2147483647,
        "source_binding_required": True,
        "stale_policy": "REBUILD_FROM_DURABLE_SOURCES",
        "authority_effect": "NONE",
    },
)


def _registry_hash(record: Mapping[str, Any], field: str = "registry_hash") -> str:
    return canonical_sha256({key: value for key, value in record.items() if key != field})


def _with_registry_hash(record: dict[str, Any], field: str = "registry_hash") -> dict[str, Any]:
    result = dict(record)
    result[field] = _registry_hash(result, field)
    return result


def _root_id(path: str) -> str:
    normalized = path.replace(".", "dot_").replace("-", "_")
    return "GRT.ROOT." + normalized + ".v1"


def build_root_registry(
    *,
    baseline_commit: str = BASELINE_COMMIT,
    baseline_tree: str = BASELINE_TREE,
) -> dict[str, Any]:
    roots = [
        {
            "schema": "grt-repository-root-record/v0.2",
            "root_id": _root_id(path),
            "path": path,
            "root_kind": "DIRECTORY",
            "classification_status": "OBSERVED_PENDING_QUALIFICATION",
            "lifecycle_class": "PROPOSED_UNADMITTED",
            "governed": True,
            "new_write_policy": "ADVISORY_ONLY_PRE_G3",
            "observed_at_commit": baseline_commit,
            "observed_at_tree": baseline_tree,
            "evidence_refs": [f"git-tree:{baseline_tree}:{path}"],
            "authority_effect": "NONE",
        }
        for path in OBSERVED_ROOTS
    ]
    return _with_registry_hash(
        {
            "schema": "grt-root-registry/v0.2",
            "registry_id": "GRT_ROOT_REGISTRY_v0_2",
            "status": CONSTITUTION_STATUS,
            "observed_at_commit": baseline_commit,
            "observed_at_tree": baseline_tree,
            "classification_rule": "OBSERVATION_DOES_NOT_CONFER_AUTHORITY",
            "roots": roots,
            "authority_effect": "NONE",
        }
    )


def build_artifact_class_registry() -> dict[str, Any]:
    descriptions = {
        "IMPLEMENTATION": "Executable or importable implementation source.",
        "CONTRACT": "Normative behavioral or interface contract.",
        "SCHEMA": "Machine-validatable record shape.",
        "REGISTRY": "Versioned controlled vocabulary or binding set.",
        "FIXTURE": "Deterministic example or adversarial input.",
        "TEST": "Mechanical assurance source.",
        "WORKFLOW": "Repository automation definition.",
        "PLAN": "Approved or proposed execution constitution.",
        "DESIGN_SPECIFICATION": "Semantic design authority artifact.",
        "DECISION_RECORD": "Immutable delegated or operator decision.",
        "PROGRAMME_STATE": "Machine-readable packet/gate state.",
        "DOCUMENTATION": "Human-facing explanatory material.",
        "READ_MODEL": "Rebuildable derived projection.",
        "GENERATED_ARTIFACT": "Deterministically generated output.",
        "EVIDENCE_POINTER": "Address to source-bound evidence.",
        "TOOLING": "Non-authoritative development or governance tool.",
        "CONFIGURATION": "Versioned behavior/configuration input.",
        "MIGRATION": "Forward mapping or migration artifact.",
        "ARCHIVE_INDEX": "Index over preserved historical material.",
    }
    entries = [
        {
            "schema": "grt-artifact-class/v0.2",
            "artifact_class_id": name,
            "description": descriptions[name],
            "permanent_governed": True,
            "identity_policy": "LOGICAL_IDENTITY_OVER_PATH",
            "default_lifecycle_class": (
                "DERIVED_GENERATED"
                if name in {"READ_MODEL", "GENERATED_ARTIFACT"}
                else "PROPOSED_UNADMITTED"
            ),
            "authority_effect": "NONE",
        }
        for name in ARTIFACT_CLASSES
    ]
    return _with_registry_hash(
        {
            "schema": "grt-artifact-class-registry/v0.2",
            "registry_id": "GRT_ARTIFACT_CLASS_REGISTRY_v0_2",
            "status": CONSTITUTION_STATUS,
            "artifact_classes": entries,
            "authority_effect": "NONE",
        }
    )


def build_lifecycle_registry() -> dict[str, Any]:
    properties = {
        "CURRENT_AUTHORITATIVE": (True, True, True),
        "CURRENT_IMPLEMENTATION": (True, True, True),
        "CURRENT_SUPPORTING": (True, True, True),
        "PROPOSED_UNADMITTED": (False, True, True),
        "HISTORICAL_IMMUTABLE": (False, True, False),
        "DERIVED_GENERATED": (False, False, True),
        "QUARANTINED": (False, True, False),
        "EPHEMERAL_LOCAL": (False, False, False),
    }
    entries = [
        {
            "schema": "grt-lifecycle-class/v0.2",
            "lifecycle_class_id": name,
            "description": name.replace("_", " ").title(),
            "current": properties[name][0],
            "durable": properties[name][1],
            "canonical_write_allowed": properties[name][2],
            "authority_effect": "NONE",
        }
        for name in LIFECYCLE_CLASSES
    ]
    return _with_registry_hash(
        {
            "schema": "grt-lifecycle-registry/v0.2",
            "registry_id": "GRT_LIFECYCLE_REGISTRY_v0_2",
            "status": CONSTITUTION_STATUS,
            "lifecycle_classes": entries,
            "authority_effect": "NONE",
        }
    )


def build_relationship_registry() -> dict[str, Any]:
    directional = {
        "OWNED_BY",
        "GOVERNED_BY",
        "CROSSWALKS_TO",
        "IMPLEMENTS",
        "TESTS",
        "FIXTURES",
        "DOCUMENTS",
        "DEPENDS_ON",
        "GENERATED_FROM",
        "SUPERSEDES",
        "ARCHIVES",
        "PROJECTS",
        "REFERENCES",
        "QUARANTINES",
    }
    entries = [
        {
            "schema": "grt-artifact-relationship-type/v0.2",
            "relationship_type": name,
            "description": name.replace("_", " ").title(),
            "directional": name in directional,
            "current_governance_evidence_minimum": (
                "SOURCE_EXPLICIT"
                if name
                in {"OWNED_BY", "GOVERNED_BY", "CROSSWALKS_TO", "DEPENDS_ON"}
                else "PATH_AND_CONTENT_CORROBORATED"
            ),
            "authority_effect": "NONE",
        }
        for name in RELATIONSHIP_TYPES
    ]
    return _with_registry_hash(
        {
            "schema": "grt-relationship-registry/v0.2",
            "registry_id": "GRT_RELATIONSHIP_REGISTRY_v0_2",
            "status": CONSTITUTION_STATUS,
            "relationship_types": entries,
            "authority_effect": "NONE",
        }
    )


def build_rule_bundle() -> dict[str, Any]:
    rules: list[dict[str, Any]] = []
    for seed in RULE_SEEDS:
        rule = dict(seed)
        rule["schema"] = "grt-conformance-rule/v0.2"
        rule["canonical_hash"] = canonical_sha256(rule)
        rules.append(rule)
    rules.sort(key=lambda item: item["rule_id"])
    bundle = {
        "schema": "grt-rule-bundle/v0.2",
        "bundle_id": "GRT_RULE_BUNDLE_v0_2",
        "status": CONSTITUTION_STATUS,
        "serialization_version": SERIALIZATION_ID,
        "rules": rules,
        "authority_effect": "NONE_PRE_ENFORCEMENT",
    }
    return _with_registry_hash(bundle, "bundle_hash")


def build_current_state_registry() -> dict[str, Any]:
    entries = sorted(
        (dict(item) | {"schema": "grt-current-state-obligation/v0.1"} for item in CURRENT_STATE_OBLIGATIONS),
        key=lambda item: item["obligation_id"],
    )
    return _with_registry_hash(
        {
            "schema": "grt-current-state-obligation-registry/v0.1",
            "registry_id": "GRT_CURRENT_STATE_OBLIGATION_REGISTRY_v0_1",
            "status": CONSTITUTION_STATUS,
            "obligations": entries,
            "authority_effect": "NONE",
        }
    )


def build_information_architecture_policy() -> dict[str, Any]:
    return _with_registry_hash(
        {
            "schema": "grt-information-architecture-policy/v0.1",
            "policy_id": "GRT_INFORMATION_ARCHITECTURE_POLICY_v0_1",
            "status": CONSTITUTION_STATUS,
            "root_registry_id": "GRT_ROOT_REGISTRY_v0_2",
            "current_content_rule": "CURRENT_ROLE_REQUIRES_SOURCE_BOUND_LIFECYCLE_NOT_FILENAME",
            "deprecated_root_rule": "NO_NEW_CANONICAL_WRITES_AFTER_ACTIVATION",
            "move_rule": "PATH_MOVE_DOES_NOT_CHANGE_LOGICAL_ARTIFACT_IDENTITY",
            "migration_mode": "NON_DESTRUCTIVE_FORWARD_WITH_LINEAGE",
            "authority_effect": "NONE_PRE_ENFORCEMENT",
        }
    )


def build_supersession_policy() -> dict[str, Any]:
    return _with_registry_hash(
        {
            "schema": "grt-supersession-policy/v0.1",
            "policy_id": "GRT_SUPERSESSION_POLICY_v0_1",
            "status": CONSTITUTION_STATUS,
            "required_relationship": "SUPERSEDES",
            "historical_preservation": "MANDATORY",
            "current_dependency_rule": "FORBID_UNDECLARED_REQUIRED_DEPENDENCY_ON_SUPERSEDED",
            "filename_authority": "NONE",
            "authority_effect": "NONE_PRE_ENFORCEMENT",
        }
    )


def build_bootstrap_manifest() -> dict[str, Any]:
    dependencies = {
        "repository_root_record.schema.json": [],
        "artifact_class.schema.json": [],
        "lifecycle_class.schema.json": [],
        "artifact_relationship.schema.json": [
            "artifact_class.schema.json",
            "lifecycle_class.schema.json",
        ],
        "grt_conformance_rule.schema.json": [
            "artifact_class.schema.json",
            "lifecycle_class.schema.json",
            "repository_root_record.schema.json",
        ],
        "current_state_obligation.schema.json": ["artifact_class.schema.json"],
        "constitution_amendment.schema.json": ["grt_conformance_rule.schema.json"],
        "conformance_override.schema.json": ["grt_conformance_rule.schema.json"],
        "historical_disposition.schema.json": ["grt_conformance_rule.schema.json"],
        "information_architecture_policy.schema.json": [
            "repository_root_record.schema.json"
        ],
        "supersession_policy.schema.json": ["artifact_relationship.schema.json"],
        "repository_constitution.schema.json": [
            "repository_root_record.schema.json",
            "artifact_class.schema.json",
            "lifecycle_class.schema.json",
            "artifact_relationship.schema.json",
            "grt_conformance_rule.schema.json",
            "current_state_obligation.schema.json",
            "information_architecture_policy.schema.json",
            "supersession_policy.schema.json",
        ],
        "bootstrap_validation_manifest.schema.json": [],
    }
    schemas = [
        {
            "schema_id": name,
            "path": (SCHEMA_DIR / name).as_posix(),
            "dialect": DIALECT,
            "dependencies": dependencies[name],
        }
        for name in SCHEMA_FILES
    ]
    manifest = {
        "schema": "grt-bootstrap-validation-manifest/v0.1",
        "manifest_id": "GRT_BOOTSTRAP_VALIDATION_MANIFEST_v0_1",
        "status": CONSTITUTION_STATUS,
        "profile_id": PROFILE_ID,
        "validator_release": VALIDATOR_RELEASE,
        "schema_dialect": DIALECT,
        "schemas": schemas,
        "registry_validations": [
            {
                "path": (REGISTRY_DIR / "GRT_ROOT_REGISTRY_v0_2.json").as_posix(),
                "schema_id": "repository_root_record.schema.json",
                "collection_field": "roots",
                "identity_field": "root_id",
            },
            {
                "path": (REGISTRY_DIR / "GRT_ARTIFACT_CLASS_REGISTRY_v0_2.json").as_posix(),
                "schema_id": "artifact_class.schema.json",
                "collection_field": "artifact_classes",
                "identity_field": "artifact_class_id",
            },
            {
                "path": (REGISTRY_DIR / "GRT_LIFECYCLE_REGISTRY_v0_2.json").as_posix(),
                "schema_id": "lifecycle_class.schema.json",
                "collection_field": "lifecycle_classes",
                "identity_field": "lifecycle_class_id",
            },
            {
                "path": (REGISTRY_DIR / "GRT_RELATIONSHIP_REGISTRY_v0_2.json").as_posix(),
                "schema_id": "artifact_relationship.schema.json",
                "collection_field": "relationship_types",
                "identity_field": "relationship_type",
            },
            {
                "path": (REGISTRY_DIR / "GRT_RULE_BUNDLE_v0_2.json").as_posix(),
                "schema_id": "grt_conformance_rule.schema.json",
                "collection_field": "rules",
                "identity_field": "rule_id",
            },
            {
                "path": (REGISTRY_DIR / "GRT_CURRENT_STATE_OBLIGATION_REGISTRY_v0_1.json").as_posix(),
                "schema_id": "current_state_obligation.schema.json",
                "collection_field": "obligations",
                "identity_field": "obligation_id",
            },
        ],
        "negative_assurance": [
            "UNKNOWN_SCHEMA_DIALECT_REJECTED",
            "UNKNOWN_SCHEMA_KEYWORD_REJECTED",
            "SELF_REFERENTIAL_SCHEMA_REJECTED",
            "CYCLIC_SCHEMA_DEPENDENCY_REJECTED",
            "DUPLICATE_REGISTRY_ID_REJECTED",
            "MALFORMED_INSTANCE_REJECTED",
        ],
        "authority_effect": "NONE_BOOTSTRAP_ONLY",
    }
    return _with_registry_hash(manifest, "manifest_hash")


def _policy_hashes(repository_root: Path) -> dict[str, str]:
    return {
        name: file_sha256(repository_root / CONTRACT_DIR / name)
        for name in POLICY_FILES
    }


def build_constitution_record(
    repository_root: Path,
    *,
    registries: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    policy_hashes = _policy_hashes(repository_root)
    core = {
        "root_registry": registries["GRT_ROOT_REGISTRY_v0_2.json"]["registry_hash"],
        "artifact_class_registry": registries["GRT_ARTIFACT_CLASS_REGISTRY_v0_2.json"]["registry_hash"],
        "lifecycle_registry": registries["GRT_LIFECYCLE_REGISTRY_v0_2.json"]["registry_hash"],
        "relationship_registry": registries["GRT_RELATIONSHIP_REGISTRY_v0_2.json"]["registry_hash"],
        "rule_bundle": registries["GRT_RULE_BUNDLE_v0_2.json"]["bundle_hash"],
        "current_state_registry": registries["GRT_CURRENT_STATE_OBLIGATION_REGISTRY_v0_1.json"]["registry_hash"],
        "information_architecture_policy": registries["GRT_INFORMATION_ARCHITECTURE_POLICY_v0_1.json"]["registry_hash"],
        "serialization_version": SERIALIZATION_ID,
    }
    record = {
        "schema": "grt-repository-constitution/v0.2",
        "constitution_id": CONSTITUTION_ID,
        "constitution_version": "0.2",
        "status": CONSTITUTION_STATUS,
        "design_id": "OVC-GRT-V0.2-RCCC-DESIGN-SPEC-0.2-R1",
        "design_sha256": "bee3b1d9095a5f45f141abae550af35acb1a2aceca1bee555e59ddd2a19de9d7",
        "schema_dialect": DIALECT,
        "bootstrap_profile_id": PROFILE_ID,
        "bootstrap_validator_release": VALIDATOR_RELEASE,
        "serialization_version": SERIALIZATION_ID,
        "baseline_commit": BASELINE_COMMIT,
        "baseline_tree": BASELINE_TREE,
        "core_bindings": core,
        "policy_hashes": policy_hashes,
        "supporting_protocols": {
            "amendment": policy_hashes["GRT_CONSTITUTION_AMENDMENT_PROTOCOL_v0_1.md"],
            "override": policy_hashes["GRT_OVERRIDE_PROTOCOL_v0_1.md"],
            "historical_disposition": policy_hashes["GRT_HISTORICAL_DISPOSITION_POLICY_v0_1.md"],
            "bootstrap_validation": policy_hashes["GRT_BOOTSTRAP_VALIDATION_CONTRACT_v0_1.md"],
        },
        "activation": {
            "current": "INACTIVE",
            "limited_enforcement_gate": "GRT2-G2.5_OPERATOR_REQUIRED",
            "full_enforcement_gate": "GRT2-G3_OPERATOR_REQUIRED",
        },
        "authority_effect": "NONE_PRE_ENFORCEMENT",
    }
    record["canonical_hash"] = canonical_sha256(
        {
            "constitution_id": record["constitution_id"],
            "constitution_version": record["constitution_version"],
            "core_bindings": core,
        }
    )
    return record


def build_registry_bundle(repository_root: Path | None = None) -> dict[str, dict[str, Any]]:
    registries: dict[str, dict[str, Any]] = {
        "GRT_ROOT_REGISTRY_v0_2.json": build_root_registry(),
        "GRT_ARTIFACT_CLASS_REGISTRY_v0_2.json": build_artifact_class_registry(),
        "GRT_LIFECYCLE_REGISTRY_v0_2.json": build_lifecycle_registry(),
        "GRT_RELATIONSHIP_REGISTRY_v0_2.json": build_relationship_registry(),
        "GRT_RULE_BUNDLE_v0_2.json": build_rule_bundle(),
        "GRT_CURRENT_STATE_OBLIGATION_REGISTRY_v0_1.json": build_current_state_registry(),
        "GRT_INFORMATION_ARCHITECTURE_POLICY_v0_1.json": build_information_architecture_policy(),
        "GRT_SUPERSESSION_POLICY_v0_1.json": build_supersession_policy(),
        "GRT_BOOTSTRAP_VALIDATION_MANIFEST_v0_1.json": build_bootstrap_manifest(),
    }
    if repository_root is not None:
        registries["GRT_REPOSITORY_CONSTITUTION_v0_2.json"] = build_constitution_record(
            repository_root, registries=registries
        )
    return registries


def _schema_map(repository_root: Path) -> dict[str, Mapping[str, Any]]:
    return {
        name: load_json(repository_root / SCHEMA_DIR / name)
        for name in SCHEMA_FILES
    }


def validate_committed_bundle(repository_root: str | Path) -> dict[str, Any]:
    root = Path(repository_root)
    schemas = _schema_map(root)
    for schema in schemas.values():
        validate_schema(schema)

    manifest = load_json(
        root
        / REGISTRY_DIR
        / "GRT_BOOTSTRAP_VALIDATION_MANIFEST_v0_1.json"
    )
    validate_instance(
        manifest,
        schemas["bootstrap_validation_manifest.schema.json"],
    )
    order = validate_manifest_dag(manifest)

    for validation in manifest["registry_validations"]:
        registry = load_json(root / validation["path"])
        validate_registry_unique(
            registry,
            collection_field=validation["collection_field"],
            identity_field=validation["identity_field"],
        )
        entry_schema = schemas[validation["schema_id"]]
        for entry in registry[validation["collection_field"]]:
            validate_instance(entry, entry_schema)

    expected = build_registry_bundle(root)
    committed: dict[str, Mapping[str, Any]] = {
        name: load_json(root / REGISTRY_DIR / name)
        for name in expected
    }
    for name, expected_record in expected.items():
        actual = committed[name]
        if actual != expected_record:
            raise BootstrapValidationError(
                f"GRT_WP1_COMMITTED_REGISTRY_DRIFT:{name}"
            )

    constitution = committed["GRT_REPOSITORY_CONSTITUTION_v0_2.json"]
    validate_instance(
        constitution,
        schemas["repository_constitution.schema.json"],
    )
    if constitution["status"] != CONSTITUTION_STATUS:
        raise BootstrapValidationError("GRT_WP1_CONSTITUTION_PREMATURELY_ACTIVE")
    if constitution["activation"]["current"] != "INACTIVE":
        raise BootstrapValidationError("GRT_WP1_CONSTITUTION_PREMATURELY_ACTIVE")

    return {
        "schema": "grt-wp1-validation-receipt/v0.1",
        "result": "PASS",
        "schema_count": len(schemas),
        "registry_count": len(committed),
        "manifest_order": list(order),
        "constitution_hash": constitution["canonical_hash"],
        "validator_release": VALIDATOR_RELEASE,
        "authority_effect": "NONE_PRE_ENFORCEMENT",
    }
