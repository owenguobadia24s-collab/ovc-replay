from __future__ import annotations

import hashlib
import json
import mimetypes
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .canonical import canonical_json_bytes, canonical_sha256
from .paths import ApprovedPathRegistry


CATALOGUE_STATES = {
    "NOT_EVALUATED",
    "LOCAL_PRESENT",
    "LOCAL_VERIFIED",
    "REMOTE_PRESENT",
    "REMOTE_VERIFIED",
    "PARTIALLY_AVAILABLE",
    "MISSING",
    "EXPIRED",
    "QUARANTINED",
}


@dataclass(frozen=True)
class CatalogueIssue:
    code: str
    severity: str
    artifact_id: str
    detail: str


@dataclass(frozen=True)
class ArtifactNode:
    artifact_id: str
    artifact_type: str
    owner: str
    authority: str
    release_id: str | None
    sha256: str | None
    size_bytes: int | None
    media_type: str | None
    locations: tuple[dict[str, str], ...]
    availability: str
    expires_at: str | None = None
    dependencies: tuple[str, ...] = ()
    source_kind: str = "LOCAL"
    metadata: dict[str, Any] = field(default_factory=dict)

    def logical_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["locations"] = list(self.locations)
        value["dependencies"] = list(self.dependencies)
        return value


@dataclass(frozen=True)
class ArtifactCatalogue:
    schema: str
    generated_at: str
    source_commit: str
    nodes: tuple[ArtifactNode, ...]
    issues: tuple[CatalogueIssue, ...]
    logical_inventory_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "generated_at": self.generated_at,
            "source_commit": self.source_commit,
            "nodes": [node.logical_dict() for node in self.nodes],
            "issues": [asdict(issue) for issue in self.issues],
            "logical_inventory_sha256": self.logical_inventory_sha256,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ArtifactCatalogue":
        nodes = tuple(
            ArtifactNode(
                **{
                    **node,
                    "locations": tuple(node.get("locations", [])),
                    "dependencies": tuple(node.get("dependencies", [])),
                }
            )
            for node in value.get("nodes", [])
        )
        issues = tuple(CatalogueIssue(**issue) for issue in value.get("issues", []))
        return cls(
            schema=value["schema"],
            generated_at=value["generated_at"],
            source_commit=value["source_commit"],
            nodes=nodes,
            issues=issues,
            logical_inventory_sha256=value["logical_inventory_sha256"],
        )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_time(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("catalogue timestamps must be timezone-aware")
    return parsed.astimezone(timezone.utc)


class ArtifactCatalogueBuilder:
    def __init__(self, path_registry: ApprovedPathRegistry):
        self.path_registry = path_registry

    def scan(
        self,
        *,
        aliases: Iterable[str],
        generated_at: str,
        source_commit: str,
        owner: str = "ovc-replay",
        authority: str = "DERIVED_CATALOGUE_ONLY",
    ) -> ArtifactCatalogue:
        nodes: list[ArtifactNode] = []
        for alias in sorted(set(aliases)):
            for path in self.path_registry.safe_files(alias):
                digest = _sha256_file(path)
                media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                artifact_type = "MANIFEST" if "manifest" in path.name.lower() else "FILE"
                location = self.path_registry.portable_location(alias, path)
                nodes.append(
                    ArtifactNode(
                        artifact_id=f"artifact:sha256:{digest}",
                        artifact_type=artifact_type,
                        owner=owner,
                        authority=authority,
                        release_id=None,
                        sha256=digest,
                        size_bytes=path.stat().st_size,
                        media_type=media_type,
                        locations=(location,),
                        availability="LOCAL_VERIFIED",
                    )
                )
        return self._finish(nodes, [], generated_at=generated_at, source_commit=source_commit)

    def verify_declarations(
        self,
        declarations: list[dict[str, Any]],
        *,
        generated_at: str,
        source_commit: str,
    ) -> ArtifactCatalogue:
        nodes: list[ArtifactNode] = []
        issues: list[CatalogueIssue] = []
        now = _parse_time(generated_at)
        for item in declarations:
            artifact_id = str(item["artifact_id"])
            source_kind = str(item.get("source_kind", "LOCAL"))
            expires_at = item.get("expires_at")
            if expires_at and _parse_time(expires_at) <= now:
                availability = "EXPIRED"
                issues.append(CatalogueIssue("EXPIRED_CI_ARTIFACT", "BLOCK", artifact_id, str(expires_at)))
                nodes.append(self._node_from_declaration(item, availability=availability))
                continue

            location = item.get("location")
            if source_kind == "LOCAL":
                if not location:
                    raise ValueError(f"LOCAL declaration requires location: {artifact_id}")
                alias = str(location["root_alias"])
                rel = str(location["relative_path"])
                path = self.path_registry.resolve(alias, rel, must_exist=False)
                if not path.exists():
                    issues.append(CatalogueIssue("MISSING_ARTIFACT", "BLOCK", artifact_id, f"{alias}:{rel}"))
                    nodes.append(self._node_from_declaration(item, availability="MISSING"))
                    continue
                actual_size = path.stat().st_size
                actual_hash = _sha256_file(path)
                mismatches: list[str] = []
                if item.get("size_bytes") is not None and int(item["size_bytes"]) != actual_size:
                    mismatches.append("size_bytes")
                if item.get("sha256") and str(item["sha256"]) != actual_hash:
                    mismatches.append("sha256")
                if mismatches:
                    issues.append(CatalogueIssue("HASH_MISMATCH", "BLOCK", artifact_id, ",".join(mismatches)))
                    nodes.append(self._node_from_declaration(item, availability="LOCAL_PRESENT", actual_hash=actual_hash, actual_size=actual_size))
                else:
                    nodes.append(self._node_from_declaration(item, availability="LOCAL_VERIFIED", actual_hash=actual_hash, actual_size=actual_size))
            elif source_kind in {"GITHUB_ACTIONS", "R2"}:
                declared_state = str(item.get("availability", "NOT_EVALUATED"))
                if declared_state not in CATALOGUE_STATES:
                    raise ValueError(f"invalid declared availability: {declared_state}")
                nodes.append(self._node_from_declaration(item, availability=declared_state))
            else:
                raise ValueError(f"unsupported source_kind: {source_kind}")

        declared_ids = {node.artifact_id for node in nodes}
        for node in nodes:
            if node.artifact_type == "MANIFEST" and not node.dependencies:
                issues.append(CatalogueIssue("ORPHAN_MANIFEST", "WARN", node.artifact_id, "manifest declares no dependent artifacts"))
            for dependency in node.dependencies:
                if dependency not in declared_ids:
                    issues.append(CatalogueIssue("MISSING_DEPENDENCY", "BLOCK", node.artifact_id, dependency))
        return self._finish(nodes, issues, generated_at=generated_at, source_commit=source_commit)

    @staticmethod
    def _node_from_declaration(
        item: dict[str, Any],
        *,
        availability: str,
        actual_hash: str | None = None,
        actual_size: int | None = None,
    ) -> ArtifactNode:
        location = item.get("location")
        locations: tuple[dict[str, str], ...] = (dict(location),) if location else tuple(dict(x) for x in item.get("locations", []))
        return ArtifactNode(
            artifact_id=str(item["artifact_id"]),
            artifact_type=str(item.get("artifact_type", "FILE")),
            owner=str(item.get("owner", "ovc-replay")),
            authority=str(item.get("authority", "DECLARED_ONLY")),
            release_id=item.get("release_id"),
            sha256=actual_hash or item.get("sha256"),
            size_bytes=actual_size if actual_size is not None else item.get("size_bytes"),
            media_type=item.get("media_type"),
            locations=locations,
            availability=availability,
            expires_at=item.get("expires_at"),
            dependencies=tuple(item.get("dependencies", [])),
            source_kind=str(item.get("source_kind", "LOCAL")),
            metadata=dict(item.get("metadata", {})),
        )

    @staticmethod
    def _finish(
        nodes: list[ArtifactNode],
        issues: list[CatalogueIssue],
        *,
        generated_at: str,
        source_commit: str,
    ) -> ArtifactCatalogue:
        ordered_nodes = tuple(sorted(nodes, key=lambda node: node.artifact_id))
        ordered_issues = tuple(sorted(issues, key=lambda issue: (issue.code, issue.artifact_id, issue.detail)))
        logical_material = {
            "source_commit": source_commit,
            "nodes": [node.logical_dict() for node in ordered_nodes],
            "issues": [asdict(issue) for issue in ordered_issues],
        }
        return ArtifactCatalogue(
            schema="ovc-research-operations-artifact-catalogue/v0.1",
            generated_at=generated_at,
            source_commit=source_commit,
            nodes=ordered_nodes,
            issues=ordered_issues,
            logical_inventory_sha256=canonical_sha256(logical_material),
        )


def write_catalogue(path: str | Path, catalogue: ArtifactCatalogue) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(canonical_json_bytes(catalogue.to_dict()))


def read_catalogue(path: str | Path) -> ArtifactCatalogue:
    return ArtifactCatalogue.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def catalogue_report(catalogue: ArtifactCatalogue) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for node in catalogue.nodes:
        counts[node.availability] = counts.get(node.availability, 0) + 1
    issue_counts: dict[str, int] = {}
    for issue in catalogue.issues:
        issue_counts[issue.code] = issue_counts.get(issue.code, 0) + 1
    return {
        "schema": "ovc-research-operations-artifact-report/v0.1",
        "source_commit": catalogue.source_commit,
        "logical_inventory_sha256": catalogue.logical_inventory_sha256,
        "artifact_count": len(catalogue.nodes),
        "availability_counts": dict(sorted(counts.items())),
        "issue_counts": dict(sorted(issue_counts.items())),
        "blocking_issue_count": sum(1 for issue in catalogue.issues if issue.severity == "BLOCK"),
    }
