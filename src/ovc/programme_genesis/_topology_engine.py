from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
import time
import tracemalloc
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence


class TopologyError(ValueError):
    """Raised when the derived repository topology cannot be built safely."""


DEFAULT_SCAN_ROOTS = (
    "src/",
    "apps/",
    "contracts/",
    "schemas/",
    "registries/",
    "fixtures/",
    "tests/",
    "scripts/",
    "tools/",
    ".github/workflows/",
    "docs/releases/",
    "records/",
    "plans/",
    "legacy/",
)

COMPONENT_TYPES = {
    "PYTHON_PACKAGE",
    "PYTHON_MODULE",
    "CONTRACT",
    "SCHEMA",
    "REGISTRY",
    "FIXTURE",
    "TEST",
    "SCRIPT",
    "TOOL",
    "WORKFLOW",
    "APP",
    "RELEASE_RECORD",
    "EVIDENCE_RECORD",
    "MANIFEST",
    "DECISION_RECORD",
    "PROGRAMME_STATE",
    "DOCUMENT",
    "LEGACY_COMPONENT",
    "EXTERNAL_ARTIFACT_REFERENCE",
}

EDGE_TYPES = {
    "IMPLEMENTS",
    "OWNED_BY",
    "GOVERNED_BY",
    "DEFINED_BY",
    "VALIDATED_BY",
    "TESTED_BY",
    "EXECUTED_BY",
    "READS",
    "WRITES",
    "PRODUCES",
    "CONSUMES",
    "DEPENDS_ON",
    "OPTIONAL_DEPENDS_ON",
    "SUPERSEDES",
    "SUPERSEDED_BY",
    "MIGRATED_FROM",
    "PROJECTS_TO",
    "EXPOSED_BY",
    "REFERENCES",
    "DERIVED_FROM",
    "SHARES_COMPONENT_WITH",
}

EVIDENCE_CLASSES = {
    "SOURCE_EXPLICIT",
    "LINEAGE_EXPLICIT",
    "PATH_AND_CONTENT_CORROBORATED",
    "TEST_CORROBORATED",
    "IMPORT_CORROBORATED",
    "CANDIDATE_RELATION",
    "INFERRED",
    "UNRESOLVED",
}

ANOMALY_CODES = {
    "PROGRAMME_WITHOUT_IMPLEMENTATION",
    "IMPLEMENTATION_WITHOUT_PROGRAMME_OWNER",
    "IMPLEMENTATION_WITHOUT_GENESIS_CROSSWALK",
    "ORPHAN_CONTRACT",
    "ORPHAN_SCHEMA",
    "ORPHAN_REGISTRY",
    "ORPHAN_FIXTURE",
    "ORPHAN_TEST",
    "ORPHAN_WORKFLOW",
    "MISSING_CONTRACT",
    "MISSING_SCHEMA",
    "MISSING_FIXTURE",
    "MISSING_TEST",
    "MISSING_AUTHORITY_RECORD",
    "MISSING_RELEASE_LINEAGE",
    "DUPLICATE_COMPONENT_OWNERSHIP",
    "CONFLICTING_PROGRAMME_OWNERSHIP",
    "GENESIS_TOPOLOGY_CONFLICT",
    "UNRESOLVED_DEPENDENCY",
    "INFERRED_HARD_DEPENDENCY",
    "STALE_PROGRAMME_STATE",
    "STALE_DOCUMENTATION",
    "SUPERSEDED_COMPONENT_STILL_REFERENCED",
    "LEGACY_RUNTIME_IMPORT",
    "AUTHORITY_MISMATCH",
    "IMPLEMENTATION_STATE_MISMATCH",
    "SHADOW_ACTIVE_MISMATCH",
    "RELEASE_WITHOUT_PROGRAMME_LINEAGE",
    "PROGRAMME_WITHOUT_ACCEPTED_COMPLETION_EVIDENCE",
}

_IMPLEMENTATION_TYPES = {"PYTHON_PACKAGE", "PYTHON_MODULE", "SCRIPT", "TOOL", "APP"}
_SUPPORT_TYPES = {"CONTRACT", "SCHEMA", "REGISTRY", "FIXTURE", "TEST", "WORKFLOW"}
_TEXT_SUFFIXES = {".py", ".md", ".json", ".yaml", ".yml", ".toml", ".txt", ".cfg", ".ini", ".csv"}

_PROGRAMME_PATTERNS = (
    re.compile(r'"programme_id"\s*:\s*"([^"\\]+)"'),
    re.compile(r"(?im)^\s*programme_id\s*:\s*['\"`]?([A-Za-z0-9_.:+-]+)"),
    re.compile(r"(?im)^\s*(?:programme|program)\s*:\s*['\"`]?([A-Za-z0-9_.:+-]+)"),
)
_PATH_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_.-])((?:src|apps|contracts|schemas|registries|fixtures|tests|scripts|tools|docs/releases|records|plans|legacy|\.github/workflows)/[A-Za-z0-9_./@+=:-]+)"
)
_RELEASE_ID_PATTERN = re.compile(r'"release_id"\s*:\s*"([^"\\]+)"')
_STATUS_PATTERN = re.compile(r'"status"\s*:\s*"([^"\\]+)"')
_AUTHORITY_EFFECT_PATTERN = re.compile(r'"authority_effect"\s*:\s*"([^"\\]+)"')
_GENESIS_ID_PATTERN = re.compile(r'"(?:genesis_record_id|genesis_id)"\s*:\s*"([^"\\]+)"')
_VERSION_PATTERN = re.compile(r"(?i)(v\d+(?:[._]\d+){0,2})")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _git(repository_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository_root), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise TopologyError(f"git {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout


def resolve_commit(repository_root: Path | str, ref: str = "HEAD") -> str:
    root = Path(repository_root)
    commit = _git(root, "rev-parse", ref).strip()
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit):
        raise TopologyError(f"invalid commit identity: {commit}")
    return commit


def _scan_path(path: str, roots: Sequence[str]) -> bool:
    return any(path == root.rstrip("/") or path.startswith(root) for root in roots)


def tracked_inventory(
    repository_root: Path | str,
    *,
    commit: str,
    scan_roots: Sequence[str] = DEFAULT_SCAN_ROOTS,
) -> list[dict[str, str]]:
    root = Path(repository_root)
    rows: list[dict[str, str]] = []
    for line in _git(root, "ls-tree", "-r", "--full-tree", commit).splitlines():
        metadata, path = line.split("\t", 1)
        mode, object_type, blob_hash = metadata.split(" ", 2)
        if object_type != "blob" or not _scan_path(path, scan_roots):
            continue
        rows.append({"path": path, "blob_hash": blob_hash, "mode": mode})
    return sorted(rows, key=lambda row: row["path"])


