from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .console_overview import (
    HealthDomainProjection,
    OverviewProjectionBuilder,
    STATUS_ALIASES,
    STATUS_PRIORITY,
    normalize_health_status,
)
from .read_model import ReadModelNode, ResearchReadModel


def load_read_model(path: Path) -> ResearchReadModel:
    """Load the deterministic RC-WP2 read-model fixture/source contract."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    nodes = tuple(
        ReadModelNode(
            object_id=str(node["object_id"]),
            object_type=str(node["object_type"]),
            authority=str(node["authority"]),
            status=str(node["status"]),
            source_refs=tuple(str(value) for value in node.get("source_refs", [])),
            payload=dict(node.get("payload", {})),
        )
        for node in raw.get("nodes", [])
    )
    return ResearchReadModel(
        schema=str(raw["schema"]),
        source_commit=str(raw["source_commit"]),
        catalogue_sha256=raw.get("catalogue_sha256"),
        nodes=nodes,
        health=tuple(dict(item) for item in raw.get("health", [])),
        logical_sha256=str(raw["logical_sha256"]),
    )


class CandidateOverviewProjectionBuilder(OverviewProjectionBuilder):
    """Canonical RC-WP2 candidate builder.

    Read-model node ``status`` frequently contains lifecycle or authority vocabulary rather
    than a health assertion. Only registered health statuses and aliases may create node-level
    attention items. Unknown lifecycle values remain visible in summaries but cannot be
    misrepresented as health ``BLOCK`` events.
    """

    def _attention(
        self,
        nodes: tuple[ReadModelNode, ...],
        health_domains: tuple[HealthDomainProjection, ...],
    ) -> tuple[dict[str, Any], ...]:
        rows: list[dict[str, Any]] = []
        for item in health_domains:
            if item.status in {"PASS", "NOT_APPLICABLE"}:
                continue
            rows.append(
                {
                    "object_id": item.object_id,
                    "object_type": "HEALTH_DOMAIN",
                    "status": item.status,
                    "label": item.label,
                    "consequence": item.consequence,
                    "source_refs": list(item.source_refs),
                }
            )

        for node in nodes:
            raw = str(node.status or "").strip().upper()
            if raw not in STATUS_PRIORITY and raw not in STATUS_ALIASES:
                continue
            status = normalize_health_status(raw)
            if status in {"PASS", "NOT_APPLICABLE", "NOT_EVALUATED"}:
                continue
            rows.append(
                {
                    "object_id": node.object_id,
                    "object_type": node.object_type,
                    "status": status,
                    "label": node.object_id,
                    "consequence": "Inspect the source object and its affected surfaces.",
                    "source_refs": list(node.source_refs),
                }
            )

        return tuple(
            sorted(
                rows,
                key=lambda item: (
                    -STATUS_PRIORITY[normalize_health_status(item["status"])],
                    str(item["object_type"]),
                    str(item["object_id"]),
                ),
            )
        )
