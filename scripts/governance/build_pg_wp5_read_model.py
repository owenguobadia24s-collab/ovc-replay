from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ovc.programme_genesis import (
    build_compact_portfolio_report,
    build_disabled_control_plane_projection,
    build_portfolio_health_report,
    build_portfolio_read_model,
    build_snapshot_from_registry,
    load_migration_source_registry,
)


DEFAULT_MIGRATION_REGISTRY = Path(
    "registries/governance/programme_genesis/MIGRATION_SOURCE_REGISTRY_v0_1.json"
)
DEFAULT_NATIVE_STATE = Path(
    "registries/governance/programme_genesis/OVC_PG_PROGRAMME_STATE_v0_2.json"
)
DEFAULT_GRAPH_REPORT = Path(
    "docs/releases/programme-genesis-v0-2/pg-g3/PG_G3_GRAPH_VALIDATION_REPORT.json"
)
DEFAULT_ADAPTER_REGISTRY = Path(
    "registries/governance/programme_genesis/CONTROL_PLANE_ADAPTER_REGISTRY_v0_1.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build PG-WP5 deterministic read-model, health, compact report and disabled adapter outputs."
    )
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root")
    parser.add_argument("--source-commit", required=True, help="Exact lowercase 40-character source commit SHA")
    parser.add_argument("--output-dir", type=Path, required=True, help="Explicit output directory")
    parser.add_argument("--migration-registry", type=Path, default=DEFAULT_MIGRATION_REGISTRY)
    parser.add_argument("--native-state", type=Path, default=DEFAULT_NATIVE_STATE)
    parser.add_argument("--graph-report", type=Path, default=DEFAULT_GRAPH_REPORT)
    parser.add_argument("--adapter-registry", type=Path, default=DEFAULT_ADAPTER_REGISTRY)
    return parser.parse_args()


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot load JSON source {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"JSON source must be an object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def graph_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "graph_id": report.get("graph_id"),
        "scope": report.get("scope"),
        "status": report.get("status"),
        "census": report.get("census", {}),
        "validation_findings": report.get("validation_findings", {}),
        "authority_paths": report.get("authority_paths", {}),
        "migration_boundary": report.get("migration_boundary", {}),
    }


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    output_dir = resolve(root, args.output_dir).resolve()
    try:
        output_dir.relative_to(root)
    except ValueError:
        pass

    migration_registry = load_migration_source_registry(resolve(root, args.migration_registry))
    migration_snapshot = build_snapshot_from_registry(root, migration_registry)
    native_state = load_json(resolve(root, args.native_state))
    graph_report = load_json(resolve(root, args.graph_report))
    adapter_registry = load_json(resolve(root, args.adapter_registry))

    read_model = build_portfolio_read_model(
        migration_snapshot,
        native_state,
        source_commit=args.source_commit,
        graph_summary=graph_summary(graph_report),
    )
    health = build_portfolio_health_report(root, read_model, adapter_config=adapter_registry)
    compact = build_compact_portfolio_report(read_model, health)
    adapter = build_disabled_control_plane_projection(compact, adapter_registry)

    outputs = {
        "migration_snapshot": output_dir / "migration-snapshot.json",
        "read_model": output_dir / "portfolio-read-model.json",
        "health": output_dir / "portfolio-health.json",
        "compact_report": output_dir / "portfolio-compact-report.json",
        "disabled_adapter": output_dir / "disabled-control-plane-adapter.json",
    }
    write_json(outputs["migration_snapshot"], migration_snapshot)
    write_json(outputs["read_model"], read_model)
    write_json(outputs["health"], health)
    write_json(outputs["compact_report"], compact)
    write_json(outputs["disabled_adapter"], adapter)

    summary = {
        "status": health["status"],
        "source_commit": args.source_commit,
        "programme_count": compact["programme_count"],
        "migrated_programme_count": compact["migrated_programme_count"],
        "migration_warning_count": compact["migration_warning_count"],
        "health_warning_count": compact["health_warning_count"],
        "health_blocking_count": compact["health_blocking_count"],
        "read_model_sha256": read_model["read_model_sha256"],
        "health_sha256": health["health_sha256"],
        "report_sha256": compact["report_sha256"],
        "adapter_projection_sha256": adapter["adapter_projection_sha256"],
        "adapter_status": adapter["status"],
        "outputs": {name: path.as_posix() for name, path in outputs.items()},
        "authority_effect": "NONE",
    }
    print(json.dumps(summary, sort_keys=True))
    return 0 if health["blocking_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
