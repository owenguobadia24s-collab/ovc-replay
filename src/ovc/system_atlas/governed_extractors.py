from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from copy import deepcopy
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from .canonical import canonical_sha256, logical_id


class AtlasGovernedExtractorError(ValueError):
    """Raised when governed source records cannot be observed exactly."""


GOVERNED_SET_SCHEMA = "ovc-atlas-governed-raw-observation-set/v1"
EXTRACTOR_VERSION = "0.1"
SOURCE_EXTRACTORS = {
    "PROGRAMME_RECORD": "atlas.extractor.programme-record.v0.1",
    "AUTHORITY_RECORD": "atlas.extractor.authority-record.v0.1",
    "CONTRACT": "atlas.extractor.contract.v0.1",
    "SCHEMA": "atlas.extractor.schema.v0.1",
    "REGISTRY": "atlas.extractor.registry.v0.1",
    "RESEARCH_RECORD": "atlas.extractor.research-record.v0.1",
}
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_FIELD = re.compile(r"^([A-Za-z][A-Za-z0-9 _./-]{0,80}):\s*(.+?)\s*$")
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_IDENTITY_KEYS = (
    "programme_id",
    "authority_id",
    "registry_id",
    "manifest_id",
    "contract_id",
    "decision_id",
    "packet_id",
    "gate_id",
    "question_id",
    "protocol_id",
    "research_id",
    "$id",
    "id",
)


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise AtlasGovernedExtractorError(code)


def _git(root: Path, *args: str, binary: bool = False) -> bytes | str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=not binary,
        encoding=None if binary else "utf-8",
        errors=None if binary else "replace",
    )
    _require(completed.returncode == 0, "ATLAS_GOVERNED_GIT_READ_FAILED")
    return completed.stdout


def _source_class(component: Mapping[str, Any]) -> str | None:
    path = str(component.get("path", "")).lower()
    component_type = str(component.get("component_type", ""))
    name = PurePosixPath(path).name
    if "atlas_architecture_manifest" in name:
        return None
    if component_type == "CONTRACT":
        return "CONTRACT"
    if component_type == "SCHEMA":
        return "SCHEMA"
    if (
        component_type == "PROGRAMME_STATE"
        or "/implementation/" in path
        and ("state" in name or "current" in name or "pointer" in name)
    ):
        return "PROGRAMME_RECORD"
    if path.startswith("registries/authority/") or "authority" in name:
        return "AUTHORITY_RECORD"
    if component_type in {"REGISTRY", "PROGRAMME_STATE", "MANIFEST", "DECISION_RECORD", "EVIDENCE_RECORD", "RELEASE_RECORD"}:
        if "research" in path or "/rccr" in path or name.startswith(("rps_", "dmrp_")):
            return "RESEARCH_RECORD"
    if component_type == "REGISTRY":
        return "REGISTRY"
    return None


def _record_subject(path: str, value: Any) -> str:
    if isinstance(value, Mapping):
        for key in _IDENTITY_KEYS:
            candidate = value.get(key)
            if isinstance(candidate, (str, int)) and str(candidate).strip():
                return str(candidate).strip()
    return f"source:{path}"


def _observation(
    *,
    extractor_id: str,
    repository_commit: str,
    repository_tree: str,
    source_path: str,
    source_blob_sha: str,
    locator: str,
    observation_type: str,
    raw_subject: str,
    raw_predicate: str,
    raw_object: Any,
    scope_hints: Mapping[str, Any],
    parse_status: str,
) -> dict[str, Any]:
    content = {
        "observation_type": observation_type,
        "raw_subject": raw_subject,
        "raw_predicate": raw_predicate,
        "raw_object": deepcopy(raw_object),
        "scope_hints": deepcopy(dict(scope_hints)),
        "parse_status": parse_status,
        "evidence_class": "SOURCE_EXPLICIT",
        "source_class": scope_hints["source_class"],
    }
    identity = {
        "extractor_id": extractor_id,
        "extractor_version": EXTRACTOR_VERSION,
        "repository_commit": repository_commit,
        "repository_tree": repository_tree,
        "source_path": source_path,
        "source_blob_sha": source_blob_sha,
        "locator": locator,
        "normalized_content_hash": canonical_sha256(content),
    }
    return {
        "observation_id": logical_id("observation", identity),
        **identity,
        **content,
        "canonical_promotion": "DENIED_PENDING_RESOLVER_AND_PREDICATE_AUTHORITY",
        "authority_effect": "NONE_RAW_OBSERVATION_ONLY",
    }


