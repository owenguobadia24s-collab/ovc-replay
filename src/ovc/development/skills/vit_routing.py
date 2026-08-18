from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from ovc.development.identity import canonical_sha256, normalize_relative_path, resolve_under
from ovc.development.skills.vit_core import TREE_IDENTITY_PROFILE, VitContractError

VIT_MANDATORY = "VIT_MANDATORY"
REGISTERED_EXCEPTION = "REGISTERED_EXCEPTION"
UNLAWFUL = "UNLAWFUL"
ROUTE_CLASSES = frozenset({VIT_MANDATORY, REGISTERED_EXCEPTION, UNLAWFUL})

LINEAGE_SCHEMA = "ovc-vit-routing-lineage/v1"
SOURCE_HEAD_SCHEMA = "ovc-vit-source-head/v1"
VIT_CONTROLLER = "DSAI_VIT_PHYSICAL_CONTROLLER"
SIQ_GATEWAY = "DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY"


def _is_hex(value: str, length: int) -> bool:
    if not isinstance(value, str) or len(value) != length:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value.lower() == value


def _required_mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise VitContractError(f"{name} must be an object")
    return value


def _tree_sha(tree: Mapping[str, Any], name: str) -> str:
    tree_sha = str(tree.get("tree_sha", ""))
    if not _is_hex(tree_sha, 40) or tree.get("profile") != TREE_IDENTITY_PROFILE:
        raise VitContractError(f"VIT_LINEAGE_{name}_TREE_INVALID")
    return tree_sha


def _validated_source_head(value: object) -> tuple[dict[str, Any], str] | None:
    if value is None:
        return None
    source = _required_mapping(value, "source_head")
    allowed = {
        "schema",
        "commit_sha",
        "tree_sha",
        "pr_number",
        "head_ref",
        "development_base_commit",
        "development_base_tree",
    }
    if set(source) - allowed:
        raise VitContractError("VIT_LINEAGE_SOURCE_HEAD_FIELDS_INVALID")
    if source.get("schema") != SOURCE_HEAD_SCHEMA:
        raise VitContractError("VIT_LINEAGE_SOURCE_HEAD_SCHEMA_INVALID")
    commit_sha = str(source.get("commit_sha", ""))
    tree_sha = str(source.get("tree_sha", ""))
    if not _is_hex(commit_sha, 40) or not _is_hex(tree_sha, 40):
        raise VitContractError("VIT_LINEAGE_SOURCE_HEAD_GIT_ID_INVALID")
    try:
        pr_number = int(source.get("pr_number", -1))
    except (TypeError, ValueError) as exc:
        raise VitContractError("VIT_LINEAGE_SOURCE_HEAD_PR_INVALID") from exc
    if pr_number < 1:
        raise VitContractError("VIT_LINEAGE_SOURCE_HEAD_PR_INVALID")
    head_ref = str(source.get("head_ref", "")).strip()
    if (
        not head_ref
        or head_ref.startswith("/")
        or ".." in PurePosixPath(head_ref).parts
    ):
        raise VitContractError("VIT_LINEAGE_SOURCE_HEAD_REF_INVALID")
    base_commit = source.get("development_base_commit")
    base_tree = source.get("development_base_tree")
    if (base_commit is None) != (base_tree is None):
        raise VitContractError("VIT_LINEAGE_SOURCE_BASE_INCOMPLETE")
    normalized: dict[str, Any] = {
        "schema": SOURCE_HEAD_SCHEMA,
        "commit_sha": commit_sha,
        "tree_sha": tree_sha,
        "pr_number": pr_number,
        "head_ref": head_ref,
    }
    if base_commit is not None:
        base_commit = str(base_commit)
        base_tree = str(base_tree)
        if not _is_hex(base_commit, 40) or not _is_hex(base_tree, 40):
            raise VitContractError("VIT_LINEAGE_SOURCE_BASE_GIT_ID_INVALID")
        normalized["development_base_commit"] = base_commit
        normalized["development_base_tree"] = base_tree
    source_id = canonical_sha256(normalized, role="OVC_VIT_SOURCE_HEAD")
    return normalized, source_id