def _read_text(
    repository_root: Path,
    path: str,
    *,
    commit: str,
    head_commit: str,
    max_bytes: int,
) -> str:
    suffix = PurePosixPath(path).suffix.lower()
    if suffix not in _TEXT_SUFFIXES:
        return ""
    raw: bytes
    local_path = repository_root / PurePosixPath(path)
    if commit == head_commit and local_path.is_file():
        try:
            raw = local_path.read_bytes()
        except OSError:
            return ""
    else:
        completed = subprocess.run(
            ["git", "-C", str(repository_root), "show", f"{commit}:{path}"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        if completed.returncode != 0:
            return ""
        raw = completed.stdout
    if len(raw) > max_bytes:
        raw = raw[:max_bytes]
    if b"\x00" in raw:
        return ""
    return raw.decode("utf-8", errors="replace")


def classify_component(path: str) -> str:
    pure = PurePosixPath(path)
    name = pure.name.lower()
    suffix = pure.suffix.lower()
    if path.startswith("legacy/"):
        return "LEGACY_COMPONENT"
    if path.startswith(".github/workflows/"):
        return "WORKFLOW"
    if path.startswith("contracts/"):
        return "CONTRACT"
    if path.startswith("schemas/"):
        return "SCHEMA"
    if path.startswith("registries/"):
        return "REGISTRY"
    if path.startswith("fixtures/"):
        return "FIXTURE"
    if path.startswith("tests/"):
        return "TEST"
    if path.startswith("scripts/"):
        return "SCRIPT"
    if path.startswith("tools/"):
        return "TOOL"
    if path.startswith("apps/"):
        return "APP"
    if path.startswith("src/") and suffix == ".py":
        return "PYTHON_PACKAGE" if name == "__init__.py" else "PYTHON_MODULE"
    if path.startswith("docs/releases/"):
        upper = pure.name.upper()
        if "DECISION" in upper:
            return "DECISION_RECORD"
        if "PROGRAMME_STATE" in upper or upper.endswith("_STATE.JSON"):
            return "PROGRAMME_STATE"
        if "MANIFEST" in upper:
            return "MANIFEST"
        if "EVIDENCE" in upper or "RECEIPT" in upper or "QA_PACKET" in upper:
            return "EVIDENCE_RECORD"
        if "RELEASE" in upper:
            return "RELEASE_RECORD"
        return "DOCUMENT"
    if path.startswith(("records/", "plans/")):
        return "DOCUMENT"
    return "DOCUMENT"


def _source_precedence(component_type: str, path: str) -> int:
    if component_type == "DECISION_RECORD":
        return 1
    if component_type == "PROGRAMME_STATE":
        return 3
    if component_type == "REGISTRY" and "authority" in path.lower():
        return 4
    if component_type == "REGISTRY":
        return 5
    if component_type in {"MANIFEST", "RELEASE_RECORD", "EVIDENCE_RECORD"}:
        return 6
    if component_type in {"PYTHON_PACKAGE", "PYTHON_MODULE", "SCRIPT", "TOOL", "APP"}:
        return 7
    if component_type in {"CONTRACT", "SCHEMA"}:
        return 8
    if component_type in {"TEST", "FIXTURE", "WORKFLOW"}:
        return 9
    return 10


def _strong_programme_ids(text: str) -> list[str]:
    values: set[str] = set()
    for pattern in _PROGRAMME_PATTERNS:
        for match in pattern.finditer(text):
            candidate = match.group(1).strip().strip("`'\"")
            if candidate and candidate not in {"NONE", "UNRESOLVED", "null"}:
                values.add(candidate)
    return sorted(values)


def _extract_path_refs(text: str, known_paths: set[str]) -> tuple[list[str], list[str]]:
    found: set[str] = set()
    unresolved: set[str] = set()
    for match in _PATH_PATTERN.finditer(text):
        token = match.group(1).rstrip(".,;:)]}'\"")
        if token in known_paths:
            found.add(token)
        elif PurePosixPath(token).suffix.lower() in _TEXT_SUFFIXES:
            unresolved.add(token)
    return sorted(found), sorted(unresolved)


def _first_match(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    return match.group(1).strip() if match else None


def _logical_name(path: str) -> str:
    pure = PurePosixPath(path)
    if path.startswith("src/") and pure.suffix == ".py":
        parts = list(pure.with_suffix("").parts[1:])
        if parts and parts[-1] == "__init__":
            parts.pop()
        return ".".join(parts)
    if path.startswith("apps/") and pure.suffix == ".py":
        parts = list(pure.with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts.pop()
        return ".".join(parts)
    return pure.stem


def _option_or_domain(path: str) -> str | None:
    lower = path.lower()
    for token in ("opt_a", "opt_b", "opt_c", "opt_d", "research_operations", "programme_genesis", "governance"):
        if token in lower:
            return token.upper()
    return None


def _layer(path: str) -> str | None:
    lower = path.lower()
    for token in ("c2e", "c2p", "c2g", "c2_5", "c2.5", "c2", "c1", "opt_a", "sri", "fdi", "srfd", "mcarb", "irof"):
        if token in lower:
            return token.upper().replace("_", ".")
    return None


def _component_states(component_type: str, path: str, text: str) -> tuple[str, str, str, str]:
    upper = text[:65536].upper()
    if path.startswith("legacy/"):
        implementation = "LEGACY"
        lifecycle = "HISTORICAL"
        historical = "LEGACY"
    elif "SUPERSEDED" in upper and component_type in {"DOCUMENT", "REGISTRY", "CONTRACT", "PROGRAMME_STATE", "DECISION_RECORD"}:
        implementation = "SUPPORTING" if component_type not in _IMPLEMENTATION_TYPES else "SUPERSEDED"
        lifecycle = "SUPERSEDED"
        historical = "SUPERSEDED"
    elif component_type in _IMPLEMENTATION_TYPES:
        implementation = "CURRENT_TRACKED"
        lifecycle = "CURRENT_TRACKED"
        historical = "CURRENT"
    elif component_type in {"RELEASE_RECORD", "EVIDENCE_RECORD", "MANIFEST", "DECISION_RECORD", "PROGRAMME_STATE"}:
        implementation = "EVIDENCE_ONLY"
        lifecycle = "PRESERVED"
        historical = "CURRENT_OR_HISTORICAL_EVIDENCE"
    else:
        implementation = "SUPPORTING"
        lifecycle = "CURRENT_TRACKED"
        historical = "CURRENT"
    qa_state = "PRESENT" if component_type in {"TEST", "FIXTURE", "WORKFLOW"} else "NOT_EVALUATED"
    return implementation, lifecycle, historical, qa_state


def _module_name(path: str) -> str | None:
    pure = PurePosixPath(path)
    if pure.suffix != ".py":
        return None
    if path.startswith("src/"):
        parts = list(pure.with_suffix("").parts[1:])
    elif path.startswith("apps/"):
        parts = list(pure.with_suffix("").parts)
    else:
        return None
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts) if parts else None


def _imports(text: str) -> list[str]:
    if not text.strip():
        return []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module)
    return sorted(result)


def _edge(
    from_id: str,
    to_id: str,
    edge_type: str,
    evidence_class: str,
    source_ref: str,
    source_commit: str,
    *,
    confidence: str = "CORROBORATED",
) -> dict[str, Any]:
    if edge_type not in EDGE_TYPES:
        raise TopologyError(f"unsupported edge type: {edge_type}")
    if evidence_class not in EVIDENCE_CLASSES:
        raise TopologyError(f"unsupported evidence class: {evidence_class}")
    identity = {
        "from_id": from_id,
        "to_id": to_id,
        "edge_type": edge_type,
        "evidence_class": evidence_class,
        "source_ref": source_ref,
    }
    return {
        "edge_id": f"GRT.EDGE.{canonical_sha256(identity)[:24]}",
        **identity,
        "authority_effect": "NONE",
        "confidence_or_evidence_status": confidence,
        "first_seen_commit": source_commit,
        "last_verified_commit": source_commit,
    }


def _structured_json(text: str) -> Any:
    if not text.lstrip().startswith(("{", "[")):
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _programme_dependency_rows(path: str, text: str) -> list[dict[str, Any]]:
    payload = _structured_json(text)
    candidates: list[Mapping[str, Any]] = []
    if isinstance(payload, dict):
        if isinstance(payload.get("edges"), list):
            candidates.extend(item for item in payload["edges"] if isinstance(item, dict))
        if {"edge_type", "from_node", "to_node"}.issubset(payload):
            candidates.append(payload)
    rows: list[dict[str, Any]] = []
    for item in candidates:
        edge_type = str(item.get("edge_type", ""))
        if edge_type not in {"REQUIRES", "GOVERNED_BY", "BLOCKED_BY", "CONSUMES", "PARENT_OF", "PRODUCES", "REFERENCES"}:
            continue
        rows.append(
            {
                "from_programme_id": str(item.get("from_node")),
                "to_programme_id": str(item.get("to_node")),
                "edge_type": edge_type,
                "hardness": str(item.get("hardness", "UNRESOLVED")),
                "status": str(item.get("status", "UNRESOLVED")),
                "source_kind": str(item.get("source_kind", item.get("evidence_status", "UNRESOLVED"))),
                "source_ref": path,
                "authority_effect": "SOURCE_REFERENCED_NOT_REWRITTEN",
            }
        )
    return rows


def _anomaly(
    code: str,
    severity: str,
    *,
    components: Iterable[str] = (),
    programmes: Iterable[str] = (),
    source_evidence: Iterable[str] = (),
    denominator_name: str,
    denominator_count: int,
    recommendation: str,
    detail: str,
) -> dict[str, Any]:
    if code not in ANOMALY_CODES:
        raise TopologyError(f"unsupported anomaly code: {code}")
    if severity not in {"INFO", "WARNING", "BLOCKER"}:
        raise TopologyError(f"unsupported anomaly severity: {severity}")
    row = {
        "anomaly_code": code,
        "severity": severity,
        "affected_component_ids": sorted(set(components)),
        "affected_programme_ids": sorted(set(programmes)),
        "source_evidence": sorted(set(source_evidence)),
        "denominator": {"name": denominator_name, "count": denominator_count},
        "recommended_disposition": recommendation,
        "detail": detail,
        "authority_effect": "NONE_ADVISORY_ONLY",
    }
    row["anomaly_id"] = f"GRT.ANOM.{canonical_sha256(row)[:24]}"
    return row


def _component_category(component_type: str) -> str | None:
    return {
        "PYTHON_PACKAGE": "implementation_namespaces",
        "PYTHON_MODULE": "implementation_namespaces",
        "APP": "implementation_namespaces",
        "CONTRACT": "contracts",
        "SCHEMA": "schemas",
        "REGISTRY": "registries",
        "FIXTURE": "fixtures",
        "TEST": "tests",
        "SCRIPT": "scripts",
        "TOOL": "scripts",
        "WORKFLOW": "workflows",
        "RELEASE_RECORD": "release_records",
        "EVIDENCE_RECORD": "evidence_records",
        "MANIFEST": "evidence_records",
        "DECISION_RECORD": "evidence_records",
    }.get(component_type)


def _build_anomalies(
    programmes: Sequence[Mapping[str, Any]],
    components: Sequence[Mapping[str, Any]],
    crosswalks: Sequence[Mapping[str, Any]],
    component_edges: Sequence[Mapping[str, Any]],
    programme_dependencies: Sequence[Mapping[str, Any]],
    unresolved_refs: Mapping[str, Sequence[str]],
    content_by_path: Mapping[str, str],
) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []
    programme_count = len(programmes)
    component_count = len(components)
    by_id = {str(component["component_id"]): component for component in components}
    by_path = {str(component["path"]): component for component in components}
    crosswalk_by_programme = {str(row["programme_id"]): row for row in crosswalks}
    connected: set[str] = set()
    for edge in component_edges:
        if str(edge["from_id"]) in by_id:
            connected.add(str(edge["from_id"]))
        if str(edge["to_id"]) in by_id:
            connected.add(str(edge["to_id"]))

    for programme in programmes:
        programme_id = str(programme["programme_id"])
        row = crosswalk_by_programme[programme_id]
        implementation = row["implementation_namespaces"]
        if not implementation:
            anomalies.append(_anomaly(
                "PROGRAMME_WITHOUT_IMPLEMENTATION", "WARNING", programmes=[programme_id],
                source_evidence=programme.get("source_refs", []), denominator_name="programmes", denominator_count=programme_count,
                recommendation="REVIEW_PROGRAMME_IMPLEMENTATION_COVERAGE", detail="No owned executable implementation component was derived for this programme.",
            ))
        else:
            for category, code in (("contracts", "MISSING_CONTRACT"), ("schemas", "MISSING_SCHEMA"), ("fixtures", "MISSING_FIXTURE"), ("tests", "MISSING_TEST")):
                if not row[category]:
                    anomalies.append(_anomaly(
                        code, "INFO", components=implementation, programmes=[programme_id], source_evidence=programme.get("source_refs", []),
                        denominator_name="programmes_with_implementation", denominator_count=sum(bool(item["implementation_namespaces"]) for item in crosswalks),
                        recommendation="REVIEW_SUPPORTING_GOVERNANCE_COVERAGE", detail=f"Programme has implementation but no derived {category} association.",
                    ))
        authority_components = row["programme_state_records"] + row["authority_records"]
        if not authority_components:
            anomalies.append(_anomaly(
                "MISSING_AUTHORITY_RECORD", "WARNING", programmes=[programme_id], source_evidence=programme.get("source_refs", []),
                denominator_name="programmes", denominator_count=programme_count, recommendation="REVIEW_AUTHORITATIVE_SOURCE_COVERAGE",
                detail="No programme-state or authority-bearing record was derived for this programme.",
            ))
        if str(programme.get("status", "")).upper() == "COMPLETED" and not row["completion_evidence"]:
            anomalies.append(_anomaly(
                "PROGRAMME_WITHOUT_ACCEPTED_COMPLETION_EVIDENCE", "WARNING", programmes=[programme_id], source_evidence=programme.get("source_refs", []),
                denominator_name="completed_programmes", denominator_count=sum(str(p.get("status", "")).upper() == "COMPLETED" for p in programmes),
                recommendation="REVIEW_COMPLETION_LINEAGE", detail="Programme projects COMPLETED but no decision/receipt completion evidence was associated.",
            ))

    for component in components:
        component_id = str(component["component_id"])
        component_type = str(component["component_type"])
        owners = list(component.get("owner_programme_ids", []))
        if component_type in _IMPLEMENTATION_TYPES and not owners:
            anomalies.append(_anomaly(
                "IMPLEMENTATION_WITHOUT_PROGRAMME_OWNER", "WARNING", components=[component_id], source_evidence=component["source_refs"],
                denominator_name="implementation_components", denominator_count=sum(c["component_type"] in _IMPLEMENTATION_TYPES for c in components),
                recommendation="RESOLVE_OWNERSHIP_OR_PRESERVE_UNRESOLVED", detail="Executable implementation is tracked without a defensible programme owner.",
            ))
        if component_type in _IMPLEMENTATION_TYPES and owners and not component.get("owner_genesis_id"):
            anomalies.append(_anomaly(
                "IMPLEMENTATION_WITHOUT_GENESIS_CROSSWALK", "INFO", components=[component_id], programmes=owners, source_evidence=component["source_refs"],
                denominator_name="owned_implementation_components", denominator_count=sum(c["component_type"] in _IMPLEMENTATION_TYPES and c.get("owner_programme_ids") for c in components),
                recommendation="PRESERVE_NON_NATIVE_OR_DEFERRED_GENESIS_STATUS", detail="Implementation ownership is derived, but no accepted native Genesis identity is bound.",
            ))
        if len(owners) > 1:
            explicit_owners = {item["programme_id"] for item in component.get("ownership_evidence", []) if item["evidence_class"] == "SOURCE_EXPLICIT"}
            code = "CONFLICTING_PROGRAMME_OWNERSHIP" if len(explicit_owners) > 1 else "DUPLICATE_COMPONENT_OWNERSHIP"
            severity = "WARNING" if code == "CONFLICTING_PROGRAMME_OWNERSHIP" else "INFO"
            anomalies.append(_anomaly(
                code, severity, components=[component_id], programmes=owners, source_evidence=component["source_refs"],
                denominator_name="components", denominator_count=component_count, recommendation="REVIEW_SHARED_OR_CONFLICTING_OWNERSHIP",
                detail="Component is associated with more than one programme; no canonical owner was guessed.",
            ))
        orphan_code = {
            "CONTRACT": "ORPHAN_CONTRACT", "SCHEMA": "ORPHAN_SCHEMA", "REGISTRY": "ORPHAN_REGISTRY",
            "FIXTURE": "ORPHAN_FIXTURE", "TEST": "ORPHAN_TEST", "WORKFLOW": "ORPHAN_WORKFLOW",
        }.get(component_type)
        if orphan_code and component_id not in connected and not owners:
            anomalies.append(_anomaly(
                orphan_code, "INFO", components=[component_id], source_evidence=component["source_refs"],
                denominator_name=f"{component_type.lower()}_components", denominator_count=sum(c["component_type"] == component_type for c in components),
                recommendation="REVIEW_ORPHAN_OR_PRESERVE_AS_STANDALONE", detail="Supporting component has no derived owner and no derived component relationship.",
            ))
        if component_type in {"RELEASE_RECORD", "MANIFEST"} and not owners:
            anomalies.append(_anomaly(
                "RELEASE_WITHOUT_PROGRAMME_LINEAGE", "WARNING", components=[component_id], source_evidence=component["source_refs"],
                denominator_name="release_or_manifest_components", denominator_count=sum(c["component_type"] in {"RELEASE_RECORD", "MANIFEST"} for c in components),
                recommendation="REVIEW_RELEASE_LINEAGE", detail="Release/manifest evidence has no derived programme lineage.",
            ))
            anomalies.append(_anomaly(
                "MISSING_RELEASE_LINEAGE", "WARNING", components=[component_id], source_evidence=component["source_refs"],
                denominator_name="release_or_manifest_components", denominator_count=sum(c["component_type"] in {"RELEASE_RECORD", "MANIFEST"} for c in components),
                recommendation="REVIEW_RELEASE_LINEAGE", detail="Required programme lineage is not derivable for this release evidence.",
            ))

    for source_path, refs in sorted(unresolved_refs.items()):
        if not refs:
            continue
        source_component = by_path.get(source_path)
        anomalies.append(_anomaly(
            "UNRESOLVED_DEPENDENCY", "INFO", components=[source_component["component_id"]] if source_component else [],
            programmes=source_component.get("owner_programme_ids", []) if source_component else [], source_evidence=[source_path, *refs[:20]],
            denominator_name="components", denominator_count=component_count, recommendation="REVIEW_MISSING_OR_HISTORICAL_REFERENCE",
            detail=f"{len(refs)} repository-like path reference(s) do not resolve to a scanned tracked component.",
        ))

    for dependency in programme_dependencies:
        if dependency.get("hardness") == "HARD" and dependency.get("source_kind") != "SOURCE_EXPLICIT":
            anomalies.append(_anomaly(
                "INFERRED_HARD_DEPENDENCY", "BLOCKER", programmes=[dependency["from_programme_id"], dependency["to_programme_id"]],
                source_evidence=[dependency["source_ref"]], denominator_name="programme_dependencies", denominator_count=len(programme_dependencies),
                recommendation="DO_NOT_USE_AS_HARD_PREREQUISITE", detail="A hard programme dependency is not source-explicit; topology cannot promote it.",
            ))

    active_sources: set[str] = set()
    incoming_to: defaultdict[str, list[str]] = defaultdict(list)
    for edge in component_edges:
        source = by_id.get(str(edge["from_id"]))
        target = by_id.get(str(edge["to_id"]))
        if source and target and edge["edge_type"] in {"DEPENDS_ON", "REFERENCES", "EXECUTED_BY", "TESTED_BY"}:
            incoming_to[target["component_id"]].append(source["component_id"])
            if source["component_type"] in _IMPLEMENTATION_TYPES and source["historical_state"] == "CURRENT":
                active_sources.add(source["component_id"])
    for component in components:
        if component["historical_state"] in {"SUPERSEDED", "LEGACY"}:
            referrers = [source for source in incoming_to.get(component["component_id"], []) if source in active_sources]
            if referrers:
                anomalies.append(_anomaly(
                    "SUPERSEDED_COMPONENT_STILL_REFERENCED", "WARNING", components=[component["component_id"], *referrers],
                    programmes=component.get("owner_programme_ids", []), source_evidence=component["source_refs"],
                    denominator_name="historical_or_legacy_components", denominator_count=sum(c["historical_state"] in {"SUPERSEDED", "LEGACY"} for c in components),
                    recommendation="REVIEW_RUNTIME_REACHABILITY", detail="Current implementation evidence references a superseded or legacy component.",
                ))

    legacy_paths = {component["path"]: component for component in components if component["historical_state"] == "LEGACY"}
    for edge in component_edges:
        source = by_id.get(str(edge["from_id"]))
        target = by_id.get(str(edge["to_id"]))
        if source and target and source["historical_state"] == "CURRENT" and target["path"] in legacy_paths and edge["edge_type"] == "DEPENDS_ON":
            anomalies.append(_anomaly(
                "LEGACY_RUNTIME_IMPORT", "BLOCKER", components=[source["component_id"], target["component_id"]],
                programmes=source.get("owner_programme_ids", []), source_evidence=[source["path"]], denominator_name="component_dependencies", denominator_count=len(component_edges),
                recommendation="REMOVE_OR_EXPLICITLY_GOVERN_LEGACY_RUNTIME_IMPORT", detail="Current executable code imports a legacy component.",
            ))

    pg_g6_present = any("PG_G6_OPERATOR_DECISION" in path and "READ_ONLY_ROUTE" in text and "DEFER" in text for path, text in content_by_path.items())
    if pg_g6_present:
        for path, text in content_by_path.items():
            if "CONTROL_PLANE_ADAPTER_REGISTRY" in path and "PENDING_PG_G6" in text:
                component = by_path.get(path)
                if component:
                    anomalies.append(_anomaly(
                        "STALE_PROGRAMME_STATE", "WARNING", components=[component["component_id"]], programmes=component.get("owner_programme_ids", []),
                        source_evidence=[path], denominator_name="programme_state_or_registry_components", denominator_count=sum(c["component_type"] in {"PROGRAMME_STATE", "REGISTRY"} for c in components),
                        recommendation="SUPERSEDE_LABEL_NON_DESTRUCTIVELY_IF_SEPARATELY_AUTHORISED", detail="Status label still says PENDING_PG_G6 although accepted PG-G6 already decided route/enforcement DEFER; disabled booleans remain authoritative-by-source and unchanged.",
                    ))
            elif component := by_path.get(path):
                if component["component_type"] == "DOCUMENT" and "PENDING_PG_G6" in text:
                    anomalies.append(_anomaly(
                        "STALE_DOCUMENTATION", "INFO", components=[component["component_id"]], programmes=component.get("owner_programme_ids", []),
                        source_evidence=[path], denominator_name="document_components", denominator_count=sum(c["component_type"] == "DOCUMENT" for c in components),
                        recommendation="REVIEW_DOCUMENTATION_FRESHNESS", detail="Documentation still carries a pre-PG-G6 pending label after the accepted PG-G6 decision.",
                    ))

    for path, text in content_by_path.items():
        component = by_path.get(path)
        if not component:
            continue
        upper = text.upper()
        if "TOPOLOGY_CONFLICT" in upper and path.startswith("docs/releases/genesis-repository-topology"):
            anomalies.append(_anomaly(
                "GENESIS_TOPOLOGY_CONFLICT", "WARNING", components=[component["component_id"]], programmes=component.get("owner_programme_ids", []),
                source_evidence=[path], denominator_name="components", denominator_count=component_count,
                recommendation="REQUIRE_OPERATOR_SOURCE_PRECEDENCE_REVIEW", detail="A topology conflict is explicitly recorded; no automatic resolution is allowed.",
            ))
        if component["historical_state"] in {"SUPERSEDED", "LEGACY"} and "ACTIVE" in upper and component["component_type"] in _IMPLEMENTATION_TYPES:
            anomalies.append(_anomaly(
                "IMPLEMENTATION_STATE_MISMATCH", "WARNING", components=[component["component_id"]], programmes=component.get("owner_programme_ids", []),
                source_evidence=[path], denominator_name="implementation_components", denominator_count=sum(c["component_type"] in _IMPLEMENTATION_TYPES for c in components),
                recommendation="REVIEW_IMPLEMENTATION_LIFECYCLE_STATE", detail="Historical/superseded implementation contains an ACTIVE marker; topology does not reinterpret it.",
            ))
        if component["component_type"] == "REGISTRY" and "SHADOW" in upper and '"ACTIVE"' in upper:
            anomalies.append(_anomaly(
                "SHADOW_ACTIVE_MISMATCH", "INFO", components=[component["component_id"]], programmes=component.get("owner_programme_ids", []),
                source_evidence=[path], denominator_name="registry_components", denominator_count=sum(c["component_type"] == "REGISTRY" for c in components),
                recommendation="REVIEW_SHADOW_ACTIVE_SEMANTICS", detail="Registry contains both SHADOW and ACTIVE markers; no authority interpretation is inferred.",
            ))

    return sorted(anomalies, key=lambda row: (row["severity"], row["anomaly_code"], row["anomaly_id"]))


def build_topology_from_inventory(
    *,
    repository: str,
    source_commit: str,
    entries: Sequence[Mapping[str, str]],
    content_by_path: Mapping[str, str],
    rule_pack: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if len(source_commit) != 40 or any(character not in "0123456789abcdef" for character in source_commit):
        raise TopologyError("source_commit must be a lowercase 40-character SHA")
    rules = deepcopy(dict(rule_pack or {}))
    rule_pack_id = str(rules.get("rule_pack_id", "GRT.TOPOLOGY.RULEPACK.v0.1"))
    rule_pack_sha256 = canonical_sha256(rules)
    known_paths = {str(entry["path"]) for entry in entries}

    raw_components: list[dict[str, Any]] = []
    direct_owners: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    referenced_paths: dict[str, list[str]] = {}
    unresolved_refs: dict[str, list[str]] = {}
    programme_sources: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    programme_dependencies: list[dict[str, Any]] = []

    for entry in sorted(entries, key=lambda item: str(item["path"])):
        path = str(entry["path"])
        blob_hash = str(entry["blob_hash"])
        text = str(content_by_path.get(path, ""))
        component_type = classify_component(path)
        implementation_state, lifecycle_state, historical_state, qa_state = _component_states(component_type, path, text)
        programme_ids = _strong_programme_ids(text)
        refs, unresolved = _extract_path_refs(text, known_paths)
        referenced_paths[path] = refs
        unresolved_refs[path] = unresolved
        release_id = _first_match(_RELEASE_ID_PATTERN, text)
        status = _first_match(_STATUS_PATTERN, text)
        authority_effect = _first_match(_AUTHORITY_EFFECT_PATTERN, text)
        genesis_id = _first_match(_GENESIS_ID_PATTERN, text)
        version_match = _VERSION_PATTERN.search(path)
        identity = {
            "repository": repository,
            "path": path,
            "component_type": component_type,
            "blob_hash_or_tree_hash": blob_hash,
        }
        component_id = f"GRT.COMP.{canonical_sha256(identity)[:24]}"
        row = {
            "component_id": component_id,
            "component_type": component_type,
            "path": path,
            "logical_name": _logical_name(path),
            "repository": repository,
            "commit": source_commit,
            "blob_hash_or_tree_hash": blob_hash,
            "owner_programme_id": None,
            "owner_programme_ids": [],
            "owner_genesis_id": genesis_id,
            "authority_state": authority_effect or "UNRESOLVED",
            "implementation_state": implementation_state,
            "lifecycle_state": lifecycle_state,
            "option_or_domain": _option_or_domain(path),
            "layer": _layer(path),
            "version": version_match.group(1) if version_match else None,
            "schema_version": version_match.group(1) if component_type == "SCHEMA" and version_match else None,
            "release_id": release_id,
            "qa_state": qa_state,
            "freshness_state": "AT_SOURCE_COMMIT",
            "historical_state": historical_state,
            "source_precedence": _source_precedence(component_type, path),
            "source_refs": [f"git:{path}@{blob_hash}"],
            "created_from": "TRACKED_GIT_BLOB",
            "last_verified_at": source_commit,
            "ownership_evidence": [],
        }
        raw_components.append(row)
        for programme_id in programme_ids:
            evidence = {"programme_id": programme_id, "evidence_class": "SOURCE_EXPLICIT", "source_ref": path}
            direct_owners[path].append(evidence)
            programme_sources[programme_id].append({
                "source_ref": path,
                "component_type": component_type,
                "source_precedence": row["source_precedence"],
                "status": status,
                "authority_state": authority_effect,
                "genesis_record_id": genesis_id,
            })
        programme_dependencies.extend(_programme_dependency_rows(path, text))

    by_path = {component["path"]: component for component in raw_components}
    owner_evidence: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for path, evidence_rows in direct_owners.items():
        owner_evidence[path].extend(evidence_rows)
        if len({row["programme_id"] for row in evidence_rows}) != 1:
            continue
        programme_id = evidence_rows[0]["programme_id"]
        source_component = by_path[path]
        if source_component["component_type"] not in {"PROGRAMME_STATE", "DECISION_RECORD", "REGISTRY", "CONTRACT", "MANIFEST", "RELEASE_RECORD", "EVIDENCE_RECORD", "DOCUMENT"}:
            continue
        if source_component["source_precedence"] > 8:
            continue
        for target_path in referenced_paths.get(path, []):
            owner_evidence[target_path].append({
                "programme_id": programme_id,
                "evidence_class": "PATH_AND_CONTENT_CORROBORATED",
                "source_ref": path,
            })

    accepted_native_ids: set[str] = set()
    for programme_id, sources in programme_sources.items():
        for source in sources:
            if source.get("genesis_record_id"):
                accepted_native_ids.add(programme_id)
            if programme_id == "OVC-PG-v0.2" and "OVC_PG_PROGRAMME_STATE_v0_2.json" in str(source["source_ref"]):
                accepted_native_ids.add(programme_id)

    components: list[dict[str, Any]] = []
    for component in raw_components:
        evidence_rows = sorted(owner_evidence.get(component["path"], []), key=lambda row: (row["evidence_class"], row["programme_id"], row["source_ref"]))
        owners = sorted({row["programme_id"] for row in evidence_rows})
        component["owner_programme_ids"] = owners
        component["owner_programme_id"] = owners[0] if len(owners) == 1 else None
        component["ownership_evidence"] = evidence_rows
        if len(owners) == 1 and owners[0] in accepted_native_ids and not component.get("owner_genesis_id"):
            component["owner_genesis_id"] = owners[0]
        components.append(component)
    components.sort(key=lambda item: (item["component_type"], item["path"], item["component_id"]))
    by_path = {component["path"]: component for component in components}

    programmes: list[dict[str, Any]] = []
    for programme_id in sorted(programme_sources):
        sources = sorted(programme_sources[programme_id], key=lambda row: (int(row["source_precedence"]), row["source_ref"]))
        selected_status = next((source["status"] for source in sources if source.get("status")), "UNRESOLVED")
        selected_authority = next((source["authority_state"] for source in sources if source.get("authority_state")), "UNRESOLVED")
        selected_genesis = next((source["genesis_record_id"] for source in sources if source.get("genesis_record_id")), None)
        if programme_id == "OVC-PG-v0.2" and programme_id in accepted_native_ids:
            selected_genesis = selected_genesis or programme_id
        programmes.append({
            "programme_id": programme_id,
            "genesis_record_id": selected_genesis,
            "genesis_status": "ACCEPTED_NATIVE_REFERENCE" if programme_id in accepted_native_ids else "NO_ACCEPTED_NATIVE_GENESIS_BINDING_DERIVED",
            "status": selected_status,
            "authority_state": selected_authority,
            "constitutional_parent": None,
            "source_refs": sorted({source["source_ref"] for source in sources}),
            "source_precedence": min(int(source["source_precedence"]) for source in sources),
            "authority_effect": "NONE_DERIVED_PROJECTION",
        })

    component_edges: list[dict[str, Any]] = []
    edge_keys: set[tuple[str, str, str, str, str]] = set()

    def add_edge(row: dict[str, Any]) -> None:
        key = (row["from_id"], row["to_id"], row["edge_type"], row["evidence_class"], row["source_ref"])
        if key not in edge_keys:
            edge_keys.add(key)
            component_edges.append(row)

    for component in components:
        for evidence in component["ownership_evidence"]:
            add_edge(_edge(
                component["component_id"], f"programme:{evidence['programme_id']}", "OWNED_BY",
                evidence["evidence_class"], evidence["source_ref"], source_commit,
                confidence="EXPLICIT" if evidence["evidence_class"] == "SOURCE_EXPLICIT" else "CORROBORATED",
            ))

    for source_path, refs in sorted(referenced_paths.items()):
        source = by_path[source_path]
        for target_path in refs:
            if target_path == source_path:
                continue
            target = by_path[target_path]
            if source["component_type"] == "TEST":
                add_edge(_edge(target["component_id"], source["component_id"], "TESTED_BY", "TEST_CORROBORATED", source_path, source_commit))
            elif source["component_type"] == "WORKFLOW":
                add_edge(_edge(target["component_id"], source["component_id"], "EXECUTED_BY", "PATH_AND_CONTENT_CORROBORATED", source_path, source_commit))
            elif source["component_type"] == "CONTRACT" and target["component_type"] in _IMPLEMENTATION_TYPES:
                add_edge(_edge(target["component_id"], source["component_id"], "GOVERNED_BY", "PATH_AND_CONTENT_CORROBORATED", source_path, source_commit))
            else:
                add_edge(_edge(source["component_id"], target["component_id"], "REFERENCES", "PATH_AND_CONTENT_CORROBORATED", source_path, source_commit))

    module_map: dict[str, str] = {}
    for component in components:
        module = _module_name(component["path"])
        if module:
            module_map[module] = component["component_id"]
    for source_path, text in sorted(content_by_path.items()):
        source = by_path.get(source_path)
        if not source or PurePosixPath(source_path).suffix != ".py":
            continue
        for imported in _imports(text):
            candidates = [name for name in module_map if imported == name or imported.startswith(f"{name}.")]
            if not candidates:
                continue
            target_name = max(candidates, key=len)
            target_id = module_map[target_name]
            if target_id == source["component_id"]:
                continue
            add_edge(_edge(source["component_id"], target_id, "DEPENDS_ON", "IMPORT_CORROBORATED", source_path, source_commit))
            if source["component_type"] == "TEST":
                add_edge(_edge(target_id, source["component_id"], "TESTED_BY", "TEST_CORROBORATED", source_path, source_commit))

    component_edges.sort(key=lambda row: row["edge_id"])
    programme_dependencies = sorted(
        {canonical_sha256(row): row for row in programme_dependencies}.values(),
        key=lambda row: (row["from_programme_id"], row["to_programme_id"], row["edge_type"], row["source_ref"]),
    )

    components_by_programme: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for component in components:
        for owner in component["owner_programme_ids"]:
            components_by_programme[owner].append(component)
    crosswalks: list[dict[str, Any]] = []
    for programme in programmes:
        programme_id = programme["programme_id"]
        owned = components_by_programme.get(programme_id, [])
        row: dict[str, Any] = {
            "programme_id": programme_id,
            "genesis_record_id": programme["genesis_record_id"],
            "programme_class": "UNRESOLVED",
            "authority_state": programme["authority_state"],
            "status": programme["status"],
            "constitutional_parent": programme["constitutional_parent"],
            "hard_dependencies": sorted({dep["to_programme_id"] for dep in programme_dependencies if dep["from_programme_id"] == programme_id and dep["hardness"] == "HARD" and dep["source_kind"] == "SOURCE_EXPLICIT"}),
            "implementation_namespaces": [], "contracts": [], "schemas": [], "registries": [], "fixtures": [], "tests": [],
            "scripts": [], "workflows": [], "release_records": [], "evidence_records": [], "console_surfaces": [],
            "shared_components": [], "historical_components": [], "programme_state_records": [], "authority_records": [],
            "completion_evidence": [], "open_warnings": [], "topology_health": "NOT_EVALUATED",
            "authority_effect": "NONE_DERIVED_CROSSWALK",
        }
        for component in owned:
            category = _component_category(component["component_type"])
            if category:
                row[category].append(component["component_id"])
            if component["component_type"] == "PROGRAMME_STATE":
                row["programme_state_records"].append(component["component_id"])
            if component["component_type"] in {"DECISION_RECORD", "REGISTRY"} and component["source_precedence"] <= 5:
                row["authority_records"].append(component["component_id"])
            if component["component_type"] in {"DECISION_RECORD", "EVIDENCE_RECORD"} and ("completion" in component["path"].lower() or "receipt" in component["path"].lower()):
                row["completion_evidence"].append(component["component_id"])
            if component["component_type"] == "APP" and "research_console" in component["path"]:
                row["console_surfaces"].append(component["component_id"])
            if len(component["owner_programme_ids"]) > 1:
                row["shared_components"].append(component["component_id"])
            if component["historical_state"] != "CURRENT":
                row["historical_components"].append(component["component_id"])
        for field, value in row.items():
            if isinstance(value, list):
                row[field] = sorted(set(value))
        if not row["implementation_namespaces"]:
            row["coverage_status"] = "NO_IMPLEMENTATION"
        elif all(row[field] for field in ("contracts", "schemas", "fixtures", "tests")):
            row["coverage_status"] = "COMPLETE"
        else:
            row["coverage_status"] = "PARTIAL"
        crosswalks.append(row)

    anomalies = _build_anomalies(
        programmes, components, crosswalks, component_edges, programme_dependencies, unresolved_refs, content_by_path
    )
    anomaly_ids_by_programme: defaultdict[str, list[str]] = defaultdict(list)
    for anomaly in anomalies:
        for programme_id in anomaly["affected_programme_ids"]:
            anomaly_ids_by_programme[programme_id].append(anomaly["anomaly_id"])
    for row in crosswalks:
        ids = sorted(anomaly_ids_by_programme.get(row["programme_id"], []))
        row["open_warnings"] = ids
        programme_anomalies = [a for a in anomalies if row["programme_id"] in a["affected_programme_ids"]]
        if any(a["severity"] == "BLOCKER" for a in programme_anomalies):
            row["topology_health"] = "BLOCKER_PRESENT"
        elif any(a["severity"] == "WARNING" for a in programme_anomalies):
            row["topology_health"] = "WARNINGS_PRESENT"
        elif programme_anomalies:
            row["topology_health"] = "INFO_ONLY"
        else:
            row["topology_health"] = "NO_ANOMALIES_DERIVED"

    type_counts = dict(sorted(Counter(component["component_type"] for component in components).items()))
    edge_type_counts = dict(sorted(Counter(edge["edge_type"] for edge in component_edges).items()))
    evidence_counts = dict(sorted(Counter(edge["evidence_class"] for edge in component_edges).items()))
    anomaly_code_counts = dict(sorted(Counter(anomaly["anomaly_code"] for anomaly in anomalies).items()))
    severity_counts = dict(sorted(Counter(anomaly["severity"] for anomaly in anomalies).items()))
    coverage_counts = dict(sorted(Counter(row["coverage_status"] for row in crosswalks).items()))

    authority_projection = [
        {"authority_state": state, "component_count": count}
        for state, count in sorted(Counter(component["authority_state"] for component in components).items())
    ]
    implementation_projection = [
        {"implementation_state": state, "component_count": count}
        for state, count in sorted(Counter(component["implementation_state"] for component in components).items())
    ]
    release_projection = [
        {"component_id": component["component_id"], "path": component["path"], "release_id": component["release_id"], "owner_programme_ids": component["owner_programme_ids"]}
        for component in components if component["component_type"] in {"RELEASE_RECORD", "MANIFEST", "EVIDENCE_RECORD"}
    ]
    historical_projection = [
        {"component_id": component["component_id"], "path": component["path"], "historical_state": component["historical_state"], "owner_programme_ids": component["owner_programme_ids"]}
        for component in components if component["historical_state"] != "CURRENT"
    ]

    read_model: dict[str, Any] = {
        "schema": "ovc-genesis-repository-topology-read-model/v1",
        "programme_id": "OVC-GENESIS-REPOSITORY-TOPOLOGY-v0.1",
        "authority_effect": "NONE_DERIVED_REPLACEABLE_READ_MODEL",
        "portfolio": {
            "repository": repository,
            "source_commit": source_commit,
            "programme_count": len(programmes),
            "component_count": len(components),
            "component_edge_count": len(component_edges),
            "programme_dependency_count": len(programme_dependencies),
            "anomaly_count": len(anomalies),
            "component_type_counts": type_counts,
            "edge_type_counts": edge_type_counts,
            "edge_evidence_class_counts": evidence_counts,
            "programme_coverage_counts": coverage_counts,
        },
        "programmes": programmes,
        "components": components,
        "programme_component_crosswalk": crosswalks,
        "programme_dependencies": programme_dependencies,
        "component_dependencies": component_edges,
        "authority_projection": authority_projection,
        "implementation_projection": implementation_projection,
        "release_projection": release_projection,
        "anomalies": anomalies,
        "health_summary": {
            "severity_counts": severity_counts,
            "anomaly_code_counts": anomaly_code_counts,
            "denominators": {
                "programmes": len(programmes),
                "components": len(components),
                "implementation_components": sum(component["component_type"] in _IMPLEMENTATION_TYPES for component in components),
                "component_dependencies": len(component_edges),
                "programme_dependencies": len(programme_dependencies),
            },
            "opaque_score": None,
        },
        "historical_supersession_projection": historical_projection,
        "build_metadata": {
            "repository": repository,
            "source_commit": source_commit,
            "rule_pack_id": rule_pack_id,
            "rule_pack_sha256": rule_pack_sha256,
            "source_precedence_contract": "GENESIS_REPOSITORY_TOPOLOGY_DESIGN_v0.1",
            "rebuildable": True,
            "logical_identity_excludes": ["wall_clock_duration", "peak_memory", "serialized_size", "hostname", "absolute_local_path", "worker_identity"],
        },
    }
    read_model["topology_sha256"] = canonical_sha256(read_model)
    return read_model


def build_repository_topology(
    repository_root: Path | str,
    *,
    repository: str = "owenguobadia24s-collab/ovc-replay",
    ref: str = "HEAD",
    rule_pack: Mapping[str, Any] | None = None,
    max_text_bytes: int = 512 * 1024,
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    source_commit = resolve_commit(root, ref)
    head_commit = resolve_commit(root, "HEAD")
    rules = dict(rule_pack or {})
    scan_roots = tuple(rules.get("scan_roots", DEFAULT_SCAN_ROOTS))
    entries = tracked_inventory(root, commit=source_commit, scan_roots=scan_roots)
    tracemalloc.start()
    started = time.perf_counter()
    content_by_path = {
        entry["path"]: _read_text(root, entry["path"], commit=source_commit, head_commit=head_commit, max_bytes=max_text_bytes)
        for entry in entries
    }
    result = build_topology_from_inventory(
        repository=repository,
        source_commit=source_commit,
        entries=entries,
        content_by_path=content_by_path,
        rule_pack=rules,
    )
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    serialized_size = len(canonical_json_bytes(result))
    result["diagnostics"] = {
        "full_rebuild_duration_seconds": round(elapsed, 6),
        "peak_traced_memory_bytes": int(peak),
        "serialized_read_model_size_bytes": serialized_size,
        "tracked_scan_entry_count": len(entries),
        "authority_effect": "NONE_DIAGNOSTIC_ONLY",
    }
    return result


def compact_topology_summary(read_model: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": "ovc-genesis-repository-topology-compact-summary/v1",
        "programme_id": read_model["programme_id"],
        "topology_sha256": read_model["topology_sha256"],
        "portfolio": deepcopy(read_model["portfolio"]),
        "health_summary": deepcopy(read_model["health_summary"]),
        "diagnostics": deepcopy(read_model.get("diagnostics", {})),
        "programmes_without_implementation": [
            row["programme_id"] for row in read_model["programme_component_crosswalk"] if row["coverage_status"] == "NO_IMPLEMENTATION"
        ],
        "components_without_programme_owner": [
            component["component_id"] for component in read_model["components"] if not component.get("owner_programme_ids")
        ],
        "shared_components": [
            component["component_id"] for component in read_model["components"] if len(component.get("owner_programme_ids", [])) > 1
        ],
        "unresolved_dependencies": [
            anomaly["anomaly_id"] for anomaly in read_model["anomalies"] if anomaly["anomaly_code"] == "UNRESOLVED_DEPENDENCY"
        ],
        "authority_mismatches": [
            anomaly["anomaly_id"] for anomaly in read_model["anomalies"] if anomaly["anomaly_code"] in {"AUTHORITY_MISMATCH", "GENESIS_TOPOLOGY_CONFLICT", "INFERRED_HARD_DEPENDENCY"}
        ],
        "authority_effect": "NONE_READ_ONLY_SUMMARY",
    }
