from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping

from .canonical import canonical_sha256
from .read_model import ReadModelNode, ResearchReadModel

OVERVIEW_SCHEMA = "ovc-research-console-overview-projection/v0.3"
HEALTH_DOMAIN_ORDER = (
    "DATA",
    "READ_MODEL",
    "ARTIFACTS",
    "QA",
    "RESEARCH_RECORDS",
    "REPOSITORY",
    "SEMANTIC",
)

STATUS_PRIORITY = {
    "BLOCK": 90,
    "MISSING": 85,
    "QUARANTINE": 80,
    "STALE": 75,
    "INCOMPLETE": 70,
    "CENSORED": 65,
    "WARN": 60,
    "NOT_EVALUATED": 50,
    "UNRESOLVED": 45,
    "NOT_MATERIALIZED": 40,
    "NOT_APPLICABLE": 10,
    "PASS": 0,
}

STATUS_ALIASES = {
    "ERROR": "BLOCK",
    "FAIL": "BLOCK",
    "FAILED": "BLOCK",
    "CRITICAL": "BLOCK",
    "WARNING": "WARN",
    "DEGRADED": "WARN",
    "UNKNOWN": "NOT_EVALUATED",
    "NONE": "NOT_EVALUATED",
}

SYSTEM_OBJECT_TYPES = {
    "ARTIFACT",
    "QA_RUN",
    "RELEASE",
    "RELEASE_DESCRIPTOR",
    "GATE",
    "GATE_PACKET",
    "CONFIGURATION",
}


@dataclass(frozen=True)
class HealthDomainProjection:
    object_id: str
    domain: str
    label: str
    status: str
    progress: float
    detail: str
    consequence: str
    affected_surfaces: tuple[str, ...]
    source_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["affected_surfaces"] = list(self.affected_surfaces)
        value["source_refs"] = list(self.source_refs)
        return value


@dataclass(frozen=True)
class OverviewProjection:
    schema: str
    source_commit: str
    read_model_sha256: str
    summary_status: str
    metrics: dict[str, int]
    health_domains: tuple[HealthDomainProjection, ...]
    releases: tuple[dict[str, Any], ...]
    gates: tuple[dict[str, Any], ...]
    sessions: tuple[dict[str, Any], ...]
    attention: tuple[dict[str, Any], ...]
    source_refs: tuple[str, ...]
    logical_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "source_commit": self.source_commit,
            "read_model_sha256": self.read_model_sha256,
            "summary_status": self.summary_status,
            "metrics": dict(self.metrics),
            "health_domains": [item.to_dict() for item in self.health_domains],
            "releases": [dict(item) for item in self.releases],
            "gates": [dict(item) for item in self.gates],
            "sessions": [dict(item) for item in self.sessions],
            "attention": [dict(item) for item in self.attention],
            "source_refs": list(self.source_refs),
            "logical_sha256": self.logical_sha256,
        }


def normalize_health_status(value: Any) -> str:
    candidate = str(value or "NOT_EVALUATED").strip().upper()
    candidate = STATUS_ALIASES.get(candidate, candidate)
    return candidate if candidate in STATUS_PRIORITY else "BLOCK"


def worst_status(statuses: Iterable[Any], *, empty: str = "NOT_EVALUATED") -> str:
    normalized = [normalize_health_status(value) for value in statuses]
    if not normalized:
        return normalize_health_status(empty)
    return max(normalized, key=lambda value: (STATUS_PRIORITY[value], value))


def _progress_for(status: str) -> float:
    return {
        "PASS": 1.0,
        "NOT_APPLICABLE": 1.0,
        "WARN": 0.55,
        "INCOMPLETE": 0.35,
        "CENSORED": 0.25,
        "STALE": 0.2,
        "QUARANTINE": 0.15,
        "NOT_MATERIALIZED": 0.0,
        "NOT_EVALUATED": 0.0,
        "UNRESOLVED": 0.0,
        "MISSING": 0.0,
        "BLOCK": 0.0,
    }[status]


def _node_type(node: ReadModelNode) -> str:
    return str(node.object_type).upper()


def _node_matches(node: ReadModelNode, tokens: Iterable[str]) -> bool:
    object_type = _node_type(node)
    return any(token in object_type for token in tokens)