@dataclass(frozen=True)
class ValidatedVitLineage:
    programme_id: str
    packet_id: str
    pip_id: str
    generation_id: str
    placement_id: str
    route_class: str
    lineage_ref: str | None = None
    source_head_id: str | None = None


def build_vit_lineage_record(
    *,
    programme_id: str,
    packet_id: str,
    pip_identity_payload: Mapping[str, Any],
    train_generation_id: str,
    ordinal: int,
    predecessor_tree_sha: str,
    result_tree_sha: str,
    apply_profile: str,
    route_class: str = VIT_MANDATORY,
    source_head: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one canonical PIP -> VirtualIntegrationGeneration -> LedgerPlacement lineage.

    ``source_head`` is transport/provenance only.  It is deliberately excluded from
    PIP/generation/placement identities so a lawful frontier refresh can preserve the
    semantic packet while producing a new placement.
    """
    pip = dict(pip_identity_payload)
    if str(pip.get("programme_id", "")) != programme_id or str(pip.get("packet_id", "")) != packet_id:
        raise VitContractError("VIT_LINEAGE_PIP_PACKET_MISMATCH")
    authority_manifest_id = str(pip.get("authority_manifest_id", ""))
    dependency_frontier_id = str(pip.get("dependency_frontier_id", ""))
    if not _is_hex(authority_manifest_id, 64) or not _is_hex(dependency_frontier_id, 64):
        raise VitContractError("VIT_LINEAGE_PIP_FRONTIER_INVALID")
    if route_class not in {VIT_MANDATORY, REGISTERED_EXCEPTION}:
        raise VitContractError("VIT_LINEAGE_ROUTE_CLASS_INVALID")
    if ordinal < 0 or not str(train_generation_id).strip() or not str(apply_profile).strip():
        raise VitContractError("VIT_LINEAGE_BUILD_INPUT_INVALID")
    if not _is_hex(predecessor_tree_sha, 40) or not _is_hex(result_tree_sha, 40):
        raise VitContractError("VIT_LINEAGE_BUILD_TREE_INVALID")

    pip_id = canonical_sha256(pip)
    generation = {
        "train_generation_id": str(train_generation_id),
        "ordinal": int(ordinal),
        "predecessor_tree": {"tree_sha": predecessor_tree_sha, "profile": TREE_IDENTITY_PROFILE},
        "payload_id": pip_id,
        "result_tree": {"tree_sha": result_tree_sha, "profile": TREE_IDENTITY_PROFILE},
        "authority_manifest_id": authority_manifest_id,
        "dependency_frontier_id": dependency_frontier_id,
    }
    generation_id = canonical_sha256(generation)
    placement = {
        "payload_id": pip_id,
        "predecessor_tree": predecessor_tree_sha,
        "result_tree": result_tree_sha,
        "apply_profile": str(apply_profile),
        "ordinal": int(ordinal),
        "dependency_frontier_id": dependency_frontier_id,
        "authority_manifest_id": authority_manifest_id,
    }
    placement_id = canonical_sha256(placement)
    record: dict[str, Any] = {
        "schema": LINEAGE_SCHEMA,
        "status": "ADMITTED",
        "programme_id": str(programme_id),
        "packet_id": str(packet_id),
        "route_class": route_class,
        "pip": pip,
        "pip_id": pip_id,
        "generation": generation,
        "generation_id": generation_id,
        "placement": placement,
        "placement_id": placement_id,
        "routing": {
            "controller": VIT_CONTROLLER,
            "physical_gateway": SIQ_GATEWAY,
            "route_class": route_class,
        },
    }
    validated_source = _validated_source_head(source_head)
    if validated_source is not None:
        normalized, source_id = validated_source
        if normalized["tree_sha"] != result_tree_sha:
            raise VitContractError("VIT_LINEAGE_SOURCE_HEAD_NOT_RESULT_TREE")
        record["source_head"] = normalized
        record["source_head_id"] = source_id
    validate_vit_lineage_record(record)
    return record


def validate_vit_lineage_record(record: Mapping[str, Any], *, lineage_ref: str | None = None) -> ValidatedVitLineage:
    """Validate lineage using the repository's canonical PIP/generation/placement identity shapes."""
    if record.get("schema") != LINEAGE_SCHEMA:
        raise VitContractError("VIT_LINEAGE_SCHEMA_INVALID")
    if record.get("status") != "ADMITTED":
        raise VitContractError("VIT_LINEAGE_NOT_ADMITTED")

    programme_id = str(record.get("programme_id", "")).strip()
    packet_id = str(record.get("packet_id", "")).strip()
    route_class = str(record.get("route_class", "")).strip()
    if not programme_id or not packet_id:
        raise VitContractError("VIT_LINEAGE_PACKET_IDENTITY_MISSING")
    if route_class not in {VIT_MANDATORY, REGISTERED_EXCEPTION}:
        raise VitContractError("VIT_LINEAGE_ROUTE_CLASS_INVALID")

    pip = _required_mapping(record.get("pip"), "pip")
    if str(pip.get("programme_id", "")) != programme_id or str(pip.get("packet_id", "")) != packet_id:
        raise VitContractError("VIT_LINEAGE_PIP_PACKET_MISMATCH")
    authority_manifest_id = str(pip.get("authority_manifest_id", ""))
    dependency_frontier_id = str(pip.get("dependency_frontier_id", ""))
    if not _is_hex(authority_manifest_id, 64) or not _is_hex(dependency_frontier_id, 64):
        raise VitContractError("VIT_LINEAGE_PIP_FRONTIER_INVALID")
    pip_id = str(record.get("pip_id", ""))
    if not _is_hex(pip_id, 64) or pip_id != canonical_sha256(dict(pip)):
        raise VitContractError("VIT_LINEAGE_PIP_ID_INVALID")

    generation = _required_mapping(record.get("generation"), "generation")
    if str(generation.get("payload_id", "")) != pip_id:
        raise VitContractError("VIT_LINEAGE_GENERATION_PIP_MISMATCH")
    if str(generation.get("authority_manifest_id", "")) != authority_manifest_id:
        raise VitContractError("VIT_LINEAGE_GENERATION_AUTHORITY_MISMATCH")
    if str(generation.get("dependency_frontier_id", "")) != dependency_frontier_id:
        raise VitContractError("VIT_LINEAGE_GENERATION_DEPENDENCY_MISMATCH")
    predecessor = _required_mapping(generation.get("predecessor_tree"), "generation.predecessor_tree")
    result = _required_mapping(generation.get("result_tree"), "generation.result_tree")
    predecessor_sha = _tree_sha(predecessor, "PREDECESSOR")
    result_sha = _tree_sha(result, "RESULT")
    if not str(generation.get("train_generation_id", "")).strip():
        raise VitContractError("VIT_LINEAGE_TRAIN_GENERATION_MISSING")
    try:
        ordinal = int(generation.get("ordinal", -1))
    except (TypeError, ValueError) as exc:
        raise VitContractError("VIT_LINEAGE_ORDINAL_INVALID") from exc
    if ordinal < 0:
        raise VitContractError("VIT_LINEAGE_ORDINAL_INVALID")
    generation_id = str(record.get("generation_id", ""))
    if not _is_hex(generation_id, 64) or generation_id != canonical_sha256(dict(generation)):
        raise VitContractError("VIT_LINEAGE_GENERATION_ID_INVALID")

    placement = _required_mapping(record.get("placement"), "placement")
    if str(placement.get("payload_id", "")) != pip_id:
        raise VitContractError("VIT_LINEAGE_PLACEMENT_PIP_MISMATCH")
    if str(placement.get("predecessor_tree", "")) != predecessor_sha or str(placement.get("result_tree", "")) != result_sha:
        raise VitContractError("VIT_LINEAGE_PLACEMENT_TREE_MISMATCH")
    if str(placement.get("dependency_frontier_id", "")) != dependency_frontier_id:
        raise VitContractError("VIT_LINEAGE_PLACEMENT_DEPENDENCY_MISMATCH")
    if str(placement.get("authority_manifest_id", "")) != authority_manifest_id:
        raise VitContractError("VIT_LINEAGE_PLACEMENT_AUTHORITY_MISMATCH")
    if int(placement.get("ordinal", -1)) != ordinal or not str(placement.get("apply_profile", "")).strip():
        raise VitContractError("VIT_LINEAGE_PLACEMENT_IDENTITY_MISMATCH")
    placement_id = str(record.get("placement_id", ""))
    if not _is_hex(placement_id, 64) or placement_id != canonical_sha256(dict(placement)):
        raise VitContractError("VIT_LINEAGE_PLACEMENT_ID_INVALID")

    routing = _required_mapping(record.get("routing"), "routing")
    if routing.get("controller") != VIT_CONTROLLER or routing.get("physical_gateway") != SIQ_GATEWAY:
        raise VitContractError("VIT_LINEAGE_ROUTING_OWNER_INVALID")
    if str(routing.get("route_class", "")) != route_class:
        raise VitContractError("VIT_LINEAGE_ROUTING_CLASS_MISMATCH")

    source_head_id: str | None = None
    validated_source = _validated_source_head(record.get("source_head"))
    if validated_source is not None:
        source_head, source_head_id = validated_source
        if source_head["tree_sha"] != result_sha:
            raise VitContractError("VIT_LINEAGE_SOURCE_HEAD_NOT_RESULT_TREE")
        if record.get("source_head_id") != source_head_id:
            raise VitContractError("VIT_LINEAGE_SOURCE_HEAD_ID_INVALID")
    elif record.get("source_head_id") is not None:
        raise VitContractError("VIT_LINEAGE_SOURCE_HEAD_ID_WITHOUT_SOURCE")

    return ValidatedVitLineage(
        programme_id=programme_id,
        packet_id=packet_id,
        pip_id=pip_id,
        generation_id=generation_id,
        placement_id=placement_id,
        route_class=route_class,
        lineage_ref=lineage_ref,
        source_head_id=source_head_id,
    )


def load_vit_lineage(root: str | Path, relative_path: str) -> ValidatedVitLineage:
    import json

    normalized = normalize_relative_path(relative_path)
    path = resolve_under(Path(root), normalized)
    if not path.is_file():
        raise VitContractError("VIT_LINEAGE_REF_NOT_FOUND")
    record = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record, Mapping):
        raise VitContractError("VIT_LINEAGE_RECORD_INVALID")
    return validate_vit_lineage_record(record, lineage_ref=normalized)


