from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from .migration import file_sha256, logical_sha256


class ReadModelError(ValueError):
    """Raised when a deterministic Programme Genesis read model cannot be built safely."""


def _compact_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _normalise_blockers(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return deepcopy(value)
    return [deepcopy(value)]


def build_portfolio_read_model(
    migration_snapshot: Mapping[str, Any],
    native_pg_state: Mapping[str, Any],
    *,
    source_commit: str,
    graph_summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if migration_snapshot.get("schema") != "ovc-programme-migration-snapshot/v1":
        raise ReadModelError("unsupported migration snapshot schema")
    if migration_snapshot.get("status") != "PASS":
        raise ReadModelError("blocking migration snapshot cannot feed the read model")
    if migration_snapshot.get("authority_effect") != "NONE":
        raise ReadModelError("migration snapshot must be authority-neutral")
    if native_pg_state.get("programme_id") != "OVC-PG-v0.2":
        raise ReadModelError("native Programme Genesis state is missing or mismatched")
    if len(source_commit) != 40 or any(character not in "0123456789abcdef" for character in source_commit):
        raise ReadModelError("source_commit must be a lowercase 40-character commit SHA")

    programmes: list[dict[str, Any]] = []
    for record in migration_snapshot.get("records", []):
        preserved = record.get("preserved_values", {})
        programmes.append(
            {
                "programme_id": record["programme_id"],
                "source_kind": "MIGRATED_PROGRAMME_STATE",
                "source_path": record["source"]["path"],
                "source_sha256": record["source"]["sha256"],
                "status": deepcopy(preserved.get("status")),
                "current_packet": deepcopy(preserved.get("current_packet")),
                "current_gate": deepcopy(preserved.get("current_gate")),
                "authority": deepcopy(preserved.get("authority")),
                "blockers": _normalise_blockers(preserved.get("blockers")),
                "next_action": deepcopy(preserved.get("next_action")),
                "confidence": record["confidence"],
                "migration_uncertainty": deepcopy(record["migration_uncertainty"]),
                "unresolved_fields": list(record.get("unresolved_fields", [])),
                "conflicting_fields": list(record.get("conflicting_fields", [])),
                "native_governance_deadline": record["native_governance_deadline"],
                "authority_effect": "NONE",
                "canonical": False,
            }
        )

    programmes.append(
        {
            "programme_id": "OVC-PG-v0.2",
            "source_kind": "NATIVE_PROGRAMME_STATE",
            "source_path": "registries/governance/programme_genesis/OVC_PG_PROGRAMME_STATE_v0_2.json",
            "source_sha256": None,
            "status": deepcopy(native_pg_state.get("status")),
            "current_packet": deepcopy(native_pg_state.get("current_packet")),
            "current_gate": deepcopy(native_pg_state.get("current_gate")),
            "authority": deepcopy(native_pg_state.get("authority")),
            "blockers": _normalise_blockers(native_pg_state.get("blockers")),
            "next_action": deepcopy(native_pg_state.get("next_action")),
            "confidence": "NATIVE",
            "migration_uncertainty": None,
            "unresolved_fields": [],
            "conflicting_fields": [],
            "native_governance_deadline": None,
            "authority_effect": "NONE",
            "canonical": True,
        }
    )
    programmes.sort(key=lambda row: row["programme_id"])

    status_counts: dict[str, int] = {}
    for programme in programmes:
        status = str(programme.get("status") or "UNKNOWN")
        status_counts[status] = status_counts.get(status, 0) + 1

    migration_warnings = [
        deepcopy(finding)
        for finding in migration_snapshot.get("conflict_ledger", [])
        if finding.get("severity") == "WARN"
    ]
    health_summary = {
        "programme_count": len(programmes),
        "native_programme_count": 1,
        "migrated_programme_count": len(programmes) - 1,
        "migration_warning_count": len(migration_warnings),
        "migration_blocker_count": int(migration_snapshot.get("blocking_conflict_count", 0)),
        "programmes_with_blockers": sum(bool(programme["blockers"]) for programme in programmes),
        "programmes_with_unresolved_fields": sum(bool(programme["unresolved_fields"]) for programme in programmes),
        "status_counts": dict(sorted(status_counts.items())),
    }

    graph = deepcopy(dict(graph_summary or {}))
    result: dict[str, Any] = {
        "schema": "ovc-programme-portfolio-read-model/v1",
        "programme_id": "OVC-PG-v0.2",
        "source_commit": source_commit,
        "status": "PASS_WITH_WARNINGS" if migration_warnings else "PASS",
        "authority_effect": "NONE_READ_ONLY_DERIVED_VIEW",
        "canonical_adoption": "DENIED_PENDING_PG_G6",
        "admission_enforcement": "DENIED_PENDING_PG_G6",
        "control_plane_route": "DENIED_PENDING_PG_G6",
        "automatic_upkeep": "DENIED_PENDING_PG_G7",
        "programmes": programmes,
        "health_summary": health_summary,
        "migration_findings": migration_warnings,
        "graph_summary": graph,
        "source_snapshot_sha256": migration_snapshot["snapshot_sha256"],
        "read_model_replaceable": True,
        "rollback": "Discard and rebuild this read model from programme-owned state, the provisional migration snapshot and accepted graph records.",
    }
    result["read_model_sha256"] = logical_sha256(result)
    return result


def build_portfolio_health_report(
    repository_root: Path | str,
    read_model: Mapping[str, Any],
    *,
    adapter_config: Mapping[str, Any],
) -> dict[str, Any]:
    root = Path(repository_root)
    findings: list[dict[str, Any]] = []

    for programme in read_model.get("programmes", []):
        if programme.get("source_kind") != "MIGRATED_PROGRAMME_STATE":
            continue
        path = root / programme["source_path"]
        if not path.is_file():
            findings.append(
                {
                    "finding_type": "MIGRATION_SOURCE_MISSING",
                    "severity": "BLOCK",
                    "programme_id": programme["programme_id"],
                    "source_path": programme["source_path"],
                    "authority_effect": "NONE",
                }
            )
            continue
        actual_hash = file_sha256(path)
        if actual_hash != programme["source_sha256"]:
            findings.append(
                {
                    "finding_type": "MIGRATION_SOURCE_HASH_MISMATCH",
                    "severity": "BLOCK",
                    "programme_id": programme["programme_id"],
                    "source_path": programme["source_path"],
                    "expected_sha256": programme["source_sha256"],
                    "actual_sha256": actual_hash,
                    "authority_effect": "NONE",
                }
            )
        if programme.get("migration_uncertainty") is None:
            findings.append(
                {
                    "finding_type": "MIGRATION_UNCERTAINTY_MISSING",
                    "severity": "BLOCK",
                    "programme_id": programme["programme_id"],
                    "authority_effect": "NONE",
                }
            )
        if programme.get("unresolved_fields"):
            findings.append(
                {
                    "finding_type": "MIGRATION_UNRESOLVED_FIELDS",
                    "severity": "WARN",
                    "programme_id": programme["programme_id"],
                    "fields": sorted(programme["unresolved_fields"]),
                    "authority_effect": "NONE",
                }
            )

    required_disabled = {
        "enabled": False,
        "route_registered": False,
        "write_enabled": False,
        "enforcement_enabled": False,
    }
    for field, expected in required_disabled.items():
        if adapter_config.get(field) is not expected:
            findings.append(
                {
                    "finding_type": "CONTROL_PLANE_ADAPTER_PREMATURE_ACTIVATION",
                    "severity": "QUARANTINE",
                    "field": field,
                    "value": adapter_config.get(field),
                    "authority_effect": "NONE",
                }
            )

    if adapter_config.get("activation_gate") != "PG-G6":
        findings.append(
            {
                "finding_type": "CONTROL_PLANE_ADAPTER_GATE_MISMATCH",
                "severity": "BLOCK",
                "value": adapter_config.get("activation_gate"),
                "authority_effect": "NONE",
            }
        )

    blocking = [finding for finding in findings if finding["severity"] in {"BLOCK", "QUARANTINE"}]
    warning = [finding for finding in findings if finding["severity"] == "WARN"]
    report: dict[str, Any] = {
        "schema": "ovc-programme-portfolio-health/v1",
        "programme_id": "OVC-PG-v0.2",
        "status": "FAIL" if blocking else ("PASS_WITH_WARNINGS" if warning else "PASS"),
        "read_model_sha256": read_model["read_model_sha256"],
        "finding_count": len(findings),
        "warning_count": len(warning),
        "blocking_count": len(blocking),
        "findings": sorted(findings, key=lambda item: (item["severity"], item["finding_type"], str(item.get("programme_id", "")))),
        "control_plane_adapter": {
            "adapter_id": adapter_config.get("adapter_id"),
            "enabled": adapter_config.get("enabled"),
            "route_registered": adapter_config.get("route_registered"),
            "write_enabled": adapter_config.get("write_enabled"),
            "enforcement_enabled": adapter_config.get("enforcement_enabled"),
            "activation_gate": adapter_config.get("activation_gate"),
        },
        "authority_effect": "NONE_HEALTH_ONLY",
        "rollback": "Discard and rebuild the health report; do not modify sources or adapter activation state.",
    }
    report["health_sha256"] = _compact_hash(report)
    return report


def build_compact_portfolio_report(read_model: Mapping[str, Any], health_report: Mapping[str, Any]) -> dict[str, Any]:
    if health_report.get("read_model_sha256") != read_model.get("read_model_sha256"):
        raise ReadModelError("health report does not bind the supplied read model")
    report = {
        "schema": "ovc-programme-portfolio-compact-report/v1",
        "programme_id": "OVC-PG-v0.2",
        "source_commit": read_model["source_commit"],
        "read_model_status": read_model["status"],
        "health_status": health_report["status"],
        "programme_count": read_model["health_summary"]["programme_count"],
        "migrated_programme_count": read_model["health_summary"]["migrated_programme_count"],
        "migration_warning_count": read_model["health_summary"]["migration_warning_count"],
        "health_warning_count": health_report["warning_count"],
        "health_blocking_count": health_report["blocking_count"],
        "status_counts": deepcopy(read_model["health_summary"]["status_counts"]),
        "control_plane_adapter_status": "DISABLED",
        "canonical_adoption": read_model["canonical_adoption"],
        "admission_enforcement": read_model["admission_enforcement"],
        "control_plane_route": read_model["control_plane_route"],
        "automatic_upkeep": read_model["automatic_upkeep"],
        "authority_effect": "NONE_COMPACT_REPORT_ONLY",
    }
    report["report_sha256"] = _compact_hash(report)
    return report


def build_disabled_control_plane_projection(
    compact_report: Mapping[str, Any],
    adapter_config: Mapping[str, Any],
) -> dict[str, Any]:
    if any(
        adapter_config.get(field) is not False
        for field in ("enabled", "route_registered", "write_enabled", "enforcement_enabled")
    ):
        raise ReadModelError("Control Plane adapter activation is not authorised before PG-G6")
    if adapter_config.get("activation_gate") != "PG-G6":
        raise ReadModelError("Control Plane adapter activation gate must be PG-G6")
    projection = {
        "schema": "ovc-control-plane-programme-portfolio-adapter/v1",
        "adapter_id": adapter_config["adapter_id"],
        "status": "DISABLED_PENDING_PG_G6",
        "route_registered": False,
        "read_only": True,
        "write_enabled": False,
        "enforcement_enabled": False,
        "payload_available_locally": True,
        "payload": deepcopy(dict(compact_report)),
        "authority_effect": "NONE_DISABLED_ADAPTER_CANDIDATE",
        "activation_gate": "PG-G6",
    }
    projection["adapter_projection_sha256"] = _compact_hash(projection)
    return projection
