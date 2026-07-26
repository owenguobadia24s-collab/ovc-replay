from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from .canonical import canonical_sha256
from .catalogue import ArtifactCatalogue


@dataclass(frozen=True)
class ReadModelNode:
    object_id: str
    object_type: str
    authority: str
    status: str
    source_refs: tuple[str, ...]
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["source_refs"] = list(self.source_refs)
        return value


@dataclass(frozen=True)
class ResearchReadModel:
    schema: str
    source_commit: str
    catalogue_sha256: str | None
    nodes: tuple[ReadModelNode, ...]
    health: tuple[dict[str, Any], ...]
    logical_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "source_commit": self.source_commit,
            "catalogue_sha256": self.catalogue_sha256,
            "nodes": [node.to_dict() for node in self.nodes],
            "health": list(self.health),
            "logical_sha256": self.logical_sha256,
        }


class ReadModelBuilder:
    """Build a replaceable, non-authoritative index from compact source objects."""

    def build(
        self,
        *,
        source_commit: str,
        catalogue: ArtifactCatalogue | None,
        records: Iterable[dict[str, Any]],
        qa_runs: Iterable[dict[str, Any]] = (),
    ) -> ResearchReadModel:
        nodes: list[ReadModelNode] = []
        health: list[dict[str, Any]] = []

        if catalogue is not None:
            for artifact in catalogue.nodes:
                nodes.append(ReadModelNode(
                    object_id=artifact.artifact_id,
                    object_type="ARTIFACT",
                    authority=artifact.authority,
                    status=artifact.availability,
                    source_refs=tuple(f"{loc['root_alias']}:{loc['relative_path']}" for loc in artifact.locations),
                    payload={"release_id": artifact.release_id, "sha256": artifact.sha256, "dependencies": list(artifact.dependencies)},
                ))
            health.extend({"domain": "ARTIFACT", "code": issue.code, "status": issue.severity, "object_id": issue.artifact_id, "detail": issue.detail} for issue in catalogue.issues)

        for record in records:
            record_id = str(record.get("record_id", "UNRESOLVED"))
            authority = str(record.get("authority_state", "UNRESOLVED"))
            status = str(record.get("lifecycle_state", authority))
            sources = tuple(str(x.get("release_id", x)) if isinstance(x, dict) else str(x) for x in record.get("source_release_refs", []))
            nodes.append(ReadModelNode(
                object_id=record_id,
                object_type=str(record.get("record_type", "UNKNOWN")),
                authority=authority,
                status=status,
                source_refs=sources,
                payload={
                    "created_at": record.get("created_at"),
                    "frozen_at": record.get("frozen_at"),
                    "reproducibility_state": record.get("reproducibility_state"),
                    "missingness": record.get("missingness", []),
                    "lineage": record.get("lineage", {}),
                },
            ))

        for run in qa_runs:
            run_id = str(run.get("logical_sha256", "UNRESOLVED"))
            nodes.append(ReadModelNode(
                object_id=run_id,
                object_type="QA_RUN",
                authority="DERIVED_ASSURANCE_ONLY",
                status=str(run.get("disposition", "NOT_EVALUATED")),
                source_refs=(str(run.get("target_id", "UNRESOLVED")),),
                payload={"assertions": run.get("assertions", []), "source_commit": run.get("source_commit")},
            ))

        ordered_nodes = tuple(sorted(nodes, key=lambda item: (item.object_type, item.object_id)))
        ordered_health = tuple(sorted(health, key=lambda item: (item["domain"], item["code"], item["object_id"])))
        logical = {
            "source_commit": source_commit,
            "catalogue_sha256": catalogue.logical_inventory_sha256 if catalogue else None,
            "nodes": [node.to_dict() for node in ordered_nodes],
            "health": list(ordered_health),
        }
        return ResearchReadModel(
            schema="ovc-research-operations-read-model/v0.1",
            source_commit=source_commit,
            catalogue_sha256=catalogue.logical_inventory_sha256 if catalogue else None,
            nodes=ordered_nodes,
            health=ordered_health,
            logical_sha256=canonical_sha256(logical),
        )


def query_nodes(model: ResearchReadModel, *, object_type: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
    result = []
    for node in model.nodes:
        if object_type is not None and node.object_type != object_type:
            continue
        if status is not None and node.status != status:
            continue
        result.append(node.to_dict())
    return result
