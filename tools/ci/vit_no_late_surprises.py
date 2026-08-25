from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Sequence

from ovc.development.skills.vit_core import VitContractError
from ovc.development.skills.vit_routing import validate_vit_lineage_record

PREQUALIFICATION_SCHEMA = "ovc-no-late-surprises-prequalification/v0.1"
COMPILER_VERSION = "NLS/1"
FORBIDDEN_PIP_KEYS = frozenset(
    {
        "base_sha",
        "main_sha",
        "current_main",
        "physical_main",
        "predecessor_tree",
        "result_tree",
        "placement",
        "placement_id",
        "ordinal",
        "queue_position",
        "train_generation_id",
    }
)
ALLOWED_SHARED_SYSTEMS_EXTERNAL_IMPORTS = frozenset({"pytest"})


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        dict(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _git(root: Path, args: Sequence[str], *, binary: bool = False):
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=not binary,
        timeout=30,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace") if binary else proc.stderr
        raise RuntimeError(stderr.strip() or "NLS_GIT_COMMAND_FAILED")
    return proc.stdout if binary else proc.stdout.strip()


def _git_tree(root: Path, head_sha: str) -> str:
    tree = _git(root, ["rev-parse", f"{head_sha}^{{tree}}"])
    if len(tree) != 40:
        raise RuntimeError("NLS_HEAD_TREE_INVALID")
    return tree


def _head_entry(root: Path, head_sha: str, path: str) -> tuple[str, str, str] | None:
    row = _git(root, ["ls-tree", head_sha, "--", path])
    if not row:
        return None
    meta, listed = row.split("\t", 1)
    if listed != path:
        raise RuntimeError(f"NLS_HEAD_ENTRY_PATH_MISMATCH:{path}")
    mode, object_type, object_sha = meta.split(" ", 2)
    return mode, object_type, object_sha


def _validate_payload_against_head(*, root: Path, head_sha: str, record: Mapping[str, Any]) -> list[str]:
    pip = record.get("pip")
    if not isinstance(pip, Mapping):
        raise RuntimeError("NLS_PIP_INVALID")
    forbidden = sorted(FORBIDDEN_PIP_KEYS.intersection(str(key) for key in pip.keys()))
    if forbidden:
        raise RuntimeError(f"NLS_PHYSICAL_PLACEMENT_IDENTITY_FORBIDDEN:{','.join(forbidden)}")

    changes = pip.get("logical_changes")
    if not isinstance(changes, list) or not changes:
        raise RuntimeError("NLS_PIP_CHANGES_INVALID")

    seen: set[str] = set()
    paths: list[str] = []
    for change in changes:
        if not isinstance(change, Mapping):
            raise RuntimeError("NLS_PIP_CHANGE_INVALID")
        path = str(change.get("path", ""))
        if not path or Path(path).is_absolute() or ".." in Path(path).parts or path in seen:
            raise RuntimeError(f"NLS_PIP_PATH_INVALID:{path}")
        seen.add(path)

        op = str(change.get("op", ""))
        entry = _head_entry(root, head_sha, path)
        if op == "DELETE":
            if entry is not None:
                raise RuntimeError(f"NLS_PIP_DELETE_STILL_PRESENT:{path}")
            continue
        paths.append(path)
        if op not in {"ADD", "MODIFY"}:
            raise RuntimeError(f"NLS_PIP_OP_INVALID:{op}:{path}")
        if entry is None:
            raise RuntimeError(f"NLS_PIP_HEAD_PATH_MISSING:{path}")
        mode, object_type, object_sha = entry
        if object_type not in {"blob", "commit"}:
            raise RuntimeError(f"NLS_PIP_HEAD_ENTRY_INVALID:{path}")
        if object_sha != str(change.get("blob_sha", "")) or mode != str(change.get("mode", "")):
            raise RuntimeError(f"NLS_PIP_HEAD_BLOB_MISMATCH:{path}")
    return paths


def _project_import_roots(root: Path) -> set[str]:
    roots: set[str] = {"tests", "tools", "scripts"}
    src = root / "src"
    if src.is_dir():
        for child in src.iterdir():
            if child.name.startswith("."):
                continue
            if child.is_dir() and (child / "__init__.py").is_file():
                roots.add(child.name)
            elif child.is_file() and child.suffix == ".py":
                roots.add(child.stem)
    return roots


def _import_roots(source: str, path: str) -> set[str]:
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as exc:
        raise RuntimeError(f"NLS_PYTHON_SYNTAX_INVALID:{path}:{exc.msg}") from exc
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def _validate_shared_systems_dependency_closure(
    *,
    root: Path,
    head_sha: str,
    logical_paths: Sequence[str],
) -> None:
    project_roots = _project_import_roots(root)
    stdlib = set(getattr(sys, "stdlib_module_names", ()))
    allowed = stdlib | project_roots | set(ALLOWED_SHARED_SYSTEMS_EXTERNAL_IMPORTS)
    for path in logical_paths:
        if not path.startswith("tests/shared_systems/") or not path.endswith(".py"):
            continue
        raw = _git(root, ["cat-file", "blob", f"{head_sha}:{path}"], binary=True)
        source = raw.decode("utf-8")
        external = sorted(root_name for root_name in _import_roots(source, path) if root_name not in allowed)
        if external:
            raise RuntimeError(
                f"NLS_SHARED_SYSTEMS_UNDECLARED_DEPENDENCY:{path}:{','.join(external)}"
            )


def compile_prequalification(
    *,
    root: Path,
    head_sha: str,
    lineage_record: Mapping[str, Any],
) -> Mapping[str, Any]:
    try:
        lineage = validate_vit_lineage_record(lineage_record)
    except (VitContractError, TypeError, ValueError) as exc:
        raise RuntimeError(f"NLS_LINEAGE_INVALID:{exc}") from exc
    if not lineage.late_binding:
        raise RuntimeError("NLS_LATE_BINDING_REQUIRED")

    logical_paths = _validate_payload_against_head(root=root, head_sha=head_sha, record=lineage_record)
    _validate_shared_systems_dependency_closure(
        root=root,
        head_sha=head_sha,
        logical_paths=logical_paths,
    )

    pip = lineage_record.get("pip")
    assert isinstance(pip, Mapping)
    payload = {
        "schema_version": PREQUALIFICATION_SCHEMA,
        "compiler_version": COMPILER_VERSION,
        "status": "PASS",
        "candidate_head_sha": head_sha,
        "candidate_head_tree": _git_tree(root, head_sha),
        "pip_id": lineage.pip_id,
        "authority_manifest_id": str(pip.get("authority_manifest_id", "")),
        "dependency_frontier_id": str(pip.get("dependency_frontier_id", "")),
        "checks": [
            "LATE_BINDING_ONLY",
            "PIP_HEAD_BLOB_MODE",
            "NO_PHYSICAL_MAIN_IDENTITY",
            "SHARED_SYSTEMS_IMPORT_CLOSURE",
        ],
    }
    return {**payload, "receipt_id": _canonical_sha256(payload)}


def validate_prequalification_receipt(
    receipt: Mapping[str, Any],
    *,
    expected_head_sha: str | None = None,
    expected_head_tree: str | None = None,
    expected_pip_id: str | None = None,
    expected_authority_manifest_id: str | None = None,
    expected_dependency_frontier_id: str | None = None,
) -> str:
    if str(receipt.get("schema_version", "")) != PREQUALIFICATION_SCHEMA:
        raise RuntimeError("NLS_RECEIPT_SCHEMA_INVALID")
    if str(receipt.get("compiler_version", "")) != COMPILER_VERSION:
        raise RuntimeError("NLS_RECEIPT_COMPILER_INVALID")
    if str(receipt.get("status", "")) != "PASS":
        raise RuntimeError("NLS_RECEIPT_STATUS_INVALID")
    receipt_id = str(receipt.get("receipt_id", ""))
    if len(receipt_id) != 64:
        raise RuntimeError("NLS_RECEIPT_ID_INVALID")
    identity_payload = {key: value for key, value in receipt.items() if key != "receipt_id"}
    if _canonical_sha256(identity_payload) != receipt_id:
        raise RuntimeError("NLS_RECEIPT_ID_MISMATCH")
    expected = {
        "candidate_head_sha": expected_head_sha,
        "candidate_head_tree": expected_head_tree,
        "pip_id": expected_pip_id,
        "authority_manifest_id": expected_authority_manifest_id,
        "dependency_frontier_id": expected_dependency_frontier_id,
    }
    for key, value in expected.items():
        if value is not None and str(receipt.get(key, "")) != value:
            raise RuntimeError(f"NLS_RECEIPT_{key.upper()}_MISMATCH")
    return receipt_id