def _compact_node(node: ReadModelNode) -> dict[str, Any]:
    return {
        "object_id": node.object_id,
        "object_type": node.object_type,
        "status": node.status,
        "authority": node.authority,
        "source_refs": list(node.source_refs),
        "payload": dict(node.payload),
    }


class OverviewProjectionBuilder:
    """Build a deterministic, replaceable Overview candidate from an approved read model.

    RC-WP2-v0.3 implements this projection but does not activate it in the console.
    RC-G2 remains the authority boundary for live projection consumption.
    """

    def build(self, model: ResearchReadModel) -> OverviewProjection:
        ordered_nodes = tuple(sorted(model.nodes, key=lambda item: (_node_type(item), item.object_id)))
        ordered_health = tuple(
            sorted(
                (dict(item) for item in model.health),
                key=lambda item: (
                    str(item.get("domain", "UNKNOWN")),
                    str(item.get("code", "UNKNOWN")),
                    str(item.get("object_id", "UNRESOLVED")),
                ),
            )
        )

        releases = self._summaries(ordered_nodes, ("RELEASE",))
        gates = self._summaries(ordered_nodes, ("GATE",))
        sessions = self._summaries(ordered_nodes, ("SESSION",))
        health_domains = self._health_domains(model, ordered_nodes, ordered_health)
        attention = self._attention(ordered_nodes, health_domains)
        summary_status = worst_status(item.status for item in health_domains)

        metrics = {
            "indexed_objects": len(ordered_nodes),
            "health_signals": len(ordered_health),
            "release_objects": len(releases),
            "gate_objects": len(gates),
            "session_objects": len(sessions),
            "attention_items": len(attention),
        }
        source_refs = (
            f"read-model:{model.logical_sha256}",
            f"source-commit:{model.source_commit}",
        )
        logical_payload = {
            "schema": OVERVIEW_SCHEMA,
            "source_commit": model.source_commit,
            "read_model_sha256": model.logical_sha256,
            "summary_status": summary_status,
            "metrics": metrics,
            "health_domains": [item.to_dict() for item in health_domains],
            "releases": list(releases),
            "gates": list(gates),
            "sessions": list(sessions),
            "attention": list(attention),
            "source_refs": list(source_refs),
        }
        return OverviewProjection(
            schema=OVERVIEW_SCHEMA,
            source_commit=model.source_commit,
            read_model_sha256=model.logical_sha256,
            summary_status=summary_status,
            metrics=metrics,
            health_domains=health_domains,
            releases=releases,
            gates=gates,
            sessions=sessions,
            attention=attention,
            source_refs=source_refs,
            logical_sha256=canonical_sha256(logical_payload),
        )

    def _summaries(self, nodes: tuple[ReadModelNode, ...], tokens: tuple[str, ...]) -> tuple[dict[str, Any], ...]:
        rows = []
        for node in nodes:
            if not _node_matches(node, tokens):
                continue
            payload = dict(node.payload)
            rows.append(
                {
                    "object_id": node.object_id,
                    "object_type": node.object_type,
                    "status": node.status,
                    "authority": node.authority,
                    "release_id": payload.get("release_id"),
                    "created_at": payload.get("created_at"),
                    "frozen_at": payload.get("frozen_at"),
                    "source_refs": list(node.source_refs),
                }
            )
        return tuple(sorted(rows, key=lambda item: (str(item["object_type"]), str(item["object_id"]))))

    def _health_domains(
        self,
        model: ResearchReadModel,
        nodes: tuple[ReadModelNode, ...],
        health: tuple[dict[str, Any], ...],
    ) -> tuple[HealthDomainProjection, ...]:
        by_domain: dict[str, list[dict[str, Any]]] = {domain: [] for domain in HEALTH_DOMAIN_ORDER}
        for signal in health:
            domain = self._map_signal_domain(str(signal.get("domain", "")))
            if domain is not None:
                by_domain[domain].append(signal)

        artifacts = tuple(node for node in nodes if _node_type(node) == "ARTIFACT")
        qa_runs = tuple(node for node in nodes if _node_type(node) == "QA_RUN")
        records = tuple(node for node in nodes if _node_type(node) not in SYSTEM_OBJECT_TYPES)
        data_nodes = tuple(node for node in nodes if _node_matches(node, ("DATA", "POPULATION", "BAR", "OHLC", "PROVIDER")))
        semantic_nodes = tuple(node for node in nodes if _node_matches(node, ("SEMANTIC", "TERM", "CONTRACT", "CLASSIFICATION")))

        domains = (
            self._signal_domain(
                "DATA",
                "Data",
                by_domain["DATA"],
                no_signal_detail=(
                    "Data-like objects are indexed, but no explicit coverage or chronology assertion is represented."
                    if data_nodes
                    else "No explicit data-health assertion is represented."
                ),
                consequence="Affected market-data and replay surfaces remain unverified.",
                surfaces=("OVERVIEW", "RESEARCH_REPLAY", "SYSTEM_CATALOGUE"),
            ),
            self._identity_domain(model),
            self._artifact_domain(artifacts, by_domain["ARTIFACTS"]),
            self._qa_domain(qa_runs, by_domain["QA"]),
            self._research_record_domain(records, by_domain["RESEARCH_RECORDS"]),
            self._repository_domain(model, by_domain["REPOSITORY"]),
            self._signal_domain(
                "SEMANTIC",
                "Semantic",
                by_domain["SEMANTIC"],
                no_signal_detail=(
                    "Semantic objects are indexed, but no explicit ambiguity or contract-health assertion is represented."
                    if semantic_nodes
                    else "No explicit semantic-health assertion is represented."
                ),
                consequence="No semantic-health or vocabulary-stability claim is made.",
                surfaces=("RESEARCH_BRIEF", "SYSTEM_LINEAGE"),
            ),
        )
        return tuple(domains)

    def _signal_domain(
        self,
        domain: str,
        label: str,
        signals: list[dict[str, Any]],
        *,
        no_signal_detail: str,
        consequence: str,
        surfaces: tuple[str, ...],
    ) -> HealthDomainProjection:
        if not signals:
            return self._domain(
                domain,
                label,
                "NOT_EVALUATED",
                no_signal_detail,
                consequence,
                surfaces,
                (),
            )
        status = worst_status(signal.get("status") for signal in signals)
        details = tuple(sorted({str(signal.get("detail", "No detail.")) for signal in signals}))
        refs = tuple(
            sorted(
                {
                    str(signal.get("object_id", "UNRESOLVED"))
                    for signal in signals
                }
            )
        )
        return self._domain(
            domain,
            label,
            status,
            " | ".join(details),
            consequence,
            surfaces,
            refs,
        )

    def _identity_domain(self, model: ResearchReadModel) -> HealthDomainProjection:
        valid = bool(model.source_commit and model.logical_sha256 and model.schema)
        status = "PASS" if valid else "BLOCK"
        detail = (
            f"Read-model identity is represented by {model.schema}."
            if valid
            else "Read-model schema, source commit or logical hash is missing."
        )
        return self._domain(
            "READ_MODEL",
            "Read model",
            status,
            detail,
            "Overview projection is reproducible." if valid else "Overview projection must fail closed.",
            ("OVERVIEW", "SYSTEM_LINEAGE"),
            (f"read-model:{model.logical_sha256 or 'MISSING'}",),
        )

    def _artifact_domain(
        self,
        artifacts: tuple[ReadModelNode, ...],
        signals: list[dict[str, Any]],
    ) -> HealthDomainProjection:
        if signals:
            return self._signal_domain(
                "ARTIFACTS",
                "Artifacts",
                signals,
                no_signal_detail="No artifact assertion is represented.",
                consequence="Affected sources may be unavailable or non-reproducible.",
                surfaces=("OVERVIEW", "SYSTEM_CATALOGUE", "SYSTEM_LINEAGE"),
            )
        if not artifacts:
            return self._domain(
                "ARTIFACTS",
                "Artifacts",
                "NOT_EVALUATED",
                "No artifact nodes or artifact-health assertions are represented.",
                "No artifact availability claim is made.",
                ("OVERVIEW", "SYSTEM_CATALOGUE"),
                (),
            )
        return self._domain(
            "ARTIFACTS",
            "Artifacts",
            "PASS",
            f"{len(artifacts)} catalogue artifact nodes are represented with no recorded catalogue issue.",
            "Represented artifact catalogue entries may be inspected.",
            ("OVERVIEW", "SYSTEM_CATALOGUE", "SYSTEM_LINEAGE"),
            tuple(sorted(ref for node in artifacts for ref in node.source_refs)),
        )

    def _qa_domain(
        self,
        qa_runs: tuple[ReadModelNode, ...],
        signals: list[dict[str, Any]],
    ) -> HealthDomainProjection:
        statuses = [signal.get("status") for signal in signals]
        statuses.extend(node.status for node in qa_runs)
        if not statuses:
            return self._domain(
                "QA",
                "QA",
                "NOT_EVALUATED",
                "No QA-run node or explicit QA-health assertion is represented.",
                "No assurance claim is made.",
                ("OVERVIEW", "SYSTEM_QA_GATES"),
                (),
            )
        status = worst_status(statuses)
        return self._domain(
            "QA",
            "QA",
            status,
            f"{len(qa_runs)} QA runs and {len(signals)} QA signals are represented.",
            "Blocking or warning assertions constrain affected surfaces." if status != "PASS" else "Represented QA assertions passed.",
            ("OVERVIEW", "SYSTEM_QA_GATES"),
            tuple(sorted({node.object_id for node in qa_runs} | {str(item.get('object_id', 'UNRESOLVED')) for item in signals})),
        )

    def _research_record_domain(
        self,
        records: tuple[ReadModelNode, ...],
        signals: list[dict[str, Any]],
    ) -> HealthDomainProjection:
        if signals:
            return self._signal_domain(
                "RESEARCH_RECORDS",
                "Research records",
                signals,
                no_signal_detail="No research-record assertion is represented.",
                consequence="Affected research records remain unverified.",
                surfaces=("OVERVIEW", "RESEARCH", "SYSTEM_LINEAGE"),
            )
        detail = (
            f"{len(records)} research-like nodes are indexed, but required schema, freeze, duplicate, cutoff and lineage assertions are not represented."
            if records
            else "No research-record nodes or required research-record health assertions are represented."
        )
        return self._domain(
            "RESEARCH_RECORDS",
            "Research records",
            "NOT_EVALUATED",
            detail,
            "No research-record health claim is made.",
            ("OVERVIEW", "RESEARCH", "SYSTEM_LINEAGE"),
            tuple(sorted(node.object_id for node in records)),
        )

    def _repository_domain(
        self,
        model: ResearchReadModel,
        signals: list[dict[str, Any]],
    ) -> HealthDomainProjection:
        if signals:
            return self._signal_domain(
                "REPOSITORY",
                "Repository",
                signals,
                no_signal_detail="No repository assertion is represented.",
                consequence="Affected registry and source paths remain unverified.",
                surfaces=("OVERVIEW", "SYSTEM_CONFIGURATION"),
            )
        status = "PASS" if model.source_commit else "BLOCK"
        return self._domain(
            "REPOSITORY",
            "Repository",
            status,
            (
                "The represented source commit is explicit; no working-tree cleanliness or remote-state claim is inferred."
                if status == "PASS"
                else "The represented source commit is missing."
            ),
            "Source identity may be displayed." if status == "PASS" else "Source-bound views must fail closed.",
            ("OVERVIEW", "SYSTEM_CONFIGURATION"),
            (f"source-commit:{model.source_commit or 'MISSING'}",),
        )

    def _domain(
        self,
        domain: str,
        label: str,
        status: str,
        detail: str,
        consequence: str,
        surfaces: tuple[str, ...],
        source_refs: tuple[str, ...],
    ) -> HealthDomainProjection:
        normalized = normalize_health_status(status)
        return HealthDomainProjection(
            object_id=f"HEALTH.{domain}",
            domain=domain,
            label=label,
            status=normalized,
            progress=_progress_for(normalized),
            detail=detail,
            consequence=consequence,
            affected_surfaces=tuple(surfaces),
            source_refs=tuple(sorted(set(source_refs))),
        )

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
            status = normalize_health_status(node.status)
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

    @staticmethod
    def _map_signal_domain(value: str) -> str | None:
        candidate = value.strip().upper()
        if candidate in HEALTH_DOMAIN_ORDER:
            return candidate
        if candidate in {"ARTIFACT", "CATALOGUE"}:
            return "ARTIFACTS"
        if candidate in {"RECORD", "RESEARCH", "RESEARCH_RECORD"}:
            return "RESEARCH_RECORDS"
        if candidate in {"REPO", "REGISTRY"}:
            return "REPOSITORY"
        if candidate.startswith("QA"):
            return "QA"
        if candidate.startswith("DATA") or candidate in {"PROVIDER", "POPULATION"}:
            return "DATA"
        if candidate.startswith("SEMANTIC") or candidate in {"TERM", "CONTRACT"}:
            return "SEMANTIC"
        return None
