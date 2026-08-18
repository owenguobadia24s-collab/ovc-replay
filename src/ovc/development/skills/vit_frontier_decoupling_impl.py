"""Frontier-decoupled PR/VIT materialisation contracts and deterministic helpers.

A permanent PR is transport/provenance for one immutable PacketIntegrationPayload
(PIP).  Physical-main movement never mutates that PIP.  Instead, the same PIP is
recomposed against the current lawful VIT predecessor to produce a new immutable
VirtualIntegrationGeneration and placement.  Only the final physical transaction
is allowed to freeze current main.
"""

from __future__ import annotations

import base64
from dataclasses import asdict, dataclass
from fnmatch import fnmatchcase
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
from typing import Any, Iterable, Mapping, Sequence

from ovc.development.identity import canonical_sha256
from ovc.development.skills.vit_apply import REFERENCE_APPLY_PROFILE
from ovc.development.skills.vit_core import TREE_IDENTITY_PROFILE, VitContractError
from ovc.development.skills.vit_routing import (
    build_vit_lineage_record,
    validate_vit_lineage_record,
)

FRONTIER_RESOLUTION_SCHEMA = "ovc-vit-frontier-resolution/v1"
SOURCE_HEAD_SCHEMA = "ovc-vit-source-head/v1"
ASSURANCE_GENERATION_SCHEMA = "ovc-vit-frontier-assurance-generation/v1"
ADMISSION_RECEIPT_SCHEMA = "ovc-vit-frontier-admission-receipt/v1"
A2_PROOF_SCHEMA = "ovc-vit-a2-prospective-tree-proof/v1"
FRONTIER_LEDGER_ENVELOPE_SCHEMA = "ovc-vit-frontier-ledger-envelope/v1"

MOVEMENT_DISPOSITIONS = frozenset(
    {
        "NO_MOVEMENT",
        "PLACEMENT_RECOMPUTE_ONLY",
        "ASSURANCE_RENEWAL_REQUIRED",
        "PAYLOAD_REBUILD_REQUIRED",
        "AUTHORITY_REVIEW_REQUIRED",
        "WAITING_VIT_PREDECESSOR",
    }
)

# These surfaces change the integration harness rather than the packet payload.
# They renew A1/A2 but do not invalidate an otherwise unchanged PIP/A0 result.
DEFAULT_GLOBAL_INTEGRATION_PATTERNS = (
    ".github/workflows/**",
    "tools/ci/**",
    "src/ovc/development/**",
    "tests/development/**",
    "registries/development/**",
)

_HEX = frozenset("0123456789abcdef")
_SAFE_REF = re.compile(r"[A-Za-z0-9._/-]+")


def _hex(value: object, length: int, label: str) -> str:
    token = str(value or "").strip()
    if len(token) != length or token.lower() != token or any(ch not in _HEX for ch in token):
        raise VitContractError(f"{label}_INVALID")
    return token


def _required(value: object, label: str) -> str:
    token = str(value or "").strip()
    if not token:
        raise VitContractError(f"{label}_MISSING")
    return token


def _safe_path(value: object) -> str:
    token = str(value or "").replace("\\", "/").strip()
    path = PurePosixPath(token)
    if (
        not token
        or token.startswith("/")
        or any(part in {"", ".", ".."} for part in path.parts)
        or token == ".git"
        or token.startswith(".git/")
    ):
        raise VitContractError(f"VIT_PIP_PATH_INVALID:{token!r}")
    return path.as_posix()