def _json_observations(*, value: Any, subject: str, context: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = [
        _observation(
            **context,
            locator="#",
            observation_type=f"{context['scope_hints']['source_class']}_PRESENCE",
            raw_subject=subject,
            raw_predicate="PRESENT_IN_EXACT_TREE",
            raw_object={"format": "JSON"},
            parse_status="PARSED",
        )
    ]
    if not isinstance(value, Mapping):
        return rows
    for key in sorted(value):
        raw = value[key]
        if isinstance(raw, (str, int, float, bool)) or raw is None:
            rows.append(
                _observation(
                    **context,
                    locator=f"#/{str(key).replace('~', '~0').replace('/', '~1')}",
                    observation_type=f"{context['scope_hints']['source_class']}_FIELD",
                    raw_subject=subject,
                    raw_predicate=str(key),
                    raw_object=raw,
                    parse_status="PARSED",
                )
            )
    return rows


def _text_observations(*, text: str, subject: str, context: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = [
        _observation(
            **context,
            locator="line:1",
            observation_type=f"{context['scope_hints']['source_class']}_PRESENCE",
            raw_subject=subject,
            raw_predicate="PRESENT_IN_EXACT_TREE",
            raw_object={"format": "MARKDOWN_OR_TEXT"},
            parse_status="PARSED" if text else "UNRESOLVED",
        )
    ]
    for number, line in enumerate(text.splitlines(), 1):
        heading = _HEADING.match(line)
        field = _FIELD.match(line)
        if heading:
            rows.append(
                _observation(
                    **context,
                    locator=f"line:{number}",
                    observation_type=f"{context['scope_hints']['source_class']}_HEADING",
                    raw_subject=subject,
                    raw_predicate="DECLARES_HEADING",
                    raw_object={"level": len(heading.group(1)), "text": heading.group(2)},
                    parse_status="PARSED",
                )
            )
        elif field:
            rows.append(
                _observation(
                    **context,
                    locator=f"line:{number}",
                    observation_type=f"{context['scope_hints']['source_class']}_FIELD",
                    raw_subject=subject,
                    raw_predicate=field.group(1).strip(),
                    raw_object=field.group(2).strip(),
                    parse_status="PARSED",
                )
            )
    return rows


def extract_governed_sources(repository_root: Path | str, *, grt_observation_set: Mapping[str, Any]) -> dict[str, Any]:
    """Extract governed records from the exact component census supplied by GRT."""
    root = Path(repository_root).resolve()
    _require(grt_observation_set.get("court_record_status") == "EXACT_GIT_TREE", "ATLAS_GOVERNED_GRT_NOT_EXACT")
    commit = str(grt_observation_set.get("repository_commit", ""))
    tree = str(grt_observation_set.get("repository_tree", ""))
    _require(_SHA40.fullmatch(commit) is not None and _SHA40.fullmatch(tree) is not None, "ATLAS_GOVERNED_SOURCE_IDENTITY_INVALID")
    _require(str(_git(root, "rev-parse", f"{commit}^{{tree}}")).strip() == tree, "ATLAS_GOVERNED_TREE_MISMATCH")
    components = grt_observation_set.get("physical_components")
    _require(isinstance(components, Sequence) and not isinstance(components, (str, bytes)), "ATLAS_GOVERNED_COMPONENTS_INVALID")

    observations: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    for component in sorted(components, key=lambda row: str(row.get("path", ""))):
        _require(isinstance(component, Mapping), "ATLAS_GOVERNED_COMPONENT_INVALID")
        source_class = _source_class(component)
        if source_class is None:
            continue
        path = str(component.get("path", ""))
        blob = str(component.get("blob_hash_or_tree_hash", ""))
        _require(_SHA40.fullmatch(blob) is not None, "ATLAS_GOVERNED_BLOB_INVALID")
        exact_blob = str(_git(root, "rev-parse", f"{commit}:{path}")).strip()
        _require(exact_blob == blob, "ATLAS_GOVERNED_BLOB_MISMATCH")
        raw = _git(root, "show", f"{commit}:{path}", binary=True)
        _require(isinstance(raw, bytes) and b"\x00" not in raw, "ATLAS_GOVERNED_SOURCE_NOT_TEXT")
        text = raw.decode("utf-8", errors="replace")
        value: Any = None
        parsed_json = False
        if path.lower().endswith(".json"):
            try:
                value = json.loads(text)
                parsed_json = True
            except json.JSONDecodeError:
                value = None
        subject = _record_subject(path, value)
        scope_hints = {"source_class": source_class, "git_tree": tree}
        context = {
            "extractor_id": SOURCE_EXTRACTORS[source_class],
            "repository_commit": commit,
            "repository_tree": tree,
            "source_path": path,
            "source_blob_sha": blob,
            "scope_hints": scope_hints,
        }
        extracted = (
            _json_observations(value=value, subject=subject, context=context)
            if parsed_json
            else _text_observations(text=text, subject=subject, context=context)
        )
        observations.extend(extracted)
        sources.append(
            {
                "source_path": path,
                "source_blob_sha": blob,
                "component_id": str(component.get("component_id", "")),
                "source_class": source_class,
                "extractor_id": SOURCE_EXTRACTORS[source_class],
                "observation_count": len(extracted),
                "parse_status": "PARSED" if parsed_json or text else "UNRESOLVED",
                "authority_effect": "NONE_SOURCE_INDEX_ONLY",
            }
        )

    observations.sort(key=lambda row: row["observation_id"])
    sources.sort(key=lambda row: row["source_path"])
    body = {
        "schema": GOVERNED_SET_SCHEMA,
        "extractor_version": EXTRACTOR_VERSION,
        "repository_commit": commit,
        "repository_tree": tree,
        "grt_raw_observation_set_hash": str(grt_observation_set.get("raw_observation_set_hash", "")),
        "sources": sources,
        "raw_observations": observations,
        "source_class_counts": dict(sorted(Counter(row["source_class"] for row in sources).items())),
        "canonical_assertions": [],
        "court_record_status": "EXACT_GIT_TREE",
        "authority_effect": "NONE_GOVERNED_RAW_OBSERVATIONS_ONLY",
    }
    return {**body, "governed_observation_set_hash": canonical_sha256(body)}