def classify_main_movement(
    *,
    previous_pip_id: str,
    current_pip_id: str,
    dependency_frontier_changed: bool,
    authority_changed: bool,
    packet_local_defect_changed_payload: bool,
) -> Mapping[str, Any]:
    """Classify physical-main movement without conflating placement with payload identity."""
    if not _is_hex(previous_pip_id, 64) or not _is_hex(current_pip_id, 64):
        raise VitContractError("VIT_PIP_ID_INVALID")
    payload_changed = previous_pip_id != current_pip_id or packet_local_defect_changed_payload
    if authority_changed:
        return {
            "disposition": "AUTHORITY_REVIEW_REQUIRED",
            "payload_rebuild_required": False,
            "assurance_renewal_required": True,
        }
    if dependency_frontier_changed:
        return {
            "disposition": "PAYLOAD_REBUILD_REQUIRED",
            "payload_rebuild_required": True,
            "assurance_renewal_required": True,
        }
    if not payload_changed:
        return {
            "disposition": "PLACEMENT_RECOMPUTE_ONLY",
            "payload_rebuild_required": False,
            "assurance_renewal_required": True,
        }
    return {
        "disposition": "PAYLOAD_REBUILD_REQUIRED",
        "payload_rebuild_required": True,
        "assurance_renewal_required": True,
    }