def _git(
    root: str | Path,
    *args: str,
    env: Mapping[str, str] | None = None,
    binary: bool = False,
) -> str | bytes:
    proc = subprocess.run(
        ["git", "-C", str(Path(root)), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=not binary,
        env={**os.environ, **dict(env or {})},
    )
    if proc.returncode != 0:
        stderr = proc.stderr if isinstance(proc.stderr, str) else proc.stderr.decode("utf-8", errors="replace")
        raise VitContractError(stderr.strip() or f"git {' '.join(args)} failed")
    if binary:
        assert isinstance(proc.stdout, bytes)
        return proc.stdout
    assert isinstance(proc.stdout, str)
    return proc.stdout.strip()


def git_tree(root: str | Path, commitish: str) -> str:
    return _hex(_git(root, "rev-parse", f"{commitish}^{{tree}}"), 40, "VIT_GIT_TREE")


def git_commit(root: str | Path, commitish: str) -> str:
    return _hex(_git(root, "rev-parse", f"{commitish}^{{commit}}"), 40, "VIT_GIT_COMMIT")


def tree_is_in_commit_ancestry(
    root: str | Path, *, tree_sha: str, descendant_commit: str
) -> bool:
    """Return true only when ``tree_sha`` occurred in descendant's first-parent ancestry.

    The physical-main court record is a first-parent sequence of squash materialisations.
    Confining this proof to first-parent history prevents a feature-branch tree that merely
    appears through another merge parent from being mistaken for a physical predecessor.
    """

    expected = _hex(tree_sha, 40, "VIT_HISTORICAL_TREE")
    descendant = git_commit(root, descendant_commit)
    raw = _git(root, "log", "--first-parent", "--format=%H%x00%T", descendant, binary=True)
    assert isinstance(raw, bytes)
    for line in raw.splitlines():
        if not line:
            continue
        try:
            _commit_raw, tree_raw = line.split(b"\x00", 1)
        except ValueError as exc:
            raise VitContractError("VIT_HISTORY_TREE_SCAN_INVALID") from exc
        if tree_raw.decode("ascii") == expected:
            return True
    return False


def diff_tree_paths(root: str | Path, before_tree: str, after_tree: str) -> tuple[str, ...]:
    before = _hex(before_tree, 40, "VIT_DIFF_BEFORE_TREE")
    after = _hex(after_tree, 40, "VIT_DIFF_AFTER_TREE")
    if before == after:
        return ()
    raw = _git(
        root,
        "diff",
        "--name-only",
        "--no-renames",
        "-z",
        before,
        after,
        binary=True,
    )
    assert isinstance(raw, bytes)
    return tuple(
        sorted(
            {
                _safe_path(chunk.decode("utf-8"))
                for chunk in raw.split(b"\0")
                if chunk
            }
        )
    )


def compose_pip_tree(
    root: str | Path,
    predecessor_tree: str,
    logical_changes: Sequence[Mapping[str, Any]],
) -> str:
    """Reference-apply one immutable PIP to an arbitrary predecessor tree."""

    predecessor = _hex(predecessor_tree, 40, "VIT_COMPOSE_PREDECESSOR_TREE")
    if not logical_changes:
        raise VitContractError("VIT_PIP_LOGICAL_CHANGES_EMPTY")
    with tempfile.TemporaryDirectory() as td:
        env = {"GIT_INDEX_FILE": str(Path(td) / "index")}
        _git(root, "read-tree", predecessor, env=env)
        seen: set[str] = set()
        for raw_change in logical_changes:
            if not isinstance(raw_change, Mapping):
                raise VitContractError("VIT_PIP_CHANGE_INVALID")
            path = _safe_path(raw_change.get("path"))
            if path in seen:
                raise VitContractError(f"VIT_PIP_DUPLICATE_PATH:{path}")
            seen.add(path)
            op = str(raw_change.get("op", "")).strip().upper()
            if op == "DELETE":
                _git(root, "update-index", "--force-remove", "--", path, env=env)
                continue
            if op not in {"ADD", "MODIFY"}:
                raise VitContractError(f"VIT_PIP_OPERATION_UNSUPPORTED:{op}:{path}")
            blob_sha = _hex(raw_change.get("blob_sha"), 40, "VIT_PIP_BLOB")
            mode = str(raw_change.get("mode", "100644"))
            if mode not in {"100644", "100755", "120000", "160000"}:
                raise VitContractError(f"VIT_PIP_MODE_INVALID:{mode}:{path}")
            object_type = "commit" if mode == "160000" else "blob"
            _git(root, "cat-file", "-e", f"{blob_sha}^{{{object_type}}}")
            _git(
                root,
                "update-index",
                "--add",
                "--cacheinfo",
                mode,
                blob_sha,
                path,
                env=env,
            )
        return _hex(_git(root, "write-tree", env=env), 40, "VIT_COMPOSE_RESULT_TREE")


def create_prospective_commit(
    root: str | Path,
    *,
    predecessor_commit: str,
    result_tree: str,
    generation_id: str,
) -> str:
    """Create a deterministic local-only commit for A2 execution on the exact tree."""

    parent = git_commit(root, predecessor_commit)
    tree = _hex(result_tree, 40, "VIT_PROSPECTIVE_RESULT_TREE")
    generation = _hex(generation_id, 64, "VIT_PROSPECTIVE_GENERATION")
    env = {
        "GIT_AUTHOR_NAME": "OVC VIT",
        "GIT_AUTHOR_EMAIL": "vit@ovc.invalid",
        "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z",
        "GIT_COMMITTER_NAME": "OVC VIT",
        "GIT_COMMITTER_EMAIL": "vit@ovc.invalid",
        "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z",
    }
    commit = _git(
        root,
        "commit-tree",
        tree,
        "-p",
        parent,
        "-m",
        f"OVC VIT prospective generation {generation}",
        env=env,
    )
    return _hex(commit, 40, "VIT_PROSPECTIVE_COMMIT")


@dataclass(frozen=True)
class SourceHead:
    commit_sha: str
    tree_sha: str
    pr_number: int
    head_ref: str
    development_base_commit: str | None = None
    development_base_tree: str | None = None
    schema: str = SOURCE_HEAD_SCHEMA

    def __post_init__(self) -> None:
        _hex(self.commit_sha, 40, "VIT_SOURCE_HEAD_COMMIT")
        _hex(self.tree_sha, 40, "VIT_SOURCE_HEAD_TREE")
        if self.pr_number < 1:
            raise VitContractError("VIT_SOURCE_PR_NUMBER_INVALID")
        ref = _required(self.head_ref, "VIT_SOURCE_HEAD_REF")
        if not _SAFE_REF.fullmatch(ref) or ref.startswith("/") or ".." in PurePosixPath(ref).parts:
            raise VitContractError("VIT_SOURCE_HEAD_REF_INVALID")
        if self.schema != SOURCE_HEAD_SCHEMA:
            raise VitContractError("VIT_SOURCE_HEAD_SCHEMA_INVALID")
        if (self.development_base_commit is None) != (self.development_base_tree is None):
            raise VitContractError("VIT_SOURCE_DEVELOPMENT_BASE_INCOMPLETE")
        if self.development_base_commit is not None:
            _hex(self.development_base_commit, 40, "VIT_SOURCE_BASE_COMMIT")
            _hex(self.development_base_tree, 40, "VIT_SOURCE_BASE_TREE")

    @property
    def source_head_id(self) -> str:
        return canonical_sha256(asdict(self), role="OVC_VIT_SOURCE_HEAD")


@dataclass(frozen=True)
class FrontierMovementDecision:
    disposition: str
    source_predecessor_tree: str
    current_predecessor_tree: str
    changed_paths: tuple[str, ...] = ()
    payload_conflicts: tuple[str, ...] = ()
    dependency_conflicts: tuple[str, ...] = ()
    authority_conflicts: tuple[str, ...] = ()
    integration_relevant_paths: tuple[str, ...] = ()
    a0_reuse_allowed: bool = True
    a1_renewal_required: bool = True
    a2_renewal_required: bool = True
    payload_rebuild_required: bool = False
    authority_review_required: bool = False

    def __post_init__(self) -> None:
        if self.disposition not in MOVEMENT_DISPOSITIONS:
            raise VitContractError("VIT_FRONTIER_MOVEMENT_DISPOSITION_INVALID")
        _hex(self.source_predecessor_tree, 40, "VIT_SOURCE_PREDECESSOR_TREE")
        _hex(self.current_predecessor_tree, 40, "VIT_CURRENT_PREDECESSOR_TREE")
        for collection in (
            self.changed_paths,
            self.payload_conflicts,
            self.dependency_conflicts,
            self.authority_conflicts,
            self.integration_relevant_paths,
        ):
            for path in collection:
                _safe_path(path)
        if self.payload_rebuild_required and self.a0_reuse_allowed:
            raise VitContractError("VIT_PAYLOAD_REBUILD_CANNOT_REUSE_A0")
        if self.authority_review_required and self.a0_reuse_allowed:
            raise VitContractError("VIT_AUTHORITY_REVIEW_CANNOT_REUSE_A0")

    @property
    def decision_id(self) -> str:
        return canonical_sha256(asdict(self), role="OVC_VIT_FRONTIER_MOVEMENT_DECISION")


def _patterns_from_footprint(
    pip: Mapping[str, Any], key: str
) -> tuple[str, ...]:
    footprint = pip.get("dependency_footprint")
    if not isinstance(footprint, Mapping):
        return ()
    values = footprint.get(key, ())
    if not isinstance(values, (list, tuple)):
        raise VitContractError(f"VIT_DEPENDENCY_FOOTPRINT_{key.upper()}_INVALID")
    return tuple(sorted({_safe_path(value) for value in values}))


def _identity_patterns_from_footprint(pip: Mapping[str, Any]) -> tuple[str, ...]:
    footprint = pip.get("dependency_footprint")
    if not isinstance(footprint, Mapping):
        return ()
    explicit = _patterns_from_footprint(pip, "identity_binding_paths")
    rows = footprint.get("identity_bindings", ())
    if not isinstance(rows, (list, tuple)):
        raise VitContractError("VIT_DEPENDENCY_FOOTPRINT_IDENTITY_BINDINGS_INVALID")
    bound: set[str] = set(explicit)
    for row in rows:
        if not isinstance(row, Mapping) or not str(row.get("identity", "")).strip():
            raise VitContractError("VIT_DEPENDENCY_FOOTPRINT_IDENTITY_BINDING_INVALID")
        bound.add(_safe_path(row.get("path")))
    return tuple(sorted(bound))


def _matching(paths: Iterable[str], patterns: Iterable[str]) -> tuple[str, ...]:
    matches = {
        path
        for path in paths
        for pattern in patterns
        if fnmatchcase(path, pattern)
    }
    return tuple(sorted(matches))


def classify_frontier_movement(
    *,
    pip: Mapping[str, Any],
    source_predecessor_tree: str,
    current_predecessor_tree: str,
    changed_paths: Iterable[str],
    dependency_frontier_changed: bool = False,
    authority_changed: bool = False,
    global_integration_patterns: Iterable[str] = DEFAULT_GLOBAL_INTEGRATION_PATTERNS,
) -> FrontierMovementDecision:
    """Classify main movement without conflating source-head ancestry with placement.

    Exact PIP-path collisions and explicitly bound dependency/authority changes fail
    closed.  Global integration-harness changes retain the same PIP/A0 but renew A1/A2.
    All other movement is placement-only recomposition.
    """

    source_tree = _hex(source_predecessor_tree, 40, "VIT_SOURCE_PREDECESSOR_TREE")
    current_tree = _hex(current_predecessor_tree, 40, "VIT_CURRENT_PREDECESSOR_TREE")
    changed = tuple(sorted({_safe_path(path) for path in changed_paths}))
    logical_changes = pip.get("logical_changes")
    if not isinstance(logical_changes, (list, tuple)) or not logical_changes:
        raise VitContractError("VIT_PIP_LOGICAL_CHANGES_INVALID")
    payload_paths = tuple(sorted({_safe_path(row.get("path")) for row in logical_changes if isinstance(row, Mapping)}))
    if len(payload_paths) != len(logical_changes):
        raise VitContractError("VIT_PIP_LOGICAL_CHANGE_SHAPE_INVALID")

    payload_conflicts = tuple(sorted(set(changed) & set(payload_paths)))
    dependency_patterns = _patterns_from_footprint(pip, "dependency_paths")
    semantic_patterns = _patterns_from_footprint(pip, "semantic_authority_paths")
    identity_patterns = _identity_patterns_from_footprint(pip)
    shared_integration_patterns = _patterns_from_footprint(
        pip, "shared_integration_paths"
    )
    dependency_conflicts = _matching(changed, dependency_patterns + identity_patterns)
    authority_conflicts = _matching(changed, semantic_patterns)
    integration_paths = _matching(
        changed,
        tuple(_safe_path(pattern) for pattern in global_integration_patterns)
        + shared_integration_patterns,
    )

    if source_tree == current_tree:
        return FrontierMovementDecision(
            disposition="NO_MOVEMENT",
            source_predecessor_tree=source_tree,
            current_predecessor_tree=current_tree,
            changed_paths=changed,
            a1_renewal_required=False,
            a2_renewal_required=True,
        )
    if authority_changed or authority_conflicts:
        return FrontierMovementDecision(
            disposition="AUTHORITY_REVIEW_REQUIRED",
            source_predecessor_tree=source_tree,
            current_predecessor_tree=current_tree,
            changed_paths=changed,
            authority_conflicts=authority_conflicts,
            integration_relevant_paths=integration_paths,
            a0_reuse_allowed=False,
            payload_rebuild_required=False,
            authority_review_required=True,
        )
    if dependency_frontier_changed or dependency_conflicts or payload_conflicts:
        return FrontierMovementDecision(
            disposition="PAYLOAD_REBUILD_REQUIRED",
            source_predecessor_tree=source_tree,
            current_predecessor_tree=current_tree,
            changed_paths=changed,
            payload_conflicts=payload_conflicts,
            dependency_conflicts=dependency_conflicts,
            integration_relevant_paths=integration_paths,
            a0_reuse_allowed=False,
            payload_rebuild_required=True,
        )
    if integration_paths:
        return FrontierMovementDecision(
            disposition="ASSURANCE_RENEWAL_REQUIRED",
            source_predecessor_tree=source_tree,
            current_predecessor_tree=current_tree,
            changed_paths=changed,
            integration_relevant_paths=integration_paths,
        )
    return FrontierMovementDecision(
        disposition="PLACEMENT_RECOMPUTE_ONLY",
        source_predecessor_tree=source_tree,
        current_predecessor_tree=current_tree,
        changed_paths=changed,
    )


def waiting_predecessor_decision(
    *, source_predecessor_tree: str, current_main_tree: str
) -> FrontierMovementDecision:
    return FrontierMovementDecision(
        disposition="WAITING_VIT_PREDECESSOR",
        source_predecessor_tree=_hex(
            source_predecessor_tree, 40, "VIT_SOURCE_PREDECESSOR_TREE"
        ),
        current_predecessor_tree=_hex(
            current_main_tree, 40, "VIT_CURRENT_PREDECESSOR_TREE"
        ),
        a1_renewal_required=False,
        a2_renewal_required=False,
    )


def build_frontier_lineage(
    *,
    source_lineage_record: Mapping[str, Any],
    source_head: SourceHead,
    predecessor_commit: str,
    predecessor_tree: str,
    prospective_result_tree: str,
    movement: FrontierMovementDecision,
) -> dict[str, Any]:
    """Create one content-addressed current-frontier lineage for the unchanged PIP."""

    source = validate_vit_lineage_record(source_lineage_record)
    source_generation = source_lineage_record.get("generation")
    if not isinstance(source_generation, Mapping):
        raise VitContractError("VIT_SOURCE_GENERATION_INVALID")
    source_result = source_generation.get("result_tree")
    if not isinstance(source_result, Mapping):
        raise VitContractError("VIT_SOURCE_RESULT_TREE_INVALID")
    if _hex(source_result.get("tree_sha"), 40, "VIT_SOURCE_RESULT_TREE") != source_head.tree_sha:
        raise VitContractError("VIT_SOURCE_LINEAGE_RESULT_NOT_SOURCE_HEAD_TREE")

    predecessor_commit = _hex(
        predecessor_commit, 40, "VIT_FRONTIER_PREDECESSOR_COMMIT"
    )
    predecessor_tree = _hex(
        predecessor_tree, 40, "VIT_FRONTIER_PREDECESSOR_TREE"
    )
    result_tree = _hex(
        prospective_result_tree, 40, "VIT_FRONTIER_RESULT_TREE"
    )
    if movement.current_predecessor_tree != predecessor_tree:
        raise VitContractError("VIT_MOVEMENT_PREDECESSOR_TREE_MISMATCH")
    if movement.disposition in {
        "PAYLOAD_REBUILD_REQUIRED",
        "AUTHORITY_REVIEW_REQUIRED",
        "WAITING_VIT_PREDECESSOR",
    }:
        raise VitContractError(
            f"VIT_FRONTIER_LINEAGE_NOT_ADMISSIBLE:{movement.disposition}"
        )

    pip = source_lineage_record.get("pip")
    if not isinstance(pip, Mapping):
        raise VitContractError("VIT_SOURCE_PIP_INVALID")
    record = build_vit_lineage_record(
        programme_id=source.programme_id,
        packet_id=source.packet_id,
        pip_identity_payload=dict(pip),
        train_generation_id=str(source_generation["train_generation_id"]),
        ordinal=int(source_generation["ordinal"]),
        predecessor_tree_sha=predecessor_tree,
        result_tree_sha=result_tree,
        apply_profile=str(
            (source_lineage_record.get("placement") or {}).get(
                "apply_profile", REFERENCE_APPLY_PROFILE
            )
        ),
        route_class=source.route_class,
    )
    frontier = {
        "schema": FRONTIER_RESOLUTION_SCHEMA,
        "source_head": asdict(source_head),
        "source_head_id": source_head.source_head_id,
        "source_pip_id": source.pip_id,
        "source_generation_id": source.generation_id,
        "source_placement_id": source.placement_id,
        "current_predecessor_commit": predecessor_commit,
        "current_predecessor_tree": predecessor_tree,
        "prospective_result_tree": result_tree,
        "movement_decision": asdict(movement),
        "movement_decision_id": movement.decision_id,
        "a0_binding": {
            "payload_id": source.pip_id,
            "reused": movement.a0_reuse_allowed,
        },
        "a1_binding": {
            "predecessor_tree": predecessor_tree,
            "payload_id": source.pip_id,
            "result_tree": result_tree,
        },
        "a2_binding": {
            "generation_id": record["generation_id"],
            "placement_id": record["placement_id"],
            "prospective_result_tree": result_tree,
        },
        "pr_role": "TRANSPORT_AND_SOURCE_PROVENANCE_ONLY",
        "authority_effect": "NONE",
    }
    record["frontier_resolution"] = frontier
    record["frontier_resolution_id"] = canonical_sha256(
        frontier, role="OVC_VIT_FRONTIER_RESOLUTION"
    )
    validate_frontier_lineage(record)
    return record


def validate_frontier_lineage(record: Mapping[str, Any]) -> None:
    lineage = validate_vit_lineage_record(record)
    frontier = record.get("frontier_resolution")
    if not isinstance(frontier, Mapping):
        raise VitContractError("VIT_FRONTIER_RESOLUTION_MISSING")
    if frontier.get("schema") != FRONTIER_RESOLUTION_SCHEMA:
        raise VitContractError("VIT_FRONTIER_RESOLUTION_SCHEMA_INVALID")
    source_head = frontier.get("source_head")
    if not isinstance(source_head, Mapping):
        raise VitContractError("VIT_FRONTIER_SOURCE_HEAD_INVALID")
    source = SourceHead(**dict(source_head))
    if frontier.get("source_head_id") != source.source_head_id:
        raise VitContractError("VIT_FRONTIER_SOURCE_HEAD_ID_INVALID")
    if frontier.get("source_pip_id") != lineage.pip_id:
        raise VitContractError("VIT_FRONTIER_PIP_ID_MISMATCH")
    generation = record["generation"]
    predecessor_tree = generation["predecessor_tree"]["tree_sha"]
    result_tree = generation["result_tree"]["tree_sha"]
    if frontier.get("current_predecessor_tree") != predecessor_tree:
        raise VitContractError("VIT_FRONTIER_PREDECESSOR_TREE_MISMATCH")
    if frontier.get("prospective_result_tree") != result_tree:
        raise VitContractError("VIT_FRONTIER_RESULT_TREE_MISMATCH")
    if frontier.get("a1_binding") != {
        "predecessor_tree": predecessor_tree,
        "payload_id": lineage.pip_id,
        "result_tree": result_tree,
    }:
        raise VitContractError("VIT_FRONTIER_A1_BINDING_INVALID")
    if frontier.get("a2_binding") != {
        "generation_id": lineage.generation_id,
        "placement_id": lineage.placement_id,
        "prospective_result_tree": result_tree,
    }:
        raise VitContractError("VIT_FRONTIER_A2_BINDING_INVALID")
    expected = canonical_sha256(frontier, role="OVC_VIT_FRONTIER_RESOLUTION")
    if record.get("frontier_resolution_id") != expected:
        raise VitContractError("VIT_FRONTIER_RESOLUTION_ID_INVALID")


@dataclass(frozen=True)
class FrontierIntegrationAssuranceGeneration:
    source_head_id: str
    source_head_commit: str
    pip_id: str
    vit_generation_id: str
    placement_id: str
    predecessor_commit: str
    predecessor_tree: str
    prospective_result_tree: str
    authority_manifest_id: str
    dependency_frontier_id: str
    policy_id: str
    a0_result_ids: tuple[str, ...]
    a1_proof_id: str
    assurance_stage: str = "A0_A1_BOUND"
    a2_result_ids: tuple[str, ...] = ()
    source_run_ids: tuple[str, ...] = ()
    supersedes_assurance_generation_id: str | None = None
    schema: str = ASSURANCE_GENERATION_SCHEMA

    def __post_init__(self) -> None:
        for label, value, length in (
            ("SOURCE_HEAD_ID", self.source_head_id, 64),
            ("SOURCE_HEAD_COMMIT", self.source_head_commit, 40),
            ("PIP", self.pip_id, 64),
            ("VIT_GENERATION", self.vit_generation_id, 64),
            ("PLACEMENT", self.placement_id, 64),
            ("PREDECESSOR_COMMIT", self.predecessor_commit, 40),
            ("PREDECESSOR_TREE", self.predecessor_tree, 40),
            ("RESULT_TREE", self.prospective_result_tree, 40),
            ("AUTHORITY", self.authority_manifest_id, 64),
            ("FRONTIER", self.dependency_frontier_id, 64),
            ("A1_PROOF", self.a1_proof_id, 64),
        ):
            _hex(value, length, f"VIT_ASSURANCE_{label}")
        if self.schema != ASSURANCE_GENERATION_SCHEMA:
            raise VitContractError("VIT_ASSURANCE_SCHEMA_INVALID")
        if self.assurance_stage not in {"A0_A1_BOUND", "A2_QUALIFIED"}:
            raise VitContractError("VIT_ASSURANCE_STAGE_INVALID")
        if self.assurance_stage == "A0_A1_BOUND" and self.a2_result_ids:
            raise VitContractError("VIT_ASSURANCE_A2_RESULTS_BEFORE_A2_QUALIFICATION")
        if self.assurance_stage == "A2_QUALIFIED" and not self.a2_result_ids:
            raise VitContractError("VIT_ASSURANCE_A2_RESULTS_REQUIRED")
        if not self.policy_id.strip() or not self.a0_result_ids:
            raise VitContractError("VIT_ASSURANCE_GENERATION_INCOMPLETE")
        for result_id in self.a0_result_ids + self.a2_result_ids:
            _hex(result_id, 64, "VIT_ASSURANCE_RESULT_ID")
        if self.supersedes_assurance_generation_id is not None:
            _hex(
                self.supersedes_assurance_generation_id,
                64,
                "VIT_ASSURANCE_SUPERSEDES",
            )

    @property
    def assurance_generation_id(self) -> str:
        return canonical_sha256(
            asdict(self), role="OVC_VIT_FRONTIER_ASSURANCE_GENERATION"
        )


def build_a2_proof(
    *,
    frontier_lineage: Mapping[str, Any],
    workflow_run_id: str,
    run_attempt: str,
    job_name: str = "OVC merge readiness",
) -> dict[str, Any]:
    """Bind observed A2 success to one exact VIT generation and prospective tree."""

    validate_frontier_lineage(frontier_lineage)
    lineage = validate_vit_lineage_record(frontier_lineage)
    resolution = frontier_lineage["frontier_resolution"]
    logical = {
        "schema": A2_PROOF_SCHEMA,
        "vit_generation_id": lineage.generation_id,
        "placement_id": lineage.placement_id,
        "predecessor_commit": str(resolution["current_predecessor_commit"]),
        "predecessor_tree": str(resolution["current_predecessor_tree"]),
        "prospective_result_tree": str(resolution["prospective_result_tree"]),
        "workflow_run_id": _required(workflow_run_id, "VIT_A2_WORKFLOW_RUN_ID"),
        "run_attempt": _required(run_attempt, "VIT_A2_RUN_ATTEMPT"),
        "job_name": _required(job_name, "VIT_A2_JOB_NAME"),
        "state": "PASS",
        "assurance_scope": "AA2_MATERIALISATION_EDGE_AND_EXACT_PROSPECTIVE_TREE",
        "authority_effect": "NONE",
    }
    return {
        **logical,
        "record_id": canonical_sha256(logical, role="OVC_VIT_A2_PROSPECTIVE_TREE_PROOF"),
    }


def validate_a2_proof(
    record: Mapping[str, Any], *, frontier_lineage: Mapping[str, Any]
) -> str:
    if record.get("schema") != A2_PROOF_SCHEMA or record.get("state") != "PASS":
        raise VitContractError("VIT_A2_PROOF_INVALID")
    validate_frontier_lineage(frontier_lineage)
    lineage = validate_vit_lineage_record(frontier_lineage)
    resolution = frontier_lineage["frontier_resolution"]
    expected_fields = {
        "vit_generation_id": lineage.generation_id,
        "placement_id": lineage.placement_id,
        "predecessor_commit": str(resolution["current_predecessor_commit"]),
        "predecessor_tree": str(resolution["current_predecessor_tree"]),
        "prospective_result_tree": str(resolution["prospective_result_tree"]),
    }
    for field, expected in expected_fields.items():
        if record.get(field) != expected:
            raise VitContractError(f"VIT_A2_PROOF_{field.upper()}_MISMATCH")
    logical = {key: value for key, value in record.items() if key != "record_id"}
    expected_id = canonical_sha256(logical, role="OVC_VIT_A2_PROSPECTIVE_TREE_PROOF")
    if record.get("record_id") != expected_id:
        raise VitContractError("VIT_A2_PROOF_ID_INVALID")
    return expected_id


def assurance_generation_from_record(
    record: Mapping[str, Any], *, expected_id: str | None = None
) -> FrontierIntegrationAssuranceGeneration:
    generation = FrontierIntegrationAssuranceGeneration(**dict(record))
    observed = generation.assurance_generation_id
    if expected_id is not None and observed != expected_id:
        raise VitContractError("VIT_ASSURANCE_GENERATION_ID_MISMATCH")
    return generation


def build_frontier_ledger_envelope(
    *,
    frontier_lineage: Mapping[str, Any],
    assurance_generation: FrontierIntegrationAssuranceGeneration | Mapping[str, Any],
    a2_proof: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one closed, reconstructible ledger envelope for post-write A3.

    The envelope carries canonical base64 records rather than embedding open-ended
    nested mappings in the physical transaction freeze.  Post-merge completion
    decodes, revalidates and persists every content-addressed record separately.
    """

    validate_frontier_lineage(frontier_lineage)
    lineage = validate_vit_lineage_record(frontier_lineage)
    frontier_record = dict(frontier_lineage)
    frontier_record_id = canonical_sha256(
        frontier_record, role="OVC_VIT_FRONTIER_LEDGER_RECORD"
    )
    assurance_record = (
        asdict(assurance_generation)
        if isinstance(assurance_generation, FrontierIntegrationAssuranceGeneration)
        else dict(assurance_generation)
    )
    assurance = assurance_generation_from_record(assurance_record)
    if assurance.assurance_stage != "A2_QUALIFIED":
        raise VitContractError("VIT_FRONTIER_LEDGER_A2_ASSURANCE_REQUIRED")
    resolution = frontier_lineage["frontier_resolution"]
    expected = {
        "pip_id": lineage.pip_id,
        "vit_generation_id": lineage.generation_id,
        "placement_id": lineage.placement_id,
        "predecessor_commit": str(resolution["current_predecessor_commit"]),
        "predecessor_tree": str(resolution["current_predecessor_tree"]),
        "prospective_result_tree": str(resolution["prospective_result_tree"]),
    }
    for field, value in expected.items():
        if getattr(assurance, field) != value:
            raise VitContractError(
                f"VIT_FRONTIER_LEDGER_ASSURANCE_{field.upper()}_MISMATCH"
            )
    a2_id = validate_a2_proof(a2_proof, frontier_lineage=frontier_lineage)
    if a2_id not in assurance.a2_result_ids:
        raise VitContractError("VIT_FRONTIER_LEDGER_A2_NOT_BOUND_TO_ASSURANCE")

    logical = {
        "schema": FRONTIER_LEDGER_ENVELOPE_SCHEMA,
        "source_head_id": assurance.source_head_id,
        "pip_id": lineage.pip_id,
        "vit_generation_id": lineage.generation_id,
        "placement_id": lineage.placement_id,
        "frontier_lineage_record_id": frontier_record_id,
        "frontier_lineage_b64": encode_record(frontier_record),
        "assurance_generation_id": assurance.assurance_generation_id,
        "assurance_generation_b64": encode_record(assurance_record),
        "a2_proof_id": a2_id,
        "a2_proof_b64": encode_record(a2_proof),
        "authority_effect": "NONE",
    }
    return {
        **logical,
        "record_id": canonical_sha256(
            logical, role="OVC_VIT_FRONTIER_LEDGER_ENVELOPE"
        ),
    }


def validate_frontier_ledger_envelope(
    envelope: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate and decode the late frontier ledger envelope."""

    if envelope.get("schema") != FRONTIER_LEDGER_ENVELOPE_SCHEMA:
        raise VitContractError("VIT_FRONTIER_LEDGER_ENVELOPE_SCHEMA_INVALID")
    allowed = {
        "schema",
        "source_head_id",
        "pip_id",
        "vit_generation_id",
        "placement_id",
        "frontier_lineage_record_id",
        "frontier_lineage_b64",
        "assurance_generation_id",
        "assurance_generation_b64",
        "a2_proof_id",
        "a2_proof_b64",
        "authority_effect",
        "record_id",
    }
    if set(envelope) != allowed or envelope.get("authority_effect") != "NONE":
        raise VitContractError("VIT_FRONTIER_LEDGER_ENVELOPE_FIELDS_INVALID")
    for field in (
        "source_head_id",
        "pip_id",
        "vit_generation_id",
        "placement_id",
        "frontier_lineage_record_id",
        "assurance_generation_id",
        "a2_proof_id",
        "record_id",
    ):
        _hex(envelope.get(field), 64, f"VIT_FRONTIER_LEDGER_{field.upper()}")

    frontier = decode_record(str(envelope["frontier_lineage_b64"]))
    validate_frontier_lineage(frontier)
    lineage = validate_vit_lineage_record(frontier)
    frontier_id = canonical_sha256(
        dict(frontier), role="OVC_VIT_FRONTIER_LEDGER_RECORD"
    )
    if frontier_id != envelope["frontier_lineage_record_id"]:
        raise VitContractError("VIT_FRONTIER_LEDGER_LINEAGE_ID_MISMATCH")

    assurance_record = decode_record(str(envelope["assurance_generation_b64"]))
    assurance = assurance_generation_from_record(
        assurance_record, expected_id=str(envelope["assurance_generation_id"])
    )
    a2_proof = decode_record(str(envelope["a2_proof_b64"]))
    a2_id = validate_a2_proof(a2_proof, frontier_lineage=frontier)
    if a2_id != envelope["a2_proof_id"] or a2_id not in assurance.a2_result_ids:
        raise VitContractError("VIT_FRONTIER_LEDGER_A2_BINDING_INVALID")

    matches = {
        "source_head_id": assurance.source_head_id,
        "pip_id": lineage.pip_id,
        "vit_generation_id": lineage.generation_id,
        "placement_id": lineage.placement_id,
    }
    for field, expected in matches.items():
        if envelope[field] != expected:
            raise VitContractError(
                f"VIT_FRONTIER_LEDGER_{field.upper()}_MISMATCH"
            )
    if assurance.assurance_stage != "A2_QUALIFIED":
        raise VitContractError("VIT_FRONTIER_LEDGER_A2_ASSURANCE_REQUIRED")

    logical = {key: value for key, value in envelope.items() if key != "record_id"}
    expected_envelope_id = canonical_sha256(
        logical, role="OVC_VIT_FRONTIER_LEDGER_ENVELOPE"
    )
    if envelope["record_id"] != expected_envelope_id:
        raise VitContractError("VIT_FRONTIER_LEDGER_ENVELOPE_ID_INVALID")
    return {
        "frontier_lineage": frontier,
        "frontier_lineage_record_id": frontier_id,
        "assurance_generation": dict(assurance_record),
        "assurance_generation_id": assurance.assurance_generation_id,
        "a2_proof": dict(a2_proof),
        "a2_proof_id": a2_id,
        "envelope_record": dict(envelope),
        "envelope_record_id": expected_envelope_id,
    }


@dataclass(frozen=True)
class FrontierIntegrationAdmissionReceipt:
    assurance_generation_id: str
    transaction_id: str
    source_head_id: str
    source_head_commit: str
    pip_id: str
    vit_generation_id: str
    placement_id: str
    predecessor_commit: str
    predecessor_tree: str
    prospective_result_tree: str
    grt_proof_binding_id: str
    disposition: str
    reason_codes: tuple[str, ...] = ()
    schema: str = ADMISSION_RECEIPT_SCHEMA

    def __post_init__(self) -> None:
        for label, value, length in (
            ("ASSURANCE", self.assurance_generation_id, 64),
            ("TRANSACTION", self.transaction_id, 64),
            ("SOURCE_HEAD_ID", self.source_head_id, 64),
            ("SOURCE_HEAD_COMMIT", self.source_head_commit, 40),
            ("PIP", self.pip_id, 64),
            ("GENERATION", self.vit_generation_id, 64),
            ("PLACEMENT", self.placement_id, 64),
            ("PREDECESSOR_COMMIT", self.predecessor_commit, 40),
            ("PREDECESSOR_TREE", self.predecessor_tree, 40),
            ("RESULT_TREE", self.prospective_result_tree, 40),
            ("GRT", self.grt_proof_binding_id, 64),
        ):
            _hex(value, length, f"VIT_ADMISSION_{label}")
        if self.schema != ADMISSION_RECEIPT_SCHEMA:
            raise VitContractError("VIT_ADMISSION_SCHEMA_INVALID")
        if self.disposition != "FRONTIER_READY":
            raise VitContractError("VIT_ADMISSION_DISPOSITION_INVALID")

    @property
    def receipt_id(self) -> str:
        return canonical_sha256(
            asdict(self), role="OVC_VIT_FRONTIER_ADMISSION_RECEIPT"
        )


def a1_proof_id(frontier_lineage: Mapping[str, Any]) -> str:
    validate_frontier_lineage(frontier_lineage)
    lineage = validate_vit_lineage_record(frontier_lineage)
    generation = frontier_lineage["generation"]
    return canonical_sha256(
        {
            "predecessor_tree": generation["predecessor_tree"]["tree_sha"],
            "payload_id": lineage.pip_id,
            "prospective_result_tree": generation["result_tree"]["tree_sha"],
            "apply_profile": frontier_lineage["placement"]["apply_profile"],
        },
        role="OVC_VIT_A1_REFERENCE_APPLY_PROOF",
    )


def encode_record(record: Mapping[str, Any]) -> str:
    raw = json.dumps(
        dict(record),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_record(token: str) -> Mapping[str, Any]:
    token = str(token).strip()
    token += "=" * ((4 - len(token) % 4) % 4)
    try:
        value = json.loads(
            base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        )
    except Exception as exc:
        raise VitContractError("VIT_FRONTIER_RECORD_ENCODING_INVALID") from exc
    if not isinstance(value, Mapping):
        raise VitContractError("VIT_FRONTIER_RECORD_INVALID")
    return value
